"""
Grammar-constrained DSL generation for SDF geometry.
Uses transformers-cfg for token-level grammar decoding with DeepSeek-Coder-V2-Lite-Base.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

# Optional: transformers-cfg for grammar-constrained decoding
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from transformers_cfg.grammar_utils import IncrementalGrammarConstraint
    from transformers_cfg.generation.logits_process import GrammarConstrainedLogitsProcessor
    HAS_TRANSFORMERS_CFG = True
except ImportError:
    HAS_TRANSFORMERS_CFG = False


def _find_validate_dsl() -> Path | None:
    """Locate the validate_dsl executable."""
    base = Path(__file__).resolve().parent
    candidates = [
        base.parent / "build" / "validate_dsl",
        base / "build" / "validate_dsl",
        Path("build/validate_dsl"),
        Path("./validate_dsl"),
    ]
    for p in candidates:
        if p.is_file() and os.access(p, os.X_OK):
            return p
    return None


# Few-shot context so DeepSeek understands the DSL format
DSL_CONTEXT = """SDF DSL for signed-distance-field geometry. Format:
%N = <primitive|op>(args)
return %N

Primitives: sphere(r), box(x,y,z), plane(nx,ny,nz,d)
Transforms: translate(x,y,z), scale(x,y,z)
CSG: unite(%a,%b,...), intersect(%a,%b,...), subtract(%a,%b)
Apply: apply(transform_var, shape_var). Define vars before use.

Example - "a unit sphere":
%0 = sphere(1.0)
return %0

Example - "sphere and box union":
%0 = sphere(1.0)
%1 = box(0.5, 0.5, 0.5)
%2 = unite(%0, %1)
return %2

Generate DSL for: """


def validate_dsl(dsl: str) -> tuple[bool, str]:
    """
    Validate DSL via validate_dsl CLI. Returns (ok, error_message).
    """
    exe = _find_validate_dsl()
    if not exe:
        return False, "validate_dsl executable not found (run 'make validate_dsl' from project root)"

    result = subprocess.run(
        [str(exe)],
        input=dsl,
        capture_output=True,
        text=True,
        timeout=5,
    )

    if result.returncode == 0:
        return True, ""
    return False, (result.stderr or result.stdout or "unknown error").strip()


def generate_dsl(
    prompt: str,
    model_id: str = "deepseek-ai/DeepSeek-Coder-V2-Lite-Base",
    dsl_context: str | None = DSL_CONTEXT,
    grammar_path: str | Path | None = None,
    max_new_tokens: int = 256,
    temperature: float = 0.2,
    top_p: float = 0.95,
    repetition_penalty: float = 1.05,
    device: str | None = None,
) -> str:
    """
    Generate DSL from prompt using grammar-constrained decoding.
    Requires transformers-cfg and a loaded model.
    """
    if not HAS_TRANSFORMERS_CFG:
        raise RuntimeError("transformers-cfg is required. Install with: pip install transformers-cfg")

    base = Path(__file__).resolve().parent
    grammar_path = grammar_path or base / "grammar.gbnf"
    with open(grammar_path) as f:
        grammar_str = f.read()

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        trust_remote_code=True,
        dtype=torch.bfloat16 if device == "cuda" else torch.float32,
    ).to(device)

    grammar = IncrementalGrammarConstraint(grammar_str, "root", tokenizer)
    grammar_processor = GrammarConstrainedLogitsProcessor(grammar)

    full_prompt = (dsl_context or "") + prompt
    inputs = tokenizer(full_prompt, return_tensors="pt", add_special_tokens=True).to(device)
    input_len = inputs["input_ids"].shape[1]

    output = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        do_sample=temperature > 0,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
        logits_processor=[grammar_processor],
    )

    generated = tokenizer.decode(output[0][input_len:], skip_special_tokens=True)
    return generated.strip()


def generate_valid_dsl(
    prompt: str,
    max_retries: int = 3,
    **kwargs,
) -> str | None:
    """
    Generate DSL and validate via compileIR. Retries up to max_retries on semantic failure.
    Returns valid DSL string or None if all retries fail.
    """
    for _ in range(max_retries):
        dsl = generate_dsl(prompt, **kwargs)
        ok, err = validate_dsl(dsl)
        if ok:
            return dsl
        # Could log err and retry with adjusted prompt; for now just retry
    return None


def quick_test(prompt: str = "a box translated by 2, 0, 0") -> None:
    """Quick test: generate DSL with context and print output."""
    print("Quick test - prompt:", repr(prompt))
    print("Generating...")
    dsl = generate_dsl(prompt)
    print("Output DSL:")
    print(dsl)
    ok, err = validate_dsl(dsl)
    print("Valid:", ok, ("- " + err if err else ""))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Running quick test (no args). Usage: python inference.py <prompt>")
        quick_test()
    else:
        prompt = " ".join(sys.argv[1:])
        print("Generating DSL for:", repr(prompt))
        result = generate_valid_dsl(prompt)
        if result:
            print(result)
        else:
            print("Failed to generate valid DSL after retries", file=sys.stderr)
            sys.exit(1)




