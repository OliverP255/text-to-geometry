"""Parameter optimization for FlatIR SDF."""

import torch
from typing import Callable, List, Tuple, Optional, Dict, Any


def _refill_hard_pool(
    pool: List[torch.Tensor],
    target_sdf: Callable,
    bbox_min: Tuple[float, float, float],
    bbox_max: Tuple[float, float, float],
    band: float,
    pool_size: int,
    device: torch.device,
) -> None:
    """Refill hard pool via rejection sampling. Modifies pool in place."""
    pool.clear()
    bmin = torch.tensor(bbox_min, device=device, dtype=torch.float32)
    bmax = torch.tensor(bbox_max, device=device, dtype=torch.float32)
    attempts = 0
    max_attempts = pool_size * 20
    while len(pool) < pool_size and attempts < max_attempts:
        pts = torch.rand(pool_size - len(pool), 3, device=device, dtype=torch.float32)
        pts = bmin + pts * (bmax - bmin)
        vals = target_sdf(pts)
        mask = vals.abs() < band
        kept = pts[mask]
        for i in range(kept.shape[0]):
            pool.append(kept[i])
            if len(pool) >= pool_size:
                break
        attempts += 1


def sample_batch(
    batch_size: int,
    bbox_min: Tuple[float, float, float],
    bbox_max: Tuple[float, float, float],
    target_sdf: Callable,
    band: float = 0.1,
    hard_pool: Optional[List[torch.Tensor]] = None,
    device: Optional[torch.device] = None,
) -> Tuple[torch.Tensor, List[torch.Tensor]]:
    """Sample a batch of points: 50% uniform in bbox, 50% from hard pool near surface.

    Args:
        batch_size: Total number of points.

        bbox_min: (x_min, y_min, z_min).
        bbox_max: (x_max, y_max, z_max).
        target_sdf: Callable (N,3) -> (N,) returns target SDF values.
        band: Hard pool band |target| < band.
        hard_pool: Mutable pool of near-surface points (refilled if needed).
        device: Torch device.

    Returns:
        (points (batch_size, 3), updated hard_pool).
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if hard_pool is None:
        hard_pool = []

    n_uniform = batch_size // 2
    n_hard = batch_size - n_uniform

    bmin = torch.tensor(bbox_min, device=device, dtype=torch.float32)
    bmax = torch.tensor(bbox_max, device=device, dtype=torch.float32)

    uniform_pts = bmin + torch.rand(n_uniform, 3, device=device, dtype=torch.float32) * (bmax - bmin)

    if len(hard_pool) < n_hard:
        _refill_hard_pool(hard_pool, target_sdf, bbox_min, bbox_max, band, max(n_hard, 256), device)

    if hard_pool:
        n_take = min(n_hard, len(hard_pool))
        indices = torch.randperm(len(hard_pool), device=device)[:n_take]
        hard_pts = torch.stack([hard_pool[i] for i in indices.tolist()])
        if n_take < n_hard:
            hard_pts = torch.cat([hard_pts, uniform_pts[: n_hard - n_take]], dim=0)
    else:
        hard_pts = uniform_pts[:n_hard]

    points = torch.cat([uniform_pts, hard_pts], dim=0)
    return points, hard_pool


def optimise_params(
    flatir_dict: Dict[str, Any],
    target_sdf: Callable,
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
    """Optimize FlatIR parameters to match target SDF.

    Args:
        flatir_dict: FlatIR dict from compile().
        target_sdf: Callable (N,3) -> (N,) target SDF.
        steps: Optimization steps.
        batch_size: Points per step.
        lr: Adam learning rate.
        delta: L1 clamped loss delta.
        bbox_min/max: Sampling bounds.
        band: Hard pool band.
        device: Torch device.

    Returns:
        Updated flatir_dict (params written back).
    """
    from evaluator_cache import get_or_create_evaluator
    from loss import l1_clamped_loss

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    evaluator, _ = get_or_create_evaluator(flatir_dict)
    evaluator.to(device)
    evaluator.train()

    optimizer = torch.optim.Adam(evaluator.parameters(), lr=lr)
    hard_pool: List[torch.Tensor] = []

    for step in range(steps):
        optimizer.zero_grad()
        points, hard_pool = sample_batch(
            batch_size, bbox_min, bbox_max, target_sdf, band, hard_pool, device
        )
        pred = evaluator(points)
        target_vals = target_sdf(points)
        loss = l1_clamped_loss(pred, target_vals, delta)
        loss.backward()
        optimizer.step()

    evaluator.eval()

    # Write optimized params back to flatir_dict
    import text_to_geometry_bindings as t2g
    params = []
    for p in evaluator.parameters():
        params.extend(p.detach().cpu().numpy().tolist())
    t2g.writeBackParams(flatir_dict, params)

    return flatir_dict
