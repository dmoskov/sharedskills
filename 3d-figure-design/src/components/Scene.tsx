import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Box, Sphere } from '@react-three/drei'
import * as THREE from 'three'
import { useStore } from '../store/useStore'
import FigureModel from './FigureModel'
import BlockoutFigure from './BlockoutFigure'
import MuscleSystem from './MuscleSystem'
import SkeletonSystem from './SkeletonSystem'
import ProportionGuides from './ProportionGuides'
import SymmetryHelper from './SymmetryHelper'
import DetailedLegMesh from './DetailedLegMesh'
import EdgeFlowVisualization from './EdgeFlowVisualization'

export default function Scene() {
  const { viewMode } = useStore()
  
  return (
    <>
      {/* Main figure based on view mode */}
      {viewMode === 'skin' && <BlockoutFigure />}
      {viewMode === 'muscles' && <MuscleSystem />}
      {viewMode === 'skeleton' && <SkeletonSystem />}
      {viewMode === 'combined' && (
        <>
          <BlockoutFigure />
          <MuscleSystem />
          <SkeletonSystem />
        </>
      )}
      {viewMode === 'detailed' && (
        <>
          <DetailedLegMesh side="left" />
          <DetailedLegMesh side="right" />
          <EdgeFlowVisualization />
        </>
      )}
      
      {/* Proportion guides */}
      <ProportionGuides />
      
      {/* Symmetry helpers */}
      <SymmetryHelper />
      
      {/* Ground plane for shadows */}
      <mesh 
        rotation={[-Math.PI / 2, 0, 0]} 
        position={[0, 0, 0]} 
        receiveShadow
      >
        <planeGeometry args={[10, 10]} />
        <shadowMaterial opacity={0.3} />
      </mesh>
    </>
  )
}