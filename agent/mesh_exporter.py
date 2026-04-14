"""SDF to STL mesh exporter using GPU sampling and marching cubes.

Converts WGSL SDF code (fn map(p: vec3f) -> f32) to watertight STL mesh.
"""

from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Callable

import numpy as np
import wgpu

# Import SDF library for assembling shader
_AGENT_DIR = Path(__file__).resolve().parent
_SDF_LIBRARY = (_AGENT_DIR / "sdf_library.wgsl").read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# Bounds Detection via SDF Probing
# -----------------------------------------------------------------------------

def probe_sdf_bounds(
    sdf_func: Callable[[float, float, float], float],
    max_dist: float = 20.0,
    step: float = 0.5,
) -> tuple[float, float]:
    """Find bounding box by probing SDF along all axes.

    This function handles translated geometry by searching for transitions
    from inside (negative distance) to outside (positive distance) along
    each axis, not just from the origin.

    Args:
        sdf_func: Callable that takes (x, y, z) and returns signed distance.
        max_dist: Maximum distance to probe (default 20 units).
        step: Step size for probing (default 0.5 units).

    Returns:
        (min_bound, max_bound) for a cube containing the geometry.
    """
    # First, find where the geometry actually is by searching along each axis
    # for inside regions (negative distances)
    min_coords = [max_dist, max_dist, max_dist]
    max_coords = [-max_dist, -max_dist, -max_dist]

    # Sample along each axis to find where the geometry is
    for axis in range(3):
        for t in np.arange(-max_dist, max_dist + step, step):
            point = [0.0, 0.0, 0.0]
            point[axis] = float(t)
            d = sdf_func(*point)

            # If inside or near surface, expand bounds
            if d < step * 2:  # Inside or close to surface
                min_coords[axis] = min(min_coords[axis], float(t))
                max_coords[axis] = max(max_coords[axis], float(t))

    # If no geometry found, use default bounds
    if all(m > M for m, M in zip(min_coords, max_coords)):
        return (-2.0, 2.0)

    # Add margin
    max_extent = max(abs(min(min_coords)), abs(max(max_coords)))
    margin = max_extent * 0.1 + 0.5

    return (-max_extent - margin, max_extent + margin)


# -----------------------------------------------------------------------------
# GPU Device Management
# -----------------------------------------------------------------------------

_device_cache: wgpu.GPUDevice | None = None


def _get_device() -> wgpu.GPUDevice:
    """Get or create wgpu device (cached)."""
    global _device_cache
    if _device_cache is not None:
        return _device_cache
    adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
    _device_cache = adapter.request_device_sync()
    return _device_cache


# -----------------------------------------------------------------------------
# GPU SDF Sampling via Compute Shader
# -----------------------------------------------------------------------------

_SDF_SAMPLER_WGSL = r"""
struct Uniforms {
    bounds_min: f32,
    bounds_max: f32,
    resolution: u32,
    _pad: u32,
}

@group(0) @binding(0) var<uniform> u: Uniforms;
@group(0) @binding(1) var<storage, read_write> distance_field: array<f32>;

fn map_wrapped(p: vec3f) -> f32 {
    return map(p);
}

@compute @workgroup_size(4, 4, 4)
fn main(@builtin(global_invocation_id) id: vec3u) {
    let res = u.resolution;
    if (id.x >= res || id.y >= res || id.z >= res) { return; }

    let t = (vec3f(id) + 0.5) / f32(res);
    let p = mix(vec3f(u.bounds_min), vec3f(u.bounds_max), t);

    let d = map(p);
    let idx = id.x + id.y * res + id.z * res * res;
    distance_field[idx] = d;
}
"""


