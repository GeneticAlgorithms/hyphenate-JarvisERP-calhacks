"""Seeded world generator for Afterglow Labs, Jan-Oct 2026.

Produces, under data/worlds/seed_<n>/:
  systems/bank/chase_operating_2026-MM.csv     (Chase business checking export format)
  systems/paypal/activity_2026-MM.csv          (PayPal activity download format)
  systems/ramp/transactions_2026-MM.csv        (Ramp card transactions export)
  systems/qbo/*.csv                            (vendor list, CoA, open bills) - GL export is produced by the ledger
  systems/docs/...                             (SOWs, timesheets, invoices, emails, run sheets, bank notices)
  systems/reference/fx_eur_usd.csv             (market reference rates)
  arrivals/2026-10-late/...                    (data that lands mid-October, for true-ups)
  policy/close_policy.md, policy/approval_matrix.json
  history/precedents.jsonl                     (Jan-Aug decisions: the company's memory)
  ledger_seed.json                             (what the ledger contains before Jarvis starts)
  answer_key.json                              (planted issues + expected treatment; NEVER read by the agent)

Usage:  python -m jarvis.world.generator --seed 2026
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from jarvis import config
from jarvis.money import mul_rate, plain
from jarvis.world import bible, ids

YEAR = 2026
MONTHS_HIST = range(1, 9)        # Jan..Aug are closed history
CLOSE_M = 9
LATE_OCT_FROM = date(2026, 10, 7)  # data on/after this lands in the "October arrivals" phase
CLOSE_START = date(2026, 10, 6)    # the day Jarvis starts the September close


def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def month_end(m: int) -> date:
    return (date(YEAR, m, 28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def biz(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def biz_back(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def us(d: date) -> str:
    return d.strftime("%m/%d/%Y")


def period(d: date) -> str:
    return d.strftime("%Y-%m")


@dataclass
class World:
    seed: int
    rng: random.Random
    bank: list = field(default_factory=list)
    paypal: list = field(default_factory=list)
    ramp: list = field(default_factory=list)
    ledger: list = field(default_factory=list)
    docs: list = field(default_factory=list)
    precedents: list = field(default_factory=list)
    bills: list = field(default_factory=list)
    key: list = field(default_factory=list)
    fx: dict = field(default_factory=dict)
    _seq: dict = field(default_factory=dict)
    _occ: dict = field(default_factory=dict)

    # ---------------- id helpers ----------------
    def seq(self, name: str) -> int:
        self._seq[name] = self._seq.get(name, 0) + 1
        return self._seq[name]

    def pp_id(self) -> str:
        n = self.seq("pp")
        h = md5(f"pp{self.seed}{n}").upper()
        return f"{h[0]}{h[1:3]}{int(h[3:9], 16) % 10**6:06d}{h[9:11]}{int(h[11:17], 16) % 10**6:06d}"[:17]

    def ramp_id(self) -> str:
        h = md5(f"ramp{self.seed}{self.seq('ramp')}")
        return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"

    # ---------------- record helpers ----------------
    def bank_row(self, d: date, desc: str, cents: int, typ: str, truth: dict, post_lag: int = 0) -> dict:
        pdate = biz(d + timedelta(days=post_lag))
        k = (us(pdate), plain(cents), desc.strip())
        occ = self._occ.get(k, 0)
        self._occ[k] = occ + 1
        row = {
            "bank_id": ids.bank_id("x4471", us(pdate), plain(cents), desc, occ),
            "date": d, "post_date": pdate,
            "desc": desc, "amount": cents, "type": typ,
            "details": "CREDIT" if cents > 0 else "DEBIT",
            "check": "", "truth": truth,
        }
        self.bank.append(row)
        return row

    def je(self, d: date, memo: str, lines: list[tuple[str, int]], source: str, refs: dict | None = None,
           name: str = "", txn_type: str = "Journal Entry", num: str = "") -> dict:
        assert sum(c for _, c in lines) == 0, (memo, lines)
        e = {"id": f"JE-{self.seq('je'):05d}", "date": d.isoformat(), "memo": memo, "name": name,
             "txn_type": txn_type, "num": num, "source": source, "refs": refs or {},
             "lines": [[a, c] for a, c in lines]}
        self.ledger.append(e)
        return e

    def doc(self, kind: str, doc_id: str, title: str, d: date, body: str, fields: dict, folder: str,
            ext: str = "md", arrival: str = "initial") -> dict:
        rec = {"doc_id": doc_id, "kind": kind, "title": title, "date": d.isoformat(), "fields": fields,
               "path": f"{folder}/{doc_id}.{ext}", "body": body, "arrival": arrival}
        self.docs.append(rec)
        return rec

    def precedent(self, d: date, pattern: str, summary: str, decision: dict, actor: str, refs: dict | None = None):
        self.precedents.append({
            "id": f"prec-{len(self.precedents) + 101:03d}", "date": d.isoformat(), "period": period(d),
            "pattern": pattern, "summary": summary, "decision": decision, "decided_by": actor,
            "status": "approved", "refs": refs or {},
        })

    def keyitem(self, anchor: str, category: str, phase: str, expected: dict, note: str):
        self.key.append({"key_id": f"K{len(self.key) + 1:02d}", "anchor": anchor, "category": category,
                         "phase": phase, "expected": expected, "note": note})

    # ---------------- FX ----------------
    def market(self, d: date) -> float:
        return self.fx[d.isoformat()]


# =============================================================================
def build(seed: int) -> World:
    rng = random.Random(seed)
    w = World(seed=seed, rng=rng)
    exact = seed == 2026  # the demo seed reproduces the numbers in PLAN.md exactly

    # ---- reference FX: EUR->USD daily, a gentle random walk around 1.17
    r = 1.165
    d = date(YEAR, 1, 1)
    while d <= date(YEAR, 10, 31):
        r = max(1.12, min(1.21, r + rng.uniform(-0.0035, 0.0035)))
        w.fx[d.isoformat()] = round(r, 4)
        d += timedelta(days=1)
    if exact:
        w.fx["2026-09-17"] = 1.1700
        w.fx["2026-09-18"] = 1.1700

    # ---- opening balances (Jan 1)
    dec_interest = 101_0_17 if exact else rng.randint(95_000, 108_000)
    dec_ramp = rng.randint(880_000, 980_000)
    opening = [("1010", 185_000_000), ("1030", 250_000), ("1260", dec_interest)]
    opening.append(("2050", -dec_ramp))
    opening.append(("3000", -sum(c for _, c in opening)))
    w.je(date(YEAR, 1, 1), "Opening balances (migrated from prior system)", opening, "migration")

    normal_ramp = [  # merchant, descriptor, qbo vendor, acct, low, high, mcc
        ("Uber", "UBER *TRIP HELP.UBER.COM", "Uber", "6430", 1800, 7200, "4121"),
        ("Delta Air Lines", "DELTA AIR 0062187390114", "Delta Air Lines", "6430", 28000, 94000, "3058"),
        ("Marriott", "MARRIOTT OAKLAND CITY CTR", "Marriott", "6430", 21000, 68000, "3509"),
        ("Figma", "FIGMA MONTHLY", "Figma", "6410", 4500, 4500, "5734"),
        ("Notion", "NOTION LABS INC", "Notion", "6410", 9600, 9600, "5734"),
        ("Sweetgreen", "SWEETGREEN OAKLAND", "Sweetgreen", "6440", 2400, 9800, "5814"),
        ("B&H Photo", "B&H PHOTO 800-606-6969", "B&H Photo", "5030", 12000, 86000, "5732"),
        ("FedEx", "FEDEX 78231904", "FedEx", "6900", 3500, 21000, "4215"),
    ]
    people_cards = [("J. Ortiz", "8812"), ("Sam Rivera", "3307"), ("Lee Okafor", "5521"), ("Maya Chen", "1194")]

    def ramp_txn(d: date, merchant: str, descriptor: str, ramp_vendor: str, erp_vendor: str, acct: str,
                 cents: int, mcc: str, who: tuple[str, str], memo: str = "", receipt: bool = True,
                 category_label: str | None = None, truth: dict | None = None, post_to: str | None = None) -> dict:
        t = {"ramp_id": w.ramp_id(), "date": d, "settle": biz(d + timedelta(days=rng.choice([1, 2]))),
             "merchant": merchant, "descriptor": descriptor, "amount": cents, "currency": "USD",
             "cardholder": who[0], "last4": who[1], "mcc": mcc,
             "department": "Live" if who[0] == "J. Ortiz" else rng.choice(["Cloud", "Studio", "G&A"]),
             "category": category_label or bible.acct_name(acct), "memo": memo,
             "receipt": "Yes" if receipt else "No", "ramp_vendor": ramp_vendor, "erp_vendor": erp_vendor,
             "acct": post_to or acct, "truth": truth or {}}
        w.ramp.append(t)
        # Ramp -> QBO sync posts every card transaction (as categorized by Ramp)
        w.je(t["settle"], f"Ramp card {merchant} ({who[0]}) {memo}".strip(),
             [(t["acct"], cents), ("2050", -cents)], "ramp_sync",
             {"ramp_id": t["ramp_id"]}, name=erp_vendor or ramp_vendor, txn_type="Expense")
        return t

    def bill(d: date, vendor_id: str, cents: int, memo: str, acct: str, num: str, service: str,
             source: str = "ap_clerk") -> dict:
        v = next(x for x in bible.VENDORS if x["id"] == vendor_id)
        b = {"bill_id": f"BILL-{w.seq('bill'):04d}", "vendor_id": vendor_id, "vendor": v["qbo_name"],
             "date": d.isoformat(), "due": (d + timedelta(days=30)).isoformat(), "amount": cents,
             "memo": memo, "num": num, "service_period": service, "acct": acct, "status": "Open"}
        e = w.je(d, memo, [(acct, cents), ("2010", -cents)], source, {"bill_id": b["bill_id"]},
                 name=v["qbo_name"], txn_type="Bill", num=num)
        b["je_id"] = e["id"]
        w.bills.append(b)
        return b

    def pay_bill(b: dict, d: date, desc: str, book: bool = True) -> dict:
        row = w.bank_row(d, desc, -b["amount"], "ACH_DEBIT", {"kind": "bill_payment", "bill_id": b["bill_id"]})
        if book:
            w.je(d, f"Bill payment {b['vendor']} {b['num']}", [("2010", b["amount"]), ("1010", -b["amount"])],
                 "ap_clerk", {"bill_id": b["bill_id"], "bank_id": row["bank_id"]}, name=b["vendor"],
                 txn_type="Bill Payment (Check)")
            b["status"] = "Paid"
        return row

    def paypal_payment(d: date, name: str, email: str, item: str, cents: int, currency: str,
                       ptype: str, from_email: str = "ap@afterglowlabs.com") -> dict:
        p = {"txn_id": w.pp_id(), "date": d, "time": f"{rng.randint(8, 18):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}",
             "name": name, "type": ptype, "status": "Completed", "currency": currency,
             "gross": -cents, "fee": 0, "net": -cents, "from": from_email, "to": email, "item": item, "ref": "",
             "impact": "Debit"}
        w.paypal.append(p)
        return p

    def paypal_conversion(d: date, pay: dict, usd_cents: int, eur_cents: int):
        for cur, amt, imp in (("USD", -usd_cents, "Debit"), ("EUR", eur_cents, "Credit")):
            w.paypal.append({"txn_id": w.pp_id(), "date": d, "time": pay["time"], "name": "",
                             "type": "General Currency Conversion", "status": "Completed", "currency": cur,
                             "gross": amt, "fee": 0, "net": amt, "from": "", "to": "", "item": "",
                             "ref": pay["txn_id"], "impact": imp})

    def paypal_funding(d: date, usd_cents: int, ref: str = "") -> dict:
        p = {"txn_id": w.pp_id(), "date": d, "time": f"{rng.randint(8, 18):02d}:{rng.randint(0, 59):02d}:00",
             "name": "", "type": "Bank Deposit to PP Account", "status": "Completed", "currency": "USD",
             "gross": usd_cents, "fee": 0, "net": usd_cents, "from": "", "to": "", "item": "", "ref": ref,
             "impact": "Credit"}
        w.paypal.append(p)
        return p

    def eur_payment(d: date, vendor_id: str, eur: int, spread: float, item: str):
        v = next(x for x in bible.VENDORS if x["id"] == vendor_id)
        pp_rate = round(w.market(d) * (1 + spread), 4)
        usd_paid = mul_rate(eur, pp_rate)
        usd_mkt = mul_rate(eur, w.market(d))
        pay = paypal_payment(d, v["legal"], f"billing@{v['domain']}", item, eur, "EUR", "General Payment")
        paypal_conversion(d, pay, usd_paid, eur)
        return pay, usd_paid, usd_mkt, pp_rate

    # bank descriptors (Chase ACH style)
    def ach_desc(co: str, oid: str, descr: str, d: date, ind: str = "") -> str:
        trace = int(md5(f"{co}{d}{w.seq('trace')}")[:12], 16) % 10**15
        s = (f"ORIG CO NAME:{co:<16} ORIG ID:{oid} DESC DATE:{d.strftime('%y%m%d')} "
             f"CO ENTRY DESCR:{descr:<10}SEC:CCD    TRACE#:{trace:015d} EED:{d.strftime('%y%m%d')}")
        if ind:
            s += f"   IND ID:{ind} IND NAME:AFTERGLOW LABS INC"
        return s

    month_ramp_total: dict[int, int] = {}
    lumen_hist: list[dict] = []
    interest_by_month: dict[int, int] = {}
    pending_lumen_bill: dict | None = None

    # =================== monthly activity Jan..Oct ===================
    for m in range(1, 11):
        me = month_end(m)
        is_close = m == CLOSE_M
        is_oct = m == 10

        # --- prior month interest deposited on the 1st (accrued last month-end)
        prev_int = dec_interest if m == 1 else interest_by_month[m - 1]
        d1 = date(YEAR, m, 1)
        row = w.bank_row(d1, "INTEREST PAYMENT", prev_int, "MISC_CREDIT",
                         {"kind": "interest_receipt", "for_period": f"{YEAR}-{m - 1:02d}" if m > 1 else "2025-12"})
        if not is_close and not is_oct:
            w.je(d1, "Interest received (clears prior-month receivable)", [("1010", prev_int), ("1260", -prev_int)],
                 "staff_accountant", {"bank_id": row["bank_id"]}, txn_type="Deposit")
        elif is_close:
            w.keyitem(f"bank:{row['bank_id']}", "interest_receipt", "close",
                      {"kind": "receivable_receipt", "lines": [["1010", prev_int], ["1260", -prev_int]], "escalate": False},
                      "Aug interest credited Sep 1: clear Interest Receivable, not new income.")
        else:
            w.keyitem(f"bank:{row['bank_id']}", "interest_receipt", "october",
                      {"kind": "receivable_receipt", "lines": [["1010", prev_int], ["1260", -prev_int]], "escalate": False},
                      "Sep interest credited Oct 1 must clear the Sep accrual (timing difference).")

        if is_oct:
            continue  # October only needs the items handled further below

        # --- Stripe payouts (synced to ledger by the Stripe integration)
        for day in (3, 10, 17, 24):
            dd = biz(date(YEAR, m, day) + timedelta(days=rng.choice([0, 0, 1])))
            amt = rng.randint(1_800_000, 3_250_000)
            sid = f"po_{md5(f'{seed}{dd}{amt}')[:14]}"
            row = w.bank_row(dd, ach_desc("STRIPE", "1800948598", "TRANSFER", dd, f"ST-{sid[3:11].upper()}"), amt,
                             "ACH_CREDIT", {"kind": "synced_deposit", "payout": sid})
            w.je(dd, f"Stripe payout {sid}", [("1010", amt), ("4010", -amt)], "stripe_sync",
                 {"payout": sid, **({} if is_close else {"bank_id": row["bank_id"]})}, name="Stripe", txn_type="Deposit")
            if is_close:
                w.keyitem(f"bank:{row['bank_id']}", "clean_match", "close",
                          {"kind": "match", "lines": [], "escalate": False}, "Synced Stripe payout - match, no new entry.")

        # --- festival wire
        fest = rng.choice(bible.FESTIVALS)
        dd = biz(date(YEAR, m, rng.randint(6, 26)))
        amt = rng.randint(800_000, 4_500_000)
        inv = f"AG-INV-{YEAR}-{m:02d}{rng.randint(10, 99)}"
        row = w.bank_row(dd, f"FEDWIRE CREDIT VIA: {fest[1].upper()} B/O: {fest[0].upper()} REF: {inv}", amt,
                         "WIRE_INCOMING", {"kind": "synced_deposit", "invoice": inv})
        w.je(dd, f"Payment received {fest[0]} {inv}", [("1010", amt), ("4020", -amt)], "invoicing",
             {"invoice": inv, **({} if is_close else {"bank_id": row["bank_id"]})}, name=fest[0], txn_type="Payment")
        if is_close:
            w.keyitem(f"bank:{row['bank_id']}", "clean_match", "close",
                      {"kind": "match", "lines": [], "escalate": False}, "Festival wire already recorded from invoicing.")

        # --- Gusto payroll (synced)
        for dd in (biz_back(date(YEAR, m, 15)), biz_back(me)):
            amt = rng.randint(9_200_000, 9_850_000)
            row = w.bank_row(dd, ach_desc("GUSTO", "9138864001", "NET PAY", dd), -amt, "ACH_DEBIT",
                             {"kind": "synced_payroll"})
            w.je(dd, "Payroll (Gusto)", [("6100", amt), ("1010", -amt)], "gusto_sync",
                 {} if is_close else {"bank_id": row["bank_id"]}, name="Gusto", txn_type="Journal Entry")
            if is_close:
                w.keyitem(f"bank:{row['bank_id']}", "clean_match", "close",
                          {"kind": "match", "lines": [], "escalate": False}, "Payroll synced from Gusto.")

        # --- Ramp card statement payment for previous month (paid ~5th)
        prev_total = dec_ramp if m == 1 else month_ramp_total[m - 1]
        dd = biz(date(YEAR, m, 5))
        row = w.bank_row(dd, ach_desc("RAMP", "1474827333", "CARD PMT", dd), -prev_total, "ACH_DEBIT",
                         {"kind": "card_statement_payment"})
        if is_close:
            w.keyitem(f"bank:{row['bank_id']}", "card_statement_payment", "close",
                      {"kind": "card_statement_payment", "lines": [["2050", prev_total], ["1010", -prev_total]],
                       "escalate": False}, "Ramp statement payment for August - relieves Ramp Card Payable.")
        else:
            w.je(dd, "Ramp card statement payment", [("2050", prev_total), ("1010", -prev_total)], "staff_accountant",
                 {"bank_id": row["bank_id"]}, name="Ramp", txn_type="Credit Card Payment")

        # --- AP bills: Anthropic API + AWS, paid ~15th
        for vid, lo, hi, acct, desc_co, oid in (("V-ANTHROPIC", 250_000, 360_000, "6410", "ANTHROPIC PBC", "4510287713"),
                                                 ("V-AWS", 190_000, 265_000, "6450", "AMAZON WEB SERV", "9111146592")):
            amt = rng.randint(lo, hi)
            v = next(x for x in bible.VENDORS if x["id"] == vid)
            b = bill(biz(date(YEAR, m, 2)), vid, amt, f"{v['qbo_name']} usage {YEAR}-{m:02d}", acct,
                     f"{v['qbo_name'][:3].upper()}-{m:02d}{rng.randint(1000, 9999)}", f"{YEAR}-{m:02d}")
            dd = biz(date(YEAR, m, 15) + timedelta(days=rng.choice([0, 1])))
            row = pay_bill(b, dd, ach_desc(desc_co, oid, "BILL PAY", dd), book=not is_close)
            if is_close:
                w.keyitem(f"bank:{row['bank_id']}", "bill_payment", "close",
                          {"kind": "bill_payment", "lines": [["2010", amt], ["1010", -amt]], "escalate": False,
                           "bill_id": b["bill_id"]}, f"ACH pays open bill {b['num']}.")

        # --- Ramp card spend
        n_normal = rng.randint(9, 13)
        mt = 0
        for _ in range(n_normal):
            mer = rng.choice(normal_ramp)
            dd = date(YEAR, m, rng.randint(1, me.day))
            amt = rng.randint(mer[4], mer[5])
            who = rng.choice(people_cards)
            t = ramp_txn(dd, mer[0], mer[1], mer[2], mer[2], mer[3], amt, mer[6], who)
            mt += amt
            if is_close:
                w.keyitem(f"ramp:{t['ramp_id']}", "trap_clean_card", "close",
                          {"kind": "no_action", "lines": [], "escalate": False}, "Ordinary card spend - leave alone.")
        # recurring SaaS on cards
        gw_amt = 67_200 if m < 9 else 75_600     # Google Workspace price increase in September (TRAP)
        t = ramp_txn(date(YEAR, m, 3), "Google Workspace", "GOOGLE *GSUITE_afterglowla", "Google", "Google",
                     "6410", gw_amt, "5734", ("Maya Chen", "1194"))
        mt += gw_amt
        if is_close:
            w.keyitem(f"ramp:{t['ramp_id']}", "trap_price_change", "close",
                      {"kind": "no_action", "lines": [], "escalate": False},
                      "Workspace seat price rose 12.5% - legitimate; note it, don't flag it.")

        # --- monthly bank fee
        row = w.bank_row(me, "MONTHLY SERVICE FEE", -9_500, "FEE_TRANSACTION", {"kind": "bank_fee"})
        if is_close:
            w.keyitem(f"bank:{row['bank_id']}", "bank_fee", "close",
                      {"kind": "bank_fee", "lines": [["6810", 9_500], ["1010", -9_500]], "escalate": False},
                      "Monthly service fee.")
        else:
            w.je(me, "Bank service fee", [("6810", 9_500), ("1010", -9_500)], "staff_accountant",
                 {"bank_id": row["bank_id"]}, name="JPMorgan Chase", txn_type="Expense")

        # --- interest earned this month (accrued at month end; credited on the 1st)
        if exact and m == CLOSE_M:
            interest = 104_217
        else:
            interest = rng.randint(96_000, 109_000)
        interest_by_month[m] = interest
        if is_close:
            notice_id = f"CHASE-INT-{YEAR}{m:02d}"
            w.doc("bank_notice", notice_id, f"Chase interest accrual notice {YEAR}-{m:02d}", me,
                  f"""---
