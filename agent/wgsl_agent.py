#!/usr/bin/env python3
"""
Text-to-CAD agent: WGSL SDF code generation via tool calls.

The agent uses tool calls to generate, validate, render, and submit WGSL code.
It iterates until satisfied with the result.

Usage:
    python wgsl_agent.py
    python wgsl_agent.py --once "a snowman made of three spheres"

Vertex AI: Set T2G_BACKEND=vertex, T2G_VERTEX_PROJECT_ID, T2G_MODEL_ID=claude-opus-4-6
Extended thinking: Set T2G_CLAUDE_BUDGET_TOKENS=4096
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "agent"))

from inference import load_llm
from tools import TOOLS, execute_tool, get_current_code, set_current_code, post_wgsl_scene

SERVER_URL = os.environ.get("SCENE_SERVER_URL", "http://localhost:5001/scene/wgsl")

# ---------------------------------------------------------------------------
# System prompt for WGSL SDF generation
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert SDF (Signed Distance Function) artist. Given a description, write WGSL code that defines the shape mathematically.

## Workflow
1. Call generate_wgsl with your complete fn map(p: vec3f) -> f32 code
2. Call validate_wgsl to check for syntax errors
3. If invalid, use edit_wgsl to fix specific errors or regenerate
4. Call render_wgsl to see the result visually
5. If it doesn't look perfect, use edit_wgsl for small tweaks or regenerate for major changes
6. Call submit_wgsl only when you are completely satisfied with the shape

## Available Tools
- generate_wgsl: Generate complete WGSL SDF code
- edit_wgsl: Find/replace in existing code for incremental changes
- validate_wgsl: Check for syntax errors
- render_wgsl: Render to image (4 views: front, top, side, back)
- submit_wgsl: Push to viewer

## When to use edit_wgsl vs generate_wgsl
- Use edit_wgsl for small tweaks (changing a radius, position, blend amount)
- Use generate_wgsl when starting fresh or making major structural changes

### Coordinate system
Y-axis is up. Objects centred near origin. Most shapes fit within 0.5–2.0 units.

### Primitives (library functions)
| Function | Signature |
|----------|-----------|
| `sdSphere(p, r)` | Sphere |
| `sdBox(p, vec3f(hx,hy,hz))` | Box (half-extents) |
| `sdRoundBox(p, vec3f(hx,hy,hz), r)` | Rounded box |
| `sdTorus(p, vec2f(R,r))` | Torus (major R, tube r) |
| `sdCylinder(p, h, r)` | Y-cylinder (h=HALF-HEIGHT first, r=RADIUS second) |
| `sdCylinderX(p, h, r)` / `sdCylinderZ(p, h, r)` | Horizontal cylinders |
| `sdCapsule(p, a, b, r)` | Capsule between two vec3f points |
| `sdCone(p, c, h)` | IQ cone: `c = vec2f(sin(α), cos(α))`, `h` = height |
| `sdHemisphere(p, r)` | Dome (+Y) |
| `sdEllipsoid(p, vec3f(rx,ry,rz))` | Ellipsoid |
| `sdHexPrism(p, vec2f(hexR, halfH))` | Hex prism |

### Operations
| Function | Description |
|----------|-------------|
| `opU(d1, d2)` | Hard union |
| `opS(d1, d2)` | Subtract d2 from d1 |
| `opI(d1, d2)` | Intersection |
| `opSmoothUnion(d1, d2, k)` | Smooth blend — k=0.05 tight, k=0.2 organic, k=0.4 blobby |
| `opOnion(d, t)` | Shell (wall thickness t) |
| `opRound(d, r)` | Round all edges by r |

### Transforms
| `p - vec3f(x,y,z)` | Translate |
| `opRotateX/Y/Z(p, radians)` | Rotate |
| `opTwist(p, k)` | Twist around Y |

### Rules
- Output ONLY `fn map(p: vec3f) -> f32 { ... }` — no extra functions
- Use `let` for all variables; never reuse a variable name
- Only ONE `return` statement per function
- `sdCylinder(p, h, r)`: h = HALF-HEIGHT (first), r = RADIUS (second)
- Prefer `opSmoothUnion` over `opU` for organic shapes
"""

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

MAX_TURNS = 20


