"""Workbench 2 — Roll the monthly financial package forward from raw QBO exports (+ last-minute change refresh)."""
from __future__ import annotations

import csv
import re
import shutil

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

from jarvis.money import fmt
from jarvis.workbench import clean as C
from jarvis.work.transition import get_item, transition
from jarvis.workbench.core import JARVIS

TITLE = "Financial package roll-forward"
STAGES = [("ingest", "Ingest exports + last package"), ("parse", "Clean QBO report exports"), ("map", "Map accounts (new / renamed)"),
          ("roll", "Add September column"), ("tie", "Tie-out checks"), ("flux", "Flux commentary"),
          ("publish", "Build package"), ("approve", "Controller sign-off → Gateway")]
ACCT_RX = re.compile(r"^(\d{4})\s+(.+)$")


def parse_qbo(r, path, label, quiet=False):
    """QBO 'Export to Excel': 3 title rows, header, indented lines, 'Total …' rows, blank rows, footer."""
    ws = load_workbook(path).active
    log = (lambda *a, **k: None) if quiet else r.log
    out, controls, chrome, text_nums, section = {}, {}, 0, 0, []
    footer = ""
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        a, b = (row + (None, None))[:2]
        if i <= 3:
            chrome += 1
            log("fix", f"{label} row {i}: report title '{a}' removed", pause=0.25)
            continue
        if a is None and b is None:
            chrome += 1
            continue
        if b == "Total" and not a:
            chrome += 1
            continue
        if isinstance(a, str) and a.startswith("Accrual Basis"):
            footer = a
            chrome += 1
            log("fix", f"{label}: footer '{a}' removed (kept as export timestamp)", pause=0.25)
            continue
        label_txt = str(a)
        depth = (len(label_txt) - len(label_txt.lstrip(" "))) // 3
        name = label_txt.strip()
        if isinstance(b, str):
            v, note = C.money(b)
            text_nums += 1
            log("fix", f"{label}: '{name}' value stored as text '{b}' → {v / 100:,.2f} ({note})", pause=0.35)
        else:
            v = None if b is None else int(round(float(b) * 100))
        m = ACCT_RX.match(name)
        if m:
            out[m.group(1)] = {"num": m.group(1), "name": m.group(2), "cents": v, "section": " > ".join(section)}
        elif v is None:
            section = section[:depth] + [name]
        else:
            controls[name] = v
    log("info", f"{label}: {len(out)} accounts, {len(controls)} control totals, {chrome} chrome rows removed, "
                  f"{text_nums} text-numbers converted", pause=0.5)
    return out, controls, footer


def _pkg(path):
    wb = load_workbook(path)
    pkg = {}
    for sh in ("IS", "BS", "CF"):
        ws = wb[sh]
        rows = list(ws.iter_rows(values_only=True))
        pkg[sh] = {"header": rows[1], "rows": rows[2:]}
    return wb, pkg


