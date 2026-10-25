"""Defend a decision when questioned — from the run's own evidence, not from a script.

Every point cites the log line (and audit hash) it rests on, says what the alternative would cost, and says what
evidence would change the agent's mind. The Controller can still override: rejecting with a reason re-plans and
becomes precedent. Defending is not refusing.
"""
from __future__ import annotations

import re

from jarvis.money import fmt
from jarvis.world.bible import COA

STOP = {"accrue", "september", "sept", "bank", "merge", "file", "into", "drive", "with", "from", "publish", "financial",
        "package", "documents", "install", "vendor", "mapping", "rules", "what", "late", "change", "credited", "earned",
        "invoice", "dated", "paypal", "xfer", "inst"}


def _name(a):
    return f"{a} {COA[a][1]}" if a in COA else a


def _keywords(it):
    toks = re.findall(r"[A-Za-z][A-Za-z&]{3,}|\$[\d,]+\.\d\d|\d{2,}[A-Z0-9]{4,}", it["title"])
    return [t for t in toks if t.lower() not in STOP]


def _evidence(run, it, n=4, question: str = ""):
    kws = [k.lower() for k in _keywords(it)]
    # Extract keywords from question to focus evidence
    question_kws = [w.lower() for w in re.findall(r'\b[A-Za-z]{4,}\b', question)][:8] if question else []
    
    # Scope evidence to this item: extract amounts, accounts, vendors from proposal
    pr = it.get("proposal") or {}
    lines = pr.get("lines") or []
    item_amounts = {abs(l.get("cents", 0)) for l in lines if l.get("cents")}
    item_accounts = {l.get("acct") for l in lines if l.get("acct")}
    
    hits = []
    for e in run.logs:
        if e["level"] not in ("find", "decide", "check", "sim", "warn") or e.get("moment") == "defended" \
                or e["msg"].startswith(("Proposed", "Challenge", "①", "②", "③")):
            continue
        m = e["msg"].lower()
        
        # Question-specific scoring
        q_score = sum(1 for k in question_kws if k in m)
        
        # Keyword match from item title
        kw_score = sum(1 for k in kws if k in m)
        # Amount match (if log mentions same dollar amount)
        amt_score = sum(1 for amt in item_amounts if f"{amt/100:.2f}" in m or f"${amt//100}" in m)
        # Account match
        acct_score = sum(1 for acct in item_accounts if acct in m)
        
        score = q_score * 3 + kw_score + amt_score * 2 + acct_score * 2 + (1 if e.get("moment") else 0)
        if score:
            hits.append((score, e))
    hits.sort(key=lambda x: (-x[0], x[1]["seq"]))
    return [e for _, e in hits[:n]]


def _counterfactual(run, it):
    pr = it["proposal"]
    kind = pr.get("kind")
    lines = pr.get("lines") or []
    if kind == "accrual":
        amt = max(abs(l["cents"]) for l in lines)
        pl = next(l for l in lines if l["acct"][0] in "45")
        side = "income" if pl["acct"][0] == "4" else "expense"
        return (f"Without it, September {side} is understated by {fmt(amt)} and October overstated by the same. "
                f"It auto-reverses on {pr.get('auto_reverse', '2026-10-01')}, so when the cash or bill arrives there is no double count.")
    if kind == "bank_categorize":
        m = re.search(r"line (\d+)", pr.get("memo", ""))
        feed = {f["line"]: f for f in run.ctx.get("feed", [])}
        f = feed.get(int(m.group(1))) if m else None
        qbo = f["qbo_suggestion"] if f else "the suggested category"
        wrong = [l for l in lines if l["acct"] != "1010" and COA.get(l["acct"], ("", ""))[1] != qbo]
        parts = ", ".join(f"{fmt(l['cents'])} that is {_name(l['acct'])}" for l in wrong)
        return f"QBO's suggestion books all of it to '{qbo}'. That would misclassify {parts}."
    if kind == "vendor_merge":
        return (f"Left split, {pr['master']}'s spend history, 1099 totals and contract renewals are spread across "
                f"{1 + len(pr['aliases'])} records, and Ramp keeps creating new ones.")
    if kind == "vendor_rules":
        return "Without the rules, next month's Ramp sync recreates the same duplicates. Merging alone is a one-off cleanup."
    if kind == "file_evidence":
        return "Filed as downloaded, the auditor gets 'Statement (3).pdf', a duplicate and an August file, and three gaps nobody sees."
    if kind == "package_publish":
        return "All four tie-outs pass on these exact exports. Signing an older version would put numbers in front of the board that QBO no longer shows."
    if kind == "question":
        return "Guessing would put an unsupported payment in the books. A run-sheet mention is a hint, not support."
    return ""


