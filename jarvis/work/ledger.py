"""Ledger reads + exports (Beancount text, QBO-style GL CSV). Writes happen only in gateway.py."""
from __future__ import annotations

import csv
import io
from collections import defaultdict
from pathlib import Path

from jarvis import config
from jarvis.money import plain
from jarvis.work.db import DB, L
from jarvis.world import bible


def balances(db: DB, through: str | None = None, period: str | None = None) -> dict[str, int]:
    sql = ("SELECT l.account, SUM(l.amount_cents) s FROM ledger_lines l JOIN ledger_entries e USING(entry_id) "
           "WHERE 1=1")
    args: list = []
    if through:
        sql += " AND e.date <= ?"
        args.append(through)
    if period:
        sql += " AND e.period = ?"
        args.append(period)
    sql += " GROUP BY l.account"
    return {r["account"]: r["s"] for r in db.q(sql, args)}


def trial_balance(db: DB, through: str | None = None) -> dict:
    b = balances(db, through)
    total = sum(b.values())
    return {"balances": b, "out_of_balance_cents": total, "ok": total == 0}


def entry(db: DB, entry_id: str) -> dict | None:
    e = db.one("SELECT * FROM ledger_entries WHERE entry_id=?", (entry_id,))
    if not e:
        return None
    e["refs"] = L(e["refs"], {})
    e["lines"] = db.q("SELECT line_no, account, amount_cents, memo, vendor_id FROM ledger_lines WHERE entry_id=? "
                      "ORDER BY line_no", (entry_id,))
    return e


def bank_reconciliation(db: DB, period: str) -> dict:
    """Bank statement ending balance vs ledger cash; differences must be explained by unreconciled items."""
    st = (db.kv_get("bank_statements", {}) or {}).get(period)
    ending = st["ending_cents"] if st else None
    y, m = int(period[:4]), int(period[5:7])
    import calendar
    month_end = f"{period}-{calendar.monthrange(y, m)[1]:02d}"
    ledger_cash = balances(db, through=month_end).get("1010", 0)
    unrec = db.q("SELECT r.record_id, r.txn_date, r.amount_cents, r.description FROM records r "
                 "LEFT JOIN reconciliation c USING(record_id) WHERE r.source='bank' AND r.period=? "
                 "AND c.record_id IS NULL ORDER BY r.txn_date", (period,))
    unrec_total = sum(r["amount_cents"] for r in unrec)
    diff = None if ending is None else ending - ledger_cash
    return {"period": period, "statement_ending_cents": ending, "ledger_cash_cents": ledger_cash,
            "difference_cents": diff, "unreconciled": unrec, "unreconciled_total_cents": unrec_total,
            "ties": diff == 0, "explained": diff is not None and diff == unrec_total}


def to_beancount(db: DB) -> str:
    out = io.StringIO()
    out.write(f'option "title" "{bible.COMPANY["name"]}"\noption "operating_currency" "USD"\n\n')
    for num, (bean, name, _t) in bible.COA.items():
        out.write(f'2025-12-31 open {bean} USD\n  number: "{num}"\n  display: "{name}"\n')
    out.write("\n")
    for e in db.q("SELECT * FROM ledger_entries ORDER BY date, entry_id"):
        memo = (e["memo"] or "").replace('"', "'")
        payee = (e["name"] or "").replace('"', "'")
        out.write(f'{e["date"]} * "{payee}" "{memo}"\n  entry_id: "{e["entry_id"]}"\n  source: "{e["source"]}"\n')
        if e["work_item_id"]:
            out.write(f'  work_item: "{e["work_item_id"]}"\n  posted_by: "{e["posted_by"]}"\n')
        for l in db.q("SELECT account, amount_cents FROM ledger_lines WHERE entry_id=? ORDER BY line_no",
                      (e["entry_id"],)):
            out.write(f"  {bible.acct(l['account']):<40} {plain(l['amount_cents']):>14} USD\n")
        out.write("\n")
    return out.getvalue()


def bean_check(text: str) -> list[str]:
    try:
        from beancount import loader
    except Exception:  # pragma: no cover
        return []
    _entries, errors, _opts = loader.load_string(text)
    return [str(getattr(e, "message", e)) for e in errors]


def write_beancount(db: DB, seed: int) -> tuple[Path, list[str]]:
    p = config.RUNTIME_DIR / f"seed_{seed}" / "afterglow.beancount"
    text = to_beancount(db)
    p.write_text(text)
    return p, bean_check(text)


def qbo_gl_csv(db: DB, period: str | None = None) -> str:
    """QuickBooks 'General Ledger' report style export (one row per distribution line)."""
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(["Date", "Transaction Type", "Num", "Name", "Memo/Description", "Distribution Account", "Split",
                 "Debit", "Credit", "Amount", "Balance"])
    running: dict[str, int] = defaultdict(int)
    sql = "SELECT * FROM ledger_entries"
    args: tuple = ()
    if period:
        sql += " WHERE period=?"
        args = (period,)
    for e in db.q(sql + " ORDER BY date, entry_id", args):
        lines = db.q("SELECT account, amount_cents FROM ledger_lines WHERE entry_id=? ORDER BY line_no",
                     (e["entry_id"],))
        for l in lines:
            others = [x for x in lines if x is not l]
            split = bible.acct_name(others[0]["account"]) if len(others) == 1 else "-Split-"
            running[l["account"]] += l["amount_cents"]
            a = l["amount_cents"]
            wr.writerow([e["date"][5:7] + "/" + e["date"][8:10] + "/" + e["date"][:4], e["txn_type"], e["num"],
                         e["name"], e["memo"], f"{l['account']} {bible.acct_name(l['account'])}", split,
                         plain(a) if a > 0 else "", plain(-a) if a < 0 else "", plain(a), plain(running[l["account"]])])
    return buf.getvalue()
