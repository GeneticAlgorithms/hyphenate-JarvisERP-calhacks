"""People Jarvis works with. A model (or a script, without a key) plays the Controller.

Maya Chen (Controller) is busy and terse, cares about cut-off, and sometimes says no. Her scripted
behaviour reproduces the demo exactly; with an API key she reasons over the dossier instead."""
from __future__ import annotations

from jarvis.agent import llm
from jarvis.money import fmt
from jarvis.work.roles import actor
from jarvis.work.transition import get_item, transition
from jarvis.work import events

MAYA = actor("maya")

SCRIPTED_ANSWERS = [
    ("lopez", "That's R. Lopez - the stagehand we paid via Zelle for load-out at the Fox Theater on 9/25. "
              "Book it to crew costs (5010)."),
]
SCRIPTED_REJECTIONS = [
    # (match on title/vendor, reason)
    ("nadia kroll", "Nadia texted me yesterday: she's billing $2,000.00 for the 25th - the set got cut short. "
                    "Accrue $2,000.00, not the SOW amount."),
]


def controller_decide(item: dict) -> tuple[str, str]:
    """Return ('approve'|'reject', reason)."""
    title = (item["title"] + " " + str(item.get("proposal", {}).get("name", ""))).lower()
    if item["kind"] == "accrual" and not item.get("parent_id"):
        for key, reason in SCRIPTED_REJECTIONS:
            if key in title:
                return "reject", reason
    if llm.available():
        out = llm.complete_json(
            "You are Maya Chen, Controller at Afterglow Labs. Busy, precise, cares about cut-off and segregation of "
            "duties. Approve or reject the proposed entry. Reject only for a concrete accounting reason.",
            f"Proposal: {item['title']}\nKind: {item['kind']}\nLines: {item['proposal'].get('lines')}\n"
            f"Rationale: {item['rationale']}\nReturn {{\"decision\": \"approve\"|\"reject\", \"reason\": \"...\"}}")
        if out and out.get("decision") in ("approve", "reject"):
            return out["decision"], out.get("reason", "")
    reasons = {"paypal_split": "Agree - deposit is for November, keep it in prepaid.",
               "accrual": "Fine - support is solid.", "reclass": "Yes. Make sure the employee gets the note.",
               "duplicate": "Good catch - void it.", "vendor_link": "Approved - link it.",
               "vendor_create": "Approved.", "accrual_reversal": "Approved.", "answered": "Thanks - approved.",
               "transfer": "Correct, it's just a top-up.", "paypal_payment": "Approved."}
    return "approve", reasons.get(item["kind"], "Approved.")


def controller_answer(item: dict) -> str:
    q = (item.get("question") or "").lower() + " " + item["title"].lower()
    for key, ans in SCRIPTED_ANSWERS:
        if key in q:
            return ans
    if llm.available():
        out = llm.complete("You are Maya Chen, Controller. Answer the accountant's question in one or two sentences. "
                           "If you genuinely don't know, say so and say what to do.", item.get("question", ""), fast=True)
        if out:
            return out
    if item["kind"] == "aging":
        return "Keep the accrual open - I'll ping her on Slack."
    return "I don't recognize it either. Leave it unreconciled; I'll check with ops tomorrow."


def act_on(engine, item_id: str) -> dict:
    """Controller handles one pending item end-to-end (used by the auto-controller and the eval)."""
    from jarvis.work import gateway
    it = get_item(engine.db, item_id)
    if it["state"] == "PROPOSED":
        decision, reason = controller_decide(it)
        if decision == "approve":
            transition(engine.db, item_id, "approve", MAYA, reason=reason)
            return gateway.post(engine.db, item_id)
        transition(engine.db, item_id, "reject", MAYA, {"answer": reason}, reason=reason)
        new = engine.after_reject(item_id)
        return new or get_item(engine.db, item_id)
    if it["state"] == "NEEDS_INFO":
        ans = controller_answer(it)
        if it["kind"] == "aging" or "don't recognize" in ans:
            # an answer that doesn't change the plan: log it, item stays with the human
            transition(engine.db, item_id, "answer", MAYA, {"answer": ans}, reason=ans)
            it2 = get_item(engine.db, item_id)
            if it["kind"] == "aging":
                return transition(engine.db, item_id, "dismiss", actor("jarvis"),
                                  {"rationale": "Controller: keep accrual open; vendor chased twice."},
                                  reason="Accrual kept open per Controller; will re-check next run")
            return it2
        transition(engine.db, item_id, "answer", MAYA, {"answer": ans}, reason=ans)
        return engine.after_answer(item_id)
    return it


def auto_controller(engine, max_rounds: int = 4) -> int:
    """Process everything waiting on the Controller (policies first), until quiet."""
    from jarvis.agent.policies import decide_policy
    n = 0
    for _ in range(max_rounds):
        did = 0
        for p in engine.db.q("SELECT policy_id, version FROM policies WHERE status='proposed'"):
            decide_policy(engine.db, p["policy_id"], p["version"], "approve", MAYA,
                          "Matches how we've always done it." if p["policy_id"] != "pol-008"
                          else "Yes - that's the rule. Generalize it.")
            did += 1
        for row in engine.db.q("SELECT item_id FROM work_items WHERE state IN ('PROPOSED','NEEDS_INFO') ORDER BY created_at"):
            engine.pause(0.5)
            act_on(engine, row["item_id"])
            did += 1
        n += did
        if not did:
            break
    return n
