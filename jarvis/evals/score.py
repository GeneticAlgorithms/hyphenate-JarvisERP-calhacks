"""Score a finished run against the answer key (the agent never sees the key)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from jarvis.work.db import DB, L

KIND_EQUIV = {
    "match": {"match"}, "bill_payment": {"bill_payment"}, "card_statement_payment": {"card_statement_payment"},
    "receivable_receipt": {"receivable_receipt"}, "bank_fee": {"bank_fee"}, "paypal_split": {"paypal_split"},
    "transfer": {"transfer"}, "paypal_payment": {"paypal_payment"}, "reclass": {"reclass"}, "duplicate": {"duplicate"},
    "vendor_link": {"vendor_link"}, "vendor_create": {"vendor_create"}, "accrual": {"accrual"},
    "accrual_reversal": {"accrual_reversal"}, "ask": {"unknown", "aging", "answered"},
}


def _norm_lines(lines) -> Counter:
    c = Counter()
    for l in lines or []:
        acct, cents = (l["acct"], l["cents"]) if isinstance(l, dict) else (l[0], l[1])
        c[acct] += cents
    return Counter({k: v for k, v in c.items() if v})


def outcomes(db: DB) -> dict[str, dict]:
    """First item per anchor (what Jarvis did on its own, before any human correction)."""
    out = {}
    for r in db.q("SELECT * FROM work_items ORDER BY created_at"):
        if r["anchor"] in out:
            out[r["anchor"]]["later"].append(r["item_id"])
            continue
        prop = L(r["proposal"], {}) or {}
        asked = db.one("SELECT 1 FROM audit_log WHERE subject=? AND action='ask' AND allowed=1", (r["item_id"],))
        out[r["anchor"]] = {"item_id": r["item_id"], "kind": r["kind"], "state": r["state"], "lines": prop.get("lines", []),
                            "vendor": prop.get("vendor"), "escalated": bool(asked) or bool(prop.get("escalate")),
                            "later": []}
    return out


def score(answer_key: Path, got: dict[str, dict], phases=("close", "october")) -> dict:
    key = json.loads(Path(answer_key).read_text())
    rows = []
    for k in key["items"]:
        if k["phase"] not in phases:
            continue
        exp = k["expected"]
        o = got.get(k["anchor"])
        trap = exp["kind"] == "no_action"
        res = {"key_id": k["key_id"], "anchor": k["anchor"], "category": k["category"], "expected": exp["kind"],
               "got": (o or {}).get("kind", "-"), "trap": trap}
        if trap:
            ok = o is None or o["state"] == "DISMISSED"
            res.update(detected=ok, treatment=ok, escalation=ok if not (o and o["escalated"]) else False,
                       ok=ok and not (o and o["escalated"]))
        else:
            detected = o is not None and (o["state"] != "DISMISSED" or exp["kind"] == "ask")
            kind_ok = detected and o["kind"] in KIND_EQUIV.get(exp["kind"], {exp["kind"]})
            if exp["kind"] in ("vendor_link", "vendor_create"):
                v = (o or {}).get("vendor") or {}
                treat = kind_ok and (v.get("vendor_id") == exp.get("vendor_id") if exp["kind"] == "vendor_link" else
                                     v.get("action") == "create")
            elif exp["kind"] == "ask":
                treat = detected and o["escalated"]
            elif exp["kind"] == "match":
                treat = kind_ok
            else:
                treat = kind_ok and _norm_lines(o["lines"]) == _norm_lines(exp.get("lines"))
            esc_ok = detected and (o["escalated"] == bool(exp.get("escalate")))
            res.update(detected=detected, treatment=bool(treat), escalation=bool(esc_ok),
                       ok=bool(detected and treat and esc_ok))
            if detected and not treat:
                res["detail"] = {"got_lines": dict(_norm_lines(o["lines"])), "exp_lines": dict(_norm_lines(exp.get("lines")))}
        rows.append(res)
    real = [r for r in rows if not r["trap"]]
    traps = [r for r in rows if r["trap"]]
    esc_items = [r for r in rows if not r["trap"]]
    summary = {
        "items": len(rows), "issues": len(real), "traps": len(traps),
        "detection_recall": round(sum(r["detected"] for r in real) / max(1, len(real)), 3),
        "treatment_accuracy": round(sum(r["treatment"] for r in real) / max(1, len(real)), 3),
        "trap_precision": round(sum(r["ok"] for r in traps) / max(1, len(traps)), 3),
        "escalation_correct": round(sum(r["escalation"] for r in esc_items) / max(1, len(esc_items)), 3),
        "fully_correct": round(sum(r["ok"] for r in rows) / max(1, len(rows)), 3),
    }
    return {"summary": summary, "rows": rows}
