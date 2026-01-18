#!/usr/bin/env python3
"""
Heron Building - Event Space Diorama
7 Heron Street, San Francisco

Features:
- Large arched firehouse door (east facade) - KEY FEATURE
- Double-height event space interior
- Wraparound mezzanine balcony on 2nd floor
- Cutaway view to see inside
- Bougainvillea on north facade

Based on exterior photos showing brick industrial building
with distinctive tall arched entry

Scale: 1:200
"""

import numpy as np
from stl import mesh
import math
import zipfile
import xml.etree.ElementTree as ET
import os
import re


def load_filament_settings(source_3mf):
    """
    Extract filament colors and object-to-extruder mappings from a Bambu 3MF.
    Returns (filament_colors, extruder_map) or (None, None) if not found.
    """
    if not os.path.exists(source_3mf):
        return None, None

    filament_colors = None
    extruder_map = {}

    try:
        with zipfile.ZipFile(source_3mf, 'r') as zf:
            # Look for Bambu/Slic3r config files
            for name in zf.namelist():
                if 'model_settings.config' in name or 'Slic3r_PE.config' in name:
                    content = zf.read(name).decode('utf-8')
                    # Parse [object:N] sections
                    current_obj = None
                    for line in content.split('\n'):
                        obj_match = re.match(r'\[object:(\d+)\]', line)
                        if obj_match:
                            current_obj = int(obj_match.group(1))
                        elif '=' in line and current_obj:
                            key, val = line.split('=', 1)
                            key = key.strip()
                            val = val.strip()
                            if key == 'name':
                                extruder_map[current_obj] = {'name': val}
                            elif key == 'extruder' and current_obj in extruder_map:
                                extruder_map[current_obj]['extruder'] = int(val)

                if 'project_settings.config' in name or 'slice_info.config' in name:
                    content = zf.read(name).decode('utf-8')
                    # Look for filament_colour line
                    for line in content.split('\n'):
                        if 'filament_colour' in line and '=' in line:
                            _, colors = line.split('=', 1)
                            filament_colors = [c.strip() for c in colors.strip().split(';')]
                            break

        # Convert extruder_map to name->extruder format
        name_to_extruder = {}
        for obj_id, data in extruder_map.items():
            if 'name' in data and 'extruder' in data:
                name_to_extruder[data['name']] = data['extruder']

        return filament_colors, name_to_extruder

    except Exception as e:
        print(f"Warning: Could not read {source_3mf}: {e}")
        return None, None


# File to preserve user's color choices
USER_COLORS_FILE = "heron_user_colors.3mf"

# === CONFIGURATION ===
SCALE = 1/200
FT = 304.8
INCH = 25.4

# Building dimensions
BUILDING_WIDTH = 50 * FT   # East-West
BUILDING_DEPTH = 70 * FT   # North-South
BUILDING_HEIGHT = 28 * FT  # Total height to parapet

# Floor heights
GROUND_FLOOR_H = 16 * FT   # Tall ground floor for events
MEZZANINE_H = 10 * FT      # Mezzanine level
PARAPET_H = 2 * FT

# Construction
EXT_WALL = 1.2 * FT
FLOOR_THICK = 0.6 * FT
RAILING_H = 3.5 * FT
MEZZANINE_DEPTH = 8 * FT   # How far balcony extends into space

# The big firehouse door
FIREHOUSE_DOOR_WIDTH = 14 * FT
FIREHOUSE_DOOR_HEIGHT = 18 * FT

# Colors
COLORS = {
    'brick': (0.65, 0.35, 0.28),       # Aged brick red
    'brick_dark': (0.45, 0.25, 0.20),  # Darker brick accent
    'concrete': (0.72, 0.70, 0.68),    # Floor
    'wood_floor': (0.70, 0.55, 0.38),  # Event space floor
    'metal': (0.35, 0.35, 0.38),       # Railings, structure
    'glass': (0.75, 0.88, 0.95),       # Windows
    'bougainvillea': (0.85, 0.15, 0.35), # Red flowering vine
    'base': (0.25, 0.25, 0.25),
}


