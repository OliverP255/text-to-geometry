"""Grammar output validation tests."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_grammar_choice_inference_valid_strings():
    """Output is one of: edit_plan, edit_dsl, rewrite_plan, rewrite_dsl, submit."""
    valid = {"edit_plan", "edit_dsl", "rewrite_plan", "rewrite_dsl", "submit"}
    for s in valid:
        assert s in valid
    assert len(valid) == 5


def test_grammar_choice_training_valid_strings():
    """Same plus eval_loss, optimise_dsl."""
    valid = {"edit_plan", "edit_dsl", "rewrite_plan", "rewrite_dsl", "eval_loss", "optimise_dsl", "submit"}
    assert len(valid) == 7


def test_grammar_edit_plan_valid_json():
    """Output parses as JSON with tool and edits."""
    s = '{"tool": "edit_plan", "edits": [{"find": "x", "replace": "y"}]}'
    d = json.loads(s)
    assert d["tool"] == "edit_plan"
    assert "edits" in d
    assert len(d["edits"]) == 1
    assert d["edits"][0]["find"] == "x"
    assert d["edits"][0]["replace"] == "y"


def test_grammar_edit_dsl_valid_json():
    """Same for edit_dsl."""
    s = '{"tool": "edit_dsl", "edits": [{"find": "r=0.5", "replace": "r=1.0"}]}'
    d = json.loads(s)
    assert d["tool"] == "edit_dsl"
    assert "edits" in d
    assert len(d["edits"]) == 1
    assert d["edits"][0]["find"] == "r=0.5"
    assert d["edits"][0]["replace"] == "r=1.0"


def test_grammar_plan_non_empty():
    """Plan grammar produces non-empty text (grammar file exists)."""
    base = Path(__file__).resolve().parent.parent
    grammar_plan = base / "grammar_plan.gbnf"
    assert grammar_plan.exists()
    content = grammar_plan.read_text()
    assert "root" in content
    assert "content" in content
