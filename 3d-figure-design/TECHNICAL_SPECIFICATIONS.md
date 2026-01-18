# Technical Specifications for 3D Figure Design Pipeline

## Overview
This document outlines the complete technical pipeline for creating a high-quality 3D human figure with specialized leg mapping capabilities, from initial modeling to final delivery.

## Software Pipeline

### Primary Software Stack

#### 1. Modeling & Sculpting
- **Primary**: Blender 4.0+ (Free, comprehensive toolset)
  - Base mesh creation
  - Retopology
  - UV mapping
  - Initial rigging tests
- **High-Res Sculpting**: ZBrush 2024
  - Anatomical detail sculpting
  - Displacement map generation
  - Polygroups for organization
- **Alternative**: Autodesk Maya 2024 (Industry standard)

#### 2. Texturing
- **Primary**: Substance 3D Painter
  - PBR texture creation
  - Smart materials for skin
  - Procedural wear and detail
- **Secondary**: Mari (Film-quality texturing)
  - UDIM workflow
  - High-resolution painting
- **Utility**: Substance 3D Designer
  - Procedural texture creation
  - Tiling patterns

#### 3. Rigging & Animation
- **Primary**: Maya 2024
  - Advanced rigging systems
  - Muscle simulation
  - Animation tools
- **Alternative**: Blender (Rigify addon)
- **Muscle System**: Ziva Dynamics
  - Realistic muscle simulation
  - Volume preservation

#### 4. Real-time Engine Integration
- **Unreal Engine 5.3+**
  - Nanite virtualized geometry
  - Lumen global illumination
  - Control Rig integration
- **Unity 2023.2 LTS**
  - HDRP for high-quality rendering
  - Animation Rigging package

### Supporting Software
- **Version Control**: Perforce or Git LFS
- **Project Management**: ShotGrid or Asana
- **Render Farm**: Deadline or custom solution

## File Formats and Standards

### 3D Model Formats
- **Source Files**: 
  - .blend (Blender native)
  - .ma/.mb (Maya native)
  - .ztl/.zpr (ZBrush)
- **Exchange Formats**:
  - .fbx (animation/rigging)
  - .obj (static mesh)
  - .abc (Alembic for animation)
  - .usd/usda/usdc (Universal Scene Description)

### Texture Formats
- **Working Files**:
  - .exr (32-bit float, linear)
  - .tiff (16-bit, uncompressed)
- **Delivery**:
  - .png (8-bit, web/game)
  - .dds (compressed, game engines)
  - .tx (renderman/arnold)

### Map Types Required
1. **Base Color/Albedo** (sRGB)
2. **Normal Map** (Tangent space)
3. **Displacement** (32-bit float)
4. **Roughness** (Linear)
5. **Metallic** (Linear)
6. **Ambient Occlusion** (Linear)
7. **Subsurface Scattering**
   - SSS Color
   - SSS Radius
   - SSS Scale
8. **Specular** (for skin)
9. **Cavity Map**
10. **Thickness Map** (for SSS)

## Naming Conventions

### File Naming Structure
```
[project]_[asset]_[variant]_[version]_[suffix].[ext]

Example: fig_body_male_v03_highpoly.fbx
```

### Components:
- **project**: 3-letter project code (fig)
- **asset**: Asset name (body, leg, foot)
- **variant**: Variation (male, female, neutral)
- **version**: v01, v02, etc.
- **suffix**: 
  - highpoly (sculpt)
  - lowpoly (game)
  - midpoly (animation)
  - rig (rigged file)

### Texture Naming
```
[asset]_[part]_[maptype]_[resolution].[ext]

Example: body_leg_normal_4k.png
```

### Node/Object Naming (in scene)
```
[side]_[part]_[type]_[number]

Example: L_femur_bone_01
```

Sides:
- L = Left
- R = Right
- C = Center

## UV Mapping Strategy

### UDIM Layout (Primary Method)
```
1001: Head
1002: Torso Front
1003: Torso Back
1004: Right Leg Front
1005: Right Leg Back
1006: Left Leg Front
1007: Left Leg Back
1008: Arms
1009: Hands
1010: Feet
```

### UV Requirements
- **Texel Density**: Consistent 20.48 pixels/cm for 4K
- **Padding**: 16 pixels minimum between islands
- **Orientation**: Consistent up-vector
- **Seams**: Hidden in natural creases
- **Overlap**: None (except for symmetrical parts)

### Special Considerations for Legs
- Separate UV space for each leg
- Higher texel density for close-up details
- Seams placed on inner thigh and back of leg
- Special attention to knee and ankle deformation

## Rigging Specifications

### Bone Naming Convention
```
[side]_[part]_[type]_[number]

Example: L_femur_jnt_01
```

### Joint Hierarchy
```
Root
├── Pelvis
│   ├── L_Hip
│   │   ├── L_Femur
│   │   │   ├── L_Knee
│   │   │   │   ├── L_Tibia
│   │   │   │   │   ├── L_Ankle
│   │   │   │   │   │   ├── L_Foot
│   │   │   │   │   │   │   ├── L_Toes
```

### Control Types
1. **FK Controls**: Direct rotation
2. **IK Controls**: End-effector based
3. **Blend Controls**: IK/FK switching
4. **Space Switches**: Parent constraints
5. **Attribute Controls**: Custom channels

### Leg-Specific Controls
- **IK Foot Control**:
  - Foot position/rotation
  - Heel raise
  - Ball roll
  - Toe tap
  - Bank (side roll)