type: bank_notice
issuer: JPMorgan Chase Bank, N.A.
account: Business Complete Checking ...4471
period_start: {YEAR}-{m:02d}-01
period_end: {me.isoformat()}
interest_accrued_cents: {interest}
credit_date: {YEAR}-{m + 1:02d}-01
apy: 0.70%
---
# Interest accrual notice — account ending 4471

Interest accrued {us(date(YEAR, m, 1))} – {us(me)}: **{plain(interest)} USD**.
This amount will be credited to your account on {us(date(YEAR, m + 1, 1))}.
Average collected balance: varies. Annual percentage yield earned: 0.70%.
""", {"issuer": "JPMorgan Chase", "period_end": me.isoformat(), "interest_cents": interest,
      "credit_date": f"{YEAR}-{m + 1:02d}-01"}, "systems/docs/bank")
            w.keyitem(f"interest:{YEAR}-{m:02d}", "interest_accrual", "close",
                      {"kind": "accrual", "lines": [["1260", interest], ["4900", -interest]], "escalate": False},
                      "September interest earned, credited Oct 1 - accrue to Interest Receivable at 9/30.")
        else:
            w.je(me, "Accrue interest earned (credited 1st of next month)", [("1260", interest), ("4900", -interest)],
                 "staff_accountant", {}, txn_type="Journal Entry")
            w.precedent(me, "interest_accrual", f"Accrued {YEAR}-{m:02d} interest {plain(interest)} at month end; "
                        f"credited next month and cleared against 1260.",
                        {"debit": "1260", "credit": "4900", "amount_cents": interest}, "staff_accountant (Dev Patel)")

        # --- bill for the previous month's Lumen work arrives ~8th of this month
        if pending_lumen_bill and pending_lumen_bill["m"] == m - 1:
            pb = pending_lumen_bill
            b = bill(biz(date(YEAR, m, 8)), "V-LUMENCREW", pb["actual"],
                     f"Lumen Crew lighting services {YEAR}-{pb['m']:02d}", "5010", f"LC-{YEAR}-{pb['m']:02d}",
                     f"{YEAR}-{pb['m']:02d}")
            dd = biz(date(YEAR, m, 20))
            row = pay_bill(b, dd, ach_desc("LUMEN CREW LLC", "8340021977", "PAYMENT", dd), book=not is_close)
            if is_close:
                w.keyitem(f"bank:{row['bank_id']}", "bill_payment", "close",
                          {"kind": "bill_payment", "lines": [["2010", pb["actual"]], ["1010", -pb["actual"]]],
                           "escalate": False, "bill_id": b["bill_id"]}, "Pays Lumen's August invoice.")
            pending_lumen_bill = None

        # --- Lumen Crew (lighting) from June: accrue at month end, invoice ~8th next month
        if m >= 6:
            hours = rng.randint(104, 138) if not (exact and is_close) else 130
            rate = 9_500
            est = hours * rate
            if not is_close:
                ratio = rng.uniform(1.09, 1.13)
                actual = int(round(est * ratio / 100.0)) * 100
                w.je(me, f"Accrue Lumen Crew lighting {YEAR}-{m:02d} ({hours}h x $95)", [("5010", est), ("2100", -est)],
                     "staff_accountant", {"vendor": "V-LUMENCREW"})
                lumen_hist.append({"m": m, "hours": hours, "est": est, "actual": actual})
                w.precedent(me, "accrual", f"Lumen Crew {YEAR}-{m:02d}: accrued {plain(est)} (SOW $95/h x {hours}h timesheet); "
                            f"invoice later came in at {plain(actual)} (+{(actual / est - 1) * 100:.1f}%, after-hours premiums).",
                            {"vendor_id": "V-LUMENCREW", "estimate_cents": est, "actual_cents": actual,
                             "method": "contract_rate_x_timesheet", "debit": "5010", "credit": "2100"},
                            "staff_accountant (Dev Patel)", {"vendor_id": "V-LUMENCREW"})
                # reversal on the 1st of next month + invoice/bill + payment
                nd = date(YEAR, m + 1, 1)
                w.je(nd, f"Reverse Lumen Crew accrual {YEAR}-{m:02d}", [("2100", est), ("5010", -est)],
                     "qbo_autoreverse", {"vendor": "V-LUMENCREW"})
                pending_lumen_bill = {"m": m, "actual": actual, "hours": hours}

        month_ramp_total[m] = mt  # updated further below for special txns

        # ======================= HISTORY-SPECIFIC EVENTS =======================
        if m == 2:
            w.precedent(date(YEAR, 2, 12), "vendor_alias", "Ramp merchant 'AWS Marketplace' linked to existing vendor "
                        "Amazon Web Services (same legal entity on invoice). No new vendor created.",
                        {"alias": "AWS Marketplace", "vendor_id": "V-AWS", "evidence": "invoice issuer Amazon Web Services, Inc."},
                        "human_controller (Maya Chen)")
        if m == 3:
            t = ramp_txn(date(YEAR, 3, 14), "Sephora", "SEPHORA #1123 LOS ANGELES", "Sephora", "Sephora", "6430",
                         14_218, "5977", ("Sam Rivera", "3307"))
            month_ramp_total[m] += t["amount"]
            w.je(date(YEAR, 3, 31), "Reclass personal purchase to employee receivable (Sam Rivera) per ruling P-0317",
                 [("1250", 14_218), ("6430", -14_218)], "staff_accountant", {"ramp_id": t["ramp_id"]})
            w.precedent(date(YEAR, 3, 31), "personal", "RULING P-0317 (Controller): personal purchases on company cards "
                        "or PayPal go to 1250 Employee Receivable and the employee is notified - regardless of amount. "
                        "Case: Sephora $142.18 by Sam Rivera on tour.",
                        {"debit": "1250", "credit_original": "6430", "mcc": "5977", "employee": "Sam Rivera",
                         "rule": "P-0317", "personal_mccs": sorted(bible.PERSONAL_MCC),
                         "personal_merchant_keywords": ["sephora", "nordstrom", "macy", "steam", "valve", "playstation",
                                                        "nintendo", "ulta"]}, "human_controller (Maya Chen)", {"ramp_id": t["ramp_id"]})
            # Damlicht Amsterdam show in March (EUR, same month -> expense)
            dd = date(YEAR, 3, 9)
            pay, paid, mkt, ppr = eur_payment(dd, "V-DAMLICHT", 160_000, 0.041, "Crew fee Amsterdam 21 Mar")
            f = paypal_funding(dd, paid, pay["txn_id"])
            row = w.bank_row(dd, f"PAYPAL INST XFER {f['txn_id'][:10]} WEB ID: PAYPALSI77", -paid, "ACH_DEBIT",
                             {"kind": "paypal_funding"})
            w.je(dd, "PayPal: Damlicht Crew Amsterdam show (EUR 1,600.00)",
                 [("5010", mkt), ("6810", paid - mkt), ("1010", -paid)], "staff_accountant",
                 {"bank_id": row["bank_id"], "paypal": pay["txn_id"]}, name="Damlicht Crew B.V.")
            w.precedent(dd, "fx_fee", f"EUR 1,600 to Damlicht booked at ECB {w.market(dd)} = {plain(mkt)}; PayPal charged "
                        f"{plain(paid)} at {ppr}; difference {plain(paid - mkt)} to 6810 Bank & FX Fees.",
                        {"expense_acct": "5010", "fee_acct": "6810", "spread": round(ppr / w.market(dd) - 1, 4)},
                        "staff_accountant (Dev Patel)")
        if m == 4:
            w.precedent(date(YEAR, 4, 30), "controller_correction", "Strobe & Co accrual proposed at contract $3,000; "
                        "Controller corrected to $2,700: vendor confirmed a 10% loyalty discount by phone. "
                        "Lesson: when a freelancer/vendor confirms a different amount, accrue the confirmed amount.",
                        {"vendor_id": "V-STROBE", "proposed_cents": 300_000, "corrected_cents": 270_000, "tag": "verbal_discount"},
                        "human_controller (Maya Chen)")
            w.je(date(YEAR, 4, 30), "Accrue Strobe & Co Apr show (confirmed discounted amount)",
                 [("5010", 270_000), ("2100", -270_000)], "staff_accountant", {"vendor": "V-STROBE"})
            w.je(date(YEAR, 5, 1), "Reverse Strobe & Co Apr accrual", [("2100", 270_000), ("5010", -270_000)],
                 "qbo_autoreverse", {"vendor": "V-STROBE"})
            b = bill(date(YEAR, 5, 6), "V-STROBE", 270_000, "Strobe & Co - April show", "5010", "SC-0412", "2026-04")
            pay_bill(b, biz(date(YEAR, 5, 22)), ach_desc("STROBE AND CO", "8211033901", "PAYMENT", biz(date(YEAR, 5, 22))))
        if m == 5:
            w.precedent(date(YEAR, 5, 9), "vendor_alias", "Ramp merchant 'Google Workspace' linked to existing vendor "
                        "Google (invoice issuer Google LLC). Product name is not a vendor.",
                        {"alias": "Google Workspace", "vendor_id": "V-GOOGLE", "evidence": "invoice issuer Google LLC"},
                        "human_controller (Maya Chen)")
            # Kraftwerk deposit for July Berlin show + Splice, one PayPal funding transfer (split precedent)
            dd = date(YEAR, 5, 19)
            pay, paid, mkt, ppr = eur_payment(dd, "V-KRAFTWERK", 240_000, 0.043, "Deposit rigging Berlin 18 Jul")
            sp = paypal_payment(dd, "Splice.com, Inc.", "billing@splice.com", "Splice Sounds subscription", 2_499,
                                "USD", "PreApproved Payment Bill User Payment")
            f = paypal_funding(dd, paid + 2_499, pay["txn_id"])
            row = w.bank_row(dd, f"PAYPAL INST XFER {f['txn_id'][:10]} WEB ID: PAYPALSI77", -(paid + 2_499), "ACH_DEBIT",
                             {"kind": "paypal_funding"})
            w.je(dd, "PayPal transfer split: Kraftwerk deposit (Jul show) + Splice",
                 [("1310", mkt), ("6810", paid - mkt), ("6410", 2_499), ("1010", -(paid + 2_499))],
                 "staff_accountant", {"bank_id": row["bank_id"]}, name="PayPal")
            w.precedent(dd, "paypal_split", "One PayPal instant transfer funded two PayPal payments (Kraftwerk EUR deposit "
                        "+ Splice subscription). Split to the underlying payments instead of booking 'PayPal'.",
                        {"funding_ref": f["txn_id"], "n_payments": 2}, "staff_accountant (Dev Patel)")
            w.precedent(dd, "prepaid_deposit", "Kraftwerk deposit paid in May for the 18 Jul Berlin show booked to 1310 "
                        "Prepaid Tour Costs; expensed to 5010 in July when the show happened.",
                        {"vendor_id": "V-KRAFTWERK", "debit": "1310"}, "staff_accountant (Dev Patel)")
            w.precedent(dd, "fx_fee", f"EUR 2,400 Kraftwerk deposit at ECB {w.market(dd)}; PayPal spread {plain(paid - mkt)} -> 6810.",
                        {"expense_acct": "1310", "fee_acct": "6810", "spread": round(ppr / w.market(dd) - 1, 4)},
                        "staff_accountant (Dev Patel)")
            w._kraft_may = mkt
        if m in (6, 7, 8) and m != 5:
            # Splice monthly via PayPal from balance (payee name 'Splice.com, Inc.')
            dd = date(YEAR, m, 19)
            sp = paypal_payment(dd, "Splice.com, Inc.", "billing@splice.com", "Splice Sounds subscription", 2_499, "USD",
                                "PreApproved Payment Bill User Payment")
            w.je(dd, "Splice subscription (PayPal balance)", [("6410", 2_499), ("1030", -2_499)], "staff_accountant",
                 {"paypal": sp["txn_id"]}, name="Splice")
        if m == 6:
            dd = date(YEAR, 6, 11)
            gp = paypal_payment(dd, "Valve Corporation", "noreply@steampowered.com", "Steam purchase", 5_999, "USD",
                                "Express Checkout Payment", from_email="j.ortiz@afterglowlabs.com")
            w.je(dd, "Personal purchase via company PayPal (J. Ortiz) -> employee receivable per P-0317",
                 [("1250", 5_999), ("1030", -5_999)], "staff_accountant", {"paypal": gp["txn_id"]}, name="J. Ortiz")
            w.precedent(dd, "personal", "Steam purchase $59.99 on company PayPal by J. Ortiz -> 1250 Employee "
                        "Receivable per P-0317; employee notified and repaid via payroll deduction.",
                        {"debit": "1250", "mcc": "5816", "employee": "J. Ortiz", "rule": "P-0317"},
                        "staff_accountant (Dev Patel)")
            dd = date(YEAR, 6, 8)
            pay, paid, mkt, ppr = eur_payment(dd, "V-DAMLICHT", 185_000, 0.039, "Crew fee Amsterdam 20 Jun")
            f = paypal_funding(dd, paid, pay["txn_id"])
            row = w.bank_row(dd, f"PAYPAL INST XFER {f['txn_id'][:10]} WEB ID: PAYPALSI77", -paid, "ACH_DEBIT",
                             {"kind": "paypal_funding"})
            w.je(dd, "PayPal: Damlicht Crew (EUR 1,850.00)", [("5010", mkt), ("6810", paid - mkt), ("1010", -paid)],
                 "staff_accountant", {"bank_id": row["bank_id"]}, name="Damlicht Crew B.V.")
            w.precedent(dd, "fx_fee", f"EUR 1,850 Damlicht at ECB {w.market(dd)}; spread {plain(paid - mkt)} -> 6810.",
                        {"expense_acct": "5010", "fee_acct": "6810", "spread": round(ppr / w.market(dd) - 1, 4)},
                        "staff_accountant (Dev Patel)")
        if m == 7:
            w.je(date(YEAR, 7, 18), "Berlin show held: release Kraftwerk deposit from prepaid",
                 [("5010", w._kraft_may), ("1310", -w._kraft_may)], "staff_accountant", {"vendor": "V-KRAFTWERK"})
            w.precedent(date(YEAR, 7, 31), "controller_correction", "Nadia Kroll (VJ) accrual proposed at SOW $2,500; "
                        "Controller corrected to $2,250 because Nadia texted she would bill $2,250. "
                        "Lesson: accrue the amount the freelancer confirmed.",
                        {"vendor_id": "V-NADIA", "proposed_cents": 250_000, "corrected_cents": 225_000, "tag": "verbal_discount"},
                        "human_controller (Maya Chen)")
            w.je(date(YEAR, 7, 31), "Accrue Nadia Kroll VJ Jul show (confirmed amount)", [("5010", 225_000), ("2100", -225_000)],
                 "staff_accountant", {"vendor": "V-NADIA"})
            w.je(date(YEAR, 8, 1), "Reverse Nadia Kroll Jul accrual", [("2100", 225_000), ("5010", -225_000)],
                 "qbo_autoreverse", {"vendor": "V-NADIA"})
            b = bill(date(YEAR, 9, 16) if False else date(YEAR, 8, 30), "V-NADIA", 225_000, "Nadia Kroll - VJ July show",
                     "5010", "NK-07", "2026-07")
            w._nadia_jul_bill = b
        if m == 8:
            dd = date(YEAR, 8, 7)
            pay, paid, mkt, ppr = eur_payment(dd, "V-DAMLICHT", 140_000, 0.040, "Crew fee Amsterdam 15 Aug")
            f = paypal_funding(dd, paid, pay["txn_id"])
            row = w.bank_row(dd, f"PAYPAL INST XFER {f['txn_id'][:10]} WEB ID: PAYPALSI77", -paid, "ACH_DEBIT",
                             {"kind": "paypal_funding"})
            w.je(dd, "PayPal: Damlicht Crew (EUR 1,400.00)", [("5010", mkt), ("6810", paid - mkt), ("1010", -paid)],
                 "staff_accountant", {"bank_id": row["bank_id"]}, name="Damlicht Crew B.V.")
            w.precedent(dd, "fx_fee", f"EUR 1,400 Damlicht at ECB {w.market(dd)}; spread {plain(paid - mkt)} -> 6810.",
                        {"expense_acct": "5010", "fee_acct": "6810", "spread": round(ppr / w.market(dd) - 1, 4)},
                        "staff_accountant (Dev Patel)")
            # Bay Rig original gear rental on Ramp (refund comes in September)
            t = ramp_txn(date(YEAR, 8, 21), "Bay Rig Rentals", "BAYRIG RENTALS OAKLAND", "Bay Rig Rentals",
                         "Bay Rig Rentals", "5020", 168_000, "7394", ("J. Ortiz", "8812"), memo="Truss + motors Aug 22-24")
            month_ramp_total[m] += t["amount"]
            w._bayrig_aug = t
            # Nadia July bill paid late Aug from bank
            pay_bill(w._nadia_jul_bill, date(YEAR, 8, 31) if date(YEAR, 8, 31).weekday() < 5 else biz_back(date(YEAR, 8, 31)),
                     ach_desc("NADIA KROLL", "0000000000", "PAYMENT", date(YEAR, 8, 28)))
            w.precedent(date(YEAR, 8, 30), "vendor_slow", "Nadia Kroll invoiced July's show 30 days late (Aug 30) and "
                        "February's show 47 days late. Expect late or missing invoices.",
                        {"vendor_id": "V-NADIA", "days_late": [47, 30]}, "staff_accountant (Dev Patel)")

        # ======================= SEPTEMBER (THE CLOSE) =======================
        if is_close:
            sep_extra = 0
            # (1) THE MOMENT: one PayPal instant transfer funding 3 payments
            dd = date(YEAR, 9, 18)
            if exact:
                eur, spread_rate = 295_000, None
                pp_rate = 1.2200
                v = next(x for x in bible.VENDORS if x["id"] == "V-KRAFTWERK")
                pay = paypal_payment(dd, v["legal"], "billing@kraftwerk-rigging.de", "Deposit rigging Berlin 14 Nov",
                                     eur, "EUR", "General Payment")
                paid, mkt = mul_rate(eur, pp_rate), mul_rate(eur, w.market(dd))
                paypal_conversion(dd, pay, paid, eur)
                claude_amt, game_amt = 20_000, 11_344
            else:
                eur = rng.choice([250_000, 275_000, 295_000, 320_000])
                pay, paid, mkt, pp_rate = eur_payment(dd, "V-KRAFTWERK", eur, rng.uniform(0.035, 0.045),
                                                      "Deposit rigging Berlin 14 Nov")
                claude_amt, game_amt = 20_000, rng.randint(4_999, 14_999)
            cl = paypal_payment(dd, "Anthropic, PBC", "billing@anthropic.com", "Claude Max subscription", claude_amt,
                                "USD", "PreApproved Payment Bill User Payment")
            gm = paypal_payment(dd, "Valve Corporation", "noreply@steampowered.com", "Steam purchase", game_amt, "USD",
                                "Express Checkout Payment", from_email="j.ortiz@afterglowlabs.com")
            total = paid + claude_amt + game_amt
            f = paypal_funding(dd, total, pay["txn_id"])   # NB: links only the FIRST payment (realistic partial linkage)
            row = w.bank_row(dd, f"PAYPAL INST XFER {f['txn_id'][:10]} WEB ID: PAYPALSI77", -total, "ACH_DEBIT",
                             {"kind": "paypal_funding"})
            w.moment_bank_id = row["bank_id"]
            w.keyitem(f"bank:{row['bank_id']}", "paypal_bundle_prepaid_fx_personal_alias", "close",
                      {"kind": "paypal_split", "escalate": False,
                       "lines": [["1310", mkt], ["6810", paid - mkt], ["6410", claude_amt], ["1250", game_amt],
                                 ["1010", -total]],
                       "vendors": {"Anthropic, PBC": "V-ANTHROPIC"}},
                      "THE MOMENT: bank-feed rule says 'PayPal - Software Expense'. Truth: Nov show deposit (prepaid) + FX "
                      "fee + Claude subscription (vendor Anthropic) + personal Steam purchase (employee receivable).")
            # SOW that proves the deposit is for November
            w.doc("sow", "SOW-KRW-2026-11", "Kraftwerk Rigging - SOW Berlin 14 Nov 2026", date(YEAR, 9, 2), f"""---
