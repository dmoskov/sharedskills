import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface FigureModelProps {
  transparent?: boolean
  opacity?: number
}

export default function FigureModel({ transparent = false, opacity = 1 }: FigureModelProps) {
  const meshRef = useRef<THREE.Group>(null)
  
  // Basic humanoid figure placeholder
  // In production, this would load a proper 3D model
  
  return (
    <group ref={meshRef} position={[0, 0, 0]}>
      {/* Head */}
      <mesh position={[0, 1.7, 0]} castShadow>
        <sphereGeometry args={[0.12, 32, 32]} />
        <meshStandardMaterial 
          color="#fdbcb4" 
          roughness={0.7}
          transparent={transparent}
          opacity={opacity}
        />
      </mesh>
      
      {/* Torso */}
      <mesh position={[0, 1.2, 0]} castShadow>
        <boxGeometry args={[0.35, 0.6, 0.2]} />
        <meshStandardMaterial 
          color="#fdbcb4" 
          roughness={0.7}
          transparent={transparent}
          opacity={opacity}
        />
      </mesh>
      
      {/* Pelvis */}
      <mesh position={[0, 0.85, 0]} castShadow>
        <boxGeometry args={[0.3, 0.2, 0.18]} />
        <meshStandardMaterial 
          color="#fdbcb4" 
          roughness={0.7}
          transparent={transparent}
          opacity={opacity}
        />
      </mesh>
      
      {/* Left Leg - Upper */}
      <mesh position={[-0.1, 0.5, 0]} castShadow>
        <cylinderGeometry args={[0.06, 0.05, 0.5, 16]} />
        <meshStandardMaterial 
          color="#fdbcb4" 
          roughness={0.7}
          transparent={transparent}
          opacity={opacity}
        />
      </mesh>
      
      {/* Left Leg - Lower */}
      <mesh position={[-0.1, 0.125, 0]} castShadow>
        <cylinderGeometry args={[0.05, 0.04, 0.4, 16]} />
        <meshStandardMaterial 
          color="#fdbcb4" 
          roughness={0.7}
          transparent={transparent}
          opacity={opacity}
        />
      </mesh>
      
      {/* Right Leg - Upper */}
      <mesh position={[0.1, 0.5, 0]} castShadow>
        <cylinderGeometry args={[0.06, 0.05, 0.5, 16]} />
        <meshStandardMaterial 
          color="#fdbcb4" 
          roughness={0.7}
          transparent={transparent}
          opacity={opacity}
        />
      </mesh>
      
      {/* Right Leg - Lower */}
      <mesh position={[0.1, 0.125, 0]} castShadow>
        <cylinderGeometry args={[0.05, 0.04, 0.4, 16]} />
        <meshStandardMaterial 
          color="#fdbcb4" 
          roughness={0.7}
          transparent={transparent}
          opacity={opacity}
        />
      </mesh>
      
      {/* Arms */}
      <mesh position={[-0.25, 1.3, 0]} rotation={[0, 0, -0.5]} castShadow>
        <cylinderGeometry args={[0.04, 0.03, 0.5, 16]} />
        <meshStandardMaterial 
          color="#fdbcb4" 
          roughness={0.7}
          transparent={transparent}
          opacity={opacity}
        />
      </mesh>
      
      <mesh position={[0.25, 1.3, 0]} rotation={[0, 0, 0.5]} castShadow>
        <cylinderGeometry args={[0.04, 0.03, 0.5, 16]} />
        <meshStandardMaterial 
          color="#fdbcb4" 
          roughness={0.7}
          transparent={transparent}
          opacity={opacity}
        />
      </mesh>
    </group>
  )
}