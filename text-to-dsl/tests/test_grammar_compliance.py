"""
Grammar and syntax compliance tests for SDF DSL.
Uses validate_dsl subprocess; includes token-level smoke test for transformers-cfg.
"""

import pytest
import sys
from pathlib import Path

# Add parent for inference module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inference import validate_dsl

# Valid DSL fixtures from ir_tests.cpp
VALID_DSL = [
    "%0 = sphere(1.0)\nreturn %0",
    "%0 = sphere(1.0)\n%1 = box(1.0, 1.0, 1.0)\n%2 = unite(%0, %1)\nreturn %2",
    "%0 = sphere(0.5)\n%1 = translate(2.0, 0.0, 0.0)\n%2 = apply(%1, %0)\nreturn %2",
    "%0 = sphere(1.0)\n%1 = box(0.5, 0.5, 0.5)\n%2 = subtract(%0, %1)\nreturn %2",
    "%0 = sphere(1.0)\n%1 = box(1.0, 1.0, 1.0)\n%2 = unite(%0, %1)\nreturn %2",
    "%0 = sphere(1.0)\n%1 = box(1.0, 1.0, 1.0)\n%2 = plane(0.0, 1.0, 0.0, 0.0)\n%3 = unite(%0, %1, %2)\nreturn %3",
    "%0 = plane(0.0, 1.0, 0.0, 0.0)\nreturn %0",
    "%0 = box(1.0, 1.0, 1.0)\n%1 = scale(2.0, 2.0, 2.0)\n%2 = apply(%1, %0)\nreturn %2",
    "%0 = plane(0.0, -1.0, 0.0, 0.0)\nreturn %0",
]

# Invalid DSL fixtures from ir_tests.cpp: (dsl, expected_error_substring)
INVALID_DSL = [
    ("%0 = sphere(1.0)\n%1 = box(1.0, 1.0, 1.0)\n%2 = unite(%0, %1)", "return"),
    ("%0 = foo(1.0)", "unknown"),
    ("%0 = unite(%1, %2)\nreturn %0", ""),  # undefined ref
    (
        "%0 = sphere(1.0)\n%1 = apply(%0, %0)\nreturn %1",
        "",
    ),  # apply type mismatch
    ("%0 = sphere(1.0)\n%x = box(1,1,1)", "digit"),
    ("%0 = sphere(1.0)\nreturn %0\nx", "unexpected"),
    ("%0 = sphere(1e99)\nreturn %0", "invalid"),
    ("%0 = sphere(nan)\nreturn %0", "number"),
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
    """At least one valid fixture per production: sphere, box, plane, unite, intersect, subtract, apply, translate, scale."""
    productions = {
        "sphere": "%0 = sphere(1.0)\nreturn %0",
        "box": "%0 = box(1.0, 1.0, 1.0)\nreturn %0",
        "plane": "%0 = plane(0.0, 1.0, 0.0, 0.0)\nreturn %0",
        "unite": "%0 = sphere(1.0)\n%1 = box(0.5, 0.5, 0.5)\n%2 = unite(%0, %1)\nreturn %2",
        "intersect": "%0 = sphere(1.0)\n%1 = box(0.5, 0.5, 0.5)\n%2 = intersect(%0, %1)\nreturn %2",
        "subtract": "%0 = sphere(1.0)\n%1 = box(0.5, 0.5, 0.5)\n%2 = subtract(%0, %1)\nreturn %2",
        "apply": "%0 = sphere(0.5)\n%1 = translate(2.0, 0.0, 0.0)\n%2 = apply(%1, %0)\nreturn %2",
        "translate": "%0 = sphere(0.5)\n%1 = translate(2.0, 0.0, 0.0)\n%2 = apply(%1, %0)\nreturn %2",
        "scale": "%0 = box(1.0, 1.0, 1.0)\n%1 = scale(2.0, 2.0, 2.0)\n%2 = apply(%1, %0)\nreturn %2",
    }
    for name, dsl in productions.items():
        ok, err = validate_dsl(dsl)
        assert ok, f"Grammar coverage for {name}: {dsl!r} -> {err}"


@pytest.mark.skipif(
    not __import__("inference").HAS_TRANSFORMERS_CFG,
    reason="transformers-cfg not installed",
)
def test_token_level_smoke():
    """Verify minimal DSL tokenizes and IncrementalGrammarConstraint creates with DeepSeek tokenizer."""
    from transformers import AutoTokenizer
    from transformers_cfg.grammar_utils import IncrementalGrammarConstraint

    base = Path(__file__).resolve().parent.parent
    grammar_path = base / "grammar.gbnf"
    with open(grammar_path) as f:
        grammar_str = f.read()

    minimal_dsl = "%0 = sphere(1.0)\nreturn %0"

    tokenizer = AutoTokenizer.from_pretrained(
        "deepseek-ai/DeepSeek-Coder-V2-Lite-Base",
        trust_remote_code=True,
    )
    grammar = IncrementalGrammarConstraint(grammar_str, "root", tokenizer)

    # Verify tokenizer produces sensible tokens for minimal DSL
    tokens = tokenizer.encode(minimal_dsl, add_special_tokens=False)
    assert len(tokens) > 0, "Minimal DSL should tokenize to non-empty sequence"
    decoded = tokenizer.decode(tokens)
    assert "sphere" in decoded and "return" in decoded, "Tokenization should preserve keywords"
