import './style-new.css'
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
      showWebGLFallback()
    }
  } else {
    showWebGLFallback()
  }
  
  initTheMoment()
  initEngine()
  initGlossary()
  initUI()
}

function initUI() {
  // Tab switching
  const tabButtons = document.querySelectorAll('.tab-button')
  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const tabName = button.getAttribute('data-tab')
      
      // Update buttons
      tabButtons.forEach(btn => btn.classList.remove('active'))
      button.classList.add('active')
      
      // Update content
      document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active')
      })
      const targetContent = document.querySelector(`[data-tab-content="${tabName}"]`)
      if (targetContent) {
        targetContent.classList.add('active')
      }
    })
  })

  // FAQ Accordion
  const faqItems = document.querySelectorAll('.faq-item')
  faqItems.forEach(item => {
    const question = item.querySelector('.faq-question')
    question?.addEventListener('click', () => {
      const isActive = item.classList.contains('active')
      
      // Close all
      faqItems.forEach(i => i.classList.remove('active'))
      
      // Open clicked if it wasn't active
      if (!isActive) {
        item.classList.add('active')
      }
    })
  })

  // Trust layer interaction
  const layers = document.querySelectorAll('.glass-layer')
  const details = document.querySelectorAll('.trust-detail')
  
  layers.forEach((layer, index) => {
    layer.addEventListener('click', () => {
      // Update layers
      layers.forEach(l => l.classList.remove('active'))
      layer.classList.add('active')
      
      // Update details
      details.forEach(d => d.classList.remove('active'))
      const targetDetail = document.querySelector(`[data-detail="${index + 1}"]`)
      if (targetDetail) {
        targetDetail.classList.add('active')
      }
    })
  })

  // Activate first layer by default
  if (layers.length > 0 && details.length > 0) {
    layers[0].classList.add('active')
    details[0].classList.add('active')
  }

  // Mobile menu toggle
  const menuToggle = document.querySelector('.mobile-menu-toggle')
  const navLinks = document.querySelector('.nav-links')
  
  menuToggle?.addEventListener('click', () => {
    navLinks?.classList.toggle('active')
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

function showWebGLFallback() {
  const heroCanvas = document.getElementById('particle-canvas') as HTMLCanvasElement
  if (heroCanvas) {
    heroCanvas.style.display = 'none'
    const hero = document.getElementById('hero')
    if (hero) {
      hero.style.background = 'linear-gradient(135deg, #6b1d2a 0%, #0a0a0a 50%, #ff7a1a 100%)'
    }
  }
  
  const archCanvas = document.getElementById('arch-canvas') as HTMLCanvasElement
  if (archCanvas) {
    const ctx = archCanvas.getContext('2d')
    if (ctx) {
      archCanvas.width = archCanvas.clientWidth
      archCanvas.height = archCanvas.clientHeight
      ctx.fillStyle = '#141414'
      ctx.fillRect(0, 0, archCanvas.width, archCanvas.height)
      ctx.fillStyle = '#ff7a1a'
      ctx.font = '16px Fira Mono'
      ctx.textAlign = 'center'
      ctx.fillText('WebGL unavailable - 3D visualization disabled', archCanvas.width / 2, archCanvas.height / 2)
    }
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init)
} else {
  init()
}
