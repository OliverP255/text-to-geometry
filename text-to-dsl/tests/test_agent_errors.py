"""Error handling tests for agent."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_edits import apply_edits
from agent import parse_choice, parse_edit_json


def test_apply_edits_find_not_found():
    """Clear error when find is missing."""
    with pytest.raises(ValueError, match="find not found"):
        apply_edits("hello world", [{"find": "xyz", "replace": "a"}])


def test_agent_edit_parse_failure():
    """Invalid edit JSON returns clear error."""
    with pytest.raises(Exception):  # JSONDecodeError or ValueError
        parse_edit_json("{ invalid }", "edit_plan")


def test_agent_choice_unknown():
    """Unknown choice string is handled safely."""
    with pytest.raises(ValueError, match="Unknown choice"):
        parse_choice("invalid_choice")
