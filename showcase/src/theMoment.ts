import { gsap } from 'gsap'

const SPLITS = [
  { account: '1310', name: 'Prepaid Tour Costs', detail: 'EUR crew deposit', amount: 3451.50 },
  { account: '6810', name: 'Bank & FX Fees', detail: 'Transfer fees', amount: 147.50 },
  { account: '6410', name: 'Software', detail: 'Claude API', amount: 200.00 },
  { account: '1250', name: 'Employee Receivable', detail: 'Maya - Steam', amount: 113.44 }
]

function formatCurrency(amount: number): string {
  return '$' + amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

export function initTheMoment() {
  const bankLine = document.getElementById('bank-line')
  
  let activated = false
  
  bankLine?.addEventListener('click', () => {
    if (activated) return
    activated = true
    
    gsap.to(bankLine, {
      duration: 0.5,
      scale: 1.05,
      borderColor: '#ff7a1a',
      onComplete: () => {
        initWorkflowSplit()
      }
    })
  })
}

export function initWorkflowSplit() {
  const cardsContainer = document.getElementById('split-cards')
  const tableContainer = document.getElementById('balance-table')
  
  if (!cardsContainer || !tableContainer) return
  
  cardsContainer.innerHTML = SPLITS.map(split => `
    <div class="split-card">
      <div class="split-account">${split.account}</div>
      <div class="split-name">${split.name}</div>
      <div style="font-size: 0.85rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${split.detail}</div>
      <div class="split-amount">${formatCurrency(split.amount)}</div>
    </div>
  `).join('')
  
  gsap.to(cardsContainer, {
    duration: 0.8,
    opacity: 1,
    y: 0,
    ease: 'power2.out',
    onComplete: () => {
      showBalanceTable()
    }
  })
  
  const cards = cardsContainer.querySelectorAll('.split-card')
  cards.forEach((card, i) => {
    gsap.from(card, {
      duration: 0.6,
      delay: i * 0.1,
      opacity: 0,
      y: 30,
      rotationX: -20,
      ease: 'back.out(1.7)'
    })
  })
  
  function showBalanceTable() {
    if (!tableContainer) return
    
    const total = SPLITS.reduce((sum, split) => sum + split.amount, 0)
    
    tableContainer.innerHTML = `
      <table>
        <thead>
          <tr>
            <th>Account</th>
            <th>Debit</th>
            <th>Credit</th>
          </tr>
        </thead>
        <tbody>
          ${SPLITS.map(split => `
            <tr>
              <td>${split.account} ${split.name}</td>
              <td>${formatCurrency(split.amount)}</td>
              <td>—</td>
            </tr>
          `).join('')}
          <tr>
            <td>1010 Cash - Chase</td>
            <td>—</td>
            <td>${formatCurrency(total)}</td>
          </tr>
          <tr class="total-row">
            <td>Net Amount</td>
            <td>${formatCurrency(total)}</td>
            <td>${formatCurrency(total)}</td>
          </tr>
        </tbody>
      </table>
      <div class="status-row">
        <strong>✓ Balanced · Awaiting Controller Approval</strong>
      </div>
    `
    
    gsap.to(tableContainer, {
      duration: 0.8,
      opacity: 1,
      y: 0,
      ease: 'power2.out'
    })
  }
}
