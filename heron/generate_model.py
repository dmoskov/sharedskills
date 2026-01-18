#!/usr/bin/env python3
"""
Heron Building - 7 Heron Street, San Francisco
3D Printable Diorama Model Generator

Based on Boor Bridges Architecture drawings dated 2012-11-07
Creates STL file for 3D printing on Bambu A1

Scale: 1:200 (resulting in ~75mm x 130mm x 45mm model)
"""

import numpy as np
from stl import mesh
import math

# === SCALE AND DIMENSIONS ===
# Scale 1:200 for bookshelf size (~3 inches tall)
SCALE = 1/200

# Real dimensions in mm (converted from architectural drawings)
# 1 foot = 304.8mm
FT = 304.8

# Building footprint from floor plans
MAIN_WIDTH = 50 * FT      # ~15.24m - East/West
MAIN_DEPTH = 65 * FT      # ~19.8m - North/South main block
REAR_EXTENSION_WIDTH = 35 * FT
REAR_EXTENSION_DEPTH = 18 * FT

# Heights from sections/elevations
FLOOR1_HEIGHT = 14 * FT   # ~4.3m
FLOOR2_HEIGHT = 11 * FT   # ~3.4m
PARAPET_HEIGHT = 3 * FT   # ~0.9m
TOTAL_HEIGHT = FLOOR1_HEIGHT + FLOOR2_HEIGHT + PARAPET_HEIGHT

# Wall thickness for hollow model (saves filament)
WALL_THICK = 2 * FT  # ~600mm real = 3mm at 1:200

# Detail dimensions
WINDOW_INSET = 0.5 * FT   # Window depth
CORNICE_PROJECT = 1.5 * FT


def create_box(origin, size):
    """Create a simple box mesh given origin (x,y,z) and size (w,d,h)"""
    x, y, z = origin
    w, d, h = size

    # 8 vertices of the box
    vertices = np.array([
        [x, y, z],          # 0: front-bottom-left
        [x+w, y, z],        # 1: front-bottom-right
        [x+w, y+d, z],      # 2: back-bottom-right
        [x, y+d, z],        # 3: back-bottom-left
        [x, y, z+h],        # 4: front-top-left
        [x+w, y, z+h],      # 5: front-top-right
        [x+w, y+d, z+h],    # 6: back-top-right
        [x, y+d, z+h],      # 7: back-top-left
    ])

    # 12 triangles (2 per face)
    faces = np.array([
        # Bottom
        [0, 2, 1], [0, 3, 2],
        # Top
        [4, 5, 6], [4, 6, 7],
        # Front (south)
        [0, 1, 5], [0, 5, 4],
        # Back (north)
        [2, 3, 7], [2, 7, 6],
        # Left (west)
        [0, 4, 7], [0, 7, 3],
        # Right (east)
        [1, 2, 6], [1, 6, 5],
    ])

    box = mesh.Mesh(np.zeros(faces.shape[0], dtype=mesh.Mesh.dtype))
    for i, f in enumerate(faces):
        for j in range(3):
            box.vectors[i][j] = vertices[f[j], :]
    return box


def create_arch_cutout(x, y, z, width, height, depth, resolution=16):
    """
    Create an arched window/door cutout shape.
    The arch is a semicircle on top of a rectangle.
    Returns vertices and faces for the cutout volume.
    """
    radius = width / 2
    rect_height = height - radius

    vertices = []
    faces = []

    # Front face vertices (y = y)
    # Bottom left and right of rectangle
    v_idx = 0
    front_bottom = []
    front_top = []

    # Front bottom-left
    vertices.append([x, y, z])
    front_bottom.append(v_idx); v_idx += 1

    # Front bottom-right
    vertices.append([x + width, y, z])
    front_bottom.append(v_idx); v_idx += 1

    # Front top-right (start of arch)
    vertices.append([x + width, y, z + rect_height])
    v_idx += 1

    # Arch vertices on front
    front_arch_start = v_idx
    for i in range(resolution + 1):
        angle = math.pi * i / resolution
        vx = x + radius - radius * math.cos(angle)
        vz = z + rect_height + radius * math.sin(angle)
        vertices.append([vx, y, vz])
        v_idx += 1
    front_arch_end = v_idx - 1

    # Front top-left
    vertices.append([x, y, z + rect_height])
    front_top_left_idx = v_idx; v_idx += 1

    # Back face vertices (y = y + depth)
    back_offset = v_idx

    # Back bottom-left
    vertices.append([x, y + depth, z])
    v_idx += 1

    # Back bottom-right
    vertices.append([x + width, y + depth, z])
    v_idx += 1

    # Back top-right
    vertices.append([x + width, y + depth, z + rect_height])
    v_idx += 1

    # Arch vertices on back
    back_arch_start = v_idx
    for i in range(resolution + 1):
        angle = math.pi * i / resolution
        vx = x + radius - radius * math.cos(angle)
        vz = z + rect_height + radius * math.sin(angle)
        vertices.append([vx, y + depth, vz])
        v_idx += 1

    # Back top-left
    vertices.append([x, y + depth, z + rect_height])
    v_idx += 1

    vertices = np.array(vertices)

    # Create faces - this is complex, so we'll use a simpler box approximation
    # for the cutout and rely on boolean operations

    # For simplicity, return a box that approximates the arch
    return create_box((x, y, z), (width, depth, height))


