"""Target SDF providers for optimization."""

import torch
from typing import Callable


def sphere_target(center: tuple = (0, 0, 0), radius: float = 1.0) -> Callable:
    """Create a target SDF for a sphere."""

    def sdf(points: torch.Tensor) -> torch.Tensor:
        c = torch.tensor(center, dtype=points.dtype, device=points.device)
        d = torch.norm(points - c, dim=-1) - radius
        return d

    return sdf
