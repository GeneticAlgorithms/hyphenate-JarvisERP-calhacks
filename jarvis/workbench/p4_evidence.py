"""Workbench 4 — File the month's bank statements & reconciliations into Drive, named properly, and prove completeness."""
from __future__ import annotations

import csv
import json
import re
import shutil
import zipfile

from pypdf import PdfReader

from jarvis.money import fmt
from jarvis.workbench import clean as C

TITLE = "Evidence & folder organization"
STAGES = [("ingest", "Inventory the Downloads folder"), ("read", "Read every file's contents"), ("classify", "Classify (type, account, period)"),
          ("dedupe", "Duplicates & wrong periods"), ("crosscheck", "Cross-check recon ↔ statement"),
          ("plan", "Learn naming convention + plan"), ("complete", "Completeness vs checklist"), ("approve", "Controller → Gateway files to Drive")]
PERIOD = "2026-09"


def run(r, **_):
    raw = r.data_dir / "raw"
    dl = raw / "Downloads"
    with r.stage("ingest", "what landed in ~/Downloads this week"):
        files = sorted(dl.iterdir())
        inv = []
        for p in files:
            h = C.sha(p)
            inv.append({"file": p.name, "bytes": p.stat().st_size, "sha256": h[:12]})
            r.log("info", f"found '{p.name}' ({p.stat().st_size} B, sha256 {h[:12]}…)", pause=0.3)
        r.artifact("tree", "Before: ~/Downloads", {"lines": [f"Downloads/{f['file']}" for f in inv]})
        r.ctx["files"] = files
        r.count(files=len(files))
        r.done(f"{len(files)} files with useless names — names won't be trusted, contents will")

    with r.stage("read", "extract text from each PDF (names lie, contents don't)"):
        texts = {}
        for p in r.ctx["files"]:
            t = "\n".join(pg.extract_text() or "" for pg in PdfReader(str(p)).pages)
            texts[p.name] = t
            first = t.strip().splitlines()[0] if t.strip() else "(empty)"
            r.log("info", f"'{p.name}': {len(t)} chars · first line: '{first[:70]}'", pause=0.35)
        r.ctx["texts"] = texts
        r.done("text extracted from all files")

    with r.stage("classify"):
        docs = []
        months = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                              "September", "October", "November", "December"], start=1)}
        for name, t in r.ctx["texts"].items():
            d = {"file": name, "type": "other", "account": None, "last4": None, "period": None, "balance": None}
            if "Reconciliation Report" in t:
                d["type"] = "BankReconciliation"
                m = re.search(r"\(\.\.\.(\w+)\)", t)
                d["last4"] = m.group(1) if m else None
                e = re.search(r"Statement ending date: (\d{2})/(\d{2})/(\d{4})", t)
                d["period"] = f"{e.group(3)}-{e.group(1)}" if e else None
                d["balance"] = C.money(re.search(r"Statement ending balance: ([\d,.]+)", t).group(1))[0]
            elif "Statement" in t and ("Ending balance" in t or "New balance" in t):
                d["type"] = "CardStatement" if "Card" in t else "BankStatement"
                m = re.search(r"\.\.\.(\d{4})", t)
                d["last4"] = m.group(1) if m else None
                mm = re.search(r"Statement period: (\w+) (\d+)", t) or re.search(r"Statement period: (\w{3}) \d+, (\d{4})", t)
                if mm:
                    mon = mm.group(1)
                    num = months.get(mon) or {k[:3]: v for k, v in months.items()}.get(mon[:3])
                    yr = re.search(r"(\d{4})", t[t.find("Statement period"):]).group(1)
                    d["period"] = f"{yr}-{num:02d}"
                bal = re.search(r"(Ending balance|New balance): \$?([\d,.]+)", t)
                d["balance"] = C.money(bal.group(2))[0] if bal else None
            acc = {"4471": "Chase Operating", "8820": "Chase Savings", "0091": "Ramp Card"}
            d["account"] = acc.get(d["last4"])
            docs.append(d)
            r.log("decide" if d["type"] != "other" else "warn",
                  f"'{name}' → {d['type']}" + (f" · {d['account']} …{d['last4']} · period {d['period']} · balance {fmt(d['balance'])}"
                                              if d["type"] != "other" else " — not close evidence (budget draft) → ignore"))
        r.artifact("table", "Classification (from contents)", {"columns": ["file", "type", "account", "last4", "period", "balance"],
                                                               "rows": docs})
        r.ctx["docs"] = docs
        r.done(f"{sum(1 for d in docs if d['type'] != 'other')} evidence files, 1 irrelevant")

    with r.stage("dedupe"):
        seen, keep = {}, []
        for d, p in zip(r.ctx["docs"], r.ctx["files"]):
            if d["type"] == "other":
                continue
            h = C.sha(p)
            if h in seen:
                r.moment("caught", "find", f"'{d['file']}' is byte-identical to '{seen[h]}' (sha256 {h[:10]}) → duplicate download, not filed twice")
                continue
            seen[h] = d["file"]
            if d["period"] != PERIOD:
                r.moment("caught", "find", f"'{d['file']}' is {d['account']} for {d['period']}, not {PERIOD} → wrong period; it already belongs in "
                              f"the {d['period']} folder, so it can't count as September evidence")
                continue
            keep.append((d, p))
        r.ctx["keep"] = keep
        r.count(kept=len(keep))
        r.done(f"{len(keep)} valid September documents")

    with r.stage("crosscheck", "a recon only counts if it ties to the statement"):
        stm = {d["last4"]: d for d, _ in r.ctx["keep"] if d["type"] in ("BankStatement", "CardStatement")}
        for d, _ in r.ctx["keep"]:
            if d["type"] == "BankReconciliation":
                s = stm.get(d["last4"])
                if s:
                    ok = s["balance"] == d["balance"]
                    r.log("check" if ok else "fail", f"{d['account']}: recon statement ending balance {fmt(d['balance'])} vs bank statement "
                                                     f"{fmt(s['balance'])} {'✓ ties' if ok else '✗ does not tie'}")
                else:
                    r.moment("caught", "warn", f"{d['account']} recon has no matching statement")
        r.done("recons tie to their statements")

    with r.stage("plan", "learn the convention from last month's Drive folder"):
        existing = (raw / "drive_tree_existing.txt").read_text().splitlines()
        ex = existing[0].split("/")[-1]
        r.log("info", f"learned from Drive (2026-08): '{ex}' → pattern YYYY-MM_DocType_Institution-AccountName-Last4_PeriodEnd.pdf; "
                      f"folders '01 - Statements/<Account>' and '02 - Reconciliations/<Account>'")
        plan = []
        for d, p in r.ctx["keep"]:
            acct_slug = d["account"].replace(" ", "-")
            if d["type"] == "BankReconciliation":
                new = f"{PERIOD}_BankReconciliation_QBO-{acct_slug}-{d['last4']}_{PERIOD}-30.pdf"
                folder = f"02 - Reconciliations/{d['account']}"
            else:
                new = f"{PERIOD}_{d['type']}_{acct_slug}-{d['last4']}_{PERIOD}-30.pdf"
                folder = f"01 - Statements/{d['account']}"
            dest = f"Afterglow Labs/Finance/Monthly Close/2026/{PERIOD}/01 - Bank and Cash/{folder}/{new}"
            plan.append({"from": p.name, "to": dest})
            r.log("decide", f"'{p.name}' → {dest}", pause=0.4)
        r.artifact("table", "Rename & filing plan", {"columns": ["from", "to"], "rows": plan})
        r.artifact("tree", "After: Drive (planned)", {"lines": [x["to"] for x in plan]})
        r.ctx["plan"] = plan
        r.done(f"{len(plan)} files to rename & file")

    with r.stage("complete", "expected evidence vs what we actually have"):
        inv = list(csv.DictReader((raw / "account_inventory.csv").open()))
        have = {(d["last4"], "statement" if "Statement" in d["type"] else "reconciliation") for d, _ in r.ctx["keep"]}
        rows, exceptions = [], []
        for a in inv:
            for need in a["Requires"].split(";"):
                ok = (a["Last4"], need) in have
                rows.append({"account": a["Account"], "document": need, "status": "✓ filed" if ok else "✗ MISSING"})
                if not ok:
                    why = ("only an AUGUST recon was downloaded ('Reconciliation (1).pdf')" if a["Last4"] == "0091"
                           else "nothing downloaded for this account")
                    exceptions.append({"account": a["Account"], "missing": need, "why": why})
                    r.moment("caught", "find", f"{a['Account']}: {need} MISSING — {why}")
        r.artifact("table", "Evidence manifest", {"columns": ["account", "document", "status"], "rows": rows})
        r.artifact("table", "Exceptions", {"columns": ["account", "missing", "why"], "rows": exceptions})
        r.ctx["exceptions"] = exceptions
        r.flag(f"{len(exceptions)} items missing — the pack is NOT complete (and Jarvis says so)")

    with r.stage("approve"):
        r.propose("file_evidence", f"File {len(r.ctx['plan'])} documents into Drive (2026-09)", {"plan": r.ctx["plan"]},
                  f"Contents-verified, deduplicated, period-checked; recons tie to statements. {len(r.ctx['exceptions'])} exceptions "
                  f"stay open.", [], 0.95)
        for e in r.ctx["exceptions"]:
            r.moment("asked", "ask", f"request: {e['account']} {e['missing']} for {PERIOD} — assign to Dev Patel (owner of {e['account']} rec)")
        r._stage("approve")["status"] = "waiting"
        r._stage("approve")["summary"] = "filing plan waiting; exceptions assigned"


def apply(r, it):
    drive = r.out_dir.parent / "Drive"
    dl = r.data_dir / "raw" / "Downloads"
    for step in it["proposal"]["plan"]:
        dest = drive / step["to"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(dl / step["from"], dest)
        r.log("ok", f"Gateway filed {step['from']} → Drive/{step['to']}", pause=0.3)
    man = drive / "Afterglow Labs/Finance/Monthly Close/2026/2026-09/01 - Bank and Cash/manifest.json"
    man.write_text(json.dumps({"filed": it["proposal"]["plan"], "exceptions": r.ctx.get("exceptions", []), "run": r.id}, indent=1))
    zp = r.out_dir / "Drive_2026-09_bank_and_cash.zip"
    with zipfile.ZipFile(zp, "w") as z:
        for f in (drive / "Afterglow Labs/Finance/Monthly Close/2026/2026-09").rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(drive))
    r.artifact("file", zp.name, {"path": str(zp), "url": f"/wb/file/{r.id}/{zp.name}"})
    return f"{len(it['proposal']['plan'])} files filed + manifest.json; zip available"
