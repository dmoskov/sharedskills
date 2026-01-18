import { useRef } from 'react'
import { Line, Text } from '@react-three/drei'
import { useControls } from 'leva'
import * as THREE from 'three'

export default function EdgeFlowVisualization() {
  const { showEdgeFlow, edgeFlowOpacity, showLabels } = useControls('Edge Flow', {
    showEdgeFlow: { value: true, label: 'Show Edge Flow' },
    edgeFlowOpacity: { value: 0.6, min: 0, max: 1, label: 'Line Opacity' },
    showLabels: { value: true, label: 'Show Labels' }
  })

  if (!showEdgeFlow) return null

  // Define key edge loops for leg deformation
  const edgeLoops = [
    {
      name: 'Hip Joint',
      points: [
        [-0.15, 0.9, 0.05],
        [-0.1, 0.9, 0.07],
        [0, 0.9, 0.08],
        [0.1, 0.9, 0.07],
        [0.15, 0.9, 0.05],
        [0.15, 0.9, -0.05],
        [0.1, 0.9, -0.07],
        [0, 0.9, -0.08],
        [-0.1, 0.9, -0.07],
        [-0.15, 0.9, -0.05],
        [-0.15, 0.9, 0.05]
      ],
      color: '#ff0000'
    },
    {
      name: 'Upper Thigh',
      points: [
        [-0.06, 0.7, 0.05],
        [0, 0.7, 0.06],
        [0.06, 0.7, 0.05],
        [0.06, 0.7, -0.05],
        [0, 0.7, -0.06],
        [-0.06, 0.7, -0.05],
        [-0.06, 0.7, 0.05]
      ],
      color: '#ff6600'
    },
    {
      name: 'Mid Thigh',
      points: [
        [-0.05, 0.6, 0.04],
        [0, 0.6, 0.05],
        [0.05, 0.6, 0.04],
        [0.05, 0.6, -0.04],
        [0, 0.6, -0.05],
        [-0.05, 0.6, -0.04],
        [-0.05, 0.6, 0.04]
      ],
      color: '#ffcc00'
    },
    {
      name: 'Above Knee',
      points: [
        [-0.04, 0.48, 0.035],
        [0, 0.48, 0.04],
        [0.04, 0.48, 0.035],
        [0.04, 0.48, -0.035],
        [0, 0.48, -0.04],
        [-0.04, 0.48, -0.035],
        [-0.04, 0.48, 0.035]
      ],
      color: '#00ff00'
    },
    {
      name: 'Knee Joint (3 loops)',
      points: [
        [-0.035, 0.45, 0.04],
        [0, 0.45, 0.05],
        [0.035, 0.45, 0.04],
        [0.035, 0.45, -0.03],
        [0, 0.45, -0.035],
        [-0.035, 0.45, -0.03],
        [-0.035, 0.45, 0.04]
      ],
      color: '#00ffff'
    },
    {
      name: 'Below Knee',
      points: [
        [-0.04, 0.42, 0.03],
        [0, 0.42, 0.035],
        [0.04, 0.42, 0.03],
        [0.04, 0.42, -0.035],
        [0, 0.42, -0.04],
        [-0.04, 0.42, -0.035],
        [-0.04, 0.42, 0.03]
      ],
      color: '#0066ff'
    },
    {
      name: 'Upper Calf',
      points: [
        [-0.04, 0.35, 0.02],
        [0, 0.35, 0.025],
        [0.04, 0.35, 0.02],
        [0.04, 0.35, -0.04],
        [0, 0.35, -0.045],
        [-0.04, 0.35, -0.04],
        [-0.04, 0.35, 0.02]
      ],
      color: '#0000ff'
    },
    {
      name: 'Mid Calf',
      points: [
        [-0.03, 0.25, 0.02],
        [0, 0.25, 0.025],
        [0.03, 0.25, 0.02],
        [0.03, 0.25, -0.03],
        [0, 0.25, -0.035],
        [-0.03, 0.25, -0.03],
        [-0.03, 0.25, 0.02]
      ],
      color: '#6600ff'
    },
    {
      name: 'Above Ankle',
      points: [
        [-0.025, 0.08, 0.015],
        [0, 0.08, 0.018],
        [0.025, 0.08, 0.015],
        [0.025, 0.08, -0.015],
        [0, 0.08, -0.018],
        [-0.025, 0.08, -0.015],
        [-0.025, 0.08, 0.015]
      ],
      color: '#cc00ff'
    },
    {
      name: 'Ankle Joint (2 loops)',
      points: [
        [-0.025, 0.055, 0.015],
        [0, 0.055, 0.02],
        [0.02, 0.055, 0.015],
        [0.02, 0.055, -0.015],
        [0, 0.055, -0.02],
        [-0.025, 0.055, -0.015],
        [-0.025, 0.055, 0.015]
      ],
      color: '#ff00ff'
    }
  ]

  // Vertical edge flows (muscle fiber direction)
  const verticalFlows = [
    {
      name: 'Rectus Femoris',
      points: [
        [0, 0.9, 0.05],
        [0, 0.7, 0.06],
        [0, 0.5, 0.04],
        [0, 0.45, 0.05]
      ],
      color: '#ff9999'
    },
    {
      name: 'Vastus Lateralis',
      points: [
        [0.06, 0.85, 0.03],
        [0.06, 0.7, 0.05],
        [0.05, 0.55, 0.04],
        [0.035, 0.45, 0.04]
      ],
      color: '#99ff99'
    },
    {
      name: 'Hamstring Line',
      points: [
        [0, 0.9, -0.05],
        [0, 0.7, -0.06],
        [0, 0.5, -0.04],
        [0, 0.45, -0.035]
      ],
      color: '#9999ff'
    },
    {
      name: 'Gastrocnemius',
      points: [
        [0, 0.45, -0.035],
        [0, 0.35, -0.045],
        [0, 0.25, -0.035],
        [0, 0.15, -0.02],
        [0, 0.055, -0.015]
      ],
      color: '#ff99ff'
    },
    {
      name: 'Tibialis Anterior',
      points: [
        [0.035, 0.42, 0.03],
        [0.04, 0.35, 0.02],
        [0.03, 0.25, 0.02],
        [0.025, 0.15, 0.015],
        [0.02, 0.08, 0.015]
      ],
      color: '#99ffff'
    }
  ]

  return (
    <group>
      {/* Horizontal edge loops */}
      {edgeLoops.map((loop, index) => (
        <group key={index}>
          {/* Left leg */}
          <Line
            points={loop.points.map(p => [-0.1 + p[0], p[1], p[2]] as [number, number, number])}
            color={loop.color}
            lineWidth={2}
            transparent
            opacity={edgeFlowOpacity}
          />
          {/* Right leg */}
          <Line
            points={loop.points.map(p => [0.1 + p[0], p[1], p[2]] as [number, number, number])}
            color={loop.color}
            lineWidth={2}
            transparent
            opacity={edgeFlowOpacity}
          />
          {showLabels && index % 2 === 0 && (
            <Text
              position={[0.3, loop.points[0][1], 0]}
              fontSize={0.03}
              color={loop.color}
              anchorX="left"
            >
              {loop.name}
            </Text>
          )}
        </group>
      ))}

      {/* Vertical edge flows */}
      {verticalFlows.map((flow, index) => (
        <group key={`v-${index}`}>
          {/* Left leg */}
          <Line
            points={flow.points.map(p => [-0.1 + p[0], p[1], p[2]] as [number, number, number])}
            color={flow.color}
            lineWidth={1.5}
            transparent
            opacity={edgeFlowOpacity * 0.7}
            dashed
            dashScale={50}
          />
          {/* Right leg */}
          <Line
            points={flow.points.map(p => [0.1 + p[0], p[1], p[2]] as [number, number, number])}
            color={flow.color}
            lineWidth={1.5}
            transparent
            opacity={edgeFlowOpacity * 0.7}
            dashed
            dashScale={50}
          />
        </group>
      ))}

      {/* Spiral topology indicators */}
      <group visible={showLabels}>
        <Text
          position={[-0.35, 0.7, 0]}
          fontSize={0.025}
          color="#ffffff"
          anchorX="center"
          rotation={[0, 0, Math.PI / 2]}
        >
          Spiral topology follows muscle fibers
        </Text>
        <Text
          position={[-0.35, 0.3, 0]}
          fontSize={0.025}
          color="#ffffff"
          anchorX="center"
          rotation={[0, 0, Math.PI / 2]}
        >
          3 loops minimum at joints
        </Text>
      </group>
    </group>
  )
}