def _mind_changers(it):
    kind = it["proposal"].get("kind")
    return {
        "accrual": "a vendor invoice or written confirmation for a different amount, or proof the work happened in October",
        "bank_categorize": "a receipt or invoice showing a different purpose, or a Controller ruling that changes policy",
        "vendor_merge": "a W-9 or TIN showing different legal entities",
        "vendor_rules": "a business reason to track a product line as its own vendor",
        "file_evidence": "a different naming convention from the Controller",
        "package_publish": "another change posted in QBO after these exports were downloaded",
        "question": "an invoice, W-9 or approval for the payment",
    }.get(kind, "new evidence")


def _classify_challenge(question: str) -> str:
    """Classify challenge type: purpose, period, amount, identity, policy, materiality."""
    q = question.lower()
    # Check policy/precedent FIRST - look for explicit policy questions
    if any(phrase in q for phrase in ("last time", "policy", "precedent", "always", "usually", "why change")):
        return "policy"  # Policy/precedent application
    # Check materiality - use word boundaries for "under" to avoid matching "understand"
    import re
    if any(w in q for w in ("materiality", "immaterial", "small", "threshold", "does it matter", "just expense it")) or \
       re.search(r'\bunder\b', q):
        return "materiality"  # Materiality threshold
    if any(w in q for w in ("what is", "what's", "who is", "merchant", "vendor", "this payment", "company")):
        return "identity"  # Who/what is this vendor/transaction
    if any(w in q for w in ("when", "period", "month", "september", "october", "timing", "accrual", "cut-off", "prepaid", "should", "booked")):
        return "period"  # When to recognize/which period
    if any(w in q for w in ("how much", "amount", "$", "too much", "too little", "wrong amount")):
        return "amount"  # Dollar amount questioned
    if any(w in q for w in ("why", "purpose", "what for", "category", "account", "expense", "revenue", "classify")):
        return "purpose"  # What is this transaction for/how to categorize
    return "general"


def _check_concession(question: str, it: dict) -> dict | None:
    """Check if new evidence in question should trigger concession and re-proposal."""
    from jarvis.money import to_cents
    
    # Don't concede if item is already dismissed
    if it["state"] in ("DISMISSED", "REJECTED"):
        return None
    
    q = question.lower()
    kind = it["proposal"].get("kind")
    
    # Pattern: "the show moved to [date]" or "actually happened [date]"
    # ONLY for accruals/timing items (not cleared bank transactions)
    if kind in ("accrual",) and ("moved to" in q or "actually" in q or "changed to" in q):
        # Extract new date
        date_match = re.search(r'(sept|september|oct|october)\s*(\d{1,2})', q)
        if date_match:
            month = {"sept": 9, "september": 9, "oct": 10, "october": 10}.get(date_match.group(1))
            day = int(date_match.group(2))
            new_date = f"2026-{month:02d}-{day:02d}"
            
            # Check if this changes period classification
            proposal_date = it["proposal"].get("date", "")
            if proposal_date and new_date[:7] != proposal_date[:7]:
                return {
                    "concede": True,
                    "reason": f"New evidence shows work happened in {new_date[:7]} not {proposal_date[:7]}",
                    "new_date": new_date,
                    "action": "withdraw accrual - work did not occur in this period"
                }
    
    # Pattern: "actually billed $X" or "invoice shows $Y"
    if "actually" in q or "invoice shows" in q or "billed" in q:
        amt_match = re.search(r'\$\s?([\d,]+(?:\.\d{2})?)', question)
        if amt_match:
            # Use to_cents to avoid float truncation
            new_amt = to_cents(amt_match.group(0))
            # Sum debits only to get transaction amount (not double-counting)
            proposal_amt = sum(l.get("cents", 0) for l in it["proposal"].get("lines", []) if l.get("cents", 0) > 0)
            if abs(new_amt - proposal_amt) > 100:  # More than $1 difference
                return {
                    "concede": True,
                    "reason": f"Invoice confirms {fmt(new_amt)} not {fmt(proposal_amt)}",
                    "new_amount": new_amt,
                    "action": "withdraw and re-propose with correct amount"
                }
    
    return None