def create_building_shell():
    """Create the main building shell with L-shape footprint"""
    meshes = []

    # Main rectangular block
    main_block = create_box(
        (0, 0, 0),
        (MAIN_WIDTH, MAIN_DEPTH, TOTAL_HEIGHT)
    )
    meshes.append(main_block)

    # Rear L-extension (northeast corner)
    rear_block = create_box(
        (MAIN_WIDTH - REAR_EXTENSION_WIDTH, MAIN_DEPTH, 0),
        (REAR_EXTENSION_WIDTH, REAR_EXTENSION_DEPTH, TOTAL_HEIGHT)
    )
    meshes.append(rear_block)

    return meshes


def create_window_details():
    """Create recessed window details as separate geometry"""
    meshes = []

    inset = WINDOW_INSET

    # South facade (street facing) - large arched windows ground floor
    # Based on elevation A4.1
    for i in range(4):
        x = 3*FT + i * 11.5*FT
        # Window frame - represented as slightly recessed box
        frame = create_box(
            (x, -inset, 2*FT),
            (8*FT, inset*0.8, 10*FT)
        )
        meshes.append(frame)

    # South facade - 2nd floor smaller windows
    for i in range(5):
        x = 2.5*FT + i * 9.5*FT
        frame = create_box(
            (x, -inset, FLOOR1_HEIGHT + 1.5*FT),
            (6*FT, inset*0.8, 7*FT)
        )
        meshes.append(frame)

    # West facade windows (similar pattern)
    for i in range(4):
        y_pos = 6*FT + i * 14*FT
        frame = create_box(
            (-inset, y_pos, 2*FT),
            (inset*0.8, 8*FT, 9*FT)
        )
        meshes.append(frame)

    # East facade windows
    for i in range(4):
        y_pos = 6*FT + i * 14*FT
        frame = create_box(
            (MAIN_WIDTH + inset*0.2, y_pos, 2*FT),
            (inset*0.8, 8*FT, 9*FT)
        )
        meshes.append(frame)

    return meshes


def create_cornice():
    """Create decorative cornice detail at parapet"""
    meshes = []

    cornice_z = FLOOR1_HEIGHT + FLOOR2_HEIGHT - 0.5*FT
    cornice_h = 1.5*FT
    proj = CORNICE_PROJECT

    # South cornice (main facade)
    south_cornice = create_box(
        (-proj*0.2, -proj, cornice_z),
        (MAIN_WIDTH + proj*0.4, proj, cornice_h)
    )
    meshes.append(south_cornice)

    # Second tier
    south_cornice2 = create_box(
        (-proj*0.1, -proj*0.6, cornice_z + cornice_h),
        (MAIN_WIDTH + proj*0.2, proj*0.6, cornice_h*0.5)
    )
    meshes.append(south_cornice2)

    # West cornice
    west_cornice = create_box(
        (-proj, 0, cornice_z),
        (proj, MAIN_DEPTH, cornice_h*0.7)
    )
    meshes.append(west_cornice)

    # East cornice
    east_cornice = create_box(
        (MAIN_WIDTH, 0, cornice_z),
        (proj, MAIN_DEPTH, cornice_h*0.7)
    )
    meshes.append(east_cornice)

    return meshes


