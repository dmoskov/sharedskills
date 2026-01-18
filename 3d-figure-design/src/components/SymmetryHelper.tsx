import { useRef, useEffect } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Line } from '@react-three/drei'
import { useControls } from 'leva'

export default function SymmetryHelper() {
  const { showSymmetryPlane, symmetryOpacity, mirrorMode } = useControls('Symmetry', {
    showSymmetryPlane: { value: true, label: 'Show Symmetry Plane' },
    symmetryOpacity: { value: 0.2, min: 0, max: 1, label: 'Plane Opacity' },
    mirrorMode: { 
      value: 'none', 
      options: ['none', 'left-to-right', 'right-to-left'],
      label: 'Mirror Mode'
    }
  })

  const planeRef = useRef<THREE.Mesh>(null)

  // Animate the symmetry plane
  useFrame((state) => {
    if (planeRef.current && showSymmetryPlane) {
      // Subtle pulsing effect
      const scale = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.02
      planeRef.current.scale.set(1, scale, scale)
    }
  })

  return (
    <group>
      {/* Symmetry plane */}
      {showSymmetryPlane && (
        <mesh ref={planeRef} position={[0, 0.9, 0]}>
          <planeGeometry args={[0.01, 2, 2]} />
          <meshBasicMaterial 
            color="#00ffff"
            transparent
            opacity={symmetryOpacity}
            side={THREE.DoubleSide}
          />
        </mesh>
      )}

      {/* Center line */}
      <Line
        points={[
          [0, 0, -1],
          [0, 0, 1]
        ]}
        color="#00ffff"
        lineWidth={2}
        dashed
        dashScale={20}
      />

      {/* Symmetry axis indicator */}
      <Line
        points={[
          [0, 0, 0],
          [0, 2, 0]
        ]}
        color="#00ffff"
        lineWidth={1}
        dashed
        dashScale={10}
        opacity={0.5}
      />

      {/* Mirror visualization helpers */}
      {mirrorMode !== 'none' && (
        <>
          {/* Left side indicator */}
          <mesh position={[-0.5, 1, 0]}>
            <coneGeometry args={[0.05, 0.1, 4]} />
            <meshBasicMaterial 
              color={mirrorMode === 'left-to-right' ? '#00ff00' : '#ff0000'}
            />
          </mesh>
          
          {/* Right side indicator */}
          <mesh position={[0.5, 1, 0]} rotation={[0, 0, Math.PI]}>
            <coneGeometry args={[0.05, 0.1, 4]} />
            <meshBasicMaterial 
              color={mirrorMode === 'right-to-left' ? '#00ff00' : '#ff0000'}
            />
          </mesh>

          {/* Arrow showing mirror direction */}
          <Line
            points={
              mirrorMode === 'left-to-right' 
                ? [[-0.3, 1, 0], [0.3, 1, 0]]
                : [[0.3, 1, 0], [-0.3, 1, 0]]
            }
            color="#ffff00"
            lineWidth={3}
          />
        </>
      )}
    </group>
  )
}