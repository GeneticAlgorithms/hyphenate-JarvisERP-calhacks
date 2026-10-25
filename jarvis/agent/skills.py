"""Jarvis's skills: each turns one work item into a proposal (or a question, or a reasoned dismissal).

Pattern for every skill:  retrieve candidates (search / SQL)  ->  verify deterministically (amounts to the
cent, dates, periods)  ->  cite evidence, policy and precedent  ->  decide propose | ask | dismiss.
"""
from __future__ import annotations

import calendar
import itertools
import re
from dataclasses import dataclass, field

from jarvis import config
from jarvis.agent.context import Ctx, norm, sim
from jarvis.money import fmt, mul_rate
from jarvis.work.db import L
from jarvis.world import bible


@dataclass
class Plan:
    kind: str
    action: str = "propose"            # propose | ask | dismiss
    lines: list = field(default_factory=list)
    date: str = ""
    memo: str = ""
    name: str = ""
    reconcile: list = field(default_factory=list)
    match_entries: list = field(default_factory=list)
    bill_updates: list = field(default_factory=list)
    vendor: dict | None = None
    consumes: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    policy_id: str | None = None
    precedent_ids: list = field(default_factory=list)
    confidence: float = 0.9
    rationale: str = ""
    question: str = ""
    escalate: bool = False
    extra: dict = field(default_factory=dict)

    def patch(self) -> dict:
        prop = {"kind": self.kind, "date": self.date, "memo": self.memo, "name": self.name,
                "lines": self.lines, "reconcile": self.reconcile, "match_entries": self.match_entries,
                "bill_updates": self.bill_updates, "vendor": self.vendor, "consumes": self.consumes,
                "escalate": self.escalate, **self.extra}
        return {"kind": self.kind, "proposal": prop, "evidence": self.evidence, "policy_id": self.policy_id,
                "precedent_ids": self.precedent_ids, "confidence": self.confidence, "rationale": self.rationale,
                "question": self.question}


def L_(acct: str, cents: int, memo: str = "", vendor_id: str | None = None, **kw) -> dict:
    d = {"acct": acct, "cents": cents, "memo": memo}
    if vendor_id:
        d["vendor_id"] = vendor_id
    d.update(kw)
    return d


def ev(type_: str, id_: str, label: str, relation: str = "supports", detail: str = "") -> dict:
    return {"type": type_, "id": id_, "label": label, "relation": relation, "detail": detail}


def month_end(period: str) -> str:
    y, m = int(period[:4]), int(period[5:7])
    return f"{period}-{calendar.monthrange(y, m)[1]:02d}"


def _prev_period(period: str) -> str:
    y, m = int(period[:4]), int(period[5:7])
    return f"{y - (m == 1)}-{(m - 2) % 12 + 1:02d}"


def _prec_ids(ctx: Ctx, pattern: str, k: int = 4) -> list[str]:
    return [p["prec_id"] for p in ctx.precedents(pattern)][-k:]


# =============================================================================== BANK LINES
BANK_RULES = [
    ("paypal", re.compile(r"PAYPAL INST XFER (\w+)")),
    ("interest", re.compile(r"^INTEREST PAYMENT")),
    ("fee", re.compile(r"SERVICE FEE")),
    ("ramp", re.compile(r"ORIG CO NAME:RAMP\b.*CARD PMT")),
    ("synced", re.compile(r"ORIG CO NAME:(STRIPE|GUSTO)\b|FEDWIRE CREDIT")),
    ("billpay", re.compile(r"ORIG CO NAME:(.+?)\s{2,}.*CO ENTRY DESCR:(BILL PAY|PAYMENT)")),
]


def classify_bank(desc: str) -> tuple[str, re.Match | None]:
    for name, rx in BANK_RULES:
        m = rx.search(desc)
        if m:
            return name, m
    return "unknown", None


def plan_bank_line(ctx: Ctx, item: dict) -> Plan:
    rec = ctx.record(item["source_refs"][0])
    cls, m = classify_bank(rec["description"])
    ctx.tool("classify_bank_line", item["item_id"], f"'{rec['description'][:60]}' -> {cls}",
             [rec["record_id"]])
    fn = {"synced": _bank_synced, "interest": _bank_interest, "fee": _bank_fee, "ramp": _bank_ramp,
          "billpay": _bank_billpay, "paypal": _bank_paypal, "unknown": _bank_unknown}[cls]
    return fn(ctx, item, rec, m)


def _bank_ev(rec: dict) -> dict:
    return ev("record", rec["record_id"], f"Bank {rec['txn_date']} {fmt(rec['amount_cents'])}", "supports",
              rec["description"][:90])


def _bank_synced(ctx, item, rec, m) -> Plan:
    amt, d = rec["amount_cents"], rec["txn_date"]
    cands = ctx.db.q(
        "SELECT e.entry_id, e.date, e.memo, e.source FROM ledger_entries e JOIN ledger_lines l USING(entry_id) "
        "LEFT JOIN reconciliation c ON c.entry_id = e.entry_id "
        "WHERE l.account='1010' AND l.amount_cents=? AND julianday(e.date) BETWEEN julianday(?)-3 AND julianday(?)+3 "
        "AND c.entry_id IS NULL", (amt, d, d))
    ctx.tool("find_ledger_match", item["item_id"], f"{len(cands)} unreconciled ledger entries with cash {fmt(amt)} "
             f"within ±3 days", [c["entry_id"] for c in cands])
    if len(cands) == 1:
        c = cands[0]
        return Plan(kind="match", date=d, memo=f"Reconcile to {c['entry_id']} ({c['source']})", reconcile=[rec["record_id"]],
                    match_entries=[c["entry_id"]], confidence=0.99,
                    evidence=[_bank_ev(rec), ev("ledger", c["entry_id"], f"{c['memo'][:40]}", "supports",
                                                f"posted by {c['source']} on {c['date']}")],
                    rationale=f"Exactly one unreconciled ledger entry ({c['entry_id']}, {c['source']}) has cash "
                              f"{fmt(amt)} within 3 days. Already booked by the integration - reconcile, no new entry.")
    return _bank_unknown(ctx, item, rec, None, note=f"{len(cands)} possible ledger matches")


