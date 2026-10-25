"""Build the Synapse Trace: a layered evidence graph of everything Jarvis touched.

Layers (left -> right):  0 systems & people  ·  1 source records & documents  ·  2 policies, precedents,
vendors, FX  ·  3 work items (decisions)  ·  4 ledger entries / vendor master / messages (outcomes)
"""
from __future__ import annotations

from jarvis.money import fmt
from jarvis.work.db import DB, L

SYSTEMS = {"bank": "Chase x4471", "paypal": "PayPal", "ramp": "Ramp", "docs": "Drive / Email", "qbo": "Ledger (QBO)",
           "injector": "Scenario injector"}
PEOPLE = {"maya": "Maya Chen · Controller", "jarvis": "Jarvis · preparer", "jarvis-reviewer": "Jarvis · reviewer",
          "policy:P-001": "Standing policy P-001", "gateway": "Gateway"}


def build(db: DB) -> dict:
    nodes: dict[str, dict] = {}
    links: list[dict] = []

    def node(nid, label, layer, group, **kw):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "label": label, "layer": layer, "group": group, **kw}
        else:
            nodes[nid].update({k: v for k, v in kw.items() if v is not None})
        return nid

    def link(a, b, rel="supports", **kw):
        if a in nodes and b in nodes:
            links.append({"source": a, "target": b, "rel": rel, **kw})

    for k, v in SYSTEMS.items():
        node(f"sys:{k}", v, 0, "system")
    for k, v in PEOPLE.items():
        node(f"actor:{k}", v, 0 if k == "maya" else 4 if k == "gateway" else 3, "actor")

    items = db.q("SELECT * FROM work_items ORDER BY created_at")
    for it in items:
        prop = L(it["proposal"], {}) or {}
        amt = sum(l["cents"] for l in prop.get("lines", []) if l["cents"] > 0)
        node(it["item_id"], it["title"], 3, "item", state=it["state"], kind=it["kind"],
             amount=fmt(amt) if amt else "", confidence=it["confidence"])
        for e in L(it["evidence"], []) or []:
            t, i = e["type"], e["id"]
            if t == "record":
                r = db.one("SELECT source, txn_date, amount_cents, currency, description FROM records WHERE record_id=?", (i,))
                if not r:
                    continue
                nid = node(f"rec:{i}", f"{r['source']} {r['txn_date']} {fmt(r['amount_cents'], r['currency'])}", 1,
                           f"rec_{r['source']}", detail=r["description"][:120])
                node(f"sys:{r['source']}", SYSTEMS.get(r["source"], r["source"]), 0, "system")
                link(f"sys:{r['source']}", nid, "context")
            elif t == "doc":
                d = db.one("SELECT kind, title FROM docs WHERE doc_id=?", (i,))
                nid = node(f"doc:{i}", d["title"] if d else i, 1, "doc", detail=(d or {}).get("kind"))
                link("sys:docs", nid, "context")
            elif t == "precedent":
                p = db.one("SELECT summary, period FROM precedents WHERE prec_id=?", (i,))
                nid = node(f"prec:{i}", f"{i} ({(p or {}).get('period', '')})", 2, "precedent",
                           detail=(p or {}).get("summary", "")[:160])
            elif t == "vendor":
                v = db.one("SELECT qbo_name, legal FROM vendors WHERE vendor_id=?", (i,))
                nid = node(f"vendor:{i}", f"Vendor {(v or {}).get('qbo_name', i)}", 2, "vendor", detail=(v or {}).get("legal"))
            elif t == "fx":
                nid = node(f"fx:{i}", e["label"], 2, "fx")
            elif t == "person":
                nid = node(f"person:{i}", e["label"][:40], 0, "person")
            elif t == "ledger":
                nid = node(f"je:{i}", e["label"][:50], 4 if i.startswith("JX") else 2, "ledger_ref")
            elif t == "bill":
                nid = node(f"bill:{i}", e["label"][:50], 1, "bill")
                link("sys:qbo", nid, "context")
            else:
                continue
            link(nid, it["item_id"], e.get("relation", "supports"))
        for pref in (it["policy_id"] or "").split(", "):
            if pref:
                pid = pref.split(" ")[0]
                node(f"pol:{pid}", pref, 2, "policy")
                link(f"pol:{pid}", it["item_id"], "policy")
        for pid in L(it["precedent_ids"], []) or []:
            if f"prec:{pid}" not in nodes:
                p = db.one("SELECT summary, period FROM precedents WHERE prec_id=?", (pid,))
                node(f"prec:{pid}", f"{pid} ({(p or {}).get('period', '')})", 2, "precedent",
                     detail=(p or {}).get("summary", "")[:160])
            link(f"prec:{pid}", it["item_id"], "precedent")
        if it["approved_by"]:
            link(f"actor:{it['approved_by']}", it["item_id"], "approval")
        if it["parent_id"]:
            link(it["parent_id"], it["item_id"], "revision")
        je = db.one("SELECT entry_id, memo FROM ledger_entries WHERE work_item_id=?", (it["item_id"],))
        if je:
            node(f"je:{je['entry_id']}", f"JE {je['entry_id']}", 4, "ledger", detail=je["memo"])
            link(it["item_id"], f"je:{je['entry_id']}", "posted")
            link("actor:gateway", f"je:{je['entry_id']}", "posted")
        v = prop.get("vendor")
        if v and it["state"] == "POSTED":
            nid = node(f"alias:{v['alias']}", f"Alias '{v['alias']}' → {v.get('vendor_id') or v.get('new', {}).get('vendor_id')}",
                       4, "vendor_master")
            link(it["item_id"], nid, "posted")
    # policies and their precedents (the learning layer)
    for p in db.q("SELECT * FROM policies WHERE status IN ('active','proposed')"):
        nid = node(f"pol:{p['policy_id']}", f"{p['policy_id']} v{p['version']} · {p['title'][:44]}", 2, "policy",
                   state=p["status"], detail=p["rule_text"])
        for pid in L(p["evidence"], []):
            pr = db.one("SELECT summary, period FROM precedents WHERE prec_id=?", (pid,))
            node(f"prec:{pid}", f"{pid} ({(pr or {}).get('period', '')})", 2, "precedent", detail=(pr or {}).get("summary", "")[:160])
            link(f"prec:{pid}", nid, "evidence")
        if p["approved_by"]:
            link(f"actor:{p['approved_by']}", nid, "approval")
    # denied attempts (limits made visible)
    for d in db.q("SELECT seq, actor, action, subject, reason FROM audit_log WHERE allowed=0 ORDER BY seq DESC LIMIT 25"):
        nid = node(f"denied:{d['seq']}", f"DENIED {d['action']} by {d['actor']}", 3, "denied", detail=d["reason"])
        link(f"actor:{d['actor']}" if f"actor:{d['actor']}" in nodes else "actor:jarvis", nid, "denied")
        if d["subject"] in nodes:
            link(nid, d["subject"], "denied")
    return {"nodes": list(nodes.values()), "links": links}
