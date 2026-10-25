"""JarvisERP API + UI server.

    python -m jarvis.api.server --seed 2026 --port 8000     ->  http://localhost:8000
"""
from __future__ import annotations

import argparse
import asyncio
import json
import threading
import traceback

import uvicorn
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from jarvis import config
from jarvis.agent import injector, llm, personas
from jarvis.agent.session import Session
from jarvis.api import closepack, graph
from jarvis.evals import baselines, score
from jarvis.work import events, ledger, sync
from jarvis.work.db import L
from jarvis.work.transition import Denied, get_item, why

app = FastAPI(title="JarvisERP", version="1.0")
STATE: dict = {"session": None, "busy": None, "auto_controller": False, "speed": 0.35}


def S() -> Session:
    if STATE["session"] is None:
        STATE["session"] = Session(config.world_seed(), speed=STATE["speed"])
    return STATE["session"]


def background(name: str, fn, *a, **kw):
    if STATE["busy"]:
        raise HTTPException(409, f"busy: {STATE['busy']}")

    def run():
        STATE["busy"] = name
        events.publish("busy", name=name, on=True)
        try:
            fn(*a, **kw)
            if STATE["auto_controller"] and name in ("close", "october", "onboard", "inject"):
                personas.auto_controller(S().engine)
        except Exception as e:
            traceback.print_exc()
            events.publish("error", where=name, error=str(e))
        finally:
            STATE["busy"] = None
            events.publish("busy", name=name, on=False)
            events.publish("refresh")

    threading.Thread(target=run, daemon=True).start()
    return {"started": name}


def item_out(it: dict) -> dict:
    return {k: it[k] for k in ("item_id", "kind", "anchor", "state", "title", "period", "confidence", "rationale",
                               "question", "answer", "policy_id", "precedent_ids", "proposed_by", "approved_by",
                               "parent_id", "review", "evidence", "proposal", "source_refs")}


# ------------------------------------------------------------------ UI + SSE
@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(config.UI_DIR / "workbench.html")


@app.get("/landing", response_class=HTMLResponse)
def landing():
    return FileResponse(config.UI_DIR / "landing.html")


@app.get("/synapse", response_class=HTMLResponse)
def synapse():
    return FileResponse(config.UI_DIR / "synapse.html")


from jarvis.api.wb_routes import router as wb_router  # noqa: E402
app.include_router(wb_router)


app.mount("/ui", StaticFiles(directory=config.UI_DIR), name="ui")


@app.get("/events")
async def sse():
    q = events.subscribe()

    async def gen():
        try:
            yield f"data: {json.dumps({'type': 'hello'})}\n\n"
            while True:
                try:
                    ev = await asyncio.get_event_loop().run_in_executor(None, lambda: q.get(timeout=15))
                    yield f"data: {json.dumps(ev, default=str)}\n\n"
                except Exception:
                    yield ": ping\n\n"
        finally:
            events.unsubscribe(q)
    return StreamingResponse(gen(), media_type="text/event-stream")


# ------------------------------------------------------------------ state
@app.get("/api/state")
def state():
    s = S()
    db = s.db
    boot = bool(db.kv_get("bootstrapped"))
    st = s.engine.status() if boot else {}
    pols = db.q("SELECT policy_id, version, title, status, evidence, approved_by, rule_text, matcher FROM policies "
                "ORDER BY policy_id, version")
    for p in pols:
        p["evidence"] = L(p["evidence"], [])
        p["matcher"] = L(p["matcher"], {})
    # Test LLM live, not just if key is configured
    llm_test = llm.test_live()
    llm_live = llm_test.get("status") == "live"
    
    return {"seed": s.seed, "company": "Afterglow Labs, Inc.", "period": config.CLOSE_PERIOD, "bootstrapped": boot,
            "phase": db.kv_get("phase"), "world_date": db.kv_get("world_date"), "busy": STATE["busy"],
            "auto_controller": STATE["auto_controller"], "llm": llm_live, "search": s.ctx.search.status(),
            "paypal_fault": sync.PayPalAPI.fault, "status": st, "policies": pols,
            "counts": {"records": db.one("SELECT COUNT(*) n FROM records")["n"],
                       "docs": db.one("SELECT COUNT(*) n FROM docs")["n"],
                       "precedents": db.one("SELECT COUNT(*) n FROM precedents")["n"],
                       "ledger_entries": db.one("SELECT COUNT(*) n FROM ledger_entries")["n"],
                       "audit": db.one("SELECT COUNT(*) n FROM audit_log")["n"],
                       "denied": db.one("SELECT COUNT(*) n FROM audit_log WHERE allowed=0")["n"]},
            "templates": {k: v["label"] for k, v in injector.TEMPLATES.items()}}


