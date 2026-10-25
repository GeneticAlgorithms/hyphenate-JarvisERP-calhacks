"""Scenario Injector: judges type a scenario; it becomes new source records through a bounded set of
generator primitives (so free text can't corrupt the world), then Jarvis processes it live."""
from __future__ import annotations

import hashlib
import json
import re
import uuid

from jarvis.agent import llm
from jarvis.agent.context import JARVIS
from jarvis.money import fmt, to_cents
from jarvis.work import events


def _dollars_to_cents(amount) -> int:
    """Convert any amount representation (int, float, str) to cents, treating numbers as dollars."""
    if isinstance(amount, str):
        # String like "$1,234.56" - let to_cents handle it
        return to_cents(amount)
    # Treat int and float as dollars, not cents
    return to_cents(float(amount))
from jarvis.work.db import J
from jarvis.work.roles import actor
from jarvis.work.sync import _upsert
from jarvis.work.transition import append_audit, create_item, get_item, now, transition
from jarvis.world import bible, ids

SYNC = actor("sync")

TEMPLATES = {
    "unknown_debit": {"label": "Unknown bank debit", "params": {"amount": 742.18, "description": "SQ *MOONLIGHT GEAR CO",
                                                                "date": "2026-09-29"}},
    "invoice_over_accrual": {"label": "Vendor invoices more than we accrued",
                             "params": {"vendor": "Lumen Crew LLC", "amount": 13020.00, "date": "2026-10-09"}},
    "personal_card": {"label": "Personal purchase on a company card",
                      "params": {"merchant": "SEPHORA #2210", "amount": 96.40, "cardholder": "J. Ortiz",
                                 "date": "2026-09-27"}},
    "duplicate_bill": {"label": "Same purchase in Ramp and as a bill",
                       "params": {"vendor": "Notion", "amount": 96.00, "date": "2026-09-14"}},
    "paypal_bundle": {"label": "One PayPal transfer funding several payments",
                      "params": {"date": "2026-09-29", "payments": [{"name": "Damlicht Crew B.V.", "eur": 900.00,
                                                                     "item": "Crew fee Amsterdam 4 Oct"},
                                                                    {"name": "Splice.com, Inc.", "usd": 24.99,
                                                                     "item": "Splice Sounds subscription"}]}},
    "vendor_bank_change": {"label": "Vendor changes bank account before payment",
                          "params": {"vendor": "Lumen Crew LLC", "amount": 12000.00, "date": "2026-09-28"}},
    "split_purchases": {"label": "Multiple small purchases under approval threshold",
                       "params": {"merchant": "Office Depot", "amounts": [245.00, 235.00, 240.00], "date": "2026-09-20",
                                 "count": 3, "approval_limit": 2500.00, "source": "Ramp"}},
    "ghost_vendor": {"label": "Payment to non-existent vendor",
                    "params": {"vendor": "Advanced Solutions Inc", "amount": 8500.00, "date": "2026-09-22"}},
    "refund_as_revenue": {"label": "Refund incorrectly booked as revenue",
                         "params": {"merchant": "Bay Rig Rentals", "amount": 1200.00, "date": "2026-09-25"}},
}


def _parse_amount(text: str) -> float | None:
    """Extract dollar amount with k/m suffix support, avoiding date confusion."""
    # Try $50k, $12m format
    m = re.search(r'\$\s?([\d,]+(?:\.\d+)?)\s*([km])\b', text.lower())
    if m:
        base = float(m.group(1).replace(",", ""))
        return base * (1000 if m.group(2) == 'k' else 1000000)
    
    # Regular $X format - avoid confusing $96 with 9/6 date
    amounts = re.findall(r'\$\s?([\d,]+(?:\.\d{1,2})?)', text)
    for amt_str in amounts:
        amt = float(amt_str.replace(",", ""))
        # Skip likely dates (numbers under 32)
        if amt < 32 and re.search(rf'\${amt_str}.*\d+/\d+', text):
            continue
        if amt >= 1:
            return amt
    
    # Try "900 euros" format
    m = re.search(r'\b([\d,]+(?:\.\d+)?)\s*(euros?|eur)\b', text.lower())
    if m:
        return float(m.group(1).replace(",", ""))
    
    # Try "2500 dollars" format (no $ sign)
    m = re.search(r'\b([\d,]+(?:\.\d{1,2})?)\s*dollars?\b', text.lower())
    if m:
        amt = float(m.group(1).replace(",", ""))
        if amt >= 1:
            return amt
    
    return None


def _parse_date(text: str) -> str | None:
    """Extract date from date-like tokens only."""
    # Match M/D format
    m = re.search(r'\b(9|10)/(\d{1,2})\b', text.lower())
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        if 1 <= day <= 31:
            return f"2026-{month:02d}-{day:02d}"
    
    # Match 'Sept 15' format
    m = re.search(r'\b(sept|september|oct|october)\s+(\d{1,2})\b', text.lower())
    if m:
        month = {"sept": 9, "september": 9, "oct": 10, "october": 10}[m.group(1)]
        day = int(m.group(2))
        if 1 <= day <= 31:
            return f"2026-{month:02d}-{day:02d}"
    
    # Match 'on the 29th' or 'the 15th' format (default to September)
    m = re.search(r'\b(?:on )?the (\d{1,2})(?:st|nd|rd|th)\b', text.lower())
    if m:
        day = int(m.group(1))
        if 1 <= day <= 31:
            return f"2026-09-{day:02d}"
    
    return None


def _match_cardholder(text: str) -> str | None:
    """Match cardholder name case-insensitively."""
    t_lower = text.lower()
    for person in bible.PEOPLE.values():
        first = person["name"].split()[0].lower()
        full_name = person["name"].lower()
        # Match various patterns
        patterns = [
            f"{first}'s card",
            f"{first} spent",
            f"{first} bought",
            f"cardholder {first}",
            f"cardholder {full_name}",
            f"cardholder: {first}",
            f"cardholder: {full_name}"
        ]
        if any(p in t_lower for p in patterns):
            return person["name"]
    return None


