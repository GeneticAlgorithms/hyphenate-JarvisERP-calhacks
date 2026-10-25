"""Read-only tools the agent uses. Every call is logged (the harness sees tools, not tables or keys)."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from pathlib import Path

from jarvis.search import SearchFacade
from jarvis.work import events
from jarvis.work.db import DB, L
from jarvis.work.roles import actor
from jarvis.work.transition import log
from jarvis.world import bible

JARVIS = actor("jarvis")
REVIEWER = actor("jarvis-reviewer")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def sim(a: str, b: str) -> float:
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


class Ctx:
    def __init__(self, db: DB, world: Path, seed: int, search: SearchFacade | None = None, quiet: bool = False):
        self.db, self.world, self.seed = db, world, seed
        self.search = search or SearchFacade()
        self.quiet = quiet
        self.speed = 0.0  # seconds of pause between steps (UI drama); 0 for evals

    # ------------------------------------------------------------- logging
    def tool(self, name: str, subject: str, summary: str, evidence: list | None = None):
        """Record a tool call as an audit event (the graph pulses on these)."""
        if self.quiet:
            return
        log(self.db, JARVIS, f"tool:{name}", subject, summary, evidence or [])

    def think(self, subject: str, text: str):
        events.publish("think", subject=subject, text=text)

    # ------------------------------------------------------------- indexing for retrieval
    def build_index(self):
        db, s = self.db, self.search
        for d in db.q("SELECT * FROM docs"):
            s.index("doc", d["doc_id"], f"{d['title']}\n{d['text']}", {"kind": d["kind"], "vendor": d["vendor"],
                                                                       "date": d["date"]})
        for p in db.q("SELECT * FROM precedents"):
            s.index("precedent", p["prec_id"], f"{p['pattern']} {p['summary']}", {"pattern": p["pattern"],
                                                                                 "period": p["period"]})
        for v in db.q("SELECT * FROM vendors"):
            prods = " ".join(L(v["products"], []))
            s.index("vendor", v["vendor_id"], f"{v['qbo_name']} {v['legal']} {v['domain']} {prods}",
                    {"vendor_id": v["vendor_id"]})
        for r in db.q("SELECT record_id, source, kind, txn_date, amount_cents, counterparty, description FROM records "
                      "WHERE period >= '2026-08'"):
            s.index("record", r["record_id"], f"{r['counterparty']} {r['description']}",
                    {"source": r["source"], "period": r["txn_date"][:7]})
        s.flush()

    # ------------------------------------------------------------- records
    def record(self, rid: str) -> dict | None:
        r = self.db.one("SELECT * FROM records WHERE record_id=?", (rid,))
        if r:
            r["fields"] = L(r["fields"], {})
        return r

    def records(self, sql_where: str, args=()) -> list[dict]:
        rows = self.db.q(f"SELECT * FROM records WHERE {sql_where}", args)
        for r in rows:
            r["fields"] = L(r["fields"], {})
        return rows

    def doc(self, doc_id: str) -> dict | None:
        d = self.db.one("SELECT * FROM docs WHERE doc_id=?", (doc_id,))
        if d:
            d["fields"] = L(d["fields"], {})
        return d

    def docs(self, kind: str | None = None) -> list[dict]:
        rows = self.db.q("SELECT * FROM docs" + (" WHERE kind=?" if kind else ""), (kind,) if kind else ())
        for d in rows:
            d["fields"] = L(d["fields"], {})
        return rows

    def fx(self, date: str) -> float | None:
        r = self.db.one("SELECT eur_usd FROM fx_rates WHERE date=?", (date,))
        return r["eur_usd"] if r else None

    def precedents(self, pattern: str | None = None) -> list[dict]:
        rows = self.db.q("SELECT * FROM precedents WHERE status IN ('approved', 'active')" + (" AND pattern=?" if pattern else "") +
                         " ORDER BY date", (pattern,) if pattern else ())
        for p in rows:
            p["decision"] = L(p["decision"], {})
        return rows

    def active_policy(self, pattern: str) -> dict | None:
        p = self.db.one("SELECT * FROM policies WHERE pattern=? AND status='active' ORDER BY version DESC LIMIT 1",
                        (pattern,))
        if p:
            p["matcher"] = L(p["matcher"], {})
            p["evidence"] = L(p["evidence"], [])
        return p

    def policy_ref(self, pattern: str) -> str | None:
        p = self.active_policy(pattern)
        return f"{p['policy_id']} v{p['version']}" if p else None

    # ------------------------------------------------------------- vendors
    def vendor(self, vendor_id: str) -> dict | None:
        v = self.db.one("SELECT * FROM vendors WHERE vendor_id=?", (vendor_id,))
        if v:
            v["products"] = L(v["products"], [])
        return v

    def vendor_for_alias(self, name: str) -> str | None:
        r = self.db.one("SELECT vendor_id FROM vendor_aliases WHERE alias=? AND status='active'", (name,))
        if r:
            return r["vendor_id"]
        r = self.db.one("SELECT vendor_id FROM vendors WHERE legal=? OR qbo_name=?", (name, name))
        return r["vendor_id"] if r else None

    def vendor_by_domain(self, domain: str) -> str | None:
        if not domain:
            return None
        r = self.db.one("SELECT vendor_id FROM vendors WHERE domain != '' AND (domain=? OR ? LIKE '%.' || domain)",
                        (domain, domain))
        return r["vendor_id"] if r and r["vendor_id"] else None

    def resolve_vendor(self, name: str, email: str = "", descriptor: str = "") -> tuple[str | None, list[dict]]:
        """Returns (vendor_id or None, signals). Product names are weak evidence; legal entity/domain/TIN strong."""
        signals: list[dict] = []
        vid = self.vendor_for_alias(name)
        if vid:
            signals.append({"signal": "known alias/legal name", "strength": "strong", "vendor_id": vid})
            return vid, signals
        dom = email.split("@")[-1] if "@" in email else ""
        if dom:
            vid = self.vendor_by_domain(dom)
            if vid:
                signals.append({"signal": f"payee email domain {dom}", "strength": "strong", "vendor_id": vid})
                return vid, signals
        for v in self.db.q("SELECT vendor_id, products FROM vendors"):
            prods = [norm(p) for p in L(v["products"], [])]
            if norm(name) in prods or any(p and p in norm(descriptor) for p in prods):
                signals.append({"signal": f"'{name}' is a product of {v['vendor_id']}", "strength": "medium",
                                "vendor_id": v["vendor_id"]})
                return v["vendor_id"], signals
        return None, signals

    def ledger_entry_for(self, key: str, value: str) -> dict | None:
        return self.db.one(f"SELECT * FROM ledger_entries WHERE refs LIKE ?", (f'%"{key}": "{value}"%',))

    def entry_lines(self, entry_id: str) -> list[dict]:
        return self.db.q("SELECT account, amount_cents, vendor_id FROM ledger_lines WHERE entry_id=? ORDER BY line_no",
                         (entry_id,))

    def consumed_records(self) -> set[str]:
        """Source records already claimed by a live work item (so nothing is matched twice)."""
        out = set()
        for it in self.db.q("SELECT source_refs, proposal FROM work_items WHERE state NOT IN ('REJECTED','DISMISSED')"):
            for ref in L(it["source_refs"], []):
                out.add(ref)
            for ref in (L(it["proposal"], {}) or {}).get("consumes", []):
                out.add(ref)
        return out

    def employee_for_email(self, email: str) -> str | None:
        for p in bible.PEOPLE.values():
            if p["email"].lower() == (email or "").lower() and p["actor"] == "employee":
                return p["name"]
        return None
