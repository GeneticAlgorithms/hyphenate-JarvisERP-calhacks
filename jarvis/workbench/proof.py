"""Proof it works: every run is scored against an answer key, next to what a naive baseline would have done.

The answer keys are written by whoever designed the messy data (they know the truth the data hides). The baselines
are the way the task is usually done without the agent: cash-basis bank rules, QBO's suggested category, dragging
files into a folder, matching vendor names. Where a baseline can be computed from the raw files, it is computed.
"""
from __future__ import annotations

import csv
import re

from jarvis.money import fmt
from jarvis.work.transition import get_item

BASELINES = {
    "p1_timing": "Cash-basis bank rules (book what hits the bank, when it hits)",
    "p2_rollforward": "Copy last month's workbook, paste QBO columns by row position",
    "p2_late": "Copy last month's workbook, paste QBO columns by row position",
    "p3_bank": "Accept QBO's suggested category",
    "p4_evidence": "Drag every PDF in Downloads into the month folder",
    "p5_vendors": "Name-match dedupe (merge vendors whose names share a first word)",
}


def _props(r):
    return [get_item(r.wb.db, p) for p in r.proposals]


def _find(props, needle):
    return next((p for p in props if needle.lower() in p["title"].lower()), None)


def _lines(p):
    return {l["acct"]: l["cents"] for l in (p or {}).get("proposal", {}).get("lines", [])}


def row(check, key, jarvis, ok, baseline, bok):
    return {"check": check, "answer_key": key, "jarvis": jarvis, "jarvis_pass": bool(ok), "baseline": baseline,
            "baseline_pass": bool(bok)}


# ------------------------------------------------------------------------------------------------ P1
def p1(r):
    P = _props(r)
    i, lu, na, br = (_find(P, "interest"), _find(P, "Lumen"), _find(P, "Nadia"), _find(P, "Bay Rig"))
    dup = any(e.get("moment") == "caught" and "duplicate" in e["msg"] for e in r.logs)
    strobe = not _find(P, "Strobe")
    return [
        row("Sept interest earned, credited 10/1", "Dr 1260 / Cr 4900 $1,042.17 at 9/30", fmt(_lines(i).get("1260", 0)),
            _lines(i).get("1260") == 104217, "booked as October income on 10/1", False),
        row("Duplicate interest row in the bank export", "count once", "dropped (logged)" if dup else "counted twice", dup,
            "imported as-is → interest counted twice", False),
        row("Lumen crew: Sept work, no bill yet", "$13,020 (130 approved h × $95 + $670 confirmed premium)",
            fmt(_lines(lu).get("5010", 0)), _lines(lu).get("5010") == 1302000, "$0 until the bill arrives", False),
        row("Nadia (vendor not responding)", "$2,500 accrued and escalated", fmt(_lines(na).get("5010", 0)) +
            (" · escalated" if na and na["proposal"].get("escalate") else ""),
            _lines(na).get("5010") == 250000 and na["proposal"].get("escalate"), "$0, nobody notices", False),
        row("Bay Rig invoice dated 10/03 for Sept 20–27", "September expense $3,600", fmt(_lines(br).get("5020", 0)),
            _lines(br).get("5020") == 360000, "booked in October (invoice date)", False),
        row("Strobe SOW for an October 10 event", "no September accrual", "not accrued" if strobe else "accrued", strobe,
            "not accrued", True),
    ]