class MeshBuilder:
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

        v = [self.add_vertex([x, y, z]),
             self.add_vertex([x+w, y, z]),
             self.add_vertex([x+w, y+d, z]),
             self.add_vertex([x, y+d, z]),
             self.add_vertex([x, y, z+h]),
             self.add_vertex([x+w, y, z+h]),
             self.add_vertex([x+w, y+d, z+h]),
             self.add_vertex([x, y+d, z+h])]

        self.add_quad(v[0], v[3], v[2], v[1])
        self.add_quad(v[4], v[5], v[6], v[7])
        self.add_quad(v[0], v[1], v[5], v[4])
        self.add_quad(v[2], v[3], v[7], v[6])
        self.add_quad(v[0], v[4], v[7], v[3])
        self.add_quad(v[1], v[2], v[6], v[5])

    def add_arch(self, x, y, z, width, height, depth, segments=20):
        """Add an arched opening/frame extruded along Y"""
        radius = width / 2
        rect_h = height - radius
        cx = x + radius

        # Create arch profile points
        profile = []
        # Start bottom left, go clockwise
        profile.append([x, z])
        profile.append([x + width, z])
        profile.append([x + width, z + rect_h])

        # Arch from right to left (top)
        for i in range(segments + 1):
            angle = math.pi * (1 - i / segments)
            px = cx + radius * math.cos(angle)
            pz = z + rect_h + radius * math.sin(angle)
            profile.append([px, pz])

        profile.append([x, z + rect_h])

        n = len(profile)

        # Front and back vertices
        front_v = [self.add_vertex([p[0], y, p[1]]) for p in profile]
        back_v = [self.add_vertex([p[0], y + depth, p[1]]) for p in profile]

        # Connect front to back (sides of the arch tunnel)
        for i in range(n):
            i_next = (i + 1) % n
            self.add_quad(front_v[i], front_v[i_next], back_v[i_next], back_v[i])

    def add_arch_frame(self, x, y, z, width, height, depth, frame_width, segments=20):
        """Add a frame around an arch (the brick surround)"""
        # This creates the solid frame, not the opening
        outer_w = width + frame_width * 2
        outer_h = height + frame_width

        # Just add corner pieces and top arch frame
        # Left pilaster
        self.add_box((x - frame_width, y, z), (frame_width, depth, height))
        # Right pilaster
        self.add_box((x + width, y, z), (frame_width, depth, height))
        # Arch top (simplified as rectangular for now)
        self.add_box((x - frame_width, y, z + height - frame_width),
                    (outer_w, depth, frame_width))

    def to_stl(self):
        vertices = np.array(self.vertices)
        faces = np.array(self.faces)
        stl_mesh = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
        for i, f in enumerate(faces):
            for j in range(3):
                stl_mesh.vectors[i][j] = vertices[f[j]]
        return stl_mesh


def build_exterior_walls_cutaway():
    """
    Build exterior walls based on reference photo:
    - South facade: Window LEFT, Fire door CENTER, Window RIGHT
    - Brick industrial building style
    """
    mb = MeshBuilder()

    # === SOUTH WALL (street-facing) ===
    # Layout from photo: [Window] [FIRE DOOR] [Window]
    # Fire door is in the CENTER

    window_w = 10 * FT
    window_h = 16 * FT  # Tall arched windows
    window_sill = 2 * FT

    # Calculate positions for symmetrical layout
    # Door in center, windows on either side
    door_x = (BUILDING_WIDTH - FIREHOUSE_DOOR_WIDTH) / 2  # Center the door

    # Left window position
    win_left_x = 3 * FT

    # Right window position (mirror of left)
    win_right_x = BUILDING_WIDTH - 3*FT - window_w

    # Pier widths between elements
    pier_width = door_x - win_left_x - window_w

    # === Build wall sections ===

    # Far left wall
    mb.add_box((0, 0, 0), (win_left_x, EXT_WALL, BUILDING_HEIGHT))

    # Left window - wall above
    mb.add_box((win_left_x, 0, window_sill + window_h),
              (window_w, EXT_WALL, BUILDING_HEIGHT - window_sill - window_h))
    # Left window - wall below
    mb.add_box((win_left_x, 0, 0), (window_w, EXT_WALL, window_sill))

    # Pier between left window and door
    mb.add_box((win_left_x + window_w, 0, 0),
              (pier_width, EXT_WALL, BUILDING_HEIGHT))

    # Wall above door
    mb.add_box((door_x, 0, FIREHOUSE_DOOR_HEIGHT),
              (FIREHOUSE_DOOR_WIDTH, EXT_WALL, BUILDING_HEIGHT - FIREHOUSE_DOOR_HEIGHT))

    # Pier between door and right window
    mb.add_box((door_x + FIREHOUSE_DOOR_WIDTH, 0, 0),
              (pier_width, EXT_WALL, BUILDING_HEIGHT))

    # Right window - wall above
    mb.add_box((win_right_x, 0, window_sill + window_h),
              (window_w, EXT_WALL, BUILDING_HEIGHT - window_sill - window_h))
    # Right window - wall below
    mb.add_box((win_right_x, 0, 0), (window_w, EXT_WALL, window_sill))

    # Far right wall
    mb.add_box((win_right_x + window_w, 0, 0),
              (BUILDING_WIDTH - win_right_x - window_w, EXT_WALL, BUILDING_HEIGHT))

    # === EAST WALL - FULL ===
    east_x = BUILDING_WIDTH - EXT_WALL
    mb.add_box((east_x, 0, 0), (EXT_WALL, BUILDING_DEPTH, BUILDING_HEIGHT))

    # === NORTH WALL - FULL ===
    north_y = BUILDING_DEPTH - EXT_WALL
    mb.add_box((0, north_y, 0), (BUILDING_WIDTH, EXT_WALL, BUILDING_HEIGHT))

    # === WEST WALL - FULL ===
    mb.add_box((0, 0, 0), (EXT_WALL, BUILDING_DEPTH, BUILDING_HEIGHT))

    # === PARAPET (all sides) ===
    parapet_z = BUILDING_HEIGHT - PARAPET_H
    parapet_thick = EXT_WALL + 0.5*FT
    parapet_extra_h = PARAPET_H + 0.5*FT

    # North parapet
    mb.add_box((0, north_y, parapet_z), (BUILDING_WIDTH, parapet_thick, parapet_extra_h))
    # East parapet
    mb.add_box((east_x, 0, parapet_z), (parapet_thick, BUILDING_DEPTH, parapet_extra_h))
    # South parapet
    mb.add_box((0, -0.5*FT, parapet_z), (BUILDING_WIDTH, parapet_thick, parapet_extra_h))
    # West parapet
    mb.add_box((-0.5*FT, 0, parapet_z), (parapet_thick, BUILDING_DEPTH, parapet_extra_h))

    return mb