type: sow
vendor: Kraftwerk Rigging GmbH
vendor_domain: kraftwerk-rigging.de
client: Afterglow Labs, Inc.
service: Rigging crew and motors, Berlin show
service_date: 2026-11-14
currency: EUR
total: 9800.00
deposit: {eur / 100:.2f}
deposit_due: 2026-09-18
---
# Statement of Work — Rigging, Berlin (14 November 2026)

Kraftwerk Rigging GmbH will provide a 6-person rigging crew, 12 chain motors and load-in/out for
Afterglow Live at Kraftwerk Berlin on **14 November 2026**.

Fees: EUR 9,800.00 total. A deposit of EUR {eur / 100:,.2f} is due 18 September 2026 via PayPal;
the balance is due 7 days after the show. Cancellation within 30 days forfeits the deposit.
""", {"vendor": "Kraftwerk Rigging GmbH", "service_date": "2026-11-14", "deposit_cents": eur, "currency": "EUR"},
                  "systems/docs/contracts")

            # (2) PayPal transfer: Damlicht September show (EUR, expense) + Splice under new payee name
            dd = date(YEAR, 9, 9)
            d_eur = 180_000 if exact else rng.choice([150_000, 180_000, 210_000])
            pay2, paid2, mkt2, ppr2 = eur_payment(dd, "V-DAMLICHT", d_eur, 0.04 if exact else rng.uniform(0.035, 0.045),
                                                  "Crew fee Amsterdam 13 Sep")
            sp = paypal_payment(dd, "Splice.com", "billing@splice.com", "Splice Sounds subscription", 2_499, "USD",
                                "PreApproved Payment Bill User Payment")
            f2 = paypal_funding(dd, paid2 + 2_499, "")
            row = w.bank_row(dd, f"PAYPAL INST XFER {f2['txn_id'][:10]} WEB ID: PAYPALSI77", -(paid2 + 2_499), "ACH_DEBIT",
                             {"kind": "paypal_funding"})
            w.keyitem(f"bank:{row['bank_id']}", "paypal_bundle_fx_alias", "close",
                      {"kind": "paypal_split", "escalate": False,
                       "lines": [["5010", mkt2], ["6810", paid2 - mkt2], ["6410", 2_499], ["1010", -(paid2 + 2_499)]]},
                      "Damlicht show was in September -> expense (not prepaid); Splice payee renamed 'Splice.com'.")
            w.doc("run_sheet", "ROS-AMS-2026-09-13", "Run of show - Amsterdam 13 Sep", date(YEAR, 9, 13), """---