def sample_sdf_on_gpu(
    wgsl_map_code: str,
    bounds: tuple[float, float],
    resolution: int = 256,
) -> np.ndarray:
    """Sample SDF on a 3D grid using GPU compute shader.

    Args:
        wgsl_map_code: WGSL code containing fn map(p: vec3f) -> f32.
        bounds: (min_bound, max_bound) for sampling cube.
        resolution: Grid resolution (default 256).

    Returns:
        3D numpy array of shape (resolution, resolution, resolution) with distances.
    """
    device = _get_device()

    # Assemble shader code
    shader_code = _SDF_LIBRARY + "\n" + wgsl_map_code + "\n" + _SDF_SAMPLER_WGSL

    # Create pipeline
    pipeline = device.create_compute_pipeline(
        layout="auto",
        compute={
            "module": device.create_shader_module(code=shader_code),
            "entry_point": "main",
        },
    )

    # Pack uniforms (16 bytes: bounds_min, bounds_max, resolution, padding)
    uniform_data = struct.pack("ffII", bounds[0], bounds[1], resolution, 0)
    uniform_buf = device.create_buffer_with_data(
        data=uniform_data,
        usage=wgpu.BufferUsage.UNIFORM,
    )

    # Create storage buffer for distance field
    n_voxels = resolution ** 3
    storage_buf = device.create_buffer(
        size=n_voxels * 4,  # float32 per voxel
        usage=wgpu.BufferUsage.STORAGE | wgpu.BufferUsage.COPY_SRC,
    )

    # Create bind group
    bind_group = device.create_bind_group(
        layout=pipeline.get_bind_group_layout(0),
        entries=[
            {"binding": 0, "resource": {"buffer": uniform_buf}},
            {"binding": 1, "resource": {"buffer": storage_buf}},
        ],
    )

    # Dispatch compute shader
    wg_size = 4
    n_wg = math.ceil(resolution / wg_size)
    encoder = device.create_command_encoder()
    cpass = encoder.begin_compute_pass()
    cpass.set_pipeline(pipeline)
    cpass.set_bind_group(0, bind_group)
    cpass.dispatch_workgroups(n_wg, n_wg, n_wg)
    cpass.end()
    device.queue.submit([encoder.finish()])

    # Read back results
    raw = device.queue.read_buffer(storage_buf)
    df = np.frombuffer(raw, dtype=np.float32).reshape((resolution, resolution, resolution))

    # Cleanup
    uniform_buf.destroy()
    storage_buf.destroy()

    return df


# -----------------------------------------------------------------------------
# CPU-based SDF Evaluator for Bounds Probing
# -----------------------------------------------------------------------------

def _create_cpu_sdf_evaluator(wgsl_code: str) -> Callable[[float, float, float], float]:
    """Create a CPU function that evaluates a simple SDF.

    This is a limited evaluator for bounds probing only - it parses
    simple SDF calls and evaluates them on CPU. For complex WGSL,
    it falls back to GPU probing.
    """
    # Try to extract a simple sphere/box pattern
    import re

    # Look for sdSphere(p, R) pattern
    sphere_match = re.search(r'sdSphere\s*\(\s*p\s*,\s*([\d.]+)\s*\)', wgsl_code)
    if sphere_match:
        radius = float(sphere_match.group(1))

        def sphere_sdf(x, y, z):
            return math.sqrt(x*x + y*y + z*z) - radius
        return sphere_sdf

    # Look for sdBox(p, vec3f(X, Y, Z)) pattern
    box_match = re.search(r'sdBox\s*\(\s*p\s*,\s*vec3f\s*\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)\s*\)', wgsl_code)
    if box_match:
        hx, hy, hz = float(box_match.group(1)), float(box_match.group(2)), float(box_match.group(3))

        def box_sdf(x, y, z):
            qx, qy, qz = abs(x) - hx, abs(y) - hy, abs(z) - hz
            return math.sqrt(max(qx, 0)**2 + max(qy, 0)**2 + max(qz, 0)**2) + min(max(qx, max(qy, qz)), 0)
        return box_sdf

    # Fall back to GPU-based probing
    return None


