"""Workbench runtime: a Run moves through named stages; every step is logged, hash-chained and streamed.

Transparency contract (what the judges see for every run):
  * each stage logs start, every action it takes, every row it changes (before -> after), its counts and its end
  * every log line is an audit row in the same append-only, hash-chained log as the rest of the system
  * outputs are artifacts (tables, diffs, file trees, journal entries) attached to the stage that made them
  * anything that changes a system of record becomes a proposal (work item) that a human approves; only the
    Gateway applies it, and that is logged too
"""
from __future__ import annotations

import json
import shutil
import threading
import time
import traceback
import uuid
from contextlib import contextmanager
from pathlib import Path

from jarvis import config
from jarvis.work import events, gateway
from jarvis.work.db import DB, J
from jarvis.work.roles import actor
from jarvis.work.transition import (Denied, append_audit, create_item, get_item, now, transition, verify_chain, why)

JARVIS, SYNC, MAYA, GATEWAY = actor("jarvis"), actor("sync"), actor("maya"), actor("gateway")
DATA = config.ROOT / "data" / "workbench"
OUT = config.RUNTIME_DIR / "workbench"

LEVELS = {"info", "fix", "find", "warn", "decide", "ask", "ok", "deny", "sim", "check", "fail"}


class Run:
    def __init__(self, wb: "Workbench", problem: str, title: str, stages: list[tuple[str, str]], instructions: str = ""):
        self.wb, self.problem, self.title, self.instructions = wb, problem, title, instructions
        self.id = f"RUN-{problem.split('_')[0].upper()}-{uuid.uuid4().hex[:6].upper()}"
        self.stages = [{"key": k, "title": t, "status": "pending", "started": None, "ended": None, "summary": "",
                        "counts": {}, "logs": 0} for k, t in stages]
        self.logs: list[dict] = []
        self.artifacts: dict[str, dict] = {}
        self.proposals: list[str] = []
        self.status = "queued"
        self.cur: str | None = None
        self.started = now()
        self.data_dir = DATA / problem
        self.out_dir = OUT / self.id
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.ctx: dict = {}
        self.moments: list[dict] = []      # the "moment" pillar: caught / recovered / asked / defended
        self.proof: dict | None = None     # answer-key scorecard vs a naive baseline

    # ---------------------------------------------------------------- logging
    def _stage(self, key: str) -> dict:
        return next(s for s in self.stages if s["key"] == key)

    def moment(self, kind: str, level: str, msg: str, data=None, **kw):
        """A log line that is also one of the run's moments (caught what others miss, recovered, asked, defended)."""
        e = self.log(level, msg, data, moment=kind, **kw)
        self.moments.append({"kind": kind, "seq": e["seq"], "stage": e["stage"], "msg": msg})
        return e

    def log(self, level: str, msg: str, data=None, evidence: list | None = None, pause: float = 1.0, moment: str | None = None):
        assert level in LEVELS, level
        entry = {"seq": len(self.logs) + 1, "t": now(), "stage": self.cur, "level": level, "msg": msg, "data": data,
                 "moment": moment}
        with self.wb.db.tx():
            row = append_audit(self.wb.db, JARVIS if level != "sim" else SYNC, f"{self.problem}:{self.cur}:{level}",
                               self.id, True, msg[:400], {"data": data} if data is not None else {}, evidence or [],
                               publish=False)
        entry["audit_seq"], entry["hash"] = row["seq"], row["hash"]
        self.logs.append(entry)
        if self.cur:
            self._stage(self.cur)["logs"] += 1
        events.publish("wb", run_id=self.id, problem=self.problem, kind="log", entry=entry)
        if self.wb.speed:
            time.sleep(self.wb.speed * pause)
        return entry

    def artifact(self, kind: str, title: str, payload, aid: str | None = None) -> str:
        aid = aid or f"A{len(self.artifacts) + 1:02d}"
        self.artifacts[aid] = {"id": aid, "kind": kind, "title": title, "stage": self.cur, "payload": payload}
        events.publish("wb", run_id=self.id, problem=self.problem, kind="artifact", artifact={"id": aid, "kind": kind,
                                                                                               "title": title, "stage": self.cur})
        return aid

    def count(self, **kw):
        self._stage(self.cur)["counts"].update(kw)
        events.publish("wb", run_id=self.id, problem=self.problem, kind="stage", stage=self._stage(self.cur))

    @contextmanager
    def stage(self, key: str, summary: str = ""):
        st = self._stage(key)
        self.cur = key
        st["status"], st["started"] = "running", now()
        events.publish("wb", run_id=self.id, problem=self.problem, kind="stage", stage=st)
        self.log("info", f"▶ {st['title']}" + (f" — {summary}" if summary else ""), pause=0.5)
        t0 = time.time()
        try:
            yield st
            if st["status"] == "running":
                st["status"] = "done"
        except Exception as e:
            st["status"] = "failed"
            self.log("fail", f"Stage failed: {e}", {"trace": traceback.format_exc()[-800:]})
            raise
        finally:
            st["ended"] = now()
            st["seconds"] = round(time.time() - t0, 2)
            if st["status"] in ("done", "flag", "waiting"):
                self.log({"done": "ok", "flag": "warn", "waiting": "ask"}[st["status"]],
                         f"■ {st['title']} {'complete' if st['status'] == 'done' else st['status']}"
                         + (f" — {st['summary']}" if st["summary"] else ""), st["counts"] or None, pause=0.6)
            events.publish("wb", run_id=self.id, problem=self.problem, kind="stage", stage=st)

    def flag(self, summary: str):
        st = self._stage(self.cur)
        st["status"] = "flag"
        st["summary"] = summary

    def done(self, summary: str):
        self._stage(self.cur)["summary"] = summary

    # ---------------------------------------------------------------- proposals (system-of-record changes)
    def propose(self, kind: str, title: str, proposal: dict, rationale: str, evidence: list, confidence: float = 0.9,
                escalate: bool = False, question: str = "") -> str:
        # Apply materiality: amounts above threshold require higher scrutiny
        from jarvis.world import bible
        from jarvis.money import fmt
        materiality_cents = bible.APPROVAL_MATRIX.get("materiality_cents", 50000)
        # Sum debits only (positive cents) to avoid double-counting in double-entry
        total_cents = sum(line.get("cents", 0) for line in proposal.get("lines", []) if line.get("cents", 0) > 0)
        if total_cents >= materiality_cents:
            self.log("decide", f"Amount {fmt(total_cents)} exceeds materiality threshold {fmt(materiality_cents)} "
                         f"— requires manual review")
        
        anchor = f"{self.id}:{kind}:{len(self.proposals) + 1}"
        it = create_item(self.wb.db, SYNC, kind, anchor, title, "2026-09", [self.id])
        patch = {"kind": kind, "proposal": {"kind": kind, **proposal, "escalate": escalate, "run_id": self.id},
                 "evidence": evidence, "rationale": rationale, "confidence": confidence, "question": question}
        it = transition(self.wb.db, it["item_id"], "propose", JARVIS, patch, reason=rationale[:300])
        self.proposals.append(it["item_id"])
        self.log("decide", f"Proposed {kind}: {title} → waiting for Controller approval ({it['item_id']})",
                 {"item_id": it["item_id"], "lines": proposal.get("lines")})
        return it["item_id"]

    def summary(self, full: bool = False) -> dict:
        out = {"id": self.id, "problem": self.problem, "title": self.title, "status": self.status, "stages": self.stages,
               "started": self.started, "instructions": self.instructions,
               "proposals": [self._prop(i) for i in self.proposals],
               "artifacts": [{k: v for k, v in a.items() if k != "payload"} for a in self.artifacts.values()],
               "moments": self.moments, "proof": self.proof, "agent": getattr(self, "agent", self.problem)}
        if full:
            out["logs"] = self.logs
        return out

    def _prop(self, item_id: str) -> dict:
        it = get_item(self.wb.db, item_id)
        return {k: it[k] for k in ("item_id", "kind", "state", "title", "rationale", "confidence", "proposal", "evidence",
                                   "approved_by", "question", "answer")}


