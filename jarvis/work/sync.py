"""Stateful sync from the systems of record into one shape (raw -> standardized -> golden).

* Change-only: each source keeps a cursor (files + content hashes already landed).
* Stable ids: md5(source|src_id); Chase rows get md5(acct|date|amount|desc|occurrence).
* Re-sync never duplicates; a changed row (late bank post) is updated and logged.
* Every golden row keeps raw_ref back to its raw row.
* PayPal is read through a (mock) API first; on failure we retry with backoff, then fall back
  to the CSV activity export and mark the evidence quality as 'export'.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from pathlib import Path

from jarvis import money
from jarvis.work import events
from jarvis.work.db import DB, J, L
from jarvis.work.roles import actor
from jarvis.work.transition import append_audit, log, now
from jarvis.world import ids

SYNC = actor("sync")


def _h(obj) -> str:
    return hashlib.md5(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def _us_to_iso(s: str) -> str:
    m, d, y = s.split("/")
    return f"{y}-{int(m):02d}-{int(d):02d}"


def parse_front_matter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


# ----------------------------------------------------------------------------- PayPal mock API
class PayPalAPI:
    """Stand-in for PayPal's Transaction Search API, serving the same rows as the export.
    fault: None | 'flaky' (fails twice then works) | 'down' (always fails) | 'ratelimit' (429 x3)."""
    fault: str | None = None
    _calls = 0

    def __init__(self, world: Path):
        self.world = world

    def fetch(self, month: str) -> list[dict]:
        type(self)._calls += 1
        f = type(self).fault
        if f == "down":
            raise ConnectionError("PayPal API 503 Service Unavailable")
        if f == "ratelimit" and type(self)._calls <= 3:
            raise ConnectionError("PayPal API 429 Too Many Requests (retry-after: 1)")
        if f == "flaky" and type(self)._calls <= 2:
            raise ConnectionError("PayPal API 502 Bad Gateway")
        p = self.world / "systems" / "paypal" / f"activity_{month}.csv"
        return list(csv.DictReader(p.open())) if p.exists() else []


# ----------------------------------------------------------------------------- upsert
def _upsert(db: DB, source: str, src_id: str, kind: str, txn_date: str, amount: int, currency: str,
            counterparty: str, description: str, fields: dict, raw: dict, file: str, row_num: int,
            quality: str = "api") -> str:
    rid = ids.record_id(source, src_id)
    raw_id = f"raw-{rid}"
    payload_hash = _h(raw)
    ts = now()
    existing = db.conn.execute("SELECT fields FROM records WHERE record_id=?", (rid,)).fetchone()
    db.conn.execute("INSERT OR REPLACE INTO raw_rows(raw_id,source,file,row_num,payload,landed_at) VALUES(?,?,?,?,?,?)",
                    (raw_id, source, file, row_num, J(raw), ts))
    fields = {**fields, "_raw_hash": payload_hash}
    if existing is None:
        db.conn.execute(
            "INSERT INTO records(record_id,source,src_id,kind,txn_date,period,amount_cents,currency,counterparty,"
            "description,fields,raw_ref,evidence_quality,synced_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, source, src_id, kind, txn_date, txn_date[:7], amount, currency, counterparty, description, J(fields),
             raw_id, quality, ts, ts))
        return "new"
    if L(existing[0], {}).get("_raw_hash") != payload_hash:
        db.conn.execute("UPDATE records SET txn_date=?, period=?, amount_cents=?, counterparty=?, description=?, "
                        "fields=?, evidence_quality=?, updated_at=? WHERE record_id=?",
                        (txn_date, txn_date[:7], amount, counterparty, description, J(fields), quality, ts, rid))
        return "updated"
    return "unchanged"


# ----------------------------------------------------------------------------- sources
def _sync_bank(db: DB, files: list[Path]) -> dict:
    c = {"new": 0, "updated": 0, "unchanged": 0}
    for f in files:
        rows = list(csv.DictReader(f.open()))
        occ: dict = {}
        for i, r in enumerate(rows):
            k = (r["Posting Date"], r["Amount"], r["Description"].strip())
            o = occ.get(k, 0)
            occ[k] = o + 1
            bid = ids.bank_id("x4471", *k, o)
            res = _upsert(db, "bank", bid, "bank_txn", _us_to_iso(r["Posting Date"]), money.to_cents(r["Amount"]), "USD",
                          "", r["Description"].strip(),
                          {"bank_id": bid, "details": r["Details"], "type": r["Type"],
                           "balance_cents": money.to_cents(r["Balance"]), "account": "Chase x4471"},
                          r, f.name, i)
            c[res] += 1
    return c


def _paypal_rows_to_records(db: DB, rows: list[dict], file: str, quality: str) -> dict:
    c = {"new": 0, "updated": 0, "unchanged": 0}
    for i, r in enumerate(rows):
        res = _upsert(db, "paypal", r["Transaction ID"], "paypal_" + re.sub(r"\W+", "_", r["Type"].lower()).strip("_"),
                      _us_to_iso(r["Date"]), money.to_cents(r["Gross"]), r["Currency"], r["Name"],
                      f"{r['Type']} {r['Name']} {r['Item Title']}".strip(),
                      {"txn_id": r["Transaction ID"], "type": r["Type"], "time": r["Time"], "status": r["Status"],
                       "fee_cents": money.to_cents(r["Fee"]), "net_cents": money.to_cents(r["Net"]),
                       "from_email": r["From Email Address"], "to_email": r["To Email Address"],
                       "item": r["Item Title"], "ref": r["Reference Txn ID"], "impact": r["Balance Impact"]},
                      r, file, i, quality)
        c[res] += 1
    return c


def _sync_paypal(db: DB, world: Path, months: list[str]) -> dict:
    total = {"new": 0, "updated": 0, "unchanged": 0, "api_failures": 0, "fallback_months": []}
    api = PayPalAPI(world)
    for mon in months:
        rows, quality = None, "api"
        for attempt in range(3):
            try:
                rows = api.fetch(mon)
                break
            except ConnectionError as e:
                total["api_failures"] += 1
                with db.tx():
                    append_audit(db, SYNC, "fetch_failed", f"paypal:{mon}", True,
                                 f"{e} (attempt {attempt + 1}/3, backing off {0.2 * 2 ** attempt:.1f}s)")
                time.sleep(0.2 * 2 ** attempt)
        if rows is None:
            p = world / "systems" / "paypal" / f"activity_{mon}.csv"
            rows = list(csv.DictReader(p.open())) if p.exists() else []
            quality = "export"
            total["fallback_months"].append(mon)
            with db.tx():
                append_audit(db, SYNC, "fallback", f"paypal:{mon}", True,
                             f"PayPal API unavailable - fell back to activity export {p.name}; evidence marked 'export'")
        with db.tx():
            c = _paypal_rows_to_records(db, rows, f"activity_{mon}.csv", quality)
        for k in ("new", "updated", "unchanged"):
            total[k] += c[k]
    return total


def _sync_ramp(db: DB, files: list[Path]) -> dict:
    c = {"new": 0, "updated": 0, "unchanged": 0}
    for f in files:
        for i, r in enumerate(csv.DictReader(f.open())):
            res = _upsert(db, "ramp", r["Transaction ID"], "card_txn", r["Transaction Date"], money.to_cents(r["Amount"]),
                          r["Currency"], r["Merchant Name"], f"{r['Merchant Descriptor']} {r['Memo']}".strip(),
                          {"ramp_id": r["Transaction ID"], "settle": r["Settlement Date"], "merchant": r["Merchant Name"],
                           "descriptor": r["Merchant Descriptor"], "cardholder": r["Cardholder"], "last4": r["Card Last 4"],
                           "mcc": r["MCC"], "department": r["Department"], "category": r["Accounting Category"],
                           "memo": r["Memo"], "receipt": r["Receipt Attached"], "ramp_vendor": r["Ramp Vendor"],
                           "erp_vendor": r["ERP Vendor"]}, r, f.name, i)
            c[res] += 1
    return c


def _sync_docs(db: DB, world: Path, index_file: Path) -> dict:
    c = {"new": 0, "unchanged": 0}
    if not index_file.exists():
        return c
    for d in json.loads(index_file.read_text()):
        text = (world / d["path"]).read_text()
        fm = parse_front_matter(text)
        fields = {**fm, **d.get("fields", {})}
        vendor = fields.get("vendor") or fields.get("issuer") or ""
        if db.conn.execute("SELECT 1 FROM docs WHERE doc_id=?", (d["doc_id"],)).fetchone():
            c["unchanged"] += 1
            continue
        db.conn.execute("INSERT INTO docs(doc_id,kind,title,date,vendor,fields,path,text,synced_at) VALUES(?,?,?,?,?,?,?,?,?)",
                        (d["doc_id"], d["kind"], d["title"], d["date"], vendor, J(fields), d["path"], text, now()))
        c["new"] += 1
    return c


# ----------------------------------------------------------------------------- public API
def bootstrap(db: DB, world: Path):
    """First connection to the company: master data + the existing ledger (Jan-Sep as of close start)."""
    if db.kv_get("bootstrapped"):
        return False
    with db.tx():
        for v in json.loads((world / "vendors.json").read_text()):
            db.conn.execute("INSERT OR IGNORE INTO vendors(vendor_id,qbo_name,legal,domain,default_acct,products,tin,status,"
                            "created_by) VALUES(?,?,?,?,?,?,?,?,?)",
                            (v["id"], v["qbo_name"], v["legal"], v.get("domain", ""), v.get("default_acct", ""),
                             J(v.get("products", [])), v.get("tin", ""), "active", "qbo"))
            db.conn.execute("INSERT OR IGNORE INTO vendor_aliases(alias,vendor_id,source,status,work_item_id,at) "
                            "VALUES(?,?,?,?,?,?)", (v["qbo_name"], v["id"], "qbo", "active", None, now()))
        for e in json.loads((world / "ledger_seed.json").read_text()):
            db.conn.execute("INSERT OR IGNORE INTO ledger_entries(entry_id,date,period,memo,name,txn_type,num,source,refs,"
                            "work_item_id,posted_by,posted_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (e["id"], e["date"], e["date"][:7], e["memo"], e["name"], e["txn_type"], e["num"], e["source"],
                             J(e["refs"]), None, e["source"], now()))
            for i, (a, cents) in enumerate(e["lines"]):
                db.conn.execute("INSERT OR IGNORE INTO ledger_lines(entry_id,line_no,account,amount_cents,memo,vendor_id) "
                                "VALUES(?,?,?,?,?,?)", (e["id"], i, a, cents, "", None))
        for b in json.loads((world / "bills.json").read_text()):
            db.conn.execute("INSERT OR IGNORE INTO bills(bill_id,vendor_id,vendor,date,due,amount_cents,num,memo,acct,status,"
                            "service_period,je_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (b["bill_id"], b["vendor_id"], b["vendor"], b["date"], b["due"], b["amount"], b["num"],
                             b["memo"], b["acct"], b["status"], b["service_period"], b.get("je_id")))
        for line in (world / "history" / "precedents.jsonl").read_text().splitlines():
            p = json.loads(line)
            db.conn.execute("INSERT OR IGNORE INTO precedents(prec_id,date,period,pattern,summary,decision,decided_by,status,"
                            "refs,source_item) VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (p["id"], p["date"], p["period"], p["pattern"], p["summary"], J(p["decision"]),
                             p["decided_by"], p["status"], J(p["refs"]), None))
        for r in csv.DictReader((world / "systems" / "reference" / "fx_eur_usd.csv").open()):
            db.conn.execute("INSERT OR IGNORE INTO fx_rates(date,eur_usd,source) VALUES(?,?,?)",
                            (r["date"], float(r["eur_usd"]), r["source"]))
        append_audit(db, SYNC, "bootstrap", "systems_of_record", True,
                     "Connected to QBO (ledger, vendors, open bills), precedents and reference FX")
    # mark historical bank lines that the books already reconcile (refs carry bank_id) after bank sync
    db.kv_set("bank_statements", json.loads((world / "systems" / "bank" / "statements" / "statements.json").read_text()))
    db.kv_set("world_date", "2026-10-06")
    db.kv_set("phase", "initial")
    db.kv_set("bootstrapped", True)
    return True


def sync_all(db: DB, world: Path, phase: str = "initial") -> dict:
    t0 = time.time()
    out: dict = {}
    if phase == "initial":
        bank_files = sorted((world / "systems" / "bank").glob("chase_operating_*.csv"))
        ramp_files = sorted((world / "systems" / "ramp").glob("transactions_*.csv"))
        pp_months = sorted(p.stem.split("_")[1] for p in (world / "systems" / "paypal").glob("activity_*.csv"))
        with db.tx():
            out["bank"] = _sync_bank(db, bank_files)
            out["ramp"] = _sync_ramp(db, ramp_files)
            out["docs"] = _sync_docs(db, world, world / "systems" / "docs" / "index.json")
        out["paypal"] = _sync_paypal(db, world, pp_months)
        with db.tx():
            # history: link bank lines the existing books already reconciled
            n = 0
            for e in db.q("SELECT entry_id, refs FROM ledger_entries WHERE refs LIKE '%bank_id%'"):
                bid = L(e["refs"], {}).get("bank_id")
                if bid:
                    rid = ids.record_id("bank", bid)
                    db.conn.execute("INSERT OR IGNORE INTO reconciliation(record_id,entry_id,work_item_id,at) "
                                    "VALUES(?,?,?,?)", (rid, e["entry_id"], None, now()))
                    n += 1
            out["history_reconciled"] = n
    else:
        arr = world / "arrivals" / "2026-10-late"
        with db.tx():
            out["bank"] = _sync_bank(db, sorted((arr / "bank").glob("*.csv")) if (arr / "bank").exists() else [])
            out["docs"] = _sync_docs(db, world, arr / "docs_index.json")
            nb = 0
            for b in json.loads((arr / "qbo_bills.json").read_text()) if (arr / "qbo_bills.json").exists() else []:
                if db.conn.execute("SELECT 1 FROM bills WHERE bill_id=?", (b["bill_id"],)).fetchone():
                    continue
                je_id = f"JE-{b['bill_id']}"
                db.conn.execute("INSERT INTO ledger_entries(entry_id,date,period,memo,name,txn_type,num,source,refs,"
                                "work_item_id,posted_by,posted_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                                (je_id, b["date"], b["date"][:7], b["memo"], b["vendor"], "Bill", b["num"], "ap_clerk",
                                 J({"bill_id": b["bill_id"], "doc_id": b.get("doc_id")}), None, "ap_clerk", now()))
                db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (je_id, 0, b["acct"], b["amount"], "", b["vendor_id"]))
                db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (je_id, 1, "2010", -b["amount"], "", b["vendor_id"]))
                db.conn.execute("INSERT INTO bills(bill_id,vendor_id,vendor,date,due,amount_cents,num,memo,acct,status,"
                                "service_period,je_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                                (b["bill_id"], b["vendor_id"], b["vendor"], b["date"], b["date"], b["amount"], b["num"],
                                 b["memo"], b["acct"], "Open", b["service_period"], je_id))
                nb += 1
            out["bills_entered_by_ap_clerk"] = nb
        db.kv_set("world_date", "2026-10-12")
        db.kv_set("phase", "october")
    out["seconds"] = round(time.time() - t0, 2)
    summary = ", ".join(f"{k}: {v}" for k, v in out.items() if isinstance(v, dict))
    log(db, SYNC, "sync", f"sync:{phase}", f"change-only sync ({phase}) - {summary}")
    events.publish("sync", phase=phase, result=out)
    return out
