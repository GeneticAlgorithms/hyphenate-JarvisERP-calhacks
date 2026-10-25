const TERMS = [
  { term: 'Debit', definition: 'An accounting entry that increases assets or expenses, or decreases liabilities or equity. Always on the left side of the ledger.' },
  { term: 'Credit', definition: 'An accounting entry that increases liabilities or equity, or decreases assets or expenses. Always on the right side.' },
  { term: 'Net Amount', definition: 'The final result after debits and credits offset each other. In a balanced entry, total debits equal total credits.' },
  { term: 'ERP', definition: 'Enterprise Resource Planning system. Software that manages core business processes including accounting, inventory, and operations.' },
  { term: 'General Ledger (GL)', definition: 'The master accounting record containing all financial transactions, organized by account. The source of truth for financial statements.' },
  { term: 'Reconcile', definition: 'The process of matching records from two sources (e.g., bank statements and internal ledger) to ensure they agree and identify discrepancies.' },
  { term: 'AP (Accounts Payable)', definition: 'Money the company owes to vendors and suppliers. A liability on the balance sheet until paid.' },
  { term: 'AR (Accounts Receivable)', definition: 'Money customers owe to the company. An asset on the balance sheet until collected.' },
  { term: 'Accrual', definition: 'Recording revenue when earned and expenses when incurred, regardless of when cash changes hands. The foundation of accrual accounting.' },
  { term: 'Prepaid', definition: 'An asset representing payment made in advance for goods or services to be received in the future (e.g., prepaid insurance, deposits).' },
  { term: 'Materiality', definition: 'The threshold at which a misstatement becomes significant enough to influence decisions. Does not determine classification.' },
  { term: 'Chart of Accounts', definition: 'The organized list of all accounts used in the ledger, typically numbered (e.g., 1000s for assets, 6000s for expenses).' },
  { term: 'Subledger', definition: 'A detailed record supporting a GL control account, like individual vendor balances backing up the AP total.' },
  { term: 'Journal Entry (JE)', definition: 'A record of a financial transaction with debits and credits that must balance. The atomic unit of accounting.' },
  { term: 'Approval Matrix', definition: 'A control defining who can approve transactions at different dollar thresholds or categories.' },
  { term: 'Precedent', definition: 'A recorded decision on how similar transactions should be classified in the future, building institutional knowledge.' },
  { term: 'Audit Trail', definition: 'A chronological record of all changes, showing who did what and when, enabling verification and compliance.' },
  { term: 'Hash Chain', definition: 'A cryptographic structure where each record includes the hash of the previous one, making tampering detectable.' }
]

export function initGlossary() {
  const grid = document.getElementById('glossary-grid')
  const search = document.getElementById('glossary-search') as HTMLInputElement
  
  function render(filter = '') {
    if (!grid) return
    
    const filtered = TERMS.filter(({ term, definition }) =>
      term.toLowerCase().includes(filter.toLowerCase()) ||
      definition.toLowerCase().includes(filter.toLowerCase())
    )
    
    grid.innerHTML = filtered.map(({ term, definition }) => `
      <div class="glossary-term">
        <h4>${term}</h4>
        <p>${definition}</p>
      </div>
    `).join('')
  }
  
  render()
  
  search?.addEventListener('input', (e) => {
    render((e.target as HTMLInputElement).value)
  })
}