def _parse_split_purchases(text: str) -> dict:
    """Parse split purchases, separating limit from charges."""
    params = {}
    t_lower = text.lower()
    
    # Parse count
    for word in ["two", "three", "four", "five", "six", "2", "3", "4", "5", "6"]:
        if f" {word} " in f" {t_lower} ":
            params["count"] = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}[word] if word.isalpha() else int(word)
            break
    
    # Extract ALL amounts
    all_amounts = []
    for m in re.finditer(r'\$\s?([\d,]+(?:\.\d{1,2})?)\s*([km])?', text.lower()):
        amt = float(m.group(1).replace(",", ""))
        if m.group(2):
            amt *= 1000 if m.group(2) == 'k' else 1000000
        all_amounts.append(amt)
    
    # Separate limit from charges
    limit = None
    if "limit" in t_lower or "threshold" in t_lower:
        # Last or largest amount is likely the limit if "under" is mentioned
        if "under" in t_lower and all_amounts:
            limit = max(all_amounts)
            all_amounts = [a for a in all_amounts if a < limit]
            params["approval_limit"] = limit
    
    if all_amounts:
        if len(all_amounts) == 1:
            params["amount_each"] = all_amounts[0]
        else:
            params["amounts"] = all_amounts
            params["count"] = len(all_amounts)
    
    # Extract merchant
    for v in bible.VENDORS:
        if v["qbo_name"].lower() in t_lower:
            params["merchant"] = v["qbo_name"]
            break
    
    # Extract source
    if "ramp" in t_lower:
        params["source"] = "Ramp"
    
    return params


