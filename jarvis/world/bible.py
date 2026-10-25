"""The company bible: Afterglow Labs, Inc.

Everything here is fictional. Vendor names that are real companies (Anthropic,
Anysphere, Google, AWS, Gusto, Stripe, PayPal, Ramp, Chase) are used only as
counterparties so the data looks like a real 2026 startup's books.
"""
from __future__ import annotations

COMPANY = {
    "name": "Afterglow Labs, Inc.",
    "short": "Afterglow",
    "hq": "Oakland, CA",
    "employees": 28,
    "functional_currency": "USD",
    "fiscal_year_end": "12-31",
    "description": (
        "Audio-visual studio with two businesses: Afterglow Cloud (a SaaS for live-visuals "
        "artists, billed via Stripe) and Afterglow Live (produces AV shows for festivals "
        "and clubs in the US and EU; EU crews are paid in EUR through PayPal)."
    ),
}

# --- Chart of accounts ------------------------------------------------------
# number: (beancount name, display name, type)
COA = {
    "1010": ("Assets:Cash:Chase-Operating", "Cash - Chase Operating x4471", "Bank"),
    "1030": ("Assets:Cash:PayPal", "PayPal Balance", "Bank"),
    "1250": ("Assets:Receivable:Employee", "Employee Receivable", "Other Current Asset"),
    "1260": ("Assets:Receivable:Interest", "Interest Receivable", "Other Current Asset"),
    "1310": ("Assets:Prepaid:Tour-Costs", "Prepaid Tour Costs", "Other Current Asset"),
    "1320": ("Assets:Prepaid:Software", "Prepaid Software", "Other Current Asset"),
    "2010": ("Liabilities:AP", "Accounts Payable", "Accounts Payable"),
    "2050": ("Liabilities:Ramp-Card", "Ramp Card Payable", "Credit Card"),
    "2100": ("Liabilities:Accrued-Expenses", "Accrued Expenses", "Other Current Liability"),
    "3000": ("Equity:Opening-Balances", "Opening Balance Equity", "Equity"),
    "4010": ("Income:SaaS", "SaaS Subscription Revenue", "Income"),
    "4020": ("Income:Live-Shows", "Live Show Revenue", "Income"),
    "4900": ("Income:Interest", "Interest Income", "Other Income"),
    "4950": ("Income:Other", "Other Income", "Other Income"),
    "5010": ("Expenses:COGS:Crew-Production", "Crew & Production Costs", "Cost of Goods Sold"),
    "5020": ("Expenses:COGS:Gear-Rental", "Gear Rental", "Cost of Goods Sold"),
    "5030": ("Expenses:COGS:Gear-Purchases", "Gear & Equipment (expensed)", "Cost of Goods Sold"),
    "6100": ("Expenses:Payroll", "Salaries & Wages", "Expense"),
    "6410": ("Expenses:Software-AI", "Software & AI Tools", "Expense"),
    "6420": ("Expenses:Advertising", "Advertising & Marketing", "Expense"),
    "6430": ("Expenses:Travel", "Travel", "Expense"),
    "6440": ("Expenses:Meals", "Meals", "Expense"),
    "6450": ("Expenses:Cloud-Hosting", "Cloud Hosting", "Expense"),
    "6810": ("Expenses:Bank-FX-Fees", "Bank & FX Fees", "Expense"),
    "6900": ("Expenses:Office", "Office & Misc", "Expense"),
}


def acct(num: str) -> str:
    return COA[num][0]


def acct_name(num: str) -> str:
    return COA[num][1]


NUM_BY_BEAN = {v[0]: k for k, v in COA.items()}

# --- People -----------------------------------------------------------------
PEOPLE = {
    "maya": {"name": "Maya Chen", "role": "Controller", "email": "maya@afterglowlabs.com",
             "actor": "human_controller"},
    "dev": {"name": "Dev Patel", "role": "Staff Accountant (human)", "email": "dev@afterglowlabs.com",
            "actor": "human_accountant"},
    "jortiz": {"name": "J. Ortiz", "role": "Tour Manager", "email": "j.ortiz@afterglowlabs.com",
               "actor": "employee"},
    "sam": {"name": "Sam Rivera", "role": "Creative Director", "email": "sam@afterglowlabs.com",
            "actor": "employee"},
    "lee": {"name": "Lee Okafor", "role": "Head of Engineering", "email": "lee@afterglowlabs.com",
            "actor": "employee"},
}

