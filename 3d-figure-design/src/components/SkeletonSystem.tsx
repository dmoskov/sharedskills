import { useRef } from 'react'
import * as THREE from 'three'
import { Line } from '@react-three/drei'
import { useStore } from '../store/useStore'

export default function SkeletonSystem() {
  const groupRef = useRef<THREE.Group>(null)
  const { highlightedBone } = useStore()
  
  const getBoneColor = (boneId: string) => {
    return highlightedBone === boneId ? '#3b82f6' : '#e9ecef'
  }
  
  // Simplified skeletal structure
  // In production, this would be an anatomically accurate bone system
  
  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* Pelvis */}
      <mesh position={[0, 0.85, 0]}>
        <boxGeometry args={[0.25, 0.08, 0.15]} />
        <meshStandardMaterial 
          color={getBoneColor('pelvis')}
          roughness={0.9}
          metalness={0.1}
        />
      </mesh>
      
      {/* Femur - Left */}
      <group>
        <mesh position={[-0.1, 0.5, 0]}>
          <cylinderGeometry args={[0.025, 0.02, 0.48, 8]} />
          <meshStandardMaterial 
            color={getBoneColor('femur_left')}
            roughness={0.9}
            metalness={0.1}
          />
        </mesh>
        {/* Femur head */}
        <mesh position={[-0.1, 0.75, 0]}>
          <sphereGeometry args={[0.03, 16, 16]} />
          <meshStandardMaterial 
            color={getBoneColor('femur_left')}
            roughness={0.9}
            metalness={0.1}
          />
        </mesh>
      </group>
      
      {/* Femur - Right */}
      <group>
        <mesh position={[0.1, 0.5, 0]}>
          <cylinderGeometry args={[0.025, 0.02, 0.48, 8]} />
          <meshStandardMaterial 
            color={getBoneColor('femur_right')}
            roughness={0.9}
            metalness={0.1}
          />
        </mesh>
        {/* Femur head */}
        <mesh position={[0.1, 0.75, 0]}>
          <sphereGeometry args={[0.03, 16, 16]} />
          <meshStandardMaterial 
            color={getBoneColor('femur_right')}
            roughness={0.9}
            metalness={0.1}
          />
        </mesh>
      </group>
      
      {/* Patella (Kneecap) */}
      <mesh position={[-0.1, 0.25, 0.03]}>
        <sphereGeometry args={[0.02, 8, 8]} />
        <meshStandardMaterial 
          color={getBoneColor('patella_left')}
          roughness={0.9}
          metalness={0.1}
        />
      </mesh>
      <mesh position={[0.1, 0.25, 0.03]}>
        <sphereGeometry args={[0.02, 8, 8]} />
        <meshStandardMaterial 
          color={getBoneColor('patella_right')}
          roughness={0.9}
          metalness={0.1}
        />
      </mesh>
      
      {/* Tibia - Left */}
      <mesh position={[-0.1, 0.125, 0]}>
        <cylinderGeometry args={[0.02, 0.015, 0.36, 8]} />
        <meshStandardMaterial 
          color={getBoneColor('tibia_left')}
          roughness={0.9}
          metalness={0.1}
        />
      </mesh>
      
      {/* Tibia - Right */}
      <mesh position={[0.1, 0.125, 0]}>
        <cylinderGeometry args={[0.02, 0.015, 0.36, 8]} />
        <meshStandardMaterial 
          color={getBoneColor('tibia_right')}
          roughness={0.9}
          metalness={0.1}
        />
      </mesh>
      
      {/* Fibula - Left */}
      <mesh position={[-0.12, 0.125, -0.01]}>
        <cylinderGeometry args={[0.008, 0.006, 0.34, 8]} />
        <meshStandardMaterial 
          color={getBoneColor('fibula_left')}
          roughness={0.9}
          metalness={0.1}
        />
      </mesh>
      
      {/* Fibula - Right */}
      <mesh position={[0.12, 0.125, -0.01]}>
        <cylinderGeometry args={[0.008, 0.006, 0.34, 8]} />
        <meshStandardMaterial 
          color={getBoneColor('fibula_right')}
          roughness={0.9}
          metalness={0.1}
        />
      </mesh>
      
      {/* Foot bones (simplified) */}
      <mesh position={[-0.1, 0.02, 0.05]}>
        <boxGeometry args={[0.06, 0.02, 0.12]} />
        <meshStandardMaterial 
          color={getBoneColor('foot_left')}
          roughness={0.9}
          metalness={0.1}
        />
      </mesh>
      <mesh position={[0.1, 0.02, 0.05]}>
        <boxGeometry args={[0.06, 0.02, 0.12]} />
        <meshStandardMaterial 
          color={getBoneColor('foot_right')}
          roughness={0.9}
          metalness={0.1}
        />
      </mesh>
      
      {/* Joint connections visualization */}
      <Line
        points={[
          [-0.1, 0.75, 0],  // Hip joint
          [-0.1, 0.25, 0],  // Knee joint
          [-0.1, -0.05, 0], // Ankle joint
        ]}
        color="#666666"
        lineWidth={1}
        dashed={false}
      />
      <Line
        points={[
          [0.1, 0.75, 0],   // Hip joint
          [0.1, 0.25, 0],   // Knee joint
          [0.1, -0.05, 0],  // Ankle joint
        ]}
        color="#666666"
        lineWidth={1}
        dashed={false}
      />
    </group>
  )
}