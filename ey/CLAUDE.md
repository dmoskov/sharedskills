## Universal Instructions
See: /Users/moskov/Code/CLAUDE.md for universal coding standards

# The Masculine Mongoose Story Universe - Project Documentation

## Overview

This project is an interactive web-based storytelling platform centered around "The Masculine Mongoose" universe. It's a creative writing and world-building tool that explores themes of identity, heroism, vulnerability, and deception through an innovative narrative structure.

## Directory Structure

```
/Users/moskov/Code/ey/
├── index.html                      # Main entry point and navigation hub
├── character_relationships.html    # Interactive character relationship network
├── heroism_layers.html            # Exploration of heroism themes
├── bruce_situation_timeline.html  # Timeline of protagonist's daily reality
├── tension_map.html               # Conflict and tension visualization
├── story-generator.html           # Tool for generating story ideas
├── story-belief-mapper.html       # Maps stories to character beliefs
├── story-web.html                 # Interactive story connection visualizer
├── story-ideas.html               # Collection of story concepts
└── masculine_mongoose_story.html  # Core story content
└── mongoose_network.html          # Network visualization component
```

## Project Purpose

This is a sophisticated creative writing tool that serves multiple purposes:

1. **Narrative Development**: Provides tools for exploring complex character relationships and story dynamics
2. **World Building**: Creates an interconnected universe with detailed character networks and belief systems
3. **Theme Exploration**: Deeply examines concepts of heroism, identity, deception, and vulnerability
4. **Interactive Storytelling**: Offers various visualization tools to understand narrative connections

## Core Story Concept

The project revolves around "The Masculine Mongoose" universe, which features:

- **Bruce Kent**: A powerless volunteer who pretends to be the superhero "Masculine Mongoose"
- **The Real Mongoose (Baibhav Hegadi)**: The actual hero with a large family who needs protection
- **The Deception**: Bruce faces daily assassination attempts and isolation to protect the real hero's identity
- **The Mask Code**: A universe rule that prevents proving secret identities

## File Types and Their Roles

### 1. Main Navigation (index.html)
- **Purpose**: Central hub for the entire application
- **Features**:
  - Responsive sidebar navigation
  - Story overview and context
  - Character listings
  - Theme tags
  - Dynamic iframe loading for different views
- **Design**: Dark theme with color-coded sections (red, yellow, cyan, green accents)

### 2. Visualization Files
These files use D3.js for interactive data visualization:

- **character_relationships.html**: Network graph showing character connections
- **tension_map.html**: Visual representation of story conflicts
- **story-web.html**: Interactive web of story connections
- **mongoose_network.html**: Additional network visualization

### 3. Story Development Tools
- **story-generator.html**: Generates narrative scenarios based on character beliefs
- **story-belief-mapper.html**: Connects stories to character belief systems
- **story-ideas.html**: Repository of story concepts

### 4. Content Files
- **heroism_layers.html**: Thematic exploration of heroism
- **bruce_situation_timeline.html**: Day-in-the-life timeline
- **masculine_mongoose_story.html**: Core narrative content

## Technical Implementation

### Technologies Used
- **HTML5**: Structure and semantic markup
- **CSS3**: Styling with modern features (Grid, Flexbox, CSS Variables)
- **JavaScript**: Interactivity and dynamic content loading
- **D3.js**: Data visualization library for network graphs
- **Responsive Design**: Mobile-first approach with breakpoints

### Design Patterns
1. **Single Page Application (SPA) Pattern**: Uses iframe loading for seamless navigation
2. **Component-Based Structure**: Each HTML file is a self-contained component
3. **Dark Theme Design**: Consistent color palette across all pages
4. **Interactive Visualizations**: Click-and-explore interfaces

## Key Features

### 1. Character Network Visualization
- Interactive node-link diagrams
- Color-coded relationship types
- Dynamic exploration of character connections

### 2. Story Generation System
- Belief-based narrative generation
- Character motivation mapping
- Conflict scenario creation

### 3. Thematic Organization
- Core themes: Identity vs Truth, Vulnerability as Strength, Cost of Deception
- Visual theme tagging system
- Cross-referenced story elements

### 4. Responsive Navigation
- Collapsible sidebar for mobile devices
- Touch-friendly interface
- Persistent navigation state

## Conventions and Patterns

### Color Coding System
- **#ff6b6b (Red)**: Core deception/conflict elements
- **#4ecdc4 (Cyan)**: Protected/positive elements
- **#ffe66d (Yellow)**: Public/media elements
- **#a8e6cf (Green)**: Timeline/progression elements
- **#ff8b94 (Pink)**: Personal relationships

### File Naming Convention
- Hyphenated lowercase for multi-word files (story-generator.html)
- Underscore separation for conceptual groupings (character_relationships.html)
- Descriptive names that indicate content purpose

### Code Organization
- Inline styles and scripts for self-contained components
- Consistent indentation and formatting
- Comprehensive comments in complex sections

## User Interface Elements

### Navigation Structure
1. **Logo Section**: Project branding and tagline
2. **Story Overview**: Quick synopsis of the universe
3. **Key Facts**: Bullet-pointed critical information
4. **Navigation Links**: Categorized by purpose
5. **Character List**: Quick reference for key players
6. **Theme Tags**: Visual representation of core themes

### Interactive Elements
- Hover effects on navigation items
- Active state indicators
- Smooth transitions
- Click-to-explore visualizations

## Project Goals

1. **Creative Exploration**: Enable deep exploration of narrative possibilities
2. **Visual Understanding**: Use data visualization to understand story complexity
3. **Theme Development**: Examine philosophical questions through fiction
4. **Character Development**: Create multi-dimensional character relationships
5. **World Consistency**: Maintain coherent universe rules and logic

## Summary

This project represents a sophisticated approach to digital storytelling, combining narrative theory with interactive visualization. It's designed for writers, world-builders, and anyone interested in exploring complex themes through the lens of superhero deconstruction. The technical implementation supports both casual exploration and deep creative work, with tools that scale from simple story ideas to complex relationship networks.