"""Defend a decision when questioned: answer from the item's own evidence, policies and precedents.

Without an API key the defense is assembled deterministically from the dossier (every number recomputed);
with a key Claude writes it, constrained to the same dossier."""
from __future__ import annotations

from jarvis import config
from jarvis.agent import llm
from jarvis.agent.context import JARVIS
from jarvis.money import fmt
from jarvis.work import events
from jarvis.work.roles import actor
from jarvis.work.transition import get_item, log
from jarvis.world import bible

TRUST = {
    "paypal_split": "Cash: bank statement > PayPal > descriptor. Purpose: SOW/receipt > PayPal item > bank text. "
                    "Period: contract service date > payment date.",
    "accrual": "Measurement: invoice > contract rate x approved hours > flat fee with performance evidence > vendor "
               "estimate. A contract alone is a commitment, not performance.",
    "vendor_link": "Identity: invoice issuer legal name / domain / TIN > ERP vendor id > card merchant > product name.",
    "vendor_create": "Identity: invoice issuer legal name / domain / TIN > ERP vendor id > card merchant > product name.",
    "reclass": "Ruling P-0317: personal purchases go to 1250 regardless of amount; Ramp's category is a suggestion.",
    "duplicate": "One economic event, one expense: the card charge is the payment of record; the bill duplicates it.",
}


def _dossier(item: dict) -> str:
    lines = "\n".join(f"  {l['acct']} {bible.acct_name(l['acct'])}: {fmt(l['cents'])}  ({l.get('memo', '')})"
                      for l in item["proposal"].get("lines", []))
    evid = "\n".join(f"  [{e['relation']}] {e['type']} {e['id']}: {e['label']} {e.get('detail', '')}"
                     for e in item.get("evidence", []))
    
    # Include materiality threshold and P-0317 context
    materiality = fmt(bible.APPROVAL_MATRIX.get("materiality_cents", 50000))
    p0317_note = ("\nRuling P-0317 (March 2026): Personal purchases on company cards/PayPal go to 1250 Employee Receivable "
                  "regardless of amount. Materiality ($500) applies to judgment calls, not control issues like personal purchases.")
    
    return (f"Item {item['item_id']} ({item['kind']}, state {item['state']}): {item['title']}\nProposed lines:\n{lines}\n"
            f"Rationale: {item['rationale']}\nEvidence:\n{evid}\nPolicies: {item.get('policy_id')}\n"
            f"Precedents: {item.get('precedent_ids')}\nTrust ranking: {TRUST.get(item['kind'], 'n/a')}\n"
            f"Materiality threshold: {materiality}{p0317_note}")


def _template(item: dict, question: str) -> str:
    q = question.lower()
    lines = item["proposal"].get("lines", [])
    pl = [l for l in lines if l["acct"][0] in "456" and l["cents"] > 0]
    bs = [l for l in lines if l["acct"][0] in "123" and l["cents"] > 0 and l["acct"] not in ("1010", "1030")]
    out = []
    if item["kind"] == "paypal_split" and ("expense" in q or "software" in q or "materiality" in q or "always" in q):
        total = -sum(l["cents"] for l in lines if l["acct"] in ("1010", "1030"))
        not_expense = sum(l["cents"] for l in bs)
        personal_line = next((l for l in lines if l["acct"] == "1250"), None)
        out.append(f"Booking the whole {fmt(total)} as Software Expense would overstate September operating expenses by "
                   f"{fmt(not_expense)} - money that isn't a September expense at all:")
        for l in bs:
            if l["acct"] == "1310":
                out.append(f"• {fmt(l['cents'])} is a deposit for a show that hasn't happened yet ({l['memo']}). Under our "
                           f"cut-off policy it's a prepaid asset until the show, then crew cost - not software.")
            elif l["acct"] == "1250":
                out.append(f"• {fmt(l['cents'])} is a personal purchase. Ruling P-0317 says amount doesn't matter: it's an "
                           f"employee receivable and a control issue, so materiality isn't the test.")
        fee = next((l for l in lines if l["acct"] == "6810"), None)
        sw = next((l for l in lines if l["acct"] == "6410"), None)
        if fee:
            out.append(f"• {fmt(fee['cents'])} is PayPal's FX spread - a real cost, but a bank/FX fee, not software.")
        if sw:
            out.append(f"• Only {fmt(sw['cents'])} is actually software ({sw['memo']}).")
        if personal_line and "materiality" in q:
            out.append(f"The {fmt(personal_line['cents'])} personal purchase is classified under P-0317 regardless of "
                      f"materiality because it's a control issue: employee reimbursables must be tracked separately.")
        out.append("Every figure ties to a source record: the bank line, the PayPal funding row, each payment and its "
                   "conversion row, the ECB rate and the SOW (click any node to see it).")
    elif item["kind"] == "accrual" and ("email" in q or "10k" in q or "estimate" in q or "why" in q or "lower" in q):
        out.append(item["rationale"])
        out.append("Why not the vendor's number: an informal email is the weakest evidence on our ranking; signed rate x "
                   "approved hours is auditable. If the invoice differs, October's reversal shows the true-up explicitly.")
    else:
        out.append(item["rationale"] or "This item has no rationale recorded.")
    sup = [e for e in item.get("evidence", []) if e["relation"] == "supports"]
    con = [e for e in item.get("evidence", []) if e["relation"] == "contradicts"]
    out.append(f"Evidence: {len(sup)} supporting source(s)" + (f", {len(con)} contradicting source(s) that I weighed: " +
                                                                "; ".join(f"{e['label']}" for e in con) if con else "") + ".")
    if item.get("policy_id"):
        out.append(f"Policy: {item['policy_id']}" + (f"; precedents {', '.join(item['precedent_ids'])}." if item.get("precedent_ids") else "."))
    out.append("What would change my mind: a document showing the service period or the counterparty is different "
               "from what the evidence says - send it and I'll revise the proposal (as a new, logged transition).")
    return "\n".join(out)


def defend(ctx, item_id: str, question: str, asker: str = "maya") -> dict:
    item = get_item(ctx.db, item_id)
    log(ctx.db, actor(asker), "challenge", item_id, question[:300])
    answer = None
    if llm.available():
        answer = llm.complete(
            "You are Jarvis, the autonomous staff accountant at Afterglow Labs. The Controller is challenging one of your "
            "decisions. Defend it (or concede if the dossier doesn't support it) using ONLY facts in the dossier. "
            "Quote amounts exactly. Be direct, 4-8 short sentences or bullets. End with what evidence would change your mind.",
            f"{_dossier(item)}\n\nController's challenge: {question}")
    if not answer:
        answer = _template(item, question)
    evid_ids = [e["id"] for e in item.get("evidence", [])]
    log(ctx.db, JARVIS, "defend", item_id, answer[:500], evid_ids)
    events.publish("defend", item_id=item_id, question=question, answer=answer, evidence=evid_ids)
    return {"item_id": item_id, "question": question, "answer": answer, "evidence": evid_ids,
            "llm": llm.available()}
