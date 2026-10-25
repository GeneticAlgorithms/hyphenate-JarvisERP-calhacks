"""The close orchestrator: discover work -> plan -> review -> route (policy / Controller) -> post via the Gateway.

Jarvis never touches the ledger. It creates and advances work items through transition(); the
Gateway is the only writer; every step lands in the hash-chained audit log.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from jarvis import config
from jarvis.agent import llm, policies, skills
from jarvis.agent.context import JARVIS, REVIEWER, Ctx
from jarvis.money import fmt, to_cents
from jarvis.work import events, gateway, ledger
from jarvis.work.db import DB, J, L
from jarvis.work.roles import P001_KINDS, actor
from jarvis.work.transition import Denied, append_audit, create_item, get_item, item_by_anchor, log, now, transition
from jarvis.world import bible

P001 = actor("policy:P-001")
SYNC = actor("sync")


class Engine:
    def __init__(self, ctx: Ctx):
        self.ctx = ctx
        self.db = ctx.db
        self.period = config.CLOSE_PERIOD

    # ------------------------------------------------------------------ helpers
    def pause(self, k: float = 1.0):
        if self.ctx.speed:
            time.sleep(self.ctx.speed * k)

    def _apply(self, item: dict, plan: skills.Plan) -> dict:
        patch = plan.patch()
        # the item's source refs = what it rests on (records it reconciles/consumes)
        refs = list(dict.fromkeys(item["source_refs"] + plan.reconcile + plan.consumes))
        patch["source_refs"] = refs
        if plan.action == "dismiss":
            it = transition(self.db, item["item_id"], "dismiss", JARVIS, patch, reason=plan.rationale[:300])
        elif plan.action == "ask":
            it = transition(self.db, item["item_id"], "ask", JARVIS, patch, reason=plan.question[:300])
            self.send("jarvis", "maya", f"Question: {item['title']}", plan.question, item["item_id"])
        else:
            it = transition(self.db, item["item_id"], "propose" if item["state"] in ("NEW", "NEEDS_INFO") else "revise",
                            JARVIS, patch, reason=plan.rationale[:300],
                            evidence=[e["id"] for e in plan.evidence])
            if plan.escalate and plan.question:
                vid = plan.extra.get("vendor_id")
                v = self.ctx.vendor(vid) if vid else None
                to = f"vendor:{v['qbo_name']}" if v else "maya"
                self.send("jarvis", to, f"Confirm {item['period']} amount - Afterglow Labs",
                          f"Hi {v['qbo_name'].split()[0] if v else ''}, could you confirm the amount for your "
                          f"{item['period']} work (we have {fmt(plan.extra.get('accrual_amount', 0))}) and send the invoice? "
                          f"Thanks - Afterglow AP (Jarvis)", item["item_id"])
            if plan.extra.get("notify"):
                self.send("jarvis", f"employee:{plan.extra['notify']}", "Personal charge on company card",
                          f"Hi {plan.extra['notify']}, a charge on your company card looks personal and has been moved to "
                          f"your employee receivable per policy P-0317. Reply if it was a business expense (with receipt).",
                          item["item_id"])
        self.review(it)
        return get_item(self.db, item["item_id"])

    def send(self, frm: str, to: str, subject: str, body: str, item_id: str | None = None):
        mid = f"MSG-{int(time.time() * 1000) % 10**10:010d}-{abs(hash(body)) % 1000:03d}"
        with self.db.tx():
            self.db.conn.execute("INSERT INTO messages(msg_id,at,from_actor,to_actor,subject,body,item_id,direction) "
                                 "VALUES(?,?,?,?,?,?,?,?)", (mid, now(), frm, to, subject, body, item_id, "out"))
            append_audit(self.db, actor(frm) if frm in ("jarvis", "maya", "dev") else JARVIS, "send_message",
                         item_id or to, True, f"to {to}: {subject}", {}, [mid])
        events.publish("message", msg_id=mid, frm=frm, to=to, subject=subject, body=body, item_id=item_id)

    def review(self, item: dict):
        """Critic pass (separate identity): deterministic checks on the proposal."""
        if item["state"] != "PROPOSED":
            return
        p = item["proposal"] or {}
        lines = p.get("lines", [])
        checks = {
            "balanced": sum(l["cents"] for l in lines) == 0,
            "accounts_valid": all(l["acct"] in bible.COA for l in lines),
            "open_period": (not lines) or (p.get("date", "")[:7] > config.LOCKED_THROUGH),
            "has_evidence": len(item.get("evidence") or []) > 0,
            "cites_policy_or_precedent": bool(item.get("policy_id") or item.get("precedent_ids")) or item["kind"] in
            ("match", "bank_fee", "bill_payment", "card_statement_payment", "duplicate", "reclass", "vendor_create"),
        }
        contradicting = [e for e in item.get("evidence", []) if e.get("relation") == "contradicts"]
        verdict = "pass" if all(checks.values()) else "flag"
        note = "; ".join(k for k, v in checks.items() if not v) or "all checks pass"
        if contradicting:
            note += f"; {len(contradicting)} contradicting source(s) acknowledged in rationale"
        transition(self.db, item["item_id"], "review", REVIEWER, {"review": {"verdict": verdict, "checks": checks,
                                                                              "note": note}},
                   reason=f"review {verdict}: {note}")

    def route(self, item: dict):
        """Standing policy P-001 approves narrow, exact, no-judgment items; everything else waits for the Controller."""
        if item["state"] != "PROPOSED":
            return item
        kind = item["kind"]
        if kind in P001_KINDS or kind == "bank_fee":
            try:
                transition(self.db, item["item_id"], "approve", P001,
                           reason="P-001: exact match to existing subledger / bank fee < $250, confidence >= 0.95")
                return gateway.post(self.db, item["item_id"])
            except Denied:
                pass
        return get_item(self.db, item["item_id"])

    # ------------------------------------------------------------------ phases
    def onboard(self) -> list[dict]:
        events.publish("phase", name="onboarding", text="Learning the job from Jan-Aug history")
        return policies.onboard(self.ctx)

    def discover(self, period: str) -> list[dict]:
        ctx, db = self.ctx, self.db
        created = []
        rec = db.q("SELECT r.record_id, r.src_id, r.txn_date, r.amount_cents, r.description FROM records r "
                   "LEFT JOIN reconciliation c USING(record_id) WHERE r.source='bank' AND r.period=? "
                   "AND c.record_id IS NULL ORDER BY r.txn_date", (period,))
        for r in rec:
            created.append(create_item(db, SYNC, "bank_line", f"bank:{r['src_id']}",
                                       f"Bank {r['txn_date']} {fmt(r['amount_cents'])} {r['description'][:38]}",
                                       period, [r["record_id"]]))
        return created

    def discover_reviews(self, period: str) -> list[tuple[dict, str, object]]:
        """Card review, duplicates, vendors, accruals - each finding becomes a work item."""
        ctx, db = self.ctx, self.db
        out = []
        for iss in skills.detect_card_issues(ctx, period):
            r = iss["record"]
            it = create_item(db, JARVIS_SYNC(), "card_review", f"ramp:{r['src_id']}",
                             f"Card {r['counterparty']} {fmt(r['amount_cents'])} - {iss['type']}", period, [r["record_id"]])
            out.append((it, iss["type"], iss))
        for dup in skills.detect_duplicates(ctx, period):
            b = dup["bill"]
            it = create_item(db, JARVIS_SYNC(), "duplicate_check", f"bill:{b['bill_id']}",
                             f"Bill {b['num']} {b['vendor']} {fmt(b['amount_cents'])} vs card", period,
                             [dup["card"]["record_id"]])
            out.append((it, "duplicate", dup))
        for info in skills.discover_vendor_names(ctx, period):
            it = create_item(db, JARVIS_SYNC(), "vendor_review", f"vendor:{info['name']}",
                             f"Vendor '{info['name']}' not in vendor master", period, [info["record"]["record_id"]])
            out.append((it, "vendor", info))
        for cand in skills.accrual_candidates(ctx, period):
            v = ctx.vendor(cand["vendor_id"])
            it = create_item(db, JARVIS_SYNC(), "accrual_review", f"accrual:{cand['vendor_id']}:{period}",
                             f"Accrual check {v['qbo_name']} {period}", period,
                             [d["doc_id"] for d in [cand.get("invoice"), cand.get("timesheet"), cand.get("sow")] if d])
            out.append((it, "accrual", cand))
        for d in ctx.docs("bank_notice"):
            if str(d["fields"].get("period_end", ""))[:7] == period:
                it = create_item(db, JARVIS_SYNC(), "accrual_review", f"interest:{period}",
                                 f"Interest earned {period} (credited next month)", period, [d["doc_id"]])
                out.append((it, "interest", d))
        return out

    def process_item(self, item: dict, kind: str = "bank_line", payload=None) -> dict:
        ctx = self.ctx
        item = get_item(self.db, item["item_id"])   # always act on the current state
        if item["state"] not in ("NEW",):
            return item
        events.publish("focus", item_id=item["item_id"], title=item["title"])
        self.pause(0.6)
        if kind == "bank_line":
            plan = skills.plan_bank_line(ctx, item)
        elif kind == "personal":
            plan = skills.plan_card_personal(ctx, item, payload)
        elif kind == "refund":
            plan = skills.plan_card_refund(ctx, item, payload)
        elif kind == "duplicate":
            plan = skills.plan_duplicate(ctx, item, payload)
        elif kind == "vendor":
            plan = skills.plan_vendor(ctx, item, payload)
        elif kind == "accrual":
            plan = skills.plan_accrual(ctx, item, payload)
        elif kind == "interest":
            plan = skills.plan_interest_accrual(ctx, item, payload)
        elif kind == "paypal_balance":
            plan = skills.plan_paypal_balance_payment(ctx, item)
        else:
            raise ValueError(kind)
        if llm.available() and plan.action == "propose" and plan.kind in ("paypal_split", "accrual", "duplicate"):
            better = llm.complete("You are Jarvis, an autonomous staff accountant. Rewrite this rationale in 2-4 crisp "
                                  "sentences for the Controller. Keep every number exactly as given. No new facts.",
                                  plan.rationale, fast=True, max_tokens=300)
            if better:
                plan.rationale = better
        it = self._apply(item, plan)
        return self.route(it)

    def run_close(self, period: str | None = None) -> dict:
        period = period or self.period
        ctx = self.ctx
        events.publish("phase", name="close", text=f"Closing {period}")
        t0 = time.time()
        
        # Auto-onboard policies if any are pending (fixes order dependence bug I)
        from jarvis.agent import personas
        personas.auto_controller(self, max_rounds=1)
        
        # 1) every unreconciled bank line is work
        for it in self.discover(period):
            self.process_item(it, "bank_line")
        # 2) PayPal payments made from the balance (never in the bank feed)
        consumed = ctx.consumed_records()
        for p in ctx.records("source='paypal' AND period=? AND amount_cents<0", (period,)):
            if p["fields"].get("type") in skills.PAYPAL_PAYMENT_TYPES and p["record_id"] not in consumed:
                it = create_item(self.db, JARVIS_SYNC(), "paypal_review", f"paypal:{p['src_id']}",
                                 f"PayPal payment {p['counterparty']} {fmt(p['amount_cents'], p['currency'])} (from balance)",
                                 period, [p["record_id"]])
                self.process_item(it, "paypal_balance")
        # 3) reviews: cards, duplicates, vendors, accruals
        for it, kind, payload in self.discover_reviews(period):
            self.process_item(it, kind, payload)
        events.publish("phase", name="close_done", text=f"First pass done in {time.time() - t0:.1f}s")
        return self.status(period)

    def run_october(self) -> dict:
        """Late October data: accrual reversals/true-ups, the interest receipt, aging."""
        ctx, db = self.ctx, self.db
        events.publish("phase", name="october", text="October arrivals: invoices for September work")
        for it in self.discover("2026-10"):
            self.process_item(it, "bank_line")
        acc_items = db.q("SELECT item_id FROM work_items WHERE kind='accrual' AND state='POSTED' AND period=?",
                         (self.period,))
        for row in acc_items:
            ai = get_item(db, row["item_id"])
            vid = ai["proposal"].get("vendor_id")
            if not vid:
                continue
            entry = db.one("SELECT entry_id FROM ledger_entries WHERE work_item_id=?", (ai["item_id"],))
            amount = ai["proposal"]["accrual_amount"]
            acct = next(l["acct"] for l in ai["proposal"]["lines"] if l["acct"] != "2100")
            acc = {"vendor_id": vid, "amount": amount, "acct": acct, "period": ai["period"], "item_id": ai["item_id"],
                   "entry_id": entry["entry_id"] if entry else ""}
            bill = db.one("SELECT * FROM bills WHERE vendor_id=? AND service_period=? AND status IN ('Open','Paid') "
                          "AND date > ?", (vid, ai["period"], f"{ai['period']}-31"))
            if bill:
                it = create_item(db, JARVIS_SYNC(), "accrual_trueup", f"trueup:{vid}:{ai['period']}",
                                 f"True-up {ctx.vendor(vid)['qbo_name']} {ai['period']} accrual vs invoice", "2026-10",
                                 [ai["item_id"], bill["bill_id"]])
                if it["state"] == "NEW":
                    plan = skills.plan_accrual_reversal(ctx, it, acc, bill)
                    self.route(self._apply(it, plan))
            else:
                it = create_item(db, JARVIS_SYNC(), "aging", f"aging:{vid}:{ai['period']}",
                                 f"No invoice yet: {ctx.vendor(vid)['qbo_name']} ({ai['period']} accrual {fmt(amount)})",
                                 "2026-10", [ai["item_id"]])
                if it["state"] == "NEW":
                    plan = skills.Plan(kind="aging", action="ask", date="2026-10-12", escalate=True, confidence=0.8,
                                       evidence=[skills.ev("ledger", acc["entry_id"], f"Open accrual {fmt(amount)}")],
                                       question=f"{ctx.vendor(vid)['qbo_name']} still hasn't invoiced {ai['period']} "
                                                f"({fmt(amount)} accrued). Second request sent - keep the accrual open, "
                                                f"or do you know something I don't?",
                                       rationale="Accrual stays open; invoice is overdue vs this vendor's terms. Chasing "
                                                 "again and escalating aging.")
                    self._apply(it, plan)
                    self.send("jarvis", f"vendor:{ctx.vendor(vid)['qbo_name']}", "Second request: invoice",
                              f"Hi - following up on the invoice for your {ai['period']} work. Thanks!", it["item_id"])
        return self.status("2026-10")

    # ------------------------------------------------------------------ human answers & rejections
    def after_answer(self, item_id: str):
        """Agent re-plans an item that came back from NEEDS_INFO with the human's answer."""
        it = get_item(self.db, item_id)
        if it["state"] != "NEW":
            return it
        ans = it["answer"] or ""
        rec = self.ctx.record(it["source_refs"][0]) if it["source_refs"] else None
        acct = _account_from_text(ans)
        if rec is None or acct is None:
            plan = skills.Plan(kind=it["kind"] if it["kind"] != "bank_line" else "unknown", action="ask",
                               date=(rec or {}).get("txn_date", ""), confidence=0.3, escalate=True,
                               evidence=[skills.ev("person", "maya", "Controller answer", "context", ans[:120])],
                               question=f"Thanks - which account should '{(rec or {}).get('description', it['title'])[:50]}' go to?",
                               rationale="The answer didn't identify an account; asking a narrower question.")
            return self._apply(it, plan)
        amt = -rec["amount_cents"]
        ros = self.ctx.search.search(ans, kind="doc", k=2)
        evid = [skills.ev("record", rec["record_id"], f"Bank {rec['txn_date']} {fmt(rec['amount_cents'])}", "supports",
                          rec["description"][:80]),
                skills.ev("person", "maya", "Controller's answer", "supports", ans[:160])]
        if ros:
            evid.append(skills.ev("doc", ros[0]["id"], ros[0]["id"], "supports", ros[0]["highlight"][:120]))
        plan = skills.Plan(kind="answered", date=rec["txn_date"], memo=f"{rec['description'][:40]} per Controller",
                           lines=[skills.L_(acct, amt, ans[:80]), skills.L_("1010", -amt)], reconcile=[rec["record_id"]],
                           confidence=0.9, evidence=evid,
                           rationale=f"Maya answered: \"{ans[:200]}\". Booking {fmt(amt)} to {acct} "
                                     f"{bible.acct_name(acct)}" + (f"; consistent with {ros[0]['id']}." if ros else "."))
        return self.route(self._apply(it, plan))

    def after_reject(self, item_id: str) -> dict | None:
        """A 'no' becomes precedent; Jarvis re-plans with the correction and checks if it should generalize."""
        it = get_item(self.db, item_id)
        reason = it.get("answer") or ""
        amt = _amount_from_text(reason)
        pid = None
        if it["kind"] == "accrual" and amt:
            vid = it["proposal"].get("vendor_id")
            pid = policies.record_precedent(self.db, "controller_correction",
                                            f"{it['title']}: proposed {fmt(it['proposal']['accrual_amount'])}; Controller "
                                            f"corrected to {fmt(amt)} - {reason[:160]}",
                                            {"vendor_id": vid, "proposed_cents": it["proposal"]["accrual_amount"],
                                             "corrected_cents": amt, "tag": "verbal_discount"},
                                            "human_controller (Maya Chen)", {"item_id": item_id}, item_id,
                                            it["proposal"]["date"])
            new = create_item(self.db, JARVIS_SYNC(), "accrual_review", it["anchor"], it["title"] + " (revised)",
                              it["period"], it["source_refs"], parent_id=item_id)
            lines = [dict(l, cents=amt if l["cents"] > 0 else -amt) for l in it["proposal"]["lines"]]
            plan = skills.Plan(kind="accrual", date=it["proposal"]["date"], memo=it["proposal"]["memo"] + " (confirmed amount)",
                               name=it["proposal"].get("name", ""), lines=lines, confidence=0.95,
                               policy_id=it.get("policy_id"), precedent_ids=[pid] + (it.get("precedent_ids") or []),
                               evidence=(it.get("evidence") or []) + [skills.ev("person", "maya", "Controller correction",
                                                                                 "supports", reason[:160]),
                                                                       skills.ev("precedent", pid, "new precedent", "supports")],
                               extra={"vendor_id": vid, "accrual_amount": amt, "method": "confirmed by vendor via Controller"},
                               rationale=f"Controller rejected {fmt(it['proposal']['accrual_amount'])}: \"{reason[:160]}\". "
                                         f"Re-proposed at the confirmed {fmt(amt)}; the correction is now precedent {pid}.")
            out = self._apply(new, plan)
            policies.maybe_generalize(self.ctx, "controller_correction")
            return out
        return None

    # ------------------------------------------------------------------ status
    def status(self, period: str | None = None) -> dict:
        period = period or self.period
        rows = self.db.q("SELECT state, COUNT(*) n FROM work_items GROUP BY state")
        rec = ledger.bank_reconciliation(self.db, self.period)
        tb = ledger.trial_balance(self.db)
        return {"states": {r["state"]: r["n"] for r in rows}, "bank_rec": {k: v for k, v in rec.items() if k != "unreconciled"},
                "unreconciled": rec["unreconciled"], "trial_balance_ok": tb["ok"],
                "pending_controller": self.db.one("SELECT COUNT(*) n FROM work_items WHERE state IN ('PROPOSED','NEEDS_INFO')")["n"]}


def JARVIS_SYNC():
    """Discovery of review findings is done by the agent identity but item creation is a sync-role action:
    Jarvis asks the sync job to open the item (the agent itself can't create records)."""
    return SYNC


ACCOUNT_HINTS = [
    (r"crew|stage ?hand|load[- ]out|rigging|lighting|vj", "5010"),
    (r"gear|rental|truss|motor", "5020"),
    (r"software|subscription|saas", "6410"),
    (r"travel|flight|hotel|uber", "6430"),
    (r"meal|dinner|lunch", "6440"),
    (r"advertis|marketing|promo", "6420"),
    (r"personal|employee", "1250"),
    (r"fee|bank charge", "6810"),
    (r"office|supplies", "6900"),
]


def _account_from_text(t: str) -> str | None:
    m = re.search(r"\b(1[0-3]\d0|2\d{3}|[456]\d{3})\b", t)
    if m and m.group(1) in bible.COA:
        return m.group(1)
    low = t.lower()
    for rx, acct in ACCOUNT_HINTS:
        if re.search(rx, low):
            return acct
    return None


def _amount_from_text(t: str) -> int | None:
    m = re.search(r"\$\s?([\d,]+(?:\.\d{2})?)", t or "")
    return to_cents(m.group(1)) if m else None
