"""
Grammar-constrained DSL generation for SDF geometry.
Uses vLLM with StructuredOutputsParams (grammar) for grammar-constrained decoding. Model: GLM-4.7-Flash.
"""

from __future__ import annotations

from vllm import LLM
from vllm.sampling_params import SamplingParams, StructuredOutputsParams

import os
import subprocess
from pathlib import Path


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


# Few-shot context so GLM understands the DSL format (kept short for faster prefill)
DSL_CONTEXT = """SDF DSL. sN=shape, tN=transform. Primitives: sphere(r), box(x,y,z), plane(nx,ny,nz,d). Transforms: translate(x,y,z), scale(x,y,z). CSG: union, intersect, subtract. Apply: apply(t,s).
Example: s0=sphere(r=1)\nreturn s0
Generate DSL for: """

# Module-level cache: (model_id, tensor_parallel_size, max_model_len) -> LLM
_llm_cache: dict[tuple[str, int, int], LLM] = {}


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


def load_llm(
    model_id: str = "zai-org/GLM-4.7-Flash",
    tensor_parallel_size: int = 1,
    max_model_len: int = 1024,
    enable_prefix_caching: bool = True,
    gpu_memory_utilization: float = 0.95,
    **kwargs,
) -> LLM:
    """Load an LLM instance. Reuse the returned object across generate_dsl calls to avoid reloading."""
    cache_key = (model_id, tensor_parallel_size, max_model_len)
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]
    llm = LLM(
        model=model_id,
        trust_remote_code=True,
        tensor_parallel_size=tensor_parallel_size,
        max_model_len=max_model_len,
        enable_prefix_caching=enable_prefix_caching,
        enable_chunked_prefill=True,
        gpu_memory_utilization=gpu_memory_utilization,
        **kwargs,
    )
    _llm_cache[cache_key] = llm
    return llm


def warmup_prefix_cache(llm: LLM, dsl_context: str = DSL_CONTEXT) -> None:
    """Run a warmup generation to populate the prefix cache for dsl_context."""
    base = Path(__file__).resolve().parent
    with open(base / "grammar_dsl.gbnf") as f:
        grammar_str = f.read()
    structured = StructuredOutputsParams(grammar=grammar_str)
    sampling = SamplingParams(structured_outputs=structured, max_tokens=16)
    llm.generate(prompts=[dsl_context + "warmup"], sampling_params=sampling)


def generate_dsl(
    prompt: str,
    model_id: str = "zai-org/GLM-4.7-Flash",
    dsl_context: str | None = DSL_CONTEXT,
    grammar_path: str | Path | None = None,
    max_new_tokens: int = 64,
    temperature: float = 0.2,
    top_p: float = 0.95,
    repetition_penalty: float = 1.05,
    tensor_parallel_size: int = 1,
    max_model_len: int = 1024,
    llm: LLM | None = None,
) -> str:
    """
    Generate DSL from prompt using grammar-constrained decoding.
    Uses vLLM with StructuredOutputsParams (grammar). Model: GLM-4.7-Flash.
    Pass llm from load_llm() to reuse a loaded model across calls.
    """

    base = Path(__file__).resolve().parent
    grammar_path = grammar_path or base / "grammar_dsl.gbnf"
    with open(grammar_path) as f:
        grammar_str = f.read()

    full_prompt = (dsl_context or "") + prompt

    if llm is None:
        llm = load_llm(
            model_id=model_id,
            tensor_parallel_size=tensor_parallel_size,
            max_model_len=max_model_len,
        )

    structured = StructuredOutputsParams(grammar=grammar_str)
    sampling = SamplingParams(
        structured_outputs=structured,
        max_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
    )

    outputs = llm.generate(prompts=[full_prompt], sampling_params=sampling)
    return outputs[0].outputs[0].text.strip()


def generate_with_grammar(
    prompt: str,
    grammar_path: str | Path,
    max_new_tokens: int = 256,
    temperature: float = 0.2,
    top_p: float = 0.95,
    repetition_penalty: float = 1.05,
    llm: LLM | None = None,
    model_id: str = "zai-org/GLM-4.7-Flash",
    **kwargs,
) -> str:
    """
    Generate text with a specific grammar. No DSL context prefix.
    Used for plan phase, choice phase, edit phase, etc.
    """
    return generate_dsl(
        prompt=prompt,
        dsl_context="",  # No context - caller provides full prompt
        grammar_path=grammar_path,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
        repetition_penalty=repetition_penalty,
        llm=llm,
        model_id=model_id,
        **kwargs,
    )


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
