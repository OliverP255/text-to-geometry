"""
High-level primitives library for CadQuery.

CRITICAL for LLM reliability. Raw CadQuery chains are verbose (15+ lines for a
mounting plate) and error-prone for LLMs. This library provides one-liners that
dramatically improve generation reliability.

Each primitive returns a cq.Workplane for further chaining if needed.

Coordinate conventions:
- Z-axis is up (CAD standard)
- Units are millimetres
- Objects are centered on origin by default
"""

from __future__ import annotations

from typing import List, Optional, Tuple

try:
    import cadquery as cq
    _CADQUERY_AVAILABLE = True
except ImportError:
    _CADQUERY_AVAILABLE = False
    cq = None  # type: ignore


# =============================================================================
# Basic Solids
# =============================================================================

def box(width: float, depth: float, height: float) -> "cq.Workplane":
    """
    Create a rectangular box centered on origin.

    Args:
        width: X dimension in mm
        depth: Y dimension in mm
        height: Z dimension in mm

    Returns:
        cq.Workplane with the box
    """
    return cq.Workplane("XY").box(width, depth, height)


def cylinder(radius: float, height: float) -> "cq.Workplane":
    """
    Create a cylinder centered on origin, Z-axis aligned.

    Args:
        radius: Cylinder radius in mm
        height: Z height in mm

    Returns:
        cq.Workplane with the cylinder
    """
    return cq.Workplane("XY").circle(radius).extrude(height)


def cone(radius_bottom: float, radius_top: float, height: float) -> "cq.Workplane":
    """
    Create a cone or truncated cone centered on origin, Z-axis aligned.

    Args:
        radius_bottom: Bottom radius in mm
        radius_top: Top radius in mm (0 for pointed cone)
        height: Z height in mm

    Returns:
        cq.Workplane with the cone
    """
    # Use Solid.makeCone for reliability
    solid = cq.Solid.makeCone(radius_bottom, radius_top, height)
    return cq.Workplane("XY").newObject([solid])


def sphere(radius: float) -> "cq.Workplane":
    """
    Create a sphere centered on origin.

    Args:
        radius: Sphere radius in mm

    Returns:
        cq.Workplane with the sphere
    """
    return cq.Workplane("XY").sphere(radius)


def torus(tube_radius: float, ring_radius: float) -> "cq.Workplane":
    """
    Create a torus centered on origin, Z-axis aligned.

    Args:
        tube_radius: Radius of the tube (cross-section) in mm
        ring_radius: Radius from center to tube center in mm

    Returns:
        cq.Workplane with the torus
    """
    # Use Solid.makeTorus for reliability
    solid = cq.Solid.makeTorus(ring_radius, tube_radius)
    return cq.Workplane("XY").newObject([solid])


# =============================================================================
# Enhanced Solids
# =============================================================================

def rounded_box(width: float, depth: float, height: float, radius: float) -> "cq.Workplane":
    """
    Create a box with rounded vertical edges.

    Args:
        width: X dimension in mm
        depth: Y dimension in mm
        height: Z dimension in mm
        radius: Edge radius in mm

    Returns:
        cq.Workplane with the rounded box
    """
    return (
        cq.Workplane("XY")
        .box(width, depth, height)
        .edges("|Z")
        .fillet(radius)
    )


def tube(outer_radius: float, inner_radius: float, height: float) -> "cq.Workplane":
    """
    Create a hollow tube centered on origin, Z-axis aligned.

    Args:
        outer_radius: Outer radius in mm
        inner_radius: Inner radius in mm (must be < outer_radius)
        height: Z height in mm

    Returns:
        cq.Workplane with the tube
    """
    return (
        cq.Workplane("XY")
        .circle(outer_radius)
        .circle(inner_radius)
        .extrude(height)
    )


def hollow_box(width: float, depth: float, height: float, wall_thickness: float) -> "cq.Workplane":
    """
    Create a hollow box with specified wall thickness.

    Args:
        width: Outer X dimension in mm
        depth: Outer Y dimension in mm
        height: Outer Z dimension in mm
        wall_thickness: Wall thickness in mm

    Returns:
        cq.Workplane with the hollow box (open top)
    """
    return (
        cq.Workplane("XY")
        .box(width, depth, height)
        .faces(">Z")
        .shell(wall_thickness * -1)
    )


# =============================================================================
# Plates and Brackets
# =============================================================================

