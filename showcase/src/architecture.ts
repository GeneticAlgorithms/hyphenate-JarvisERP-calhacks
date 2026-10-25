import * as THREE from 'three'

const LAYERS = [
  {
    name: 'Systems of Record',
    color: 0x6b1d2a,
    components: ['Chase Bank', 'PayPal', 'Ramp', 'External APIs']
  },
  {
    name: 'QBO ERP / GL',
    color: 0x8c2a3a,
    components: ['Chart of Accounts', 'General Ledger', 'Subledgers (AP/AR)', 'Trial Balance']
  },
  {
    name: 'JarvisERP System of Work',
    color: 0xff7a1a,
    components: ['Work Item State Machine', 'Evidence Lookup', 'Classification Engine', 'Challenge/Defend']
  },
  {
    name: 'Controls in Code',
    color: 0xffb066,
    components: ['Single Gateway', 'Role Authorization (403)', 'Approval Matrix', 'Hash-Chained Audit Log']
  },
  {
    name: 'People & Outputs',
    color: 0xff7a1a,
    components: ['Controller Approval', 'Posted Entries', 'Financial Package', 'Audit Trail']
  }
]

export function initArchitecture() {
  const container = document.getElementById('arch-canvas-container')
  const canvas = document.getElementById('arch-canvas') as HTMLCanvasElement
  if (!canvas || !container) return

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.1, 1000)
  camera.position.set(30, 25, 30)
  camera.lookAt(0, 0, 0)

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true })
  renderer.setSize(container.clientWidth, container.clientHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

  // Create layers
  const layerMeshes: THREE.Mesh[] = []
  const layerSpacing = 4

  LAYERS.forEach((layer, index) => {
    const geometry = new THREE.BoxGeometry(20, 0.5, 15)
    const material = new THREE.MeshPhongMaterial({
      color: layer.color,
      transparent: true,
      opacity: 0.7,
      emissive: layer.color,
      emissiveIntensity: 0.2
    })
    
    const mesh = new THREE.Mesh(geometry, material)
    mesh.position.y = index * layerSpacing - (LAYERS.length * layerSpacing) / 2
    mesh.userData = { layer: layer, index }
    layerMeshes.push(mesh)
    scene.add(mesh)

    const edges = new THREE.EdgesGeometry(geometry)
    const lineMaterial = new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.3 })
    const line = new THREE.LineSegments(edges, lineMaterial)
    mesh.add(line)
  })

  // Add lights
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
  scene.add(ambientLight)

  const pointLight = new THREE.PointLight(0xff7a1a, 1, 100)
  pointLight.position.set(10, 20, 10)
  scene.add(pointLight)

  // Create data packets
  const packets: THREE.Mesh[] = []
  const packetGeometry = new THREE.SphereGeometry(0.3, 8, 8)

  function createPacket(fromLayer: number, toLayer: number, color: number) {
    const material = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.8 })
    const packet = new THREE.Mesh(packetGeometry, material)
    packet.userData = { fromLayer, toLayer, progress: 0 }
    packets.push(packet)
    scene.add(packet)
  }

  // Initial packets
  createPacket(0, 1, 0xff7a1a)
  createPacket(1, 2, 0xff7a1a)
  createPacket(2, 3, 0xffb066)

  // 403 denial path (Jarvis trying to approve itself)
  const denialPacket = new THREE.Mesh(
    packetGeometry,
    new THREE.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.8 })
  )
  denialPacket.userData = { fromLayer: 2, toLayer: 3, progress: 0, isDenial: true }
  packets.push(denialPacket)
  scene.add(denialPacket)

  // Animation
  let time = 0
  let mouseX = 0

  function animate() {
    requestAnimationFrame(animate)
    time += 0.01

    // Rotate layers slightly
    layerMeshes.forEach((mesh, i) => {
      mesh.rotation.y = Math.sin(time + i) * 0.1 + mouseX * 0.001
      mesh.position.x = Math.sin(time * 0.5 + i) * 0.5
    })

    // Animate packets
    packets.forEach(packet => {
      packet.userData.progress += 0.005
      
      if (packet.userData.progress > 1) {
        packet.userData.progress = 0
        
        if (packet.userData.isDenial) {
          const fromMesh = layerMeshes[packet.userData.fromLayer]
          packet.position.copy(fromMesh.position)
          
          const flash = new THREE.PointLight(0xef4444, 2, 10)
          flash.position.copy(fromMesh.position)
          scene.add(flash)
          setTimeout(() => scene.remove(flash), 100)
        }
      }

      const fromMesh = layerMeshes[packet.userData.fromLayer]
      const toMesh = layerMeshes[packet.userData.toLayer]
      
      if (packet.userData.isDenial && packet.userData.progress > 0.5) {
        packet.position.copy(fromMesh.position)
      } else {
        packet.position.lerpVectors(
          fromMesh.position,
          toMesh.position,
          packet.userData.progress
        )
      }
    })

    renderer.render(scene, camera)
  }

  animate()

  // Mouse interaction
  const raycaster = new THREE.Raycaster()
  const mouse = new THREE.Vector2()
  const infoDiv = document.getElementById('arch-info')

  canvas.addEventListener('mousemove', (event) => {
    const rect = canvas.getBoundingClientRect()
    mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
    mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
    
    mouseX = mouse.x * 50

    raycaster.setFromCamera(mouse, camera)
    const intersects = raycaster.intersectObjects(layerMeshes)

    if (intersects.length > 0 && infoDiv) {
      const layer = intersects[0].object.userData.layer
      infoDiv.classList.add('visible')
      infoDiv.innerHTML = `
        <h3>${layer.name}</h3>
        <ul>
          ${layer.components.map((comp: string) => `<li>${comp}</li>`).join('')}
        </ul>
      `
    } else if (infoDiv) {
      infoDiv.classList.remove('visible')
    }
  })

  // Resize
  window.addEventListener('resize', () => {
    if (!container) return
    camera.aspect = container.clientWidth / container.clientHeight
    camera.updateProjectionMatrix()
    renderer.setSize(container.clientWidth, container.clientHeight)
  })
}
