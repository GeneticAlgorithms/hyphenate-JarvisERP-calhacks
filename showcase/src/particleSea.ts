import * as THREE from 'three'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js'

// Simplified particle sea adapted from Alexander's animation
const SINGLES = ['0','1','2','3','4','5','6','7','8','9','$','.','-','+',',','?','✓','·','→']
const TOKENS = ['3,912.44','113.44','DR','CR','1310','6810','6410','1250','GL','AP','AR','JE','FX','EUR','P-0317','403','SHA-256']
const GLYPHS = [...SINGLES, ...TOKENS]

const ATLAS_COLS = 8
const ATLAS_ROWS = Math.ceil(GLYPHS.length / ATLAS_COLS)
const CELL_W = 512
const CELL_H = 128
const FONT_FRAC = 0.62

function mulberry32(a: number) {
  return function() {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    const t = Math.imul(a ^ (a >>> 15), 1 | a)
    const t2 = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t2 ^ (t2 >>> 14)) >>> 0) / 4294967296
  }
}

const rnd = mulberry32(20261025)

function buildAtlas() {
  const c = document.createElement('canvas')
  c.width = CELL_W * ATLAS_COLS
  c.height = CELL_H * ATLAS_ROWS
  const g = c.getContext('2d')!
  g.fillStyle = '#000'
  g.fillRect(0, 0, c.width, c.height)
  g.fillStyle = '#fff'
  g.textAlign = 'center'
  g.textBaseline = 'middle'
  
  GLYPHS.forEach((s, i) => {
    const col = i % ATLAS_COLS
    const row = Math.floor(i / ATLAS_COLS)
    let px = CELL_H * FONT_FRAC
    g.font = `600 ${px}px Fira Mono, monospace`
    const w = g.measureText(s).width
    if (w > CELL_W * 0.94) {
      px *= (CELL_W * 0.94) / w
      g.font = `600 ${px}px Fira Mono, monospace`
    }
    g.fillText(s, col * CELL_W + CELL_W / 2, row * CELL_H + CELL_H / 2)
  })
  
  const tex = new THREE.CanvasTexture(c)
  tex.generateMipmaps = true
  tex.minFilter = THREE.LinearMipmapLinearFilter
  tex.magFilter = THREE.LinearFilter
  return tex
}

