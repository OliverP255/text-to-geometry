"""Full end-to-end tests for FlatIR parameter optimization pipeline."""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Add build for text_to_geometry_bindings, text-to-dsl for modules
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "build"))
sys.path.insert(0, str(_root / "text-to-dsl"))

from agent_tools import evaluate_loss


def test_e2e_sphere_optimization():
    """DSL -> compile -> optimise_params -> assert loss decreases and spheres[0] converges."""
    import torch
    import text_to_geometry_bindings as t2g
    from optimise_params import optimise_params
    from target_sdf import sphere_target

    torch.manual_seed(123)
    dsl = "s0=sphere(r=0.5)\nreturn s0"
    flatir = t2g.compile(dsl)
    target = sphere_target(radius=1.0)
    loss_before = evaluate_loss(flatir, target, seed=123)
    result = optimise_params(flatir, target, steps=300, batch_size=512)
    loss_after = evaluate_loss(result, target, seed=123)

    assert loss_after < loss_before, f"Loss should decrease: {loss_before:.6f} -> {loss_after:.6f}"
    assert result["spheres"][0] >= 0.7, f"Expected r >= 0.7, got {result['spheres'][0]}"
    assert loss_after < 0.1, f"Final loss should be below 0.1, got {loss_after:.6f}"


def test_e2e_union_optimization():
    """Union DSL -> compile -> optimise_params -> assert loss decreases and radii change."""
    import torch
    import text_to_geometry_bindings as t2g
    from optimise_params import optimise_params
    from target_sdf import sphere_target

    torch.manual_seed(123)
    dsl = (
        "s0=sphere(r=0.3)\n"
        "t0=translate(x=2,y=0,z=0)\n"
        "s1=sphere(r=0.3)\n"
        "s2=apply(t0,s1)\n"
        "s3=union(s0,s2)\n"
        "return s3"
    )
    flatir = t2g.compile(dsl)
    target = sphere_target(radius=1.0)
    loss_before = evaluate_loss(flatir, target, seed=123)
    result = optimise_params(flatir, target, steps=150, batch_size=512)
    loss_after = evaluate_loss(result, target, seed=123)

    assert loss_after < loss_before, f"Loss should decrease: {loss_before:.6f} -> {loss_after:.6f}"
    assert len(result["spheres"]) == 2
    assert any(r > 0.3 for r in result["spheres"]), (
        f"Expected at least one sphere radius to increase from 0.3, got {result['spheres']}"
    )


def test_e2e_serialize_optimize_roundtrip():
    """compile -> serialize -> deserialize -> optimise_params -> serialize -> deserialize."""
    import torch
    import text_to_geometry_bindings as t2g
    from optimise_params import optimise_params
    from target_sdf import sphere_target

    torch.manual_seed(123)
    dsl = "s0=sphere(r=0.5)\nreturn s0"
    flatir = t2g.compile(dsl)
    target = sphere_target(radius=1.0)
    loss_before = evaluate_loss(flatir, target, seed=123)
    b1 = t2g.serialize(flatir)
    d1 = t2g.deserialize(b1)
    result = optimise_params(d1, target, steps=150, batch_size=512)
    loss_after = evaluate_loss(result, target, seed=123)
    b2 = t2g.serialize(result)
    final = t2g.deserialize(b2)

    assert loss_after < loss_before, f"Loss should decrease: {loss_before:.6f} -> {loss_after:.6f}"
    assert "spheres" in final and "transforms" in final and "instrs" in final
    assert final["spheres"][0] != 0.5
    assert set(final.keys()) == set(flatir.keys())


def test_e2e_cache_reuse():
    """Same topology twice -> second get_or_create_evaluator returns was_cached=True."""
    import torch
    import text_to_geometry_bindings as t2g
    from evaluator_cache import get_or_create_evaluator, clear_cache
    from optimise_params import optimise_params
    from target_sdf import sphere_target

    torch.manual_seed(123)
    clear_cache()
    d1 = t2g.compile("s0=sphere(r=0.5)\nreturn s0")
    ev1, cached1 = get_or_create_evaluator(d1)
    assert not cached1
    target = sphere_target(radius=1.0)
    loss1_before = evaluate_loss(d1, target, seed=123)
    optimise_params(d1, target, steps=50, batch_size=256)
    loss1_after = evaluate_loss(d1, target, seed=123)

    d2 = t2g.compile("s0=sphere(r=0.7)\nreturn s0")
    ev2, cached2 = get_or_create_evaluator(d2)
    assert cached2, "Second call with same topology should hit cache"
    assert ev1 is ev2
    assert loss1_after < loss1_before, "First optimization should decrease loss"


def test_e2e_cli():
    """Run optimise_dsl.py via subprocess -> assert exit 0, output is valid DSL."""
    import os

    import text_to_geometry_bindings as t2g

    dsl = "s0=sphere(r=0.5)\nreturn s0"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".dsl", delete=False) as f:
        f.write(dsl)
        dsl_path = f.name
    try:
        env = {**os.environ, "PYTHONPATH": f"{_root / 'build'}:{_root / 'text-to-dsl'}"}
        result = subprocess.run(
            [sys.executable, str(_root / "text-to-dsl" / "optimise_dsl.py"), dsl_path, "--steps", "100"],
            cwd=str(_root),
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        out = result.stdout.strip()
        assert "s0=" in out or "sphere" in out, f"Expected DSL output, got: {out[:200]}"
        assert "return s" in out, f"Expected return in DSL, got: {out[:200]}"
        # Round-trip: compiled DSL should be valid
        flatir = t2g.compile(out)
        assert "spheres" in flatir and len(flatir["spheres"]) >= 1
        assert flatir["spheres"][0] > 0.5, f"Optimized r should be > 0.5, got {flatir['spheres'][0]}"
    finally:
        Path(dsl_path).unlink(missing_ok=True)


def test_e2e_unparse_dsl_roundtrip():
    """compile -> optimise -> unparseDSL -> compile round-trip; recompiled FlatIR is valid."""
    import torch
    import text_to_geometry_bindings as t2g
    from optimise_params import optimise_params
    from target_sdf import sphere_target

    torch.manual_seed(123)
    dsl = "s0=sphere(r=0.5)\nreturn s0"
    flatir = t2g.compile(dsl)
    target = sphere_target(radius=1.0)
    result = optimise_params(flatir, target, steps=100, batch_size=256)
    dsl_out = t2g.unparseDSL(result)
    assert "sphere" in dsl_out and "return" in dsl_out
    flatir2 = t2g.compile(dsl_out)
    assert len(flatir2["instrs"]) == len(result["instrs"])
    assert flatir2["rootTemp"] == result["rootTemp"]
    assert len(flatir2["spheres"]) >= 1


def test_e2e_compile_invalid_dsl():
    """Invalid DSL raises ValueError with non-empty message."""
    import text_to_geometry_bindings as t2g

    with pytest.raises(ValueError) as excinfo:
        t2g.compile("s0=foo(r=1)\nreturn s0")
    assert len(str(excinfo.value)) > 0