def mounting_plate(
    width: float,
    depth: float,
    thickness: float,
    hole_diameter: float,
    hole_margin: float,
    hole_count: Tuple[int, int] = (2, 2),
) -> "cq.Workplane":
    """
    Create a mounting plate with a grid of mounting holes.

    Args:
        width: X dimension in mm
        depth: Y dimension in mm
        thickness: Z thickness in mm
        hole_diameter: Mounting hole diameter in mm
        hole_margin: Distance from edge to hole center in mm
        hole_count: (x_count, y_count) number of holes in each direction

    Returns:
        cq.Workplane with the mounting plate

    Example:
        mounting_plate(100, 60, 8, 6, 10)  # 4 corner holes
        mounting_plate(100, 60, 8, 6, 10, (3, 2))  # 6 holes in 3x2 grid
    """
    x_count, y_count = hole_count

    # Calculate hole positions
    hole_x_spacing = (width - 2 * hole_margin) / max(1, x_count - 1) if x_count > 1 else 0
    hole_y_spacing = (depth - 2 * hole_margin) / max(1, y_count - 1) if y_count > 1 else 0

    hole_positions = []
    for i in range(x_count):
        for j in range(y_count):
            x = -width / 2 + hole_margin + i * hole_x_spacing
            y = -depth / 2 + hole_margin + j * hole_y_spacing
            hole_positions.append((x, y))

    return (
        cq.Workplane("XY")
        .box(width, depth, thickness)
        .faces(">Z")
        .workplane()
        .pushPoints(hole_positions)
        .hole(hole_diameter)
    )


def corner_bracket(
    width: float,
    height: float,
    thickness: float,
    hole_diameter: float,
) -> "cq.Workplane":
    """
    Create an L-shaped corner bracket with mounting holes.

    Args:
        width: Width of each arm in mm
        height: Height (vertical dimension) in mm
        thickness: Material thickness in mm
        hole_diameter: Mounting hole diameter in mm

    Returns:
        cq.Workplane with the corner bracket
    """
    hole_offset = width * 0.25

    return (
        cq.Workplane("XY")
        .box(width, width, thickness)
        .faces(">Z")
        .workplane()
        .transformed(offset=cq.Vector(0, width / 2, 0))
        .rect(width, width)
        .extrude(height - thickness)
        .faces(">Z")
        .workplane()
        .pushPoints([
            (-width / 2 + hole_offset, -width / 2 + hole_offset),
            (width / 2 - hole_offset, -width / 2 + hole_offset),
        ])
        .hole(hole_diameter)
        .faces(">Z")
        .workplane(offset=-(height - thickness))
        .pushPoints([
            (-width / 2 + hole_offset, width / 2 - hole_offset),
        ])
        .hole(hole_diameter)
    )


# =============================================================================
# Holes and Features
# =============================================================================

def counterbore_hole(
    solid: "cq.Workplane",
    hole_diameter: float,
    counterbore_diameter: float,
    counterbore_depth: float,
    depth: float = float("inf"),
    face: str = ">Z",
) -> "cq.Workplane":
    """
    Add a counterbore hole to a solid.

    Args:
        solid: The solid to add the hole to
        hole_diameter: Main hole diameter in mm
        counterbore_diameter: Counterbore diameter in mm
        counterbore_depth: Counterbore depth in mm
        depth: Total hole depth (inf for through-hole)
        face: Face selector for hole placement

    Returns:
        cq.Workplane with the counterbore hole
    """
    return solid.faces(face).cboreHole(hole_diameter, counterbore_diameter, counterbore_depth, depth)


def countersink_hole(
    solid: "cq.Workplane",
    hole_diameter: float,
    countersink_diameter: float,
    countersink_angle: float = 82.0,
    depth: float = float("inf"),
    face: str = ">Z",
) -> "cq.Workplane":
    """
    Add a countersink hole to a solid.

    Args:
        solid: The solid to add the hole to
        hole_diameter: Main hole diameter in mm
        countersink_diameter: Countersink diameter in mm
        countersink_angle: Countersink angle in degrees (default 82)
        depth: Total hole depth (inf for through-hole)
        face: Face selector for hole placement

    Returns:
        cq.Workplane with the countersink hole
    """
    return solid.faces(face).cskHole(hole_diameter, countersink_diameter, countersink_angle, depth)


def slot(
    solid: "cq.Workplane",
    length: float,
    width: float,
    depth: float,
    face: str = ">Z",
) -> "cq.Workplane":
    """
    Cut a rectangular slot into a solid.

    Args:
        solid: The solid to cut
        length: Slot length in mm
        width: Slot width in mm
        depth: Slot depth in mm
        face: Face selector for slot placement

    Returns:
        cq.Workplane with the slot cut
    """
    return (
        solid
        .faces(face)
        .workplane()
        .rect(length, width)
        .cutBlind(-depth)
    )


# =============================================================================
# Patterns
# =============================================================================

def circular_pattern(
    solid: "cq.Workplane",
    radius: float,
    count: int,
) -> "cq.Workplane":
    """
    Create a circular pattern of a solid.

    Args:
        solid: The solid to pattern (will be moved to radius)
        radius: Radius of the pattern circle in mm
        count: Number of copies

    Returns:
        cq.Workplane with the patterned solids
    """
    angle = 360.0 / count
    return (
        cq.Workplane("XY")
        .polarArray(radius, 0, 360, count)
        .eachpoint(lambda loc: solid.val().located(loc))
        .combine()
    )