def _bank_interest(ctx, item, rec, m) -> Plan:
    amt, d = rec["amount_cents"], rec["txn_date"]
    prev = _prev_period(rec["period"])
    acc = ctx.db.q("SELECT e.entry_id, e.date, l.amount_cents FROM ledger_entries e JOIN ledger_lines l USING(entry_id) "
                   "WHERE l.account='1260' AND l.amount_cents>0 AND e.period=?", (prev,))
    bal = ctx.db.one("SELECT COALESCE(SUM(amount_cents),0) s FROM ledger_lines l JOIN ledger_entries e USING(entry_id) "
                     "WHERE l.account='1260' AND e.date < ?", (d,))["s"]
    ctx.tool("check_receivable", item["item_id"], f"1260 Interest Receivable balance before {d}: {fmt(bal)}; "
             f"{prev} accruals: {[fmt(a['amount_cents']) for a in acc]}", [a["entry_id"] for a in acc])
    match = next((a for a in acc if a["amount_cents"] == amt), None)
    pol = ctx.policy_ref("interest_accrual")
    if match:
        return Plan(kind="receivable_receipt", date=d, memo=f"Interest received for {prev} - clears 1260",
                    lines=[L_("1010", amt), L_("1260", -amt)], reconcile=[rec["record_id"]], confidence=0.99,
                    policy_id=pol, precedent_ids=_prec_ids(ctx, "interest_accrual", 2),
                    evidence=[_bank_ev(rec), ev("ledger", match["entry_id"], f"{prev} interest accrual {fmt(amt)}")],
                    rationale=f"This credit is {prev}'s interest, already recognized by accrual {match['entry_id']}. "
                              f"Booking it as income again would double-count {fmt(amt)}; it clears Interest Receivable.")
    return Plan(kind="receivable_receipt", action="ask", date=d, confidence=0.5, reconcile=[rec["record_id"]],
                evidence=[_bank_ev(rec)], escalate=True,
                question=f"Interest credit {fmt(amt)} doesn't match the {prev} accrual - was the accrual wrong?",
                rationale="Interest credit does not match any accrual; asking before booking.")


def _bank_fee(ctx, item, rec, m) -> Plan:
    amt = -rec["amount_cents"]
    return Plan(kind="bank_fee", date=rec["txn_date"], memo="Bank monthly service fee",
                lines=[L_("6810", amt), L_("1010", -amt)], reconcile=[rec["record_id"]], confidence=0.99,
                evidence=[_bank_ev(rec)], precedent_ids=[],
                rationale=f"Recurring Chase service fee {fmt(amt)} (same every month) -> 6810 Bank & FX Fees.")


def _bank_ramp(ctx, item, rec, m) -> Plan:
    amt = -rec["amount_cents"]
    prev = _prev_period(rec["period"])
    # the Ramp statement covers transactions dated in the cycle (by transaction date, not settlement)
    tot = -ctx.db.one("SELECT COALESCE(SUM(amount_cents),0) s FROM records WHERE source='ramp' AND period=?",
                      (prev,))["s"]
    ctx.tool("sum_card_statement", item["item_id"], f"Ramp card charges synced for {prev}: {fmt(-tot)}; "
             f"payment {fmt(amt)}", [rec["record_id"]])
    if -tot == amt:
        return Plan(kind="card_statement_payment", date=rec["txn_date"], memo=f"Ramp statement payment ({prev})",
                    lines=[L_("2050", amt), L_("1010", -amt)], reconcile=[rec["record_id"]], confidence=0.99,
                    evidence=[_bank_ev(rec), ev("ledger", f"ramp:{prev}", f"{prev} Ramp charges {fmt(-tot)}")],
                    rationale=f"Payment equals the {prev} Ramp statement ({fmt(amt)}) to the cent - relieves 2050 Ramp "
                              f"Card Payable. Expenses were already recorded by the Ramp sync.")
    return _bank_unknown(ctx, item, rec, None, note=f"Ramp payment {fmt(amt)} != statement {fmt(-tot)}")


def _bank_billpay(ctx, item, rec, m) -> Plan:
    amt = -rec["amount_cents"]
    payee = m.group(1).strip()
    bills = ctx.db.q("SELECT * FROM bills WHERE status='Open' AND amount_cents=?", (amt,))
    scored = sorted(bills, key=lambda b: -max(sim(payee, b["vendor"]), sim(payee, (ctx.vendor(b["vendor_id"]) or {})
                                                                               .get("legal", ""))))
    ctx.tool("find_open_bill", item["item_id"], f"payee '{payee}', {fmt(amt)}: {len(bills)} open bills with that amount",
             [b["bill_id"] for b in bills])
    if scored and max(sim(payee, scored[0]["vendor"]), sim(payee, ctx.vendor(scored[0]["vendor_id"])["legal"])) > 0.45:
        b = scored[0]
        return Plan(kind="bill_payment", date=rec["txn_date"], memo=f"Bill payment {b['vendor']} {b['num']}",
                    name=b["vendor"], lines=[L_("2010", amt, vendor_id=b["vendor_id"]), L_("1010", -amt)],
                    reconcile=[rec["record_id"]], bill_updates=[{"bill_id": b["bill_id"], "status": "Paid"}],
                    confidence=0.98,
                    evidence=[_bank_ev(rec), ev("bill", b["bill_id"], f"Open bill {b['num']} {b['vendor']} {fmt(amt)}")],
                    rationale=f"ACH to '{payee}' for {fmt(amt)} matches open bill {b['num']} ({b['vendor']}) exactly.")
    return _bank_unknown(ctx, item, rec, None, note="no open bill matches")


def _bank_unknown(ctx, item, rec, m, note: str = "") -> Plan:
    toks = [t for t in norm(rec["description"]).split() if len(t) > 3 and not t.startswith("jpm")]
    hits = ctx.search.search(" ".join(toks[:6]), kind="doc", k=3)
    ctx.tool("search_documents", item["item_id"], f"query '{' '.join(toks[:6])}' via {ctx.search.backend}: " +
             "; ".join(f"{h['id']} {h['highlight'][:60]}" for h in hits), [h["id"] for h in hits])
    hint = ""
    evid = [_bank_ev(rec)]
    if hits:
        hint = f" Closest evidence: {hits[0]['id']} ('{hits[0]['highlight'][:90].replace('«', '').replace('»', '')}')."
        evid.append(ev("doc", hits[0]["id"], hits[0]["id"], "context", hits[0]["highlight"][:120]))
    return Plan(kind="unknown", action="ask", date=rec["txn_date"], reconcile=[rec["record_id"]], confidence=0.3,
                evidence=evid, escalate=True,
                question=f"What is '{rec['description'][:60]}' ({fmt(rec['amount_cents'])} on {rec['txn_date']})? "
                         f"No invoice, bill or vendor record matches.{hint}",
                rationale=(note + ". " if note else "") + "No invoice, bill, vendor or policy explains this cash movement; "
                          "guessing an account would put an unsupported number in the books, so I'm asking.")