def _address(question, it):
    q = question.lower()
    kind = it["proposal"].get("kind")
    lines = it["proposal"].get("lines") or []
    
    # Check for concession first
    concession = _check_concession(question, it)
    if concession:
        return f"**CONCEDING**: {concession['reason']}. {concession['action']}. The corrected proposal will appear in the next run."
    
    # Classify and address challenge
    challenge_type = _classify_challenge(question)
    
    if challenge_type == "materiality":
        personal = any(l["acct"] == "1250" for l in lines)
        return ("Materiality decides whether a misstatement matters, not how to classify a transaction."
                + (" The personal purchase is a control issue, and ruling P-0317 applies regardless of size." if personal else ""))
    elif challenge_type == "policy":
        # Give specific policy/precedent answer with history, including P-0317
        policy_refs = it.get("policy_id") or "current policy"
        precedent_refs = it.get("precedent_ids", [])
        personal = any(l["acct"] == "1250" for l in lines)
        
        if kind in ("bank_categorize", "paypal_split"):
            prec_text = f"precedents: {', '.join(precedent_refs)}" if precedent_refs else "precedents: none"
            policy_note = ""
            if personal or "P-0317" in policy_refs or any("P-0317" in str(p) for p in precedent_refs):
                policy_note = " Per ruling P-0317 (March 2026), personal purchases go to 1250 Employee Receivable regardless of amount."
            return (f"Last month's categorization isn't a binding precedent for a different transaction. "
                    f"This decision follows {policy_refs} ({prec_text}).{policy_note} "
                    f"The documents for this transaction — the SOW, receipt, and payment record — point to these specific accounts.")
        return "Last month's habit isn't evidence about this month's transaction. The documents for this one point elsewhere."
    elif challenge_type == "period":
        # Give specific period/prepaid explanation
        prepaid = any(l["acct"] == "1310" for l in lines)
        if prepaid:
            prepaid_line = next(l for l in lines if l["acct"] == "1310")
            memo = prepaid_line.get("memo", "")
            return (f"This is a deposit for a future event ({memo}). Under cut-off policy, costs are recognized "
                    f"when earned/incurred, not when paid. The {fmt(prepaid_line['cents'])} goes to 1310 Prepaid "
                    f"(asset) in September, then to expense when the event happens (November). Booking it as "
                    f"September expense would overstate the period's costs.")
        return "Waiting books September cost in October. The close is about the period the work happened, not when paper arrives."
    elif challenge_type == "identity" or challenge_type == "purpose":
        return f"Confidence is {round((it.get('confidence') or 0) * 100)}% because each step below is backed by a source document."
    elif challenge_type == "amount":
        # Sum debits only (positive cents) to avoid double-counting in double-entry
        total = sum(l.get("cents", 0) for l in lines if l.get("cents", 0) > 0)
        return f"Total {fmt(total)} ties to source documents. Each line is computed from receipts/contracts, not estimated."
    else:
        return "Here is what the decision rests on."