export function initParticleSea() {
  const canvas = document.getElementById('particle-canvas') as HTMLCanvasElement
  if (!canvas) return

  const isMobile = window.innerWidth < 768
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(38, window.innerWidth / window.innerHeight, 0.1, 100)
  camera.position.set(0, 3.1, 11.2)
  camera.lookAt(0, 0.9, -2.2)

  const renderer = new THREE.WebGLRenderer({ 
    canvas, 
    alpha: true, 
    antialias: !isMobile,
    powerPreference: isMobile ? 'low-power' : 'high-performance'
  })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1 : 2))
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setClearColor(0x000000, 0)

  const composer = new EffectComposer(renderer)
  composer.setPixelRatio(renderer.getPixelRatio())
  composer.setSize(window.innerWidth, window.innerHeight)
  composer.addPass(new RenderPass(scene, camera))
  
  const bloom = new UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    isMobile ? 0.5 : 0.95,
    0.5,
    0.22
  )
  composer.addPass(bloom)
  composer.addPass(new OutputPass())

  // Build particle system
  const GX = isMobile ? 48 : 64
  const GZ = isMobile ? 64 : 96
  const SX = 0.42
  const SZ = 0.22
  const Z0 = 5.2
  const N = GX * GZ

  const atlas = buildAtlas()
  const grid = new Float32Array(N * 3)
  const seed = new Float32Array(N * 4)
  const info = new Float32Array(N * 2)

  for (let iz = 0; iz < GZ; iz++) {
    for (let ix = 0; ix < GX; ix++) {
      const i = iz * GX + ix
      grid[i * 3] = (ix - (GX - 1) / 2) * SX
      grid[i * 3 + 1] = 0
      grid[i * 3 + 2] = Z0 - iz * SZ
      seed.set([rnd(), rnd(), rnd(), rnd()], i * 4)
      const glyphIdx = Math.floor(rnd() * GLYPHS.length)
      info.set([glyphIdx, 0], i * 2)
    }
  }

  const quad = new THREE.PlaneGeometry(1, 1)
  const geo = new THREE.InstancedBufferGeometry()
  geo.index = quad.index
  geo.setAttribute('position', quad.attributes.position)
  geo.setAttribute('uv', quad.attributes.uv)
  geo.setAttribute('aGrid', new THREE.InstancedBufferAttribute(grid, 3))
  geo.setAttribute('aSeed', new THREE.InstancedBufferAttribute(seed, 4))
  geo.setAttribute('aInfo', new THREE.InstancedBufferAttribute(info, 2))
  geo.instanceCount = N
  geo.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 60)

  const mat = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    uniforms: {
      uTime: { value: 0 },
      uBlob: { value: 0 },
      uScroll: { value: 0 },
      uAtlas: { value: atlas },
      uCols: { value: ATLAS_COLS },
      uRows: { value: ATLAS_ROWS }
    },
    vertexShader: `
      uniform float uTime, uBlob, uScroll;
      uniform float uCols, uRows;
      in vec3 aGrid;
      in vec4 aSeed;
      in vec2 aInfo;
      out vec2 vUv;
      out vec3 vColor;
      out float vAlpha;
      
      float hash(float n) { return fract(sin(n) * 43758.5453123); }
      
      vec3 hsv2rgb(vec3 c) {
        vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
        vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
        return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
      }
      
      void main() {
        float t = uTime;
        vec3 g = aGrid;
        vec2 blobC = vec2(0.0, -2.6);
        vec2 d2 = g.xz - blobC;
        float d = length(d2);
        
        float h = sin(g.x * 0.16 + t * 0.34) * cos(g.z * 0.17 + t * 0.34) * 2.3;
        float R = 3.9;
        float b = exp(-d * d / (R * R));
        float dome = uBlob * b * (2.7 + sin(t + d) * 0.5);
        
        vec3 p = g + vec3(0.0, h + dome, 0.0) * (1.0 - uScroll * 0.8);
        
        vec3 camR = vec3(viewMatrix[0][0], viewMatrix[1][0], viewMatrix[2][0]);
        vec3 camU = vec3(viewMatrix[0][1], viewMatrix[1][1], viewMatrix[2][1]);
        
        float s = 0.16 * (0.7 + 0.65 * aSeed.w) * (1.0 + 0.12 * b * uBlob);
        vec3 world = p + position.x * 4.0 * s * camR + position.y * s * camU;
        
        float rate = 2.5 + aSeed.y * 8.0;
        float tick = floor(t * rate + aSeed.z * 17.0);
        float r1 = hash(aSeed.x * 91.7 + tick * 1.37);
        float glyphIdx = r1 < 0.7 ? floor(r1 / 0.7 * ${SINGLES.length}.0) : ${SINGLES.length}.0 + floor((r1 - 0.7) / 0.3 * ${TOKENS.length}.0);
        
        float colI = mod(glyphIdx, uCols);
        float rowI = floor(glyphIdx / uCols);
        vUv = vec2((colI + uv.x) / uCols, 1.0 - (rowI + 1.0 - uv.y) / uRows);
        
        float hn = clamp((h + dome * 0.7 + 0.5) / 2.4, 0.0, 1.0);
        float hue = mix(0.03, 0.09, hn);
        float sat = mix(0.8, 0.9, hn);
        float val = mix(0.4, 1.0, hn * hn);
        vColor = hsv2rgb(vec3(hue, sat, val));
        
        vec4 mv = viewMatrix * vec4(world, 1.0);
        float depth = -mv.z;
        float fog = (1.0 - smoothstep(13.0, 30.0, depth)) * smoothstep(0.8, 2.5, depth);
        vAlpha = fog * (1.0 - uScroll * 0.5);
        
        gl_Position = projectionMatrix * mv;
      }
    `,
    fragmentShader: `
      precision highp float;
      uniform sampler2D uAtlas;
      in vec2 vUv;
      in vec3 vColor;
      in float vAlpha;
      layout(location = 0) out vec4 fragColor;
      
      void main() {
        float a = texture(uAtlas, vUv).r;
        a = smoothstep(0.02, 0.9, a);
        if (a * vAlpha < 0.002) discard;
        fragColor = vec4(vColor * a * vAlpha, 1.0);
      }
    `
  })

  const particleSystem = new THREE.Mesh(geo, mat)
  particleSystem.frustumCulled = false
  scene.add(particleSystem)

  // Floating labels
  const labelsContainer = document.getElementById('hero-labels')
  const labels = [
    { text: 'PAYPAL *INST XFER −$3,912.44', x: 25, y: 15 },
    { text: '1310 · $3,451.50 · EUR crew deposit', x: 70, y: 25 },
    { text: '6810 · $147.50 · wire fees', x: 15, y: 55 },
    { text: '6410 · $200 · Claude API', x: 80, y: 60 },
    { text: '1250 · $113.44 · Steam · reimburse', x: 40, y: 75 }
  ]

  if (labelsContainer && !prefersReducedMotion) {
    labels.forEach((label, i) => {
      const div = document.createElement('div')
      div.className = 'hero-label'
      div.textContent = label.text
      div.style.left = `${label.x}%`
      div.style.top = `${label.y}%`
      div.style.animationDelay = `${i * 0.4}s`
      labelsContainer.appendChild(div)
    })
  }

  // Animation
  let time = 0
  let scrollProgress = 0
  let isAnimating = !prefersReducedMotion

  function animate() {
    requestAnimationFrame(animate)
    
    if (isAnimating) {
      time += prefersReducedMotion ? 0 : 0.016
    }

    const u = mat.uniforms
    u.uTime.value = time
    u.uBlob.value = 1.0 - scrollProgress * 0.6
    u.uScroll.value = scrollProgress

    composer.render()
  }

  animate()

  // Scroll interaction
  window.addEventListener('scroll', () => {
    const hero = document.getElementById('hero')
    if (hero) {
      const rect = hero.getBoundingClientRect()
      scrollProgress = Math.max(0, Math.min(1, 1 - (rect.bottom / window.innerHeight)))
    }
  })

  // Resize
  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(window.innerWidth, window.innerHeight)
    composer.setSize(window.innerWidth, window.innerHeight)
  })
}