# --------------------------------------------------------------------------- PayPal
PAYPAL_PAYMENT_TYPES = {"General Payment", "PreApproved Payment Bill User Payment", "Express Checkout Payment",
                        "Website Payment"}


def paypal_usd_value(ctx: Ctx, p: dict) -> tuple[int, dict | None]:
    """USD actually paid for a PayPal payment (via its currency-conversion row for non-USD payments)."""
    if p["currency"] == "USD":
        return -p["amount_cents"], None
    conv = ctx.records("source='paypal' AND kind='paypal_general_currency_conversion' AND currency='USD' "
                       "AND json_extract(fields,'$.ref')=?", (p["src_id"],))
    return (-conv[0]["amount_cents"], conv[0]) if conv else (0, None)


def _is_personal(ctx: Ctx, name: str, item_text: str, mcc: str = "") -> tuple[bool, str]:
    pol = ctx.active_policy("personal")
    stats = pol["matcher"] if pol else {}
    mccs = set(stats.get("mccs", []))
    kws = stats.get("merchant_keywords", [])
    
    # Fall back to precedents if no active policy (e.g., before onboarding)
    if not pol:
        precs = ctx.precedents("personal")
        if precs:
            # Use the decision from the most recent precedent
            latest = precs[-1]
            decision = latest.get("decision", {})
            mccs = set(decision.get("personal_mccs", []))
            kws = decision.get("personal_merchant_keywords", [])
    
    text = norm(f"{name} {item_text}")
    if mcc and mcc in mccs:
        return True, f"MCC {mcc} ({bible.PERSONAL_MCC.get(mcc, 'personal category')}) is on ruling P-0317's list"
    kw = next((k for k in kws if k in text.split() or k in text), None)
    if kw:
        return True, f"merchant matches personal category keyword '{kw}' from ruling P-0317"
    return False, ""


def treat_paypal_payment(ctx: Ctx, p: dict, period: str) -> tuple[list[dict], list[dict], list[str], list[str], str]:
    """Returns (lines w/o the cash credit, evidence, policy refs, precedent ids, narrative)."""
    f = p["fields"]
    usd, conv = paypal_usd_value(ctx, p)
    evid = [ev("record", p["record_id"], f"PayPal {f['type']} {p['counterparty'] or ''} {fmt(-p['amount_cents'], p['currency'])}",
               "supports", f"{f.get('item', '')} | to {f.get('to_email')} | from {f.get('from_email')}")]
    pols, precs = [], []
    name = p["counterparty"] or ""
    employee = ctx.employee_for_email(f.get("from_email", ""))
    personal, why = _is_personal(ctx, name, f.get("item", ""))
    if personal and employee:
        pols.append(ctx.policy_ref("personal"))
        precs += _prec_ids(ctx, "personal", 2)
        evid.append(ev("person", employee, f"{employee} (paid from their login {f.get('from_email')})", "supports"))
        return ([L_("1250", usd, f"Personal purchase - {name} - {employee}", employee=employee)], evid, pols, precs,
                f"{fmt(usd)} to {name} ('{f.get('item')}') was initiated from {employee}'s PayPal login and {why} -> "
                f"1250 Employee Receivable; notify {employee}.")
    vid, sig = ctx.resolve_vendor(name, f.get("to_email", ""), f.get("item", ""))
    v = ctx.vendor(vid) if vid else None
    if sig:
        evid.append(ev("vendor", vid, f"Vendor {v['qbo_name']} ({sig[0]['signal']})", "supports"))
    if p["currency"] != "USD":
        rate = ctx.fx(p["txn_date"])
        foreign = -p["amount_cents"]
        mkt = mul_rate(foreign, rate)
        fee = usd - mkt
        pp_rate = usd / foreign
        pols.append(ctx.policy_ref("fx_fee"))
        precs += _prec_ids(ctx, "fx_fee", 2)
        evid.append(ev("fx", f"ECB:{p['txn_date']}", f"ECB {p['currency']}/USD {rate} on {p['txn_date']}", "supports",
                       f"market value {fmt(mkt)}"))
        if conv:
            evid.append(ev("record", conv["record_id"], f"PayPal conversion {fmt(usd)} at {pp_rate:.4f}", "supports"))
        # cut-off: is the service in this period or later?
        service = None
        hits = ctx.search.search(f"{name} service date {f.get('item', '')}", kind="doc", k=5)
        ctx.tool("search_documents", p["record_id"], f"'{name} {f.get('item', '')}' via {ctx.search.backend}: " +
                 "; ".join(h["id"] for h in hits), [h["id"] for h in hits])
        for h in hits:
            d = ctx.doc(h["id"])
            if d and (sim(d["vendor"], name) > 0.6 or norm(name) in norm(" ".join(map(str, d["fields"].get("crew", []))))):
                sd = d["fields"].get("service_date") or d["fields"].get("event_date")
                if sd:
                    service = (sd, d)
                    break
        acct = (v or {}).get("default_acct") or "5010"
        if service and service[0] > month_end(period):
            acct_use, timing = "1310", (f"the SOW ({service[1]['doc_id']}) puts the service on {service[0]}, after "
                                        f"{month_end(period)} -> 1310 Prepaid Tour Costs (cut-off), not {period} expense")
            pols.append(ctx.policy_ref("prepaid_deposit"))
            precs += _prec_ids(ctx, "prepaid_deposit", 1)
            evid.append(ev("doc", service[1]["doc_id"], f"{service[1]['title']}", "supports",
                           f"service_date {service[0]}"))
        elif service:
            acct_use, timing = acct, f"the service happened {service[0]} ({service[1]['doc_id']}) -> {period} expense"
            evid.append(ev("doc", service[1]["doc_id"], service[1]["title"], "supports", f"event {service[0]}"))
        else:
            acct_use, timing = acct, "no service-date document found; expensed in the payment period (lower confidence)"
        lines = [L_(acct_use, mkt, f"{name} {f.get('item', '')} ({fmt(foreign, p['currency'])} @ ECB {rate})", vid),
                 L_("6810", fee, f"PayPal FX spread on {fmt(foreign, p['currency'])} ({pp_rate:.4f} vs {rate})")]
        return (lines, evid, pols, precs,
                f"{fmt(foreign, p['currency'])} to {name}: {timing}. Market value at ECB {rate} is {fmt(mkt)}; PayPal "
                f"charged {fmt(usd)} at {pp_rate:.4f}, so {fmt(fee)} is a conversion fee (6810).")
    acct = (v or {}).get("default_acct") or "5010"
    alias_note = ""
    if v and name and name not in (v["qbo_name"], v["legal"]):
        alias_note = f" Payee name '{name}' isn't in the vendor master; it resolves to {v['qbo_name']} ({sig[0]['signal']})."
    if not v:
        hits = ctx.search.search(f"{name} {f.get('item', '')}", kind="doc", k=3)
        crew = [h for h in hits if norm(name) in norm(h["highlight"]) or norm(name) in norm(str(ctx.doc(h['id'])['fields']))]
        if crew:
            evid.append(ev("doc", crew[0]["id"], ctx.doc(crew[0]["id"])["title"], "supports", crew[0]["highlight"][:100]))
            return ([L_("5010", usd, f"{name} - {f.get('item', '')}")], evid, pols, precs,
                    f"{fmt(usd)} to {name} ('{f.get('item')}'): {crew[0]['id']} lists {name} on the crew -> 5010 "
                    f"Crew & Production. New payee - vendor record proposed separately.")
        return ([L_("6900", usd, f"{name} - {f.get('item', '')}")], evid, pols, precs,
                f"{fmt(usd)} to unknown payee {name}; no supporting document - parked in 6900 pending review.")
    return ([L_(acct, usd, f"{v['qbo_name']} - {f.get('item', '')}", vid)], evid, pols, precs,
            f"{fmt(usd)} to {name} ('{f.get('item')}') -> {acct} {bible.acct_name(acct)} (vendor {v['qbo_name']})."
            + alias_note)


