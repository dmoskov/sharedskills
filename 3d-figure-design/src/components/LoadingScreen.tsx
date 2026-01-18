import { Html, useProgress } from '@react-three/drei'

export default function LoadingScreen() {
  const { progress } = useProgress()
  
  return (
    <Html center>
      <div className="loading-screen">
        <div className="loading-spinner" />
        <p style={{ marginTop: 16, fontSize: 14, color: '#666' }}>
          Loading 3D assets... {progress.toFixed(0)}%
        </p>
      </div>
    </Html>
  )
}