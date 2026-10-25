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
      start: 'top 80%',
      toggleActions: 'play none none none'
    },
    opacity: 0,
    y: 30,
    duration: 0.6
  })
  
  gsap.from('.problem-card', {
    scrollTrigger: {
      trigger: '#five-problems',
      start: 'top 75%'
    },
    opacity: 0,
    y: 20,
    stagger: 0.1,
    duration: 0.5
  })
  
  gsap.from('.comparison-col', {
    scrollTrigger: {
      trigger: '#real-vs-simulated',
      start: 'top 75%'
    },
    opacity: 0,
    x: (i) => i === 0 ? -30 : 30,
    stagger: 0.15,
    duration: 0.6
  })
  
  gsap.from('.engine-panel', {
    scrollTrigger: {
      trigger: '#live-engine',
      start: 'top 75%'
    },
    opacity: 0,
    scale: 0.97,
    stagger: 0.08,
    duration: 0.5
  })
}