def _bank_paypal(ctx, item, rec, m) -> Plan:
    amt = -rec["amount_cents"]
    fid = m.group(1)
    d = rec["txn_date"]
    funding = ctx.records("source='paypal' AND kind='paypal_bank_deposit_to_pp_account' AND src_id LIKE ? "
                          "AND amount_cents=?", (fid + "%", amt))
    ctx.tool("lookup_paypal_funding", item["item_id"], f"PayPal funding id {fid}… -> "
             f"{funding[0]['src_id'] if funding else 'not found'}", [f["record_id"] for f in funding])
    evid = [_bank_ev(rec)]
    if not funding:
        return _bank_unknown(ctx, item, rec, None, note=f"no PayPal funding record for {fid}")
    fr = funding[0]
    evid.append(ev("record", fr["record_id"], f"PayPal 'Bank Deposit to PP Account' {fmt(amt)}", "supports",
                   f"txn {fr['src_id']} ref {fr['fields'].get('ref') or '(none)'} | quality: {fr['evidence_quality']}"))
    consumed = ctx.consumed_records()
    cands = [p for p in ctx.records("source='paypal' AND julianday(txn_date) BETWEEN julianday(?)-2 AND julianday(?)+2",
                                    (d, d))
             if p["fields"].get("type") in PAYPAL_PAYMENT_TYPES and p["amount_cents"] < 0
             and p["record_id"] not in consumed]
    vals = {p["record_id"]: paypal_usd_value(ctx, p)[0] for p in cands}
    linked = fr["fields"].get("ref")
    ctx.tool("subset_sum", item["item_id"], f"{len(cands)} candidate PayPal payments within ±2 days; searching the "
             f"subset that sums to {fmt(amt)}" + (f" and includes linked payment {linked}" if linked else ""),
             [p["record_id"] for p in cands])
    best = None
    for r_ in range(1, min(len(cands), 6) + 1):
        for combo in itertools.combinations(cands, r_):
            if sum(vals[p["record_id"]] for p in combo) == amt:
                if linked and linked not in {p["src_id"] for p in combo}:
                    continue
                best = combo
                break
        if best:
            break
    if not best:
        pol = ctx.policy_ref("paypal_split")
        return Plan(kind="transfer", date=d, memo="Transfer to PayPal balance", name="PayPal",
                    lines=[L_("1030", amt, "Top-up of PayPal balance"), L_("1010", -amt)], reconcile=[rec["record_id"]],
                    consumes=[fr["record_id"]], confidence=0.92, policy_id=pol, evidence=evid,
                    rationale=f"No PayPal payment combination in ±2 days sums to {fmt(amt)}: this is a top-up of our own "
                              f"PayPal balance - a transfer between our accounts (1010 -> 1030), not an expense. Any later "
                              f"payment out of that balance is booked when it happens.")
    lines, pols, precs, story = [], [ctx.policy_ref("paypal_split")], _prec_ids(ctx, "paypal_split", 2), []
    for p in sorted(best, key=lambda x: -vals[x["record_id"]]):
        ls, e, pl, pr, narrative = treat_paypal_payment(ctx, p, item["period"])
        lines += ls
        evid += e
        pols += pl
        precs += pr
        story.append(narrative)
    lines.append(L_("1010", -amt, f"PayPal instant transfer {fr['src_id']}"))
    cons = [fr["record_id"]] + [p["record_id"] for p in best]
    for p in best:  # conversion rows belong to the payment too
        _, conv = paypal_usd_value(ctx, p)
        if conv:
            cons.append(conv["record_id"])
    pols = [x for x in dict.fromkeys(pols) if x]
    rationale = (f"The bank line is a PayPal instant transfer, not a purchase. {len(best)} PayPal payments sum to "
                 f"{fmt(amt)} to the cent" + (f" (PayPal linked only {linked}; the others were found by subset-sum)" if linked
                                              and len(best) > 1 else "") + ". " + " ".join(story))
    return Plan(kind="paypal_split", date=d, memo=f"PayPal transfer {fr['src_id']} split to {len(best)} payments",
                name="PayPal", lines=lines, reconcile=[rec["record_id"]], consumes=cons,
                confidence=0.93, policy_id=", ".join(pols), precedent_ids=list(dict.fromkeys(precs)), evidence=evid,
                rationale=rationale)


def plan_paypal_balance_payment(ctx: Ctx, item: dict) -> Plan:
    p = ctx.record(item["source_refs"][0])
    ls, e, pols, precs, narrative = treat_paypal_payment(ctx, p, item["period"])
    usd = sum(l["cents"] for l in ls)
    lines = ls + [L_("1030", -usd, "Paid from PayPal balance")]
    cons = [p["record_id"]]
    _, conv = paypal_usd_value(ctx, p)
    if conv:
        cons.append(conv["record_id"])
    return Plan(kind="paypal_payment", date=p["txn_date"], memo=f"PayPal payment {p['counterparty']}",
                name=p["counterparty"], lines=lines, consumes=cons, confidence=0.88,
                policy_id=", ".join(x for x in pols if x) or None, precedent_ids=precs, evidence=e,
                rationale="Paid from the PayPal balance, so it never appears in the bank feed. " + narrative)


