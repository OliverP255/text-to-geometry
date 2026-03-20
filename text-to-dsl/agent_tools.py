"""LLM agent tools: evaluate loss and optimise parameters for DSL SDF."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple, Union

# Add parent/build for text_to_geometry_bindings when run from text-to-dsl/
_build = Path(__file__).resolve().parent.parent / "build"
if _build.exists() and str(_build) not in sys.path:
    sys.path.insert(0, str(_build))

import torch

import text_to_geometry_bindings as t2g
from evaluator_cache import get_or_create_evaluator
from loss import agent_eval_loss
from optimise_params import optimise_params, sample_batch


def evaluate_loss(
    dsl_or_flatir: Union[str, Dict[str, Any]],
    target_sdf: Callable[[torch.Tensor], torch.Tensor],
    *,
    batch_size: int = 1024,
    delta: float = 0.1,
    node_count_weight: float = 0.01,
    bbox_min: Tuple[float, float, float] = (-2, -2, -2),
    bbox_max: Tuple[float, float, float] = (2, 2, 2),
    band: float = 0.1,
    seed: Optional[int] = None,
    device: Optional[torch.device] = None,
) -> float:
    """Evaluate agent loss between DSL SDF and target SDF.

    Same flow as the optimiser (compile, evaluator, sample_batch, loss) but no
    optimisation step—just one forward pass. Returns SDF loss + node count penalty.

    Args:
        dsl_or_flatir: DSL source code (str) or FlatIR dict. If str, compiles first.
        target_sdf: Callable (N,3) -> (N,) returns target SDF values.
        batch_size: Number of points to sample.
        delta: L1 clamped loss delta.
        node_count_weight: Weight for node count penalty (default 0.01).
        bbox_min: (x_min, y_min, z_min).
        bbox_max: (x_max, y_max, z_max).
        band: Hard pool band |target| < band.
        seed: If provided, use for reproducibility.
        device: Torch device.

    Returns:
        Agent eval loss: SDF loss + node_count_weight * node_count.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if seed is not None:
        torch.manual_seed(seed)

    flatir = t2g.compile(dsl_or_flatir) if isinstance(dsl_or_flatir, str) else dsl_or_flatir
    evaluator, _ = get_or_create_evaluator(flatir)
    evaluator.to(device)
    evaluator.eval()

    points, _ = sample_batch(
        batch_size, bbox_min, bbox_max, target_sdf, band, hard_pool=[], device=device
    )

    with torch.no_grad():
        pred = evaluator(points)
        target_vals = target_sdf(points)

    node_count = len(flatir.get("instrs", []))
    return agent_eval_loss(pred, target_vals, node_count, delta, node_count_weight)


def optimise_params_for_target(
    dsl: str,
    target_sdf: Callable[[torch.Tensor], torch.Tensor],
    *,
    steps: int = 500,
    batch_size: int = 1024,
    lr: float = 1e-3,
    delta: float = 0.1,
    bbox_min: Tuple[float, float, float] = (-2, -2, -2),
    bbox_max: Tuple[float, float, float] = (2, 2, 2),
    band: float = 0.1,
    device: Optional[torch.device] = None,
) -> Dict[str, Any]:
    """Compile DSL, optimise parameters to match target SDF, return updated FlatIR dict.

    Args:
        dsl: DSL source code.
        target_sdf: Callable (N,3) -> (N,) returns target SDF values.
        steps: Optimization steps.
        batch_size: Points per step.
        lr: Adam learning rate.
        delta: L1 clamped loss delta.
        bbox_min: (x_min, y_min, z_min).
        bbox_max: (x_max, y_max, z_max).
        band: Hard pool band.
        device: Torch device.

    Returns:
        Updated FlatIR dict (params written back).
    """
    flatir = t2g.compile(dsl)
    return optimise_params(
        flatir,
        target_sdf,
        steps=steps,
        batch_size=batch_size,
        lr=lr,
        delta=delta,
        bbox_min=bbox_min,
        bbox_max=bbox_max,
        band=band,
        device=device,
    )
