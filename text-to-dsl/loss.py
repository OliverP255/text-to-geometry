"""L1 clamped loss for SDF optimization."""

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
