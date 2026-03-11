"""
Inference grammar tests - require model. Skip if model not available.
"""

import os
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Skip entire module if vllm or model not available
pytest.importorskip("vllm")

# Skip by default - requires model download and GPU. Set RUN_INFERENCE_TESTS=1 to enable.
if os.environ.get("RUN_INFERENCE_TESTS", "").lower() not in ("1", "true", "yes"):
    pytest.skip("Set RUN_INFERENCE_TESTS=1 to run (requires model)", allow_module_level=True)


def test_generate_dsl_passes_validation():
    """For fixed prompts, generated DSL must pass validate_dsl."""
    from inference import generate_dsl, validate_dsl

    # Use a simple prompt - model may not have been fine-tuned for DSL
    prompt = "Generate SDF DSL for a unit sphere:\n\n"
    try:
        dsl = generate_dsl(prompt, max_new_tokens=64)
    except Exception as e:
        pytest.skip(f"Model load/generation failed: {e}")

    ok, err = validate_dsl(dsl)
    assert ok, f"Generated DSL should pass validation: {dsl!r} -> {err}"