class Workbench:
    """Holds the workbench DB and active runs; agents register here."""

    def __init__(self, fresh: bool = False, speed: float = 0.15):
        path = OUT / "work.db"
        if fresh and OUT.exists():
            shutil.rmtree(OUT)
        OUT.mkdir(parents=True, exist_ok=True)
        self.db = DB(path)
        self.speed = speed
        self.runs: dict[str, Run] = {}
        self.lock = threading.Lock()
        if not (DATA / "p1_timing").exists():
            from jarvis.workbench import datagen
            datagen.generate()
        from jarvis.workbench import agents
        self.agents = agents.REGISTRY

    def start(self, problem: str, instructions: str = "", **opts) -> Run:
        spec = self.agents[problem]
        run = Run(self, spec.get("data", problem), spec["title"], spec["stages"], instructions)
        run.agent = problem
        self.runs[run.id] = run

        def go():
            run.status = "running"
            events.publish("wb", run_id=run.id, problem=problem, kind="status", status="running")
            try:
                spec["run"](run, **opts)
                from jarvis.workbench import proof
                proof.score(run)
                run.status = "awaiting_approval" if any(get_item(self.db, p)["state"] == "PROPOSED" for p in run.proposals) \
                    else "done"
            except Exception as e:  # noqa
                run.status = "failed"
                traceback.print_exc()
            events.publish("wb", run_id=run.id, problem=problem, kind="status", status=run.status)
        threading.Thread(target=go, daemon=True).start()
        return run

    # ---------------------------------------------------------------- approvals -> gateway
    def decide(self, item_id: str, decision: str, reason: str = "", who: str = "maya") -> dict:
        from jarvis.work.gateway import ValidationError
        
        it = get_item(self.db, item_id)
        run = self.runs.get(it["proposal"].get("run_id"))
        if decision == "approve":
            transition(self.db, item_id, "approve", actor(who), {"answer": reason} if reason else None,
                       reason=reason or "Approved")
            try:
                res = self.apply(item_id, run)
            except ValidationError as e:
                # Gateway validation failed - entry doesn't balance or violates rules
                raise ValidationError(f"Entry validation failed: {str(e)}")
        else:
            transition(self.db, item_id, "reject", actor(who), {"answer": reason}, reason=reason or "Rejected")
            res = {"rejected": True}
            if run:
                run.cur = run.stages[-1]["key"]
                run.log("deny", f"Controller rejected {it['title']}: {reason}")
                spec = self.agents[run.agent]
                if spec.get("on_reject"):
                    spec["on_reject"](run, it, reason)
        if run:
            pending = [p for p in run.proposals if get_item(self.db, p)["state"] == "PROPOSED"]
            if not pending:
                run.status = "done"
                last = run.stages[-1]
                last["status"] = "done"
                last["summary"] = f"{len([p for p in run.proposals if get_item(self.db, p)['state'] == 'POSTED'])} applied by Gateway"
                events.publish("wb", run_id=run.id, problem=run.problem, kind="stage", stage=last)
            events.publish("wb", run_id=run.id, problem=run.problem, kind="status", status=run.status)
        return res

    def challenge(self, item_id: str, question: str, who: str = "maya") -> dict:
        """The Controller questions a proposal; the agent defends it from its own evidence (and logs every point)."""
        from jarvis.workbench import defend
        it = get_item(self.db, item_id)
        run = self.runs.get(it["proposal"].get("run_id"))
        with self.db.tx():
            append_audit(self.db, actor(who), "challenge", item_id, True, question[:400], {}, [], publish=False)
        return defend.defend(run, it, question)

    def apply(self, item_id: str, run: Run | None) -> dict:
        it = get_item(self.db, item_id)
        kind = it["kind"]
        if run:
            run.cur = run.stages[-1]["key"]
            st = run.stages[-1]
            st["status"] = "running"
            events.publish("wb", run_id=run.id, problem=run.problem, kind="stage", stage=st)
        if it["proposal"].get("lines"):
            res = gateway.post(self.db, item_id)
            entry = self.db.one("SELECT entry_id FROM ledger_entries WHERE work_item_id=?", (item_id,))
            msg = f"Gateway posted {kind} as ledger entry {entry['entry_id'] if entry else '?'} (balanced, period open)"
        else:
            applier = self.agents[run.agent].get("apply") if run else None
            detail = applier(run, it) if applier else "applied"
            with self.db.tx():
                self.db.conn.execute("UPDATE work_items SET state='POSTED', updated_at=? WHERE item_id=?", (now(), item_id))
                append_audit(self.db, GATEWAY, "post", item_id, True, f"Gateway applied {kind}: {detail}",
                             {"state": ["APPROVED", "POSTED"]}, [run.id] if run else [])
            events.publish("item", item_id=item_id, state="POSTED")
            msg = f"Gateway applied {kind}: {detail}"
        if run:
            run.log("ok", msg, {"item_id": item_id})
        return {"item_id": item_id, "state": "POSTED", "message": msg}

    def verify(self) -> dict:
        return verify_chain(self.db)

    def audit_for(self, run_id: str) -> list[dict]:
        rows = self.db.q("SELECT seq, at, actor, actor_role, action, subject, allowed, reason, hash, prev_hash FROM audit_log "
                         "WHERE subject=? OR subject IN (SELECT item_id FROM work_items WHERE anchor LIKE ?) ORDER BY seq",
                         (run_id, f"{run_id}:%"))
        return rows