def run_agent(
    llm: Any,
    user_prompt: str,
    *,
    max_tokens: int = 4096,
    effort: str | None = None,
    verbose: bool = False,
) -> Optional[str]:
    """
    Run the WGSL agent with tool calls.

    The agent iterates until it calls submit_wgsl or exhausts max turns.
    Returns the final WGSL code, or None if unsuccessful.
    """
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Create a 3D shape: {user_prompt}"},
    ]

    submitted_code: Optional[str] = None

    for turn in range(MAX_TURNS):
        if verbose:
            print(f"[turn {turn + 1}/{MAX_TURNS}] Calling model...")

        # Check if backend supports tools (duck typing)
        supports_tools = getattr(llm, "supports_tools", False)
        if verbose:
            print(f"  LLM type: {type(llm).__name__}")
            print(f"  supports_tools: {supports_tools}")

        if supports_tools:
            # First turn: disable thinking for immediate response
            # Subsequent turns: use adaptive thinking with effort
            response = llm.chat(
                messages,
                max_tokens=max_tokens,
                effort=effort if turn > 0 else None,
                disable_thinking=(turn == 0),
                tools=TOOLS,
            )
        else:
            # vLLM doesn't support tools in the same way
            if verbose:
                print("[WARN] Backend doesn't support tools, using direct generation")
            text = llm.chat(messages, max_tokens=max_tokens)
            return _extract_code_from_text(text)

        # Check stop reason
        stop_reason = getattr(response, "stop_reason", "end_turn")

        if stop_reason == "tool_use":
            # Process tool calls
            tool_results = []
            assistant_content = []

            for block in response.content:
                block_dict = {
                    "type": block.type,
                }
                if hasattr(block, "id"):
                    block_dict["id"] = block.id
                if hasattr(block, "name"):
                    block_dict["name"] = block.name
                if hasattr(block, "input"):
                    block_dict["input"] = block.input
                if hasattr(block, "text"):
                    block_dict["text"] = block.text
                assistant_content.append(block_dict)

                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id

                    if verbose:
                        print(f"  Tool call: {tool_name}({list(tool_input.keys())})")

                    # Execute tool
                    result = execute_tool(tool_name, dict(tool_input), server_url=SERVER_URL)

                    if verbose:
                        result_preview = {k: (v[:50] + "..." if isinstance(v, str) and len(v) > 50 else v)
                                         for k, v in result.items() if k != "image_base64"}
                        if "image_base64" in result:
                            result_preview["image_base64"] = f"<{len(result['image_base64'])} chars>"
                        print(f"  Result: {result_preview}")

                    # Track submission
                    if tool_name == "submit_wgsl" and result.get("success"):
                        submitted_code = get_current_code()

                    # Build tool result content
                    if "image_base64" in result:
                        # Vertex AI doesn't support images in tool results
                        # Just return success status and image dimensions
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps({
                                "success": True,
                                "rendered": True,
                                "message": "Rendered 4 views (front, top, side, back). Check if the shape looks correct.",
                                "image_size_bytes": result.get("image_size_bytes", 0),
                            }),
                        })
                    else:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result),
                        })

            # Append assistant message and tool results
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        elif stop_reason == "end_turn":
            # Model finished with text response
            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text

            if verbose:
                print(f"  Text response: {text[:200]}...")

            # Check if we have code to return
            current = get_current_code()
            if current:
                return current
            return _extract_code_from_text(text)

        else:
            if verbose:
                print(f"  Stop reason: {stop_reason}")
            break

    return submitted_code or get_current_code()


def _extract_code_from_text(text: str) -> Optional[str]:
    """Extract WGSL code from text response."""
    import re

    # Look for code blocks
    wgsl_match = re.search(r"```wgsl\s*(.*?)\s*```", text, re.DOTALL)
    if wgsl_match:
        return wgsl_match.group(1).strip()

    generic_match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if generic_match:
        code = generic_match.group(1).strip()
        if "fn map" in code:
            return code

    # Look for fn map directly
    fn_match = re.search(r"fn\s+map\s*\([^)]*\)\s*->\s*f32\s*\{", text)
    if fn_match:
        # Find the matching closing brace
        start = fn_match.start()
        brace_count = 0
        for i, c in enumerate(text[start:], start):
            if c == "{":
                brace_count += 1
            elif c == "}":
                brace_count -= 1
                if brace_count == 0:
                    return text[start:i + 1].strip()

    return None


# Alias for backward compatibility with server.py
extract_code_block = _extract_code_from_text


def refine_agent(
    llm: Any,
    current_code: str,
    instruction: str,
    *,
    verbose: bool = False,
) -> Optional[str]:
    """Refine existing WGSL code based on a follow-up instruction.

    This is a simplified version that runs the agent with a refinement prompt.
    """
    prompt = f"Modify this WGSL code to: {instruction}\n\nCurrent code:\n```wgsl\n{current_code}\n```"
    return run_agent(llm, prompt, verbose=verbose)


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
    parser.add_argument("--verbose", "-v", action="store_true", help="Print debug information")
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model ID (e.g., claude-opus-4-6 for Vertex, Qwen/Qwen2.5-Coder-32B-Instruct-AWQ for vLLM)",
    )
    args = parser.parse_args()

    model_kwargs = {}
    if args.model:
        model_kwargs["model_id"] = args.model

    print("Loading model...")
    llm = load_llm(**model_kwargs)
    print(f"Model loaded: {llm.model_id if hasattr(llm, 'model_id') else 'vLLM'}\n")

    if args.once is not None:
        code = run_agent(llm, args.once.strip(), verbose=True)
        if code:
            print(f"\nFinal code:\n{code}")
        else:
            print("\nNo code generated")
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

        code = run_agent(llm, prompt, verbose=args.verbose)
        if code:
            print(f"\nGenerated:\n{code}\n")
        else:
            print("\nGeneration failed.\n")


if __name__ == "__main__":
    main()