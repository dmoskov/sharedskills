# 3D Figure Design Specifications

## Project Overview
This document defines the specifications and proportions for a 3D human figure model with specialized focus on anatomically accurate leg mapping.

## Figure Specifications

### Target Audience
- **Primary**: Medical visualization and education
- **Secondary**: High-end animation and VFX production
- **Tertiary**: Game development (with LOD optimization)

### Base Proportions
- **Height**: 180cm (6 feet) - Industry standard reference
- **Proportion System**: 8-head classical proportion
  - Head: 22.5cm
  - Torso: 3 heads (67.5cm)
  - Legs: 4 heads (90cm) from hip to floor
  - Arms: 3.5 heads fingertip to fingertip

### Anatomical Focus - Legs
Special emphasis on leg anatomy for medical accuracy:

#### Bone Structure
- **Femur**: 48cm (26.7% of height)
- **Tibia**: 36cm (20% of height)
- **Fibula**: Parallel to tibia
- **Patella**: 5cm diameter
- **Foot**: 25cm length

#### Major Muscle Groups
1. **Quadriceps**
   - Rectus femoris
   - Vastus lateralis
   - Vastus medialis
   - Vastus intermedius

2. **Hamstrings**
   - Biceps femoris
   - Semitendinosus
   - Semimembranosus

3. **Calf Muscles**
   - Gastrocnemius (medial and lateral heads)
   - Soleus
   - Tibialis anterior

4. **Glutes**
   - Gluteus maximus
   - Gluteus medius
   - Gluteus minimus

### Level of Detail (LOD) Requirements

#### LOD0 - Hero/Medical (500k-1M polygons)
- Full muscle definition
- Visible tendons and ligaments
- Skin pore detail
- Vein networks
- Subsurface scattering ready

#### LOD1 - Animation (50k-100k polygons)
- Major muscle groups defined
- Smooth deformation topology
- Optimized for rigging
- Clean edge loops at joints

#### LOD2 - Game High (10k-20k polygons)
- Simplified muscle forms
- Optimized joint deformation
- Normal map detail preservation

#### LOD3 - Game Low (2k-5k polygons)
- Basic form preservation
- Mobile/VR optimized
- Efficient UV layout

### Technical Requirements

#### Polygon Budget
- **Hero Model**: 500,000 - 1,000,000 polygons
- **Production Model**: 50,000 - 100,000 polygons
- **Game Model**: 2,000 - 20,000 polygons (with LODs)

#### UV Layout Strategy
- **UDIM Layout**: 10 tiles for hero model
  - Tile 1001: Head
  - Tile 1002: Torso front
  - Tile 1003: Torso back
  - Tile 1004-1005: Right leg (front/back)
  - Tile 1006-1007: Left leg (front/back)
  - Tile 1008: Arms
  - Tile 1009: Hands
  - Tile 1010: Feet

#### Texture Resolution
- **Hero**: 8K textures per UDIM tile
- **Production**: 4K textures
- **Game**: 2K textures with channel packing

#### Material Requirements
- Physically Based Rendering (PBR) workflow
- Subsurface scattering for skin
- Separate materials for:
  - Skin (with SSS profiles)
  - Muscle tissue (for medical visualization)
  - Bone (for anatomical views)
  - Connective tissue

### Rigging Specifications

#### Skeleton Structure
- 65+ bones for full articulation
- Advanced foot rig with 26 bones per foot
- Twist bones for natural deformation
- Muscle simulation bones

#### Control Systems
- IK/FK switching for all limbs
- Space switching (world/local/custom)
- Reverse foot setup
- Toe spreads and individual toe controls
- Muscle bulge controls
- Volume preservation system

### Deliverables
1. Base mesh (T-pose)
2. Sculpted high-resolution model
3. Retopologized production model
4. UV layouts
5. Texture maps (Diffuse, Normal, Displacement, etc.)
6. Rigged model with controls
7. Example animations (walk, run, medical demonstrations)
8. Documentation and style guide

### File Formats
- **Modeling**: .blend, .fbx, .obj
- **Sculpting**: .ztl, .zpr
- **Textures**: .exr, .png, .tiff
- **Production**: .usd (Universal Scene Description)

### Naming Conventions
- Model: `figure_[LOD]_v[version]`
- Textures: `figure_[part]_[type]_[resolution]`
- Rigs: `figure_rig_v[version]`

## Quality Standards
- Anatomically accurate within 95% tolerance
- Clean topology with no n-gons
- Manifold geometry (watertight)
- Consistent edge flow for deformation
- Optimized for real-time rendering where applicable

## Timeline Considerations
- Phase 1: Research and planning (1 week)
- Phase 2: Base mesh creation (2 weeks)
- Phase 3: High-res sculpting (3 weeks)
- Phase 4: Retopology and UVs (2 weeks)
- Phase 5: Rigging (3 weeks)
- Phase 6: Texturing (2 weeks)
- Phase 7: Testing and optimization (1 week)

Total estimated time: 14 weeks for full pipeline