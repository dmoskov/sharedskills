import { useRef, useMemo } from 'react'
import * as THREE from 'three'
import { useGLTF } from '@react-three/drei'

const HEAD_UNIT = 0.225 // 22.5cm

interface DetailedLegMeshProps {
  side: 'left' | 'right'
  visible?: boolean
  wireframe?: boolean
}

export default function DetailedLegMesh({ side, visible = true, wireframe = false }: DetailedLegMeshProps) {
  const meshRef = useRef<THREE.Group>(null)
  
  // Position offset based on side
  const xOffset = side === 'left' ? -0.1 : 0.1
  
  // Create custom geometry for detailed leg
  const legGeometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry()
    
    // Define vertices for a more anatomically correct leg
    // Using a simplified approach with key anatomical points
    const vertices = new Float32Array([
      // Hip region (top of femur)
      0, 0.9, 0,           // 0: Hip joint center
      0.05, 0.88, 0.03,    // 1: Greater trochanter
      -0.03, 0.88, 0.03,   // 2: Hip front
      -0.03, 0.88, -0.03,  // 3: Hip back
      0.03, 0.88, -0.03,   // 4: Hip side
      
      // Upper thigh (quadriceps bulge)
      0.06, 0.7, 0.05,     // 5: Quad peak front
      -0.04, 0.7, 0.04,    // 6: Vastus medialis
      -0.04, 0.7, -0.05,   // 7: Hamstring upper
      0.04, 0.7, -0.04,    // 8: Biceps femoris
      
      // Mid thigh
      0.05, 0.6, 0.04,     // 9
      -0.04, 0.6, 0.04,    // 10
      -0.04, 0.6, -0.04,   // 11
      0.04, 0.6, -0.04,    // 12
      
      // Lower thigh (taper to knee)
      0.04, 0.5, 0.03,     // 13
      -0.03, 0.5, 0.03,    // 14
      -0.03, 0.5, -0.03,   // 15
      0.03, 0.5, -0.03,    // 16
      
      // Knee region
      0, 0.45, 0.05,       // 17: Patella center
      0.035, 0.45, 0.02,   // 18: Lateral condyle
      -0.035, 0.45, 0.02,  // 19: Medial condyle
      0, 0.45, -0.03,      // 20: Popliteal fossa
      
      // Upper calf (gastrocnemius bulge)
      0.03, 0.35, -0.04,   // 21: Lateral head
      -0.03, 0.35, -0.04,  // 22: Medial head
      0.04, 0.35, 0.02,    // 23: Tibialis anterior
      -0.04, 0.35, 0.02,   // 24: Shin medial
      
      // Mid calf
      0.03, 0.25, -0.03,   // 25
      -0.03, 0.25, -0.03,  // 26
      0.03, 0.25, 0.02,    // 27
      -0.03, 0.25, 0.02,   // 28
      
      // Lower calf (taper)
      0.02, 0.15, -0.02,   // 29
      -0.02, 0.15, -0.02,  // 30
      0.02, 0.15, 0.015,   // 31
      -0.02, 0.15, 0.015,  // 32
      
      // Ankle
      0.02, 0.06, 0,       // 33: Lateral malleolus
      -0.025, 0.05, 0,     // 34: Medial malleolus
      0, 0.055, 0.015,     // 35: Anterior ankle
      0, 0.055, -0.015,    // 36: Achilles insertion
    ])
    
    // Define faces (indices)
    const indices = new Uint16Array([
      // Hip to upper thigh
      0, 1, 5,  0, 5, 6,  0, 6, 2,
      0, 2, 6,  0, 6, 7,  0, 7, 3,
      0, 3, 7,  0, 7, 8,  0, 8, 4,
      0, 4, 8,  0, 8, 5,  0, 5, 1,
      
      // Upper thigh ring
      5, 9, 10, 5, 10, 6,
      6, 10, 11, 6, 11, 7,
      7, 11, 12, 7, 12, 8,
      8, 12, 9, 8, 9, 5,
      
      // Mid thigh ring
      9, 13, 14, 9, 14, 10,
      10, 14, 15, 10, 15, 11,
      11, 15, 16, 11, 16, 12,
      12, 16, 13, 12, 13, 9,
      
      // Lower thigh to knee
      13, 17, 19, 13, 19, 14,
      14, 19, 20, 14, 20, 15,
      15, 20, 18, 15, 18, 16,
      16, 18, 17, 16, 17, 13,
      
      // Knee cap (patella)
      17, 18, 19,
      18, 20, 19,
      
      // Knee to upper calf
      18, 21, 23, 19, 22, 24,
      20, 21, 22,
      
      // Upper calf ring
      21, 25, 27, 21, 27, 23,
      22, 26, 28, 22, 28, 24,
      23, 27, 28, 23, 28, 24,
      21, 25, 26, 21, 26, 22,
      
      // Mid calf ring
      25, 29, 31, 25, 31, 27,
      26, 30, 32, 26, 32, 28,
      27, 31, 32, 27, 32, 28,
      25, 29, 30, 25, 30, 26,
      
      // Lower calf to ankle
      29, 33, 35, 29, 35, 31,
      30, 34, 36, 30, 36, 32,
      31, 35, 34, 31, 34, 32,
      29, 33, 36, 29, 36, 30,
      
      // Ankle closure
      33, 35, 34,
      33, 34, 36,
    ])
    
    // Set attributes
    geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3))
    geometry.setIndex(new THREE.BufferAttribute(indices, 1))
    geometry.computeVertexNormals()
    
    return geometry
  }, [])
  
  return (
    <group ref={meshRef} position={[xOffset, 0, 0]} visible={visible}>
      {/* Main leg mesh */}
      <mesh geometry={legGeometry} castShadow receiveShadow>
        <meshStandardMaterial 
          color="#fdbcb4"
          roughness={0.7}
          metalness={0.1}
          wireframe={wireframe}
        />
      </mesh>
      
      {/* Additional detail meshes */}
      
      {/* Patella (kneecap) detail */}
      <mesh position={[0, 0.45, 0.05]} scale={[1.2, 1, 0.8]}>
        <sphereGeometry args={[0.025, 8, 6]} />
        <meshStandardMaterial 
          color="#f5c9b6"
          roughness={0.6}
        />
      </mesh>
      
      {/* Medial malleolus (inner ankle bone) */}
      <mesh position={[-0.025, 0.05, 0]}>
        <sphereGeometry args={[0.015, 6, 6]} />
        <meshStandardMaterial 
          color="#f5c9b6"
          roughness={0.8}
        />
      </mesh>
      
      {/* Lateral malleolus (outer ankle bone) */}
      <mesh position={[0.02, 0.06, 0]}>
        <sphereGeometry args={[0.012, 6, 6]} />
        <meshStandardMaterial 
          color="#f5c9b6"
          roughness={0.8}
        />
      </mesh>
      
      {/* Muscle definition overlays */}
      {/* Vastus lateralis bulge */}
      <mesh position={[0.05, 0.65, 0.03]} scale={[0.8, 1.5, 0.8]}>
        <sphereGeometry args={[0.03, 8, 6]} />
        <meshStandardMaterial 
          color="#fdbcb4"
          roughness={0.7}
          transparent
          opacity={0.5}
        />
      </mesh>
      
      {/* Gastrocnemius bulge */}
      <mesh position={[0, 0.32, -0.03]} scale={[1.2, 1.3, 1]}>
        <sphereGeometry args={[0.035, 8, 6]} />
        <meshStandardMaterial 
          color="#fdbcb4"
          roughness={0.7}
          transparent
          opacity={0.5}
        />
      </mesh>
      
      {/* Tibialis anterior ridge */}
      <mesh position={[0.03, 0.25, 0.02]} scale={[0.3, 2, 0.5]}>
        <boxGeometry args={[0.02, 0.15, 0.01]} />
        <meshStandardMaterial 
          color="#fdbcb4"
          roughness={0.7}
          transparent
          opacity={0.3}
        />
      </mesh>
    </group>
  )
}