# Store door position for other modules
def get_door_x():
    """Get fire door X position (centered on facade)"""
    return (BUILDING_WIDTH - FIREHOUSE_DOOR_WIDTH) / 2


def get_window_positions():
    """Get window positions matching the facade layout"""
    window_w = 10 * FT
    win_left_x = 3 * FT
    win_right_x = BUILDING_WIDTH - 3*FT - window_w
    return win_left_x, win_right_x, window_w


def build_firehouse_door_detail():
    """Build the iconic arched firehouse door frame - dark red painted trim like photo"""
    mb = MeshBuilder()

    door_x = get_door_x()
    south_y = 0

    # Door frame/surround (projecting outward) - painted dark red
    frame_w = 1.0 * FT  # Width of frame trim
    frame_project = 0.4 * FT  # How far it sticks out

    # Left jamb
    mb.add_box((door_x - frame_w, -frame_project, 0),
              (frame_w, EXT_WALL + frame_project, FIREHOUSE_DOOR_HEIGHT))

    # Right jamb
    mb.add_box((door_x + FIREHOUSE_DOOR_WIDTH, -frame_project, 0),
              (frame_w, EXT_WALL + frame_project, FIREHOUSE_DOOR_HEIGHT))

    # Arch/header - simplified curved top
    # Build arch with stacked segments
    arch_center_x = door_x + FIREHOUSE_DOOR_WIDTH / 2
    arch_radius = FIREHOUSE_DOOR_WIDTH / 2
    arch_base_z = FIREHOUSE_DOOR_HEIGHT - arch_radius

    # Approximate arch with segments
    num_segments = 8
    for i in range(num_segments):
        angle1 = math.pi * i / num_segments
        angle2 = math.pi * (i + 1) / num_segments

        x1 = arch_center_x - arch_radius * math.cos(angle1)
        x2 = arch_center_x - arch_radius * math.cos(angle2)
        z1 = arch_base_z + arch_radius * math.sin(angle1)
        z2 = arch_base_z + arch_radius * math.sin(angle2)

        # Arch frame segment
        seg_x = min(x1, x2)
        seg_w = abs(x2 - x1) + frame_w
        seg_z = min(z1, z2)
        seg_h = abs(z2 - z1) + frame_w

        mb.add_box((seg_x - frame_w/2, -frame_project, seg_z),
                  (seg_w, EXT_WALL + frame_project, seg_h))

    # Threshold
    mb.add_box((door_x - 0.5*FT, -frame_project - 0.2*FT, -0.2*FT),
              (FIREHOUSE_DOOR_WIDTH + 1*FT, EXT_WALL + frame_project + 0.4*FT, 0.4*FT))

    return mb


