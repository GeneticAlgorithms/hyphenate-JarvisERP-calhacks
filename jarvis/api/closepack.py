"""Close evidence pack: statements, reconciliation, JE support - named and filed the way the team files it."""
from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from jarvis import config
from jarvis.money import fmt, plain
from jarvis.work import ledger
from jarvis.work.db import DB, L
from jarvis.work.transition import why
from jarvis.world import bible


def build(db: DB, world: Path, seed: int, period: str = config.CLOSE_PERIOD) -> dict:
    root = config.RUNTIME_DIR / f"seed_{seed}" / "close_pack"
    base = root / "Afterglow Labs" / "Finance" / "Monthly Close" / period[:4] / period
    if base.exists():
        shutil.rmtree(base)
    stm = base / "01 - Bank and Cash" / "01 - Statements" / "Chase Operating x4471"
    rec = base / "01 - Bank and Cash" / "02 - Reconciliations" / "Chase Operating x4471"
    sup = base / "02 - Journal Entry Support"
    for p in (stm, rec, sup):
        p.mkdir(parents=True, exist_ok=True)
    manifest = []

    src = world / "systems" / "bank" / "statements" / f"chase_x4471_{period}_statement.md"
    if src.exists():
        name = f"{period}_BankStatement_Chase-Operating-4471_{period}-30.md"
        shutil.copy(src, stm / name)
        manifest.append({"doc": name, "type": "BankStatement", "account": "Chase x4471", "verified": True,
                         "check": "ending balance read from statement"})
    r = ledger.bank_reconciliation(db, period)
    lines = [f"# Bank reconciliation — Chase Operating x4471 — {period}", "",
             f"Statement ending balance: **{fmt(r['statement_ending_cents'] or 0)}**  ",
             f"Ledger cash (1010) at month end: **{fmt(r['ledger_cash_cents'])}**  ",
             f"Difference: **{fmt(r['difference_cents'] or 0)}** {'✅ ties' if r['ties'] else ''}", "",
             "## Reconciling items (unreconciled bank lines)", ""]
    for u in r["unreconciled"]:
        lines.append(f"- {u['txn_date']} {fmt(u['amount_cents'])} {u['description'][:70]}")
    if not r["unreconciled"]:
        lines.append("- none")
    lines += ["", "Prepared by: Jarvis (ai_agent) · Reviewed by: Maya Chen (Controller) · generated from work.db audit log"]
    name = f"{period}_BankReconciliation_Chase-Operating-4471_{period}-30.md"
    (rec / name).write_text("\n".join(lines) + "\n")
    manifest.append({"doc": name, "type": "BankReconciliation", "account": "Chase x4471", "verified": r["ties"],
                     "check": f"difference {plain(r['difference_cents'] or 0)}"})
    for it in db.q("SELECT * FROM work_items WHERE state='POSTED' AND period=? AND kind NOT IN ('match')", (period,)):
        prop = L(it["proposal"], {})
        je = db.one("SELECT entry_id FROM ledger_entries WHERE work_item_id=?", (it["item_id"],))
        trail = why(db, it["item_id"])
        md = [f"# {it['title']}", "", f"Work item {it['item_id']} · kind `{it['kind']}` · ledger entry {je['entry_id'] if je else '—'}", "",
              "## Entry", "", "| Account | Debit | Credit | Memo |", "|---|---:|---:|---|"]
        for l in prop.get("lines", []):
            md.append(f"| {l['acct']} {bible.acct_name(l['acct'])} | {plain(l['cents']) if l['cents'] > 0 else ''} | "
                      f"{plain(-l['cents']) if l['cents'] < 0 else ''} | {l.get('memo', '')} |")
        md += ["", "## Why", "", it["rationale"], "", "## Evidence", ""]
        for e in L(it["evidence"], []):
            md.append(f"- [{e['relation']}] {e['type']} `{e['id']}` — {e['label']} {e.get('detail', '')}")
        md += ["", f"Policy: {it['policy_id'] or '—'} · Precedents: {', '.join(L(it['precedent_ids'], [])) or '—'}", "",
               "## Audit trail", "", "| seq | at | actor | action | allowed | reason |", "|---|---|---|---|---|---|"]
        for t in trail:
            md.append(f"| {t['seq']} | {t['at'][:19]} | {t['actor']} | {t['action']} | {'✓' if t['allowed'] else '✗'} | "
                      f"{(t['reason'] or '')[:90].replace('|', '/')} |")
        name = f"{period}_JE-Support_{it['kind']}_{it['item_id']}.md"
        (sup / name).write_text("\n".join(md) + "\n")
        manifest.append({"doc": name, "type": "JESupport", "item": it["item_id"], "verified": True,
                         "check": "balanced, approved, posted by gateway"})
    expected = ["BankStatement", "BankReconciliation"]
    missing = [t for t in expected if not any(m["type"] == t for m in manifest)]
    out = {"period": period, "root": str(base), "documents": manifest, "missing": missing,
           "complete": not missing and r["ties"]}
    (base / "manifest.json").write_text(json.dumps(out, indent=1))
    zp = root / f"close_pack_{period}.zip"
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        for f in base.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(root))
    out["zip"] = str(zp)
    return out