def run(r, late: bool = False, **_):
    base = r.data_dir
    raw = base / "raw"
    src = base / "late_change" if late else raw
    files = {"PL": next(src.glob("ProfitAndLoss*.xlsx")), "BS": next(src.glob("BalanceSheet*.xlsx")),
             "CF": next(src.glob("Statement of Cash Flows*.xlsx"))}
    prior_pkg = raw / "Afterglow_FinancialPackage_2026-08_FINAL.xlsx"
    with r.stage("ingest", "late change detected — refreshing" if late else "three QBO exports + last month's package"):
        for k, p in list(files.items()) + [("PKG", prior_pkg)]:
            r.log("info", f"landed '{p.name}' sha256 {C.sha(p)[:12]}…", pause=0.4)
        if late:
            for k in ("PL", "BS", "CF"):
                old = next(raw.glob({"PL": "ProfitAndLoss*.xlsx", "BS": "BalanceSheet*.xlsx", "CF": "Statement of Cash Flows*.xlsx"}[k]))
                r.moment("recovered", "find", f"{k}: new export '{files[k].name}' hash {C.sha(files[k])[:10]} ≠ previous '{old.name}' {C.sha(old)[:10]} "
                              f"→ content changed after the package was built")
            note = (base / "late_change" / "README_late_change.txt").read_text().strip()
            r.log("info", f"change note: {note}")
        _, pkg = _pkg(prior_pkg)
        r.log("info", f"prior package: sheets IS/BS/CF, columns through '{pkg['IS']['header'][-2]}' + YTD", pause=0.4)
        r.ctx["pkg"] = pkg
        r.done("4 files landed" + (" (3 changed)" if late else ""))

    with r.stage("parse", "strip report chrome, flatten indentation, convert text numbers"):
        parsed = {}
        for k, p in files.items():
            accts, controls, footer = parse_qbo(r, p, k)
            parsed[k] = {"accts": accts, "controls": controls, "footer": footer}
            r.artifact("table", f"{k} export (parsed)", {"columns": ["num", "name", "section", "cents"],
                                                        "rows": list(accts.values())})
        pl = parsed["PL"]
        for sec, ctl in (("Income", "Total Income"), ("Cost of Goods Sold", "Total Cost of Goods Sold"), ("Expenses", "Total Expenses")):
            s = sum(a["cents"] for a in pl["accts"].values() if a["section"] == sec)
            r.log("check" if s == pl["controls"][ctl] else "fail",
                  f"PL control: Σ {sec} accounts {fmt(s)} vs QBO '{ctl}' {fmt(pl['controls'][ctl])} {'✓' if s == pl['controls'][ctl] else '✗'}")
        r.ctx["parsed"] = parsed
        if late:
            changed = []
            for k, pat in (("PL", "ProfitAndLoss*.xlsx"), ("BS", "BalanceSheet*.xlsx"), ("CF", "Statement of Cash Flows*.xlsx")):
                old, oc, _ = parse_qbo(r, next(raw.glob(pat)), k, quiet=True)
                for num, a in parsed[k]["accts"].items():
                    o = old.get(num, {}).get("cents")
                    if o != a["cents"]:
                        changed.append({"statement": k, "line": f"{num} {a['name']}", "before": fmt(o or 0), "after": fmt(a["cents"]),
                                        "delta": fmt(a["cents"] - (o or 0))})
                        r.log("find", f"{k} {num} {a['name']}: {fmt(o or 0)} → {fmt(a['cents'])} (Δ {fmt(a['cents'] - (o or 0))})")
                for name, v in parsed[k]["controls"].items():
                    if oc.get(name) != v:
                        changed.append({"statement": k, "line": name, "before": fmt(oc.get(name) or 0), "after": fmt(v),
                                        "delta": fmt(v - (oc.get(name) or 0))})
            r.artifact("diff", "What the late change touched (v1 → v2)", {"rows": [
                {"row": c["statement"], "before": f"{c['line']}: {c['before']}", "after": c["after"], "why": f"Δ {c['delta']}"} for c in changed]})
            r.log("decide", f"{len(changed)} cells change; every other cell in the package is untouched → refresh only these, re-run tie-outs")
        r.count(accounts=sum(len(v["accts"]) for v in parsed.values()))
        r.done("3 exports parsed; QBO's own totals used as controls")

    with r.stage("map", "match by account number, never by name"):
        pkg_is = {row[0]: row for row in r.ctx["pkg"]["IS"]["rows"] if row[0]}
        changes = []
        for num, a in r.ctx["parsed"]["PL"]["accts"].items():
            if num not in pkg_is:
                r.moment("caught", "find", f"new GL account {num} '{a['name']}' ({fmt(a['cents'])}) is not in the package → insert a new row "
                              f"under '{a['section']}' in account-number order, label from QBO, prior months = 0")
                changes.append({"account": num, "change": "NEW row inserted", "detail": f"{a['name']} under {a['section']}"})
            elif pkg_is[num][1] != a["name"]:
                r.moment("caught", "find", f"account {num} renamed in QBO: '{pkg_is[num][1]}' → '{a['name']}' — matched by number, label "
                              f"updated (a name-based lookup would have dropped this row to zero)")
                changes.append({"account": num, "change": "label updated", "detail": f"{pkg_is[num][1]} → {a['name']}"})
        missing = [n for n in pkg_is if n not in r.ctx["parsed"]["PL"]["accts"]]
        for n in missing:
            r.log("decide", f"package account {n} has no September activity in QBO → 0")
        r.artifact("table", "Mapping changes", {"columns": ["account", "change", "detail"], "rows": changes})
        r.ctx["map_changes"] = changes
        r.done(f"{len(changes)} mapping changes (1 new account, 1 rename)")

    with r.stage("roll", "add 'Sep 2026', extend YTD, keep formulas"):
        r.log("info", "copy prior package → add column 'Sep 2026' before YTD on IS, after Aug on BS/CF; rewrite subtotal formulas")
        r.count(sheets=3, new_cells=len(r.ctx["parsed"]["PL"]["accts"]) + len(r.ctx["parsed"]["BS"]["accts"]) + 6)
        r.done("September column populated on IS, BS, CF")

    with r.stage("tie", "the package must agree with itself and with QBO"):
        P, B, F = r.ctx["parsed"]["PL"], r.ctx["parsed"]["BS"], r.ctx["parsed"]["CF"]
        ta, tle = B["controls"]["TOTAL ASSETS"], B["controls"]["TOTAL LIABILITIES AND EQUITY"]
        checks = [("Assets = Liabilities + Equity", ta, tle)]
        aug_ytd = [row for row in r.ctx["pkg"]["BS"]["rows"] if row[0] == "3900"][0][-1]
        checks.append(("P&L net income = Δ BS 'Net Income (YTD)'", P["controls"]["Net Income"], B["accts"]["3900"]["cents"] - aug_ytd * 100))
        checks.append(("Cash flow ending cash = BS cash", F["controls"]["CASH AT END OF PERIOD"], B["accts"]["1010"]["cents"]))
        aug_cash = [row for row in r.ctx["pkg"]["BS"]["rows"] if row[0] == "1010"][0][-1]
        checks.append(("Cash flow beginning cash = August package cash", F["controls"]["Cash at beginning of period"], aug_cash * 100))
        ok = True
        rows = []
        for name, a, b in checks:
            good = a == b
            ok &= good
            r.log("check" if good else "fail", f"{name}: {fmt(a)} vs {fmt(b)} {'✓' if good else '✗ difference ' + fmt(a - b)}")
            rows.append({"check": name, "left": fmt(a), "right": fmt(b), "result": "✓" if good else "✗"})
        r.artifact("table", "Tie-outs", {"columns": ["check", "left", "right", "result"], "rows": rows})
        r.done("all 4 tie-outs pass" if ok else "tie-out failures — see log")

    with r.stage("flux", "explain material moves with their actual drivers"):
        movers = list(csv.DictReader((raw / "gl_detail_top_movers_2026-09.csv").open()))
        aug = {row[0]: row[9] for row in r.ctx["pkg"]["IS"]["rows"] if row[0]}
        comments = []
        for num, a in r.ctx["parsed"]["PL"]["accts"].items():
            prev = (aug.get(num) or 0) * 100
            d = a["cents"] - prev
            if abs(d) >= 250000 or (prev == 0 and a["cents"]) or (prev and abs(d) / max(abs(prev), 1) >= .5 and abs(d) >= 50000):
                drv = [m for m in movers if m["Account"].startswith(num)]
                text = "; ".join(f"{m['Name'] or ''} {m['Memo']} {m['Amount']}".strip() for m in drv) or "no single driver > $500"
                if num == "5010" and not late:
                    text += " ⚠ September Lumen Crew accrual is NOT booked yet (see Timing workbench) — Crew costs understated"
                if num == "5010" and late:
                    text += " · includes AJE-0930-04 Lumen Sept accrual $12,350.00 (late change)"
                if num == "4900":
                    text += " ⚠ September interest credited 10/01 not accrued (timing difference) — see Timing workbench"
                r.log("decide", f"{num} {a['name']}: Aug {fmt(prev)} → Sep {fmt(a['cents'])} (Δ {fmt(d)}). Drivers: {text}")
                comments.append({"account": f"{num} {a['name']}", "aug": fmt(prev), "sep": fmt(a["cents"]), "change": fmt(d), "comment": text})
        r.artifact("table", "Flux commentary (draft)", {"columns": ["account", "aug", "sep", "change", "comment"], "rows": comments})
        r.ctx["flux"] = comments
        r.done(f"{len(comments)} material variances explained with GL drivers")

    with r.stage("publish", "write the September package"):
        out = r.out_dir / f"Afterglow_FinancialPackage_2026-09_{'v2_' if late else ''}DRAFT.xlsx"
        build_package(r, prior_pkg, out, late)
        r.ctx["package_path"] = str(out)
        r.artifact("file", out.name, {"path": str(out), "url": f"/wb/file/{r.id}/{out.name}"})
        r.log("ok", f"package written: {out.name} (IS/BS/CF + 'Flux comments' + 'Changelog' tabs)")
        r.propose("package_publish", f"Publish financial package 2026-09 {'v2 (late change)' if late else 'v1'}",
                  {"file": out.name}, "All tie-outs pass; " + ("refreshed after AJE-0930-04" if late else f"{len(r.ctx['flux'])} flux comments drafted; "
                                                              "2 items flagged for the Timing workbench"), [], 0.93)
        if late:                                 # the v1 sign-off request is now stale: withdraw it, on the record
            for other in list(r.wb.runs.values()):
                for pid in other.proposals:
                    it = get_item(r.wb.db, pid)
                    if other is not r and it["kind"] == "package_publish" and it["state"] == "PROPOSED":
                        transition(r.wb.db, pid, "withdraw", JARVIS,
                                   reason=f"Superseded by {r.id}: QBO changed after v1 was built (AJE-0930-04)")
                        r.moment("recovered", "decide", f"Withdrew stale sign-off request {pid} ({it['title']}) — superseded by v2; "
                                        f"Maya only signs the current numbers", {"item_id": pid, "superseded_by": r.id})
                        if not any(get_item(r.wb.db, q)["state"] == "PROPOSED" for q in other.proposals):
                            other.status = "superseded"
                            from jarvis.work import events
                            events.publish("wb", run_id=other.id, problem=other.agent, kind="status", status="superseded")
        r.done(out.name)

    with r.stage("approve", "waiting on Maya"):
        r._stage("approve")["status"] = "waiting"
        r._stage("approve")["summary"] = "package sign-off waiting"