# --- Vendor master ----------------------------------------------------------
# canonical vendors (as they exist in QBO) + evidence used for identity resolution
VENDORS = [
    {"id": "V-ANTHROPIC", "qbo_name": "Anthropic", "legal": "Anthropic, PBC", "domain": "anthropic.com",
     "default_acct": "6410", "products": ["Claude", "Claude Pro", "Claude Max", "Claude API"], "tin": "84-1xxx401",
     "phone": "+1-415-555-0198"},
    {"id": "V-ANYSPHERE", "qbo_name": "Anysphere", "legal": "Anysphere, Inc.", "domain": "cursor.com",
     "default_acct": "6410", "products": ["Cursor", "Cursor Business", "Cursor Pro"], "tin": "88-2xxx117",
     "phone": "+1-415-555-0142"},
    {"id": "V-GOOGLE", "qbo_name": "Google", "legal": "Google LLC", "domain": "google.com",
     "default_acct": "6410", "products": ["Google Workspace", "Google Ads", "Google Cloud"], "tin": "77-0xxx309",
     "phone": "+1-650-555-0100"},
    {"id": "V-SPLICE", "qbo_name": "Splice", "legal": "Splice.com, Inc.", "domain": "splice.com",
     "default_acct": "6410", "products": ["Splice Sounds", "Splice.com"], "tin": "46-3xxx982",
     "phone": "+1-646-555-0173"},
    {"id": "V-AWS", "qbo_name": "Amazon Web Services", "legal": "Amazon Web Services, Inc.", "domain": "aws.amazon.com",
     "default_acct": "6450", "products": ["AWS"], "tin": "91-1xxx586",
     "phone": "+1-206-555-0134"},
    {"id": "V-KRAFTWERK", "qbo_name": "Kraftwerk Rigging GmbH", "legal": "Kraftwerk Rigging GmbH", "domain": "kraftwerk-rigging.de",
     "default_acct": "5010", "products": [], "tin": "DE31xxxx902", "currency": "EUR",
     "phone": "+49-30-555-8742"},
    {"id": "V-DAMLICHT", "qbo_name": "Damlicht Crew B.V.", "legal": "Damlicht Crew B.V.", "domain": "damlicht.nl",
     "default_acct": "5010", "products": [], "tin": "NL85xxxx01B01", "currency": "EUR",
     "phone": "+31-20-555-6391"},
    {"id": "V-LUMENCREW", "qbo_name": "Lumen Crew LLC", "legal": "Lumen Crew LLC", "domain": "lumencrew.co",
     "default_acct": "5010", "products": [], "tin": "83-4xxx210",
     "phone": "+1-510-555-0287"},
    {"id": "V-NADIA", "qbo_name": "Nadia Kroll", "legal": "Nadia Kroll (sole prop.)", "domain": "nadiakroll.studio",
     "default_acct": "5010", "products": [], "tin": "xxx-xx-4410",
     "phone": "+1-415-555-0261"},
    {"id": "V-BAYRIG", "qbo_name": "Bay Rig Rentals", "legal": "Bay Rig Rentals Inc.", "domain": "bayrig.com",
     "default_acct": "5020", "products": [], "tin": "94-3xxx775",
     "phone": "+1-510-555-0194"},
    {"id": "V-STROBE", "qbo_name": "Strobe & Co", "legal": "Strobe & Co LLC", "domain": "strobeandco.com",
     "default_acct": "5010", "products": [], "tin": "82-1xxx339",
     "phone": "+1-415-555-0229"},
    {"id": "V-GUSTO", "qbo_name": "Gusto", "legal": "Gusto, Inc.", "domain": "gusto.com",
     "default_acct": "6100", "products": [], "tin": "45-2xxx112",
     "phone": "+1-800-555-7500"},
    {"id": "V-DELTA", "qbo_name": "Delta Air Lines", "legal": "Delta Air Lines, Inc.", "domain": "delta.com",
     "default_acct": "6430", "products": [], "tin": "58-0xxx218",
     "phone": "+1-800-221-1212"},
]

