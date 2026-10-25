"""Self-learning (onboarding) and self-improving (corrections) policies.

Onboarding: Jarvis reads the closed months' precedents, finds how this team handled each kind of
situation, and proposes a versioned policy citing the precedents as evidence. Nothing is active until
the Controller approves it.
Self-improving: when a correction matches earlier corrections, Jarvis proposes a general policy.
"""
from __future__ import annotations

from statistics import mean

from jarvis.money import plain
from jarvis.work import events
from jarvis.work.db import DB, J, L
from jarvis.work.roles import Actor, actor, can
from jarvis.work.transition import Denied, append_audit, now

TEMPLATES = {
    "paypal_split": ("pol-001", "PayPal instant transfer -> split to underlying payments",
                     "When a bank debit is a PayPal instant transfer that funds several PayPal payments, record the "
                     "underlying payments (vendor, account, period) instead of a single 'PayPal' expense."),
    "fx_fee": ("pol-002", "EUR payments at market rate; PayPal spread -> 6810",
               "Record foreign-currency payments at the ECB reference rate on the payment date; the difference to "
               "the USD actually paid is a conversion fee booked to 6810 Bank & FX Fees."),
    "personal": ("pol-003", "Personal purchases -> 1250 Employee Receivable (P-0317)",
                 "Purchases on company cards/PayPal in personal categories (apparel, department stores, cosmetics, "
                 "digital games) without a business memo/receipt go to 1250 Employee Receivable; notify the employee."),
    "prepaid_deposit": ("pol-004", "Deposits for future shows -> 1310 Prepaid Tour Costs",
                        "Payments for a show in a future period are prepaid assets until the show happens."),
    "accrual": ("pol-005", "Accrue performed-not-invoiced work at contract rate x approved hours",
                "At month end accrue services performed but not invoiced, measured by the best available evidence "
                "(invoice > rate x timesheet > flat fee with performance evidence > vendor estimate). Reverse when "
                "the bill arrives; the difference is the true-up."),
    "interest_accrual": ("pol-006", "Accrue interest earned; clear on receipt",
                         "Accrue the month's interest from the bank notice to 1260 at month end; when it is credited "
                         "on the 1st, clear 1260 instead of recording new income."),
    "vendor_alias": ("pol-007", "Product / descriptor names link to the legal-entity vendor",
                     "A product name (Claude, Cursor, Google Ads) is not a vendor. Link it to the legal entity on the "
                     "invoice/receipt; create a vendor only for a genuinely new legal entity."),
    "controller_correction": ("pol-008", "Accrue the amount a vendor/freelancer confirmed",
                              "When a vendor or freelancer confirms a different amount than the contract (discount, "
                              "shortened set), accrue the confirmed amount and cite the confirmation."),
}
MIN_PRECEDENTS = {"controller_correction": 3}


def _stats(pattern: str, precs: list[dict]) -> dict:
    if pattern == "accrual":
        ratios = [p["decision"]["actual_cents"] / p["decision"]["estimate_cents"] for p in precs
                  if p["decision"].get("estimate_cents")]
        return {"n": len(precs), "avg_actual_over_estimate": round(mean(ratios), 4) if ratios else None}
    if pattern == "fx_fee":
        spreads = [p["decision"].get("spread") for p in precs if p["decision"].get("spread") is not None]
        return {"n": len(precs), "avg_paypal_spread": round(mean(spreads), 4) if spreads else None}
    if pattern == "personal":
        mccs = sorted({m for p in precs for m in p["decision"].get("personal_mccs", [])} |
                      {p["decision"].get("mcc") for p in precs if p["decision"].get("mcc")})
        kws = sorted({k for p in precs for k in p["decision"].get("personal_merchant_keywords", [])})
        return {"n": len(precs), "mccs": mccs, "merchant_keywords": kws}
    if pattern == "interest_accrual":
        return {"n": len(precs), "avg_monthly_cents": int(mean(p["decision"]["amount_cents"] for p in precs))}
    return {"n": len(precs)}


