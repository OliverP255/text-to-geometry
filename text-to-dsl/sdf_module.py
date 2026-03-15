"""PyTorch SDF module - primitives, transforms, CSG, FlatIR conversion."""

import torch
import torch.nn as nn
from typing import Dict, List, Any

# FlatOp enum values (match C++ kernel::FlatOp)
EVAL_SPHERE = 0
EVAL_BOX = 1
EVAL_PLANE = 2
CSG_UNION = 3
CSG_INTERSECT = 4
CSG_SUBTRACT = 5


def sdf_sphere(p: torch.Tensor, r: torch.Tensor) -> torch.Tensor:
    """Sphere SDF: ||p|| - r. p: (N,3), r: scalar or (N,) -> (N,)."""
    d = torch.norm(p, dim=-1) - r.squeeze()
    return d


def sdf_box(p: torch.Tensor, half_extents: torch.Tensor) -> torch.Tensor:
    """Box SDF. p: (N,3), half_extents: (3,) or (N,3) -> (N,)."""
    q = torch.abs(p) - half_extents
    outside = torch.norm(torch.relu(q), dim=-1)
    inside = torch.clamp(torch.max(q, dim=-1)[0], max=0)
    return outside + inside


def sdf_plane(p: torch.Tensor, normal: torch.Tensor, d: torch.Tensor) -> torch.Tensor:
    """Plane SDF: dot(p, normal) + d. p: (N,3), normal: (3,), d: scalar -> (N,)."""
    return (p * normal).sum(-1) + d.squeeze()


def _min_scale(sx: torch.Tensor, sy: torch.Tensor, sz: torch.Tensor) -> torch.Tensor:
    """Min of scale components for SDF scaling."""
    return torch.minimum(torch.minimum(sx, sy), sz)


def _flatten_flatir(flatir_dict: Dict[str, Any]) -> tuple:
    """Convert FlatIR dict (semantic: list of dicts) to flat arrays for SDFModule."""
    transforms = flatir_dict.get("transforms", [])
    spheres = flatir_dict.get("spheres", [])
    boxes = flatir_dict.get("boxes", [])
    planes = flatir_dict.get("planes", [])

    def flat_transforms() -> List[float]:
        out: List[float] = []
        for t in transforms:
            if isinstance(t, dict):
                out.extend([t.get("tx", 0), t.get("ty", 0), t.get("tz", 0),
                            t.get("sx", 1), t.get("sy", 1), t.get("sz", 1)])
            else:
                out.append(float(t))
        return out if out else [0, 0, 0, 1, 1, 1]

    def flat_spheres() -> List[float]:
        out: List[float] = []
        for s in spheres:
            out.append(float(s["r"]) if isinstance(s, dict) else float(s))
        return out if out else [1.0]

    def flat_boxes() -> List[float]:
        out: List[float] = []
        for b in boxes:
            if isinstance(b, dict):
                out.extend([b.get("hx", 1), b.get("hy", 1), b.get("hz", 1)])
            else:
                out.append(float(b))
        return out if out else [1, 1, 1]

    def flat_planes() -> List[float]:
        out: List[float] = []
        for p in planes:
            if isinstance(p, dict):
                out.extend([p.get("nx", 0), p.get("ny", 1), p.get("nz", 0), p.get("d", 0)])
            else:
                out.append(float(p))
        return out if out else [0, 1, 0, 0]

    return flat_transforms(), flat_spheres(), flat_boxes(), flat_planes()


class SDFModule(nn.Module):
    """PyTorch nn.Module that evaluates FlatIR SDF at points (N,3) -> (N,)."""

    def __init__(self, flatir_dict: Dict[str, Any]):
        super().__init__()
        self.instrs = flatir_dict.get("instrs", [])
        self.root_temp = flatir_dict.get("rootTemp", 0)

        # Build parameter tensors from FlatIR (supports semantic dict format)
        transforms, spheres, boxes, planes = _flatten_flatir(flatir_dict)
        self.transforms = nn.Parameter(torch.tensor(transforms, dtype=torch.float32))
        self.spheres = nn.Parameter(torch.tensor(spheres, dtype=torch.float32))
        self.boxes = nn.Parameter(torch.tensor(boxes, dtype=torch.float32))
        self.planes = nn.Parameter(torch.tensor(planes, dtype=torch.float32))

    def _get_transform(self, idx: int) -> tuple:
        """Get (translate, scale) tensors for transform index."""
        base = idx * 6
        t = self.transforms[base : base + 6]
        translate = t[:3]
        scale = t[3:6]
        return translate, scale

    def forward(self, points: torch.Tensor) -> torch.Tensor:
        """Evaluate SDF at points. points: (N,3) -> (N,)."""
        if not self.instrs:
            return torch.full((points.shape[0],), 1e10, device=points.device, dtype=points.dtype)

        temps: List[torch.Tensor] = []

        for instr in self.instrs:
            op = instr.get("op", 0)
            arg0 = instr.get("arg0", 0)
            arg1 = instr.get("arg1", 0)
            const_idx = instr.get("constIdx", 0)

            if op == EVAL_SPHERE:
                translate, scale = self._get_transform(arg0)
                p_local = (points - translate) / scale.clamp(min=1e-6)
                r = self.spheres[const_idx]
                d_local = sdf_sphere(p_local, r)
                s = _min_scale(scale[0], scale[1], scale[2])
                temps.append(d_local * s)
            elif op == EVAL_BOX:
                translate, scale = self._get_transform(arg0)
                p_local = (points - translate) / scale.clamp(min=1e-6)
                he = self.boxes[const_idx * 3 : const_idx * 3 + 3]
                d_local = sdf_box(p_local, he)
                s = _min_scale(scale[0], scale[1], scale[2])
                temps.append(d_local * s)
            elif op == EVAL_PLANE:
                translate, scale = self._get_transform(arg0)
                p_local = (points - translate) / scale.clamp(min=1e-6)
                n = self.planes[const_idx * 4 : const_idx * 4 + 3]
                d = self.planes[const_idx * 4 + 3]
                d_local = sdf_plane(p_local, n, d)
                s = _min_scale(scale[0], scale[1], scale[2])
                temps.append(d_local * s)
            elif op == CSG_UNION:
                a = temps[arg0] if arg0 < len(temps) else torch.full((points.shape[0],), 1e10, device=points.device, dtype=points.dtype)
                b = temps[arg1] if arg1 < len(temps) else torch.full((points.shape[0],), 1e10, device=points.device, dtype=points.dtype)
                temps.append(torch.minimum(a, b))
            elif op == CSG_INTERSECT:
                a = temps[arg0] if arg0 < len(temps) else torch.full((points.shape[0],), 1e10, device=points.device, dtype=points.dtype)
                b = temps[arg1] if arg1 < len(temps) else torch.full((points.shape[0],), 1e10, device=points.device, dtype=points.dtype)
                temps.append(torch.maximum(a, b))
            elif op == CSG_SUBTRACT:
                a = temps[arg0] if arg0 < len(temps) else torch.full((points.shape[0],), 1e10, device=points.device, dtype=points.dtype)
                b = temps[arg1] if arg1 < len(temps) else torch.full((points.shape[0],), 1e10, device=points.device, dtype=points.dtype)
                temps.append(torch.maximum(a, -b))

        if self.root_temp < len(temps):
            return temps[self.root_temp]
        return torch.full((points.shape[0],), 1e10, device=points.device, dtype=points.dtype)