def linear_pattern(
    solid: "cq.Workplane",
    spacing: float,
    count: int,
    direction: str = "X",
) -> "cq.Workplane":
    """
    Create a linear pattern of a solid.

    Args:
        solid: The solid to pattern
        spacing: Distance between copies in mm
        count: Number of copies
        direction: "X", "Y", or "Z" direction

    Returns:
        cq.Workplane with the patterned solids
    """
    return solid.rarray(spacing, spacing, count, 1)


# =============================================================================
# Profile-based Operations
# =============================================================================

def extruded_profile(
    points: List[Tuple[float, float]],
    height: float,
) -> "cq.Workplane":
    """
    Create a solid by extruding a closed 2D profile.

    Args:
        points: List of (x, y) coordinates defining the profile
        height: Extrusion height in mm (Z direction)

    Returns:
        cq.Workplane with the extruded solid

    Example:
        extruded_profile([(0, 0), (10, 0), (10, 5), (0, 5)], 20)
    """
    wp = cq.Workplane("XY")
    for i, (x, y) in enumerate(points):
        if i == 0:
            wp = wp.moveTo(x, y)
        else:
            wp = wp.lineTo(x, y)
    return wp.close().extrude(height)


def revolved_profile(
    points: List[Tuple[float, float]],
    angle: float = 360.0,
) -> "cq.Workplane":
    """
    Create a solid by revolving a 2D profile around the Y-axis.

    Args:
        points: List of (x, y) coordinates defining the profile (x = radius, y = height)
        angle: Revolution angle in degrees (default 360)

    Returns:
        cq.Workplane with the revolved solid

    Example:
        revolved_profile([(5, 0), (10, 0), (10, 20), (5, 20)])  # Cylinder-like
    """
    wp = cq.Workplane("XZ")
    for i, (x, y) in enumerate(points):
        if i == 0:
            wp = wp.moveTo(x, y)
        else:
            wp = wp.lineTo(x, y)
    return wp.close().revolve(angle)


# =============================================================================
# Documentation for LLM System Prompt
# =============================================================================

PRIMITIVES_REFERENCE = """
## High-Level CadQuery Primitives (Use These!)

These primitives simplify CadQuery code. Always prefer them over raw CadQuery chains.

### Basic Solids
| Function | Description |
|----------|-------------|
| `box(width, depth, height)` | Rectangular box centered on origin |
| `cylinder(radius, height)` | Z-aligned cylinder |
| `cone(r_bottom, r_top, height)` | Cone or truncated cone |
| `sphere(radius)` | Sphere centered on origin |
| `torus(tube_r, ring_r)` | Z-aligned torus |

### Enhanced Solids
| Function | Description |
|----------|-------------|
| `rounded_box(w, d, h, r)` | Box with rounded vertical edges |
| `tube(outer_r, inner_r, h)` | Hollow tube |
| `hollow_box(w, d, h, thickness)` | Open-top hollow box |

### Plates and Brackets
| Function | Description |
|----------|-------------|
| `mounting_plate(w, d, t, hole_d, margin)` | Plate with corner holes |
| `mounting_plate(w, d, t, hole_d, margin, (nx, ny))` | Plate with nx×ny hole grid |
| `corner_bracket(w, h, t, hole_d)` | L-shaped bracket with holes |

### Holes and Features
| Function | Description |
|----------|-------------|
| `counterbore_hole(solid, d, cbore_d, cbore_depth)` | Add counterbore hole |
| `countersink_hole(solid, d, csk_d, angle)` | Add countersink hole |
| `slot(solid, length, width, depth)` | Cut rectangular slot |

### Patterns
| Function | Description |
|----------|-------------|
| `circular_pattern(solid, radius, count)` | Pattern solids in a circle |
| `linear_pattern(solid, spacing, count, dir)` | Pattern solids in a line |

### Profile Operations
| Function | Description |
|----------|-------------|
| `extruded_profile(points, height)` | Extrude closed 2D profile |
| `revolved_profile(points, angle)` | Revolve profile around Y-axis |

### Example Usage
```python
import cadquery as cq
from cadquery_primitives import mounting_plate, rounded_box

# Simple mounting plate
result = mounting_plate(100, 60, 8, 6, 10)

# Rounded box with center hole
result = rounded_box(50, 50, 20, 5)
result = result.faces(">Z").hole(10)
```

### Chaining
All primitives return cq.Workplane objects, so you can chain CadQuery operations:
```python
result = rounded_box(100, 100, 10, 5).faces(">Z").hole(20)
```
"""