def create_roof_details():
    """Create skylights and roof hatch"""
    meshes = []

    roof_z = TOTAL_HEIGHT

    # Skylights - 6 in a grid pattern (from roof plan A2.5/A2.6)
    skylight_h = 1*FT  # Raised curb
    for i in range(2):
        for j in range(3):
            x = 8*FT + i * 18*FT
            y = 12*FT + j * 16*FT
            skylight = create_box(
                (x, y, roof_z),
                (6*FT, 8*FT, skylight_h)
            )
            meshes.append(skylight)

    # Roof hatch structure (from A7.1 details)
    hatch_x = MAIN_WIDTH - 18*FT
    hatch_y = MAIN_DEPTH - 12*FT
    hatch = create_box(
        (hatch_x, hatch_y, roof_z),
        (8*FT, 8*FT, 5*FT)
    )
    meshes.append(hatch)

    # Mechanical area on roof (northeast)
    mech = create_box(
        (MAIN_WIDTH - REAR_EXTENSION_WIDTH + 2*FT, MAIN_DEPTH + 2*FT, roof_z),
        (12*FT, 10*FT, 4*FT)
    )
    meshes.append(mech)

    return meshes


def create_overhead_door():
    """Create overhead door recess on south facade"""
    # Recessed area for the overhead door
    door = create_box(
        (MAIN_WIDTH - 14*FT, -WINDOW_INSET, 0),
        (12*FT, WINDOW_INSET*0.9, 12*FT)
    )
    return [door]


def create_base_plate():
    """Create a base plate for easier printing and display"""
    margin = 2*FT
    base = create_box(
        (-margin, -margin, -1*FT),
        (MAIN_WIDTH + REAR_EXTENSION_WIDTH*0.2 + margin*2,
         MAIN_DEPTH + REAR_EXTENSION_DEPTH + margin*2,
         1*FT)
    )
    return [base]


def combine_meshes(mesh_list):
    """Combine multiple meshes into one"""
    total_faces = sum(m.vectors.shape[0] for m in mesh_list)
    combined = mesh.Mesh(np.zeros(total_faces, dtype=mesh.Mesh.dtype))

    idx = 0
    for m in mesh_list:
        for i in range(m.vectors.shape[0]):
            combined.vectors[idx] = m.vectors[i]
            idx += 1

    return combined


def main():
    print("Generating Heron Building 3D model...")
    print(f"Scale: 1:{int(1/SCALE)}")

    all_meshes = []

    # Build the model
    print("  Creating building shell...")
    all_meshes.extend(create_building_shell())

    print("  Adding cornice details...")
    all_meshes.extend(create_cornice())

    print("  Adding roof details...")
    all_meshes.extend(create_roof_details())

    print("  Adding base plate...")
    all_meshes.extend(create_base_plate())

    # Combine all meshes
    print("  Combining meshes...")
    combined = combine_meshes(all_meshes)

    # Apply scale
    print(f"  Applying scale (1:{int(1/SCALE)})...")
    combined.vectors *= SCALE

    # Calculate final dimensions
    minx = combined.vectors[:,:,0].min()
    maxx = combined.vectors[:,:,0].max()
    miny = combined.vectors[:,:,1].min()
    maxy = combined.vectors[:,:,1].max()
    minz = combined.vectors[:,:,2].min()
    maxz = combined.vectors[:,:,2].max()

    print(f"\nFinal model dimensions:")
    print(f"  Width (X):  {maxx-minx:.1f}mm")
    print(f"  Depth (Y):  {maxy-miny:.1f}mm")
    print(f"  Height (Z): {maxz-minz:.1f}mm")

    # Save STL
    output_file = "heron_building.stl"
    combined.save(output_file)
    print(f"\nSaved: {output_file}")

    # Also save a version without base plate for flexibility
    no_base_meshes = []
    no_base_meshes.extend(create_building_shell())
    no_base_meshes.extend(create_cornice())
    no_base_meshes.extend(create_roof_details())

    combined_no_base = combine_meshes(no_base_meshes)
    combined_no_base.vectors *= SCALE
    combined_no_base.save("heron_building_no_base.stl")
    print(f"Saved: heron_building_no_base.stl (without base plate)")

    print("\nReady for slicing in Bambu Studio!")
    print("Recommended settings:")
    print("  - Layer height: 0.12-0.16mm for detail")
    print("  - Infill: 15-20%")
    print("  - Supports: Not needed (flat bottom)")


if __name__ == "__main__":
    main()