type: run_sheet
event: Afterglow Live @ Paradiso Amsterdam
event_date: 2026-09-13
crew: [Damlicht Crew B.V. (6), J. Ortiz (TM)]
---
# Run of show — Amsterdam, 13 Sep 2026
Load-in 14:00 · Doors 21:00 · Show 22:30–00:30 · Load-out 01:00. Crew: Damlicht Crew B.V. (6 pax).
""", {"event_date": "2026-09-13", "crew": ["Damlicht Crew B.V."]}, "systems/docs/ops")

            # (3) PayPal top-up with no payment in the window -> balance-sheet transfer
            dd = date(YEAR, 9, 24)
            f3 = paypal_funding(dd, 100_000, "")
            row = w.bank_row(dd, f"PAYPAL INST XFER {f3['txn_id'][:10]} WEB ID: PAYPALSI77", -100_000, "ACH_DEBIT",
                             {"kind": "paypal_funding"})
            w.keyitem(f"bank:{row['bank_id']}", "transfer_not_expense", "close",
                      {"kind": "transfer", "lines": [["1030", 100_000], ["1010", -100_000]], "escalate": False},
                      "Top-up of PayPal balance - a transfer between our own accounts, not an expense.")
            # ...and a later payment out of the PayPal balance (the actual expense)
            dd = date(YEAR, 9, 26)
            kai_amt = 64_000
            kp = paypal_payment(dd, "Kai Mendes", "kai@kaimendes.art", "VJ assist - Oakland 25 Sep", kai_amt, "USD",
                                "General Payment")
            w.keyitem(f"paypal:{kp['txn_id']}", "paypal_balance_payment", "close",
                      {"kind": "paypal_payment", "lines": [["5010", kai_amt], ["1030", -kai_amt]], "escalate": False},
                      "Payment from PayPal balance (not in bank feed) - easy to miss entirely.")
            w.doc("run_sheet", "ROS-OAK-2026-09-25", "Run of show - Oakland 25 Sep", date(YEAR, 9, 25), """---
