import './style-simple.css'
import { initParticleSea } from './particleSea'
import { initEngine } from './engine'
import { initGlossary } from './glossary'
import { initTheMoment } from './theMoment'

function init() {
  // Check WebGL support
  const canvas = document.createElement('canvas')
  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
  
  if (gl) {
    try {
      initParticleSea()
    } catch (error) {
      console.warn('WebGL initialization failed, using fallback', error)
    }
  }
  
  initTheMoment()
  initEngine()
  initGlossary()
  initUI()
  initDemoAnimation()
}

function initUI() {
  // Workflow tabs
  const workflowTabs = document.querySelectorAll('.workflow-tab')
  const workflowContents = document.querySelectorAll('.workflow-content')
  
  workflowTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetTab = tab.getAttribute('data-tab')
      
      workflowTabs.forEach(t => t.classList.remove('active'))
      tab.classList.add('active')
      
      workflowContents.forEach(content => {
        content.classList.remove('active')
        if (content.getAttribute('data-content') === targetTab) {
          content.classList.add('active')
        }
      })
    })
  })

  // FAQ Accordion
  const faqItems = document.querySelectorAll('.faq-item')
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-q')
    question?.addEventListener('click', () => {
      const isActive = item.classList.contains('active')
      
      faqItems.forEach(i => i.classList.remove('active'))
      
      if (!isActive) {
        item.classList.add('active')
      }
    })
  })

  // Smooth scroll
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      e.preventDefault()
      const target = document.querySelector(anchor.getAttribute('href') || '')
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    })
  })
}

function initDemoAnimation() {
  // Simple CSS/GSAP demo animation for the product mock
  const splits = [
    { account: '1310', name: 'Prepaid Tour Costs', detail: 'EUR crew deposit', amount: 3451.50 },
    { account: '6810', name: 'Bank & FX Fees', detail: 'Transfer fees', amount: 147.50 },
    { account: '6410', name: 'Software', detail: 'Claude API', amount: 200.00 },
    { account: '1250', name: 'Employee Receivable', detail: 'Maya - Steam', amount: 113.44 }
  ]

  function formatCurrency(amount: number): string {
    return '$' + amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  }

  const splitsContainer = document.getElementById('demo-splits')
  const tableContainer = document.getElementById('demo-table')
  
  if (!splitsContainer || !tableContainer) return

  // Simple reveal animation after a delay
  setTimeout(() => {
    splitsContainer.innerHTML = splits.map(split => `
      <div style="padding: 1rem; background: var(--color-gray-50); border: 1px solid var(--color-gray-200); border-radius: 8px;">
        <div style="font-size: 0.75rem; color: var(--color-gray-600); margin-bottom: 0.25rem;">${split.account}</div>
        <div style="font-weight: 600; margin-bottom: 0.25rem;">${split.name}</div>
        <div style="font-size: 0.875rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${split.detail}</div>
        <div style="font-size: 1.125rem; font-weight: 700; color: var(--color-orange);">${formatCurrency(split.amount)}</div>
      </div>
    `).join('')
    
    splitsContainer.style.opacity = '1'
    splitsContainer.style.transition = 'opacity 0.6s ease'
  }, 1000)

  setTimeout(() => {
    const total = splits.reduce((sum, split) => sum + split.amount, 0)
    
    tableContainer.innerHTML = `
      <table style="width: 100%; border-collapse: collapse;">
        <thead>
          <tr>
            <th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--color-gray-200);">Account</th>
            <th style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">Debit</th>
            <th style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">Credit</th>
          </tr>
        </thead>
        <tbody>
          ${splits.map(split => `
            <tr>
              <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-gray-200);">${split.account} ${split.name}</td>
              <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">${formatCurrency(split.amount)}</td>
              <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">—</td>
            </tr>
          `).join('')}
          <tr>
            <td style="padding: 0.75rem; border-bottom: 1px solid var(--color-gray-200);">1010 Cash - Chase</td>
            <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">—</td>
            <td style="padding: 0.75rem; text-align: right; border-bottom: 1px solid var(--color-gray-200);">${formatCurrency(total)}</td>
          </tr>
          <tr style="font-weight: 700;">
            <td style="padding: 0.75rem; border-top: 2px solid var(--color-black);">Net Amount</td>
            <td style="padding: 0.75rem; text-align: right; border-top: 2px solid var(--color-black);">${formatCurrency(total)}</td>
            <td style="padding: 0.75rem; text-align: right; border-top: 2px solid var(--color-black);">${formatCurrency(total)}</td>
          </tr>
        </tbody>
      </table>
      <div style="margin-top: 1rem; text-align: center; color: var(--color-orange); font-weight: 600;">
        ✓ Balanced · Awaiting Controller Approval
      </div>
    `
    
    tableContainer.style.opacity = '1'
    tableContainer.style.transition = 'opacity 0.6s ease'
  }, 2000)
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init)
} else {
  init()
}
