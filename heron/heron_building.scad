// Heron Building - 7 Heron Street, San Francisco
// 3D Printable Diorama Model
// Scale: 1:100 (1mm = 100mm real)

// Based on Boor Bridges Architecture drawings dated 2012-11-07

/* Real dimensions (approximate from drawings):
   - Main building footprint: ~50' x 85' (L-shaped)
   - 1st floor height: ~14'
   - 2nd floor height: ~12'
   - Parapet: ~3'
   - Total height: ~29'
*/

// === PARAMETERS ===
scale_factor = 1/100;  // 1:100 scale

// Real dimensions in mm (convert from feet: 1' = 304.8mm)
ft = 304.8;

// Building dimensions (in feet, will be scaled)
main_width = 50 * ft;      // East-West dimension
main_depth = 65 * ft;      // North-South main section
rear_depth = 20 * ft;      // Additional rear section
rear_width = 35 * ft;      // Width of rear section

floor1_height = 14 * ft;
floor2_height = 12 * ft;
parapet_height = 3 * ft;
total_height = floor1_height + floor2_height + parapet_height;

wall_thickness = 1 * ft;

// Window dimensions
arch_window_width = 6 * ft;
arch_window_height = 10 * ft;
rect_window_width = 4 * ft;
rect_window_height = 5 * ft;

// === MODULES ===

// Arched window cutout
module arch_window(w, h, depth=500) {
    radius = w/2;
    arch_height = h - radius;

    translate([0, 0, 0])
    union() {
        // Rectangular part
        cube([w, depth, arch_height]);
        // Arch part
        translate([radius, 0, arch_height])
        rotate([-90, 0, 0])
        cylinder(h=depth, r=radius, $fn=32);
    }
}

// Rectangular window cutout
module rect_window(w, h, depth=500) {
    cube([w, depth, h]);
}

// Decorative cornice
module cornice(length, projection=300, height=400) {
    // Simple stepped cornice profile
    translate([0, 0, 0])
    union() {
        cube([length, projection*0.3, height*0.3]);
        translate([0, 0, height*0.3])
        cube([length, projection*0.6, height*0.3]);
        translate([0, 0, height*0.6])
        cube([length, projection, height*0.4]);
    }
}

// Main building mass
module building_mass() {
    union() {
        // Main rectangular volume
        cube([main_width, main_depth, total_height]);

        // Rear L extension (northeast)
        translate([main_width - rear_width, main_depth, 0])
        cube([rear_width, rear_depth, total_height]);
    }
}

// South facade (street facing) with arched openings
module south_facade_windows() {
    window_y = -100;  // Slightly outside for clean cut

    // Large arched openings - ground floor
    // Based on elevation A4.1 - shows ~4 large arches
    for (i = [0:3]) {
        translate([3*ft + i * 12*ft, window_y, 2*ft])
        arch_window(8*ft, 11*ft);
    }

    // Second floor windows - smaller arches
    for (i = [0:4]) {
        translate([4*ft + i * 10*ft, window_y, floor1_height + 2*ft])
        arch_window(5*ft, 7*ft);
    }
}

// West facade windows
module west_facade_windows() {
    window_x = -100;

    // Ground floor - large arched windows
    for (i = [0:3]) {
        translate([window_x, 8*ft + i * 15*ft, 2*ft])
        rotate([0, 0, 90])
        arch_window(6*ft, 9*ft);
    }

    // Second floor windows
    for (i = [0:4]) {
        translate([window_x, 6*ft + i * 12*ft, floor1_height + 2*ft])
        rotate([0, 0, 90])
        arch_window(4*ft, 6*ft);
    }
}

// East facade windows
module east_facade_windows() {
    window_x = main_width + 100;

    // Similar pattern to west
    for (i = [0:3]) {
        translate([window_x, 8*ft + i * 15*ft, 2*ft])
        rotate([0, 0, -90])
        arch_window(6*ft, 9*ft);
    }

    for (i = [0:4]) {
        translate([window_x, 6*ft + i * 12*ft, floor1_height + 2*ft])
        rotate([0, 0, -90])
        arch_window(4*ft, 6*ft);
    }
}

// North facade (rear)
module north_facade_windows() {
    window_y = main_depth + rear_depth + 100;

    // Simpler rear facade
    for (i = [0:2]) {
        translate([main_width - rear_width + 5*ft + i * 10*ft, window_y, 3*ft])
        rotate([0, 0, 180])
        rect_window(5*ft, 7*ft);
    }
}

// Overhead door on south facade
module overhead_door() {
    translate([main_width - 14*ft, -100, 0])
    cube([12*ft, 500, 12*ft]);
}

// Skylights on roof
module skylights() {
    skylight_z = total_height - 100;

    // Based on roof plan - 6 skylights in grid pattern
    for (i = [0:1]) {
        for (j = [0:2]) {
            translate([10*ft + i * 20*ft, 15*ft + j * 18*ft, skylight_z])
            cube([6*ft, 8*ft, 500]);
        }
    }
}

// Parapet detail
module parapet_detail() {
    parapet_z = floor1_height + floor2_height;

    // South parapet with cornice
    translate([0, -300, parapet_z])
    cornice(main_width, 400, parapet_height);

    // East parapet
    translate([main_width, 0, parapet_z])
    rotate([0, 0, 90])
    cornice(main_depth, 300, parapet_height * 0.7);

    // West parapet
    translate([0, main_depth, parapet_z])
    rotate([0, 0, -90])
    cornice(main_depth, 300, parapet_height * 0.7);
}

// Patio area (recessed at ground level, south side)
module patio_cutout() {
    translate([2*ft, -100, 0])
    cube([20*ft, 15*ft + 100, floor1_height - 1*ft]);
}

// Roof access hatch structure
module roof_hatch() {
    translate([main_width - 15*ft, main_depth - 10*ft, total_height])
    difference() {
        cube([8*ft, 8*ft, 4*ft]);
        translate([0.5*ft, 0.5*ft, 0.5*ft])
        cube([7*ft, 7*ft, 4*ft]);
    }
}

// === MAIN ASSEMBLY ===

module heron_building() {
    difference() {
        union() {
            building_mass();
            parapet_detail();
            roof_hatch();
        }

        // Cut out all windows and doors
        south_facade_windows();
        west_facade_windows();
        east_facade_windows();
        north_facade_windows();
        overhead_door();
        skylights();
        // patio_cutout();  // Optional - uncomment for recessed patio
    }
}

// === RENDER ===

// Apply scale and render
scale([scale_factor, scale_factor, scale_factor])
heron_building();

// Uncomment below to add a base plate for easier printing
/*
translate([0, -5, -2])
scale([scale_factor, scale_factor, scale_factor])
cube([main_width + 4*ft, main_depth + rear_depth + 8*ft, 2/scale_factor]);
*/