type: run_sheet
event: Afterglow Live @ Fox Theater Oakland
event_date: 2026-09-25
crew: [Lumen Crew LLC (lighting), Kai Mendes (VJ assist), Nadia Kroll (VJ)]
---
# Run of show — Oakland, 25 Sep 2026
Lighting: Lumen Crew LLC. VJ: Nadia Kroll, assisted by Kai Mendes. Stagehand (cash/Zelle): R. Lopez.
""", {"event_date": "2026-09-25", "crew": ["Lumen Crew LLC", "Kai Mendes", "Nadia Kroll", "R. Lopez"]}, "systems/docs/ops")

            # (4) Unknown Zelle -> must ask
            dd = date(YEAR, 9, 26)
            zrow = w.bank_row(dd, f"Zelle payment to R Lopez JPM99{md5(str(seed))[:6]}", -35_000, "QUICKPAY_DEBIT",
                              {"kind": "unknown"})
            w.zelle_bank_id = zrow["bank_id"]
            w.keyitem(f"bank:{zrow['bank_id']}", "unknown_ask", "close",
                      {"kind": "ask", "lines": [], "escalate": True,
                       "after_answer_lines": [["5010", 35_000], ["1010", -35_000]]},
                      "No invoice, no vendor record. The run sheet hints at a stagehand, but someone must confirm - ask.")

            # (5) Ramp: alias vendors, duplicate, personal, refund, trap
            def sep_ramp(*a, **k):
                nonlocal sep_extra
                t = ramp_txn(*a, **k)
                sep_extra += t["amount"]
                return t

            t = sep_ramp(date(YEAR, 9, 2), "Claude", "CLAUDE.AI SUBSCRIPTION", "Claude", "", "6410", 15_000, "5734",
                         ("Lee Okafor", "5521"), memo="Claude Pro team seats")
            w.keyitem("vendor:Claude", "vendor_alias", "close",
                      {"kind": "vendor_link", "vendor_id": "V-ANTHROPIC", "escalate": False},
                      "Ramp suggests new vendor 'Claude' - it is Anthropic, PBC (receipt issuer).")
            t = sep_ramp(date(YEAR, 9, 4), "Cursor", "CURSOR AI POWERED IDE", "Cursor", "", "6410", 48_000, "5734",
                         ("Lee Okafor", "5521"), memo="Cursor Business Sept")
            cursor_ramp = t
            w.keyitem("vendor:Cursor", "vendor_alias", "close",
                      {"kind": "vendor_link", "vendor_id": "V-ANYSPHERE", "escalate": False},
                      "Ramp 'Cursor' is Anysphere, Inc.")
            b = bill(date(YEAR, 9, 6), "V-ANYSPHERE", 48_000, "Anysphere - Cursor Business Sept", "6410",
                     "INV-ANY-0926", "2026-09")
            w.keyitem(f"bill:{b['bill_id']}", "duplicate_two_systems", "close",
                      {"kind": "duplicate", "lines": [["2010", 48_000], ["6410", -48_000]], "escalate": False,
                       "duplicate_of": f"ramp:{cursor_ramp['ramp_id']}"},
                      "Same Cursor charge entered as an AP bill AND synced from Ramp -> expense counted twice. Void the bill.")
            t = sep_ramp(date(YEAR, 9, 8), "Google Ads", "GOOGLE *ADS4471029388", "Google Ads", "", "6420", 125_000,
                         "7311", ("Sam Rivera", "3307"), memo="Fall tour promo")
            w.keyitem("vendor:Google Ads", "vendor_alias", "close",
                      {"kind": "vendor_link", "vendor_id": "V-GOOGLE", "escalate": False}, "Google Ads is Google LLC.")
            t = sep_ramp(date(YEAR, 9, 12), "Lumen Studios", "LUMEN STUDIOS SF", "Lumen Studios", "", "6420", 60_000,
                         "7333", ("Sam Rivera", "3307"), memo="Promo photo shoot studio rental")
            w.keyitem("vendor:Lumen Studios", "trap_similar_vendor", "close",
                      {"kind": "vendor_create", "escalate": False, "not_vendor_id": "V-LUMENCREW"},
                      "TRAP: name looks like Lumen Crew LLC but it's a different legal entity (photo studio). Create, don't merge.")
            pers = ("Nordstrom", "NORDSTROM #0412 SEATTLE", "5651") if (exact or rng.random() < .5) else \
                ("Macy's", "MACYS .COM", "5311")
            p_amt = 28_640 if exact else rng.randint(8_000, 32_000)
            t = sep_ramp(date(YEAR, 9, 21), pers[0], pers[1], pers[0], pers[0], "6430", p_amt, pers[2],
                         ("J. Ortiz", "8812"), memo="", receipt=False, category_label="Travel")
            w.keyitem(f"ramp:{t['ramp_id']}", "personal_card", "close",
                      {"kind": "reclass", "lines": [["1250", p_amt], ["6430", -p_amt]], "escalate": False},
                      "Department store on tour, no receipt, no memo -> personal per P-0317.")
            t = sep_ramp(date(YEAR, 9, 22), "Guitar Center", "GUITAR CENTER #219 SEATTLE", "Guitar Center", "Guitar Center",
                         "5030", 38_900, "5733", ("Sam Rivera", "3307"), memo="DI boxes + XLR for Seattle")
            w.keyitem(f"ramp:{t['ramp_id']}", "trap_looks_personal", "close",
                      {"kind": "no_action", "lines": [], "escalate": False},
                      "TRAP: music store on tour looks personal, but it's show gear with a memo + receipt.")
            t = ramp_txn(date(YEAR, 9, 23), "Bay Rig Rentals", "BAYRIG RENTALS OAKLAND", "Bay Rig Rentals",
                         "Bay Rig Rentals", "4950", -42_000, "7394", ("J. Ortiz", "8812"),
                         memo="Refund - 1 motor unused Aug 22-24", category_label="Other Income")
            sep_extra += t["amount"]
            w.keyitem(f"ramp:{t['ramp_id']}", "refund_misclassified", "close",
                      {"kind": "reclass", "lines": [["4950", 42_000], ["5020", -42_000]], "escalate": False},
                      "Vendor refund booked as income; it should reduce the original Gear Rental expense.")
            month_ramp_total[m] += sep_extra
            for rv, info in bible.RAMP_SUGGESTED_VENDORS.items():
                tin = info.get("tin", "")
                w.doc("receipt", f"RCPT-{md5(rv)[:6].upper()}", f"Receipt attached in Ramp - {rv}", date(YEAR, 9, 12), f"""---
