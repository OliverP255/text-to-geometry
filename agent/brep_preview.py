"""
B-Rep preview generation: mesh extraction from CadQuery code.

Extracts mesh via .val().tessellate() -> vertices/faces -> JSON for browser rendering.
No server-side image rendering - the browser renders with Three.js.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

# Ensure agent directory is on path for imports
_agent_dir = Path(__file__).resolve().parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

from brep_validator import execute_cadquery_in_subprocess


def get_mesh_json(code: str, tolerance: float = 0.1) -> dict[str, Any]:
    """
    Generate mesh JSON from CadQuery code for browser preview.

    Mesh extraction path:
        CadQuery result → .val().tessellate() → vertices/faces → JSON

    Args:
        code: CadQuery Python code with 'result' variable
        tolerance: Mesh tessellation tolerance in mm (default 0.1)

    Returns:
        Dict with:
            - type: "brep-mesh"
            - vertices: [[x, y, z], ...]
            - faces: [[i0, i1, i2], ...]
            - normals: [[nx, ny, nz], ...]
            - bounds: {min: [x, y, z], max: [x, y, z]}
            - volume_mm3: float
            - is_watertight: bool

    Raises:
        ValueError: If code execution or mesh extraction fails
    """
    result, error = execute_cadquery_in_subprocess(code)

    if error:
        raise ValueError(error)

    if result is None:
        raise ValueError("No result from code execution")

    # Add type identifier and computed properties
    result["type"] = "brep-mesh"

    # Compute normals if not present
    if "normals" not in result:
        result["normals"] = _compute_normals(result["vertices"], result["faces"])

    # Compute volume estimate (using trimesh if available)
    result["volume_mm3"] = _compute_volume(result["vertices"], result["faces"])

    # Check watertight (using trimesh if available)
    result["is_watertight"] = _check_watertight(result["vertices"], result["faces"])

    return result


def _compute_normals(vertices: list[list[float]], faces: list[list[int]]) -> list[list[float]]:
    """
    Compute vertex normals from mesh data.

    Uses simple face normal averaging for each vertex.
    """
    import math

    if not vertices or not faces:
        return [[0.0, 0.0, 1.0]] * len(vertices)

    # Initialize normals to zero
    normals = [[0.0, 0.0, 0.0] for _ in vertices]

    # Accumulate face normals to vertices
    for face in faces:
        if len(face) < 3:
            continue

        # Get triangle vertices
        v0 = vertices[face[0]]
        v1 = vertices[face[1]]
        v2 = vertices[face[2]]

        # Compute edge vectors
        e1 = [v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]]
        e2 = [v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]]

        # Cross product (face normal)
        nx = e1[1] * e2[2] - e1[2] * e2[1]
        ny = e1[2] * e2[0] - e1[0] * e2[2]
        nz = e1[0] * e2[1] - e1[1] * e2[0]

        # Normalize
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length > 0:
            nx /= length
            ny /= length
            nz /= length

        # Add to each vertex in face
        for idx in face:
            normals[idx][0] += nx
            normals[idx][1] += ny
            normals[idx][2] += nz

    # Normalize accumulated normals
    for i, n in enumerate(normals):
        length = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        if length > 0:
            normals[i] = [n[0] / length, n[1] / length, n[2] / length]
        else:
            normals[i] = [0.0, 0.0, 1.0]

    return normals


def _compute_volume(vertices: list[list[float]], faces: list[list[int]]) -> float:
    """
    Compute approximate mesh volume using signed tetrahedron method.

    Returns volume in mm^3.
    """
    if not vertices or not faces:
        return 0.0

    try:
        import trimesh
        import numpy as np

        v = np.array(vertices, dtype=np.float64)
        f = np.array(faces, dtype=np.int64)
        mesh = trimesh.Trimesh(vertices=v, faces=f)
        return float(mesh.volume)
    except ImportError:
        # Fallback: signed tetrahedron method
        return _signed_tetrahedron_volume(vertices, faces)


def _signed_tetrahedron_volume(vertices: list[list[float]], faces: list[list[int]]) -> float:
    """
    Compute volume using signed tetrahedron method (no external deps).
    """
    volume = 0.0

    for face in faces:
        if len(face) < 3:
            continue

        v0 = vertices[face[0]]
        v1 = vertices[face[1]]
        v2 = vertices[face[2]]

        # Signed volume of tetrahedron formed with origin
        vol = (
            v0[0] * (v1[1] * v2[2] - v1[2] * v2[1])
            + v0[1] * (v1[2] * v2[0] - v1[0] * v2[2])
            + v0[2] * (v1[0] * v2[1] - v1[1] * v2[0])
        ) / 6.0

        volume += vol

    return abs(volume)


def _check_watertight(vertices: list[list[float]], faces: list[list[int]]) -> bool:
    """
    Check if mesh is watertight (manifold).

    Returns True if every edge is shared by exactly 2 faces.
    """
    if not vertices or not faces:
        return False

    try:
        import trimesh
        import numpy as np

        v = np.array(vertices, dtype=np.float64)
        f = np.array(faces, dtype=np.int64)
        mesh = trimesh.Trimesh(vertices=v, faces=f)
        return bool(mesh.is_watertight)
    except ImportError:
        # Fallback: edge counting
        return _check_watertight_edge_count(faces)


def _check_watertight_edge_count(faces: list[list[int]]) -> bool:
    """
    Check watertight by counting edge occurrences.

    A watertight mesh has every edge shared by exactly 2 faces.
    """
    from collections import defaultdict

    edge_counts: dict[tuple[int, int], int] = defaultdict(int)

    for face in faces:
        if len(face) < 3:
            continue

        # Get edges (sorted tuple for undirected edge)
        for i in range(len(face)):
            v1, v2 = face[i], face[(i + 1) % len(face)]
            edge = tuple(sorted([v1, v2]))
            edge_counts[edge] += 1

    # Check all edges have count of 2
    for count in edge_counts.values():
        if count != 2:
            return False

    return True


# =============================================================================
# Direct CadQuery execution (for when CadQuery is installed in main process)
# =============================================================================

def execute_cadquery_code(code: str) -> tuple[Optional[Any], Optional[str]]:
    """
    Execute CadQuery code and return the result object.

    This uses the subprocess sandbox for safety.

    Args:
        code: CadQuery Python code

    Returns:
        (result_object, error_message)
    """
    result, error = execute_cadquery_in_subprocess(code)
    if error:
        return None, error
    return result, None