def build_window_frames():
    """Build window frames for the arched windows - dark red painted trim"""
    mb = MeshBuilder()

    # Window positions (left and right of center door)
    win_left_x, win_right_x, window_w = get_window_positions()
    window_h = 16 * FT
    window_sill = 2 * FT

    frame_w = 0.8 * FT
    frame_project = 0.3 * FT

    def add_window_frame(win_x):
        # Left jamb
        mb.add_box((win_x - frame_w, -frame_project, window_sill),
                  (frame_w, EXT_WALL + frame_project, window_h))
        # Right jamb
        mb.add_box((win_x + window_w, -frame_project, window_sill),
                  (frame_w, EXT_WALL + frame_project, window_h))
        # Header
        mb.add_box((win_x - frame_w, -frame_project, window_sill + window_h),
                  (window_w + frame_w*2, EXT_WALL + frame_project, frame_w))
        # Sill
        mb.add_box((win_x - frame_w, -frame_project - 0.2*FT, window_sill - frame_w),
                  (window_w + frame_w*2, EXT_WALL + frame_project + 0.3*FT, frame_w))

        # Mullions (vertical dividers) - 3 panes wide like photo
        mullion_w = 0.3 * FT
        for i in range(1, 3):
            mx = win_x + i * window_w / 3
            mb.add_box((mx - mullion_w/2, -frame_project, window_sill),
                      (mullion_w, frame_project + 0.2*FT, window_h))

        # Horizontal muntin (divider) - upper portion
        mb.add_box((win_x, -frame_project, window_sill + window_h * 0.6),
                  (window_w, frame_project + 0.2*FT, mullion_w))

    # Left window frame
    add_window_frame(win_left_x)
    # Right window frame
    add_window_frame(win_right_x)

    return mb


def build_event_floor():
    """Main event space floor"""
    mb = MeshBuilder()

    # Ground floor slab (full footprint)
    mb.add_box((EXT_WALL, EXT_WALL, -FLOOR_THICK),
              (BUILDING_WIDTH - EXT_WALL*2, BUILDING_DEPTH - EXT_WALL*2, FLOOR_THICK))

    return mb


def build_mezzanine():
    """
    Wraparound mezzanine/balcony on second floor
    U-shaped: wraps north, east, west but OPEN on south for door view
    """
    mb = MeshBuilder()

    mezzanine_z = GROUND_FLOOR_H - FLOOR_THICK
    inner_margin = MEZZANINE_DEPTH

    # North mezzanine (along north wall) - full width
    mb.add_box((EXT_WALL, BUILDING_DEPTH - EXT_WALL - inner_margin, mezzanine_z),
              (BUILDING_WIDTH - EXT_WALL*2, inner_margin, FLOOR_THICK))

    # East mezzanine (along east wall) - connects north to south corner
    mb.add_box((BUILDING_WIDTH - EXT_WALL - inner_margin, EXT_WALL + inner_margin, mezzanine_z),
              (inner_margin, BUILDING_DEPTH - EXT_WALL*2 - inner_margin, FLOOR_THICK))

    # West mezzanine (along west wall) - connects north to south corner
    mb.add_box((EXT_WALL, EXT_WALL + inner_margin, mezzanine_z),
              (inner_margin, BUILDING_DEPTH - EXT_WALL*2 - inner_margin, FLOOR_THICK))

    # Small corner returns on south (don't block door view)
    # Southeast corner
    mb.add_box((BUILDING_WIDTH - EXT_WALL - inner_margin, EXT_WALL, mezzanine_z),
              (inner_margin, inner_margin, FLOOR_THICK))
    # Southwest corner
    mb.add_box((EXT_WALL, EXT_WALL, mezzanine_z),
              (inner_margin, inner_margin, FLOOR_THICK))

    return mb