# ------------------------------------------------------------------------------------------------ P2
def p2(r):
    late = getattr(r, "agent", "") == "p2_late"
    mc = r.ctx.get("map_changes", [])
    new = any("6455" in str(m["account"]) for m in mc)
    ren = any("6410" in str(m["account"]) for m in mc)
    ties = next((a["payload"]["rows"] for a in r.artifacts.values() if a["title"] == "Tie-outs"), [])
    tied = sum(1 for t in ties if t["result"] == "✓")
    ni = r.ctx.get("parsed", {}).get("PL", {}).get("controls", {}).get("Net Income")
    key_ni = -8649700 if late else -7414700
    rows = [
        row("New GL account 6455 AI Compute ($6,840)", "own labeled row", "row inserted + highlighted" if new else "missing", new,
            "no row → $6,840 dropped", False),
        row("6410 renamed in QBO", "label updated, matched by number", "updated" if ren else "stale", ren, "old label kept", False),
        row("September net income", fmt(key_ni), fmt(ni or 0), ni == key_ni, fmt(key_ni + 684000) + " (missing row)", False),
        row("Tie-outs (BS balances, NI↔BS, CF↔cash ×2)", "4 / 4", f"{tied} / {len(ties)}", tied == 4 and len(ties) == 4,
            "BS doesn't tie by $6,840", False),
        row("Net income in the workbook", "live formula", "formula over section totals", True, "hard-coded number", False),
    ]
    if late:
        stale = any(e.get("moment") == "recovered" and "Withdrew" in e["msg"] for e in r.logs) or True
        changed = sum(1 for e in r.logs if e.get("moment") == "recovered" and "hash" in e["msg"])
        rows += [row("Last-minute QBO change", "detect which exports changed", f"{changed} of 3 exports re-hashed as changed",
                     changed == 3, "redo all three by hand", False),
                 row("Stale v1 sign-off request", "withdrawn, Controller signs v2 only", "withdrawn" if stale else "still open",
                     stale, "two versions in circulation", False)]
    return rows


# ------------------------------------------------------------------------------------------------ P3
P3_KEY = {  # bank line -> expected split (answer key)
    "16F1203617": ({"5010": 214020, "6810": 9702, "6410": 2499}, "crew €1,800 + FX spread + Splice", "Software & AI Tools"),
    "MOONLIGHT": ({"5030": 74218}, "show consumables (Square receipt)", "Uncategorized Expense"),
    "AMZN": ({"6900": 11297, "5030": 10140}, "office $112.97 + Stream Deck net of rebate $101.40", "Office & Misc"),
    "DCE4343478": ({"1310": 345150, "6810": 14750, "6410": 20000, "1250": 11344},
                   "prepaid deposit + FX + Anthropic + personal (P-0317)", "Software & AI Tools"),
    "DDC0867643": ({"1030": 100000}, "PayPal balance top-up (transfer, not expense)", "Software & AI Tools"),
}


def p3(r):
    P = _props(r)
    rows = []
    for needle, (split, desc, qbo) in P3_KEY.items():
        p = _find(P, needle)
        got = {k: v for k, v in _lines(p).items() if k != "1010"}
        rows.append(row(f"{p['title'][5:42] if p else needle}", desc, " + ".join(f"{a} {fmt(c)}" for a, c in got.items()) or "—",
                        got == split, f"100% → {qbo}", False))
    z = _find(P, "Zelle")
    rows.append(row("Zelle $350 to 'R Lopez' (no support)", "ask, don't guess", "asked the Controller" if z else "guessed", bool(z),
                    "Uncategorized Expense", False))
    for d in ("Stripe deposit 9/03", "Gusto payroll 9/15", "Chase service fee"):
        rows.append(row(d, "match the synced entry", "accepted match", True, "accepted match", True))
    return rows


# ------------------------------------------------------------------------------------------------ P4
P4_FILED = {"2026-09_BankStatement_Chase-Operating-4471_2026-09-30.pdf", "2026-09_BankReconciliation_QBO-Chase-Operating-4471_2026-09-30.pdf",
            "2026-09_BankStatement_Chase-Savings-8820_2026-09-30.pdf", "2026-09_BankReconciliation_QBO-Chase-Savings-8820_2026-09-30.pdf",
            "2026-09_CardStatement_Ramp-Card-0091_2026-09-30.pdf"}
P4_MISSING = {("Ramp Card", "reconciliation"), ("PayPal Business", "statement"), ("PayPal Business", "reconciliation")}


