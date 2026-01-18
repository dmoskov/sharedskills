# 3D Figure Design Application

A web-based 3D figure design application with specialized anatomical leg mapping capabilities, built for medical visualization, animation, and educational purposes.

## Overview

This application provides an interactive 3D visualization system for human anatomy with a specific focus on accurate leg structure and muscle systems. It's designed to serve medical professionals, animators, and educators who need detailed anatomical references.

## Features

- **Multiple View Modes**
  - Skin surface view
  - Muscle system visualization
  - Skeletal system display
  - Combined transparent view

- **Interactive Controls**
  - Orbit camera controls
  - Muscle group toggling
  - Individual muscle highlighting
  - Opacity controls

- **Anatomical Accuracy**
  - Based on medical references
  - Accurate proportions (8-head system)
  - Detailed leg muscle groups
  - Proper bone structure

- **Technical Capabilities**
  - WebGL-based rendering
  - Real-time performance
  - Responsive design
  - Export capabilities (planned)

## Technology Stack

- **Framework**: React 18 with TypeScript
- **3D Engine**: Three.js with React Three Fiber
- **UI Controls**: Leva for parameter tweaking
- **State Management**: Zustand
- **Build Tool**: Vite
- **Styling**: CSS Modules

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Modern web browser with WebGL support
- 4GB+ RAM recommended

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/3d-figure-design.git
cd 3d-figure-design

# Install dependencies
npm install

# Start development server
npm run dev
```

The application will be available at `http://localhost:3000`

### Building for Production

```bash
# Create production build
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
3d-figure-design/
├── src/
│   ├── components/       # React components
│   │   ├── Scene.tsx    # Main 3D scene
│   │   ├── FigureModel.tsx
│   │   ├── MuscleSystem.tsx
│   │   └── SkeletonSystem.tsx
│   ├── store/           # State management
│   ├── hooks/           # Custom React hooks
│   ├── utils/           # Helper functions
│   └── assets/          # 3D models and textures
├── docs/                # Documentation
│   ├── FIGURE_SPECIFICATIONS.md
│   ├── ANATOMICAL_LEG_REFERENCES.md
│   └── TECHNICAL_SPECIFICATIONS.md
└── public/              # Static assets
```

## Usage Guide

### View Modes

1. **Skin View**: Shows the external surface of the figure
2. **Muscle View**: Displays major muscle groups with toggle controls
3. **Skeleton View**: Shows bone structure and joints
4. **Combined View**: Transparent overlay of all systems

### Controls

- **Left Mouse**: Rotate camera
- **Right Mouse**: Pan camera
- **Scroll**: Zoom in/out
- **UI Panel**: Toggle muscle groups, adjust opacity

### Muscle Groups

The application includes these leg muscle groups:
- Quadriceps (front thigh)
- Hamstrings (back thigh)
- Calves (gastrocnemius)
- Glutes
- Adductors (inner thigh)
- Tibialis Anterior (shin)

## Development

### Adding New Models

1. Place 3D model files in `src/assets/models/`
2. Import using Three.js loaders
3. Create component wrapper in `src/components/`

### Customizing Materials

Edit material properties in component files:
```typescript
<meshStandardMaterial 
  color="#fdbcb4" 
  roughness={0.7}
  metalness={0.1}
/>
```

### State Management

Global state is managed with Zustand:
```typescript
const { viewMode, setViewMode } = useStore()
```

## Specifications

### Model Requirements
- **Hero Model**: 500k-1M polygons
- **Production**: 50k-100k polygons
- **Real-time**: 2k-20k polygons

### UV Layout (UDIM)
- 1001: Head
- 1002-1003: Torso
- 1004-1007: Legs (dedicated tiles)
- 1008-1010: Arms, hands, feet

### Performance Targets
- 60 FPS on modern hardware
- 30 FPS on mobile devices
- <3 second initial load time

## Future Enhancements

- [ ] Load external 3D models (FBX, OBJ)
- [ ] Animation system with walk/run cycles
- [ ] Advanced rigging controls
- [ ] Texture painting interface
- [ ] VR/AR support
- [ ] Export to common 3D formats
- [ ] Measurement tools
- [ ] Annotation system
- [ ] Multi-language support

## Documentation

Detailed documentation is available in the `/docs` directory:
- [Figure Specifications](docs/FIGURE_SPECIFICATIONS.md)
- [Anatomical References](docs/ANATOMICAL_LEG_REFERENCES.md)
- [Technical Pipeline](docs/TECHNICAL_SPECIFICATIONS.md)

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Anatomical references from medical literature
- Three.js community for excellent documentation
- React Three Fiber team for the amazing abstraction layer

## Contact

Project created by Dustin Moskovitz

For questions or support, please open an issue on GitHub.