def build_mezzanine_railing():
    """Railings around the mezzanine opening - U-shaped to match mezzanine"""
    mb = MeshBuilder()

    mezzanine_z = GROUND_FLOOR_H
    inner_margin = MEZZANINE_DEPTH
    rail_thick = 0.15 * FT
    post_size = 0.25 * FT

    # Inner edge railings (looking down into event space)

    # North railing (full width inner edge)
    rail_y = BUILDING_DEPTH - EXT_WALL - inner_margin
    mb.add_box((EXT_WALL + inner_margin, rail_y, mezzanine_z),
              (BUILDING_WIDTH - EXT_WALL*2 - inner_margin*2, rail_thick, RAILING_H))

    # Posts along north railing
    for i in range(6):
        post_x = EXT_WALL + inner_margin + i * 6*FT
        mb.add_box((post_x, rail_y, mezzanine_z), (post_size, post_size, RAILING_H))

    # East railing (inner edge)
    rail_x = BUILDING_WIDTH - EXT_WALL - inner_margin
    mb.add_box((rail_x, EXT_WALL + inner_margin, mezzanine_z),
              (rail_thick, BUILDING_DEPTH - EXT_WALL*2 - inner_margin*2, RAILING_H))

    # Posts along east railing
    for i in range(5):
        post_y = EXT_WALL + inner_margin + i * 10*FT
        mb.add_box((rail_x, post_y, mezzanine_z), (post_size, post_size, RAILING_H))

    # West railing (inner edge)
    rail_x = EXT_WALL + inner_margin
    mb.add_box((rail_x - rail_thick, EXT_WALL + inner_margin, mezzanine_z),
              (rail_thick, BUILDING_DEPTH - EXT_WALL*2 - inner_margin*2, RAILING_H))

    # Posts along west railing
    for i in range(5):
        post_y = EXT_WALL + inner_margin + i * 10*FT
        mb.add_box((rail_x - post_size, post_y, mezzanine_z), (post_size, post_size, RAILING_H))

    # South edge railings (on the corner returns, looking into door)
    # Southeast corner railing
    mb.add_box((BUILDING_WIDTH - EXT_WALL - inner_margin, EXT_WALL + inner_margin - rail_thick, mezzanine_z),
              (inner_margin - rail_thick, rail_thick, RAILING_H))
    # Southwest corner railing
    mb.add_box((EXT_WALL + rail_thick, EXT_WALL + inner_margin - rail_thick, mezzanine_z),
              (inner_margin - rail_thick, rail_thick, RAILING_H))

    return mb


def build_stairs():
    """Stair from ground to mezzanine (industrial style)"""
    mb = MeshBuilder()

    # Stair in southwest area
    stair_x = EXT_WALL + 3*FT
    stair_y = EXT_WALL + 3*FT
    stair_width = 4 * FT

    tread_depth = 11 * INCH
    riser_h = 7.5 * INCH
    tread_thick = 1 * INCH

    num_treads = int(GROUND_FLOOR_H / riser_h)

    # Treads
    for i in range(num_treads):
        z = i * riser_h
        y = stair_y + i * tread_depth
        mb.add_box((stair_x, y, z), (stair_width, tread_depth, tread_thick))

    # Stringers (metal side supports)
    stringer_w = 0.5 * INCH * 4
    for i in range(num_treads):
        z = i * riser_h
        y = stair_y + i * tread_depth
        # Left stringer segment
        mb.add_box((stair_x - stringer_w, y, z),
                  (stringer_w, tread_depth, riser_h + tread_thick))
        # Right stringer segment
        mb.add_box((stair_x + stair_width, y, z),
                  (stringer_w, tread_depth, riser_h + tread_thick))

    # Landing at top
    landing_y = stair_y + num_treads * tread_depth
    mb.add_box((stair_x - 1*FT, landing_y, GROUND_FLOOR_H - FLOOR_THICK),
              (stair_width + 2*FT, 4*FT, FLOOR_THICK))

    return mb


def build_roof():
    """Roof slab with skylights"""
    mb = MeshBuilder()

    roof_z = BUILDING_HEIGHT - PARAPET_H

    # Main roof
    mb.add_box((0, 0, roof_z),
              (BUILDING_WIDTH, BUILDING_DEPTH, FLOOR_THICK))

    return mb


def build_skylights():
    """Skylights on roof"""
    mb = MeshBuilder()

    roof_z = BUILDING_HEIGHT - PARAPET_H + FLOOR_THICK

    # Grid of skylights
    for i in range(2):
        for j in range(3):
            x = 12*FT + i * 18*FT
            y = 12*FT + j * 18*FT
            # Skylight curb
            mb.add_box((x, y, roof_z), (8*FT, 10*FT, 1*FT))

    return mb