@app.get("/api/llm_status")
def llm_status():
    """Test if LLM is actually live (not just configured)."""
    return llm.test_live()


@app.get("/api/graph")
def get_graph():
    return graph.build(S().db)


@app.get("/api/items")
def items(state: str | None = None):
    db = S().db
    rows = db.q("SELECT item_id FROM work_items" + (" WHERE state=?" if state else "") + " ORDER BY created_at",
                (state,) if state else ())
    return [item_out(get_item(db, r["item_id"])) for r in rows]


@app.get("/api/item/{item_id}")
def item(item_id: str):
    db = S().db
    it = get_item(db, item_id)
    if not it:
        raise HTTPException(404)
    je = db.one("SELECT entry_id FROM ledger_entries WHERE work_item_id=?", (item_id,))
    return {**item_out(it), "audit": why(db, item_id), "ledger_entry": ledger.entry(db, je["entry_id"]) if je else None,
            "messages": db.q("SELECT * FROM messages WHERE item_id=? ORDER BY at", (item_id,))}


@app.get("/api/node/{node_id:path}")
def node(node_id: str):
    db = S().db
    kind, _, rid = node_id.partition(":")
    if kind == "rec":
        r = db.one("SELECT * FROM records WHERE record_id=?", (rid,))
        if r:
            r["fields"] = L(r["fields"], {})
            r["raw"] = L((db.one("SELECT payload FROM raw_rows WHERE raw_id=?", (r["raw_ref"],)) or {}).get("payload"), {})
        return {"type": "record", "data": r}
    if kind == "doc":
        return {"type": "doc", "data": db.one("SELECT * FROM docs WHERE doc_id=?", (rid,))}
    if kind == "prec":
        return {"type": "precedent", "data": db.one("SELECT * FROM precedents WHERE prec_id=?", (rid,))}
    if kind == "pol":
        return {"type": "policy", "data": db.q("SELECT * FROM policies WHERE policy_id=? ORDER BY version", (rid,)),
                "audit": why(db, f"{rid} v1")}
    if kind == "je":
        return {"type": "ledger", "data": ledger.entry(db, rid)}
    if kind == "vendor":
        return {"type": "vendor", "data": db.one("SELECT * FROM vendors WHERE vendor_id=?", (rid,)),
                "aliases": db.q("SELECT * FROM vendor_aliases WHERE vendor_id=?", (rid,))}
    if kind == "denied":
        return {"type": "denied", "data": db.one("SELECT * FROM audit_log WHERE seq=?", (int(rid),))}
    return {"type": kind, "data": {"id": node_id}}


@app.get("/api/why/{subject:path}")
def get_why(subject: str):
    return why(S().db, subject)


@app.get("/api/audit")
def audit(limit: int = 200):
    return S().db.q("SELECT * FROM audit_log ORDER BY seq DESC LIMIT ?", (limit,))


@app.get("/api/messages")
def messages():
    return S().db.q("SELECT * FROM messages ORDER BY at DESC")


@app.get("/api/recon")
def recon(period: str = config.CLOSE_PERIOD):
    return ledger.bank_reconciliation(S().db, period)


@app.get("/api/verify")
def verify():
    return S().verify()


@app.get("/api/score")
def get_score():
    """Eval view: compares Jarvis's outcomes to the planted answer key (never visible to the agent)."""
    s = S()
    key = s.world / "answer_key.json"
    phases = ("close", "october") if s.db.kv_get("phase") == "october" else ("close",)
    jar = score.score(key, score.outcomes(s.db), phases)
    b1 = score.score(key, baselines.run_b1(s.world), ("close",))
    return {"jarvis": jar, "b1": b1["summary"], "phases": phases}


@app.get("/api/export/gl.csv", response_class=PlainTextResponse)
def gl_csv(period: str | None = None):
    return ledger.qbo_gl_csv(S().db, period)


@app.get("/api/export/beancount", response_class=PlainTextResponse)
def bean():
    return ledger.to_beancount(S().db)


@app.post("/api/closepack")
def make_closepack():
    s = S()
    return closepack.build(s.db, s.world, s.seed)


@app.get("/api/closepack.zip")
def closepack_zip():
    s = S()
    out = closepack.build(s.db, s.world, s.seed)
    return FileResponse(out["zip"], filename=f"afterglow_close_pack_{config.CLOSE_PERIOD}.zip")


# ------------------------------------------------------------------ actions
@app.post("/api/connect")
def connect():
    return background("connect", S().connect)


