#!/usr/bin/env python3
"""
Text-to-CAD agent: WGSL SDF code generation via Qwen3-32B-FP8 (default).

Usage: python wgsl_agent.py
       python wgsl_agent.py --once "a snowman made of three spheres"

Reads a text prompt, generates WGSL SDF code (fn map(p: vec3f) -> f32),
validates it, and POSTs to the scene server.

If you run `python3 wgsl_agent.py` with system Python, we re-exec using repo .venv when present
(so torch/vLLM import). Set T2G_NO_VENV_REEXEC=1 to disable.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "agent"))

from inference import generate_wgsl_code, load_llm
from wgsl_validator import validate_wgsl_with_fallback

if TYPE_CHECKING:
    from vllm import LLM
else:
    LLM = Any

SERVER_URL = os.environ.get("SCENE_SERVER_URL", "http://localhost:5001/scene/wgsl")

# ---------------------------------------------------------------------------
# System prompt for WGSL SDF generation
# ---------------------------------------------------------------------------

WGSL_SYSTEM_PROMPT = """\
You are a 3D CAD geometry assistant. Given a text description, write a WGSL SDF function.

CRITICAL: Output ONLY the code. No explanation, no markdown, no comments outside the function.

fn map(p: vec3f) -> f32 {
  // code here
}

### Coordinate system
Y-axis is up. Objects should be centred near the origin.

### Scale reference
- Bolts, nuts, small gears:   0.02 – 0.1 units
- Hand tools, knobs, brackets: 0.1 – 0.5 units  
- Furniture, large parts:      0.5 – 2.0 units

### Primitives

| Function | Description |
|----------|-------------|
| `sdSphere(p, r)` | Sphere radius r |
| `sdBox(p, vec3f(x,y,z))` | Box, half-extents x y z |
| `sdRoundBox(p, vec3f(x,y,z), r)` | Rounded box, corner radius r |
| `sdTorus(p, vec2f(R,r))` | Torus, major radius R, tube radius r |
| `sdCylinder(p, h, r)` | Cylinder, Y-aligned, half-height h, radius r |
| `sdCapsule(p, a, b, r)` | Capsule from point a to point b, radius r |
| `sdCone(p, vec2f(sin_a, cos_a), h)` | Cone, tip at origin pointing +Y |
| `sdEllipsoid(p, vec3f(rx,ry,rz))` | Ellipsoid, per-axis radii |
| `sdHexPrism(p, vec2f(hexRadius, halfHeight))` | Hexagonal prism, Y-aligned |

### CSG Operations

| Function | Description |
|----------|-------------|
| `opU(d1, d2)` | Union — combine shapes |
| `opI(d1, d2)` | Intersection — keep only overlap |
| `opS(d1, d2)` | Subtract d2 from d1 |
| `opSmoothUnion(d1, d2, k)` | Smooth union — k=0.05 tight, k=0.2 organic, k=0.4 very soft |
| `opRepPolar(p, n)` | Repeat shape n times around Y axis |
| `opOnion(d, t)` | Shell — hollow out a shape to wall thickness t |

### Transforms

| Function | Description |
|----------|-------------|
| `p - vec3f(x,y,z)` | Translate (use inline) |
| `opRotateX(p, a)` | Rotate around X, a in radians |
| `opRotateY(p, a)` | Rotate around Y, a in radians |
| `opRotateZ(p, a)` | Rotate around Z, a in radians |

Common angles: 90° = 1.5708  45° = 0.7854  30° = 0.5236

### Key Patterns

**Hollow tube** — inner h slightly larger than outer to avoid end-cap artifacts:
```wgsl
fn map(p: vec3f) -> f32 {
  let outer = sdCylinder(p, 0.5, 0.4);
  let inner = sdCylinder(p, 0.6, 0.3);  // taller and narrower
  return opS(outer, inner);
}
```

**Washer** — same principle, disc with punched hole:
```wgsl
fn map(p: vec3f) -> f32 {
  let disc = sdCylinder(p, 0.05, 0.5);
  let hole = sdCylinder(p, 0.06, 0.2);  // slightly taller
  return opS(disc, hole);
}
```

