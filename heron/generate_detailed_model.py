#!/usr/bin/env python3
"""
Heron Building - 7 Heron Street, San Francisco
DETAILED 3D Printable Diorama Model

Based on Boor Bridges Architecture elevation drawings A4.1
With semi-detailed arched windows and facade features

Scale: 1:200 (~90mm wide, ~45mm tall - bookshelf size)
"""

import numpy as np
from stl import mesh
import math

# === CONFIGURATION ===
SCALE = 1/200
FT = 304.8  # mm per foot

# Building dimensions from architectural drawings
MAIN_WIDTH = 50 * FT
MAIN_DEPTH = 65 * FT
REAR_WIDTH = 35 * FT
REAR_DEPTH = 18 * FT

FLOOR1_H = 14 * FT
FLOOR2_H = 11 * FT
PARAPET_H = 3 * FT
TOTAL_H = FLOOR1_H + FLOOR2_H + PARAPET_H

WALL_THICK = 1.5 * FT  # For window recesses


class MeshBuilder:
    """Helper class to build complex meshes"""

    def __init__(self):
        self.vertices = []
        self.faces = []

    def add_vertex(self, v):
        idx = len(self.vertices)
        self.vertices.append(v)
        return idx

    def add_face(self, v1, v2, v3):
        self.faces.append([v1, v2, v3])

    def add_quad(self, v1, v2, v3, v4):
        """Add a quad as two triangles"""
        self.add_face(v1, v2, v3)
        self.add_face(v1, v3, v4)

    def add_box(self, origin, size):
        """Add a box to the mesh"""
        x, y, z = origin
        w, d, h = size

        # Add 8 vertices
        v0 = self.add_vertex([x, y, z])
        v1 = self.add_vertex([x+w, y, z])
        v2 = self.add_vertex([x+w, y+d, z])
        v3 = self.add_vertex([x, y+d, z])
        v4 = self.add_vertex([x, y, z+h])
        v5 = self.add_vertex([x+w, y, z+h])
        v6 = self.add_vertex([x+w, y+d, z+h])
        v7 = self.add_vertex([x, y+d, z+h])

        # 6 faces (12 triangles)
        self.add_quad(v0, v3, v2, v1)  # bottom
        self.add_quad(v4, v5, v6, v7)  # top
        self.add_quad(v0, v1, v5, v4)  # front
        self.add_quad(v2, v3, v7, v6)  # back
        self.add_quad(v0, v4, v7, v3)  # left
        self.add_quad(v1, v2, v6, v5)  # right

    def add_arch_prism(self, x, y, z, width, height, depth, segments=12):
        """
        Add an arched prism (extruded arch shape).
        Arch is semicircle on top of rectangle.
        Extrudes along Y axis.
        """
        radius = width / 2
        rect_h = height - radius

        # Generate profile points (front face at y)
        profile = []

        # Bottom left
        profile.append([x, z])
        # Bottom right
        profile.append([x + width, z])
        # Right side up to arch start
        profile.append([x + width, z + rect_h])

        # Arch from right to left
        cx = x + radius
        cz = z + rect_h
        for i in range(segments + 1):
            angle = math.pi * (1 - i / segments)  # 0 to pi
            px = cx + radius * math.cos(angle)
            pz = cz + radius * math.sin(angle)
            profile.append([px, pz])

        # Left side down
        profile.append([x, z + rect_h])

        n = len(profile)

        # Front face vertices
        front_verts = []
        for p in profile:
            front_verts.append(self.add_vertex([p[0], y, p[1]]))

        # Back face vertices
        back_verts = []
        for p in profile:
            back_verts.append(self.add_vertex([p[0], y + depth, p[1]]))

        # Front face (fan from center)
        center_front = self.add_vertex([x + width/2, y, z + height/2])
        for i in range(n):
            self.add_face(center_front, front_verts[i], front_verts[(i+1) % n])

        # Back face (fan from center, reversed winding)
        center_back = self.add_vertex([x + width/2, y + depth, z + height/2])
        for i in range(n):
            self.add_face(center_back, back_verts[(i+1) % n], back_verts[i])

        # Side faces (connecting front to back)
        for i in range(n):
            i_next = (i + 1) % n
            self.add_quad(front_verts[i], front_verts[i_next],
                         back_verts[i_next], back_verts[i])

    def to_stl_mesh(self):
        """Convert to numpy-stl mesh"""
        vertices = np.array(self.vertices)
        faces = np.array(self.faces)

        stl_mesh = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
        for i, f in enumerate(faces):
            for j in range(3):
                stl_mesh.vectors[i][j] = vertices[f[j]]

        return stl_mesh


