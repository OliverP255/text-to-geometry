"""Tests for agent context at each phase - persistent prefix + short phase body."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_context import AGENT_DSL_GUIDE, PLAN_RUBRIC_SUFFIX

PREFIX_ALL = AGENT_DSL_GUIDE.rstrip() + "\n\n"
PREFIX_PLAN = PREFIX_ALL + PLAN_RUBRIC_SUFFIX.rstrip() + "\n\n"


def _plan_phase_body(user_input: str) -> str:
    """Phase-specific tail (after persistent prefix) for plan."""
    return "Plan out the DSL: " + user_input


def _full_plan_prompt(user_input: str) -> str:
    return PREFIX_PLAN + _plan_phase_body(user_input)


def test_context_plan_phase():
    """Plan uses DSL guide + plan rubric + short task; no write/choose tails."""
    user_input = "a sphere with radius 1"
    ctx = _full_plan_prompt(user_input)
    assert ctx.startswith(AGENT_DSL_GUIDE[:30])
    assert "Plan phase" in ctx
    assert "Plan out the DSL:" in ctx
    assert user_input in ctx
    assert "Write the DSL from the plan" not in _plan_phase_body(user_input)
    assert "Choose" not in _plan_phase_body(user_input)


def _write_dsl_body(plan_content: str) -> str:
    return "Write the DSL from the plan:\n\n" + plan_content


def _full_write_prompt(plan_content: str) -> str:
    return PREFIX_ALL + _write_dsl_body(plan_content)


def test_context_write_dsl_phase():
    """Write DSL: persistent guide + plan excerpt; phase body has no choice menu."""
    plan_content = "1. Create sphere s0 with r=1\n2. Return s0"
    ctx = _full_write_prompt(plan_content)
    assert AGENT_DSL_GUIDE[:30] in ctx
    assert "Write the DSL from the plan" in ctx
    assert plan_content in ctx
    assert "Choose" not in _write_dsl_body(plan_content)


def _edit_plan_body(plan_content: str) -> str:
    return "Provide edits to the plan (find/replace only):\n\n" + plan_content


def _full_edit_plan_prompt(plan_content: str) -> str:
    return PREFIX_ALL + _edit_plan_body(plan_content)


def _edit_dsl_body(dsl_content: str) -> str:
    return "Provide edits to the DSL (find/replace only):\n\n" + dsl_content


def _full_edit_dsl_prompt(dsl_content: str) -> str:
    return PREFIX_ALL + _edit_dsl_body(dsl_content)


def test_context_edit_plan_phase():
    """Edit plan: guide prefix + edit instruction + plan text."""
    plan_content = "1. Sphere\n2. Return"
    ctx = _full_edit_plan_prompt(plan_content)
    assert "Provide edits to the plan" in ctx
    assert plan_content in ctx
    assert AGENT_DSL_GUIDE[:20] in ctx


def test_context_edit_dsl_phase():
    """Edit DSL: guide prefix + edit instruction + DSL text."""
    dsl_content = "s0=sphere(r=1)\nreturn s0"
    ctx = _full_edit_dsl_prompt(dsl_content)
    assert "Provide edits to the DSL" in ctx
    assert dsl_content in ctx


def test_context_no_prompt_history_in_phase_bodies():
    """Phase tails stay isolated; persistent prefix is shared, not prior chat turns."""
    plan_tail = _plan_phase_body("a sphere")
    assert "Write the DSL from the plan" not in plan_tail
    assert "Choose" not in plan_tail

    write_tail = _write_dsl_body("plan here")
    assert "Plan out the DSL" not in write_tail
    assert "Choose" not in write_tail


def test_choice_includes_status_and_guide_when_built():
    """Choice prompt in production is PREFIX_ALL + status + menu + plan + DSL (smoke)."""
    status = "Status:\n- compile: ok\n\n"
    menu = "Choose one of: edit_plan\n\nPlan:\np\n\nDSL:\nd\n\nChoice:"
    full_choice = PREFIX_ALL + status + menu
    assert "Status:" in full_choice
    assert "Choose one of:" in full_choice
    assert AGENT_DSL_GUIDE[:25] in full_choice
