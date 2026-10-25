import './style.css'
import { initParticleSea } from './particleSea'
import { initArchitecture } from './architecture'
import { initEngine } from './engine'
import { initGlossary } from './glossary'
import { initAnimations } from './animations'
import { initTheMoment } from './theMoment'

function init() {
  // Check WebGL support
  const canvas = document.createElement('canvas')
  const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl')
  
  if (gl) {
    try {
      initParticleSea()
      initArchitecture()
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
  initAnimations()
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
