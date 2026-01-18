#!/usr/bin/env python3
"""
Heron Building - Interior Diorama Model
7 Heron Street, San Francisco

Creates a detailed diorama with:
- Exterior walls with windows
- Interior partition walls
- Stairs
- Floor plates
- Separate colored parts for multi-color printing

Based on architectural drawings:
- A2.2: First Floor Proposed
- A2.4: Second Floor Proposed
- A7.1: Stair Details

Scale: 1:200
"""

import numpy as np
from stl import mesh
import math
import zipfile
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

# === CONFIGURATION ===
SCALE = 1/200
FT = 304.8  # mm per foot
INCH = 25.4

# Building dimensions
MAIN_WIDTH = 50 * FT
MAIN_DEPTH = 65 * FT
REAR_WIDTH = 35 * FT
REAR_DEPTH = 18 * FT

FLOOR1_H = 14 * FT
FLOOR2_H = 11 * FT
PARAPET_H = 3 * FT
TOTAL_H = FLOOR1_H + FLOOR2_H + PARAPET_H

# Wall thicknesses
EXT_WALL = 1 * FT      # Exterior wall thickness
INT_WALL = 0.5 * FT    # Interior partition
FLOOR_THICK = 0.8 * FT # Floor slab thickness

# Colors (RGB 0-1)
COLORS = {
    'brick': (0.72, 0.45, 0.32),      # Exterior brick
    'concrete': (0.75, 0.75, 0.73),   # Floor slabs
    'white_wall': (0.95, 0.95, 0.93), # Interior walls
    'wood_floor': (0.76, 0.60, 0.42), # Wood flooring
    'glass': (0.7, 0.85, 0.9),        # Windows/skylights
    'metal': (0.5, 0.5, 0.55),        # Stairs, railings
    'wood_stair': (0.6, 0.45, 0.3),   # Stair treads
    'base': (0.3, 0.3, 0.3),          # Display base
}


class MeshBuilder:
    """Build mesh geometry"""

    def __init__(self):
        self.vertices = []
        self.faces = []

    def add_vertex(self, v):
        idx = len(self.vertices)
        self.vertices.append(list(v))
        return idx

    def add_face(self, v1, v2, v3):
        self.faces.append([v1, v2, v3])

    def add_quad(self, v1, v2, v3, v4):
        self.add_face(v1, v2, v3)
        self.add_face(v1, v3, v4)

    def add_box(self, origin, size):
        x, y, z = origin
        w, d, h = size
        if w <= 0 or d <= 0 or h <= 0:
            return

        v = [
            self.add_vertex([x, y, z]),
            self.add_vertex([x+w, y, z]),
            self.add_vertex([x+w, y+d, z]),
            self.add_vertex([x, y+d, z]),
            self.add_vertex([x, y, z+h]),
            self.add_vertex([x+w, y, z+h]),
            self.add_vertex([x+w, y+d, z+h]),
            self.add_vertex([x, y+d, z+h]),
        ]

        self.add_quad(v[0], v[3], v[2], v[1])  # bottom
        self.add_quad(v[4], v[5], v[6], v[7])  # top
        self.add_quad(v[0], v[1], v[5], v[4])  # front
        self.add_quad(v[2], v[3], v[7], v[6])  # back
        self.add_quad(v[0], v[4], v[7], v[3])  # left
        self.add_quad(v[1], v[2], v[6], v[5])  # right

    def add_wall_with_opening(self, x, y, z, length, height, thickness,
                               opening_start, opening_width, opening_height,
                               opening_z=0, horizontal=True):
        """Add a wall with a door/window opening"""
        if horizontal:  # Wall runs along X axis
            # Left section
            if opening_start > 0:
                self.add_box((x, y, z), (opening_start, thickness, height))
            # Right section
            right_start = opening_start + opening_width
            if right_start < length:
                self.add_box((x + right_start, y, z),
                           (length - right_start, thickness, height))
            # Above opening
            if opening_z + opening_height < height:
                self.add_box((x + opening_start, y, z + opening_z + opening_height),
                           (opening_width, thickness, height - opening_z - opening_height))
            # Below opening (if opening doesn't start at floor)
            if opening_z > 0:
                self.add_box((x + opening_start, y, z),
                           (opening_width, thickness, opening_z))
        else:  # Wall runs along Y axis
            if opening_start > 0:
                self.add_box((x, y, z), (thickness, opening_start, height))
            right_start = opening_start + opening_width
            if right_start < length:
                self.add_box((x, y + right_start, z),
                           (thickness, length - right_start, height))
            if opening_z + opening_height < height:
                self.add_box((x, y + opening_start, z + opening_z + opening_height),
                           (thickness, opening_width, height - opening_z - opening_height))
            if opening_z > 0:
                self.add_box((x, y + opening_start, z),
                           (thickness, opening_width, opening_z))

    def to_stl(self):
        vertices = np.array(self.vertices)
        faces = np.array(self.faces)
        stl_mesh = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
        for i, f in enumerate(faces):
            for j in range(3):
                stl_mesh.vectors[i][j] = vertices[f[j]]
        return stl_mesh