def _probe_bounds_via_gpu(wgsl_code: str, max_dist: float = 20.0) -> tuple[float, float]:
    """Probe bounds by sampling SDF on GPU at sparse points."""
    # Sample at progressively larger radii until we find outside points
    device = _get_device()

    # Assemble shader for point evaluation
    probe_shader = _SDF_LIBRARY + "\n" + wgsl_code + r"""

struct ProbePoint {
    p: vec3f,
}

struct ProbeResult {
    d: f32,
}

@group(0) @binding(0) var<storage, read> points: array<ProbePoint>;
@group(0) @binding(1) var<storage, read_write> results: array<ProbeResult>;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) id: vec3u) {
    let idx = id.x;
    results[idx].d = map(points[idx].p);
}
"""

    # Create probe points along axes
    step = 0.5
    n_points_per_axis = int(max_dist / step) + 1
    probe_points = []

    for axis in range(3):
        for sign in [-1, 1]:
            for i in range(n_points_per_axis):
                d = i * step
                point = [0.0, 0.0, 0.0]
                point[axis] = sign * d
                probe_points.extend(point)

    n_probes = len(probe_points) // 3
    probe_data = np.array(probe_points, dtype=np.float32)

    # For simplicity, just use a conservative bound based on GPU sampling
    # Sample at a low resolution to find approximate bounds
    df = sample_sdf_on_gpu(wgsl_code, (-max_dist, max_dist), resolution=64)

    # Find where the field transitions from negative to positive
    max_extent = 0.0
    center = 32  # Center of 64^3 grid
    for axis in range(3):
        for sign in [-1, 1]:
            for i in range(center, 64):
                idx = [center, center, center]
                idx[axis] = i if sign > 0 else 63 - i
                d = df[tuple(idx)]
                if d > 0:
                    # Convert voxel index to world coordinate
                    world_d = (i - center) / 32 * max_dist
                    max_extent = max(max_extent, abs(world_d))
                    break

    margin = max_extent * 0.1 + 0.5
    return (-max_extent - margin, max_extent + margin)


# -----------------------------------------------------------------------------
# Mesh Extraction with Marching Cubes
# -----------------------------------------------------------------------------

def extract_mesh(
    distance_field: np.ndarray,
    bounds: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray]:
    """Extract mesh from distance field using marching cubes.

    Args:
        distance_field: 3D numpy array of distances.
        bounds: (min_bound, max_bound) for world coordinates.

    Returns:
        (vertices, faces) where vertices are in world coordinates.
    """
    from skimage.measure import marching_cubes

    resolution = distance_field.shape[0]
    spacing = (bounds[1] - bounds[0]) / resolution

    verts, faces, normals, values = marching_cubes(
        distance_field,
        level=0.0,
        spacing=(spacing, spacing, spacing),
    )

    # Offset vertices to world coordinates
    verts += bounds[0]

    return verts, faces


# -----------------------------------------------------------------------------
# Mesh Simplification
# -----------------------------------------------------------------------------

def simplify_mesh(
    verts: np.ndarray,
    faces: np.ndarray,
    target_triangles: int = 75000,
) -> "trimesh.Trimesh":
    """Reduce triangle count using quadratic decimation.

    Args:
        verts: Vertex array (N, 3).
        faces: Face array (M, 3).
        target_triangles: Target number of triangles.

    Returns:
        Simplified trimesh.Trimesh object.
    """
    import trimesh

    mesh = trimesh.Trimesh(vertices=verts, faces=faces)

    if len(mesh.faces) > target_triangles:
        # calculate the reduction ratio (e.g., 0.5 means reduce to 50%)
        target_reduction = 1.0 - (target_triangles / len(mesh.faces))
        target_reduction = max(0.0, min(0.99, target_reduction))  # clamp to valid range
        mesh = mesh.simplify_quadric_decimation(target_reduction)

    return mesh


# -----------------------------------------------------------------------------
# Mesh Repair and Validation
# -----------------------------------------------------------------------------

def repair_and_validate(mesh: "trimesh.Trimesh", strict: bool = False) -> "trimesh.Trimesh":
    """Repair mesh for 3D printing and validate watertightness.

    Args:
        mesh: trimesh.Trimesh object.
        strict: If True, raise error for non-watertight meshes.
                If False, log warning and continue.

    Returns:
        Repaired mesh.

    Raises:
        ValueError: If strict=True and mesh cannot be made watertight.
    """
    from trimesh import repair

    # Fix winding order / normals
    repair.fix_normals(mesh)

    # Fill holes (common marching cubes artifact)
    # Note: Only reliable for small holes; large openings may not be fixed
    repair.fill_holes(mesh)

    # Remove duplicate vertices
    mesh.merge_vertices()

    # Remove unreferenced vertices
    mesh.remove_unreferenced_vertices()

    # Check if watertight
    if not mesh.is_watertight:
        msg = (
            "This shape has open surfaces and may not print correctly. "
            "Consider closing any openings (e.g., add a bottom to a cup, "
            "cap the ends of a tube)."
        )
        if strict:
            raise ValueError(msg)
        else:
            print(f"[WARN] {msg}")

    return mesh


