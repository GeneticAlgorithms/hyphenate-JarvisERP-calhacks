"""The five problems, in the accountant's own words (from our accountant teammate's brief)."""

SCENARIOS = {
    "p1_timing": {
        "tab": "Timing & Accruals", "icon": "⏱",
        "problem": "Interest earned September 1–30 is deposited October 1, so it hits the bank in a different month than it was "
                   "earned — September needs an Other Receivable. Separately, vendors did work in September but invoice later; "
                   "they're slow to respond, and for larger clients it's hard to gather the context on what needs to be accrued.",
        "pain": ["Timing difference: cash month ≠ earned month", "Estimate work done but not yet invoiced",
                 "Vendors take a long time to respond", "Context is scattered across contracts, timesheets, email"],
        "default_task": "Close September: find revenue earned in September but received in October, and accrue any vendor work "
                        "performed in September that hasn't been billed. Reach out to vendors where needed. Draft the entries with "
                        "Oct 1 reversals for my approval.",
        "agents": ["p1_timing"],
    },
    "p2_rollforward": {
        "tab": "Package Roll-forward", "icon": "📊",
        "problem": "Every month I take last month's Excel financial package plus the QBO Balance Sheet, Income Statement and Cash "
                   "Flow exports, and manually add a column for the new month. A new GL account means manually adding and "
                   "labeling rows. A last-minute change in QBO means downloading all three files again and redoing it.",
        "pain": ["Manually add next month's columns", "New GL accounts need new rows + labels",
                 "QBO exports are formatted reports, not data", "Last-minute QBO change → redo everything"],
        "default_task": "Roll the August package forward to September from the raw QBO exports. Handle new or renamed accounts, "
                        "tie everything out, draft flux comments, and give me the workbook to sign off.",
        "agents": ["p2_rollforward", "p2_late"],
    },
    "p3_bank": {
        "tab": "Bank Transactions", "icon": "🏦",
        "problem": "Bank feed descriptions don't match or don't give enough context. The QBO bank feed says 'PayPal transaction' — "
                   "but which PayPal transaction? I have to log into PayPal and look it up manually, which takes extra time.",
        "pain": ["Descriptor names the payment rail, not the merchant", "One debit can be several purchases",
                 "Currency conversion makes amounts differ", "QBO's suggested category is a guess"],
        "default_task": "Work the September 'For Review' bank feed. For every line that doesn't say what it is, look it up (PayPal, "
                        "receipts, order history), match it to the cent, and propose the right categorization. Ask me if you can't support it.",
        "agents": ["p3_bank"],
    },
    "p4_evidence": {
        "tab": "Evidence & Folders", "icon": "🗂",
        "problem": "We save every bank statement and reconciliation to Google Drive. I manually download each statement and recon, "
                   "rename it properly and file it in the right folder — and I still have to check nothing is missing.",
        "pain": ["Downloads have useless names ('Statement (3).pdf')", "Duplicates and wrong-month files",
                 "A statement isn't a reconciliation", "Hard to prove the pack is complete"],
        "default_task": "File September's bank statements and reconciliations from my Downloads folder into Drive using our naming "
                        "convention, and tell me exactly what's missing.",
        "agents": ["p4_evidence"],
    },
    "p5_vendors": {
        "tab": "Duplicate Vendors", "icon": "👥",
        "problem": "Claude/Anthropic, Anysphere/Cursor and Google/Google Ads end up as separate vendors. It happens because a bill is "
                   "paid under 'Anthropic', but on Ramp someone buys a Claude subscription and Ramp suggests creating a new vendor 'Claude'.",
        "pain": ["Product names become vendors", "Spend history split across records",
                 "Look-alike names that are NOT the same company", "Happens again every month"],
        "default_task": "Clean up the vendor master: find duplicates across QBO, Ramp and PayPal, prove which ones are the same legal "
                        "entity, keep look-alikes separate, show the impact, and stop it happening again.",
        "agents": ["p5_vendors"],
    },
}

EXTRA = {'p1_timing': {'eyebrow': '01 · Cut-off, the month the work happened', 'headline': ['Earned in September,', 'paid in October.'], 'seat': 'Staff Accountant: accruals & cut-off', 'reads': 'Bank export, QBO GL & AP, contracts, timesheets, vendor email (read-only)', 'writes': 'Nothing directly. Proposes journal entries; the Gateway posts after Controller approval', 'asks': 'A vendor goes quiet, sources disagree, or history says the Controller corrected this before', 'new': 'Chases the vendor itself (simulated email), measures the accrual three ways, and escalates when the vendor goes silent.'}, 'p2_rollforward': {'eyebrow': '02 · The monthly package, rolled forward', 'headline': ['Add a month,', 'not a weekend.'], 'seat': 'Senior Accountant: reporting package', 'reads': "Last month's workbook + QBO P&L, BS, CF exports (read-only)", 'writes': "A draft workbook. Publishing to Drive as FINAL needs the Controller's sign-off", 'asks': 'A tie-out fails, or QBO changes after the package was built', 'new': 'Treats formatted QBO reports as data, matches rows by account number, and diffs a last-minute re-export down to the cell.'}, 'p3_bank': {'eyebrow': "03 · The bank feed says 'PayPal'", 'headline': ['Which PayPal transaction?', 'All of them, to the cent.'], 'seat': 'Staff Accountant: cash & bank feed', 'reads': 'QBO bank feed, PayPal activity (read-only SSO), receipts inbox, order history, SOWs, ECB rates', 'writes': 'Nothing directly. Proposes categorizations and splits; asks when support is missing', 'asks': "It can't find support (Zelle to 'R Lopez'). A hint isn't evidence", 'new': 'Solves which PayPal payments one bank debit funded (subset-sum), then applies FX, cut-off and the personal-purchase policy line by line.'}, 'p4_evidence': {'eyebrow': '04 · Close evidence, filed', 'headline': ["'Statement (3).pdf'", 'is not a filing system.'], 'seat': 'Close Coordinator: evidence & audit binder', 'reads': "~/Downloads PDFs (contents, not file names), account inventory, last month's Drive tree", 'writes': 'A filing plan + manifest. Files move into Drive only after approval', 'asks': 'Something required is missing. It names the owner instead of quietly skipping it', 'new': 'Reads each PDF to decide what it is, learns the naming convention from last month, and proves completeness against the account list.'}, 'p5_vendors': {'eyebrow': '05 · One company, one vendor', 'headline': ['Claude is Anthropic.', 'Lumen Studios is not Lumen Crew.'], 'seat': 'Vendor-Master Clerk', 'reads': 'QBO vendor list, Ramp suggested vendors, W-9 registry, transactions (read-only)', 'writes': 'Nothing directly. Merges and Ramp rules go through the Gateway after approval', 'asks': 'Names look alike but the TINs differ, or a new vendor needs creating', 'new': "Merges on legal-entity evidence (TIN, W-9, receipt issuer, domain) instead of name similarity, and installs rules so it doesn't recur."}}
for _k, _v in EXTRA.items():
    SCENARIOS[_k].update(_v)
for _k, _v in {'p1_timing': 'Chases vendors itself', 'p2_rollforward': 'Cell-level QBO re-diff', 'p3_bank': 'Subset-sum PayPal tracing', 'p4_evidence': 'Reads files, not names', 'p5_vendors': 'Entity, not name, matching'}.items():
    SCENARIOS[_k]['new_short'] = _v
