"""Generate STL, validate mesh, compute estimates for a print job."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

from print_backend.printing.estimates import estimate_cost, estimate_print_hours, estimate_weight_grams
from print_backend.printing.validation import validate_mesh_for_print


def _routing_hint(estimated_hours: float) -> str:
    return "local" if estimated_hours < 4.0 else "outsource"


def process_geometry(
    geometry_kind: str,
    code: str,
    scale_mm: float,
    *,
    material: str,
    quality: str,
    infill: int,
) -> tuple[bytes | None, Any | None, dict[str, Any]]:
    """
    Returns (stl_bytes, mesh_for_estimates, meta dict with estimates and errors).

    On failure: stl_bytes is None, meta contains "errors" list.
    """
    import trimesh

    code = (code or "").strip()
    if not code:
        return None, None, {"errors": ["Missing geometry code"]}

    if geometry_kind == "wgsl-sdf":
        try:
            from mesh_exporter import generate_stl, preview_mesh
        except ImportError as e:
            return None, None, {"errors": [f"Mesh exporter unavailable: {e}"]}

        try:
            _bounds, mesh = preview_mesh(code, resolution=128, scale_mm=scale_mm)
        except Exception as e:
            return None, None, {"errors": [f"Preview mesh failed: {e}"]}

        vr = validate_mesh_for_print(mesh)
        if not vr.ok:
            return None, None, {"errors": vr.errors}

        try:
            stl_bytes = generate_stl(code, resolution=256, scale_mm=scale_mm)
        except Exception as e:
            return None, None, {"errors": [f"STL generation failed: {e}"]}

    elif geometry_kind == "brep":
        try:
            from brep_exporter import export_stl as export_brep_stl
        except ImportError as e:
            return None, None, {"errors": [f"B-Rep exporter unavailable: {e}"]}

        try:
            stl_bytes = export_brep_stl(code)
        except Exception as e:
            return None, None, {"errors": [f"B-Rep STL failed: {e}"]}

        try:
            mesh = trimesh.load(io.BytesIO(stl_bytes), file_type="stl")
        except Exception as e:
            return None, None, {"errors": [f"Could not load mesh for validation: {e}"]}

        vr = validate_mesh_for_print(mesh)
        if not vr.ok:
            return None, None, {"errors": vr.errors}
    else:
        return None, None, {"errors": [f"Unknown geometry_kind: {geometry_kind}"]}

    w_g = estimate_weight_grams(mesh, material)
    h_est = estimate_print_hours(mesh, quality=quality, infill=infill)
    cost = estimate_cost(w_g, h_est, material=material)
    meta = {
        "estimated_print_time_h": h_est,
        "estimated_cost": round(cost, 2),
        "routing_hint": _routing_hint(h_est),
        "errors": [],
    }
    return stl_bytes, mesh, meta


def save_stl_to_disk(job_id: str, stl_bytes: bytes) -> str:
    """Return storage key (relative path under upload root)."""
    root = Path(os.environ.get("PRINT_UPLOAD_DIR", "")).expanduser()
    if not str(root):
        root = Path(__file__).resolve().parent.parent / "data" / "print_uploads"
    root.mkdir(parents=True, exist_ok=True)
    rel = f"{job_id}.stl"
    path = root / rel
    path.write_bytes(stl_bytes)
    return rel


def read_stl_file(storage_key: str) -> bytes | None:
    root = Path(os.environ.get("PRINT_UPLOAD_DIR", "")).expanduser()
    if not str(root):
        root = Path(__file__).resolve().parent.parent / "data" / "print_uploads"
    path = root / storage_key
    if not path.is_file():
        return None
    return path.read_bytes()