# =============================================================================== CARD REVIEW
def detect_card_issues(ctx: Ctx, period: str) -> list[dict]:
    """Scan the period's Ramp transactions (already synced into the ledger) for judgment issues."""
    issues = []
    rows = ctx.records("source='ramp' AND period=?", (period,))
    ctx.tool("scan_card_transactions", f"ramp:{period}", f"{len(rows)} Ramp transactions in {period}", [])
    for r in rows:
        f = r["fields"]
        entry = ctx.ledger_entry_for("ramp_id", f["ramp_id"])
        if not entry:
            continue
        lines = ctx.entry_lines(entry["entry_id"])
        exp_line = next(l for l in lines if l["account"] != "2050")
        personal, why = _is_personal(ctx, f["merchant"], f["descriptor"], f["mcc"])
        if personal and (not f["memo"] or f["receipt"] == "No"):
            issues.append({"type": "personal", "record": r, "entry": entry, "line": exp_line, "why": why})
            continue
        if r["amount_cents"] < 0 and exp_line["account"].startswith("4"):
            issues.append({"type": "refund", "record": r, "entry": entry, "line": exp_line})
            continue
    return issues


def plan_card_personal(ctx: Ctx, item: dict, issue: dict) -> Plan:
    r, line = issue["record"], issue["line"]
    f = r["fields"]
    amt = r["amount_cents"]
    return Plan(kind="reclass", date=month_end(item["period"]), memo=f"Reclass personal purchase to employee receivable "
                f"({f['cardholder']})", name=f["cardholder"],
                lines=[L_("1250", amt, f"Personal - {f['merchant']} - {f['cardholder']}", employee=f["cardholder"]),
                       L_(line["account"], -amt, f"Remove from {bible.acct_name(line['account'])}")],
                confidence=0.9, policy_id=ctx.policy_ref("personal"), precedent_ids=_prec_ids(ctx, "personal", 2),
                evidence=[ev("record", r["record_id"], f"Ramp {f['merchant']} {fmt(amt)} by {f['cardholder']}", "supports",
                             f"MCC {f['mcc']} | memo '{f['memo']}' | receipt {f['receipt']} | Ramp category '{f['category']}'"),
                          ev("ledger", issue["entry"]["entry_id"], f"Synced to {line['account']} {bible.acct_name(line['account'])}",
                             "contradicts", "Ramp's category is wrong for a personal purchase")],
                extra={"notify": f["cardholder"]},
                rationale=f"{f['merchant']} {fmt(amt)} on {f['cardholder']}'s card: {issue['why']}, and there is "
                          f"{'no memo' if not f['memo'] else 'a memo'} and {'no receipt' if f['receipt'] == 'No' else 'a receipt'}. "
                          f"Ramp categorized it as '{f['category']}'. Per P-0317 size doesn't matter: reclass to 1250 "
                          f"Employee Receivable and notify {f['cardholder']}.")


def plan_card_refund(ctx: Ctx, item: dict, issue: dict) -> Plan:
    r, line = issue["record"], issue["line"]
    f = r["fields"]
    amt = -r["amount_cents"]
    orig = ctx.records("source='ramp' AND counterparty=? AND amount_cents>0 AND txn_date < ? ORDER BY txn_date DESC",
                       (r["counterparty"], r["txn_date"]))
    o_entry = ctx.ledger_entry_for("ramp_id", orig[0]["fields"]["ramp_id"]) if orig else None
    o_acct = next(l["account"] for l in ctx.entry_lines(o_entry["entry_id"]) if l["account"] != "2050") if o_entry else "5020"
    evid = [ev("record", r["record_id"], f"Ramp refund {f['merchant']} {fmt(-amt)}", "supports", f["memo"]),
            ev("ledger", issue["entry"]["entry_id"], f"Synced to {line['account']} {bible.acct_name(line['account'])}",
               "contradicts", "a vendor refund is not income")]
    if orig:
        evid.append(ev("record", orig[0]["record_id"], f"Original charge {orig[0]['txn_date']} {fmt(orig[0]['amount_cents'])}",
                       "supports", orig[0]["description"]))
    return Plan(kind="reclass", date=month_end(item["period"]), memo=f"Reclass {f['merchant']} refund to {o_acct}",
                name=f["merchant"], lines=[L_(line["account"], amt, "Remove refund from income"),
                                            L_(o_acct, -amt, f"Refund of {orig[0]['txn_date'] if orig else 'original'} charge")],
                confidence=0.92, evidence=evid,
                rationale=f"{f['merchant']} refunded {fmt(amt)} ('{f['memo']}'); Ramp booked it to "
                          f"{bible.acct_name(line['account'])}. A refund reduces the original "
                          f"{bible.acct_name(o_acct)} charge from {orig[0]['txn_date'] if orig else 'earlier'} - it isn't revenue.")


def detect_duplicates(ctx: Ctx, period: str) -> list[dict]:
    out = []
    bills = ctx.db.q("SELECT * FROM bills WHERE status='Open' AND substr(date,1,7)=?", (period,))
    cards = ctx.records("source='ramp' AND period=? AND amount_cents>0", (period,))
    for b in bills:
        for c in cards:
            vid, sig = ctx.resolve_vendor(c["fields"]["ramp_vendor"] or c["counterparty"], "", c["fields"]["descriptor"])
            if vid == b["vendor_id"] and c["amount_cents"] == b["amount_cents"]:
                from datetime import date as _d
                dd = abs((_d.fromisoformat(b["date"]) - _d.fromisoformat(c["txn_date"])).days)
                if dd <= 10:
                    prev = next((x for x in out if x["bill"]["bill_id"] == b["bill_id"]), None)
                    if prev is None:
                        out.append({"bill": b, "card": c, "signals": sig, "days": dd})
                    elif dd < prev["days"]:
                        prev.update(card=c, signals=sig, days=dd)
    ctx.tool("detect_duplicates", f"bills:{period}", f"compared {len(bills)} open bills x {len(cards)} card charges "
             f"by resolved vendor + amount ±10 days: {len(out)} duplicate(s)", [d["bill"]["bill_id"] for d in out])
    return out


