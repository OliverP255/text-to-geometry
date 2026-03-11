"""
Grammar and syntax compliance tests for SDF DSL.
Uses validate_dsl subprocess.
"""

import pytest
import sys
from pathlib import Path

# Add parent for inference module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inference import validate_dsl

# Valid DSL fixtures from ir_tests.cpp
VALID_DSL = [
    "s0 = sphere(r=1.0)\nreturn s0",
    "s0 = sphere(r=1.0)\ns1 = box(x=1.0, y=1.0, z=1.0)\ns2 = union(s0, s1)\nreturn s2",
    "s0 = sphere(r=0.5)\nt0 = translate(x=2.0, y=0.0, z=0.0)\ns1 = apply(t0, s0)\nreturn s1",
    "s0 = sphere(r=1.0)\ns1 = box(x=0.5, y=0.5, z=0.5)\ns2 = subtract(s0, s1)\nreturn s2",
    "s0 = sphere(r=1.0)\ns1 = box(x=1.0, y=1.0, z=1.0)\ns2 = union(s0, s1)\nreturn s2",
    "s0 = sphere(r=1.0)\ns1 = box(x=1.0, y=1.0, z=1.0)\ns2 = plane(nx=0.0, ny=1.0, nz=0.0, d=0.0)\ns3 = union(s0, s1, s2)\nreturn s3",
    "s0 = plane(nx=0.0, ny=1.0, nz=0.0, d=0.0)\nreturn s0",
    "s0 = box(x=1.0, y=1.0, z=1.0)\nt0 = scale(x=2.0, y=2.0, z=2.0)\ns1 = apply(t0, s0)\nreturn s1",
    "s0 = plane(nx=0.0, ny=-1.0, nz=0.0, d=0.0)\nreturn s0",
]

# Invalid DSL fixtures from ir_tests.cpp: (dsl, expected_error_substring)
INVALID_DSL = [
    ("s0 = sphere(r=1.0)\ns1 = box(x=1.0, y=1.0, z=1.0)\ns2 = union(s0, s1)", "return"),
    ("s0 = foo(r=1.0)", "unknown"),
    ("s0 = union(s1, s2)\nreturn s0", ""),  # undefined ref
    (
        "s0 = sphere(r=1.0)\ns1 = apply(s0, s0)\nreturn s1",
        "",
    ),  # apply type mismatch
    ("s0 = sphere(r=1.0)\nq0 = box(x=1,y=1,z=1)", "expected"),
    ("s0 = sphere(r=1.0)\nreturn s0\nx", "unexpected"),
    ("s0 = sphere(r=1e99)\nreturn s0", "invalid"),
    ("s0 = sphere(r=nan)\nreturn s0", "number"),
]


def test_validate_dsl_executable_available():
    """validate_dsl must be findable (build it with 'make validate_dsl')."""
    from inference import _find_validate_dsl

    exe = _find_validate_dsl()
    assert exe is not None, "validate_dsl not found - run 'make validate_dsl' from project root"


def test_valid_dsl_fixtures():
    """All valid DSL fixtures must pass validation."""
    for dsl in VALID_DSL:
        ok, err = validate_dsl(dsl)
        assert ok, f"Expected valid DSL to pass: {dsl!r} -> {err}"


def test_invalid_dsl_fixtures():
    """All invalid DSL fixtures must fail validation with expected error."""
    for dsl, expected_sub in INVALID_DSL:
        ok, err = validate_dsl(dsl)
        assert not ok, f"Expected invalid DSL to fail: {dsl!r}"
        if expected_sub:
            assert expected_sub in err.lower(), f"Expected '{expected_sub}' in error: {err}"


def test_grammar_coverage():
    """At least one valid fixture per production: sphere, box, plane, union, intersect, subtract, apply, translate, scale."""
    productions = {
        "sphere": "s0 = sphere(r=1.0)\nreturn s0",
        "box": "s0 = box(x=1.0, y=1.0, z=1.0)\nreturn s0",
        "plane": "s0 = plane(nx=0.0, ny=1.0, nz=0.0, d=0.0)\nreturn s0",
        "union": "s0 = sphere(r=1.0)\ns1 = box(x=0.5, y=0.5, z=0.5)\ns2 = union(s0, s1)\nreturn s2",
        "intersect": "s0 = sphere(r=1.0)\ns1 = box(x=0.5, y=0.5, z=0.5)\ns2 = intersect(s0, s1)\nreturn s2",
        "subtract": "s0 = sphere(r=1.0)\ns1 = box(x=0.5, y=0.5, z=0.5)\ns2 = subtract(s0, s1)\nreturn s2",
        "apply": "s0 = sphere(r=0.5)\nt0 = translate(x=2.0, y=0.0, z=0.0)\ns1 = apply(t0, s0)\nreturn s1",
        "translate": "s0 = sphere(r=0.5)\nt0 = translate(x=2.0, y=0.0, z=0.0)\ns1 = apply(t0, s0)\nreturn s1",
        "scale": "s0 = box(x=1.0, y=1.0, z=1.0)\nt0 = scale(x=2.0, y=2.0, z=2.0)\ns1 = apply(t0, s0)\nreturn s1",
    }
    for name, dsl in productions.items():
        ok, err = validate_dsl(dsl)
        assert ok, f"Grammar coverage for {name}: {dsl!r} -> {err}"


