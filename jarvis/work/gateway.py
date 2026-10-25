"""The Gateway: one door to the systems of record. Every write is checked.

Only actor 'gateway' may post, and only APPROVED items. It validates the proposal
(deterministic checks - the LLM is never trusted with arithmetic), writes ledger / vendor
master / reconciliation links, marks the item POSTED and logs the diff - all in one transaction.
"""
from __future__ import annotations

import uuid

from jarvis import config
from jarvis.work import events
from jarvis.work.db import DB, J
from jarvis.work.roles import actor
from jarvis.work.transition import Denied, append_audit, get_item, now, transition
from jarvis.world import bible

GATEWAY = actor("gateway")


class ValidationError(Exception):
    pass


def validate(db: DB, item: dict) -> list[str]:
    p = item.get("proposal") or {}
    errs: list[str] = []
    lines = p.get("lines", [])
    if lines:
        total = sum(l["cents"] for l in lines)
        if total != 0:
            errs.append(f"debits != credits (off by {total} cents)")
        for l in lines:
            if l["acct"] not in bible.COA:
                errs.append(f"unknown account {l['acct']}")
            if not isinstance(l["cents"], int):
                errs.append("amounts must be integer cents")
        d = p.get("date", "")
        if not d or d[:7] <= config.LOCKED_THROUGH:
            errs.append(f"entry date {d} falls in a locked period (<= {config.LOCKED_THROUGH})")
    for rid in p.get("reconcile", []):
        r = db.one("SELECT entry_id, work_item_id FROM reconciliation WHERE record_id=?", (rid,))
        if r and r["work_item_id"] != item["item_id"]:
            errs.append(f"record {rid} already reconciled by {r['work_item_id']}")
    for eid in p.get("match_entries", []):
        if not db.one("SELECT 1 FROM ledger_entries WHERE entry_id=?", (eid,)):
            errs.append(f"matched entry {eid} does not exist")
    for b in p.get("bill_updates", []):
        if not db.one("SELECT 1 FROM bills WHERE bill_id=?", (b["bill_id"],)):
            errs.append(f"unknown bill {b['bill_id']}")
    v = p.get("vendor")
    if v:
        if v.get("action") == "link" and not db.one("SELECT 1 FROM vendors WHERE vendor_id=?", (v["vendor_id"],)):
            errs.append(f"vendor {v.get('vendor_id')} not in vendor master")
        if db.one("SELECT 1 FROM vendor_aliases WHERE alias=? AND status='active'", (v.get("alias"),)):
            errs.append(f"alias {v.get('alias')} already resolved")
    return errs


def post(db: DB, item_id: str) -> dict:
    item = get_item(db, item_id)
    if item is None:
        raise KeyError(item_id)
    if item["state"] != "APPROVED":
        with db.tx():
            append_audit(db, GATEWAY, "post", item_id, False, f"item is {item['state']}, not APPROVED")
        raise Denied("post", item_id, f"item is {item['state']}, not APPROVED")
    errs = validate(db, item)
    if errs:
        with db.tx():
            append_audit(db, GATEWAY, "post", item_id, False, "validation failed: " + "; ".join(errs))
        events.publish("denied", item_id=item_id, actor="gateway", action="post", reason="; ".join(errs))
        raise ValidationError("; ".join(errs))

    p = item["proposal"]
    entry_id = None
    with db.tx():
        ts = now()
        if p.get("lines"):
            entry_id = f"JX-{uuid.uuid4().hex[:8].upper()}"
            db.conn.execute(
                "INSERT INTO ledger_entries(entry_id,date,period,memo,name,txn_type,num,source,refs,work_item_id,"
                "posted_by,posted_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (entry_id, p["date"], p["date"][:7], p.get("memo", item["title"]), p.get("name", ""),
                 p.get("txn_type", "Journal Entry"), p.get("num", ""), "jarvis", J({"anchor": item["anchor"]}),
                 item_id, "gateway", ts))
            for i, l in enumerate(p["lines"]):
                db.conn.execute("INSERT INTO ledger_lines(entry_id,line_no,account,amount_cents,memo,vendor_id) "
                                "VALUES(?,?,?,?,?,?)", (entry_id, i, l["acct"], l["cents"], l.get("memo", ""),
                                                        l.get("vendor_id")))
        link_entry = entry_id or (p.get("match_entries") or [None])[0]
        for rid in p.get("reconcile", []):
            db.conn.execute("INSERT OR REPLACE INTO reconciliation(record_id,entry_id,work_item_id,at) VALUES(?,?,?,?)",
                            (rid, link_entry, item_id, ts))
        for b in p.get("bill_updates", []):
            db.conn.execute("UPDATE bills SET status=? WHERE bill_id=?", (b["status"], b["bill_id"]))
        v = p.get("vendor")
        if v:
            if v["action"] == "create":
                nv = v["new"]
                db.conn.execute("INSERT OR IGNORE INTO vendors(vendor_id,qbo_name,legal,domain,default_acct,products,"
                                "tin,status,created_by) VALUES(?,?,?,?,?,?,?,?,?)",
                                (nv["vendor_id"], nv["qbo_name"], nv["legal"], nv.get("domain", ""),
                                 nv.get("default_acct", ""), J([]), nv.get("tin", ""), "active", item_id))
                vid = nv["vendor_id"]
            else:
                vid = v["vendor_id"]
            db.conn.execute("INSERT OR REPLACE INTO vendor_aliases(alias,vendor_id,source,status,work_item_id,at) "
                            "VALUES(?,?,?,?,?,?)", (v["alias"], vid, v.get("source", ""), "active", item_id, ts))
        # state change + audit in the same transaction
        db.conn.execute("UPDATE work_items SET state='POSTED', updated_at=? WHERE item_id=?", (ts, item_id))
        append_audit(db, GATEWAY, "post", item_id, True,
                     f"posted {entry_id or 'no-JE'}" + (f" reconciled {len(p.get('reconcile', []))}" if p.get('reconcile') else ""),
                     {"state": ["APPROVED", "POSTED"], "ledger_entry": [None, entry_id]},
                     item.get("source_refs"))
    events.publish("item", item_id=item_id, state="POSTED", kind=item["kind"], title=item["title"],
                   anchor=item["anchor"], action="post", actor="gateway", entry_id=entry_id)
    events.publish("ledger", entry_id=entry_id, item_id=item_id)
    return get_item(db, item_id)


def approve_and_post(db: DB, item_id: str, approver_id: str, reason: str) -> dict:
    transition(db, item_id, "approve", actor(approver_id), reason=reason)
    return post(db, item_id)
