"""Tests for agent_tools: evaluate_loss and optimise_params_for_target."""

import sys
from pathlib import Path

import pytest

# Add build for text_to_geometry_bindings, text-to-dsl for modules
_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "build"))
sys.path.insert(0, str(_root / "text-to-dsl"))

from agent_tools import evaluate_loss, optimise_params_for_target
from target_sdf import sphere_target


def test_evaluate_loss_returns_float():
    """Valid DSL, sphere target, returns scalar."""
    dsl = "s0=sphere(r=1)\nreturn s0"
    target = sphere_target(radius=1.0)
    loss = evaluate_loss(dsl, target, seed=42)
    assert isinstance(loss, float)
    assert loss >= 0


def test_evaluate_loss_reproducible():
    """Same seed gives same result."""
    dsl = "s0=sphere(r=1)\nreturn s0"
    target = sphere_target(radius=1.0)
    loss1 = evaluate_loss(dsl, target, seed=123)
    loss2 = evaluate_loss(dsl, target, seed=123)
    assert loss1 == loss2


def test_optimise_params_for_target_returns_dict():
    """Valid DSL, returns FlatIR with updated params."""
    dsl = "s0=sphere(r=0.5)\nreturn s0"
    target = sphere_target(radius=1.0)
    result = optimise_params_for_target(dsl, target, steps=50, batch_size=256)
    assert isinstance(result, dict)
    assert "instrs" in result
    assert "spheres" in result
    assert "transforms" in result
    assert len(result["spheres"]) >= 1


def test_optimise_params_for_target_decreases_loss():
    """Loss after optimisation < loss before."""
    import torch

    torch.manual_seed(123)
    dsl = "s0=sphere(r=0.5)\nreturn s0"
    target = sphere_target(radius=1.0)
    loss_before = evaluate_loss(dsl, target, seed=123)
    result = optimise_params_for_target(dsl, target, steps=200, batch_size=512)
    loss_after = evaluate_loss(result, target, seed=123)
    assert loss_after < loss_before, f"Loss should decrease: {loss_before:.6f} -> {loss_after:.6f}"
    assert result["spheres"][0]["r"] > 0.5