def build_exterior_walls():
    """Build exterior walls with window openings"""
    mb = MeshBuilder()

    # South wall (street facade) with arched openings
    # Large openings at ground floor
    y = 0

    # Ground floor - series of large openings
    # Section 1: Left of windows
    mb.add_box((0, y, 0), (2*FT, EXT_WALL, FLOOR1_H))

    # Piers between windows
    for i in range(4):
        pier_x = 2*FT + i*12*FT + 10*FT
        mb.add_box((pier_x, y, 0), (2*FT, EXT_WALL, FLOOR1_H))

    # Above ground floor openings
    mb.add_box((0, y, 11*FT), (MAIN_WIDTH, EXT_WALL, 3*FT))

    # Second floor with windows
    for i in range(6):
        # Piers
        pier_x = i * 8.5*FT
        mb.add_box((pier_x, y, FLOOR1_H), (2*FT, EXT_WALL, FLOOR2_H))
    mb.add_box((MAIN_WIDTH - 2*FT, y, FLOOR1_H), (2*FT, EXT_WALL, FLOOR2_H))

    # Parapet
    mb.add_box((0, y, FLOOR1_H + FLOOR2_H), (MAIN_WIDTH, EXT_WALL, PARAPET_H))

    # North wall (back)
    north_y = MAIN_DEPTH - EXT_WALL
    mb.add_box((0, north_y, 0), (MAIN_WIDTH - REAR_WIDTH, EXT_WALL, TOTAL_H))

    # North wall of rear extension
    mb.add_box((MAIN_WIDTH - REAR_WIDTH, MAIN_DEPTH + REAR_DEPTH - EXT_WALL, 0),
              (REAR_WIDTH, EXT_WALL, TOTAL_H))

    # West wall
    mb.add_box((0, 0, 0), (EXT_WALL, MAIN_DEPTH, TOTAL_H))

    # East wall (main section)
    mb.add_box((MAIN_WIDTH - EXT_WALL, 0, 0), (EXT_WALL, MAIN_DEPTH, TOTAL_H))

    # East wall of rear extension
    mb.add_box((MAIN_WIDTH - EXT_WALL, MAIN_DEPTH, 0),
              (EXT_WALL, REAR_DEPTH, TOTAL_H))

    # West wall of rear extension (interior becomes exterior)
    mb.add_box((MAIN_WIDTH - REAR_WIDTH - EXT_WALL, MAIN_DEPTH, 0),
              (EXT_WALL, REAR_DEPTH, TOTAL_H))

    return mb