def build_main_structure(mb):
    """Build the L-shaped building mass"""

    # Main block
    mb.add_box((0, 0, 0), (MAIN_WIDTH, MAIN_DEPTH, TOTAL_H))

    # Rear extension
    mb.add_box(
        (MAIN_WIDTH - REAR_WIDTH, MAIN_DEPTH, 0),
        (REAR_WIDTH, REAR_DEPTH, TOTAL_H)
    )


def build_south_facade_details(mb):
    """
    Build south (street) facade with arched windows.
    Based on elevation A4.1 - "Elevation Looking South"
    """

    facade_y = -0.3 * FT  # Slight projection for detail

    # === GROUND FLOOR - Large arched openings ===
    # Drawing shows 4 large arches with overhead door on right

    # Arch 1-3: Large display windows
    for i in range(3):
        x = 2*FT + i * 13*FT
        # Window recess (darker area)
        mb.add_arch_prism(
            x + 0.5*FT, facade_y, 1*FT,
            width=10*FT, height=12*FT, depth=0.8*FT,
            segments=16
        )
        # Window frame (raised border)
        mb.add_box((x, facade_y - 0.15*FT, 0.5*FT), (11*FT, 0.3*FT, 0.5*FT))

    # Arch 4: Entry with transom
    x = 41*FT
    mb.add_arch_prism(
        x, facade_y, 1*FT,
        width=7*FT, height=10*FT, depth=0.8*FT,
        segments=16
    )

    # === OVERHEAD DOOR (right side) ===
    door_x = MAIN_WIDTH - 12*FT
    mb.add_box((door_x, facade_y, 0), (10*FT, 0.6*FT, 11*FT))

    # === SECOND FLOOR - Smaller arched windows ===
    # 5 evenly spaced arched windows
    for i in range(5):
        x = 3*FT + i * 9.5*FT
        mb.add_arch_prism(
            x, facade_y, FLOOR1_H + 1*FT,
            width=6*FT, height=8*FT, depth=0.6*FT,
            segments=12
        )

    # === CORNICE / PARAPET DETAIL ===
    cornice_z = FLOOR1_H + FLOOR2_H - 1*FT

    # Main cornice band
    mb.add_box((-0.5*FT, facade_y - 0.8*FT, cornice_z),
               (MAIN_WIDTH + 1*FT, 1.2*FT, 1.2*FT))

    # Upper cornice
    mb.add_box((-0.3*FT, facade_y - 0.5*FT, cornice_z + 1.5*FT),
               (MAIN_WIDTH + 0.6*FT, 0.8*FT, 0.8*FT))

    # Parapet cap
    mb.add_box((-0.2*FT, facade_y - 0.3*FT, TOTAL_H - 0.5*FT),
               (MAIN_WIDTH + 0.4*FT, 0.6*FT, 0.6*FT))


def build_west_facade_details(mb):
    """West facade - simpler treatment with arched windows"""

    facade_x = -0.3 * FT

    # Ground floor windows (3 large arched)
    for i in range(3):
        y = 10*FT + i * 18*FT
        # Window recess
        mb.add_box((facade_x, y, 2*FT), (0.6*FT, 8*FT, 9*FT))

    # Second floor windows
    for i in range(4):
        y = 8*FT + i * 14*FT
        mb.add_box((facade_x, y, FLOOR1_H + 1.5*FT), (0.5*FT, 5*FT, 6*FT))

    # Cornice return
    mb.add_box((facade_x - 0.3*FT, 0, FLOOR1_H + FLOOR2_H - 1*FT),
               (0.8*FT, MAIN_DEPTH, 0.8*FT))


def build_east_facade_details(mb):
    """East facade - similar to west"""

    facade_x = MAIN_WIDTH

    # Ground floor windows
    for i in range(3):
        y = 10*FT + i * 18*FT
        mb.add_box((facade_x - 0.2*FT, y, 2*FT), (0.6*FT, 8*FT, 9*FT))

    # Second floor windows
    for i in range(4):
        y = 8*FT + i * 14*FT
        mb.add_box((facade_x - 0.2*FT, y, FLOOR1_H + 1.5*FT), (0.5*FT, 5*FT, 6*FT))

    # Cornice
    mb.add_box((facade_x, 0, FLOOR1_H + FLOOR2_H - 1*FT),
               (0.6*FT, MAIN_DEPTH, 0.8*FT))


