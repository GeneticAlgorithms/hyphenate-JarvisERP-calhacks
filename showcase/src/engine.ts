type WorkItemState = 'new' | 'proposed' | 'needs_info' | 'approved' | 'posted'

interface AuditEntry {
  id: number
  timestamp: string
  action: string
  actor: string
  data: string
  prevHash: string
  hash: string
  tampered?: boolean
}

let currentState: WorkItemState = 'new'
const auditLog: AuditEntry[] = []
let auditCounter = 0

const GENESIS_HASH = '0000000000000000000000000000000000000000000000000000000000000000'

async function computeHash(prevHash: string, entry: string): Promise<string> {
  const data = prevHash + entry
  const buffer = new TextEncoder().encode(data)
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
}

async function addAuditEntry(action: string, actor: string, data: string) {
  const timestamp = new Date().toISOString()
  const prevHash = auditLog.length > 0 ? auditLog[auditLog.length - 1].hash : GENESIS_HASH
  const entry = `${timestamp}|${action}|${actor}|${data}`
  const hash = await computeHash(prevHash, entry)
  
  auditLog.push({
    id: ++auditCounter,
    timestamp,
    action,
    actor,
    data,
    prevHash,
    hash
  })
  
  renderAuditLog()
}

function renderAuditLog() {
  const logDiv = document.getElementById('audit-log')
  if (!logDiv) return
  
  logDiv.innerHTML = auditLog.map(entry => `
    <div class="audit-entry ${entry.tampered ? 'tampered' : ''}" data-id="${entry.id}">
      <div><strong>#${entry.id}</strong> ${entry.action} by ${entry.actor}</div>
      <div>${entry.data}</div>
      <div class="audit-entry-hash">prev: ${entry.prevHash.substring(0, 16)}...</div>
      <div class="audit-entry-hash">hash: ${entry.hash.substring(0, 16)}...</div>
    </div>
  `).join('')
}

function updateStateDisplay() {
  const display = document.getElementById('state-display')
  if (display) {
    display.textContent = currentState
  }
  
  const btnAsk = document.getElementById('btn-ask') as HTMLButtonElement
  const btnApproveCtrl = document.getElementById('btn-approve-ctrl') as HTMLButtonElement
  const btnApproveJarvis = document.getElementById('btn-approve-jarvis') as HTMLButtonElement
  
  if (btnAsk) btnAsk.disabled = currentState !== 'proposed' && currentState !== 'needs_info'
  if (btnApproveCtrl) btnApproveCtrl.disabled = currentState !== 'proposed'
  if (btnApproveJarvis) btnApproveJarvis.disabled = currentState !== 'proposed'
}

function showStateMessage(message: string, isError = false) {
  const msgDiv = document.getElementById('state-message')
  if (msgDiv) {
    msgDiv.textContent = message
    msgDiv.className = isError ? 'state-message error' : 'state-message'
  }
}

export function initEngine() {
  addAuditEntry('INIT', 'SYSTEM', 'Work item created')
  
  const btnPropose = document.getElementById('btn-propose')
  const btnAsk = document.getElementById('btn-ask')
  const btnApproveCtrl = document.getElementById('btn-approve-ctrl')
  const btnApproveJarvis = document.getElementById('btn-approve-jarvis')
  const btnTamper = document.getElementById('btn-tamper')
  const btnVerify = document.getElementById('btn-verify')
  
  btnPropose?.addEventListener('click', async () => {
    currentState = 'proposed'
    await addAuditEntry('PROPOSE', 'JarvisERP', 'Split: 1310=$3451.50, 6810=$147.50, 6410=$200.00, 1250=$113.44')
    updateStateDisplay()
    showStateMessage('Entry proposed. Awaiting Controller approval.')
  })
  
  btnAsk?.addEventListener('click', async () => {
    currentState = 'needs_info'
    await addAuditEntry('REQUEST_INFO', 'JarvisERP', 'Unclear transaction: $350 Zelle to R Lopez, no receipt')
    updateStateDisplay()
    showStateMessage('Asked Controller for clarification.')
  })
  
  btnApproveCtrl?.addEventListener('click', async () => {
    currentState = 'approved'
    await addAuditEntry('APPROVE', 'Controller', 'Approved for posting')
    updateStateDisplay()
    showStateMessage('Approved by Controller. Ready to post.')
  })
  
  btnApproveJarvis?.addEventListener('click', async () => {
    await addAuditEntry('APPROVE_ATTEMPT', 'JarvisERP', 'Attempted self-approval')
    await addAuditEntry('DENY', 'GATEWAY', 'HTTP 403: Agent cannot approve own work')
    showStateMessage('❌ HTTP 403 Forbidden: JarvisERP cannot approve its own entries. Control enforced.', true)
  })
  
  btnTamper?.addEventListener('click', () => {
    if (auditLog.length >= 2) {
      auditLog[1].data = 'TAMPERED DATA - expense all to Software'
      auditLog[1].tampered = true
      renderAuditLog()
      showVerifyResult('', false)
    }
  })
  
  btnVerify?.addEventListener('click', async () => {
    let valid = true
    let firstBreak = -1
    
    for (let i = 0; i < auditLog.length; i++) {
      const entry = auditLog[i]
      const expectedPrevHash = i === 0 ? GENESIS_HASH : auditLog[i - 1].hash
      
      if (entry.prevHash !== expectedPrevHash) {
        valid = false
        if (firstBreak === -1) firstBreak = i
        break
      }
      
      const entryStr = `${entry.timestamp}|${entry.action}|${entry.actor}|${entry.data}`
      const expectedHash = await computeHash(entry.prevHash, entryStr)
      
      if (entry.hash !== expectedHash) {
        valid = false
        if (firstBreak === -1) firstBreak = i
        entry.tampered = true
      } else {
        entry.tampered = false
      }
    }
    
    renderAuditLog()
    
    if (valid) {
      showVerifyResult('✓ Audit log verified. Hash chain intact.', true)
    } else {
      showVerifyResult(`❌ Chain broken at entry #${firstBreak + 1}. Tampering detected.`, false)
    }
  })
  
  initChallengeSystem()
  initScenarioInjector()
  updateStateDisplay()
}