def plan_duplicate(ctx: Ctx, item: dict, dup: dict) -> Plan:
    b, c = dup["bill"], dup["card"]
    amt = b["amount_cents"]
    return Plan(kind="duplicate", date=month_end(item["period"]), memo=f"Void duplicate bill {b['num']} (paid by card)",
                name=b["vendor"], lines=[L_("2010", amt, f"Void bill {b['num']}", b["vendor_id"]),
                                          L_(b["acct"], -amt, "Remove double-counted expense", b["vendor_id"])],
                bill_updates=[{"bill_id": b["bill_id"], "status": "Voided"}], confidence=0.9,
                evidence=[ev("bill", b["bill_id"], f"AP bill {b['num']} {b['vendor']} {fmt(amt)} ({b['date']})", "contradicts",
                             "entered by AP clerk"),
                          ev("record", c["record_id"], f"Ramp {c['counterparty']} {fmt(amt)} ({c['txn_date']})", "supports",
                             "already paid by card and synced to the ledger"),
                          ev("vendor", b["vendor_id"], f"'{c['counterparty']}' resolves to {b['vendor']} "
                                                       f"({dup['signals'][0]['signal'] if dup['signals'] else 'vendor match'})")],
                rationale=f"The same {b['vendor']} charge ({fmt(amt)}, {dup['days']} days apart) exists twice: paid on "
                          f"{c['fields']['cardholder']}'s card as '{c['counterparty']}' (synced from Ramp) and entered as AP "
                          f"bill {b['num']}. The expense is counted twice and the bill would be paid twice. Void the bill; "
                          f"keep the card transaction (it's the actual payment).")


# =============================================================================== VENDORS
def discover_vendor_names(ctx: Ctx, period: str) -> list[dict]:
    seen, out = set(), []
    for r in ctx.records("source='ramp' AND period=?", (period,)):
        f = r["fields"]
        name = f["ramp_vendor"]
        if f["erp_vendor"] or not name or name in seen or ctx.vendor_for_alias(name):
            continue
        seen.add(name)
        out.append({"name": name, "source": "ramp", "record": r, "descriptor": f["descriptor"], "email": ""})
    for r in ctx.records("source='paypal' AND period=? AND amount_cents<0", (period,)):
        f = r["fields"]
        name = r["counterparty"]
        if f.get("type") not in PAYPAL_PAYMENT_TYPES or not name or name in seen or ctx.vendor_for_alias(name):
            continue
        if ctx.employee_for_email(f.get("from_email", "")) and _is_personal(ctx, name, f.get("item", ""))[0]:
            continue  # personal purchase - not a vendor relationship
        seen.add(name)
        out.append({"name": name, "source": "paypal", "record": r, "descriptor": f.get("item", ""),
                    "email": f.get("to_email", "")})
    return out


def plan_vendor(ctx: Ctx, item: dict, info: dict) -> Plan:
    name = info["name"]
    r = info["record"]
    evid = [ev("record", r["record_id"], f"{info['source'].title()} payee '{name}' {fmt(r['amount_cents'])}", "context",
               info["descriptor"])]
    receipt = next((d for d in ctx.docs("receipt") if d["fields"].get("ramp_merchant") == name), None)
    signals = []
    cand = None
    if receipt:
        evid.append(ev("doc", receipt["doc_id"], f"Receipt issuer {receipt['fields']['issuer']}", "supports",
                       f"domain {receipt['fields'].get('domain')} | TIN {receipt['fields'].get('tin') or 'n/a'}"))
        cand = ctx.vendor_for_alias(receipt["fields"]["issuer"]) or ctx.vendor_by_domain(receipt["fields"].get("domain", ""))
        if cand:
            signals.append(f"receipt issuer '{receipt['fields']['issuer']}' / domain {receipt['fields'].get('domain')} "
                           f"= {ctx.vendor(cand)['legal']}")
    if not cand:
        vid, sig = ctx.resolve_vendor(name, info["email"], info["descriptor"])
        if vid:
            cand = vid
            signals += [s["signal"] for s in sig]
    hits = ctx.search.search(name, kind="vendor", k=3)
    ctx.tool("search_vendors", item["item_id"], f"'{name}' via {ctx.search.backend}: " +
             "; ".join(f"{h['id']} ({h['score']})" for h in hits), [h["id"] for h in hits])
    lookalike = next((h for h in hits if h["id"] != cand and sim(name.split()[0], ctx.vendor(h["id"])["qbo_name"].split()[0]) > 0.85),
                     None)
    pol = ctx.policy_ref("vendor_alias")
    if cand:
        v = ctx.vendor(cand)
        evid.append(ev("vendor", cand, f"{v['qbo_name']} ({v['legal']})", "supports"))
        return Plan(kind="vendor_link", vendor={"action": "link", "alias": name, "vendor_id": cand, "source": info["source"]},
                    date=month_end(item["period"]), confidence=0.93, policy_id=pol,
                    precedent_ids=_prec_ids(ctx, "vendor_alias", 2), evidence=evid,
                    rationale=f"'{name}' is not a new supplier: {'; '.join(signals)}. Link the alias to existing vendor "
                              f"{v['qbo_name']} instead of creating a duplicate (product names aren't vendors).")
    legal = receipt["fields"]["issuer"] if receipt else name
    note = ""
    if lookalike:
        lv = ctx.vendor(lookalike["id"])
        evid.append(ev("vendor", lv["vendor_id"], f"Look-alike: {lv['qbo_name']} ({lv['legal']}, {lv['domain']})",
                       "contradicts", "similar name, different legal entity"))
        note = (f" It looks like existing vendor {lv['qbo_name']}, but the receipt shows a different legal entity "
                f"({legal}, {receipt['fields'].get('domain') if receipt else 'unknown domain'}) and a different line of "
                f"business - merging would mix two suppliers' history. Do NOT merge.")
    new_id = "V-" + re.sub(r"[^A-Z0-9]", "", name.upper())[:10]
    acct = "5010" if info["source"] == "paypal" else ""
    return Plan(kind="vendor_create", date=month_end(item["period"]), confidence=0.85, policy_id=pol, evidence=evid,
                vendor={"action": "create", "alias": name, "source": info["source"],
                        "new": {"vendor_id": new_id, "qbo_name": name, "legal": legal,
                                "domain": (receipt or {}).get("fields", {}).get("domain", info["email"].split("@")[-1] if info["email"] else ""),
                                "default_acct": acct, "tin": (receipt or {}).get("fields", {}).get("tin", "")}},
                rationale=f"'{name}' doesn't resolve to any existing vendor by legal name, domain, TIN or product." + note +
                          " Propose creating a new vendor (Controller approval required).")