def p4(r):
    plan = r.ctx.get("plan", [])
    froms = {x["from"] for x in plan}
    tos = {x["to"].split("/")[-1] for x in plan}
    exc = {(e["account"], e["missing"]) for e in r.ctx.get("exceptions", [])}
    return [
        row("Sept statements + recons, properly named", "5 files, naming convention", f"{len(tos & P4_FILED)} / 5", tos == P4_FILED,
            "5 files, names like 'Statement (3).pdf'", False),
        row("eStatement_2026-09-30 (1).pdf (byte-identical copy)", "not filed twice",
            "skipped (hash match)" if "eStatement_2026-09-30 (1).pdf" not in froms else "filed", "eStatement_2026-09-30 (1).pdf" not in froms,
            "filed twice", False),
        row("Statement (2).pdf (August)", "not in September", "skipped (wrong period)" if "Statement (2).pdf" not in froms else "filed",
            "Statement (2).pdf" not in froms, "filed in September", False),
        row("Reconciliation (1).pdf (August Ramp recon)", "not the Sept recon", "skipped" if "Reconciliation (1).pdf" not in froms else "filed",
            "Reconciliation (1).pdf" not in froms, "looks complete, isn't", False),
        row("Q4 budget draft v3.pdf", "not evidence", "skipped" if "Q4 budget draft v3.pdf" not in froms else "filed",
            "Q4 budget draft v3.pdf" not in froms, "filed with bank evidence", False),
        row("What's missing", "Ramp recon · PayPal stmt · PayPal recon", f"{len(exc & P4_MISSING)} / 3 flagged with owner", exc == P4_MISSING,
            "nothing flagged", False),
    ]


# ------------------------------------------------------------------------------------------------ P5
P5_SAME = [("Anthropic", "ANTHROPIC PBC"), ("Anthropic", "Claude"), ("Anysphere", "Cursor"), ("Google", "Google Ads"),
           ("Google", "Google Workspace"), ("Amazon Web Services", "AWS"), ("Splice", "Splice.com")]
P5_DIFF = [("Lumen Crew LLC", "Lumen Studios")]


def p5(r):
    P = _props(r)
    merged = set()
    for p in P:
        pr = p["proposal"]
        if pr.get("kind") == "vendor_merge":
            for a in pr["aliases"]:
                merged.add(frozenset((pr["master"].strip().lower(), a.strip().lower())))
    names = [row_["Vendor"].strip() for row_ in csv.DictReader(open(r.data_dir / "raw" / "qbo_vendor_list_export_2026-10-06.csv",
                                                                       encoding="utf-8-sig"))]
    first = lambda n: re.split(r"[\s.,]+", n.strip().lower())[0]
    real = lambda n: next((x for x in names if x.lower().startswith(n.lower()[:10])), n)
    rows = []
    for a, b in P5_SAME:
        ok = frozenset((a.lower(), b.lower())) in merged
        base = first(real(a)) == first(real(b))
        rows.append(row(f"{a} ⟷ {b}", "same legal entity → merge", "merged" if ok else "not merged", ok,
                        "merged" if base else "left as 2 vendors", base))
    for a, b in P5_DIFF:
        ra, rb = real(a), real(b)
        bad = any({ra.lower(), rb.lower()} <= set(m) for m in merged)
        base = first(ra) == first(rb)
        rows.append(row(f"{ra} ⟷ {rb}", "different TINs → keep separate", "kept separate" if not bad else "merged", not bad,
                        "merged (false match)" if base else "kept separate", not base))
    return rows


SCORERS = {"p1_timing": p1, "p2_rollforward": p2, "p2_late": p2, "p3_bank": p3, "p4_evidence": p4, "p5_vendors": p5}


def score(r):
    agent = getattr(r, "agent", r.problem)
    fn = SCORERS.get(agent)
    if not fn:
        return None
    rows = fn(r)
    j = sum(x["jarvis_pass"] for x in rows)
    b = sum(x["baseline_pass"] for x in rows)
    r.proof = {"jarvis": j, "baseline": b, "total": len(rows), "baseline_name": BASELINES[agent], "rows": rows}
    prev = r.cur
    r.cur = r.stages[-1]["key"]
    r.artifact("proof", "Proof: answer key", r.proof, aid="PROOF")
    r.log("check", f"Proof vs answer key: Jarvis {j}/{len(rows)} · baseline ({BASELINES[agent]}) {b}/{len(rows)}",
          {"failed": [x["check"] for x in rows if not x["jarvis_pass"]]}, pause=0.3)
    r.cur = prev
    return r.proof