- **Knee Control**:
  - Pole vector
  - Soft IK
  - Lock/unlock
- **Hip Control**:
  - Hip sway
  - Isolation from pelvis

## LOD (Level of Detail) Specifications

### LOD0 - Cinematic Quality
- **Polygons**: 500k - 1M
- **Textures**: 8K UDIM
- **Bones**: Full rig (200+ bones)
- **Use Case**: Film, medical visualization

### LOD1 - Hero Game Asset
- **Polygons**: 50k - 100k
- **Textures**: 4K atlas
- **Bones**: 65-80 bones
- **Use Case**: PC/Console protagonist

### LOD2 - Standard Game Asset
- **Polygons**: 10k - 20k
- **Textures**: 2K atlas
- **Bones**: 40-50 bones
- **Use Case**: NPCs, multiplayer

### LOD3 - Mobile/VR
- **Polygons**: 2k - 5k
- **Textures**: 1K atlas
- **Bones**: 25-30 bones
- **Use Case**: Mobile games, VR

### LOD4 - Distant/Crowd
- **Polygons**: 500 - 1k
- **Textures**: 512px
- **Bones**: 15-20 bones
- **Use Case**: Crowds, distant views

## Performance Optimization

### Polygon Optimization
- **Edge Loop Reduction**: Automated via Blender/Maya
- **Decimation**: ZBrush Decimation Master
- **Manual Optimization**: Critical deformation areas

### Texture Optimization
- **Channel Packing**:
  - R: Ambient Occlusion
  - G: Roughness
  - B: Metallic
- **Compression**: BC7 for base color, BC5 for normals
- **Mipmapping**: Proper generation for all textures

### Bone Optimization
- **Twist Bones**: Only in LOD0-1
- **Helper Bones**: Removed in LOD2+
- **Finger Bones**: Simplified in LOD3+

## Shader Requirements

### Skin Shader Components
```glsl
// Pseudo-code for skin shader
struct SkinShaderInputs {
    float3 baseColor;
    float3 normal;
    float roughness;
    float3 subsurfaceColor;
    float subsurfaceRadius;
    float subsurfaceScale;
    float3 specular;
    float thickness;
}
```

### Required Features
1. **Subsurface Scattering**: Multi-layer
2. **Dual Specular Lobes**: For skin oils
3. **Normal Blending**: Detail + base
4. **Microgeometry**: Pore-level detail
5. **Blood Flow Maps**: Dynamic coloration

## Quality Assurance Checklist

### Modeling QA
- [ ] Manifold geometry (watertight)
- [ ] No n-gons or triangles in deform areas
- [ ] Consistent edge flow
- [ ] Proper scale (real-world units)
- [ ] Clean construction history

### UV QA
- [ ] No overlapping UVs
- [ ] Consistent texel density
- [ ] Proper padding between islands
- [ ] Seams in hidden areas
- [ ] UDIM tiles properly assigned

### Rigging QA
- [ ] All controls zeroed in bind pose
- [ ] Proper rotation orders set
- [ ] No dependency cycles
- [ ] Clean channel box
- [ ] Intuitive control shapes

### Animation QA
- [ ] No mesh penetration at extremes
- [ ] Volume preservation working
- [ ] Smooth weight transitions
- [ ] No candy wrapper effects
- [ ] Stable at 30/60/120 fps

## Delivery Specifications

### Folder Structure
```
ProjectName/
├── Models/
│   ├── HighPoly/
│   ├── LowPoly/
│   └── Source/
├── Textures/
│   ├── 8K/
│   ├── 4K/
│   ├── 2K/
│   └── Source/
├── Rigs/
│   ├── Maya/
│   └── Blender/
├── Animation/
│   └── Clips/
├── Documentation/
│   ├── Setup_Guide.pdf
│   └── Control_Reference.pdf
└── Scripts/
    └── Pipeline_Tools/
```

### Delivery Formats
1. **Source Package**: All working files
2. **Game Package**: Optimized FBX + textures
3. **Film Package**: Alembic cache + EXR
4. **Documentation**: PDF guides + video tutorials

## Pipeline Integration

### Version Control Setup
```bash
# Git LFS tracking
git lfs track "*.fbx"
git lfs track "*.blend"
git lfs track "*.ma"
git lfs track "*.exr"
```

### Automated Validation
```python
# Example validation script
def validate_model(filepath):
    checks = {
        'polycount': check_polycount(),
        'uvs': check_uv_overlap(),
        'naming': check_naming_convention(),
        'scale': check_world_scale()
    }
    return all(checks.values())
```

## Hardware Requirements

### Minimum Specifications
- **CPU**: 8-core 3.5GHz+
- **RAM**: 32GB DDR4
- **GPU**: RTX 3060 or equivalent
- **Storage**: 1TB NVMe SSD

### Recommended Specifications
- **CPU**: 16-core 4.0GHz+
- **RAM**: 64GB DDR5
- **GPU**: RTX 4080 or better
- **Storage**: 2TB NVMe SSD RAID

### Render Farm Specifications
- **CPU Rendering**: 256+ cores total
- **GPU Rendering**: 8x RTX 4090
- **Network**: 10Gb ethernet
- **Storage**: 100TB+ NAS

This technical specification ensures consistency and quality throughout the 3D figure design pipeline, with special attention to the requirements for anatomically accurate leg modeling and animation.