type: receipt
ramp_merchant: {rv}
issuer: {info['receipt_issuer']}
issuer_domain: {info['domain']}
issuer_tin: {tin}
---
# Receipt — {info['receipt_issuer']} ({info['domain']})
Merchant shown on card statement: {rv}. Billed to Afterglow Labs, Inc.
""", {"ramp_merchant": rv, "issuer": info["receipt_issuer"], "domain": info["domain"], "tin": tin},
                      "systems/docs/receipts")
            w.keyitem("vendor:Kai Mendes", "new_vendor", "close",
                      {"kind": "vendor_create", "escalate": False},
                      "New freelance payee on PayPal - create a vendor record (Controller approves).")

            # (6) Accruals at Sept 30 ------------------------------------------
            # Lumen Crew: SOW + timesheet + vague email; invoice arrives Oct 8 (later phase)
            w.doc("sow", "SOW-LUMEN-2026", "Lumen Crew LLC - Master SOW 2026", date(YEAR, 5, 28), """---
type: sow
vendor: Lumen Crew LLC
vendor_domain: lumencrew.co
service: Lighting design + crew, Bay Area shows
rate_per_hour: 95.00
billing: monthly in arrears, invoice by the 10th
term: 2026-06-01 to 2026-12-31
---
# Master SOW — Lighting crew (Lumen Crew LLC)
Hourly rate USD 95.00 per crew-hour, billed monthly in arrears against approved timesheets.
After-hours load-out (after 1:00 am) billed at 1.5x.
""", {"vendor": "Lumen Crew LLC", "rate_cents": 9_500, "term_start": "2026-06-01", "term_end": "2026-12-31"},
                  "systems/docs/contracts")
            l_hours = 130 if exact else rng.randint(110, 140)
            w.doc("timesheet", "TS-LUMEN-2026-09", "Lumen Crew timesheet - September 2026", date(YEAR, 9, 30), f"""---
