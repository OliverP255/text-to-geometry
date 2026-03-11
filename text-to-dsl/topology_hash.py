"""Topology hash for FlatIR - deterministic hash from instr structure only (not params)."""

import hashlib


def topology_hash(flatir_dict: dict) -> str:
    """Compute deterministic hash from DAG structure (instrs) only.

    Same topology (instr sequence) gives same hash regardless of parameter values.
    Different topology gives different hash.

    Args:
        flatir_dict: FlatIR dict with 'instrs' key. Each instr has op, arg0, arg1, constIdx.

    Returns:
        Hex string hash (SHA256).
    """
    instrs = flatir_dict.get("instrs", [])
    # Build canonical representation: tuple of (op, arg0, arg1, constIdx) per instr
    parts = []
    for instr in instrs:
        if isinstance(instr, dict):
            parts.append((
                instr.get("op", 0),
                instr.get("arg0", 0),
                instr.get("arg1", 0),
                instr.get("constIdx", 0),
            ))
        else:
            parts.append((0, 0, 0, 0))
    data = str(tuple(parts)).encode("utf-8")
    return hashlib.sha256(data).hexdigest()
