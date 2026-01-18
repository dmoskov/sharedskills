import { Canvas } from '@react-three/fiber'
import { OrbitControls, Grid, Environment, Stats } from '@react-three/drei'
import { Suspense, useState } from 'react'
import { Leva, useControls } from 'leva'
import Scene from './components/Scene'
import LoadingScreen from './components/LoadingScreen'
import UIOverlay from './components/UIOverlay'
import { useStore } from './store/useStore'

function App() {
  const [showStats, setShowStats] = useState(true)
  const { viewMode } = useStore()

  const { gridEnabled, ambientIntensity, environmentPreset } = useControls({
    gridEnabled: { value: true, label: 'Show Grid' },
    ambientIntensity: { value: 0.5, min: 0, max: 1, label: 'Ambient Light' },
    environmentPreset: {
      value: 'studio',
      options: ['studio', 'sunset', 'dawn', 'night', 'warehouse', 'forest', 'apartment'],
      label: 'Environment'
    }
  })

  return (
    <>
      <UIOverlay />
      <Canvas
        camera={{ 
          position: [2, 1.5, 2], 
          fov: 45,
          near: 0.1,
          far: 100
        }}
        shadows
        dpr={[1, 2]}
      >
        <Suspense fallback={<LoadingScreen />}>
          <Scene />
          <OrbitControls 
            enablePan={true}
            enableZoom={true}
            enableRotate={true}
            minDistance={0.5}
            maxDistance={10}
            target={[0, 1, 0]}
          />
          {gridEnabled && (
            <Grid 
              args={[10, 10]} 
              cellSize={0.5} 
              cellThickness={0.5} 
              cellColor="#333333" 
              sectionSize={5} 
              sectionThickness={1} 
              sectionColor="#666666" 
              fadeDistance={30} 
              fadeStrength={1} 
              followCamera={false} 
              infiniteGrid={true} 
            />
          )}
          <ambientLight intensity={ambientIntensity} />
          <directionalLight 
            position={[5, 5, 5]} 
            intensity={1} 
            castShadow 
            shadow-mapSize={2048}
            shadow-bias={-0.0001}
          />
          <Environment preset={environmentPreset as any} background={false} />
        </Suspense>
        {showStats && <Stats />}
      </Canvas>
      <Leva 
        collapsed={false}
        oneLineLabels={false}
        flat={true}
        theme={{
          sizes: {
            titleBarHeight: '28px',
          },
          fontSizes: {
            root: '11px',
          },
        }}
      />
    </>
  )
}

export default App