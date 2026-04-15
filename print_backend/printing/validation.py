"""Validate a trimesh for on-demand printing (heuristics)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


def _parse_max_mm() -> tuple[float, float, float]:
    raw = (os.environ.get("PRINT_MAX_MM") or "250,210,210").strip()
    parts = [float(x.strip()) for x in raw.split(",")]
    if len(parts) != 3:
        return (250.0, 210.0, 210.0)
    return (parts[0], parts[1], parts[2])


def _max_triangles() -> int:
    return int((os.environ.get("PRINT_MAX_TRIANGLES") or "500000").strip() or "500000")


def _min_wall_mm() -> float:
    """Heuristic minimum feature size; edges shorter than this may be too thin."""
    return float((os.environ.get("PRINT_MIN_WALL_MM") or "0.4").strip() or "0.4")


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]


def validate_mesh_for_print(mesh: Any) -> ValidationResult:
    """Validate mesh bounds, triangle count, watertight, crude wall heuristic.

    Args:
        mesh: trimesh.Trimesh instance (already in mm).
    """
    errors: list[str] = []

    if mesh is None:
        return ValidationResult(False, ["No mesh data"])

    if not getattr(mesh, "is_watertight", False):
        errors.append("Mesh is not watertight")

    max_mm = _parse_max_mm()
    try:
        dims = mesh.bounds[1] - mesh.bounds[0]
        dx, dy, dz = float(dims[0]), float(dims[1]), float(dims[2])
    except Exception:
        return ValidationResult(False, ["Could not compute bounding box"])

    if dx > max_mm[0] or dy > max_mm[1] or dz > max_mm[2]:
        errors.append(
            f"Bounding box ({dx:.1f} x {dy:.1f} x {dz:.1f}) mm exceeds printer volume "
            f"({max_mm[0]} x {max_mm[1]} x {max_mm[2]}) mm"
        )

    n_faces = len(mesh.faces)
    if n_faces > _max_triangles():
        errors.append(f"Triangle count {n_faces} exceeds limit {_max_triangles()}")

    # Crude wall heuristic: shortest edge in mesh
    try:
        edges = mesh.edges_unique_length
        if len(edges) > 0:
            min_edge = float(edges.min())
            if min_edge < _min_wall_mm():
                errors.append(
                    f"Very short edges detected (min {min_edge:.3f} mm); "
                    f"may be below minimum printable wall (~{_min_wall_mm()} mm heuristic)"
                )
    except Exception:
        pass

    return ValidationResult(len(errors) == 0, errors)
