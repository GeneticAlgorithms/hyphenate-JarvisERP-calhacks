import './style-simple.css'
import { initEngine } from './engine'
import { initGlossary } from './glossary'
import { initTheMoment } from './theMoment'

function init() {
  initTheMoment()
  initEngine()
  initGlossary()
  initUI()
  initDemoAnimation()
  initVideoHero()
  initWorkflowSplit()
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

function initVideoHero() {
  const video = document.getElementById('hero-video') as HTMLVideoElement
  const splitCard = document.getElementById('hero-split-card')
  const hero = document.getElementById('hero')
  
  if (!video) return

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  
  // Show split card immediately under reduced motion
  if (prefersReducedMotion && splitCard) {
    splitCard.classList.add('visible')
    video.pause()
    video.style.display = 'none'
    return
  }

  // Multiple triggers to ensure split card appears
  let cardShown = false
  
  const showSplitCard = () => {
    if (!cardShown && splitCard) {
      splitCard.classList.add('visible')
      cardShown = true
    }
  }

  // Trigger 1: video 'ended' event
  video.addEventListener('ended', showSplitCard)

  // Trigger 2: timeupdate near end (at 9s for 10s video)
  video.addEventListener('timeupdate', () => {
    if (video.currentTime >= 9 && !cardShown) {
      showSplitCard()
    }
  })

  // Trigger 3: 9s fallback timeout
  setTimeout(showSplitCard, 9000)

  // Pause when offscreen
  if (hero && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          video.play().catch(() => {})
        } else {
          video.pause()
        }
      })
    })
    observer.observe(hero)
  }
}

function initWorkflowSplit() {
  // Render split cards in the workflow tab immediately
  const splitCards = document.getElementById('split-cards')
  const balanceTable = document.getElementById('balance-table')
  
  if (!splitCards || !balanceTable) return

  const splits = [
    { account: '1310', name: 'Prepaid Tour Costs', detail: 'EUR crew deposit', amount: 3451.50 },
    { account: '6810', name: 'Bank & FX Fees', detail: 'Transfer fees', amount: 147.50 },
    { account: '6410', name: 'Software', detail: 'Claude API', amount: 200.00 },
    { account: '1250', name: 'Employee Receivable', detail: 'Maya - Steam', amount: 113.44 }
  ]

  function formatCurrency(amount: number): string {
    return '$' + amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  }

  // Render split cards
  splitCards.innerHTML = splits.map(split => `
    <div class="split-card">
      <div class="split-account">${split.account}</div>
      <div class="split-name">${split.name}</div>
      <div style="font-size: 0.875rem; color: var(--color-gray-600); margin-bottom: 0.5rem;">${split.detail}</div>
      <div class="split-amount">${formatCurrency(split.amount)}</div>
    </div>
  `).join('')
  
  splitCards.style.opacity = '1'

  // Render balance table
  const total = splits.reduce((sum, split) => sum + split.amount, 0)
  
  balanceTable.innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Account</th>
          <th>Debit</th>
          <th>Credit</th>
        </tr>
      </thead>
      <tbody>
        ${splits.map(split => `
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
  
  balanceTable.style.opacity = '1'
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init)
} else {
  init()
}