def parse(text: str) -> tuple[str, dict]:
    """Parse free text. NEVER INVENT FACTS - return needs_info if unclear."""
    if not text or not text.strip():
        return "needs_info", {"error": "empty_text", "_parser": "none"}
    
    t_lower = text.lower()
    params = {}
    params["_parser"] = "deterministic"  # Default, may be overridden by LLM
    
    # Try LLM extraction first if available
    if llm.available():
        try:
            # Build vendor list for validation
            vendor_names = [v["qbo_name"] for v in bible.VENDORS]
            employee_names = [p["name"] for p in bible.PEOPLE.values()]
            
            schema = {
                "template": "one of: vendor_bank_change, split_purchases, ghost_vendor, refund_as_revenue, personal_card, duplicate_bill, invoice_over_accrual, paypal_bundle, needs_info",
                "vendor": f"exact vendor name from this list: {', '.join(vendor_names[:10])}..., or stated name if not in list, or null",
                "merchant": "merchant name as stated, or null",
                "amount": "number in dollars (convert k→1000, m→1000000), or null if not stated",
                "amounts": "array of charge amounts if multiple stated (exclude limit), or null",
                "count": "number of charges if stated, or null",
                "limit": "approval limit if mentioned, or null",
                "cardholder": f"full name from: {', '.join(employee_names)}, or null",
                "date": "YYYY-MM-DD in Sept/Oct 2026, or null if not stated",
                "currency": "USD or EUR if stated, or null"
            }
            
            llm_result = llm.complete_json(
                f"Extract accounting scenario details. Schema: {json.dumps(schema)}. "
                f"ONLY extract explicitly stated facts. Use null for unstated fields. "
                f"For dates: ONLY extract if an actual date is stated (e.g., '9/14', 'Sept 15'). "
                f"'for September' or 'in September' without a specific date -> null. "
                f"Validate vendor/employee names against provided lists.",
                f"Judge text: {text}",
                fast=True,
                timeout=3.0
            )
            
            if llm_result and llm_result.get("template"):
                # LLM extraction succeeded
                params["_parser"] = "llm_success"
                
                # Normalize amounts: LLM may return integer dollars, convert to float to avoid to_cents treating as cents
                if llm_result.get("amount") and isinstance(llm_result["amount"], int):
                    llm_result["amount"] = float(llm_result["amount"])
                if llm_result.get("amounts") and isinstance(llm_result["amounts"], list):
                    llm_result["amounts"] = [float(a) if isinstance(a, int) else a for a in llm_result["amounts"]]
                
                # Validate and fuzzy-match vendor
                if llm_result.get("vendor"):
                    matched = _match_vendor(llm_result["vendor"])
                    llm_result["vendor"] = matched["qbo_name"] if matched else llm_result["vendor"]
                
                # Map vendor → merchant for refund scenarios (LLM fills 'vendor' but template needs 'merchant')
                if llm_result.get("template") == "refund_as_revenue" and llm_result.get("vendor") and not llm_result.get("merchant"):
                    llm_result["merchant"] = llm_result["vendor"]
                
                # Merge LLM results, excluding template
                params.update({k: v for k, v in llm_result.items() if v is not None and k != "template"})
                
                template = llm_result["template"]
                if template in TEMPLATES or template == "needs_info":
                    return template, params
        except Exception as e:
            # LLM failed - fall back to deterministic
            params["_parser"] = "llm_failed"
            params["_llm_error"] = str(e)[:100]
    
    # Deterministic parsing fallback
    if params.get("_parser") == "deterministic":
        # Check if LLM was available but returned nothing useful
        if llm.available():
            params["_parser"] = "llm_failed"  # Was available but didn't work
        else:
            params["_parser"] = "deterministic_only"  # No LLM available
    
    # Extract amount
    amount = _parse_amount(text)
    if amount:
        params["amount"] = amount
    
    # Extract date
    date = _parse_date(text)
    if date:
        params["date"] = date
    
    # Extract vendor/merchant (prefer fuzzy match against master)
    quoted = re.search(r'["\']([^"\']{2,50})["\']', text)
    if quoted:
        v = _match_vendor(quoted.group(1))
        params["vendor"] = v["qbo_name"] if v else quoted.group(1)
        params["merchant"] = params["vendor"]
    else:
        # Try vendor master first
        for v in bible.VENDORS:
            if v["qbo_name"].lower() in t_lower:
                params["vendor"] = v["qbo_name"]
                params["merchant"] = v["qbo_name"]
                break
        
        # Try common merchant patterns (Nordstrom, Sephora, Steam, ACME Corp, etc.)
        if "vendor" not in params and "merchant" not in params:
            # Pattern: "at X" or "from X"
            m = re.search(r'\b(?:at|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
            if m:
                name = m.group(1)
                matched = _match_vendor(name)
                if matched:
                    params["vendor"] = matched["qbo_name"]
                    params["merchant"] = matched["qbo_name"]
                else:
                    params["merchant"] = name
            # Pattern: capitalized word before amount/card/purchase (e.g. "Nordstrom $250", "Steam purchase $45")
            elif not m:
                m = re.search(r'\b([A-Z][a-z]{3,}(?:\s+[A-Z][a-z]+)?)\s+(?:\$|purchase|charge)', text)
                if m:
                    name = m.group(1)
                    matched = _match_vendor(name)
                    if matched:
                        params["vendor"] = matched["qbo_name"]
                        params["merchant"] = matched["qbo_name"]
                    else:
                        params["merchant"] = name
            # Pattern: capitalized company name at start (e.g. "ACME Corp, PO box")
            if "merchant" not in params and "vendor" not in params:
                m = re.search(r'^([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\s*,', text)
                if m:
                    name = m.group(1)
                    matched = _match_vendor(name)
                    if matched:
                        params["vendor"] = matched["qbo_name"]
                        params["merchant"] = matched["qbo_name"]
                    else:
                        params["merchant"] = name
                        params["vendor"] = name
        
        # Final fallback: Try n-grams of the text against vendor master (catches "Lumen Crew", "Notion", etc.)
        if "vendor" not in params and "merchant" not in params:
            words = text.split()
            # Try 3-word, 2-word, and 1-word n-grams
            for n in [3, 2, 1]:
                if n > len(words):
                    continue
                for i in range(len(words) - n + 1):
                    ngram = " ".join(words[i:i+n])
                    matched = _match_vendor(ngram)
                    if matched:
                        params["vendor"] = matched["qbo_name"]
                        params["merchant"] = matched["qbo_name"]
                        break
                if "vendor" in params:
                    break
    
    # Extract cardholder
    cardholder = _match_cardholder(text)
    if cardholder:
        params["cardholder"] = cardholder
    
    # Classify (be conservative - use needs_info if unclear)
    # Check for described bank line (e.g. "$742.18 SQ *MOONLIGHT GEAR 9/29" or "debit...from SQ *MOONLIGHT")
    has_bank_descriptor = bool(re.search(r'\$[\d,]+\.?\d{0,2}\s+[A-Z*]+\s+', text)) or \
                         ("debit" in t_lower and ("from" in t_lower or quoted or params.get("merchant")))
    
    # Vendor bank change - broader pattern matching
    if (any(w in t_lower for w in ["bank details", "bank account", "bank acct", "banking"]) or 
        (("bank" in t_lower or "acct" in t_lower) and any(w in t_lower for w in ["change", "changed", "switch", "switched", "new"]))):
        k = "vendor_bank_change"
        # Try to extract vendor from beginning of text if not already extracted
        if "vendor" not in params and "merchant" not in params:
            # Pattern: capitalized word(s) at start or after "vendor"
            m = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', text)
            if m:
                name = m.group(1)
                matched = _match_vendor(name)
                if matched:
                    params["vendor"] = matched["qbo_name"]
                else:
                    params["vendor"] = name
    elif "split" in t_lower or re.search(r'(two|three|four|five|six|\d)\s+.*(?:charges|purchases)', t_lower):
        k = "split_purchases"
        params.update(_parse_split_purchases(text))
    elif any(w in t_lower for w in ["no w-9", "w9", "po box", "upfront", "never heard", "doesn't exist", "don't exist"]):
        k = "ghost_vendor"
    elif ("refund" in t_lower or "credit" in t_lower) and ("revenue" in t_lower or "income" in t_lower or "booked as" in t_lower or "recorded as" in t_lower):
        k = "refund_as_revenue"
    elif "refund" in t_lower and amount and params.get("merchant"):
        # Simple refund mention with merchant and amount
        k = "refund_as_revenue"
    elif "twice" in t_lower or ("paid" in t_lower and "again" in t_lower) or ("two bills" in t_lower):
        k = "duplicate_bill"
    elif ("accrued" in t_lower or "invoiced" in t_lower) and ("more" in t_lower or "showed up" in t_lower):
        k = "invoice_over_accrual"
    elif "paypal" in t_lower and ("eur" in t_lower or "fx" in t_lower):
        k = "paypal_bundle"
    elif any(w in t_lower for w in ["nordstrom", "sephora", "steam"]) or (params.get("merchant") and cardholder):
        k = "personal_card"
    elif has_bank_descriptor or (amount and "description" in params):
        # Described bank line -> unknown_debit
        k = "unknown_debit"
        if not params.get("description"):
            # Extract the descriptor portion - try bank line format first
            m = re.search(r'\$[\d,]+\.?\d{0,2}\s+([A-Z*][A-Z0-9*\s]+)', text)
            if m:
                params["description"] = m.group(1).strip()
            # Try "from X" pattern for bank descriptors
            elif "from" in t_lower:
                m = re.search(r'\bfrom\s+([A-Z*][A-Z0-9*\s]+?)(?:\s+\d|$)', text)
                if m:
                    params["description"] = m.group(1).strip()
            # Try quoted merchant as description
            elif params.get("merchant"):
                params["description"] = params["merchant"]
    elif "wire" in t_lower and (" in" in t_lower or "incoming" in t_lower):
        k = "needs_info"  # Incoming wire
    elif "boat" in t_lower or "auditor" in t_lower:
        k = "needs_info"  # Off-topic
    else:
        k = "needs_info"
    
    # Verify we have key data for classified scenario - but be less strict
    if k == "vendor_bank_change" and not (params.get("vendor") or params.get("merchant")):
        k = "needs_info"
    elif k == "split_purchases" and not (params.get("amount") or params.get("amounts") or params.get("count")):
        k = "needs_info"
    elif k == "ghost_vendor" and not (params.get("vendor") or params.get("merchant")):
        k = "needs_info"
    elif k == "refund_as_revenue" and not params.get("amount"):
        k = "needs_info"
    elif k == "personal_card" and not params.get("merchant"):
        k = "needs_info"
    
    return k, params


def _id(*parts) -> str:
    """Generate unique ID including timestamp to avoid silent no-ops on repeated injects."""
    timestamp = str(int(now().replace("-", "").replace("T", "").replace(":", "").replace(".", "").replace("Z", "")[:14]))
    return hashlib.md5((timestamp + "|" + "|".join(map(str, parts))).encode()).hexdigest()[:10].upper()


def _match_vendor(name: str) -> dict | None:
    """Fuzzy match vendor name against vendor master with case-insensitive token/prefix matching."""
    if not name:
        return None
    name_lower = name.lower().strip()
    name_tokens = set(name_lower.split())
    
    # First pass: exact match
    for v in bible.VENDORS:
        if v["qbo_name"].lower() == name_lower:
            return v
    
    # Second pass: substring match
    for v in bible.VENDORS:
        vendor_lower = v["qbo_name"].lower()
        if name_lower in vendor_lower or vendor_lower in name_lower:
            return v
        if name_lower in v.get("legal", "").lower():
            return v
    
    # Third pass: token matching (e.g. "Advanced Solutions" matches "Advanced Solutions Inc")
    for v in bible.VENDORS:
        vendor_lower = v["qbo_name"].lower()
        vendor_tokens = set(vendor_lower.split())
        # Match if all non-trivial input tokens appear in vendor name
        significant_tokens = name_tokens - {"inc", "llc", "corp", "co", "ltd", "gmbh", "b.v."}
        if significant_tokens and significant_tokens.issubset(vendor_tokens):
            return v
    
    # Fourth pass: prefix matching with distinctive token requirement
    # Require longer match or distinctive token to avoid false positives like "Crew" → "Damlicht Crew B.V."
    common_words = {"crew", "inc", "llc", "corp", "co", "ltd", "gmbh", "b.v.", "company", "group", "solutions", "services"}
    for v in bible.VENDORS:
        vendor_lower = v["qbo_name"].lower()
        vendor_tokens = set(vendor_lower.split())
        for tok in name_tokens:
            if len(tok) >= 5 and tok not in common_words:  # Distinctive token
                if any(vt.startswith(tok) or tok in vt for vt in vendor_tokens):
                    return v
    
    return None


def inject(session, text: str | None = None, template: str | None = None, params: dict | None = None) -> dict:
    """Inject judge scenario. NEVER INVENTS FACTS - creates needs_info if unclear."""
    db, eng = session.db, session.engine
    created = []
    tag = uuid.uuid4().hex[:6]
    from_free_text = bool(text and not template)
    
    try:
        if text and not template:
            template, params = parse(text)
        
        # Handle needs_info - create visible work item explaining what's missing
        if template == "needs_info":
            with db.tx():
                append_audit(db, SYNC, "inject", "scenario:needs_info", True,
                            f"Judge scenario needs clarification: {text}")
            
            anchor = f"inject:needs_info:{tag}"
            understood = []
            missing = []
            
            if params.get("amount"):
                understood.append(f"${params['amount']:.2f}")
            else:
                missing.append("amount")
            
            if params.get("vendor"):
                understood.append(f"vendor: {params['vendor']}")
            elif params.get("error") != "empty_text":
                missing.append("vendor/merchant name")
            
            if params.get("date"):
                understood.append(f"date: {params['date']}")
            
            understood_text = ", ".join(understood) if understood else "very little"
            missing_text = ", ".join(missing) if missing else "details"
            
            it = create_item(db, SYNC, "judge_scenario", anchor,
                            f"Judge scenario needs clarification: \"{text[:80] if text else 'empty'}...\"",
                            "2026-09", [])
            
            question = f"I understood: {understood_text}. Please clarify the {missing_text} for: \"{text[:150]}\""
            rationale = f"Could not confidently parse all required fields from judge prompt. {params.get('error', '')}"
            
            patch = {"question": question, "rationale": rationale, "injected": text or template}
            it = transition(db, it["item_id"], "ask", JARVIS, patch, reason=rationale)
            created.append(it)
            
            return {"template": "needs_info", "params": params, "parser": params.get("_parser", "deterministic"),
                    "items": [{"item_id": it["item_id"], "state": it["state"], "kind": it["kind"],
                              "title": it["title"], "rationale": rationale, "parser": params.get("_parser", "deterministic")}]}
        
        if template not in TEMPLATES:
            with db.tx():
                append_audit(db, SYNC, "inject", "scenario:unknown", False,
                            f"Unknown template: {template}")
            events.publish("inject_error", error="unknown_template", template=template, text=text)
            # Return error with http_status hint for API layer
            return {"error": "unknown_template", "template": template, "text": text, "items": [], "http_status": 400}
        
        # CRITICAL: For free text, NEVER merge template defaults - only use parsed values
        # For explicit template calls, merge defaults as expected
        if from_free_text:
            # Validate required fields from parsed params
            required_fields = {
                "vendor_bank_change": ["vendor", "amount", "date"],
                "split_purchases": ["amounts"],
                "ghost_vendor": ["vendor", "amount"],
                "refund_as_revenue": ["merchant", "amount"],
                "personal_card": ["merchant", "amount", "date"],
                "duplicate_bill": ["vendor", "amount", "date"],
                "invoice_over_accrual": ["vendor", "amount"],
                "paypal_bundle": ["payments"],
                "unknown_debit": ["amount", "description", "date"]
            }
            
            missing = []
            for field in required_fields.get(template, []):
                if field not in params or not params[field]:
                    missing.append(field)
            
            if missing:
                # Return needs_info instead of inventing data
                anchor = f"inject:needs_info:{tag}"
                it = create_item(db, SYNC, "judge_scenario", anchor,
                                f"Judge scenario needs clarification: missing {', '.join(missing)}",
                                "2026-09", [])
                question = f"I classified this as {TEMPLATES[template]['label']} but couldn't extract {', '.join(missing)}. Original text: \"{text[:150]}\""
                rationale = f"Required fields missing from free text: {', '.join(missing)}"
                patch = {"question": question, "rationale": rationale, "injected": text}
                it = transition(db, it["item_id"], "ask", JARVIS, patch, reason=rationale)
                created.append(it)
                return {"template": "needs_info", "params": params, "parser": params.get("_parser", "deterministic"),
                        "items": [{"item_id": it["item_id"], "state": it["state"], "kind": it["kind"],
                                  "title": it["title"], "rationale": rationale, "parser": params.get("_parser", "deterministic")}]}
            
            # Fill in reasonable defaults for optional fields ONLY when absolutely necessary
            # For unknown_debit, date is not strictly required - the bank line might not have one
        else:
            # Explicit template call - merge defaults
            params = {**TEMPLATES[template]["params"], **(params or {})}
        
        with db.tx():
            append_audit(db, SYNC, "inject", f"scenario:{template}", True,
                        f"judge scenario: {text or template} -> {params}")
        events.publish("inject", template=template, params=params, text=text)
        
    except Exception as e:
        with db.tx():
            append_audit(db, SYNC, "inject", "error", False, f"Parse error: {e}")
        events.publish("inject_error", error=str(e), text=text)
        return {"error": str(e), "text": text, "items": []}

    if template == "unknown_debit":
        cents = -abs(_dollars_to_cents(params["amount"]))
        desc = params["description"]
        d = params["date"]
        us = f"{d[5:7]}/{d[8:10]}/{d[:4]}"
        bid = ids.bank_id("x4471", us, f"{cents / 100:.2f}", desc, 0)
        with db.tx():
            _upsert(db, "bank", bid, "bank_txn", d, cents, "USD", "", desc,
                    {"bank_id": bid, "details": "DEBIT", "type": "DEBIT_CARD", "balance_cents": 0, "injected": True},
                    {"injected": text or template}, "injector", 0)
        for it in eng.discover(d[:7]):
            created.append(eng.process_item(it, "bank_line"))
    elif template == "personal_card":
        cents = abs(_dollars_to_cents(params["amount"]))
        rid = f"inj-{tag}"
        with db.tx():
            _upsert(db, "ramp", rid, "card_txn", params["date"], cents, "USD", params["merchant"].split(" #")[0].title(),
                    params["merchant"], {"ramp_id": rid, "settle": params["date"], "merchant": params["merchant"].split(" #")[0].title(),
                                         "descriptor": params["merchant"], "cardholder": params["cardholder"], "last4": "8812",
                                         "mcc": "5977" if "sephora" in params["merchant"].lower() else "5651",
                                         "department": "Live", "category": "Travel", "memo": "", "receipt": "No",
                                         "ramp_vendor": params["merchant"].split(" #")[0].title(),
                                         "erp_vendor": params["merchant"].split(" #")[0].title()},
                    {"injected": text or template}, "injector", 0)
            eid = f"JE-INJ-{tag}"
            db.conn.execute("INSERT INTO ledger_entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (eid, params["date"], params["date"][:7], f"Ramp card {params['merchant']} ({params['cardholder']})",
                             params["merchant"], "Expense", "", "ramp_sync", J({"ramp_id": rid}), None, "ramp_sync", now()))
            db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (eid, 0, "6430", cents, "", None))
            db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (eid, 1, "2050", -cents, "", None))
        for it, kind, payload in eng.discover_reviews(params["date"][:7]):
            created.append(eng.process_item(it, kind, payload))
    elif template == "duplicate_bill":
        cents = abs(_dollars_to_cents(params["amount"]))
        v = next((x for x in bible.VENDORS if x["qbo_name"] == params["vendor"]), None)
        vid = v["id"] if v else db.one("SELECT vendor_id FROM vendors WHERE qbo_name=?", (params["vendor"],))["vendor_id"]
        rid = f"inj-{tag}"
        bill_id = f"BILL-INJ-{tag}"
        with db.tx():
            _upsert(db, "ramp", rid, "card_txn", params["date"], cents, "USD", params["vendor"], params["vendor"].upper(),
                    {"ramp_id": rid, "settle": params["date"], "merchant": params["vendor"], "descriptor": params["vendor"].upper(),
                     "cardholder": "Lee Okafor", "last4": "5521", "mcc": "5734", "department": "Cloud", "category": "Software",
                     "memo": "subscription", "receipt": "Yes", "ramp_vendor": params["vendor"], "erp_vendor": params["vendor"]},
                    {"injected": text or template}, "injector", 0)
            eid = f"JE-INJ-{tag}"
            db.conn.execute("INSERT INTO ledger_entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (eid, params["date"], params["date"][:7], f"Ramp card {params['vendor']}", params["vendor"],
                             "Expense", "", "ramp_sync", J({"ramp_id": rid}), None, "ramp_sync", now()))
            db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (eid, 0, "6410", cents, "", None))
            db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (eid, 1, "2050", -cents, "", None))
            bje = f"JE-INJB-{tag}"
            db.conn.execute("INSERT INTO ledger_entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (bje, params["date"], params["date"][:7], f"{params['vendor']} subscription", params["vendor"],
                             "Bill", f"INJ-{tag}", "ap_clerk", J({"bill_id": bill_id}), None, "ap_clerk", now()))
            db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (bje, 0, "6410", cents, "", vid))
            db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (bje, 1, "2010", -cents, "", vid))
            db.conn.execute("INSERT INTO bills VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (bill_id, vid, params["vendor"], params["date"], params["date"], cents, f"INJ-{tag}",
                             f"{params['vendor']} subscription", "6410", "Open", params["date"][:7], bje))
        for it, kind, payload in eng.discover_reviews(params["date"][:7]):
            created.append(eng.process_item(it, kind, payload))
    elif template == "invoice_over_accrual":
        v = _match_vendor(params.get("vendor", ""))
        if not v:
            # Vendor not found - create needs_info
            anchor = f"inject:needs_info:{tag}"
            it = create_item(db, SYNC, "judge_scenario", anchor,
                            f"Judge scenario needs clarification: vendor '{params.get('vendor')}' not found",
                            "2026-09", [])
            question = f"Which vendor invoiced more than accrued? I couldn't find '{params.get('vendor')}' in the vendor master."
            rationale = f"Vendor '{params.get('vendor')}' not found in vendor master for invoice-over-accrual scenario."
            patch = {"question": question, "rationale": rationale, "injected": text or template}
            it = transition(db, it["item_id"], "ask", JARVIS, patch, reason=rationale)
            created.append(it)
            created = [c for c in created if c]
            return {"template": template, "params": params, "parser": params.get("_parser", "deterministic"),
                    "items": [{"item_id": c["item_id"], "state": c["state"], "kind": c["kind"], "title": c["title"],
                              "rationale": c.get("rationale", ""), "parser": params.get("_parser", "deterministic")} for c in created]}
        
        cents = abs(_dollars_to_cents(params["amount"]))
        bill_id = f"BILL-INJ-{tag}"
        bje = f"JE-INJB-{tag}"
        bill_exists = False
        
        with db.tx():
            existing_bill = db.one("SELECT 1 FROM bills WHERE vendor_id=? AND service_period='2026-09' AND date > '2026-09-30'", (v["id"],))
            bill_exists = bool(existing_bill)
            
            if not bill_exists:
                # Create the bill
                db.conn.execute("INSERT INTO ledger_entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                                (bje, "2026-10-09", "2026-10", f"{v['qbo_name']} services 2026-09", v["qbo_name"], "Bill",
                                 f"INJ-{tag}", "ap_clerk", J({"bill_id": bill_id}), None, "ap_clerk", now()))
                db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (bje, 0, v["default_acct"], cents, "", v["id"]))
                db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (bje, 1, "2010", -cents, "", v["id"]))
                db.conn.execute("INSERT INTO bills VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                                (bill_id, v["id"], v["qbo_name"], "2026-10-09", "2026-11-08", cents, f"INJ-{tag}",
                                 f"{v['qbo_name']} services 2026-09", v["default_acct"], "Open", "2026-09", bje))
        
        # ALWAYS create our own specific work item for the over-accrual scenario
        # Do NOT grab random items from eng.run_october() (might be unrelated like interest receivable)
        anchor = f"inject:accrual:{tag}:{v['id']}"
        it = create_item(db, SYNC, "invoice_over_accrual", anchor,
                        f"Review: {v['qbo_name']} invoiced ${params['amount']:.2f} vs accrued amount",
                        "2026-09", [],
                        evidence=[{"type": "bill", "id": bill_id if not bill_exists else "existing",
                                  "source": "bills", "desc": f"Invoice for ${params['amount']:.2f}"}])
        question = f"Review accrual variance for {v['qbo_name']}: invoice shows ${params['amount']:.2f}. Verify against accrued amount and adjust if needed."
        rationale = f"{v['qbo_name']} invoice amount ${params['amount']:.2f} needs reconciliation with accrual."
        patch = {"vendor": v["qbo_name"], "vendor_id": v["id"], "invoice_amount": cents,
                "question": question, "rationale": rationale, "injected": text or template}
        it = transition(db, it["item_id"], "ask", JARVIS, patch, reason=rationale)
        created.append(it)
    
    elif template == "vendor_bank_change":
        # Create work item for vendor bank detail change - MUST verify via callback before payment
        v = _match_vendor(params.get("vendor", ""))
        
        if v:
            cents = _dollars_to_cents(params["amount"])
            d = params["date"]
            anchor = f"inject:bank_change:{tag}:{v['id']}"
            
            # Check if email domain actually differs from vendor master
            email_domain_mentioned = re.search(r'from\s+([a-z0-9.-]+\.[a-z]{2,})', text.lower()) if text else None
            if email_domain_mentioned:
                mentioned_domain = email_domain_mentioned.group(1)
                domain_mismatch = mentioned_domain != v.get("domain", "")
                domain_note = f"Email from {mentioned_domain} (vendor master shows {v.get('domain', 'N/A')})" if domain_mismatch else f"New bank details received by email"
            else:
                domain_note = "New bank details received by email"
            
            it = create_item(db, SYNC, "vendor_bank_change", anchor,
                            f"ALERT: {v['qbo_name']} bank details changed before ${params['amount']:.2f} payment",
                            d[:7], [],
                            evidence=[{"type": "alert", "id": f"email-{tag}", "source": "email",
                                      "desc": domain_note}])
            
            # Persist question and rationale in fields (not just audit reason)
            question = f"BLOCK ${params['amount']:.2f} payment to {v['qbo_name']} pending verification. " + \
                      f"{domain_note}. Verify via callback to phone on file: {v.get('phone', 'not listed')}. DO NOT PROCESS until verified."
            
            rationale = f"Vendor {v['qbo_name']} bank account change reported before ${params['amount']:.2f} payment. " + \
                       f"Payment BLOCKED pending phone verification per fraud prevention policy."
            
            patch = {
                "question": question,
                "rationale": rationale,
                "vendor_id": v["id"],
                "amount_cents": cents,
                "date": d,
                "requires": "callback_verification",
                "phone_on_file": v.get("phone", "vendor master"),
                "email_domain": v.get("domain", ""),
                "injected": text or template
            }
            it = transition(db, it["item_id"], "ask", JARVIS, patch, reason=rationale[:300])
            created.append(it)
        else:
            # Vendor not found - create needs_info
            anchor = f"inject:needs_info:{tag}"
            it = create_item(db, SYNC, "judge_scenario", anchor,
                            f"Judge scenario needs clarification: vendor '{params.get('vendor')}' not found",
                            "2026-09", [])
            question = f"Which vendor's bank account changed? I couldn't find '{params.get('vendor')}' in the vendor master."
            rationale = f"Vendor '{params.get('vendor')}' not found in vendor master for bank-change scenario."
            patch = {"question": question, "rationale": rationale, "injected": text or template}
            it = transition(db, it["item_id"], "ask", JARVIS, patch, reason=rationale)
            created.append(it)
    
    elif template == "split_purchases":
        # Create N charges, then flag them as split to evade approval limits
        amounts = params.get("amounts", [])
        if not amounts:
            count = params.get("count", 3)
            total = params.get("amount", 750.0)
            amt_each = total / count
            amounts = [amt_each] * count
        else:
            count = len(amounts)
        
        # For free text, do NOT use defaults - these must be parsed or asked
        if from_free_text:
            merchant = params.get("merchant") or params.get("vendor")
            if not merchant:
                merchant = "Unknown Merchant"  # Will be visible in work item
            d = params.get("date", "2026-09-29")  # Sep end default
            source = params.get("source", "Unknown")
            approval_limit = params.get("approval_limit", 0)  # No limit assumed
        else:
            # Template call - use defaults
            merchant = params.get("merchant") or params.get("vendor", "Office Depot")
            d = params.get("date", "2026-09-20")
            source = params.get("source", "Ramp")
            approval_limit = params.get("approval_limit", 2500.0)
        
        record_ids = []
        # Create ALL N charges first
        with db.tx():
            for i, amt in enumerate(amounts):
                cents = _dollars_to_cents(amt)
                if source == "Ramp":
                    rid = f"inj-split-{tag}-{i}"
                    _upsert(db, "ramp", rid, "card_txn", d, cents, "USD", merchant,
                           f"{merchant} #{i+1}", 
                           {"ramp_id": rid, "settle": d, "merchant": merchant,
                            "descriptor": f"{merchant} #{i+1}", 
                            "cardholder": params.get("cardholder", "J. Ortiz"),
                            "last4": "8812", "mcc": "5943", "department": "Live", 
                            "category": "Supplies", "memo": f"Split {i+1}/{count}", 
                            "receipt": "Yes", "threshold_split": True,
                            "ramp_vendor": merchant,
                            "erp_vendor": merchant},
                           {"injected": text or template, "threshold_split": True}, "injector", 0)
                    # Get the record_id
                    rec = db.one("SELECT record_id FROM records WHERE src_id=?", (rid,))
                    if rec:
                        record_ids.append(rec["record_id"])
                    
                    # Create ledger entry for the charge
                    eid = f"JE-SPLIT-{tag}-{i}"
                    db.conn.execute("INSERT INTO ledger_entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                                   (eid, d, d[:7], f"{merchant} {i+1}/{count}", merchant,
                                    "Expense", "", "ramp_sync", J({"ramp_id": rid}), None, "ramp_sync", now()))
                    db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (eid, 0, "6900", cents, "", None))
                    db.conn.execute("INSERT INTO ledger_lines VALUES(?,?,?,?,?,?)", (eid, 1, "2050", -cents, "", None))
        
        # Now create the work item flagging this as threshold avoidance
        anchor = f"inject:split:{tag}"
        total_cents = sum(_dollars_to_cents(a) for a in amounts)
        it = create_item(db, SYNC, "threshold_split", anchor, 
                        f"ESCALATE: {count} purchases to {merchant} on {d}, each under ${approval_limit:.2f} limit (total ${total_cents/100:.2f})",
                        d[:7], record_ids)
        
        # Transition to NEEDS_INFO with evidence of threshold splitting
        patch = {
            "count": count,
            "amounts": amounts,
            "total_cents": total_cents,
            "approval_limit_cents": int(approval_limit * 100),
            "merchant": merchant,
            "source": source,
            "date": d,
            "flagged_for_review": True,
            "escalate_to": "Controller",
            "rationale": f"All {count} charges are under the ${approval_limit:.2f} approval limit",
            "injected": text or template
        }
        it = transition(db, it["item_id"], "ask", JARVIS, patch, 
                       reason=f"{count} charges to same vendor on same day, each under ${approval_limit:.2f} approval threshold - likely split to avoid review. Escalating to Controller")
        created.append(it)
    
    elif template == "ghost_vendor":
        # Block payment to vendor with no W-9/SOW or whose details match employee
        vendor_name = params.get("vendor", "Advanced Solutions Inc")
        cents = _dollars_to_cents(params["amount"])
        d = params.get("date", "2026-09-22")
        
        # Check if vendor is in vendor master
        v = _match_vendor(vendor_name)
        in_master = v is not None
        
        # Build list of red flags from the text
        red_flags = []
        t_lower = text.lower() if text else ""
        
        if not in_master:
            red_flags.append("Not in vendor master")
        if "no w-9" in t_lower or "w9" in t_lower or "w-9" in t_lower:
            red_flags.append("No W-9 on file")
        if "no sow" in t_lower or "no contract" in t_lower:
            red_flags.append("No SOW or contract on file")
        if "po box" in t_lower:
            red_flags.append("Address is PO box")
        if "upfront" in t_lower:
            red_flags.append("Requests payment upfront")
        if "never heard" in t_lower:
            red_flags.append("Unknown vendor")
        if "address matches" in t_lower or "employee" in t_lower:
            red_flags.append("Address may match employee")
        
        # If no specific flags, add generic ones
        if not red_flags:
            red_flags.append("Vendor verification required")
        
        anchor = f"inject:ghost:{tag}:{vendor_name.replace(' ', '_')}"
        it = create_item(db, SYNC, "ghost_vendor", anchor,
                        f"BLOCK: Payment to '{vendor_name}' ${params['amount']:.2f} - vendor verification required",
                        d[:7], [],
                        evidence=[{"type": "alert", "id": f"ghost-{tag}", "source": "vendor_check",
                                  "desc": "; ".join(red_flags)}])
        
        # Persist question and rationale in fields
        question = f"BLOCK ${params['amount']:.2f} payment to '{vendor_name}'. Red flags: {'; '.join(red_flags)}. " + \
                  "Verify vendor legitimacy, obtain W-9 and contract before processing."
        
        rationale = f"Payment to '{vendor_name}' flagged for verification. {'; '.join(red_flags)}. " + \
                   "Payment BLOCKED pending Controller approval per vendor onboarding policy."
        
        patch = {
            "question": question,
            "rationale": rationale,
            "vendor_name": vendor_name,
            "amount_cents": cents,
            "date": d,
            "in_master": in_master,
            "red_flags": red_flags,
            "requires": "vendor_verification",
            "status": "BLOCKED",
            "escalate_to": "Controller",
            "injected": text or template
        }
        it = transition(db, it["item_id"], "ask", JARVIS, patch, reason=rationale[:300])
        created.append(it)
    
    elif template == "refund_as_revenue":
        # Customer refund incorrectly booked as revenue - flag for review, NOT direct post
        merchant = params.get("merchant", "Bay Rig Rentals")
        cents = _dollars_to_cents(params["amount"])
        # For free text, use parsed date or default to Sep end; for template use template default
        d = params.get("date", "2026-09-27" if not from_free_text else "2026-09-27")
        
        # Create the incorrect revenue entry first (simulating the misclassification)
        # BUT: do NOT directly debit 1010 without a bank record
        wrong_eid = f"JE-WRONGREV-{tag}"
        with db.tx():
            # Only create the wrong ledger entry if there's a corresponding bank record
            # For now, create a memo-only item that DESCRIBES the issue
            pass
        
        # Create work item to flag this issue for review
        anchor = f"inject:refund:{tag}:{merchant.replace(' ', '_')}"
        
        # Find the original expense account for this vendor
        original_acct = "5020"  # Bay Rig Rentals is gear rental
        v = next((x for x in bible.VENDORS if merchant in x["qbo_name"] or x["qbo_name"] in merchant), None)
        if v:
            original_acct = v.get("default_acct", "5020")
        
        it = create_item(db, SYNC, "refund_reclass", anchor,
                        f"Review needed: ${params['amount']:.2f} from {merchant} may be refund booked as revenue",
                        d[:7], [],
                        evidence=[{"type": "alert", "id": f"refund-{tag}", "source": "scenario",
                                  "desc": f"${params['amount']:.2f} from {merchant} described as refund but may be in 4950 Other Income"}])
        
        # Route through NEEDS_INFO for review (not PROPOSED)
        # Only mention date in question if it was actually provided (not invented)
        date_clause = f" on {d}" if params.get("date") else ""
        question = f"Review: Is the ${params['amount']:.2f} credit from {merchant}{date_clause} a customer refund incorrectly booked to 4950 Other Income? If so, it should be reclassified to contra-expense account {original_acct} ({bible.acct_name(original_acct)})."
        rationale = f"Potential misclassification: ${params['amount']:.2f} from {merchant} may be a refund booked as revenue instead of contra-expense."
        
        patch = {
            "merchant": merchant,
            "amount_cents": cents,
            "date": d,
            "question": question,
            "rationale": rationale,
            "booked_to": "4950",
            "should_be_contra": original_acct,
            "requires_review": True,
            "injected": text or template
        }
        
        # Route through ask (NEEDS_INFO) so it goes through proper review workflow
        it = transition(db, it["item_id"], "ask", JARVIS, patch,
                       reason=f"Potential refund from {merchant} misclassified as revenue - flagging for review")
        created.append(it)
    
    elif template == "paypal_bundle":
        d = params["date"]
        rate = session.ctx.fx(d) or 1.17
        total = 0
        pays = []
        with db.tx():
            for p in params["payments"]:
                pid = _id(tag, p["name"], p.get("item"))[:17]
                if "eur" in p:
                    eur = _dollars_to_cents(p["eur"])
                    usd = round(eur * rate * 1.041)
                    _upsert(db, "paypal", pid, "paypal_general_payment", d, -eur, "EUR", p["name"],
                            f"General Payment {p['name']} {p.get('item', '')}",
                            {"txn_id": pid, "type": "General Payment", "time": "10:00:00", "status": "Completed",
                             "fee_cents": 0, "net_cents": -eur, "from_email": "ap@afterglowlabs.com",
                             "to_email": f"billing@{p['name'].split()[0].lower()}.example", "item": p.get("item", ""), "ref": "",
                             "impact": "Debit"}, {"injected": True}, "injector", 0)
                    cid = _id(tag, "conv", pid)[:17]
                    _upsert(db, "paypal", cid, "paypal_general_currency_conversion", d, -usd, "USD", "",
                            "General Currency Conversion", {"txn_id": cid, "type": "General Currency Conversion",
                                                            "ref": pid, "time": "10:00:00"}, {"injected": True}, "injector", 0)
                else:
                    usd = _dollars_to_cents(p["usd"])
                    _upsert(db, "paypal", pid, "paypal_preapproved_payment_bill_user_payment", d, -usd, "USD", p["name"],
                            f"PreApproved Payment {p['name']} {p.get('item', '')}",
                            {"txn_id": pid, "type": "PreApproved Payment Bill User Payment", "time": "10:05:00",
                             "status": "Completed", "fee_cents": 0, "net_cents": -usd, "from_email": "ap@afterglowlabs.com",
                             "to_email": "billing@splice.com" if "splice" in p["name"].lower() else "", "item": p.get("item", ""),
                             "ref": "", "impact": "Debit"}, {"injected": True}, "injector", 0)
                total += usd
                pays.append(pid)
            fid = _id(tag, "fund")[:17]
            _upsert(db, "paypal", fid, "paypal_bank_deposit_to_pp_account", d, total, "USD", "",
                    "Bank Deposit to PP Account", {"txn_id": fid, "type": "Bank Deposit to PP Account", "ref": pays[0],
                                                   "time": "10:10:00"}, {"injected": True}, "injector", 0)
            desc = f"PAYPAL INST XFER {fid[:10]} WEB ID: PAYPALSI77"
            us = f"{d[5:7]}/{d[8:10]}/{d[:4]}"
            bid = ids.bank_id("x4471", us, f"{-total / 100:.2f}", desc, 0)
            _upsert(db, "bank", bid, "bank_txn", d, -total, "USD", "", desc,
                    {"bank_id": bid, "details": "DEBIT", "type": "ACH_DEBIT", "balance_cents": 0, "injected": True},
                    {"injected": True}, "injector", 0)
        for it in eng.discover(d[:7]):
            created.append(eng.process_item(it, "bank_line"))
    created = [c for c in created if c]
    return {"template": template, "params": params, "parser": params.get("_parser", "deterministic"),
            "items": [{"item_id": c["item_id"], "state": c["state"], "kind": c["kind"], "title": c["title"],
                       "rationale": c.get("rationale", ""), "parser": params.get("_parser", "deterministic")} for c in created]}