type: timesheet
vendor: Lumen Crew LLC
period: 2026-09
approved_by: J. Ortiz
approved_on: 2026-10-01
total_hours: {l_hours}
---
| date | event | crew-hours |
|---|---|---|
| 2026-09-05 | SF Mezzanine | {l_hours // 3} |
| 2026-09-19 | Oakland warehouse | {l_hours // 3} |
| 2026-09-25 | Fox Theater Oakland | {l_hours - 2 * (l_hours // 3)} |
| **total** | | **{l_hours}** |
""", {"vendor": "Lumen Crew LLC", "period": "2026-09", "hours": l_hours, "approved": True},
                  "systems/docs/timesheets", ext="md")
            w.doc("email", "EML-LUMEN-0929", "Re: September invoice timing", date(YEAR, 9, 29), """From: ops@lumencrew.co
To: ap@afterglowlabs.com
Date: Tue, 29 Sep 2026 17:12:04 -0700
Subject: Re: September invoice timing

Hey! We're slammed with load-outs this week - September should land around 10k, give or take.
Invoice by the 10th like usual.
- Rae, Lumen Crew
""", {"vendor": "Lumen Crew LLC", "estimate_cents": 1_000_000, "informal": True}, "systems/docs/email", ext="eml")
            l_est = l_hours * 9_500
            w.keyitem("accrual:V-LUMENCREW:2026-09", "accrual_sources_disagree", "close",
                      {"kind": "accrual", "lines": [["5010", l_est], ["2100", -l_est]], "escalate": False},
                      "SOW rate x approved timesheet beats the vendor's 'around 10k' email (policy 4b > 4d).")
            # Nadia: flat SOW, run sheet proves performance, no invoice, chronically late -> accrue + ask vendor
            w.doc("sow", "SOW-NADIA-2026-09", "Nadia Kroll - VJ booking 25 Sep", date(YEAR, 9, 1), """---
type: sow
vendor: Nadia Kroll
vendor_domain: nadiakroll.studio
service: VJ performance, Fox Theater Oakland
service_date: 2026-09-25
fee: 2500.00
---
# Booking confirmation — VJ, Fox Theater Oakland (25 Sep 2026)
Flat fee USD 2,500.00. Invoice after the show.
""", {"vendor": "Nadia Kroll", "service_date": "2026-09-25", "fee_cents": 250_000}, "systems/docs/contracts")
            w.keyitem("accrual:V-NADIA:2026-09", "accrual_no_invoice_ask", "close",
                      {"kind": "accrual", "lines": [["5010", 250_000], ["2100", -250_000]], "escalate": True},
                      "Performance proven by run sheet; no invoice; vendor chronically late -> accrue SOW fee and ask her to confirm.")
            # Bay Rig: invoice dated Oct 3 for Sept service (received Oct 3, not yet entered)
            br_amt = 360_000
            w.doc("invoice", "BR-20871", "Bay Rig Rentals invoice BR-20871", date(YEAR, 10, 3), f"""---
type: invoice
vendor: Bay Rig Rentals Inc.
vendor_domain: bayrig.com
invoice_number: BR-20871
invoice_date: 2026-10-03
service_period_start: 2026-09-20
service_period_end: 2026-09-27
amount: {br_amt / 100:.2f}
currency: USD
terms: Net 30
---
# INVOICE BR-20871 — Bay Rig Rentals Inc.
Bill to: Afterglow Labs, Inc. · Service: truss, 8x 1-ton motors, delivery — **Sept 20–27, 2026**
Total due: USD {br_amt / 100:,.2f} · Terms Net 30
""", {"vendor": "Bay Rig Rentals Inc.", "invoice_date": "2026-10-03", "service_start": "2026-09-20",
      "service_end": "2026-09-27", "amount_cents": br_amt}, "systems/docs/invoices")
            w.keyitem("accrual:V-BAYRIG:2026-09", "accrual_invoice_after_period", "close",
                      {"kind": "accrual", "lines": [["5020", br_amt], ["2100", -br_amt]], "escalate": False},
                      "Invoice dated Oct 3 but the service was Sept 20-27 -> September expense.")
            # TRAP: Strobe & Co SOW for an October show -> no September accrual
            w.doc("sow", "SOW-STROBE-2026-10", "Strobe & Co - SOW 10 Oct show", date(YEAR, 9, 15), """---
type: sow
vendor: Strobe & Co
vendor_domain: strobeandco.com
service: Strobe/laser package, Portland
service_date: 2026-10-10
fee: 3000.00
---
# SOW — Strobe & laser package, Portland (10 October 2026). Flat fee USD 3,000.00.
""", {"vendor": "Strobe & Co", "service_date": "2026-10-10", "fee_cents": 300_000}, "systems/docs/contracts")
            w.keyitem("accrual:V-STROBE:2026-09", "trap_future_service", "close",
                      {"kind": "no_action", "lines": [], "escalate": False},
                      "TRAP: signed SOW but the service is in October - nothing to accrue in September.")

            # (7) vendor link for PayPal payee 'Splice.com'
            w.keyitem("vendor:Splice.com", "vendor_alias", "close",
                      {"kind": "vendor_link", "vendor_id": "V-SPLICE", "escalate": False},
                      "PayPal payee renamed to 'Splice.com' - same Splice.com, Inc.")
            w.close_ramp_total = month_ramp_total[m]

    # ======================= OCTOBER ARRIVALS (late) =======================
    est = (130 if exact else next(d for d in w.docs if d["doc_id"] == "TS-LUMEN-2026-09")["fields"]["hours"]) * 9_500
    hours = est // 9_500
    premium = 67_000
    actual = est + premium
    w.doc("invoice", "LC-2026-09", "Lumen Crew invoice LC-2026-09", date(YEAR, 10, 8), f"""---
type: invoice
vendor: Lumen Crew LLC
vendor_domain: lumencrew.co
invoice_number: LC-2026-09
invoice_date: 2026-10-08
service_period_start: 2026-09-01
service_period_end: 2026-09-30
amount: {actual / 100:.2f}
currency: USD
---
# INVOICE LC-2026-09 — Lumen Crew LLC
| line | qty | rate | amount |
|---|---|---|---|
| Lighting crew-hours (Sept) | {hours} | 95.00 | {est / 100:,.2f} |
| After-hours load-out premium (Fox Theater, 25 Sep) | 1 | 670.00 | 670.00 |
| **Total** | | | **{actual / 100:,.2f}** |
""", {"vendor": "Lumen Crew LLC", "invoice_date": "2026-10-08", "service_start": "2026-09-01",
      "service_end": "2026-09-30", "amount_cents": actual}, "arrivals/2026-10-late/docs/invoices", arrival="october")
    w.october_bills = [
        {"bill_id": "BILL-OCT-LC", "vendor_id": "V-LUMENCREW", "vendor": "Lumen Crew LLC", "date": "2026-10-08",
         "entered": "2026-10-09", "amount": actual, "num": "LC-2026-09", "memo": "Lumen Crew lighting services 2026-09",
         "acct": "5010", "service_period": "2026-09", "doc_id": "LC-2026-09"},
        {"bill_id": "BILL-OCT-BR", "vendor_id": "V-BAYRIG", "vendor": "Bay Rig Rentals", "date": "2026-10-03",
         "entered": "2026-10-07", "amount": 360_000, "num": "BR-20871", "memo": "Bay Rig Rentals truss/motors Sep 20-27",
         "acct": "5020", "service_period": "2026-09", "doc_id": "BR-20871"},
    ]
    w.keyitem("trueup:V-LUMENCREW:2026-09", "accrual_trueup", "october",
              {"kind": "accrual_reversal", "accrued_cents": est, "actual_cents": actual, "trueup_cents": premium,
               "lines": [["2100", est], ["5010", -est]], "escalate": False},
              "Invoice is $670 over the accrual (after-hours premium, SOW 1.5x clause): reverse the accrual against "
              "the bill; October carries the $670 true-up.")
    w.keyitem("trueup:V-BAYRIG:2026-09", "accrual_reversal", "october",
              {"kind": "accrual_reversal", "accrued_cents": 360_000, "actual_cents": 360_000, "trueup_cents": 0,
               "lines": [["2100", 360_000], ["5020", -360_000]], "escalate": False},
              "Bay Rig bill entered in October for the accrued amount -> reverse the accrual, zero true-up.")
    w.keyitem("aging:V-NADIA:2026-09", "invoice_never_received", "october",
              {"kind": "ask", "lines": [], "escalate": True},
              "Still no invoice from Nadia - keep the accrual, chase again, escalate aging.")

    # attach "arrival" to records dated in late October
    for r in w.bank:
        r["arrival"] = "october" if r["date"] >= LATE_OCT_FROM else "initial"
    return w


# =============================================================================
#                                  WRITERS
# =============================================================================
def _write_csv(path: Path, header: list[str], rows: list[list]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        wr = csv.writer(fh)
        wr.writerow(header)
        wr.writerows(rows)


def write(w: World, out: Path):
    if out.exists():
        shutil.rmtree(out)
    sysdir = out / "systems"

    # ---- bank (Chase): newest first, like the real export; running balance
    opening_cash = 185_000_000
    bank_sorted = sorted(w.bank, key=lambda r: (r["post_date"], r["bank_id"]))
    bal = opening_cash
    for r in bank_sorted:
        bal += r["amount"]
        r["balance"] = bal
    # monthly statements (beginning/ending balance) - the evidence a reconciliation ties to
    stmts = {}
    beg = opening_cash
    for mon in sorted({period(r["post_date"]) for r in bank_sorted}):
        rows = [r for r in bank_sorted if period(r["post_date"]) == mon]
        end = rows[-1]["balance"]
        stmts[mon] = {"period": mon, "beginning_cents": beg, "ending_cents": end,
                      "deposits_cents": sum(r["amount"] for r in rows if r["amount"] > 0),
                      "withdrawals_cents": sum(r["amount"] for r in rows if r["amount"] < 0), "n": len(rows)}
        beg = end
    (sysdir / "bank" / "statements").mkdir(parents=True, exist_ok=True)
    for mon, st in stmts.items():
        if mon > "2026-09":
            continue
        (sysdir / "bank" / "statements" / f"chase_x4471_{mon}_statement.md").write_text(
            f"# JPMorgan Chase - Business Complete Checking ...4471\n\nStatement period: {mon}\n\n"
            f"| | USD |\n|---|---:|\n| Beginning balance | {plain(st['beginning_cents'])} |\n"
            f"| Deposits and additions | {plain(st['deposits_cents'])} |\n"
            f"| Withdrawals and debits | {plain(st['withdrawals_cents'])} |\n"
            f"| **Ending balance** | **{plain(st['ending_cents'])}** |\n\nTransactions: {st['n']}\n")
    (sysdir / "bank" / "statements" / "statements.json").write_text(
        json.dumps({k: v for k, v in stmts.items() if k <= "2026-09"}, indent=1))

    for arrival in ("initial", "october"):
        by_month: dict[str, list] = {}
        for r in bank_sorted:
            if r["arrival"] != arrival:
                continue
            by_month.setdefault(period(r["post_date"]), []).append(r)
        for mon, rows in by_month.items():
            base = sysdir / "bank" if arrival == "initial" else out / "arrivals" / "2026-10-late" / "bank"
            _write_csv(base / f"chase_operating_{mon}.csv",
                       ["Details", "Posting Date", "Description", "Amount", "Type", "Balance", "Check or Slip #"],
                       [[r["details"], us(r["post_date"]), r["desc"], plain(r["amount"]), r["type"],
                         plain(r["balance"]), r["check"]] for r in sorted(rows, key=lambda x: x["post_date"], reverse=True)])

    # ---- PayPal activity download
    pp_header = ["Date", "Time", "TimeZone", "Name", "Type", "Status", "Currency", "Gross", "Fee", "Net",
                 "From Email Address", "To Email Address", "Transaction ID", "Item Title", "Reference Txn ID",
                 "Balance Impact"]
    by_month: dict[str, list] = {}
    for p in w.paypal:
        by_month.setdefault(period(p["date"]), []).append(p)
    for mon, rows in by_month.items():
        _write_csv(sysdir / "paypal" / f"activity_{mon}.csv", pp_header,
                   [[us(p["date"]), p["time"], "America/Los_Angeles", p["name"], p["type"], p["status"], p["currency"],
                     plain(p["gross"]), plain(p["fee"]), plain(p["net"]), p["from"], p["to"], p["txn_id"], p["item"],
                     p["ref"], p["impact"]] for p in sorted(rows, key=lambda x: (x["date"], x["time"]))])

    # ---- Ramp transactions export
    rp_header = ["Transaction ID", "Transaction Date", "Settlement Date", "Merchant Name", "Merchant Descriptor",
                 "Amount", "Currency", "Cardholder", "Card Last 4", "MCC", "Department", "Accounting Category",
                 "Memo", "Receipt Attached", "Ramp Vendor", "ERP Vendor"]
    by_month = {}
    for t in w.ramp:
        by_month.setdefault(period(t["date"]), []).append(t)
    for mon, rows in by_month.items():
        _write_csv(sysdir / "ramp" / f"transactions_{mon}.csv", rp_header,
                   [[t["ramp_id"], t["date"].isoformat(), t["settle"].isoformat(), t["merchant"], t["descriptor"],
                     plain(t["amount"]), t["currency"], t["cardholder"], t["last4"], t["mcc"], t["department"],
                     t["category"], t["memo"], t["receipt"], t["ramp_vendor"], t["erp_vendor"]]
                    for t in sorted(rows, key=lambda x: x["date"])])

    # ---- QBO master data
    extra_vendors = sorted({t["erp_vendor"] for t in w.ramp if t["erp_vendor"]} -
                           {v["qbo_name"] for v in bible.VENDORS})
    _write_csv(sysdir / "qbo" / "vendor_list.csv", ["Vendor", "Company Name", "Email", "Default Expense Account", "Tax ID"],
               [[v["qbo_name"], v["legal"], f"billing@{v['domain']}", bible.acct_name(v["default_acct"]), v["tin"]]
                for v in bible.VENDORS] + [[n, n, "", "", ""] for n in extra_vendors])
    _write_csv(sysdir / "qbo" / "chart_of_accounts.csv", ["Number", "Account", "Type", "Detail Type"],
               [[k, v[1], v[2], v[0]] for k, v in bible.COA.items()])
    _write_csv(sysdir / "qbo" / "open_bills.csv", ["Bill ID", "Vendor", "Bill Date", "Due Date", "Num", "Memo",
                                                   "Amount", "Status", "Service Period"],
               [[b["bill_id"], b["vendor"], b["date"], b["due"], b["num"], b["memo"], plain(b["amount"]),
                 b["status"], b["service_period"]] for b in w.bills if b["status"] == "Open"])

    # ---- reference FX
    _write_csv(sysdir / "reference" / "fx_eur_usd.csv", ["date", "eur_usd", "source"],
               [[k, v, "ECB reference rate (simulated)"] for k, v in sorted(w.fx.items())])

    # ---- documents (+ index the ingestor reads; extracted fields mimic OCR output)
    for dd in w.docs:
        p = out / dd["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(dd["body"])
    (out / "systems" / "docs").mkdir(parents=True, exist_ok=True)
    (out / "systems" / "docs" / "index.json").write_text(json.dumps(
        [{k: v for k, v in d.items() if k != "body"} for d in w.docs if d["arrival"] == "initial"], indent=1))
    (out / "arrivals" / "2026-10-late").mkdir(parents=True, exist_ok=True)
    (out / "arrivals" / "2026-10-late" / "docs_index.json").write_text(json.dumps(
        [{k: v for k, v in d.items() if k != "body"} for d in w.docs if d["arrival"] == "october"], indent=1))

    (out / "arrivals" / "2026-10-late" / "qbo_bills.json").write_text(json.dumps(getattr(w, "october_bills", []), indent=1))

    # ---- policy + history
    (out / "policy").mkdir(parents=True, exist_ok=True)
    (out / "policy" / "close_policy.md").write_text(bible.POLICY_TEXT)
    (out / "policy" / "approval_matrix.json").write_text(json.dumps(bible.APPROVAL_MATRIX, indent=1))
    (out / "history").mkdir(parents=True, exist_ok=True)
    with (out / "history" / "precedents.jsonl").open("w") as fh:
        for pr in w.precedents:
            fh.write(json.dumps(pr) + "\n")

    # ---- ledger seed + vendor master (structured)
    (out / "ledger_seed.json").write_text(json.dumps(w.ledger, indent=0))
    (out / "vendors.json").write_text(json.dumps(bible.VENDORS + [
        {"id": f"V-{md5(n)[:6].upper()}", "qbo_name": n, "legal": n, "domain": "", "default_acct": "", "products": [],
         "tin": ""} for n in extra_vendors], indent=1))
    (out / "bills.json").write_text(json.dumps(w.bills, indent=1))

    # ---- answer key (the agent never reads this)
    (out / "answer_key.json").write_text(json.dumps({
        "seed": w.seed, "close_period": "2026-09", "generated_for": "eval only - never read by the agent",
        "moment_bank_id": getattr(w, "moment_bank_id", None), "items": w.key}, indent=1))

    # ---- manifest
    (out / "MANIFEST.json").write_text(json.dumps({
        "company": bible.COMPANY, "seed": w.seed, "close_period": "2026-09", "close_start": CLOSE_START.isoformat(),
        "counts": {"bank_rows": len(w.bank), "paypal_rows": len(w.paypal), "ramp_txns": len(w.ramp),
                   "ledger_entries": len(w.ledger), "documents": len(w.docs), "precedents": len(w.precedents),
                   "planted_items": len(w.key)}}, indent=1))


def world_dir(seed: int) -> Path:
    return config.DATA_DIR / f"seed_{seed}"


def generate(seed: int) -> Path:
    w = build(seed)
    out = world_dir(seed)
    write(w, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=config.world_seed())
    a = ap.parse_args()
    out = generate(a.seed)
    print(f"world written to {out}")
    print(json.loads((out / "MANIFEST.json").read_text())["counts"])


if __name__ == "__main__":
    main()