**Stepped shaft** — overlap joins by 0.01 to avoid seams:
```wgsl
fn map(p: vec3f) -> f32 {
  let base = sdCylinder(p - vec3f(0.0, -0.26, 0.0), 0.25, 0.4);
  let shaft = sdCylinder(p - vec3f(0.0,  0.31, 0.0), 0.30, 0.2);
  return opU(base, shaft);
}
```

**L-bracket** — two boxes joined at corner:
```wgsl
fn map(p: vec3f) -> f32 {
  let vert  = sdBox(p - vec3f(0.0,  0.5, 0.0), vec3f(0.1, 0.5, 0.3));
  let horiz = sdBox(p - vec3f(0.35, 0.0, 0.0), vec3f(0.35, 0.1, 0.3));
  return opU(vert, horiz);
}
```

**Rotated part** — apply opRotateX/Y/Z before the primitive:
```wgsl
fn map(p: vec3f) -> f32 {
  let q = opRotateZ(p - vec3f(0.6, 0.0, 0.0), 1.5708);  // horizontal cylinder
  return sdCylinder(q, 0.6, 0.08);
}
```

**Radial repeat** — for gear teeth, bolt holes, fins:
```wgsl
fn map(p: vec3f) -> f32 {
  let body = sdCylinder(p, 0.1, 0.5);
  let q = opRepPolar(p, 6.0);  // 6 holes equally spaced
  let hole = sdCylinder(q - vec3f(0.35, 0.0, 0.0), 0.12, 0.05);
  return opS(body, hole);
}
```