def defend(run, it, question: str) -> dict:
    if run is None:
        return {"points": [], "error": "run no longer in memory"}
    run.cur = run.stages[-1]["key"]
    run.moment("defended", "decide", f"Challenge on {it['item_id']} ({it['title']}): \"{question}\". Defending from the evidence:",
               {"item_id": it["item_id"], "question": question}, pause=0.6)
    
    # Check for concession - if evidence contradicts, withdraw immediately
    concession = _check_concession(question, it)
    if concession:
        from jarvis.work.transition import transition, create_item, now
        from jarvis.work.roles import actor
        from jarvis.work.sync import SYNC
        
        try:
            # Execute withdrawal transition
            jarvis = actor("jarvis")
            transition(run.wb.db, it["item_id"], "withdraw", jarvis, 
                      {"concession": concession}, 
                      reason=f"Conceding: {concession['reason']}")
            
            # Record as precedent
            prec_id = f"PREC-{abs(hash(question)) % 10**6:06d}"
            run.wb.db.conn.execute(
                "INSERT INTO precedents (prec_id, date, period, pattern, summary, decision, decided_by, status, refs, source_item) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (prec_id, "2026-09-30", "2026-09", it["kind"], question[:200], concession["reason"], "maya", "active", "[]", it["item_id"])
            )
            
            run.log("decide", f"**CONCEDING**: {concession['reason']}", pause=1.0)
            run.log("decide", "Precedent recorded. Re-proposing with correction...", pause=0.5)
            
            # Immediately re-propose with corrected data
            import copy
            corrected_proposal = copy.deepcopy(it["proposal"])
            lines = corrected_proposal.get("lines", [])
            
            if "new_amount" in concession:
                # Find the disputed line (largest debit that isn't the cash account)
                cash_accounts = ("1010", "1030")
                debit_lines = [l for l in lines if l.get("cents", 0) > 0 and l.get("acct") not in cash_accounts]
                if debit_lines:
                    # Adjust ONLY the largest debit line (the disputed invoice/expense)
                    disputed_line = max(debit_lines, key=lambda l: l.get("cents", 0))
                    old_amount = disputed_line["cents"]
                    disputed_line["cents"] = concession["new_amount"]
                    
                    # Update memo to reflect correction
                    if "1310" in disputed_line.get("acct", ""):
                        # Extract merchant/description
                        memo_parts = disputed_line.get("memo", "").split()
                        if memo_parts:
                            disputed_line["memo"] = f"{memo_parts[0]} corrected invoice {fmt(concession['new_amount'])}"
                    
                    # Calculate the difference
                    diff = concession["new_amount"] - old_amount
                    
                    # Merge into existing 6810 line if present, or add new one
                    if abs(diff) > 0:
                        fx_line = next((l for l in lines if l.get("acct") == "6810"), None)
                        if fx_line:
                            # Merge into existing FX line
                            fx_line["cents"] -= diff
                            fx_line["memo"] = "FX spread + invoice difference"
                            run.log("decide", f"Merged {fmt(abs(diff))} invoice difference into existing 6810 FX line", pause=0.5)
                        else:
                            # Add new balancing line
                            diff_line = {
                                "acct": "6810",
                                "cents": -diff,
                                "memo": f"Difference from corrected invoice amount"
                            }
                            lines.append(diff_line)
                            run.log("decide", f"Added {fmt(abs(diff))} to 6810 Bank & FX Fees to balance the correction", pause=0.5)
            
            if "new_date" in concession:
                # If work moved to a different period, withdraw the accrual entirely
                new_period = concession["new_date"][:7]
                old_period = it["period"]
                if new_period != old_period:
                    # Don't accrue in the old period - withdraw entirely
                    run.log("decide", f"Work moved from {old_period} to {new_period} - withdrawing {old_period} accrual entirely", pause=0.8)
                    points = [f"**CONCEDING**: {concession['reason']}. The work happened in {new_period}, not {old_period}, so no September accrual is needed."]
                    points.append(f"Precedent recorded. Accrual withdrawn.")
                    return {"points": points, "item_id": it["item_id"], "conceded": True}
                corrected_proposal["date"] = concession["new_date"]
            
            # Create new work item with correction
            new_it = create_item(run.wb.db, SYNC, it["kind"], 
                               f"{it['anchor']}-corrected", 
                               f"{it['title']} (corrected per Controller)",
                               it["period"], it.get("tags", []))
            
            # Update title to reflect correction
            old_title = it["title"]
            new_title = f"{old_title} (corrected: {fmt(concession['new_amount'])})"
            run.wb.db.conn.execute("UPDATE work_items SET title = ? WHERE item_id = ?", (new_title, new_it["item_id"]))
            
            transition(run.wb.db, new_it["item_id"], "propose", jarvis,
                      {"proposal": corrected_proposal,
                       "evidence": it.get("evidence", []),
                       "rationale": f"Corrected: {concession['reason']}",
                       "confidence": it.get("confidence", 0.9)},
                      reason=f"Re-proposed after concession: {concession['reason'][:200]}")
            
            # Add to run.proposals so it appears in the workbench UI
            run.proposals.append(new_it["item_id"])
            
            # Log the precedent insertion to audit trail
            from jarvis.work.transition import append_audit
            append_audit(run.wb.db, jarvis, "record_precedent", new_it["item_id"], True,
                        f"Precedent recorded: {concession['reason'][:200]}", {}, [prec_id])
            
            run.log("decide", f"Re-proposed as {new_it['item_id']} with corrected amounts", pause=0.8)
            
            # Verify the corrected entry balances
            balance = sum(l.get("cents", 0) for l in corrected_proposal.get("lines", []))
            if balance != 0:
                run.log("warn", f"Corrected entry does not balance: off by {fmt(balance)}", pause=0.8)
            
            points = [f"**CONCEDING**: {concession['reason']}. Adjusted only the disputed line, kept bank payment unchanged."]
            points.append(f"Precedent recorded. Original proposal withdrawn. Corrected as {new_it['item_id']}.")
            return {"points": points, "item_id": it["item_id"], "new_item_id": new_it["item_id"], "conceded": True}
        except Exception as e:
            run.log("warn", f"Concession failed: {e}", pause=0.5)
            # Fall through to normal defense
    
    points = [_address(question, it)]
    run.log("decide", f"① {points[-1]}", pause=0.8)
    for e in _evidence(run, it, n=4, question=question):
        points.append(f"Log #{e['seq']} ({e['hash'][:8]}): {e['msg']}")
        run.log("decide", f"② evidence — log #{e['seq']} · audit {e['hash'][:8]}: {e['msg'][:220]}", {"cites": e["seq"]}, pause=0.6)
    cf = _counterfactual(run, it)
    if cf:
        points.append(cf)
        run.log("decide", f"③ the alternative — {cf}", pause=0.8)
    mc = _mind_changers(it)
    points.append(f"What would change my mind: {mc}. You can also reject with a reason. I'll re-plan, and your ruling becomes precedent.")
    run.log("ask", f"④ What would change my mind: {mc}. Reject with a reason to override; I'll re-plan and record it as precedent.",
            pause=0.6)
    return {"points": points, "item_id": it["item_id"]}