def build_bougainvillea():
    """Bougainvillea on south facade - organic flower clusters cascading over fire door"""
    import random
    random.seed(42)  # Reproducible randomness

    mb = MeshBuilder()

    south_y = -0.5 * FT
    door_x = get_door_x()  # Use actual door position
    trunk_x = 1 * FT  # Trunk at far left (like photo)
    canopy_z = BUILDING_HEIGHT - 4*FT

    # Small flower cluster size
    flower_size = 0.8 * FT

    def add_flower_cluster(cx, cy, cz, density=8, spread=2*FT):
        """Add a cluster of small flower boxes around a center point"""
        for _ in range(density):
            ox = random.uniform(-spread, spread)
            oy = random.uniform(-spread*0.5, spread*0.5)
            oz = random.uniform(-spread, spread)
            size = flower_size * random.uniform(0.6, 1.4)
            mb.add_box((cx + ox, cy + oy, cz + oz), (size, size*0.8, size))

    # === TRUNK on left side (brown, will be separate or painted) ===
    mb.add_box((trunk_x, south_y - 1*FT, 0), (1.8*FT, 1.8*FT, 8*FT))
    mb.add_box((trunk_x + 0.2*FT, south_y - 0.7*FT, 8*FT), (1.4*FT, 1.4*FT, 5*FT))
    mb.add_box((trunk_x + 0.4*FT, south_y - 0.5*FT, 13*FT), (1*FT, 1*FT, 4*FT))
    # Branch spreading right
    mb.add_box((trunk_x + 1*FT, south_y - 0.4*FT, 15*FT), (8*FT, 0.8*FT, 0.8*FT))

    # === CANOPY - dense flower clusters across top ===
    # Heavy coverage above trunk
    for i in range(12):
        x = trunk_x + random.uniform(-3*FT, 12*FT)
        z = canopy_z + random.uniform(-3*FT, 4*FT)
        add_flower_cluster(x, south_y, z, density=10, spread=2.5*FT)

    # Spreading across top of building
    for i in range(20):
        x = trunk_x + 10*FT + i * 1.8*FT
        z = canopy_z + random.uniform(0, 3*FT)
        y_offset = random.uniform(-1*FT, 0.5*FT)
        add_flower_cluster(x, south_y + y_offset, z, density=6, spread=2*FT)

    # === CASCADING down left side (heavy) ===
    for i in range(8):
        z = 10*FT + i * 2*FT
        x = trunk_x + 4*FT + random.uniform(-2*FT, 3*FT)
        add_flower_cluster(x, south_y - 0.3*FT, z, density=7, spread=2*FT)

    # More cascading tendrils
    for i in range(6):
        z = 12*FT + i * 2.5*FT
        x = trunk_x + 10*FT + random.uniform(-1*FT, 2*FT)
        add_flower_cluster(x, south_y - 0.2*FT, z, density=5, spread=1.5*FT)

    # === DRAPING over fire door ===
    # Above door
    for i in range(8):
        x = door_x + i * 2*FT
        z = FIREHOUSE_DOOR_HEIGHT + 3*FT + random.uniform(0, 3*FT)
        add_flower_cluster(x, south_y - 0.2*FT, z, density=6, spread=1.5*FT)

    # Hanging tendrils at door edges
    for i in range(4):
        z = FIREHOUSE_DOOR_HEIGHT - 2*FT + i * 1.5*FT
        add_flower_cluster(door_x + 1*FT, south_y, z, density=4, spread=1*FT)
        add_flower_cluster(door_x + FIREHOUSE_DOOR_WIDTH - 2*FT, south_y, z, density=3, spread=1*FT)

    # === RIGHT SIDE - lighter coverage ===
    for i in range(5):
        x = door_x + FIREHOUSE_DOOR_WIDTH + 4*FT + random.uniform(0, 6*FT)
        z = 16*FT + i * 2*FT
        add_flower_cluster(x, south_y - 0.2*FT, z, density=4, spread=1.5*FT)

    return mb


def build_base():
    """Display base"""
    mb = MeshBuilder()
    margin = 4 * FT

    mb.add_box((-margin, -margin, -2*FT),
              (BUILDING_WIDTH + margin*2, BUILDING_DEPTH + margin*2, 2*FT))

    # Street edge
    mb.add_box((-margin, -margin - 2*FT, -0.3*FT),
              (BUILDING_WIDTH + margin*2, 2*FT, 0.3*FT))

    return mb


def save_stl(mb, filename, scale=SCALE):
    stl = mb.to_stl()
    stl.vectors *= scale
    stl.save(filename)


