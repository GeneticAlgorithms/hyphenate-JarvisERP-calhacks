import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

export function initAnimations() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  
  if (prefersReducedMotion) {
    return
  }
  
  gsap.from('#the-moment .moment-container', {
    scrollTrigger: {
      trigger: '#the-moment',
      start: 'top center',
      toggleActions: 'play none none none'
    },
    opacity: 0,
    y: 50,
    duration: 1
  })
  
  gsap.from('.problem-card', {
    scrollTrigger: {
      trigger: '#five-problems',
      start: 'top center'
    },
    opacity: 0,
    y: 30,
    stagger: 0.15,
    duration: 0.8
  })
  
  gsap.from('.comparison-col', {
    scrollTrigger: {
      trigger: '#real-vs-simulated',
      start: 'top center'
    },
    opacity: 0,
    x: (i) => i === 0 ? -50 : 50,
    stagger: 0.2,
    duration: 0.8
  })
  
  gsap.from('.engine-panel', {
    scrollTrigger: {
      trigger: '#live-engine',
      start: 'top center'
    },
    opacity: 0,
    scale: 0.95,
    stagger: 0.1,
    duration: 0.6
  })
}