def build_first_floor_interior():
    """
    Build first floor interior walls based on A2.2

    Layout (from south to north):
    - Patio area (southwest)
    - Kitchenette (west side)
    - ADA RR (west side)
    - Communal RR (northwest)
    - Work rooms (east side, open)
    - Storage (northeast)
    """
    mb = MeshBuilder()
    z = 0
    h = FLOOR1_H - FLOOR_THICK  # Wall height (floor to ceiling)

    # === RESTROOM BLOCK (northwest corner) ===
    # West wall of RR block
    rr_x = 3 * FT
    rr_y = 35 * FT
    rr_width = 18 * FT
    rr_depth = 25 * FT

    # East wall of restroom block
    mb.add_wall_with_opening(rr_x + rr_width, rr_y, z,
                            rr_depth, h, INT_WALL,
                            5*FT, 3*FT, 7*FT, 0, horizontal=False)

    # South wall of restroom block (with door to kitchenette)
    mb.add_wall_with_opening(rr_x, rr_y, z,
                            rr_width, h, INT_WALL,
                            rr_width - 4*FT, 3*FT, 7*FT, 0, horizontal=True)

    # Divider between communal RR and ADA RR
    mb.add_box((rr_x, rr_y + 12*FT, z), (rr_width, INT_WALL, h))

    # RR stall partitions (communal RR)
    for i in range(4):
        stall_y = rr_y + 14*FT + i * 3*FT
        mb.add_box((rr_x + 2*FT, stall_y, z), (5*FT, INT_WALL*0.5, 6*FT))

    # === KITCHENETTE (southwest, adjacent to patio) ===
    kitchen_x = 3 * FT
    kitchen_y = 20 * FT

    # East wall of kitchenette
    mb.add_wall_with_opening(kitchen_x + 15*FT, kitchen_y, z,
                            15*FT, h, INT_WALL,
                            5*FT, 4*FT, 7*FT, 0, horizontal=False)

    # North wall of kitchenette (connects to RR)
    mb.add_box((kitchen_x, kitchen_y + 15*FT - INT_WALL, z),
              (15*FT, INT_WALL, h))

    # Kitchen counter (low wall)
    mb.add_box((kitchen_x + 1*FT, kitchen_y + 2*FT, z), (12*FT, 2*FT, 3*FT))

    # === STORAGE ROOM (east side) ===
    storage_x = 35 * FT
    storage_y = 45 * FT

    # West wall of storage
    mb.add_wall_with_opening(storage_x, storage_y, z,
                            15*FT, h, INT_WALL,
                            2*FT, 4*FT, 7*FT, 0, horizontal=False)

    # South wall of storage
    mb.add_box((storage_x, storage_y, z), (12*FT, INT_WALL, h))

    return mb


def build_second_floor_interior():
    """
    Build second floor interior walls based on A2.4

    Layout:
    - Entry/stair area (southwest)
    - Kitchenette (west)
    - Break room with banquette (center-west)
    - Work room (center, double height section)
    - Private office (east)
    - Storage areas
    - Bath (east)
    """
    mb = MeshBuilder()
    z = FLOOR1_H
    h = FLOOR2_H - FLOOR_THICK

    # === ENTRY VESTIBULE (southwest) ===
    entry_x = 3 * FT
    entry_y = 3 * FT

    # East wall of entry (with door)
    mb.add_wall_with_opening(entry_x + 12*FT, entry_y, z,
                            15*FT, h, INT_WALL,
                            5*FT, 4*FT, 7*FT, 0, horizontal=False)

    # === KITCHENETTE (west side) ===
    kit_x = 3 * FT
    kit_y = 25 * FT

    # Counter/peninsula
    mb.add_box((kit_x + 2*FT, kit_y, z), (8*FT, 3*FT, 3*FT))

    # === BREAK ROOM / DINING (center) ===
    # Banquette seating (built-in bench along wall)
    mb.add_box((15*FT, 3*FT, z), (15*FT, 2*FT, 1.5*FT))

    # === PRIVATE OFFICE (east side) ===
    office_x = 32 * FT
    office_y = 25 * FT

    # West wall of office
    mb.add_wall_with_opening(office_x, office_y, z,
                            20*FT, h, INT_WALL,
                            3*FT, 4*FT, 7*FT, 0, horizontal=False)

    # South wall of office
    mb.add_wall_with_opening(office_x, office_y, z,
                            15*FT, h, INT_WALL,
                            8*FT, 3*FT, 7*FT, 0, horizontal=True)

    # === BATH (east, behind office) ===
    bath_x = 40 * FT
    bath_y = 50 * FT

    # West wall of bath
    mb.add_box((bath_x, bath_y, z), (INT_WALL, 10*FT, h))

    # South wall of bath
    mb.add_wall_with_opening(bath_x, bath_y, z,
                            8*FT, h, INT_WALL,
                            1*FT, 2.5*FT, 7*FT, 0, horizontal=True)

    # Bathtub outline
    mb.add_box((bath_x + 1*FT, bath_y + 1*FT, z), (5*FT, 2.5*FT, 2*FT))

    # === STORAGE CLOSETS ===
    # North storage
    mb.add_box((3*FT, 55*FT, z), (10*FT, INT_WALL, h))

    return mb


