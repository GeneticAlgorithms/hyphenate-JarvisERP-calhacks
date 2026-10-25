"""Baseline B1: what a rules-based bank feed + accounting integration does with the same world.

Emulates typical bank-feed behaviour: auto-match on exact amount within ±3 days, otherwise categorize by payee
keyword rules; accept the card platform's categories; auto-create vendors it hasn't seen; no accruals, no
PayPal look-through, no duplicate detection, never asks. Output is in the same shape as the agent's outcomes.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from jarvis.money import to_cents
from jarvis.world import ids

RULES = [  # payee keyword -> (kind, debit account)  (typical user-created bank rules)
    (r"PAYPAL", ("rule", "6410")),         # "PayPal -> Software" - the classic shortcut
    (r"INTEREST PAYMENT", ("rule", "4900")),
    (r"SERVICE FEE", ("bank_fee", "6810")),
    (r"Zelle", ("rule", "6900")),
]


def run_b1(world: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    ledger = json.loads((world / "ledger_seed.json").read_text())
    bills = json.loads((world / "bills.json").read_text())
    reconciled_entries = {e["id"] for e in ledger if e["refs"].get("bank_id")}
    cash_entries = [(e, next(c for a, c in e["lines"] if a == "1010")) for e in ledger
                    if any(a == "1010" for a, _ in e["lines"]) and e["id"] not in reconciled_entries]
    from datetime import date
    for f in sorted((world / "systems" / "bank").glob("chase_operating_2026-09.csv")):
        occ = {}
        for r in csv.DictReader(f.open()):
            k = (r["Posting Date"], r["Amount"], r["Description"].strip())
            o = occ.get(k, 0)
            occ[k] = o + 1
            bid = ids.bank_id("x4471", *k, o)
            amt = to_cents(r["Amount"])
            m_, d_, y_ = r["Posting Date"].split("/")
            d = date(int(y_), int(m_), int(d_))
            match = [e for e, c in cash_entries if c == amt and abs((date.fromisoformat(e["date"]) - d).days) <= 3]
            anchor = f"bank:{bid}"
            if match:
                out[anchor] = {"kind": "match", "state": "POSTED", "lines": [], "escalated": False}
                continue
            bill = next((b for b in bills if b["status"] == "Open" and b["amount"] == -amt), None)
            if bill and "PAY" in r["Description"]:
                out[anchor] = {"kind": "bill_payment", "state": "POSTED", "escalated": False,
                               "lines": [["2010", -amt], ["1010", amt]]}
                continue
            if "CARD PMT" in r["Description"]:
                out[anchor] = {"kind": "card_statement_payment", "state": "POSTED", "escalated": False,
                               "lines": [["2050", -amt], ["1010", amt]]}
                continue
            for rx, (kind, acct) in RULES:
                if re.search(rx, r["Description"]):
                    out[anchor] = {"kind": "paypal_split" if "PAYPAL" in rx else kind, "state": "POSTED",
                                   "escalated": False, "lines": [[acct, -amt], ["1010", amt]]}
                    break
            else:
                out[anchor] = {"kind": "uncategorized", "state": "POSTED", "escalated": False,
                               "lines": [["6900", -amt], ["1010", amt]]}
    # card platform: categories accepted; unknown merchants -> new vendors auto-created
    vend = {v["qbo_name"] for v in json.loads((world / "vendors.json").read_text())}
    for f in sorted((world / "systems" / "ramp").glob("transactions_2026-09.csv")):
        for r in csv.DictReader(f.open()):
            if r["Ramp Vendor"] and not r["ERP Vendor"] and r["Ramp Vendor"] not in vend:
                out[f"vendor:{r['Ramp Vendor']}"] = {"kind": "vendor_create", "state": "POSTED", "escalated": False,
                                                     "lines": [], "vendor": {"action": "create"}}
    for f in sorted((world / "systems" / "paypal").glob("activity_2026-09.csv")):
        for r in csv.DictReader(f.open()):
            if r["Name"] and r["Name"] not in vend and r["Type"] != "General Currency Conversion" and \
                    not r["Name"].startswith(("Anthropic", "Damlicht", "Kraftwerk")):
                out[f"vendor:{r['Name']}"] = {"kind": "vendor_create", "state": "POSTED", "escalated": False,
                                              "lines": [], "vendor": {"action": "create"}}
    return out