def create_3mf(parts, output_file, scale=SCALE, user_colors_file=None):
    """Create 3MF with colored parts - Bambu Studio compatible"""
    import json

    # Default extruder map
    extruder_map = {
        'exterior_brick': 1,      # Brick color
        'firehouse_door': 2,      # Dark red (door frame)
        'window_frames': 2,       # Dark red (same as door)
        'event_floor': 3,         # Wood
        'mezzanine': 4,           # Concrete
        'railing': 5,             # Metal dark
        'stairs': 5,              # Metal dark (same as railing)
        'roof': 4,                # Concrete (same as mezzanine)
        'skylights': 6,           # Light blue
        'bougainvillea': 7,       # Green/flowering
        'base': 8,                # Dark gray
    }

    # Default filament colors
    filament_colors = [
        '#A55947',  # 1: Brick
        '#723F33',  # 2: Dark brown
        '#B28C60',  # 3: Wood
        '#B7B2AD',  # 4: Concrete
        '#595960',  # 5: Metal
        '#BFE0F2',  # 6: Light blue
        '#D82659',  # 7: Magenta
        '#3F3F3F',  # 8: Dark gray
    ]

    # Try to load user's saved colors
    if user_colors_file:
        saved_colors, saved_extruders = load_filament_settings(user_colors_file)
        if saved_colors:
            print(f"  Loaded filament colors from {user_colors_file}")
            filament_colors = saved_colors
        if saved_extruders:
            print(f"  Loaded extruder assignments from {user_colors_file}")
            extruder_map.update(saved_extruders)

    # Build the 3D model XML - Bambu style with components
    model = ET.Element('model')
    model.set('unit', 'millimeter')
    model.set('xmlns', 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02')
    model.set('xmlns:p', 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06')
    model.set('xml:lang', 'en-US')

    resources = ET.SubElement(model, 'resources')
    build = ET.SubElement(model, 'build')

    # Create each part as a separate object
    object_ids = []
    for obj_id, (mb, name, color) in enumerate(parts, start=1):
        stl = mb.to_stl()
        stl.vectors *= scale

        obj = ET.SubElement(resources, 'object')
        obj.set('id', str(obj_id))
        obj.set('name', name)
        obj.set('type', 'model')
        obj.set('p:UUID', f'00000000-0000-0000-0000-{obj_id:012d}')

        mesh_elem = ET.SubElement(obj, 'mesh')
        vertices_elem = ET.SubElement(mesh_elem, 'vertices')
        triangles_elem = ET.SubElement(mesh_elem, 'triangles')

        vertex_list = []
        vertex_map = {}

        for face in stl.vectors:
            for vertex in face:
                v_tuple = tuple(round(v, 6) for v in vertex)
                if v_tuple not in vertex_map:
                    vertex_map[v_tuple] = len(vertex_list)
                    vertex_list.append(vertex)

        for v in vertex_list:
            vert = ET.SubElement(vertices_elem, 'vertex')
            vert.set('x', f'{v[0]:.6f}')
            vert.set('y', f'{v[1]:.6f}')
            vert.set('z', f'{v[2]:.6f}')

        for face in stl.vectors:
            tri = ET.SubElement(triangles_elem, 'triangle')
            tri.set('v1', str(vertex_map[tuple(round(v, 6) for v in face[0])]))
            tri.set('v2', str(vertex_map[tuple(round(v, 6) for v in face[1])]))
            tri.set('v3', str(vertex_map[tuple(round(v, 6) for v in face[2])]))

        object_ids.append((obj_id, name))

    # Add items to build
    for obj_id, name in object_ids:
        item = ET.SubElement(build, 'item')
        item.set('objectid', str(obj_id))
        item.set('p:UUID', f'10000000-0000-0000-0000-{obj_id:012d}')

    xml_str = ET.tostring(model, encoding='unicode')

    # Create Bambu model settings config
    model_settings = []
    for obj_id, (mb, name, color) in enumerate(parts, start=1):
        extruder = extruder_map.get(name, 1)
        model_settings.append(f'[object:{obj_id}]')
        model_settings.append(f'name = {name}')
        model_settings.append(f'extruder = {extruder}')
        model_settings.append('')

    # Plate config (JSON format for Bambu)
    plate_objects = []
    for obj_id, (mb, name, color) in enumerate(parts, start=1):
        extruder = extruder_map.get(name, 1)
        plate_objects.append({
            "identify_id": obj_id,
            "name": name,
            "extruder": extruder,
            "geometry_id": obj_id
        })

    plate_config = {
        "plate_index": 1,
        "objects": plate_objects
    }

    # Project config
    project_config = [
        "; Bambu Studio Project",
        "; Heron Event Space - Multi-color",
        "",
        "[filament]",
        f"filament_colour = {';'.join(filament_colors)}",
        "",
    ]

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        content_types = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
  <Default Extension="json" ContentType="application/json"/>
  <Default Extension="config" ContentType="text/plain"/>
</Types>'''
        zf.writestr('[Content_Types].xml', content_types)

        rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>'''
        zf.writestr('_rels/.rels', rels)
        zf.writestr('3D/3dmodel.model', '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str)

        # Bambu-specific metadata
        zf.writestr('Metadata/model_settings.config', '\n'.join(model_settings))
        zf.writestr('Metadata/plate_1.json', json.dumps(plate_config, indent=2))
        zf.writestr('Metadata/project_settings.config', '\n'.join(project_config))


def main():
    print("=" * 60)
    print("HERON EVENT SPACE DIORAMA")
    print("Based on reference photos - Fire door & Bougainvillea")
    print("=" * 60)
    print(f"\nScale: 1:{int(1/SCALE)}")
    print(f"Firehouse door: {FIREHOUSE_DOOR_WIDTH/FT:.0f}' wide x {FIREHOUSE_DOOR_HEIGHT/FT:.0f}' tall")

    print("\nBuilding components...")

    print("  [1/11] Exterior walls...")
    exterior = build_exterior_walls_cutaway()

    print("  [2/11] Firehouse door frame...")
    door = build_firehouse_door_detail()

    print("  [3/11] Window frames...")
    window_frames = build_window_frames()

    print("  [4/11] Event space floor...")
    floor = build_event_floor()

    print("  [5/11] Mezzanine balcony...")
    mezzanine = build_mezzanine()

    print("  [6/11] Mezzanine railing...")
    railing = build_mezzanine_railing()

    print("  [7/11] Stairs...")
    stairs = build_stairs()

    print("  [8/11] Roof...")
    roof = build_roof()

    print("  [9/11] Skylights...")
    skylights = build_skylights()

    print("  [10/11] Bougainvillea...")
    bougainvillea = build_bougainvillea()

    print("  [11/11] Display base...")
    base = build_base()

    # Define parts with colors
    # Door frame and window frames are same dark red color
    parts = [
        (exterior, "exterior_brick", COLORS['brick']),
        (door, "firehouse_door", COLORS['brick_dark']),
        (window_frames, "window_frames", COLORS['brick_dark']),  # Same as door - dark red
        (floor, "event_floor", COLORS['wood_floor']),
        (mezzanine, "mezzanine", COLORS['concrete']),
        (railing, "railing", COLORS['metal']),
        (stairs, "stairs", COLORS['metal']),
        (roof, "roof", COLORS['concrete']),
        (skylights, "skylights", COLORS['glass']),
        (bougainvillea, "bougainvillea", COLORS['bougainvillea']),
        (base, "base", COLORS['base']),
    ]

    # Save individual STLs
    print("\nSaving STL files...")
    for mb, name, color in parts:
        filename = f"heron_event_{name}.stl"
        save_stl(mb, filename)
        r, g, b = [int(c*255) for c in color]
        print(f"  {filename} - RGB({r},{g},{b})")

    # Combined STL
    print("\nCreating combined model...")
    combined = MeshBuilder()
    for mb, _, _ in parts:
        base_offset = len(combined.vertices)
        for v in mb.vertices:
            combined.add_vertex(v)
        for f in mb.faces:
            combined.add_face(f[0] + base_offset, f[1] + base_offset, f[2] + base_offset)

    save_stl(combined, "heron_event_space.stl")
    print("  Saved: heron_event_space.stl")

    # 3MF with colors - try to preserve user's color choices
    print("\nCreating 3MF with colors...")
    user_colors = USER_COLORS_FILE if os.path.exists(USER_COLORS_FILE) else None
    if user_colors:
        print(f"  Found saved colors: {USER_COLORS_FILE}")
    create_3mf(parts, "heron_event_space.3mf", user_colors_file=user_colors)
    print("  Saved: heron_event_space.3mf")

    # Dimensions
    stl = combined.to_stl()
    stl.vectors *= SCALE
    dims = stl.vectors.max(axis=(0,1)) - stl.vectors.min(axis=(0,1))

    print(f"\n{'='*60}")
    print("MODEL DIMENSIONS:")
    print(f"  {dims[0]:.1f}mm x {dims[1]:.1f}mm x {dims[2]:.1f}mm")
    print(f"  ({dims[0]/25.4:.2f}\" x {dims[1]/25.4:.2f}\" x {dims[2]/25.4:.2f}\")")
    print(f"{'='*60}")

    print("\nFEATURES:")
    print("  - Large arched firehouse door on east facade")
    print("  - Cutaway on south/west to see interior")
    print("  - Double-height event space")
    print("  - Wraparound mezzanine balcony with railings")
    print("  - Industrial staircase")
    print("  - Skylights on roof")
    print("  - Bougainvillea cascading on north facade")

    print("\nSUGGESTED FILAMENTS:")
    print("  Slot 1: Brick/terracotta - exterior walls")
    print("  Slot 2: Dark red/maroon - door & window frames")
    print("  Slot 3: Wood/tan PLA - event floor")
    print("  Slot 4: Gray - mezzanine, roof, concrete")
    print("  Slot 5: Dark gray/black - railings, stairs")
    print("  Slot 6: Light blue/clear - skylights")
    print("  Slot 7: Green/flowering - bougainvillea")
    print("  Slot 8: Dark gray - base")

    print(f"\n{'='*60}")
    print("TO PRESERVE YOUR FILAMENT CHOICES:")
    print(f"  1. Set up colors in Bambu Studio")
    print(f"  2. Save project as: {USER_COLORS_FILE}")
    print(f"  3. Next regeneration will use your saved colors!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