# Vendors that show up in Ramp but are NOT in QBO yet (Ramp "suggests" creating them)
RAMP_SUGGESTED_VENDORS = {
    "Claude": {"true_vendor": "V-ANTHROPIC", "receipt_issuer": "Anthropic, PBC", "domain": "anthropic.com"},
    "Cursor": {"true_vendor": "V-ANYSPHERE", "receipt_issuer": "Anysphere, Inc.", "domain": "cursor.com"},
    "Google Ads": {"true_vendor": "V-GOOGLE", "receipt_issuer": "Google LLC", "domain": "google.com"},
    "Splice.com": {"true_vendor": "V-SPLICE", "receipt_issuer": "Splice.com, Inc.", "domain": "splice.com"},
    # TRAP: looks like Lumen Crew LLC but is a different legal entity (a photo studio)
    "Lumen Studios": {"true_vendor": None, "receipt_issuer": "Lumen Studios SF LLC", "domain": "lumenstudios.com",
                       "tin": "27-9xxx551"},
}

# Merchant categories the controller ruled personal (precedent P-0317, March)
PERSONAL_MCC = {
    "5651": "Family Clothing Stores",
    "5311": "Department Stores",
    "5816": "Digital Goods - Games",
    "5977": "Cosmetic Stores",
}

FESTIVALS = [
    ("MELT Festival GmbH", "Deutsche Bank AG", "EUR"),
    ("Dekmantel B.V.", "ABN AMRO", "EUR"),
    ("Desert Hearts LLC", "Wells Fargo", "USD"),
    ("Portola Presents LLC", "First Republic", "USD"),
]

POLICY_TEXT = """\
# Afterglow Labs — Close Policy (excerpt)

Owner: Maya Chen, Controller · Effective 2026-01-01

1. **Basis.** Accrual basis, US GAAP. Functional currency USD.
2. **Cut-off.** Expenses belong to the period the service is performed. Payments for services in a
   future period are recorded as prepaid (1310 Prepaid Tour Costs for show deposits) and expensed
   when the show happens.
3. **Foreign currency.** Foreign-currency payments are recorded at the market (ECB reference) rate
   on the payment date. Any difference between the USD actually paid and the market-rate USD is a
   conversion fee, booked to 6810 Bank & FX Fees.
4. **Accruals.** At month end, accrue services performed but not yet invoiced when supported by
   evidence of performance (timesheet, run-of-show, delivery confirmation). Preferred measurement:
   (a) vendor invoice received after period end for the period's service, then (b) contract rate x
   approved hours, then (c) flat contract fee with performance evidence, then (d) vendor estimate.
   A signed contract alone is a commitment, not evidence of performance.
   Accruals reverse on the first day of the next period; the actual invoice is booked normally and any
   difference is the true-up.
5. **Personal purchases.** Purchases on company cards or PayPal for personal use are recorded to
   1250 Employee Receivable and the employee is notified (ruling P-0317). Size does not matter.
6. **Vendor master.** Product names are not vendors. Link aliases to the legal entity on the invoice.
   Creating or merging vendors requires Controller approval.
7. **Approvals.** The preparer of an entry may never approve it. Standing policy P-001 lets exact
   matches to existing subledger entries (bill payments, card statement payments, synced deposits,
   payroll) and bank service fees under $250 be approved without review. Everything else requires
   Controller approval.
8. **Locked periods.** Periods through August 2026 are closed. Corrections to closed periods are
   booked in the current period as prior-period adjustments.
"""

APPROVAL_MATRIX = {
    "standing_policies": {
        "P-001": {
            "set_by": "Maya Chen (Controller)",
            "auto_approve_kinds": ["match", "bill_payment", "card_statement_payment"],
            "auto_approve_bank_fee_below_cents": 25000,
            "never_auto": ["fx", "prepaid", "personal", "accrual", "vendor_link", "vendor_create",
                            "reclass", "duplicate", "unknown"],
        }
    },
    "materiality_cents": 50000,
}