def build_floor_plates():
    """Build floor slabs"""
    mb = MeshBuilder()

    # First floor slab (ground level)
    mb.add_box((0, 0, -FLOOR_THICK), (MAIN_WIDTH, MAIN_DEPTH, FLOOR_THICK))
    mb.add_box((MAIN_WIDTH - REAR_WIDTH, MAIN_DEPTH, -FLOOR_THICK),
              (REAR_WIDTH, REAR_DEPTH, FLOOR_THICK))

    # Second floor slab
    # Main area (with cutout for double-height space)
    # West portion
    mb.add_box((0, 0, FLOOR1_H - FLOOR_THICK),
              (25*FT, MAIN_DEPTH, FLOOR_THICK))
    # East portion
    mb.add_box((25*FT, 35*FT, FLOOR1_H - FLOOR_THICK),
              (MAIN_WIDTH - 25*FT, MAIN_DEPTH - 35*FT, FLOOR_THICK))
    # South portion
    mb.add_box((25*FT, 0, FLOOR1_H - FLOOR_THICK),
              (MAIN_WIDTH - 25*FT, 35*FT, FLOOR_THICK))

    # Rear extension second floor
    mb.add_box((MAIN_WIDTH - REAR_WIDTH, MAIN_DEPTH, FLOOR1_H - FLOOR_THICK),
              (REAR_WIDTH, REAR_DEPTH, FLOOR_THICK))

    # Roof slab
    mb.add_box((0, 0, TOTAL_H - FLOOR_THICK),
              (MAIN_WIDTH, MAIN_DEPTH, FLOOR_THICK))
    mb.add_box((MAIN_WIDTH - REAR_WIDTH, MAIN_DEPTH, TOTAL_H - FLOOR_THICK),
              (REAR_WIDTH, REAR_DEPTH, FLOOR_THICK))

    return mb


def build_stairs():
    """
    Build the feature stair from A7.1
    Open tread stair with wood treads
    """
    mb = MeshBuilder()

    # Stair location (based on floor plans - southwest area)
    stair_x = 5 * FT
    stair_y = 5 * FT

    # Stair dimensions
    tread_depth = 10 * INCH
    tread_width = 4 * FT
    tread_thick = 1.5 * INCH
    riser_height = 7.5 * INCH

    num_treads = int(FLOOR1_H / riser_height)

    # Treads (open riser - no solid risers)
    for i in range(num_treads):
        tread_z = i * riser_height
        tread_y = stair_y + i * tread_depth
        mb.add_box((stair_x, tread_y, tread_z),
                  (tread_width, tread_depth, tread_thick))

    # Stringers (side supports)
    stringer_width = 1 * INCH
    stringer_height = 2 * FT
    total_run = num_treads * tread_depth

    # Left stringer
    for i in range(num_treads):
        seg_z = i * riser_height
        seg_y = stair_y + i * tread_depth
        mb.add_box((stair_x - stringer_width, seg_y, seg_z),
                  (stringer_width, tread_depth, riser_height + tread_thick))

    # Right stringer
    for i in range(num_treads):
        seg_z = i * riser_height
        seg_y = stair_y + i * tread_depth
        mb.add_box((stair_x + tread_width, seg_y, seg_z),
                  (stringer_width, tread_depth, riser_height + tread_thick))

    # Handrail posts
    post_size = 1.5 * INCH
    rail_height = 3 * FT
    for i in range(0, num_treads, 3):
        post_z = i * riser_height
        post_y = stair_y + i * tread_depth
        # Left post
        mb.add_box((stair_x - post_size, post_y, post_z),
                  (post_size, post_size, rail_height))
        # Right post
        mb.add_box((stair_x + tread_width, post_y, post_z),
                  (post_size, post_size, rail_height))

    return mb


def build_skylights():
    """Build raised skylight curbs"""
    mb = MeshBuilder()

    roof_z = TOTAL_H
    curb_h = 1 * FT

    # Skylights based on roof plan
    positions = [
        (10*FT, 15*FT, 5*FT, 7*FT),
        (10*FT, 30*FT, 5*FT, 7*FT),
        (10*FT, 45*FT, 5*FT, 7*FT),
        (25*FT, 15*FT, 5*FT, 7*FT),
        (25*FT, 30*FT, 5*FT, 7*FT),
        (25*FT, 45*FT, 5*FT, 7*FT),
    ]

    for x, y, w, d in positions:
        # Curb frame
        mb.add_box((x, y, roof_z), (w, d, curb_h))
        # Glazing (slightly inset and raised)
        mb.add_box((x + 0.3*FT, y + 0.3*FT, roof_z + curb_h),
                  (w - 0.6*FT, d - 0.6*FT, 0.2*FT))

    return mb


