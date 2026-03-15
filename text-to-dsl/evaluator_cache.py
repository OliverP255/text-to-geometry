"""Topology-based evaluator cache for FlatIR."""

from typing import Dict, Any, Tuple
from topology_hash import topology_hash
from sdf_module import SDFModule


_cache: Dict[str, SDFModule] = {}


def get_or_create_evaluator(flatir_dict: dict) -> Tuple[SDFModule, bool]:
    """Get or create PyTorch evaluator for FlatIR topology.

    Args:
        flatir_dict: FlatIR dict from compile().

    Returns:
        (evaluator, was_cached). Evaluator has params loaded from flatir_dict.
    """
    h = topology_hash(flatir_dict)
    if h in _cache:
        evaluator = _cache[h]
        _load_params(evaluator, flatir_dict)
        return evaluator, True

    evaluator = SDFModule(flatir_dict)
    _cache[h] = evaluator
    return evaluator, False


def _load_params(evaluator: SDFModule, flatir_dict: dict) -> None:
    """Load params from flatir_dict into evaluator (in-place)."""
    import torch
    from sdf_module import _flatten_flatir

    t, s, b, p = _flatten_flatir(flatir_dict)
    tt = torch.tensor(t, dtype=evaluator.transforms.dtype, device=evaluator.transforms.device)
    ss = torch.tensor(s, dtype=evaluator.spheres.dtype, device=evaluator.spheres.device)
    bb = torch.tensor(b, dtype=evaluator.boxes.dtype, device=evaluator.boxes.device)
    pp = torch.tensor(p, dtype=evaluator.planes.dtype, device=evaluator.planes.device)

    evaluator.transforms.data.copy_(tt)
    evaluator.spheres.data.copy_(ss)
    evaluator.boxes.data.copy_(bb)
    evaluator.planes.data.copy_(pp)


def clear_cache() -> None:
    """Clear the evaluator cache (for testing)."""
    _cache.clear()
