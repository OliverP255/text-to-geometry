"""Choice and edit JSON parsing tests."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import parse_choice, parse_edit_json


def test_parse_choice_edit_plan():
    """edit_plan parses correctly."""
    assert parse_choice("edit_plan") == "edit_plan"


def test_parse_choice_edit_dsl():
    """edit_dsl parses correctly."""
    assert parse_choice("edit_dsl") == "edit_dsl"


def test_parse_choice_submit():
    """submit parses correctly."""
    assert parse_choice("submit") == "submit"


def test_parse_choice_rewrite_plan():
    """rewrite_plan parses correctly."""
    assert parse_choice("rewrite_plan") == "rewrite_plan"


def test_parse_choice_rewrite_dsl():
    """rewrite_dsl parses correctly."""
    assert parse_choice("rewrite_dsl") == "rewrite_dsl"


def test_parse_choice_eval_loss():
    """eval_loss parses correctly (training only)."""
    assert parse_choice("eval_loss", training=True) == "eval_loss"
    with pytest.raises(ValueError, match="Unknown choice"):
        parse_choice("eval_loss", training=False)


def test_parse_choice_optimise_dsl():
    """optimise_dsl parses correctly (training only)."""
    assert parse_choice("optimise_dsl", training=True) == "optimise_dsl"
    with pytest.raises(ValueError, match="Unknown choice"):
        parse_choice("optimise_dsl", training=False)


def test_parse_choice_strips_whitespace():
    """Leading/trailing whitespace stripped."""
    assert parse_choice("  edit_plan  ") == "edit_plan"
    assert parse_choice("\nedit_dsl\n") == "edit_dsl"


def test_parse_edit_plan_json_valid():
    """Valid edit_plan JSON parses."""
    s = '{"tool": "edit_plan", "edits": [{"find": "x", "replace": "y"}]}'
    d = parse_edit_json(s, "edit_plan")
    assert d["edits"] == [{"find": "x", "replace": "y"}]


def test_parse_edit_dsl_json_valid():
    """Valid edit_dsl JSON parses."""
    s = '{"tool": "edit_dsl", "edits": [{"find": "r=0.5", "replace": "r=1.0"}]}'
    d = parse_edit_json(s, "edit_dsl")
    assert d["edits"] == [{"find": "r=0.5", "replace": "r=1.0"}]


def test_parse_edit_json_invalid_raises():
    """Malformed JSON raises."""
    with pytest.raises(json.JSONDecodeError):
        parse_edit_json("{ invalid }", "edit_plan")


def test_parse_edit_json_missing_edits_raises():
    """Missing edits raises."""
    with pytest.raises(ValueError, match="Missing 'edits'"):
        parse_edit_json('{"tool": "edit_plan"}', "edit_plan")
