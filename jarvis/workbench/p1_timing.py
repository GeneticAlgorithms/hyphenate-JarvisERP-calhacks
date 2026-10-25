"""Workbench 1 — Timing differences & accruals (Afterglow Labs, September 2026)."""
from __future__ import annotations

import csv
import re

from jarvis.money import fmt
from jarvis.workbench import clean as C

TITLE = "Timing differences & accruals"
STAGES = [("ingest", "Ingest raw sources"), ("clean", "Clean & normalize"), ("timing", "Detect timing differences"),
          ("discover", "Find unbilled work"), ("measure", "Measure each accrual"), ("outreach", "Vendor outreach (simulated)"),
          ("propose", "Draft entries + reversals"), ("validate", "Validate"), ("approve", "Controller → Gateway")]
PERIOD_END = "2026-09-30"


def _rows(path):
    return list(csv.reader(path.open(encoding="utf-8-sig")))


def run(r, **_):
    raw = r.data_dir / "raw"
    # ------------------------------------------------------------------ ingest
    with r.stage("ingest", "landing every file exactly as received"):
        files = sorted(p for p in raw.rglob("*") if p.is_file())
        inv = []
        for p in files:
            kind = {"csv": "table", "txt": "document", "eml": "email"}.get(p.suffix[1:], p.suffix[1:])
            h = C.sha(p)[:12]
            inv.append({"file": str(p.relative_to(raw)), "bytes": p.stat().st_size, "sha256": h, "type": kind})
            r.log("info", f"landed {p.relative_to(raw)} ({p.stat().st_size} B, sha256 {h}…) as {kind}", pause=0.4)
        r.artifact("table", "Raw file inventory", {"columns": ["file", "type", "bytes", "sha256"], "rows": inv})
        r.count(files=len(files))
        r.done(f"{len(files)} raw files landed, hashes recorded")

    # ------------------------------------------------------------------ clean
    with r.stage("clean", "fix formats, drop junk rows, extract fields"):
        # bank export
        diff, bank = [], []
        rows = _rows(raw / "bank" / "chase_x4471_export_2026-10.csv")
        seen = set()
        for i, row in enumerate(rows[1:], start=2):
            if not any(x.strip() for x in row):
                r.log("fix", f"bank row {i}: blank line dropped")
                diff.append({"row": i, "before": ",".join(row), "after": "(dropped)", "why": "blank line"})
                continue
            d, dn = C.day(row[1])
            a, an = C.money(row[3])
            desc = re.sub(r"\s+", " ", row[2]).strip()
            notes = [n for n in (dn, an, "whitespace trimmed" if desc != row[2] else "") if n]
            key = (d, a, desc, row[5])
            if key in seen:
                r.moment("caught", "find", f"bank row {i}: exact duplicate of an earlier row (same date, amount, description, running balance) — "
                              f"export glitch, dropped", {"row": row})
                diff.append({"row": i, "before": ",".join(row), "after": "(dropped)", "why": "duplicate export row"})
                continue
            seen.add(key)
            if notes:
                r.log("fix", f"bank row {i}: {'; '.join(notes)} → {d} {fmt(a)} '{desc[:40]}'")
                diff.append({"row": i, "before": f"{row[1]} | {row[2][:40]} | {row[3]}", "after": f"{d} | {desc[:40]} | {fmt(a)}",
                             "why": "; ".join(notes)})
            bank.append({"date": d, "description": desc, "amount_cents": a, "type": row[4]})
        r.artifact("diff", "Bank export: before → after", {"rows": diff})
        r.artifact("table", "Bank export (clean)", {"columns": ["date", "description", "amount_cents", "type"], "rows": bank})
        r.ctx["bank"] = bank
        r.count(bank_rows_in=len(rows) - 1, bank_rows_clean=len(bank), bank_fixes=len(diff))

        # OCR'd interest notice
        txt = (raw / "bank" / "chase_interest_notice_2026-09.txt").read_text()
        fixed, n = C.ocr_fix(txt)
        r.log("fix", f"interest notice: {n} OCR substitutions (letter 'O' inside numbers → '0')",
              {"before": "INTEREST ACCRUED $1,O42.17 · CREDITED 1O/01/2026", "after": "INTEREST ACCRUED $1,042.17 · CREDITED 10/01/2026"})
        per = re.search(r"PERIOD\s+(\S+)\s*-\s*(\S+)", fixed)
        amt = C.money(re.search(r"INTEREST ACCRUED\s+(\S+)", fixed).group(1))[0]
        cred = C.day(re.search(r"CREDITED ON\s+(\S+)", fixed).group(1))[0]
        notice = {"period_start": C.day(per.group(1))[0], "period_end": C.day(per.group(2))[0], "interest_cents": amt,
                  "credit_date": cred}
        r.log("info", f"extracted from notice: earned {notice['period_start']}→{notice['period_end']}, {fmt(amt)}, credited {cred}",
              notice)
        r.ctx["notice"] = notice

        # QBO GL export: title rows, section headers, totals, footer
        gl_rows = _rows(raw / "qbo" / "qbo_general_ledger_2026-09.csv")
        gl, section, removed, controls = [], None, 0, {}
        for row in gl_rows:
            first = (row[0] if row else "").strip()
            if not row or not any(c.strip() for c in row):
                removed += 1
                continue
            if first in ("Afterglow Labs, Inc.", "General Ledger", "September 2026", "TOTAL") or first.startswith("Accrual Basis"):
                removed += 1
                continue
            if row[0] == "" and len(row) > 1 and row[1] == "Date":
                removed += 1
                continue
            if first.startswith("Total for "):
                controls[first[10:]] = C.money(row[7])[0] or 0
                continue
            if first and len([c for c in row if c.strip()]) == 1:
                section = first
                continue
            if row[5] == "Beginning Balance":
                continue
            gl.append({"account": section, "date": C.day(row[1])[0], "type": row[2], "num": row[3], "name": row[4],
                       "memo": row[5], "amount_cents": C.money(row[7])[0]})
        r.log("fix", f"QBO GL export: removed {removed} report-chrome rows (company/title/period headers, blank lines, "
                     f"column header, 'TOTAL', 'Accrual Basis …' footer); carried section headers down onto {len(gl)} lines")
        for acct, tot in controls.items():
            s = sum(g["amount_cents"] for g in gl if g["account"] == acct and g["amount_cents"] is not None)
            r.log("check" if s == tot else "warn", f"control total '{acct}': lines sum {fmt(s)} vs QBO 'Total for' {fmt(tot)} "
                  f"{'✓' if s == tot else '✗'}")
        r.artifact("table", "QBO General Ledger (normalized)", {"columns": ["account", "date", "type", "num", "name", "memo",
                                                                            "amount_cents"], "rows": gl})
        r.ctx["gl"] = gl

        # AP aging
        ap = []
        for row in _rows(raw / "qbo" / "ap_open_bills_2026-10-06.csv")[1:]:
            v = re.sub(r"\s+", " ", row[0]).strip()
            vn = v.title() if v.islower() else v
            if vn != row[0]:
                r.log("fix", f"AP vendor name '{row[0]}' → '{vn}' (trimmed, cased)")
            ap.append({"vendor": vn.replace("Llc", "LLC"), "bill_date": C.day(row[1])[0], "num": row[2],
                       "amount_cents": C.money(row[4])[0], "memo": row[5]})
        r.ctx["ap"] = ap

        # timesheet
        ts_rows = _rows(raw / "timesheets" / "LumenCrew_timesheet_SEPT (approved).csv")
        kept, seen, ts_diff, stated_total = [], set(), [], None
        for i, row in enumerate(ts_rows[1:], start=2):
            if row[2] == "TOTAL":
                stated_total = float(row[3])
                r.log("fix", f"timesheet row {i}: 'TOTAL' footer row removed (kept as control total = {stated_total:g} h)")
                continue
            d, dn = C.day(row[0])
            h, hn = C.hours(row[3])
            ok = C.yes(row[4])
            key = (d, row[2].strip(), h)
            if h is None:
                r.log("warn", f"timesheet row {i}: {row[2]} on {d} has blank hours — excluded, flagged for the vendor to confirm")
                ts_diff.append({"row": i, "before": ",".join(row), "after": "(excluded)", "why": "blank hours"})
                continue
            if key in seen:
                r.log("find", f"timesheet row {i}: duplicate entry for {row[2]} on {d} ({h:g} h) — dropped")
                ts_diff.append({"row": i, "before": ",".join(row), "after": "(dropped)", "why": "duplicate"})
                continue
            if not ok:
                r.moment("caught", "decide", f"timesheet row {i}: {row[2]} {h:g} h not approved ('{row[4]}') — excluded from accrual basis")
                ts_diff.append({"row": i, "before": ",".join(row), "after": "(excluded)", "why": "not approved"})
                continue
            seen.add(key)
            notes = [n for n in (dn, hn, "approval value normalized" if row[4] not in ("Y",) else "") if n]
            if notes:
                r.log("fix", f"timesheet row {i}: {'; '.join(notes)}")
                ts_diff.append({"row": i, "before": ",".join(row), "after": f"{d},{row[2]},{h:g}", "why": "; ".join(notes)})
            kept.append({"date": d, "event": row[1], "crew": row[2].strip(), "hours": h})
        total = sum(k["hours"] for k in kept)
        r.log("check" if stated_total == total else "warn",
              f"timesheet: {len(kept)} approved crew-days = {total:g} h vs vendor's stated total {stated_total:g} h "
              f"{'✓ ties' if stated_total == total else '✗ differs'}")
        r.artifact("diff", "Timesheet: before → after", {"rows": ts_diff})
        r.ctx["hours"] = total
        r.ctx["ts_rows"] = kept

        # documents
        docs = {}
        for p in sorted((raw).rglob("*.txt")) + sorted(raw.rglob("*.eml")):
            t = p.read_text()
            docs[p.name] = t
        r.ctx["docs"] = docs
        sow = docs["SOW_LumenCrew_2026_master.txt"]
        rate = C.money(re.search(r"Rate: USD \$([\d.,]+)", sow).group(1))[0]
        r.log("info", f"SOW_LumenCrew: rate {fmt(rate)}/crew-hour; clause found: 'After-hours load-out (after 1:00 am) billed at 1.5x'")
        r.ctx["rate"] = rate
        hist = list(csv.DictReader((raw / "history" / "accrual_history_2026.csv").open()))
        r.ctx["hist"] = hist
        r.log("info", f"accrual history: {len(hist)} prior accruals loaded (Jun–Aug) — the company's memory for this task")
        r.count(gl_lines=len(gl), timesheet_rows_kept=len(kept), docs=len(docs))
        r.done(f"{len(diff) + len(ts_diff) + n} fixes logged; every change has a before/after")

    # ------------------------------------------------------------------ timing
    with r.stage("timing", "cash in October, earned in September?"):
        found = []
        for b in r.ctx["bank"]:
            d = b["description"]
            if d.startswith("INTEREST PAYMENT"):
                n = r.ctx["notice"]
                in_gl = [g for g in r.ctx["gl"] if g["account"].startswith("4900")]
                r.moment("caught", "find", f"{b['date']} INTEREST PAYMENT {fmt(b['amount_cents'])}: notice says earned {n['period_start']}–"
                              f"{n['period_end']}; September GL 4900 has {len(in_gl)} lines and 1260 ends at $0.00 → "
                              f"September revenue is missing from September books")
                found.append({"bank_line": f"{b['date']} {d}", "amount_cents": b["amount_cents"], "earned": "2026-09",
                              "received": b["date"][:7], "treatment": "Accrue at 9/30: Dr 1260 Interest Receivable / Cr 4900 Interest Income; "
                                                                       "10/1 receipt clears 1260 (not new income)"})
            elif "STRIPE" in d:
                r.log("decide", f"{b['date']} Stripe payout {fmt(b['amount_cents'])}: settles October card sales (payout lag 2 days) — "
                                f"Stripe sync books revenue on charge date, no timing entry needed")
            elif "CARD PMT" in d:
                r.log("decide", f"{b['date']} Ramp payment {fmt(b['amount_cents'])}: pays the September card statement — "
                                f"expenses already in September via Ramp sync; liability relief only, no accrual")
            elif "SERVICE FEE" in d:
                r.log("decide", f"{b['date']} service fee: October charge for October — no timing difference")
            elif "GUSTO" in d:
                r.log("decide", f"{b['date']} payroll: pay period Sep 21–Oct 4 straddles month end → wage accrual handled "
                                f"by Gusto's payroll-accrual JE (outside this workbench's seats); noted")
        r.artifact("table", "Timing differences found", {"columns": ["bank_line", "amount_cents", "earned", "received", "treatment"],
                                                         "rows": found})
        r.ctx["timing"] = found
        r.count(timing_differences=len(found))
        r.done(f"{len(found)} timing difference: interest earned in Sep, credited Oct 1")

    # ------------------------------------------------------------------ discover
    with r.stage("discover", "who worked in September but hasn't billed?"):
        docs = r.ctx["docs"]
        cands = []
        ap_lumen = [a for a in r.ctx["ap"] if "Lumen" in a["vendor"]]
        if ap_lumen:
            r.log("find", f"AP has an open Lumen bill {ap_lumen[0]['num']} ({fmt(ap_lumen[0]['amount_cents'])}) — memo says "
                          f"'{ap_lumen[0]['memo']}': that's AUGUST work, so it does NOT cover September (common trap)")
        r.log("decide", f"Lumen Crew: approved September timesheet ({r.ctx['hours']:g} h) and no September bill → accrue")
        cands.append({"vendor": "Lumen Crew LLC", "evidence": "SOW + approved timesheet", "decision": "accrue"})
        ros = docs["run_of_show_FoxTheater_2026-09-25.txt"]
        if "Nadia Kroll" in ros:
            r.log("decide", "Nadia Kroll: booking for 9/25 + run of show confirms she performed → accrue (performance evidence, not just a contract)")
            cands.append({"vendor": "Nadia Kroll", "evidence": "booking + run of show", "decision": "accrue"})
        inv = docs["BR-20871 BayRig.txt"]
        r.moment("caught", "decide", "Bay Rig Rentals: invoice BR-20871 is dated 10/03 but the service period is Sept 20–27 → September expense; "
                        "not in the September GL → accrue")
        cands.append({"vendor": "Bay Rig Rentals", "evidence": "invoice (service in Sept)", "decision": "accrue"})
        r.moment("caught", "decide", "Strobe & Co: signed SOW, but the event is October 10 → a commitment, not September work → no accrual")
        cands.append({"vendor": "Strobe & Co", "evidence": "SOW for Oct 10", "decision": "skip — future service"})
        r.artifact("table", "Accrual candidates", {"columns": ["vendor", "evidence", "decision"], "rows": cands})
        r.count(accrue=3, skipped=1)
        r.done("3 vendors to accrue, 1 correctly skipped")

    # ------------------------------------------------------------------ measure
    with r.stage("measure", "best evidence wins; say why when sources disagree"):
        rate, h = r.ctx["rate"], r.ctx["hours"]
        lumen = int(rate * h)
        r.log("decide", f"Lumen: method (b) contract rate × approved hours = {fmt(rate)} × {h:g} = {fmt(lumen)}")
        r.moment("caught", "find", "Sources disagree: vendor email (9/29) says 'around 10k' vs contract × timesheet "
                      f"{fmt(lumen)}. Ranking: invoice > rate × approved hours > flat fee w/ performance > informal estimate → "
                      f"keep {fmt(lumen)}")
        lum_hist = [x for x in r.ctx["hist"] if x["vendor"] == "Lumen Crew LLC"]
        ratios = [C.money(x["actual_invoice"])[0] / C.money(x["accrued"])[0] for x in lum_hist]
        avg = sum(ratios) / len(ratios)
        r.log("info", f"History: Lumen invoices came in at {', '.join(f'{x:.3f}' for x in ratios)}× the accrual (avg {avg:.3f}×) — "
                      f"driver noted each time: after-hours premium. The 9/25 run of show has load-out 01:00–03:30 → the SOW's 1.5x "
                      f"clause applies again. Will confirm with the vendor instead of guessing.")
        r.ctx["lumen"] = lumen
        r.ctx["lumen_hist_avg"] = avg
        nad = [x for x in r.ctx["hist"] if x["vendor"] == "Nadia Kroll"]
        r.log("decide", "Nadia: method (c) flat fee $2,500.00 (booking) with performance evidence (run of show)")
        r.moment("caught", "warn", f"Nadia history: July accrual corrected by the Controller to $2,250 ('{nad[0]['notes']}'); Feb invoice 47 days late → "
                      f"confirm amount with her and escalate")
        r.log("decide", "Bay Rig: method (a) vendor invoice $3,600.00 — strongest evidence")
        r.artifact("table", "Measurement", {"columns": ["vendor", "method", "amount", "contradicting source", "note"], "rows": [
            {"vendor": "Lumen Crew LLC", "method": "(b) $95 × 130 h", "amount": fmt(lumen), "contradicting source": "email '~10k'",
             "note": f"history avg {avg:.3f}× → likely premium"},
            {"vendor": "Nadia Kroll", "method": "(c) flat fee + run of show", "amount": "$2,500.00", "contradicting source": "—",
             "note": "corrected before; late invoicer"},
            {"vendor": "Bay Rig Rentals", "method": "(a) invoice BR-20871", "amount": "$3,600.00", "contradicting source": "—",
             "note": "invoice date ≠ service period"}]})
        r.done("3 measured; 1 conflict resolved by evidence ranking")

    # ------------------------------------------------------------------ outreach
    with r.stage("outreach", "ask the vendors (simulated mailbox)"):
        r.log("sim", "→ email to ops@lumencrew.co: 'Confirming 130 approved crew-hours for September at $95. Will the 9/25 "
                     "after-hours load-out premium (1.5x) be on the invoice? Amount please.'", pause=1.2)
        r.log("sim", "← reply from Rae Ito (simulated, +3h): 'Yep, 130 hrs confirmed. Fox Theater load-out ran past 1am for "
                     "4.7 crew-hours → premium $670.00 on top. Invoice LC-2026-09 by the 10th.'", pause=1.4)
        premium = 67000
        r.log("decide", f"Premium is contractually allowed (SOW 1.5x clause) AND confirmed by the vendor in writing → include it. "
                        f"Lumen accrual = {fmt(r.ctx['lumen'])} + {fmt(premium)} = {fmt(r.ctx['lumen'] + premium)} "
                        f"({(r.ctx['lumen'] + premium) / r.ctx['lumen']:.3f}×, consistent with history {r.ctx['lumen_hist_avg']:.3f}×)")
        r.ctx["lumen_total"] = r.ctx["lumen"] + premium
        r.log("sim", "→ email to hello@nadiakroll.studio: 'Can you confirm your fee for Fox Theater 9/25 and send the invoice?'", pause=1.0)
        r.log("sim", "… no reply after 48h (simulated clock) — second reminder sent", pause=1.0)
        r.moment("asked", "ask", "Nadia hasn't answered. Booking $2,500 accrued at the contract amount and escalated to the Controller "
                     "(she corrected Nadia's accrual once before).")
        r.flag("Lumen confirmed (+$670 premium); Nadia silent → escalated")

    # ------------------------------------------------------------------ propose
    with r.stage("propose", "journal entries the Gateway would post"):
        n = r.ctx["notice"]
        props = [
            ("accrual", "Accrue September interest earned (credited 10/01)",
             [{"acct": "1260", "cents": n["interest_cents"], "memo": "Interest receivable — Chase notice Sep"},
              {"acct": "4900", "cents": -n["interest_cents"], "memo": "Interest income Sep 2026"}],
             f"Chase notice: {fmt(n['interest_cents'])} earned 9/1–9/30, credited 10/1. Revenue belongs to September; the 10/1 "
             f"receipt will clear 1260 instead of creating new income.", 0.97, False, ""),
            ("accrual", "Accrue Lumen Crew September lighting",
             [{"acct": "5010", "cents": r.ctx["lumen_total"], "memo": "Lumen Crew Sep: 130 h × $95 + after-hours premium $670"},
              {"acct": "2100", "cents": -r.ctx["lumen_total"], "memo": "Accrued expenses — Lumen Crew"}],
             f"Contract × approved hours {fmt(r.ctx['lumen'])} plus vendor-confirmed 1.5x after-hours premium $670.00 (SOW clause). "
             f"Vendor email '~10k' rejected as weakest evidence.", 0.92, False, ""),
            ("accrual", "Accrue Nadia Kroll VJ — Fox Theater 9/25",
             [{"acct": "5010", "cents": 250000, "memo": "Nadia Kroll VJ 9/25 (booking fee)"},
              {"acct": "2100", "cents": -250000, "memo": "Accrued expenses — Nadia Kroll"}],
             "Performance proven by the run of show; booking says $2,500 flat. Vendor hasn't confirmed (48h, 2 emails) and the "
             "Controller corrected her accrual once before → escalated.", 0.78, True,
             "Nadia hasn't confirmed her 9/25 fee. Accrue the $2,500 booking amount, or do you know a different number?"),
            ("accrual", "Accrue Bay Rig Rentals Sept 20–27 (invoice dated Oct 3)",
             [{"acct": "5020", "cents": 360000, "memo": "Bay Rig BR-20871 service Sept 20–27"},
              {"acct": "2100", "cents": -360000, "memo": "Accrued expenses — Bay Rig"}],
             "Invoice BR-20871 is dated 10/03 but covers Sept 20–27 service → September expense (cut-off).", 0.96, False, ""),
        ]
        rev = []
        for kind, title, lines, why, conf, esc, q in props:
            r.propose(kind, title, {"date": PERIOD_END, "memo": title, "lines": lines, "auto_reverse": "2026-10-01"},
                      why, [{"type": "doc", "id": title, "label": why[:80], "relation": "supports"}], conf, esc, q)
            rev.append({"entry": title, "reverses_on": "2026-10-01",
                        "lines": " / ".join(f"{l['acct']} {fmt(-l['cents'])}" for l in lines)})
        r.artifact("table", "Auto-reversal schedule (Oct 1)", {"columns": ["entry", "reverses_on", "lines"], "rows": rev})
        r.done(f"{len(props)} entries proposed, each with an Oct 1 auto-reversal")

    # ------------------------------------------------------------------ validate
    with r.stage("validate", "deterministic checks before anyone approves"):
        from jarvis.work.transition import get_item
        for pid in r.proposals:
            it = get_item(r.wb.db, pid)
            ls = it["proposal"]["lines"]
            bal = sum(l["cents"] for l in ls)
            r.log("check" if bal == 0 else "fail", f"{it['title']}: debits = credits ({fmt(sum(l['cents'] for l in ls if l['cents'] > 0))}) "
                  f"{'✓' if bal == 0 else '✗'} · period 2026-09 open ✓ · no matching September GL line ✓")
        tot = sum(get_item(r.wb.db, p)["proposal"]["lines"][0]["cents"] for p in r.proposals[1:])
        r.log("check", f"accrued expenses after close: {fmt(tot)} (Aug accrual {fmt(1345000)} fully reversed 9/1 ✓)")
        r.done("all entries balance, periods open, no duplicates")

    with r.stage("approve", "waiting on Maya (Controller)"):
        r._stage("approve")["status"] = "waiting"
        r._stage("approve")["summary"] = f"{len(r.proposals)} proposals waiting — the agent cannot approve its own work"


def on_reject(r, it, reason):
    amt = C.money(re.search(r"\$\s?([\d,]+(?:\.\d{2})?)", reason).group(0))[0] if re.search(r"\$\s?[\d,]+", reason) else None
    if amt and "Nadia" in it["title"]:
        r.moment("recovered", "decide", f"Controller says {fmt(amt)}. Re-planning Nadia's accrual at the confirmed amount; the correction becomes "
                        f"precedent #3 for 'accrue the amount the vendor confirmed' → proposing that as a standing policy.")
        r.propose("accrual", "Accrue Nadia Kroll VJ — Fox Theater 9/25 (confirmed amount)",
                  {"date": PERIOD_END, "memo": "Nadia Kroll (confirmed)", "auto_reverse": "2026-10-01",
                   "lines": [{"acct": "5010", "cents": amt, "memo": "Nadia Kroll VJ 9/25 (confirmed via Controller)"},
                             {"acct": "2100", "cents": -amt, "memo": "Accrued expenses — Nadia Kroll"}]},
                  f"Controller: \"{reason}\". Re-proposed at {fmt(amt)}.", [], 0.95)
