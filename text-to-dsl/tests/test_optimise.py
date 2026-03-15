"""Tests for FlatIR parameter optimization."""

import sys
from pathlib import Path

import pytest

# Add build for text_to_geometry_bindings, text-to-dsl for modules
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "build"))
sys.path.insert(0, str(_root / "text-to-dsl"))


def test_compile_returns_dict():
    import text_to_geometry_bindings as t2g

    d = t2g.compile("s0=sphere(r=1)\nreturn s0")
    assert "instrs" in d
    assert "spheres" in d
    assert len(d["spheres"]) == 1
    assert d["spheres"][0]["r"] == 1.0


def test_serialize_deserialize_roundtrip():
    import text_to_geometry_bindings as t2g

    d = t2g.compile("s0=sphere(r=1)\nreturn s0")
    b = t2g.serialize(d)
    d2 = t2g.deserialize(b)
    assert d2["instrs"] == d["instrs"]
    assert d2["spheres"] == d["spheres"]


def test_extract_writeback_roundtrip():
    import text_to_geometry_bindings as t2g

    d = t2g.compile("s0=sphere(r=1)\nreturn s0")
    params = t2g.extractParams(d)
    params[6] = 2.0
    t2g.writeBackParams(d, params)
    assert d["spheres"][0]["r"] == 2.0


def test_topology_hash_same_topology():
    import text_to_geometry_bindings as t2g
    from topology_hash import topology_hash

    d1 = t2g.compile("s0=sphere(r=1)\nreturn s0")
    d2 = t2g.compile("s0=sphere(r=2)\nreturn s0")
    assert topology_hash(d1) == topology_hash(d2)


def test_topology_hash_different_topology():
    import text_to_geometry_bindings as t2g
    from topology_hash import topology_hash

    d1 = t2g.compile("s0=sphere(r=1)\nreturn s0")
    d2 = t2g.compile(
        "s0=sphere(r=1)\nt0=translate(x=2,y=0,z=0)\ns1=sphere(r=1)\ns2=apply(t0,s1)\ns3=union(s0,s2)\nreturn s3"
    )
    assert topology_hash(d1) != topology_hash(d2)


def test_evaluator_cache():
    import text_to_geometry_bindings as t2g
    from evaluator_cache import get_or_create_evaluator, clear_cache

    clear_cache()
    d1 = t2g.compile("s0=sphere(r=1)\nreturn s0")
    ev1, c1 = get_or_create_evaluator(d1)
    assert not c1
    ev2, c2 = get_or_create_evaluator(d1)
    assert c2
    assert ev1 is ev2


def test_sdf_sphere():
    import torch
    import text_to_geometry_bindings as t2g
    from sdf_module import SDFModule

    d = t2g.compile("s0=sphere(r=1)\nreturn s0")
    m = SDFModule(d)
    pts = torch.tensor([[1.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    out = m(pts)
    assert abs(out[0].item()) < 0.01
    assert abs(out[1].item() - 1.0) < 0.01


def test_l1_clamped_loss():
    import torch
    from loss import l1_clamped_loss

    pred = torch.tensor([0.0, 0.0])
    target = torch.tensor([0.5, 0.05])
    loss = l1_clamped_loss(pred, target, delta=0.1)
    assert abs(loss.item() - 0.075) < 1e-5


def test_optimise_converges():
    import text_to_geometry_bindings as t2g
    from optimise_params import optimise_params
    from target_sdf import sphere_target

    d = t2g.compile("s0=sphere(r=0.5)\nreturn s0")
    target = sphere_target(radius=1.0)
    d = optimise_params(d, target, steps=200, batch_size=512)
    assert d["spheres"][0]["r"] > 0.6
