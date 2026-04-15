"""Rough weight, cost, and time estimates for print jobs."""

from __future__ import annotations

import os
from typing import Any


def estimate_weight_grams(mesh: Any, material: str) -> float:
    """Volume (mm³) * density → grams."""
    try:
        vol_mm3 = float(mesh.volume)
    except Exception:
        vol_mm3 = 0.0
    vol_cm3 = vol_mm3 / 1000.0
    rho = (
        float(os.environ.get("PRINT_DENSITY_RESIN", "1.1"))
        if material.lower() == "resin"
        else float(os.environ.get("PRINT_DENSITY_PLA", "1.24"))
    )
    return max(0.0, vol_cm3 * rho)


def estimate_print_hours(
    mesh: Any,
    *,
    quality: str = "normal",
    infill: int = 20,
) -> float:
    """Very rough hours from bounding box volume and settings."""
    try:
        vol_mm3 = float(mesh.volume)
    except Exception:
        vol_mm3 = 1.0
    base_rate = 200_000.0
    if quality == "high":
        base_rate = 80_000.0
    elif quality == "draft":
        base_rate = 350_000.0
    infill_factor = 0.15 + (infill / 100.0) * 0.85
    hours = (vol_mm3 * infill_factor) / base_rate
    return max(0.1, min(hours, 500.0))


def estimate_cost(
    weight_g: float,
    print_hours: float,
    *,
    material: str = "PLA",
) -> float:
    """Rough USD from env-tunable rates."""
    mat = float(os.environ.get("PRINT_COST_PER_GRAM", "0.05"))
    time_h = float(os.environ.get("PRINT_COST_PER_HOUR", "2.0"))
    if material.lower() == "resin":
        mat = float(os.environ.get("PRINT_COST_PER_GRAM_RESIN", "0.12"))
    return weight_g * mat + print_hours * time_h