### Rules
- Output ONLY `fn map(p: vec3f) -> f32 { ... }` — no extra functions, no surrounding text
- Use `let` for all variables
- For subtraction: inner shape must be slightly larger in the cut axis than the outer
- Always overlap joined parts by ~0.01 to avoid seam artifacts
"""
# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------

def _finalize_wgsl_extraction(s: str) -> str:
    """Strip markdown junk, ``wgsl typos, and leading text before fn map."""
    t = s.strip()
    for _ in range(10):
        prev = t
        t = re.sub(r"^`{3,}\w*\s*", "", t)
        t = re.sub(r"^`{2}wgsl\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"^`+\s*\n", "", t)
        t = t.strip()
        if t == prev:
            break
    if "```" in t:
        t = t.split("```", 1)[0].strip()
    m = re.search(r"\bfn\s+map\s*\(\s*p\s*:\s*vec3f\s*\)\s*->\s*f32", t)
    if m is not None and m.start() > 0:
        t = t[m.start() :].strip()
    return t


def extract_code_block(text: str) -> str:
    """Extract WGSL code from markdown code blocks or return as-is."""
    raw = text.strip()
    wgsl_match = re.search(r"```wgsl\s*(.*?)\s*```", raw, re.DOTALL)
    if wgsl_match:
        return _finalize_wgsl_extraction(wgsl_match.group(1))

    generic_match = re.search(r"```\s*(.*?)\s*```", raw, re.DOTALL)
    if generic_match:
        return _finalize_wgsl_extraction(generic_match.group(1))

    return _finalize_wgsl_extraction(raw)


# ---------------------------------------------------------------------------
# POST to server
# ---------------------------------------------------------------------------

def post_wgsl_scene(code: str, url: str = SERVER_URL) -> tuple[bool, Optional[str]]:
    """POST WGSL code to the scene server. Returns (ok, error_message)."""
    data = json.dumps({"code": code}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                body = resp.read().decode()
                return False, f"HTTP {resp.status}: {body[:200]}"
            return True, None
    except urllib.error.URLError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Error feedback for retry loop
# ---------------------------------------------------------------------------

def _error_feedback(error_kind: str, detail: str, suggestion: str = "", code: str = "") -> str:
    """Construct error feedback message for the LLM to self-correct."""
    parts = [f"Error: {error_kind}", detail]
    if suggestion:
        parts.append(f"Suggestion: {suggestion}")
    if code:
        parts.append(f"Your code:\n```wgsl\n{code}\n```")
    parts.append("Please fix and output only the corrected `fn map(p: vec3f) -> f32 { ... }` function.")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Agent retry loop
# ---------------------------------------------------------------------------

MAX_RETRIES = 3


def run_agent(
    llm: LLM | None,
    user_prompt: str,
    *,
    attempt_post: bool = True,
    verbose: bool = False,
    max_retries: int = MAX_RETRIES,
) -> Optional[str]:
    """
    Generate WGSL SDF code from a text prompt with validation and retry.

    Args:
        llm: The loaded LLM instance
        user_prompt: Natural language description of the 3D shape
        attempt_post: Whether to POST the result to the scene server
        verbose: Print debug information
        max_retries: Maximum number of retry attempts after initial generation

    Returns:
        The WGSL code on success, None if all attempts exhausted
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": WGSL_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    for attempt in range(1, max_retries + 2):  # 1 initial + max_retries
        is_retry = attempt > 1
        label = f"(attempt {attempt}/{max_retries + 1}) " if is_retry else ""

        if verbose:
            print(f"{label}Generating WGSL for: {user_prompt!r}")

        # --- Generation ---
        if llm is None:
            print("run_agent: llm is None", flush=True)
            return None
        if not verbose:
            print("Generating WGSL…", flush=True)
        try:
            raw_output = generate_wgsl_code(messages, llm)
        except Exception as e:
            err_str = str(e)
            if verbose:
                print(f"{label}[ERROR] Generation failed: {err_str}")
            if attempt <= max_retries:
                messages.append({"role": "user", "content": f"Generation error: {err_str}. Try again."})
                continue
            return None

        # Extract code block if wrapped in markdown
        code = extract_code_block(raw_output)

        if verbose:
            print(f"{label}Generated code ({len(code)} chars)")

        # --- Validation ---
        ok, err, suggestion = validate_wgsl_with_fallback(code)
        if not ok:
            if verbose:
                print(f"{label}[ERROR] Validation failed: {err}")
            if attempt <= max_retries:
                feedback = _error_feedback("Invalid WGSL", err, suggestion, code)
                messages.append({"role": "assistant", "content": raw_output})
                messages.append({"role": "user", "content": feedback})
                continue
            return None

        if verbose:
            print(f"{label}Validation passed")
            print(f"  Code:\n    {code.replace(chr(10), chr(10) + '    ')}")

        # --- POST to server ---
        if attempt_post:
            ok, err = post_wgsl_scene(code)
            if ok:
                if verbose:
                    print(f"{label}Pushed to viewer")
            else:
                if verbose:
                    print(f"{label}[WARN] Could not push: {err}")
                # Don't retry on POST errors - code is valid

        return code

    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _maybe_reexec_in_venv() -> None:
    """Re-exec into repo .venv if running with system Python."""
    if os.environ.get("T2G_NO_VENV_REEXEC"):
        return
    venv_python = _root / ".venv" / "bin" / "python3"
    if venv_python.is_file() and sys.executable != str(venv_python):
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)


def main() -> None:
    import argparse

    _maybe_reexec_in_venv()

    parser = argparse.ArgumentParser(description="Text-to-CAD WGSL SDF agent")
    parser.add_argument("--once", type=str, default=None, help="Run once with this prompt and exit")
    parser.add_argument("--no-post", action="store_true", help="Skip POSTing to scene server")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print debug information")
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="vLLM HuggingFace model id (default: Qwen/Qwen3-32B-FP8, or T2G_MODEL_ID)",
    )
    args = parser.parse_args()

    model_kwargs = {}
    if args.model:
        model_kwargs["model_id"] = args.model

    print("Loading model...")
    llm = load_llm(**model_kwargs)
    print("Model loaded.\n")

    attempt_post = not args.no_post

    if args.once is not None:
        run_agent(llm, args.once.strip(), attempt_post=attempt_post, verbose=True)
        return

    print("Ready. Describe a shape or scene. Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            prompt = input("Describe shape: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not prompt:
            continue
        if prompt.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break

        run_agent(llm, prompt, attempt_post=attempt_post, verbose=args.verbose)
        print()


if __name__ == "__main__":
    main()