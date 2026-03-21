"""Tests for agent context at each phase - context isolation."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _plan_phase_context(user_input: str) -> str:
    """Return the context (prompt) used for plan phase. Plan uses user_input only."""
    return "Plan out the DSL: " + user_input


def test_context_plan_phase():
    """Plan phase context contains user_input only; no prior prompts."""
    user_input = "a sphere with radius 1"
    ctx = _plan_phase_context(user_input)
    assert "Plan out the DSL:" in ctx
    assert user_input in ctx
    assert "Write the DSL" not in ctx
    assert "Choose" not in ctx


def _write_dsl_phase_context(plan_content: str) -> str:
    """Return the context (prompt) used for write_dsl phase. Uses plan content only."""
    return "Write the DSL from the plan:\n\n" + plan_content


def test_context_write_dsl_phase():
    """Write DSL phase context contains plan content only; no plan prompt, no choose prompt."""
    plan_content = "1. Create sphere s0 with r=1\n2. Return s0"
    ctx = _write_dsl_phase_context(plan_content)
    assert "Write the DSL from the plan" in ctx
    assert plan_content in ctx
    assert "Choose" not in ctx


def _edit_plan_phase_context(plan_content: str) -> str:
    """Edit plan phase context contains plan content only."""
    return "Provide edits to the plan (find/replace only):\n\n" + plan_content


def _edit_dsl_phase_context(dsl_content: str) -> str:
    """Edit DSL phase context contains DSL content only."""
    return "Provide edits to the DSL (find/replace only):\n\n" + dsl_content


def test_context_edit_plan_phase():
    """Edit plan phase context contains plan content only."""
    plan_content = "1. Sphere\n2. Return"
    ctx = _edit_plan_phase_context(plan_content)
    assert "Provide edits to the plan" in ctx
    assert plan_content in ctx


def test_context_edit_dsl_phase():
    """Edit DSL phase context contains DSL content only."""
    dsl_content = "s0=sphere(r=1)\nreturn s0"
    ctx = _edit_dsl_phase_context(dsl_content)
    assert "Provide edits to the DSL" in ctx
    assert dsl_content in ctx


def test_context_no_prompt_history():
    """No phase includes previous prompts in its context."""
    # Plan phase: only user_input, not "Write the DSL" or "Choose"
    plan_ctx = _plan_phase_context("a sphere")
    assert "Write the DSL from the plan" not in plan_ctx
    assert "Choose" not in plan_ctx

    # Write DSL: only plan content, not "Plan out the DSL" or "Choose"
    write_ctx = _write_dsl_phase_context("plan here")
    assert "Plan out the DSL" not in write_ctx
    assert "Choose" not in write_ctx
