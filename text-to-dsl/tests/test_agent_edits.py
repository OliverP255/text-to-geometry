"""Tests for agent.apply_edits - find/replace edits only."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_edits import apply_edits


def test_apply_edits_single_replace():
    """Single find/replace updates content correctly."""
    content = "s0=sphere(r=0.5)\nreturn s0"
    edits = [{"find": "0.5", "replace": "1.0"}]
    result = apply_edits(content, edits)
    assert result == "s0=sphere(r=1.0)\nreturn s0"


def test_apply_edits_multiple_ordered():
    """Multiple edits applied in order."""
    content = "s0=sphere(r=0.5)\ns1=box(x=1,y=1,z=1)\nreturn s0"
    edits = [
        {"find": "0.5", "replace": "1.0"},
        {"find": "return s0", "replace": "return s1"},
    ]
    result = apply_edits(content, edits)
    assert result == "s0=sphere(r=1.0)\ns1=box(x=1,y=1,z=1)\nreturn s1"


def test_apply_edits_find_not_found_raises():
    """Raises when find is not in content."""
    content = "s0=sphere(r=1)\nreturn s0"
    edits = [{"find": "nonexistent", "replace": "x"}]
    with pytest.raises(ValueError, match="find not found"):
        apply_edits(content, edits)


def test_apply_edits_empty_edits():
    """Empty edits list returns original content."""
    content = "s0=sphere(r=1)\nreturn s0"
    result = apply_edits(content, [])
    assert result == content


def test_apply_edits_whitespace_sensitive():
    """Exact match (including whitespace) required."""
    content = "s0=sphere(r=1)\nreturn s0"
    edits = [{"find": "sphere(r=1)", "replace": "sphere(r=2)"}]
    result = apply_edits(content, edits)
    assert result == "s0=sphere(r=2)\nreturn s0"

    # Wrong whitespace - should not match
    edits_bad = [{"find": "sphere( r=1 )", "replace": "x"}]
    with pytest.raises(ValueError, match="find not found"):
        apply_edits(content, edits_bad)
