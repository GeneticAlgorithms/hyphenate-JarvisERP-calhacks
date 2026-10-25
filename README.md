# JarvisERP — Cal Hacks 2026 Submission

**An autonomous Staff Accountant you could actually hire**

JarvisERP fills the **Staff Accountant (cash & expense close)** and **Vendor-Master Clerk** seats for a small business. It reconciles bank, PayPal and Ramp to the ledger, books accruals and timing entries, and keeps the vendor list deduplicated. It **cannot post anything its human Controller hasn't approved**: that limit is enforced in code, not in a prompt.

**Cal Hacks 2026 · Hyphenate track — "The Hyphenated Enterprise: Autonomous Systems for Finance"**

🌐 **Live showcase site**: https://geneticalgorithms.github.io/hyphenate-JarvisERP-calhacks/

---

## Quick Start

### Running the Backend

The JarvisERP backend is a Python FastAPI + SQLite app with a web-based Workbench UI.

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Set API key (optional):**
```bash
export ANTHROPIC_API_KEY=your_key_here
# OR run in offline mode:
export JARVIS_LLM=off
```

**Run the server:**
```bash
python -m jarvis.api
```

The Workbench UI will be available at http://localhost:8000

### Testing

```bash
# Run tests (offline mode)
JARVIS_LLM=off pytest -q

# Or with LLM features enabled
pytest -q
```

---

## Data: synthetic but realistic

**Afterglow Labs** (an AV touring studio, September 2026 close) is synthetic — no real client books are exposed. But it's modeled on real bookkeeping:

- **QBO-style chart of accounts**: 1010 Cash, 1250 Employee Receivable, 1310 Prepaid, 5030 Gear & Equipment, 6410 Software & AI Tools, 6810 Bank & FX Fees, 6900 Office Supplies
- **Real bank descriptor formats**: `PAYPAL *INST XFER`, `ZELLE`, `SQ *VENDOR`, `RAMP*1234`
- **Four source feeds**: Chase bank CSV, PayPal activity export, Ramp card charges, QuickBooks General Ledger
- **To-the-cent amounts with FX fees**: €2,950 Kraftwerk deposit at ECB rate 1.0765 → $3,175.68 market + $275.82 PayPal spread = $3,451.50 prepaid
- **$500 materiality threshold** (50000 cents in `bible.APPROVAL_MATRIX`)
- **Written policies and precedents**: P-0317 (personal purchases → 1250 Employee Receivable regardless of amount, March 2026)
- **Real close problems**: bundled PayPal payments requiring subset-sum matching, personal card spend mixed with business, accruals for Sep-earned/Oct-received interest, duplicate vendors (Anthropic vs Anthropic PBC), vendor bank-change fraud attempts

**What's real (not simulated):**

- **The reasoning**: Every classification, split, and accrual decision is the agent's judgment from context, policies, and precedents — no hard-coded rules for specific transactions
- **Claude API calls**: When `ANTHROPIC_API_KEY` is set, the agent uses live Claude 4 Sonnet/Haiku models for LLM-grounded challenge responses and policy proposals (gracefully falls back to deterministic templates when the key is absent)
- **Role controls**: The 403 denial when Jarvis tries to self-approve is enforced by `jarvis/work/roles.py` `can(actor, action, resource_kind, res)` — not a simulated response
- **Hash-chained audit log**: Every action writes a SHA-256-chained row to `audit_log` with SQLite append-only triggers; the Auditor can verify the chain with `GET /api/verify` and detect any tampering

---

## Project Structure

```
├── showcase/           # Static website (GitHub Pages)
├── jarvis/            # Backend Python package
│   ├── agent/         # Close agents, LLM integration
│   ├── api.py         # FastAPI server
│   ├── work/          # Work items, roles, transitions
│   └── world/         # Business data, policies
├── ui/                # Workbench web UI
├── tests/             # Test suite
└── requirements.txt   # Python dependencies
```

---

## About

**Solo project by Alexander Le**, built with Cursor and Grok Bot for Cal Hacks 2026.

For full documentation, architecture diagrams, and implementation details, see [BACKEND_README.md](BACKEND_README.md).
