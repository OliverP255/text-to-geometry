"""L1 clamped loss for SDF optimization. Clamped so that loss only considered for points that are close to the surface of target or predicted."""

import torch


def l1_clamped_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    delta: float = 0.1,
) -> torch.Tensor:
    """L1 clamped loss: clamp pred and target to [-delta, delta], then L1 of difference, then mean.

    Args:
        pred: Predicted SDF values (N,).
        target: Target SDF values (N,).
        delta: Clamp threshold (default 0.1).

    Returns:
        Scalar loss.
    """
    pred_c = pred.clamp(-delta, delta)
    target_c = target.clamp(-delta, delta)
    return (pred_c - target_c).abs().mean()


def agent_eval_loss(
    pred: torch.Tensor,
    target: torch.Tensor,
    node_count: int,
    delta: float = 0.1,
    node_weight: float = 0.01,
) -> float:
    """Agent evaluation loss: L1 clamped SDF loss + node count penalty.

    Used when the agent evaluates DSL to prefer simpler programs (fewer nodes).

    Args:
        pred: Predicted SDF values (N,).
        target: Target SDF values (N,).
        node_count: Number of instructions in FlatIR (len(instrs)).
        delta: L1 clamped loss clamp threshold (default 0.1).
        node_weight: Weight for node count penalty (default 0.01).

    Returns:
        Combined loss: l1_clamped_loss(pred, target, delta) + node_weight * node_count.
    """
    sdf_loss = l1_clamped_loss(pred, target, delta).item()
    return sdf_loss + node_weight * node_count
