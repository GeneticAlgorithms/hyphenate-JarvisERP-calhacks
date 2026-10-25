"""Work-item state machine + the append-only, hash-chained audit log.

    NEW --propose--> PROPOSED --approve--> APPROVED --post(gateway)--> POSTED
     |                 |  ^ revise
     |                 +--ask--> NEEDS_INFO --answer--> NEW (agent re-plans with the answer)
     +--ask--> NEEDS_INFO          PROPOSED --reject--> REJECTED (becomes a precedent; agent re-plans as a new item)
     +--dismiss--> DISMISSED (agent found nothing to do, with a reason)
                       PROPOSED --withdraw--> DISMISSED (agent supersedes its own stale proposal)

Every transition - allowed or denied - writes one audit row in the SAME transaction as the change.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone

from jarvis.work import events
from jarvis.work.db import DB, J, L
from jarvis.work.roles import Actor, can

TRANSITIONS = {
    (None, "create"): "NEW",
    ("NEW", "propose"): "PROPOSED",
    ("NEW", "ask"): "NEEDS_INFO",
    ("NEW", "dismiss"): "DISMISSED",
    ("PROPOSED", "ask"): "NEEDS_INFO",
    ("PROPOSED", "revise"): "PROPOSED",
    ("PROPOSED", "review"): "PROPOSED",
    ("PROPOSED", "approve"): "APPROVED",
    ("PROPOSED", "reject"): "REJECTED",
    ("PROPOSED", "withdraw"): "DISMISSED",   # agent supersedes its own stale proposal (e.g. package v1 after a late QBO change)
    ("NEEDS_INFO", "answer"): "NEW",
    ("NEEDS_INFO", "propose"): "PROPOSED",   # agent proposes while still waiting (e.g. accrue AND chase vendor)
    ("APPROVED", "post"): "POSTED",
}

ITEM_FIELDS = ["kind", "anchor", "state", "title", "period", "source_refs", "proposal", "evidence", "policy_id",
               "precedent_ids", "confidence", "rationale", "question", "answer", "review", "proposed_by",
               "approved_by", "parent_id"]
JSON_FIELDS = {"source_refs", "proposal", "evidence", "precedent_ids", "review"}


class Denied(Exception):
    def __init__(self, action, subject, reason):
        super().__init__(f"DENIED {action} on {subject}: {reason}")
        self.action, self.subject, self.reason = action, subject, reason


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ------------------------------------------------------------------ audit
def _hash(prev: str, row: dict) -> str:
    return hashlib.sha256((prev + json.dumps(row, sort_keys=True, default=str)).encode()).hexdigest()


def append_audit(db: DB, actor: Actor, action: str, subject: str, allowed: bool, reason: str = "",
                 diff: dict | None = None, evidence: list | None = None, publish: bool = True) -> dict:
    """Must be called inside db.tx() when paired with a change; also usable standalone for reads/tool calls."""
    last = db.conn.execute("SELECT hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
    prev = last[0] if last else "GENESIS"
    row = {"at": now(), "actor": actor.id, "actor_role": actor.role, "action": action, "subject": subject,
           "allowed": 1 if allowed else 0, "reason": reason, "diff": J(diff or {}), "evidence": J(evidence or [])}
    row["prev_hash"] = prev
    row["hash"] = _hash(prev, row)
    cur = db.conn.execute(
        "INSERT INTO audit_log(at,actor,actor_role,action,subject,allowed,reason,diff,evidence,prev_hash,hash) "
        "VALUES(:at,:actor,:actor_role,:action,:subject,:allowed,:reason,:diff,:evidence,:prev_hash,:hash)", row)
    row["seq"] = cur.lastrowid
    if publish:
        events.publish("audit", seq=row["seq"], actor=actor.id, role=actor.role, action=action, subject=subject,
                       allowed=bool(allowed), reason=reason, evidence=evidence or [], diff=diff or {})
    return row


def log(db: DB, actor: Actor, action: str, subject: str, reason: str = "", evidence: list | None = None,
        diff: dict | None = None) -> dict:
    """Standalone audit event (tool calls, syncs, messages)."""
    with db.tx():
        return append_audit(db, actor, action, subject, True, reason, diff, evidence)


def verify_chain(db: DB) -> dict:
    rows = db.q("SELECT * FROM audit_log ORDER BY seq")
    prev = "GENESIS"
    for r in rows:
        body = {k: r[k] for k in ("at", "actor", "actor_role", "action", "subject", "allowed", "reason", "diff",
                                  "evidence")}
        body["prev_hash"] = prev
        h = _hash(prev, body)
        if r["prev_hash"] != prev or r["hash"] != h:
            return {"ok": False, "broken_at": r["seq"], "rows": len(rows)}
        prev = r["hash"]
    return {"ok": True, "rows": len(rows), "head": prev}


# ------------------------------------------------------------------ items
def get_item(db: DB, item_id: str) -> dict | None:
    r = db.one("SELECT * FROM work_items WHERE item_id=?", (item_id,))
    if not r:
        return None
    for f in JSON_FIELDS:
        r[f] = L(r[f], [] if f in ("source_refs", "evidence", "precedent_ids") else {})
    return r


def item_by_anchor(db: DB, anchor: str, live_only: bool = True) -> dict | None:
    sql = "SELECT item_id FROM work_items WHERE anchor=?"
    if live_only:
        sql += " AND state NOT IN ('REJECTED')"
    sql += " ORDER BY created_at DESC LIMIT 1"
    r = db.one(sql, (anchor,))
    return get_item(db, r["item_id"]) if r else None


def _snapshot(item: dict | None) -> dict:
    if not item:
        return {}
    return {k: item.get(k) for k in ITEM_FIELDS}


def _diff(before: dict, after: dict) -> dict:
    out = {}
    for k in ITEM_FIELDS:
        b, a = before.get(k), after.get(k)
        if b != a:
            out[k] = [b, a]
    return out


def create_item(db: DB, actor: Actor, kind: str, anchor: str, title: str, period: str, source_refs: list,
                evidence: list | None = None, parent_id: str | None = None) -> dict:
    existing = item_by_anchor(db, anchor)
    if existing:
        return existing  # idempotent: re-sync never duplicates work
    ok, why = can(actor, "create", "work_item")
    item = {"item_id": f"WI-{uuid.uuid4().hex[:8].upper()}", "kind": kind, "anchor": anchor, "state": "NEW",
            "title": title, "period": period, "source_refs": source_refs, "proposal": {}, "evidence": evidence or [],
            "policy_id": None, "precedent_ids": [], "confidence": None, "rationale": "", "question": "",
            "answer": "", "review": {}, "proposed_by": None, "approved_by": None, "parent_id": parent_id}
    with db.tx():
        if not ok:
            append_audit(db, actor, "create", anchor, False, why)
        else:
            ts = now()
            db.conn.execute(
                "INSERT INTO work_items(item_id,kind,anchor,state,title,period,source_refs,proposal,evidence,policy_id,"
                "precedent_ids,confidence,rationale,question,answer,review,proposed_by,approved_by,parent_id,created_at,"
                "updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (item["item_id"], kind, anchor, "NEW", title, period, J(source_refs), J({}), J(evidence or []), None,
                 J([]), None, "", "", "", J({}), None, None, parent_id, ts, ts))
            append_audit(db, actor, "create", item["item_id"], True, f"{kind}: {title}",
                         {"state": [None, "NEW"], "anchor": [None, anchor]}, source_refs)
    if not ok:
        raise Denied("create", anchor, why)
    events.publish("item", item_id=item["item_id"], state="NEW", kind=kind, title=title, anchor=anchor)
    return get_item(db, item["item_id"])


def transition(db: DB, item_id: str, action: str, actor: Actor, patch: dict | None = None, reason: str = "",
               evidence: list | None = None) -> dict:
    item = get_item(db, item_id)
    if item is None:
        raise KeyError(item_id)
    to = TRANSITIONS.get((item["state"], action))
    ok, why = (False, f"no transition '{action}' from state {item['state']}") if to is None else \
        can(actor, action, "work_item", item)
    before = _snapshot(item)
    after = dict(item)
    if ok:
        after.update(patch or {})
        after["state"] = to
        if action == "propose" or action == "revise":
            after["proposed_by"] = actor.id
        if action == "approve":
            after["approved_by"] = actor.id
    with db.tx():
        if ok:
            sets = ", ".join(f"{k}=?" for k in ITEM_FIELDS) + ", updated_at=?"
            vals = [J(after[k]) if k in JSON_FIELDS else after[k] for k in ITEM_FIELDS] + [now(), item_id]
            db.conn.execute(f"UPDATE work_items SET {sets} WHERE item_id=?", vals)
        append_audit(db, actor, action, item_id, ok, reason if ok else why,
                     _diff(before, after) if ok else {}, evidence or item.get("source_refs"))
    if not ok:
        events.publish("denied", item_id=item_id, actor=actor.id, action=action, reason=why)
        raise Denied(action, item_id, why)
    events.publish("item", item_id=item_id, state=to, kind=item["kind"], title=item["title"], anchor=item["anchor"],
                   action=action, actor=actor.id)
    return get_item(db, item_id)


def why(db: DB, subject: str) -> list[dict]:
    """'Months later, why? is one query.'"""
    return db.q("SELECT seq, at, actor, actor_role, action, allowed, reason, diff, evidence FROM audit_log "
                "WHERE subject=? ORDER BY seq", (subject,))


def _sleep(s: float):
    time.sleep(s)
