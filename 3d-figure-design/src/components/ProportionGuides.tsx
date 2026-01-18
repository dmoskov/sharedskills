import { Line, Text } from '@react-three/drei'
import { useControls } from 'leva'

const HEAD_UNIT = 0.225 // 22.5cm per head unit

export default function ProportionGuides() {
  const { showGuides, showLabels, guideColor, guideOpacity } = useControls('Proportion Guides', {
    showGuides: { value: true, label: 'Show Guides' },
    showLabels: { value: true, label: 'Show Labels' },
    guideColor: { value: '#00ff00', label: 'Guide Color' },
    guideOpacity: { value: 0.5, min: 0, max: 1, label: 'Guide Opacity' }
  })

  if (!showGuides) return null

  const levels = [
    { height: 0, label: 'Ground' },
    { height: HEAD_UNIT * 0.25, label: 'Ankle' },
    { height: HEAD_UNIT * 2, label: 'Knee' },
    { height: HEAD_UNIT * 4, label: 'Crotch' },
    { height: HEAD_UNIT * 5, label: 'Navel' },
    { height: HEAD_UNIT * 6, label: 'Nipple' },
    { height: HEAD_UNIT * 6.5, label: 'Shoulder' },
    { height: HEAD_UNIT * 7, label: 'Chin' },
    { height: HEAD_UNIT * 8, label: 'Head Top' }
  ]

  const verticalGuides = [
    { x: -HEAD_UNIT, label: 'L Shoulder' },
    { x: 0, label: 'Center' },
    { x: HEAD_UNIT, label: 'R Shoulder' }
  ]

  return (
    <group>
      {/* Horizontal guides */}
      {levels.map((level, i) => (
        <group key={i}>
          <Line
            points={[
              [-2, level.height, 0],
              [2, level.height, 0]
            ]}
            color={guideColor}
            lineWidth={1}
            transparent
            opacity={guideOpacity}
            dashed
            dashScale={50}
          />
          {showLabels && (
            <Text
              position={[2.2, level.height, 0]}
              fontSize={0.05}
              color={guideColor}
              anchorX="left"
              anchorY="middle"
            >
              {level.label} ({i} heads)
            </Text>
          )}
        </group>
      ))}

      {/* Vertical guides */}
      {verticalGuides.map((guide, i) => (
        <group key={i}>
          <Line
            points={[
              [guide.x, 0, 0],
              [guide.x, HEAD_UNIT * 8, 0]
            ]}
            color={guideColor}
            lineWidth={1}
            transparent
            opacity={guideOpacity * 0.5}
            dashed
            dashScale={50}
          />
        </group>
      ))}

      {/* Special leg proportion lines */}
      <group>
        {/* Femur length indicator */}
        <Line
          points={[
            [-0.5, HEAD_UNIT * 4, 0],
            [-0.5, HEAD_UNIT * 2, 0]
          ]}
          color="#ff0000"
          lineWidth={2}
          transparent
          opacity={guideOpacity}
        />
        {showLabels && (
          <Text
            position={[-0.6, HEAD_UNIT * 3, 0]}
            fontSize={0.04}
            color="#ff0000"
            anchorX="right"
            anchorY="middle"
            rotation={[0, 0, Math.PI / 2]}
          >
            Femur (2 heads)
          </Text>
        )}

        {/* Tibia length indicator */}
        <Line
          points={[
            [0.5, HEAD_UNIT * 2, 0],
            [0.5, HEAD_UNIT * 0.25, 0]
          ]}
          color="#0000ff"
          lineWidth={2}
          transparent
          opacity={guideOpacity}
        />
        {showLabels && (
          <Text
            position={[0.6, HEAD_UNIT * 1.125, 0]}
            fontSize={0.04}
            color="#0000ff"
            anchorX="left"
            anchorY="middle"
            rotation={[0, 0, -Math.PI / 2]}
          >
            Tibia (1.75 heads)
          </Text>
        )}
      </group>

      {/* Center of gravity indicator */}
      <group>
        <Line
          points={[
            [-0.2, HEAD_UNIT * 4.5, 0],
            [0.2, HEAD_UNIT * 4.5, 0]
          ]}
          color="#ff00ff"
          lineWidth={3}
        />
        {showLabels && (
          <Text
            position={[0.3, HEAD_UNIT * 4.5, 0]}
            fontSize={0.04}
            color="#ff00ff"
            anchorX="left"
            anchorY="middle"
          >
            COG
          </Text>
        )}
      </group>
    </group>
  )
}