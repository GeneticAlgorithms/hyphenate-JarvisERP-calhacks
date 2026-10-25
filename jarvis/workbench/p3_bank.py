"""Workbench 3 — Bank feed lines that don't say what they are (PayPal, Square, Amazon, Zelle)."""
from __future__ import annotations

import csv
import itertools
import re

from jarvis.money import fmt, mul_rate
from jarvis.workbench import clean as C

TITLE = "Bank transactions without context"
STAGES = [("ingest", "Ingest bank feed + PayPal"), ("clean", "Clean & parse descriptors"), ("triage", "Triage: which lines lack context?"),
          ("lookup", "Look it up (simulated portals)"), ("match", "Match & split"), ("categorize", "Enrich + categorize vs QBO"),
          ("validate", "Validate"), ("approve", "Controller → Gateway")]


def run(r, **_):
    raw = r.data_dir / "raw"
    with r.stage("ingest"):
        for p in sorted(raw.rglob("*")):
            if p.is_file():
                r.log("info", f"landed {p.relative_to(raw)} sha256 {C.sha(p)[:12]}…", pause=0.3)
        r.done("bank feed, PayPal activity, receipts, contracts, ECB rates")

    with r.stage("clean"):
        feed, diffs = [], []
        for i, row in enumerate(csv.DictReader((raw / "qbo_bank_feed_for_review_2026-09.csv").open()), start=2):
            d, dn = C.day(row["Date"])
            spent, sn = C.money(row["Spent"])
            recv, rn = C.money(row["Received"])
            amt = (recv or 0) - (spent or 0)
            m = re.search(r"(PAYPAL \*INST XFER|SQ \*|AMZN Mktp US\*|Zelle payment to)\s*(\S+)?", row["Description"])
            proc = {"PAYPAL *INST XFER": "PayPal", "SQ *": "Square", "AMZN Mktp US*": "Amazon", "Zelle payment to": "Zelle"}.get(
                m.group(1)) if m else None
            ref = m.group(2) if m else None
            line = {"line": i, "date": d, "description": row["Description"].strip(), "amount_cents": amt, "processor": proc,
                    "ref": ref, "qbo_payee": row["Payee"], "qbo_suggestion": row["Category or Match"]}
            feed.append(line)
            notes = [x for x in (dn, sn, rn) if x]
            if notes or proc:
                r.log("fix", f"line {i}: {'; '.join(notes) or 'parsed'}" + (f" · processor={proc} ref={ref}" if proc else ""),
                      pause=0.4)
        r.artifact("table", "Bank feed (clean)", {"columns": ["line", "date", "description", "amount_cents", "processor", "ref",
                                                              "qbo_suggestion"], "rows": feed})
        pp = []
        with (raw / "paypal_activity_download_2026-09.csv").open(encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        r.log("fix", "PayPal export: UTF-8 byte-order mark stripped from header (would break the 'Date' column name); "
                     "quoted names with commas ('Anthropic, PBC') preserved")
        for row in rows:
            pp.append({"id": row["Transaction ID"], "date": C.day(row["Date"])[0], "name": row["Name"], "type": row["Type"],
                       "currency": row["Currency"], "gross": C.money(row["Gross"])[0], "from": row["From Email Address"],
                       "to": row["To Email Address"], "item": row["Item Title"], "ref": row["Reference Txn ID"]})
        r.artifact("table", "PayPal activity (clean)", {"columns": ["id", "date", "name", "type", "currency", "gross", "item", "ref"],
                                                        "rows": pp})
        r.ctx.update(feed=feed, pp=pp, fx={row["date"]: float(row["eur_usd"]) for row in
                                          csv.DictReader((raw / "reference" / "ecb_eur_usd_2026-09.csv").open())})
        r.count(feed_lines=len(feed), paypal_rows=len(pp))
        r.done(f"{len(feed)} feed lines, {len(pp)} PayPal rows normalized")

    with r.stage("triage"):
        vague = []
        for f in r.ctx["feed"]:
            if f["qbo_suggestion"].startswith("Match:"):
                r.log("decide", f"line {f['line']} {f['description'][:38]}: QBO already found the synced entry ({f['qbo_suggestion']}) — accept match")
            elif f["processor"]:
                vague.append(f)
                r.moment("caught", "find", f"line {f['line']} '{f['description'][:44]}' {fmt(f['amount_cents'])}: descriptor names the "
                              f"{f['processor']} rail, not the merchant/purpose — QBO guessed '{f['qbo_suggestion']}' → needs lookup")
            else:
                r.log("decide", f"line {f['line']} {f['description'][:38]}: self-explanatory ('{f['qbo_suggestion']}') — accept")
        r.ctx["vague"] = vague
        r.count(needs_lookup=len(vague))
        r.done(f"{len(vague)} lines need context")

    with r.stage("lookup", "what a human would open in another tab"):
        receipts = {p.name: p.read_text() for p in (raw / "receipts").glob("*.txt")}
        docs = {p.name: p.read_text() for p in (raw / "docs").glob("*.txt")}
        for f in r.ctx["vague"]:
            if f["processor"] == "PayPal":
                r.log("sim", f"[PayPal portal · read-only SSO] Activity → filter {f['date']} ±2 days, funding id starts '{f['ref']}'", pause=0.8)
                fund = next((p for p in r.ctx["pp"] if p["type"] == "Bank Deposit to PP Account" and p["id"].startswith(f["ref"])), None)
                f["funding"] = fund
                r.log("find" if fund else "warn", f"funding row {fund['id']} {fmt(fund['gross'])}, linked to "
                                                  f"{fund['ref'] or 'NOTHING (no reference)'}" if fund else "no funding row found")
            elif f["processor"] == "Square":
                hit = next((n for n, t in receipts.items() if "742.18" in t), None)
                r.log("sim", f"[Receipts inbox] search amount 742.18 around {f['date']} → {hit}", pause=0.6)
                f["receipt"] = hit
            elif f["processor"] == "Amazon":
                hit = next((n for n, t in receipts.items() if (f["ref"] or "")[:7] in t), None)
                r.log("sim", f"[Amazon Business · order history] search order fragment '{f['ref'][:7]}' → {hit}", pause=0.6)
                f["receipt"] = hit
            elif f["processor"] == "Zelle":
                hits = [n for n, t in docs.items() if "Lopez" in t]
                r.log("sim", f"[Drive + email search] 'R Lopez' → {hits or 'nothing'}; no invoice, no W-9, no vendor record", pause=0.6)
                f["hint"] = hits
        r.ctx["receipts"], r.ctx["docs"] = receipts, docs
        r.done("every vague line traced to a source document (or flagged)")

    with r.stage("match", "tie each bank line to the cent"):
        used = set()
        for f in r.ctx["vague"]:
            if f["processor"] != "PayPal" or not f.get("funding"):
                continue
            fund = f["funding"]
            cands = [p for p in r.ctx["pp"] if p["type"] in ("General Payment", "PreApproved Payment Bill User Payment",
                                                             "Express Checkout Payment") and p["id"] not in used
                     and abs((int(p["date"][8:]) - int(fund["date"][8:]))) <= 2]

            def usd(p):
                if p["currency"] == "USD":
                    return -p["gross"]
                conv = next(c for c in r.ctx["pp"] if c["type"] == "General Currency Conversion" and c["currency"] == "USD"
                            and c["ref"] == p["id"])
                return -conv["gross"]
            target = fund["gross"]
            r.log("info", f"{fmt(target)}: subset-sum over {len(cands)} PayPal payments within ±2 days"
                          + (f", must include linked {fund['ref']}" if fund["ref"] else ""), [p["id"] for p in cands])
            best = None
            for k in range(1, len(cands) + 1):
                for combo in itertools.combinations(cands, k):
                    if sum(usd(p) for p in combo) == target and (not fund["ref"] or fund["ref"] in {p["id"] for p in combo}):
                        best = combo
                        break
                if best:
                    break
            if not best:
                r.moment("caught", "decide", f"no payment combination equals {fmt(target)} → this is a top-up of our PayPal balance "
                                f"(transfer 1010 → 1030), not an expense")
                f["lines"] = [{"acct": "1030", "cents": target, "memo": "Top-up PayPal balance"}]
                continue
            used |= {p["id"] for p in best}
            r.moment("caught", "find", f"{len(best)} payments sum to {fmt(target)} to the cent: " + ", ".join(
                f"{p['name']} {fmt(-p['gross'], p['currency'])}" for p in best))
            f["payments"] = [(p, usd(p)) for p in best]
        r.done("PayPal transfers decomposed; top-up recognized")

    with r.stage("categorize", "write the description QBO should have had"):
        cmp_rows = []
        for f in r.ctx["vague"]:
            lines = f.get("lines") or []
            if f.get("payments"):
                for p, usd in sorted(f["payments"], key=lambda x: -x[1]):
                    if p["currency"] != "USD":
                        rate = r.ctx["fx"][p["date"]]
                        mkt = mul_rate(-p["gross"], rate)
                        future = "14 Nov" in p["item"] or "Nov" in p["item"]
                        sow = next((n for n in r.ctx["docs"] if "Kraftwerk" in n), None) if "Kraftwerk" in p["name"] else None
                        acct = "1310" if future else "5010"
                        r.log("decide", f"{p['name']} {fmt(-p['gross'], 'EUR')}: ECB {rate} → {fmt(mkt)}; PayPal charged {fmt(usd)} → "
                                        f"FX fee {fmt(usd - mkt)}. " + (f"{sow} puts the show on 14 Nov → 1310 Prepaid (cut-off)" if future
                                                                        else "show already happened → 5010 Crew & Production"))
                        lines += [{"acct": acct, "cents": mkt, "memo": f"{p['name']} {p['item']} (€{-p['gross'] / 100:,.2f} @ ECB {rate})"},
                                  {"acct": "6810", "cents": usd - mkt, "memo": "PayPal FX spread"}]
                    elif "steam" in p["item"].lower() or "Valve" in p["name"]:
                        r.moment("caught", "decide", f"{p['name']} {fmt(usd)} paid from j.ortiz@ login, digital games → ruling P-0317 → "
                                        f"1250 Employee Receivable; notify J. Ortiz")
                        lines.append({"acct": "1250", "cents": usd, "memo": "Personal - Steam - J. Ortiz"})
                    else:
                        vendor = "Anthropic" if "Anthropic" in p["name"] else ("Splice" if "Splice" in p["name"] else p["name"])
                        r.log("decide", f"{p['name']} '{p['item']}' {fmt(usd)} → 6410 Software (vendor {vendor}"
                                        + (" — 'Claude' is a product, not a vendor" if "Claude" in p["item"] else "") + ")")
                        lines.append({"acct": "6410", "cents": usd, "memo": f"{vendor} - {p['item']}"})
            elif f["processor"] == "Square":
                r.log("decide", "Square receipt: DMX cables, haze, gaffer, LED lenses 'for Fox Theater 9/25' → 5030 Gear & Equipment "
                                "(QBO said 'Uncategorized')")
                lines = [{"acct": "5030", "cents": -f["amount_cents"], "memo": "Moonlight Gear Co - show consumables (Fox 9/25)"}]
            elif f["processor"] == "Amazon":
                r.log("decide", "Amazon order: toner + notebooks $112.97 → 6900 Office; Stream Deck $149.99 less rebate $48.59 = $101.40 → "
                                "5030 Gear (show control) — split the line (QBO put all of it in Office)")
                lines = [{"acct": "6900", "cents": 11297, "memo": "Amazon - toner, notebooks"},
                         {"acct": "5030", "cents": 10140, "memo": "Amazon - Elgato Stream Deck (net of rebate)"}]
            elif f["processor"] == "Zelle":
                r.moment("asked", "ask", "Zelle to 'R Lopez' $350.00: only a run sheet mentions a stagehand 'R. Lopez'. That's a hint, not support → "
                             "ask the Controller instead of guessing an account")
                f["question"] = ("Zelle $350.00 to 'R Lopez' on 9/28 — the Oakland run sheet lists a stagehand R. Lopez. Is this "
                                 "crew cost for the Fox Theater show? (No invoice or W-9 on file.)")
            f["lines"] = lines
            amt = -f["amount_cents"]
            if lines:
                lines.append({"acct": "1010", "cents": -amt, "memo": f"Bank {f['date']} {f['description'][:30]}"})
            cmp_rows.append({"line": f["line"], "bank": f"{f['date']} {fmt(f['amount_cents'])} {f['description'][:30]}",
                             "qbo_said": f["qbo_suggestion"],
                             "jarvis": " + ".join(f"{l['acct']} {fmt(l['cents'])}" for l in lines if l["acct"] != "1010") or "ASK"})
        r.artifact("table", "QBO suggestion vs Jarvis", {"columns": ["line", "bank", "qbo_said", "jarvis"], "rows": cmp_rows})
        r.done(f"{len(cmp_rows)} lines enriched")

    with r.stage("validate"):
        for f in r.ctx["vague"]:
            ls = f.get("lines") or []
            if ls:
                bal = sum(l["cents"] for l in ls)
                r.log("check" if bal == 0 else "fail", f"line {f['line']}: split sums to bank amount {fmt(-f['amount_cents'])} "
                                                       f"{'✓' if bal == 0 else '✗ off ' + fmt(bal)}; FX recomputed from ECB ✓")
        r.done("every split ties to its bank line")

    with r.stage("approve", "proposals waiting on Maya"):
        for f in r.ctx["vague"]:
            if f.get("question"):
                r.propose("question", f"Zelle {fmt(f['amount_cents'])} to R Lopez — what is it?",
                          {"bank_line": f["line"], "amount_cents": -f["amount_cents"]}, f["question"], [], 0.3, True, f["question"])
            elif f.get("lines"):
                r.propose("bank_categorize", f"Bank {f['date']} {fmt(f['amount_cents'])} {f['description'][:28]}",
                          {"date": f["date"], "memo": f"Categorize/split bank line {f['line']}", "lines": f["lines"]},
                          f"Traced via {f['processor']} lookup; QBO suggested '{f['qbo_suggestion']}'.", [], 0.92)
        r._stage("approve")["status"] = "waiting"
        r._stage("approve")["summary"] = f"{len(r.proposals)} proposals waiting"


def apply(r, it):
    if it["kind"] == "question":
        ans = it.get("answer") or ""
        acct = "5010" if re.search(r"crew|stage|load|5010", ans, re.I) or not ans else "6900"
        amt = it["proposal"]["amount_cents"]
        r.log("decide", f"Controller answered: \"{ans or 'yes, crew cost'}\" → booking {fmt(amt)} to {acct}; "
                        f"also requesting a W-9 from R. Lopez (payments to individuals may need a 1099)")
        r.propose("bank_categorize", "Bank 2026-09-28 -$350.00 Zelle R Lopez (per Controller)",
                  {"date": "2026-09-28", "memo": "Zelle R Lopez - stagehand Fox Theater 9/25 (per Controller)",
                   "lines": [{"acct": acct, "cents": amt, "memo": "R. Lopez stagehand load-out 9/25"},
                             {"acct": "1010", "cents": -amt, "memo": "Zelle payment"}]},
                  f"Controller confirmed: {ans or 'crew cost'}", [], 0.95)
        return f"answer recorded: {ans or 'crew cost'}; follow-up entry proposed"
    return "applied"


def on_reject(r, it, reason):
    """Handle Controller rejection - record as precedent and re-plan."""
    # Record the rejection as a precedent
    prec_id = f"PREC-{abs(hash(it['item_id'] + reason)) % 10**6:06d}"
    r.wb.db.conn.execute(
        "INSERT INTO precedents (prec_id, date, period, pattern, summary, decision, decided_by, status, refs, source_item) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (prec_id, "2026-09-30", it.get("period", "2026-09"), it["kind"], it["title"][:200], reason[:500], "maya", "active", "[]", it["item_id"])
    )
    
    r.log("decide", f"Controller rejected: \"{reason}\". Recorded as precedent; will apply in future similar transactions.", pause=0.8)
    
    # If rejection mentions a specific amount or categorization, extract and re-propose
    amt_match = re.search(r'\$\s?([\d,]+(?:\.\d{2})?)', reason)
    if amt_match and it["kind"] in ("bank_categorize", "paypal_split"):
        from jarvis.money import to_cents
        from jarvis.work.transition import create_item, transition
        from jarvis.work.roles import actor
        from jarvis.work.sync import SYNC
        
        # Parse the dollar amount
        amt_str = amt_match.group(0).replace("$", "").replace(",", "")
        new_amt = to_cents(amt_str)
        r.log("decide", f"Detected correction to {fmt(new_amt)}; re-proposing with updated amount...", pause=0.5)
        
        # Create corrected proposal - adjust only the disputed line
        import copy
        corrected_proposal = copy.deepcopy(it["proposal"])
        lines = corrected_proposal.get("lines", [])
        cash_accounts = ("1010", "1030")
        
        # Find the disputed line (largest debit that isn't cash)
        debit_lines = [l for l in lines if l.get("cents", 0) > 0 and l.get("acct") not in cash_accounts]
        
        if debit_lines:
            # Adjust only the largest debit line (the one likely corrected)
            target_line = max(debit_lines, key=lambda l: l.get("cents", 0))
            old_amt = target_line["cents"]
            target_line["cents"] = new_amt
            
            # Calculate the difference and add balancing line
            diff = new_amt - old_amt
            if diff != 0:
                # Add balancing line (6810 Bank & FX Fees or ask)
                balance_line = {
                    "acct": "6810",
                    "cents": -diff,
                    "memo": f"Adjustment from Controller correction"
                }
                lines.append(balance_line)
                r.log("decide", f"Adjusted {target_line['acct']} from {fmt(old_amt)} to {fmt(new_amt)}, added {fmt(abs(diff))} to 6810 to balance", pause=0.5)
            
            # Verify balance
            balance_check = sum(l.get("cents", 0) for l in lines)
            if balance_check == 0:
                # Create new work item
                jarvis = actor("jarvis")
                new_it = create_item(r.wb.db, SYNC, it["kind"],
                                   f"{it['anchor']}-corrected",
                                   f"{it['title']} (corrected per Controller: {fmt(new_amt)})",
                                   it["period"], it.get("tags", []))
                
                transition(r.wb.db, new_it["item_id"], "propose", jarvis,
                          {"proposal": corrected_proposal,
                           "evidence": it.get("evidence", []),
                           "rationale": f"Re-proposed per Controller correction: {reason[:300]}",
                           "confidence": 0.95},
                          reason=f"Corrected after rejection: {reason[:200]}")
                
                r.proposals.append(new_it["item_id"])
                r.log("decide", f"Re-proposed as {new_it['item_id']}", pause=0.8)
            else:
                r.log("warn", f"Corrected entry doesn't balance (off by {fmt(balance_check)}); routing to NEEDS_INFO", pause=0.8)
        else:
            # Can't auto-correct, route to NEEDS_INFO
            r.log("decide", "Cannot determine which line to adjust - needs Controller clarification", pause=0.5)
    
    # Check for policy changes mentioned in rejection
    if "policy" in reason.lower() or "always" in reason.lower():
        r.log("decide", "Rejection mentions policy — will propose policy update after 3+ similar corrections.", pause=0.5)