# =============================================================================== ACCRUALS
def accrual_candidates(ctx: Ctx, period: str) -> list[dict]:
    """Which vendors performed in the period but haven't billed for it?"""
    pe = month_end(period)
    out: dict[str, dict] = {}
    for d in ctx.docs():
        f = d["fields"]
        vname = d["vendor"]
        if not vname or d["kind"] not in ("sow", "timesheet", "invoice", "email"):
            continue
        vid = ctx.vendor_for_alias(vname)
        if not vid:
            continue
        c = out.setdefault(vid, {"vendor_id": vid, "docs": []})
        c["docs"].append(d)
    res = []
    for vid, c in out.items():
        ks = {d["kind"]: d for d in c["docs"]}
        inv = next((d for d in c["docs"] if d["kind"] == "invoice" and str(d["fields"].get("service_period_start", d["fields"].get("service_start", "")))[:7] == period), None)
        ts = next((d for d in c["docs"] if d["kind"] == "timesheet" and d["fields"].get("period") == period), None)
        sow_in = [d for d in c["docs"] if d["kind"] == "sow" and str(d["fields"].get("service_date", ""))[:7] == period]
        sow_future = [d for d in c["docs"] if d["kind"] == "sow" and str(d["fields"].get("service_date", "")) > pe
                      and str(d["fields"].get("service_date", ""))[:7] == _next_period(period)]
        if inv or ts or sow_in:
            res.append({"vendor_id": vid, "invoice": inv, "timesheet": ts, "sow": sow_in[0] if sow_in else
                        next((d for d in c["docs"] if d["kind"] == "sow" and d["fields"].get("rate_per_hour")), None),
                        "emails": [d for d in c["docs"] if d["kind"] == "email"], "future": False})
        elif sow_future and not any(d["kind"] == "invoice" for d in c["docs"]):
            res.append({"vendor_id": vid, "future": True, "sow": sow_future[0]})
    return res


def _next_period(period: str) -> str:
    y, m = int(period[:4]), int(period[5:7])
    return f"{y + (m == 12)}-{m % 12 + 1:02d}"


def plan_accrual(ctx: Ctx, item: dict, cand: dict) -> Plan:
    period = item["period"]
    pe = month_end(period)
    vid = cand["vendor_id"]
    v = ctx.vendor(vid)
    pol = ctx.policy_ref("accrual")
    if cand.get("future"):
        s = cand["sow"]
        return Plan(kind="accrual", action="dismiss", date=pe, confidence=0.95,
                    evidence=[ev("doc", s["doc_id"], s["title"], "contradicts", f"service_date {s['fields'].get('service_date')}")],
                    rationale=f"{v['qbo_name']} has a signed SOW ({s['doc_id']}), but the service date is "
                              f"{s['fields'].get('service_date')} - after {pe}. A contract is a commitment, not performance: "
                              f"nothing to accrue for {period}.")
    # already billed for this period?
    billed = ctx.db.one("SELECT * FROM bills WHERE vendor_id=? AND service_period=?", (vid, period))
    if billed:
        return Plan(kind="accrual", action="dismiss", date=pe, confidence=0.95,
                    evidence=[ev("bill", billed["bill_id"], f"Bill {billed['num']} {fmt(billed['amount_cents'])}")],
                    rationale=f"{v['qbo_name']} already billed {period} ({billed['num']}); no accrual needed.")
    evid, precs = [], []
    amount, method, contradicts = None, "", []
    inv, ts, sow = cand.get("invoice"), cand.get("timesheet"), cand.get("sow")
    acct = v["default_acct"] or "5010"
    if inv:
        amount = int(inv["fields"].get("amount_cents") or round(float(inv["fields"]["amount"]) * 100))
        method = (f"(a) vendor invoice {inv['fields'].get('invoice_number', inv['doc_id'])} dated "
                  f"{inv['fields'].get('invoice_date')} for service {inv['fields'].get('service_period_start')} – "
                  f"{inv['fields'].get('service_period_end')}")
        evid.append(ev("doc", inv["doc_id"], inv["title"], "supports",
                       f"invoice date {inv['fields'].get('invoice_date')} (after period) but service in {period}"))
    elif ts and sow and sow["fields"].get("rate_per_hour"):
        rate = int(round(float(sow["fields"]["rate_per_hour"]) * 100))
        hours = int(ts["fields"].get("hours") or ts["fields"].get("total_hours"))
        amount = rate * hours
        method = f"(b) SOW rate {fmt(rate)}/h x {hours} approved timesheet hours ({ts['doc_id']}, approved by {ts['fields'].get('approved_by', 'ops')})"
        evid += [ev("doc", sow["doc_id"], sow["title"], "supports", f"rate {fmt(rate)}/h"),
                 ev("doc", ts["doc_id"], ts["title"], "supports", f"{hours} approved hours")]
    elif sow and sow["fields"].get("fee"):
        fee = int(round(float(sow["fields"]["fee"]) * 100))
        perf = next((d for d in ctx.docs("run_sheet")
                     if str(d["fields"].get("event_date")) == str(sow["fields"].get("service_date"))
                     and norm(v["qbo_name"]) in norm(" ".join(map(str, d["fields"].get("crew", []))) + " " + d["text"])), None)
        if not perf:
            return Plan(kind="accrual", action="ask", date=pe, confidence=0.4, escalate=True,
                        evidence=[ev("doc", sow["doc_id"], sow["title"], "context")],
                        question=f"{v['qbo_name']} has a booking for {sow['fields'].get('service_date')} but I can't find "
                                 f"evidence the work happened. Did it?",
                        rationale="A contract alone is a commitment, not evidence of performance; asking before accruing.")
        amount = fee
        method = f"(c) flat fee {fmt(fee)} per {sow['doc_id']}, performance confirmed by {perf['doc_id']}"
        evid += [ev("doc", sow["doc_id"], sow["title"], "supports", f"fee {fmt(fee)}"),
                 ev("doc", perf["doc_id"], perf["title"], "supports", f"{v['qbo_name']} on the crew list")]
    if amount is None:
        return Plan(kind="accrual", action="dismiss", date=pe, confidence=0.6, evidence=evid,
                    rationale=f"No measurable evidence of {period} work for {v['qbo_name']}.")
    # sources that disagree
    for e in cand.get("emails", []):
        est = e["fields"].get("estimate_cents")
        if est and int(est) != amount:
            contradicts.append(f"{e['doc_id']} (vendor email) says ~{fmt(int(est))}")
            evid.append(ev("doc", e["doc_id"], e["title"], "contradicts", f"informal estimate ~{fmt(int(est))}"))
    hist = [p for p in ctx.precedents("accrual") if p["decision"].get("vendor_id") == vid]
    bias_note = ""
    if hist:
        ratios = [p["decision"]["actual_cents"] / p["decision"]["estimate_cents"] for p in hist]
        avg = sum(ratios) / len(ratios)
        precs += [p["prec_id"] for p in hist]
        bias_note = (f" History: {len(hist)} prior accruals for {v['qbo_name']} came in at {avg:.3f}x the estimate on "
                     f"average (~{fmt(int(amount * avg))} expected). Policy books the supportable amount, not the "
                     f"guess - flagged for the true-up when the invoice arrives.")
        ctx.tool("run_esql", item["item_id"], f"FROM precedents | WHERE pattern=='accrual' AND vendor=='{vid}' | "
                 f"STATS avg(actual/estimate) -> {avg:.3f} (n={len(hist)})", precs)
    slow = [p for p in ctx.precedents("vendor_slow") if p["decision"].get("vendor_id") == vid]
    corrections = [p for p in ctx.precedents("controller_correction") if p["decision"].get("vendor_id") == vid]
    escalate, question = False, ""
    if slow or (not inv and not ts):
        escalate = True
        question = (f"Emailed {v['qbo_name']} to confirm the {period} amount ({fmt(amount)}) and request the invoice."
                    + (f" They've been late before ({slow[0]['summary'][:80]})." if slow else ""))
        precs += [p["prec_id"] for p in slow]
    if corrections:
        precs += [p["prec_id"] for p in corrections]
        bias_note += (f" Note: in {corrections[-1]['period']} the Controller corrected this vendor's accrual to a "
                      f"confirmed amount ({corrections[-1]['prec_id']}).")
    rationale = (f"{v['qbo_name']} performed work in {period} with no bill yet. Measured by {method}: {fmt(amount)}."
                 + (f" Sources disagree: {'; '.join(contradicts)}. Policy ranks contract x approved timesheet above an "
                    f"informal email estimate, so I book {fmt(amount)}." if contradicts else "") + bias_note)
    return Plan(kind="accrual", date=pe, memo=f"Accrue {v['qbo_name']} {period} ({method.split(' ')[0]})", name=v["qbo_name"],
                lines=[L_(acct, amount, f"{v['qbo_name']} {period} services", vid), L_("2100", -amount, "Accrued expenses", vid)],
                confidence=0.86 if not contradicts else 0.82, policy_id=pol, precedent_ids=precs, evidence=evid,
                escalate=escalate, question=question, rationale=rationale,
                extra={"vendor_id": vid, "accrual_amount": amount, "method": method})