def build_base():
    """Display base"""
    mb = MeshBuilder()
    margin = 3 * FT

    mb.add_box((-margin, -margin, -2*FT),
              (MAIN_WIDTH + margin*2, MAIN_DEPTH + REAR_DEPTH + margin*2, 2*FT))

    # Street markings
    mb.add_box((-margin, -margin - 1*FT, 0),
              (MAIN_WIDTH + margin*2, 1*FT, 0.2*FT))

    return mb


def save_stl(mesh_builder, filename, scale=SCALE):
    """Save mesh as STL file"""
    stl = mesh_builder.to_stl()
    stl.vectors *= scale
    stl.save(filename)
    return filename


def create_3mf(parts, output_file, scale=SCALE):
    """
    Create a 3MF file with multiple colored parts.

    parts: list of (mesh_builder, name, color_rgb) tuples
    """

    # Create 3MF structure
    # 3MF is a ZIP file with XML content

    # Build the model XML
    model = ET.Element('model')
    model.set('unit', 'millimeter')
    model.set('xmlns', 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02')
    model.set('xmlns:m', 'http://schemas.microsoft.com/3dmanufacturing/material/2015/02')

    resources = ET.SubElement(model, 'resources')
    build = ET.SubElement(model, 'build')

    # Add color materials
    basematerials = ET.SubElement(resources, 'm:basematerials')
    basematerials.set('id', '1')

    color_map = {}
    for i, (_, name, color) in enumerate(parts):
        base = ET.SubElement(basematerials, 'm:base')
        base.set('name', name)
        r, g, b = [int(c * 255) for c in color]
        base.set('displaycolor', f'#{r:02X}{g:02X}{b:02X}')
        color_map[name] = i

    # Add mesh objects
    for obj_id, (mb, name, color) in enumerate(parts, start=2):
        stl = mb.to_stl()
        stl.vectors *= scale

        obj = ET.SubElement(resources, 'object')
        obj.set('id', str(obj_id))
        obj.set('name', name)
        obj.set('type', 'model')
        obj.set('pid', '1')  # Reference to basematerials
        obj.set('pindex', str(color_map[name]))

        mesh_elem = ET.SubElement(obj, 'mesh')
        vertices_elem = ET.SubElement(mesh_elem, 'vertices')
        triangles_elem = ET.SubElement(mesh_elem, 'triangles')

        # Get unique vertices and build index map
        vertex_list = []
        vertex_map = {}

        for face in stl.vectors:
            for vertex in face:
                v_tuple = tuple(vertex)
                if v_tuple not in vertex_map:
                    vertex_map[v_tuple] = len(vertex_list)
                    vertex_list.append(vertex)

        # Add vertices
        for v in vertex_list:
            vert = ET.SubElement(vertices_elem, 'vertex')
            vert.set('x', f'{v[0]:.6f}')
            vert.set('y', f'{v[1]:.6f}')
            vert.set('z', f'{v[2]:.6f}')

        # Add triangles
        for face in stl.vectors:
            tri = ET.SubElement(triangles_elem, 'triangle')
            tri.set('v1', str(vertex_map[tuple(face[0])]))
            tri.set('v2', str(vertex_map[tuple(face[1])]))
            tri.set('v3', str(vertex_map[tuple(face[2])]))

        # Add to build
        item = ET.SubElement(build, 'item')
        item.set('objectid', str(obj_id))

    # Pretty print XML
    xml_str = ET.tostring(model, encoding='unicode')

    # Create 3MF (ZIP) file
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Content types
        content_types = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>'''
        zf.writestr('[Content_Types].xml', content_types)

        # Relationships
        rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>'''
        zf.writestr('_rels/.rels', rels)

        # Model
        zf.writestr('3D/3dmodel.model', '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str)

    return output_file


def main():
    print("=" * 60)
    print("Heron Building - Interior Diorama Generator")
    print("7 Heron Street, San Francisco")
    print("=" * 60)
    print(f"\nScale: 1:{int(1/SCALE)}")

    # Build all parts
    print("\nBuilding components...")

    print("  [1/7] Exterior walls...")
    exterior = build_exterior_walls()

    print("  [2/7] First floor interior...")
    floor1_interior = build_first_floor_interior()

    print("  [3/7] Second floor interior...")
    floor2_interior = build_second_floor_interior()

    print("  [4/7] Floor plates...")
    floors = build_floor_plates()

    print("  [5/7] Stairs...")
    stairs = build_stairs()

    print("  [6/7] Skylights...")
    skylights = build_skylights()

    print("  [7/7] Display base...")
    base = build_base()

    # Save individual STL files (for separate printing/painting)
    print("\nSaving individual STL files...")

    stl_files = [
        (exterior, "heron_exterior_walls.stl", COLORS['brick']),
        (floor1_interior, "heron_floor1_interior.stl", COLORS['white_wall']),
        (floor2_interior, "heron_floor2_interior.stl", COLORS['white_wall']),
        (floors, "heron_floor_plates.stl", COLORS['concrete']),
        (stairs, "heron_stairs.stl", COLORS['wood_stair']),
        (skylights, "heron_skylights.stl", COLORS['glass']),
        (base, "heron_base.stl", COLORS['base']),
    ]

    for mb, filename, _ in stl_files:
        save_stl(mb, filename)
        print(f"  Saved: {filename}")

    # Create combined STL
    print("\nCreating combined model...")
    combined = MeshBuilder()
    for mb, _, _ in stl_files:
        for v in mb.vertices:
            combined.vertices.append(v)
        offset = len(combined.vertices) - len(mb.vertices)
        for f in mb.faces:
            combined.faces.append([f[0] + offset, f[1] + offset, f[2] + offset])

    # Fix: rebuild combined properly
    combined = MeshBuilder()
    vertex_offset = 0
    for mb, _, _ in stl_files:
        base_offset = len(combined.vertices)
        for v in mb.vertices:
            combined.add_vertex(v)
        for f in mb.faces:
            combined.add_face(f[0] + base_offset, f[1] + base_offset, f[2] + base_offset)

    save_stl(combined, "heron_diorama_combined.stl")
    print("  Saved: heron_diorama_combined.stl")

    # Create 3MF with colors
    print("\nCreating colored 3MF file...")
    parts = [(mb, name.replace("heron_", "").replace(".stl", ""), color)
             for mb, name, color in stl_files]
    create_3mf(parts, "heron_diorama.3mf")
    print("  Saved: heron_diorama.3mf")

    # Calculate dimensions
    stl = combined.to_stl()
    stl.vectors *= SCALE
    dims = stl.vectors.max(axis=(0,1)) - stl.vectors.min(axis=(0,1))

    print(f"\n{'=' * 60}")
    print("FINAL DIMENSIONS:")
    print(f"  Width:  {dims[0]:.1f}mm ({dims[0]/25.4:.2f}\")")
    print(f"  Depth:  {dims[1]:.1f}mm ({dims[1]/25.4:.2f}\")")
    print(f"  Height: {dims[2]:.1f}mm ({dims[2]/25.4:.2f}\")")
    print(f"{'=' * 60}")

    print("\nFILES CREATED:")
    print("  Individual parts (for multi-color printing):")
    for _, name, color in stl_files:
        r, g, b = [int(c*255) for c in color]
        print(f"    {name} - RGB({r},{g},{b})")
    print("\n  Combined files:")
    print("    heron_diorama_combined.stl - Single color print")
    print("    heron_diorama.3mf - Multi-color (Bambu Studio)")

    print(f"\n{'=' * 60}")
    print("PRINT OPTIONS:")
    print("  Option 1: Print heron_diorama.3mf in Bambu Studio")
    print("            Colors are embedded, assign filaments to parts")
    print("")
    print("  Option 2: Print individual STLs separately")
    print("            - exterior_walls: Brick red/brown filament")
    print("            - floor_plates: Gray/concrete filament")
    print("            - interior walls: White filament")
    print("            - stairs: Wood/brown filament")
    print("            Assemble with CA glue")
    print("")
    print("  Option 3: Print combined.stl, then hand paint")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