def build_roof_details(mb):
    """Skylights, hatch, and mechanical equipment"""

    roof_z = TOTAL_H

    # Skylights (from roof plan A2.6)
    # 6 skylights in 2x3 grid
    for i in range(2):
        for j in range(3):
            x = 10*FT + i * 16*FT
            y = 14*FT + j * 15*FT
            # Skylight curb
            mb.add_box((x, y, roof_z), (5*FT, 7*FT, 0.8*FT))

    # Roof hatch with motorized cover (detail from A7.1)
    hatch_x = MAIN_WIDTH - 20*FT
    hatch_y = MAIN_DEPTH - 15*FT
    # Hatch structure
    mb.add_box((hatch_x, hatch_y, roof_z), (10*FT, 10*FT, 3*FT))
    # Track rails
    mb.add_box((hatch_x - 1*FT, hatch_y + 2*FT, roof_z + 3*FT),
               (12*FT, 0.5*FT, 1*FT))
    mb.add_box((hatch_x - 1*FT, hatch_y + 7.5*FT, roof_z + 3*FT),
               (12*FT, 0.5*FT, 1*FT))

    # Future PV panel area marker (subtle)
    mb.add_box((5*FT, 5*FT, roof_z), (20*FT, 25*FT, 0.2*FT))


def build_base_plate(mb):
    """Display base"""
    margin = 3*FT
    thickness = 1.5*FT

    mb.add_box(
        (-margin, -margin - 2*FT, -thickness),
        (MAIN_WIDTH + margin*2,
         MAIN_DEPTH + REAR_DEPTH + margin*2 + 2*FT,
         thickness)
    )

    # Street indication (subtle raised line)
    mb.add_box((-margin, -margin - 2*FT, 0),
               (MAIN_WIDTH + margin*2, 1*FT, 0.3*FT))


def main():
    print("=" * 50)
    print("Heron Building - Detailed 3D Model Generator")
    print("7 Heron Street, San Francisco")
    print("=" * 50)
    print(f"\nScale: 1:{int(1/SCALE)}")

    mb = MeshBuilder()

    print("\nBuilding model...")
    print("  [1/6] Main structure...")
    build_main_structure(mb)

    print("  [2/6] South facade (arched windows)...")
    build_south_facade_details(mb)

    print("  [3/6] West facade...")
    build_west_facade_details(mb)

    print("  [4/6] East facade...")
    build_east_facade_details(mb)

    print("  [5/6] Roof details...")
    build_roof_details(mb)

    print("  [6/6] Base plate...")
    build_base_plate(mb)

    print("\nConverting to STL mesh...")
    stl_mesh = mb.to_stl_mesh()

    # Apply scale
    stl_mesh.vectors *= SCALE

    # Get dimensions
    mins = stl_mesh.vectors.min(axis=(0, 1))
    maxs = stl_mesh.vectors.max(axis=(0, 1))
    dims = maxs - mins

    print(f"\n{'='*50}")
    print("FINAL MODEL DIMENSIONS:")
    print(f"  Width:  {dims[0]:.1f}mm ({dims[0]/25.4:.2f} inches)")
    print(f"  Depth:  {dims[1]:.1f}mm ({dims[1]/25.4:.2f} inches)")
    print(f"  Height: {dims[2]:.1f}mm ({dims[2]/25.4:.2f} inches)")
    print(f"{'='*50}")

    # Save
    output = "heron_detailed.stl"
    stl_mesh.save(output)
    print(f"\nSaved: {output}")

    # Version without base
    mb_no_base = MeshBuilder()
    build_main_structure(mb_no_base)
    build_south_facade_details(mb_no_base)
    build_west_facade_details(mb_no_base)
    build_east_facade_details(mb_no_base)
    build_roof_details(mb_no_base)

    stl_no_base = mb_no_base.to_stl_mesh()
    stl_no_base.vectors *= SCALE
    stl_no_base.save("heron_detailed_no_base.stl")
    print("Saved: heron_detailed_no_base.stl")

    print(f"\n{'='*50}")
    print("BAMBU A1 PRINT SETTINGS:")
    print("  Layer Height: 0.12mm (detail) or 0.16mm (faster)")
    print("  Infill: 15%")
    print("  Wall Loops: 3")
    print("  Top Layers: 4")
    print("  Supports: None needed")
    print("  Estimated Time: ~2-3 hours")
    print("  Estimated Filament: ~15-20g")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