@app.post("/api/onboard")
def onboard():
    return background("onboard", S().onboard)


@app.post("/api/close")
def close():
    return background("close", S().run_close)


@app.post("/api/october")
def october():
    return background("october", S().october)


@app.post("/api/resync")
def resync():
    return S().resync()


@app.post("/api/controller/run")
def controller_run():
    return background("controller", lambda: personas.auto_controller(S().engine))


@app.post("/api/controller/auto")
def controller_auto(on: bool = Body(..., embed=True)):
    STATE["auto_controller"] = on
    return {"auto_controller": on}


@app.post("/api/speed")
def speed(value: float = Body(..., embed=True)):
    STATE["speed"] = value
    S().ctx.speed = value
    return {"speed": value}


def _safe(fn, *a):
    try:
        return fn(*a)
    except Denied as e:
        return JSONResponse({"denied": True, "reason": e.reason}, status_code=403)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/api/item/{item_id}/approve")
def approve(item_id: str, body: dict = Body(default={})):
    r = _safe(S().approve, item_id, body.get("who", "maya"), body.get("reason", "Approved"))
    events.publish("refresh")
    return r if isinstance(r, JSONResponse) else item_out(r)


@app.post("/api/item/{item_id}/reject")
def reject(item_id: str, body: dict = Body(...)):
    r = _safe(S().reject, item_id, body["reason"])
    events.publish("refresh")
    return r if isinstance(r, JSONResponse) else (item_out(r) if r else {})


@app.post("/api/item/{item_id}/answer")
def answer(item_id: str, body: dict = Body(...)):
    r = _safe(S().answer, item_id, body["text"])
    events.publish("refresh")
    return r if isinstance(r, JSONResponse) else item_out(r)


@app.post("/api/item/{item_id}/challenge")
def challenge(item_id: str, body: dict = Body(...)):
    return S().challenge(item_id, body["question"])


@app.post("/api/item/{item_id}/self-approve")
def self_approve(item_id: str):
    r = _safe(S().try_self_approve, item_id)
    events.publish("refresh")
    return r if isinstance(r, JSONResponse) else r


@app.post("/api/policy/{policy_id}/{version}/{decision}")
def policy_decide(policy_id: str, version: int, decision: str):
    r = _safe(S().decide_policy, policy_id, version, decision)
    events.publish("refresh")
    return r


@app.post("/api/inject")
def inject(body: dict = Body(...)):
    from jarvis.work.transition import append_audit, log as audit_log
    from jarvis.work.roles import actor
    holder = {}
    SYNC = actor("sync")

    def run():
        try:
            holder["r"] = S().inject(text=body.get("text"), template=body.get("template"), params=body.get("params"))
            # Success already logged in injector.inject()
            events.publish("inject_done", result=holder["r"])
        except Exception as e:
            # Log injection failure to audit log
            reason = f"Injection failed: {type(e).__name__}: {str(e)[:200]}"
            with S().db.tx():
                append_audit(S().db, SYNC, "inject_failed", f"scenario:{body.get('template') or 'parse'}", 
                           False, reason, {"error": str(e)[:400], "traceback": traceback.format_exc()[-800:]})
            holder["r"] = {"success": False, "error": str(e), "template": body.get("template")}
            events.publish("inject_done", result=holder["r"])
    return background("inject", run)


@app.post("/api/fault")
def fault(body: dict = Body(...)):
    return S().set_fault(body.get("mode"))


@app.post("/api/reset")
def reset(body: dict = Body(default={})):
    if STATE["busy"]:
        raise HTTPException(409, "busy")
    seed = int(body.get("seed", S().seed))
    events.reset()
    STATE["session"] = Session(seed, fresh=True, speed=STATE["speed"])
    events.publish("refresh")
    return {"reset": True, "seed": seed}


# ------------------------------------------------------------------ mock PayPal API (with fault injection)
@app.get("/mock/paypal/v1/reporting/transactions")
def mock_paypal(month: str = "2026-09"):
    try:
        rows = sync.PayPalAPI(S().world).fetch(month)
    except ConnectionError as e:
        code = 429 if "429" in str(e) else 503
        return JSONResponse({"name": "SERVICE_UNAVAILABLE", "message": str(e)}, status_code=code)
    return {"transaction_details": rows, "total_items": len(rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=config.world_seed())
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--fresh", action="store_true")
    a = ap.parse_args()
    STATE["session"] = Session(a.seed, fresh=a.fresh, speed=STATE["speed"])
    uvicorn.run(app, host=a.host, port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