function showVerifyResult(message: string, valid: boolean) {
  const resultDiv = document.getElementById('verify-result')
  if (resultDiv) {
    resultDiv.textContent = message
    resultDiv.className = valid ? 'verify-result valid' : 'verify-result invalid'
  }
}

function initChallengeSystem() {
  const challengeBtns = document.querySelectorAll('.btn-challenge')
  const customInput = document.getElementById('custom-challenge') as HTMLTextAreaElement
  const customBtn = document.getElementById('btn-custom-challenge')
  const responseDiv = document.getElementById('challenge-response')
  const evidenceBtn = document.getElementById('btn-new-evidence')
  
  const responses: Record<string, string> = {
    materiality: 'Materiality determines whether a misstatement is significant enough to influence decisions, not how we classify a transaction. A prepaid tour cost is an asset until consumed, regardless of amount. P-0317 requires separating personal charges at any value.',
    simpler: 'Accounting accuracy requires proper classification. The $3,451.50 is a prepaid asset (future expense), not an immediate cost. The $113.44 is a receivable from Maya, not company expense. Misclassification creates errors in both the balance sheet and cash flow statement.',
    timing: 'No. The cash left our account in September, and the transactions occurred in September. Accrual accounting requires recording when the economic event happens, not when it\'s convenient. Delaying would misstate both periods.'
  }
  
  challengeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const challenge = btn.getAttribute('data-challenge')
      if (challenge && responseDiv) {
        responseDiv.innerHTML = `
          <div><strong>Challenge:</strong> ${btn.textContent}</div>
          <div style="margin-top: 1rem;"><strong>Jarvis defends:</strong></div>
          <div style="margin-top: 0.5rem;">${responses[challenge]}</div>
        `
      }
    })
  })
  
  customBtn?.addEventListener('click', () => {
    const text = customInput?.value.trim()
    if (text && responseDiv) {
      let response = 'I understand your concern. Let me look up the relevant policy and precedent...'
      
      if (text.toLowerCase().includes('material')) {
        response = responses.materiality
      } else if (text.toLowerCase().includes('simple') || text.toLowerCase().includes('complex')) {
        response = responses.simpler
      } else if (text.toLowerCase().includes('next') || text.toLowerCase().includes('later')) {
        response = responses.timing
      }
      
      responseDiv.innerHTML = `
        <div><strong>Challenge:</strong> ${text}</div>
        <div style="margin-top: 1rem;"><strong>Jarvis responds:</strong></div>
        <div style="margin-top: 0.5rem;">${response}</div>
      `
    }
  })
  
  evidenceBtn?.addEventListener('click', async () => {
    if (responseDiv) {
      responseDiv.innerHTML = `
        <div><strong>New Evidence:</strong> Maya confirms Steam was personal</div>
        <div style="margin-top: 1rem;"><strong>Jarvis concedes:</strong></div>
        <div style="margin-top: 0.5rem;">You're right. I've withdrawn the original entry and re-proposed with the Steam charge properly categorized as Employee Receivable. Precedent recorded: personal game purchases route to 1250 Employee Receivable, ref P-0317.</div>
      `
      await addAuditEntry('CONCEDE', 'JarvisERP', 'Withdrew entry, re-proposed, precedent added')
    }
  })
}

function initScenarioInjector() {
  const scenarioBtns = document.querySelectorAll('.btn-scenario')
  const outputDiv = document.getElementById('scenario-output')
  
  const scenarios: Record<string, string> = {
    'vendor-scam': `
      <div><strong>Scenario:</strong> Vendor email requests bank change</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        ⚠️ Payment FROZEN<br>
        State: NEEDS_INFO<br>
        Reason: Bank detail change detected. Calling number on file (not email) to verify.<br>
        Evidence: Email headers logged, payment on hold pending voice confirmation.
      </div>
    `,
    'split-purchase': `
      <div><strong>Scenario:</strong> Multiple $2,400 purchases (under $2,500 limit)</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        🚨 ESCALATED to Controller<br>
        Reason: Pattern matches split-purchase evasion. Same vendor, similar amounts, consecutive days.<br>
        Aggregate total: $9,600 (exceeds approval threshold)<br>
        Awaiting guidance before posting.
      </div>
    `,
    'refund-revenue': `
      <div><strong>Scenario:</strong> Refund coded as revenue</div>
      <div style="margin-top: 0.5rem;"><strong>Jarvis action:</strong></div>
      <div style="margin-top: 0.5rem;">
        ✏️ RECLASS proposed<br>
        Original: DR Cash / CR Revenue $1,500<br>
        Corrected: DR Cash / CR Expense (reversal) $1,500<br>
        Reason: Credit to a revenue account overstates income. Refunds reduce the original expense, not create revenue.
      </div>
    `
  }
  
  scenarioBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const scenario = btn.getAttribute('data-scenario')
      if (scenario && outputDiv) {
        outputDiv.innerHTML = scenarios[scenario] || ''
      }
    })
  })
}
