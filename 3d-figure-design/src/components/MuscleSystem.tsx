import { useRef } from 'react'
import * as THREE from 'three'
import { useStore } from '../store/useStore'

export default function MuscleSystem() {
  const groupRef = useRef<THREE.Group>(null)
  const { muscleVisibility, selectedMuscle } = useStore()
  
  // Simplified muscle representations
  // In production, these would be anatomically accurate 3D models
  
  const getMuscleColor = (muscleId: string) => {
    if (!muscleVisibility[muscleId]) return '#333333'
    if (selectedMuscle === muscleId) return '#ff6b6b'
    return '#c92a2a'
  }
  
  const getMuscleOpacity = (muscleId: string) => {
    if (!muscleVisibility[muscleId]) return 0.1
    if (selectedMuscle === muscleId) return 1
    return 0.8
  }
  
  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* Quadriceps - Front of thigh */}
      <mesh position={[-0.1, 0.5, 0.05]} visible={muscleVisibility.quadriceps}>
        <boxGeometry args={[0.08, 0.35, 0.06]} />
        <meshStandardMaterial 
          color={getMuscleColor('quadriceps')}
          transparent
          opacity={getMuscleOpacity('quadriceps')}
          roughness={0.8}
        />
      </mesh>
      <mesh position={[0.1, 0.5, 0.05]} visible={muscleVisibility.quadriceps}>
        <boxGeometry args={[0.08, 0.35, 0.06]} />
        <meshStandardMaterial 
          color={getMuscleColor('quadriceps')}
          transparent
          opacity={getMuscleOpacity('quadriceps')}
          roughness={0.8}
        />
      </mesh>
      
      {/* Hamstrings - Back of thigh */}
      <mesh position={[-0.1, 0.5, -0.05]} visible={muscleVisibility.hamstrings}>
        <boxGeometry args={[0.07, 0.3, 0.05]} />
        <meshStandardMaterial 
          color={getMuscleColor('hamstrings')}
          transparent
          opacity={getMuscleOpacity('hamstrings')}
          roughness={0.8}
        />
      </mesh>
      <mesh position={[0.1, 0.5, -0.05]} visible={muscleVisibility.hamstrings}>
        <boxGeometry args={[0.07, 0.3, 0.05]} />
        <meshStandardMaterial 
          color={getMuscleColor('hamstrings')}
          transparent
          opacity={getMuscleOpacity('hamstrings')}
          roughness={0.8}
        />
      </mesh>
      
      {/* Calves - Gastrocnemius */}
      <mesh position={[-0.1, 0.15, -0.03]} visible={muscleVisibility.calves}>
        <sphereGeometry args={[0.05, 16, 16]} />
        <meshStandardMaterial 
          color={getMuscleColor('calves')}
          transparent
          opacity={getMuscleOpacity('calves')}
          roughness={0.8}
        />
      </mesh>
      <mesh position={[0.1, 0.15, -0.03]} visible={muscleVisibility.calves}>
        <sphereGeometry args={[0.05, 16, 16]} />
        <meshStandardMaterial 
          color={getMuscleColor('calves')}
          transparent
          opacity={getMuscleOpacity('calves')}
          roughness={0.8}
        />
      </mesh>
      
      {/* Glutes */}
      <mesh position={[0, 0.85, -0.05]} visible={muscleVisibility.glutes}>
        <boxGeometry args={[0.25, 0.15, 0.08]} />
        <meshStandardMaterial 
          color={getMuscleColor('glutes')}
          transparent
          opacity={getMuscleOpacity('glutes')}
          roughness={0.8}
        />
      </mesh>
      
      {/* Adductors - Inner thigh */}
      <mesh position={[-0.05, 0.6, 0]} visible={muscleVisibility.adductors}>
        <boxGeometry args={[0.04, 0.25, 0.06]} />
        <meshStandardMaterial 
          color={getMuscleColor('adductors')}
          transparent
          opacity={getMuscleOpacity('adductors')}
          roughness={0.8}
        />
      </mesh>
      <mesh position={[0.05, 0.6, 0]} visible={muscleVisibility.adductors}>
        <boxGeometry args={[0.04, 0.25, 0.06]} />
        <meshStandardMaterial 
          color={getMuscleColor('adductors')}
          transparent
          opacity={getMuscleOpacity('adductors')}
          roughness={0.8}
        />
      </mesh>
      
      {/* Tibialis Anterior - Front of shin */}
      <mesh position={[-0.1, 0.125, 0.04]} visible={muscleVisibility.tibialis}>
        <boxGeometry args={[0.03, 0.3, 0.02]} />
        <meshStandardMaterial 
          color={getMuscleColor('tibialis')}
          transparent
          opacity={getMuscleOpacity('tibialis')}
          roughness={0.8}
        />
      </mesh>
      <mesh position={[0.1, 0.125, 0.04]} visible={muscleVisibility.tibialis}>
        <boxGeometry args={[0.03, 0.3, 0.02]} />
        <meshStandardMaterial 
          color={getMuscleColor('tibialis')}
          transparent
          opacity={getMuscleOpacity('tibialis')}
          roughness={0.8}
        />
      </mesh>
    </group>
  )
}