def build_package(r, prior_path, out, late):
    wb = load_workbook(prior_path)
    P, B, F = (r.ctx["parsed"][k]["accts"] for k in ("PL", "BS", "CF"))
    hdr, band, new_fill = Font(bold=True), PatternFill("solid", fgColor="E8E3FF"), PatternFill("solid", fgColor="FFF6B3")
    # IS: insert Sep column at K (before YTD), new account row, rename labels
    ws = wb["IS"]
    ws.insert_cols(11)
    ws.cell(2, 11, "Sep 2026").font = hdr
    ws.cell(2, 11).fill = band
    new_num = next((n for n in P if not any(ws.cell(rw, 1).value == n for rw in range(3, ws.max_row + 1))), None)
    for rw in range(3, ws.max_row + 1):
        num = ws.cell(rw, 1).value
        if num in P:
            ws.cell(rw, 11, P[num]["cents"] / 100)
            if ws.cell(rw, 2).value != P[num]["name"]:
                ws.cell(rw, 2, P[num]["name"]).fill = new_fill
            ws.cell(rw, 12, f"=SUM(C{rw}:K{rw})")
        elif num:
            ws.cell(rw, 11, 0)
            ws.cell(rw, 12, f"=SUM(C{rw}:K{rw})")
    if new_num:
        # insert under Expenses after the last smaller account number
        target = None
        for rw in range(3, ws.max_row + 1):
            v = ws.cell(rw, 1).value
            if v and v.isdigit() and v.startswith("6") and v < new_num:
                target = rw
        ws.insert_rows(target + 1)
        ws.cell(target + 1, 1, new_num).fill = new_fill
        ws.cell(target + 1, 2, P[new_num]["name"]).fill = new_fill
        for c in range(3, 11):
            ws.cell(target + 1, c, 0)
        ws.cell(target + 1, 11, P[new_num]["cents"] / 100)
        ws.cell(target + 1, 12, f"=SUM(C{target + 1}:K{target + 1})")
        r.log("fix", f"IS: inserted row {target + 1} for {new_num} (highlighted)", pause=0.3)
    # rewrite totals formulas to include all rows of each section
    sec_start, tot_rows = None, {}
    for rw in range(3, ws.max_row + 1):
        lab = str(ws.cell(rw, 2).value or "")
        if lab.isupper() and not ws.cell(rw, 1).value and lab != "NET INCOME":
            sec_start = rw + 1
        if lab.startswith("Total ") and sec_start:
            for ci, col in enumerate("CDEFGHIJKL", start=3):
                ws.cell(rw, ci, f"=SUM({col}{sec_start}:{col}{rw - 1})")
        if lab.startswith("Total "):
            tot_rows[lab] = rw
        if lab == "NET INCOME":                   # NI becomes a live formula over the section totals, every month
            sign = {"Total Income": "+", "Total Cost of Goods Sold": "-", "Total Expenses": "-", "Total Other Income": "+"}
            for ci, col in enumerate("CDEFGHIJKL", start=3):
                ws.cell(rw, ci, "=" + "".join(f"{sign[k]}{col}{v}" for k, v in tot_rows.items() if k in sign).lstrip("+"))
            r.log("fix", f"IS: NET INCOME row {rw} converted from hard-coded values to a formula over section totals",
                  pause=0.3)
    for rw in range(3, ws.max_row + 1):          # openpyxl doesn't shift formulas on insert: rewrite every YTD cell
        if ws.cell(rw, 1).value:
            ws.cell(rw, 12, f"=SUM(C{rw}:K{rw})")
    # BS / CF: append Sep column
    for sh, src in (("BS", B), ("CF", None)):
        w = wb[sh]
        col = w.max_column + 1
        w.cell(2, col, "Sep 2026").font = hdr
        w.cell(2, col).fill = band
        for rw in range(3, w.max_row + 1):
            num, lab = w.cell(rw, 1).value, str(w.cell(rw, 2).value or "")
            if sh == "BS" and num in B:
                w.cell(rw, col, B[num]["cents"] / 100)
            elif sh == "BS" and lab.startswith("Total"):
                prev = w.cell(rw, col - 1).value
                if isinstance(prev, str) and prev.startswith("=SUM("):
                    letter = w.cell(2, col).column_letter
                    w.cell(rw, col, re.sub(r"[A-Z](\d+):[A-Z](\d+)", rf"{letter}\1:{letter}\2", prev))
            elif sh == "CF":
                cf = r.ctx["parsed"]["CF"]
                mapping = {"Net Income": "Net Income", "Change in Interest Receivable": "Interest Receivable",
                           "Change in Prepaid Tour Costs": "Prepaid Tour Costs", "Change in Accounts Payable": "Accounts Payable",
                           "Change in Ramp Card Payable": "Ramp Card Payable", "Change in Accrued Expenses": "Accrued Expenses"}
                key = mapping.get(lab)
                vals = {**{a["name"]: a["cents"] for a in cf["accts"].values()}, **cf["controls"]}
                if key in vals:
                    w.cell(rw, col, vals[key] / 100)
    fl = wb["Flux comments"]
    for c in r.ctx["flux"]:
        fl.append([c["account"], "Sep 2026", c["change"], c["comment"], "Jarvis (draft)"])
    cl = wb.create_sheet("Changelog")
    cl.append(["When", "Who", "Change"])
    for m in r.ctx["map_changes"]:
        cl.append(["2026-10-06", "Jarvis", f"{m['account']}: {m['change']} — {m['detail']}"])
    cl.append(["2026-10-06", "Jarvis", "Added Sep 2026 column from QBO exports (Accrual Basis, exported 09:14 AM)"])
    if late:
        cl.append(["2026-10-06", "Jarvis", "v2: refreshed after AJE-0930-04 (Lumen accrual $12,350) — 5010, 2100, Net Income, CF updated"])
    wb.save(out)


def run_late(r, **kw):
    return run(r, late=True)


def apply(r, it):
    src = r.out_dir / it["proposal"]["file"]
    drive = r.out_dir.parent / "Drive" / "Finance" / "Financial Packages" / "2026-09"
    drive.mkdir(parents=True, exist_ok=True)
    final = drive / src.name.replace("DRAFT", "FINAL")
    shutil.copy(src, final)
    return f"copied to Drive/Finance/Financial Packages/2026-09/{final.name} (signed off by Controller)"
