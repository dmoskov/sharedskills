import { useRef, useMemo } from 'react'
import * as THREE from 'three'
import { useFrame } from '@react-three/fiber'
import { Box, Sphere, Cylinder } from '@react-three/drei'

// Based on 8-head proportion system with 180cm height
// 1 head unit = 22.5cm
const HEAD_UNIT = 0.225 // in meters

export default function BlockoutFigure() {
  const groupRef = useRef<THREE.Group>(null)
  
  // Calculate proportions based on 8-head system
  const proportions = useMemo(() => ({
    // Heights from ground
    totalHeight: HEAD_UNIT * 8,        // 1.8m
    headTop: HEAD_UNIT * 8,            // 1.8m
    chinLevel: HEAD_UNIT * 7,          // 1.575m
    shoulderLevel: HEAD_UNIT * 6.5,    // 1.4625m
    nippleLevel: HEAD_UNIT * 6,        // 1.35m
    navelLevel: HEAD_UNIT * 5,         // 1.125m
    crotchLevel: HEAD_UNIT * 4,        // 0.9m
    kneeLevel: HEAD_UNIT * 2,          // 0.45m
    ankleLevel: HEAD_UNIT * 0.25,      // 0.05625m
    
    // Widths
    shoulderWidth: HEAD_UNIT * 2,      // 0.45m
    hipWidth: HEAD_UNIT * 1.5,         // 0.3375m
    
    // Leg specific measurements
    femurLength: HEAD_UNIT * 2,        // 0.45m (hip to knee)
    tibiaLength: HEAD_UNIT * 1.75,     // 0.39375m (knee to ankle)
    footLength: HEAD_UNIT * 1.1,       // 0.2475m
    footHeight: HEAD_UNIT * 0.3,       // 0.0675m
  }), [])
  
  const material = useMemo(() => (
    <meshStandardMaterial 
      color="#cccccc" 
      roughness={0.8}
      metalness={0.1}
      wireframe={false}
    />
  ), [])
  
  return (
    <group ref={groupRef} position={[0, 0, 0]}>
      {/* Head - 1 head unit */}
      <Sphere 
        args={[HEAD_UNIT * 0.5, 16, 16]} 
        position={[0, proportions.chinLevel + HEAD_UNIT * 0.5, 0]}
      >
        {material}
      </Sphere>
      
      {/* Neck */}
      <Cylinder 
        args={[HEAD_UNIT * 0.2, HEAD_UNIT * 0.15, HEAD_UNIT * 0.5, 8]}
        position={[0, proportions.chinLevel - HEAD_UNIT * 0.25, 0]}
      >
        {material}
      </Cylinder>
      
      {/* Torso - Upper (shoulders to navel) */}
      <Box 
        args={[proportions.shoulderWidth, proportions.shoulderLevel - proportions.navelLevel, HEAD_UNIT * 0.8]}
        position={[0, (proportions.shoulderLevel + proportions.navelLevel) / 2, 0]}
      >
        {material}
      </Box>
      
      {/* Torso - Lower (navel to crotch) */}
      <Box 
        args={[proportions.hipWidth, proportions.navelLevel - proportions.crotchLevel, HEAD_UNIT * 0.7]}
        position={[0, (proportions.navelLevel + proportions.crotchLevel) / 2, 0]}
      >
        {material}
      </Box>
      
      {/* LEFT LEG */}
      <group position={[-proportions.hipWidth * 0.3, 0, 0]}>
        {/* Femur (thigh) */}
        <Cylinder 
          args={[HEAD_UNIT * 0.35, HEAD_UNIT * 0.25, proportions.femurLength, 12]}
          position={[0, proportions.crotchLevel - proportions.femurLength / 2, 0]}
          rotation={[0, 0, 0]}
        >
          {material}
        </Cylinder>
        
        {/* Knee joint */}
        <Sphere 
          args={[HEAD_UNIT * 0.2, 12, 12]}
          position={[0, proportions.kneeLevel, 0]}
        >
          {material}
        </Sphere>
        
        {/* Tibia (lower leg) */}
        <Cylinder 
          args={[HEAD_UNIT * 0.25, HEAD_UNIT * 0.18, proportions.tibiaLength, 12]}
          position={[0, proportions.kneeLevel - proportions.tibiaLength / 2, 0]}
        >
          {material}
        </Cylinder>
        
        {/* Ankle joint */}
        <Sphere 
          args={[HEAD_UNIT * 0.15, 8, 8]}
          position={[0, proportions.ankleLevel, 0]}
        >
          {material}
        </Sphere>
        
        {/* Foot */}
        <Box 
          args={[HEAD_UNIT * 0.4, proportions.footHeight, proportions.footLength]}
          position={[0, proportions.footHeight / 2, proportions.footLength * 0.2]}
        >
          {material}
        </Box>
      </group>
      
      {/* RIGHT LEG */}
      <group position={[proportions.hipWidth * 0.3, 0, 0]}>
        {/* Femur (thigh) */}
        <Cylinder 
          args={[HEAD_UNIT * 0.35, HEAD_UNIT * 0.25, proportions.femurLength, 12]}
          position={[0, proportions.crotchLevel - proportions.femurLength / 2, 0]}
          rotation={[0, 0, 0]}
        >
          {material}
        </Cylinder>
        
        {/* Knee joint */}
        <Sphere 
          args={[HEAD_UNIT * 0.2, 12, 12]}
          position={[0, proportions.kneeLevel, 0]}
        >
          {material}
        </Sphere>
        
        {/* Tibia (lower leg) */}
        <Cylinder 
          args={[HEAD_UNIT * 0.25, HEAD_UNIT * 0.18, proportions.tibiaLength, 12]}
          position={[0, proportions.kneeLevel - proportions.tibiaLength / 2, 0]}
        >
          {material}
        </Cylinder>
        
        {/* Ankle joint */}
        <Sphere 
          args={[HEAD_UNIT * 0.15, 8, 8]}
          position={[0, proportions.ankleLevel, 0]}
        >
          {material}
        </Sphere>
        
        {/* Foot */}
        <Box 
          args={[HEAD_UNIT * 0.4, proportions.footHeight, proportions.footLength]}
          position={[0, proportions.footHeight / 2, proportions.footLength * 0.2]}
        >
          {material}
        </Box>
      </group>
      
      {/* Arms - simplified for now */}
      {/* Left arm */}
      <group position={[-proportions.shoulderWidth / 2, proportions.shoulderLevel - HEAD_UNIT * 0.2, 0]}>
        <Cylinder 
          args={[HEAD_UNIT * 0.15, HEAD_UNIT * 0.12, HEAD_UNIT * 1.5, 8]}
          position={[-HEAD_UNIT * 0.3, -HEAD_UNIT * 0.75, 0]}
          rotation={[0, 0, -0.3]}
        >
          {material}
        </Cylinder>
        <Cylinder 
          args={[HEAD_UNIT * 0.12, HEAD_UNIT * 0.1, HEAD_UNIT * 1.3, 8]}
          position={[-HEAD_UNIT * 0.7, -HEAD_UNIT * 1.8, 0]}
          rotation={[0, 0, -0.2]}
        >
          {material}
        </Cylinder>
      </group>
      
      {/* Right arm */}
      <group position={[proportions.shoulderWidth / 2, proportions.shoulderLevel - HEAD_UNIT * 0.2, 0]}>
        <Cylinder 
          args={[HEAD_UNIT * 0.15, HEAD_UNIT * 0.12, HEAD_UNIT * 1.5, 8]}
          position={[HEAD_UNIT * 0.3, -HEAD_UNIT * 0.75, 0]}
          rotation={[0, 0, 0.3]}
        >
          {material}
        </Cylinder>
        <Cylinder 
          args={[HEAD_UNIT * 0.12, HEAD_UNIT * 0.1, HEAD_UNIT * 1.3, 8]}
          position={[HEAD_UNIT * 0.7, -HEAD_UNIT * 1.8, 0]}
          rotation={[0, 0, 0.2]}
        >
          {material}
        </Cylinder>
      </group>
      
      {/* Reference measurements - can be toggled */}
      <group visible={false}>
        {/* 8 head unit markers */}
        {[...Array(9)].map((_, i) => (
          <Box 
            key={i}
            args={[2, 0.01, 0.01]}
            position={[0, HEAD_UNIT * i, 0]}
          >
            <meshBasicMaterial color="#ff0000" />
          </Box>
        ))}
      </group>
    </group>
  )
}