def plan_interest_accrual(ctx: Ctx, item: dict, notice: dict) -> Plan:
    f = notice["fields"]
    amt = int(f["interest_cents"])
    hist = ctx.precedents("interest_accrual")
    avg = int(sum(p["decision"]["amount_cents"] for p in hist) / len(hist)) if hist else None
    sanity = f" History averages {fmt(avg)}/month - in line." if avg and abs(amt - avg) < avg * 0.25 else \
        (f" History averages {fmt(avg)}/month - investigate." if avg else "")
    return Plan(kind="accrual", date=month_end(item["period"]), memo=f"Accrue interest earned {item['period']}",
                name="JPMorgan Chase", lines=[L_("1260", amt, "Interest receivable"), L_("4900", -amt, "Interest income")],
                confidence=0.95, policy_id=ctx.policy_ref("interest_accrual"), precedent_ids=_prec_ids(ctx, "interest_accrual", 3),
                evidence=[ev("doc", notice["doc_id"], notice["title"], "supports",
                             f"accrued {fmt(amt)}, credited {f.get('credit_date')}")],
                rationale=f"Chase's notice shows {fmt(amt)} interest earned in {item['period']} but credited on "
                          f"{f.get('credit_date')}. Revenue belongs to {item['period']}: accrue to 1260 Interest Receivable now; "
                          f"the October credit will clear 1260, not create new income.{sanity}")


# =============================================================================== OCTOBER: accrual vs actual
def plan_accrual_reversal(ctx: Ctx, item: dict, acc: dict, bill: dict) -> Plan:
    est = acc["amount"]
    actual = bill["amount_cents"]
    diff = actual - est
    vid = acc["vendor_id"]
    v = ctx.vendor(vid)
    inv = ctx.doc(bill["num"]) or ctx.doc((ctx.ledger_entry_for("bill_id", bill["bill_id"]) or {}).get("num", ""))
    explain = ""
    evid = [ev("ledger", acc["entry_id"], f"Sep accrual {fmt(est)} ({acc['item_id']})", "supports"),
            ev("bill", bill["bill_id"], f"Bill {bill['num']} {fmt(actual)} entered {bill['date']}", "supports")]
    if inv:
        evid.append(ev("doc", inv["doc_id"], inv["title"], "supports"))
        prem = re.search(r"\|\s*([^|]*premium[^|]*)\|\s*\d+\s*\|\s*([\d.,]+)\s*\|\s*([\d.,]+)", inv["text"], re.I)
        if prem and diff:
            explain = f" The difference is the line '{prem.group(1).strip()}' ({prem.group(3)})"
            sow = next((d for d in ctx.docs("sow") if d["vendor"] == v["qbo_name"] and "1.5x" in d["text"]), None)
            if sow:
                explain += f", allowed by the SOW's after-hours 1.5x clause ({sow['doc_id']})."
                evid.append(ev("doc", sow["doc_id"], sow["title"], "supports", "after-hours load-out billed at 1.5x"))
            else:
                explain += "."
    hist_note = ""
    hist = [p for p in ctx.precedents("accrual") if p["decision"].get("vendor_id") == vid]
    if hist and diff:
        avg = sum(p["decision"]["actual_cents"] / p["decision"]["estimate_cents"] for p in hist) / len(hist)
        hist_note = f" Actual/estimate = {actual / est:.3f} vs historical {avg:.3f} - consistent with this vendor."
    return Plan(kind="accrual_reversal", date=bill["date"] if bill["date"][:7] > acc["period"] else f"{_next_period(acc['period'])}-01",
                memo=f"Reverse {acc['period']} accrual - {v['qbo_name']} invoice {bill['num']} received", name=v["qbo_name"],
                lines=[L_("2100", est, "Release accrual", vid), L_(acc["acct"], -est, "Reverse accrued expense", vid)],
                confidence=0.95, policy_id=ctx.policy_ref("accrual"), evidence=evid,
                extra={"accrued_cents": est, "actual_cents": actual, "trueup_cents": diff},
                rationale=f"{v['qbo_name']}'s invoice {bill['num']} ({fmt(actual)}) arrived for {acc['period']}, which I accrued "
                          f"at {fmt(est)}. Reverse the accrual so the expense isn't counted twice; October carries the "
                          f"true-up of {fmt(diff)}." + explain + hist_note)