def propose_policy(db: DB, pattern: str, evidence_ids: list[str], stats: dict, by: Actor) -> dict | None:
    pid, title, text = TEMPLATES[pattern]
    ok, why = can(by, "propose", "policy")
    cur = db.one("SELECT MAX(version) v FROM policies WHERE policy_id=?", (pid,))
    version = (cur["v"] or 0) + 1
    if cur["v"] and db.one("SELECT 1 FROM policies WHERE policy_id=? AND status IN ('proposed','active') "
                           "AND evidence=?", (pid, J(evidence_ids))):
        return None
    with db.tx():
        if ok:
            db.conn.execute("INSERT INTO policies(policy_id,version,pattern,title,rule_text,matcher,evidence,status,"
                            "proposed_by,approved_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                            (pid, version, pattern, title, text, J(stats), J(evidence_ids), "proposed", by.id, None, now()))
        append_audit(db, by, "propose_policy", f"{pid} v{version}", ok,
                     f"{title} - evidence: {len(evidence_ids)} precedents" if ok else why,
                     {"status": [None, "proposed"]} if ok else {}, evidence_ids)
    if not ok:
        raise Denied("propose_policy", pid, why)
    events.publish("policy", policy_id=pid, version=version, status="proposed", title=title, n=len(evidence_ids))
    return {"policy_id": pid, "version": version, "title": title, "evidence": evidence_ids, "stats": stats}


def decide_policy(db: DB, policy_id: str, version: int, decision: str, by: Actor, reason: str = "") -> dict:
    action = "approve" if decision == "approve" else "reject"
    p = db.one("SELECT * FROM policies WHERE policy_id=? AND version=?", (policy_id, version))
    ok, why = can(by, action, "policy")
    if ok and p["proposed_by"] == by.id:
        ok, why = False, "separation of duties: the proposer cannot approve its own policy"
    if ok and p["status"] != "proposed":
        ok, why = False, f"policy is {p['status']}"
    new = "active" if action == "approve" else "rejected"
    with db.tx():
        if ok:
            if new == "active":
                db.conn.execute("UPDATE policies SET status='superseded' WHERE policy_id=? AND status='active'", (policy_id,))
            db.conn.execute("UPDATE policies SET status=?, approved_by=? WHERE policy_id=? AND version=?",
                            (new, by.id, policy_id, version))
        append_audit(db, by, f"{action}_policy", f"{policy_id} v{version}", ok, reason if ok else why,
                     {"status": ["proposed", new]} if ok else {}, L(p["evidence"], []))
    if not ok:
        raise Denied(action, policy_id, why)
    events.publish("policy", policy_id=policy_id, version=version, status=new, title=p["title"])
    return {"policy_id": policy_id, "version": version, "status": new}


def onboard(ctx) -> list[dict]:
    """Learn the job from the company's history (Jan-Aug precedents)."""
    db = ctx.db
    out = []
    by_pattern: dict[str, list] = {}
    for p in ctx.precedents():
        by_pattern.setdefault(p["pattern"], []).append(p)
    ctx.tool("run_esql", "precedents", "FROM precedents | STATS n = COUNT(*) BY pattern  -> " +
             ", ".join(f"{k}:{len(v)}" for k, v in sorted(by_pattern.items())), [])
    for pattern, precs in sorted(by_pattern.items()):
        if pattern not in TEMPLATES:
            continue
        if len(precs) < MIN_PRECEDENTS.get(pattern, 1):
            ctx.think("onboarding", f"'{pattern}': only {len(precs)} precedents - not enough to generalize yet.")
            continue
        if ctx.active_policy(pattern):
            continue
        st = _stats(pattern, precs)
        res = propose_policy(db, pattern, [p["prec_id"] for p in precs], st, actor("jarvis"))
        if res:
            out.append(res)
    return out


def maybe_generalize(ctx, pattern: str) -> dict | None:
    """Self-improving: after a correction, see if it now has enough company to become policy."""
    precs = ctx.precedents(pattern)
    if pattern not in TEMPLATES or len(precs) < MIN_PRECEDENTS.get(pattern, 1) or ctx.active_policy(pattern):
        return None
    if ctx.db.one("SELECT 1 FROM policies WHERE pattern=? AND status='proposed'", (pattern,)):
        return None
    ctx.tool("search_precedents", pattern, f"found {len(precs)} similar corrections: " +
             ", ".join(p["prec_id"] for p in precs), [p["prec_id"] for p in precs])
    return propose_policy(ctx.db, pattern, [p["prec_id"] for p in precs], _stats(pattern, precs), actor("jarvis"))


def record_precedent(db: DB, pattern: str, summary: str, decision: dict, decided_by: str, refs: dict,
                     source_item: str, date: str) -> str:
    n = db.one("SELECT COUNT(*) c FROM precedents")["c"]
    pid = f"prec-{n + 101:03d}"
    with db.tx():
        db.conn.execute("INSERT INTO precedents(prec_id,date,period,pattern,summary,decision,decided_by,status,refs,"
                        "source_item) VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (pid, date, date[:7], pattern, summary, J(decision), decided_by, "approved", J(refs), source_item))
        append_audit(db, actor("sync"), "record_precedent", pid, True, summary[:200], {}, [source_item])
    events.publish("precedent", prec_id=pid, pattern=pattern, summary=summary)
    return pid


def fmt_stats(stats: dict) -> str:
    bits = []
    for k, v in stats.items():
        if k.endswith("_cents") and isinstance(v, int):
            bits.append(f"{k[:-6]}={plain(v)}")
        else:
            bits.append(f"{k}={v}")
    return ", ".join(bits)