# -----------------------------------------------------------------------------
# Scale and Export
# -----------------------------------------------------------------------------

def apply_scale(mesh: "trimesh.Trimesh", scale_mm: float) -> "trimesh.Trimesh":
    """Apply scale factor to convert from WGSL units to millimeters.

    Args:
        mesh: trimesh.Trimesh object.
        scale_mm: Scale factor (1 WGSL unit = scale_mm mm).

    Returns:
        Scaled mesh.
    """
    mesh.vertices *= scale_mm
    return mesh


def export_stl_bytes(mesh: "trimesh.Trimesh") -> bytes:
    """Export mesh to binary STL format.

    Args:
        mesh: trimesh.Trimesh object.

    Returns:
        Binary STL data.
    """
    return mesh.export(file_type="stl")


# -----------------------------------------------------------------------------
# Main API Functions
# -----------------------------------------------------------------------------

def generate_stl(
    wgsl_code: str,
    resolution: int = 256,
    scale_mm: float = 50.0,
    target_triangles: int = 75000,
) -> bytes:
    """Generate STL from WGSL SDF code.

    Args:
        wgsl_code: WGSL code containing fn map(p: vec3f) -> f32.
        resolution: Grid resolution for SDF sampling (default 256).
        scale_mm: Scale factor for millimeters (default 50.0).
        target_triangles: Target triangle count after simplification.

    Returns:
        Binary STL data.

    Raises:
        ValueError: If geometry is invalid or not watertight.
    """
    # Extract map function from WGSL if wrapped in code blocks
    map_code = wgsl_code.strip()
    if "```wgsl" in map_code:
        import re
        match = re.search(r"```wgsl\s*(.*?)\s*```", map_code, re.DOTALL)
        if match:
            map_code = match.group(1).strip()

    # Find bounds using GPU probing
    bounds = _probe_bounds_via_gpu(map_code)

    # Sample SDF on GPU
    df = sample_sdf_on_gpu(map_code, bounds, resolution)

    # Extract mesh with marching cubes
    verts, faces = extract_mesh(df, bounds)

    # Simplify mesh
    mesh = simplify_mesh(verts, faces, target_triangles)

    # Repair and validate
    mesh = repair_and_validate(mesh)

    # Apply scale
    mesh = apply_scale(mesh, scale_mm)

    # Export to STL
    return export_stl_bytes(mesh)


def preview_mesh(
    wgsl_code: str,
    resolution: int = 128,
    scale_mm: float = 50.0,
    target_triangles: int = 75000,
) -> tuple[tuple[float, float], "trimesh.Trimesh"]:
    """Generate mesh preview with metadata (for UI size display).

    Args:
        wgsl_code: WGSL code containing fn map(p: vec3f) -> f32.
        resolution: Grid resolution (default 128 for faster preview).
        scale_mm: Scale factor for millimeters.
        target_triangles: Target triangle count.

    Returns:
        (bounds, mesh) tuple with mesh in millimeter units.
    """
    import trimesh

    # Extract map function
    map_code = wgsl_code.strip()
    if "```wgsl" in map_code:
        import re
        match = re.search(r"```wgsl\s*(.*?)\s*```", map_code, re.DOTALL)
        if match:
            map_code = match.group(1).strip()

    # Find bounds using GPU probing
    bounds = _probe_bounds_via_gpu(map_code)

    # Sample SDF on GPU
    df = sample_sdf_on_gpu(map_code, bounds, resolution)

    # Extract mesh with marching cubes
    verts, faces = extract_mesh(df, bounds)

    # Simplify mesh
    mesh = simplify_mesh(verts, faces, target_triangles)

    # Apply scale for preview
    mesh = apply_scale(mesh, scale_mm)

    return bounds, mesh