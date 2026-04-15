#!/usr/bin/env python3
"""
Text-to-CAD agent: CadQuery B-Rep code generation via tool calls.

The agent uses tool calls to generate, validate, render, and submit CadQuery code.
It iterates until satisfied with the result.

Usage:
    python brep_agent.py
    python brep_agent.py --once "a 100mm mounting plate with 4 corner holes"

Vertex AI: Set T2G_BACKEND=vertex, T2G_VERTEX_PROJECT_ID, T2G_MODEL_ID=claude-opus-4-6
Extended thinking: Set T2G_CLAUDE_BUDGET_TOKENS=4096
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "agent"))

from inference import load_llm
from brep_tools import TOOLS, execute_tool, get_current_code, set_current_code, post_brep_scene

SERVER_URL = os.environ.get("SCENE_SERVER_URL", "http://localhost:5001/scene/brep")

# ---------------------------------------------------------------------------
# System prompt for CadQuery B-Rep generation
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert CAD engineer using CadQuery (Python parametric CAD). Given a description, write CadQuery Python code that defines the shape precisely.

## Workflow
1. Call generate_cadquery with your complete CadQuery script
2. Call validate_cadquery to check for syntax errors
3. If invalid, use edit_cadquery to fix specific errors or regenerate
4. Call render_cadquery to generate mesh preview
5. If it doesn't look perfect, use edit_cadquery for tweaks or regenerate
6. Call submit_cadquery only when satisfied with the shape

## Available Tools
- generate_cadquery: Generate complete CadQuery Python code
- edit_cadquery: Find/replace in existing code for incremental changes
- validate_cadquery: Check for syntax errors and safety issues
- render_cadquery: Generate mesh for preview
- submit_cadquery: Push to viewer

## When to use edit_cadquery vs generate_cadquery
- Use edit_cadquery for small tweaks (changing a dimension, hole position)
- Use generate_cadquery when starting fresh or making major structural changes

## Coordinate System (CRITICAL)
- **Z-axis is UP** (CAD standard)
- **Units are MILLIMETRES**
- Objects are **centered on origin** by default
- X = width, Y = depth, Z = height

## Workplane Orientation
| Plane | Description |
|-------|-------------|
| `"XY"` | Z-up (default for most shapes) |
| `"XZ"` | Y-up (for Y-extruded shapes) |
| `"YZ"` | X-up (for X-extruded shapes) |

## Face Selectors
| Selector | Meaning |
|----------|---------|
| `">Z"` | Top face (max Z) |
| `"<Z"` | Bottom face (min Z) |
| `">X"` | Right face (max X) |
| `"<X"` | Left face (min X) |
| `">Y"` | Front face (max Y) |
| `"<Y"` | Back face (min Y) |
| `"|Z"` | Vertical edges (parallel to Z) |

## High-Level Primitives (USE THESE - PREFERRED)

These primitives simplify CadQuery code. Always prefer them over raw CadQuery chains.

### Basic Solids
| Function | Description |
|----------|-------------|
| `box(width, depth, height)` | Rectangular box centered on origin |
| `cylinder(radius, height)` | Z-aligned cylinder |
| `cone(r_bottom, r_top, height)` | Cone or truncated cone |
| `sphere(radius)` | Sphere centered on origin |
| `torus(tube_r, ring_r)` | Z-aligned torus |

### Enhanced Solids
| Function | Description |
|----------|-------------|
| `rounded_box(w, d, h, r)` | Box with rounded vertical edges |
| `tube(outer_r, inner_r, h)` | Hollow tube |
| `hollow_box(w, d, h, thickness)` | Open-top hollow box |

### Plates and Brackets
| Function | Description |
|----------|-------------|
| `mounting_plate(w, d, t, hole_d, margin)` | Plate with corner holes |
| `mounting_plate(w, d, t, hole_d, margin, (nx, ny))` | Plate with nx×ny hole grid |
| `corner_bracket(w, h, t, hole_d)` | L-shaped bracket with holes |

### Holes and Features
| Function | Description |
|----------|-------------|
| `counterbore_hole(solid, d, cbore_d, cbore_depth)` | Add counterbore hole |
| `countersink_hole(solid, d, csk_d, angle)` | Add countersink hole |
| `slot(solid, length, width, depth)` | Cut rectangular slot |

### Profile Operations
| Function | Description |
|----------|-------------|
| `extruded_profile(points, height)` | Extrude closed 2D profile |
| `revolved_profile(points, angle)` | Revolve profile around Y-axis |

## Raw CadQuery Reference (for advanced use)

### Basic Operations
| Method | Description |
|--------|-------------|
| `.box(w, d, h)` | Create box |
| `.circle(r)` | Draw circle |
| `.rect(w, h)` | Draw rectangle |
| `.extrude(h)` | Extrude sketch by height |
| `.revolve(angle)` | Revolve sketch around axis |
| `.union(other)` | Boolean union |
| `.cut(other)` | Boolean subtract |
| `.intersect(other)` | Boolean intersection |

### Feature Operations
| Method | Description |
|--------|-------------|
| `.hole(diameter)` | Drill a through-hole |
| `.fillet(radius)` | Round edges |
| `.chamfer(distance)` | Chamfer edges |
| `.shell(thickness)` | Hollow out solid |

## Code Template

```python
import cadquery as cq
from cadquery_primitives import mounting_plate, rounded_box

# Create your geometry
result = mounting_plate(
    width=100,    # mm
    depth=60,     # mm
    thickness=8,  # mm
    hole_diameter=6,
    hole_margin=10
)
```

## Rules
- Import cadquery as `cq`
- Import primitives from `cadquery_primitives` as needed
- Create a `result` variable holding the final shape
- Use explicit dimensions (not magic numbers)
- Add `# mm` comments for dimensions
- All dimensions are in millimetres
"""

# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

MAX_TURNS = 10  # B-Rep is more deterministic than SDF


def run_brep_agent(
    llm: Any,
    user_prompt: str,
    *,
    max_tokens: int = 4096,
    effort: str | None = None,
    verbose: bool = False,
) -> Optional[str]:
    """
    Run the B-Rep agent with tool calls.

    The agent iterates until it calls submit_cadquery or exhausts max turns.
    Returns the final CadQuery code, or None if unsuccessful.
    """
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Create a 3D shape: {user_prompt}"},
    ]

    submitted_code: Optional[str] = None
    agent_start_time = time.perf_counter()

    for turn in range(MAX_TURNS):
        turn_start_time = time.perf_counter()
        if verbose:
            print(f"[turn {turn + 1}/{MAX_TURNS}] Calling model...")

        # Check if backend supports tools (duck typing)
        supports_tools = getattr(llm, "supports_tools", False)
        if verbose:
            print(f"  LLM type: {type(llm).__name__}")
            print(f"  supports_tools: {supports_tools}")

        # Time the LLM call
        llm_start = time.perf_counter()
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
        llm_end = time.perf_counter()

        if verbose:
            print(f"[TIMING] LLM call: {llm_end - llm_start:.2f}s")

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

                    # Execute tool with timing
                    tool_start = time.perf_counter()
                    result = execute_tool(tool_name, dict(tool_input), server_url=SERVER_URL)
                    tool_end = time.perf_counter()

                    if verbose:
                        print(f"[TIMING] Tool '{tool_name}': {tool_end - tool_start:.2f}s")
                        result_preview = {k: (v[:50] + "..." if isinstance(v, str) and len(v) > 50 else v)
                                         for k, v in result.items() if k not in ("mesh", "image_base64")}
                        if "mesh" in result:
                            result_preview["mesh"] = f"<{result['mesh'].get('vertices', []).__len__()} vertices>"
                        print(f"  Result: {result_preview}")

                    # Track submission
                    if tool_name == "submit_cadquery" and result.get("success"):
                        submitted_code = get_current_code()

                    # Build tool result content
                    # For B-Rep, mesh data is sent to browser, not VLM feedback
                    if "mesh" in result:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps({
                                "success": True,
                                "rendered": True,
                                "message": f"Mesh generated: {result.get('vertices', 0)} vertices, {result.get('faces', 0)} faces",
                                "bounds": result.get("bounds"),
                                "volume_mm3": result.get("volume_mm3"),
                                "is_watertight": result.get("is_watertight"),
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

        turn_end_time = time.perf_counter()
        if verbose:
            print(f"[TIMING] Turn {turn + 1} total: {turn_end_time - turn_start_time:.2f}s")
            print(f"[TIMING] Elapsed since start: {turn_end_time - agent_start_time:.2f}s")

    return submitted_code or get_current_code()


def _extract_code_from_text(text: str) -> Optional[str]:
    """Extract CadQuery code from text response."""
    # Look for code blocks with python/cadquery label
    python_match = re.search(r"```python\s*(.*?)\s*```", text, re.DOTALL)
    if python_match:
        return python_match.group(1).strip()

    # Look for generic code blocks
    generic_match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if generic_match:
        code = generic_match.group(1).strip()
        if "import cadquery" in code or "result" in code:
            return code

    # Look for import cadquery directly
    if "import cadquery" in text or "from cadquery" in text:
        # Try to extract the code block
        lines = text.split('\n')
        code_lines = []
        in_code = False
        for line in lines:
            if 'import cadquery' in line or 'from cadquery' in line:
                in_code = True
            if in_code:
                code_lines.append(line)
        if code_lines:
            return '\n'.join(code_lines)

    return None


# Alias for backward compatibility with server.py
extract_cadquery_block = _extract_code_from_text


def refine_brep_agent(
    llm: Any,
    current_code: str,
    instruction: str,
    *,
    verbose: bool = False,
) -> Optional[str]:
    """Refine existing CadQuery code based on a follow-up instruction.

    This is a simplified version that runs the agent with a refinement prompt.
    """
    prompt = f"Modify this CadQuery code to: {instruction}\n\nCurrent code:\n```python\n{current_code}\n```"
    return run_brep_agent(llm, prompt, verbose=verbose)


# Backward compatibility aliases
run_agent = run_brep_agent
refine_agent = refine_brep_agent


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

    parser = argparse.ArgumentParser(description="Text-to-CAD B-Rep CadQuery agent")
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

    t0 = time.perf_counter()
    print("Loading model...")
    llm = load_llm(**model_kwargs)
    t1 = time.perf_counter()
    print(f"Model loaded: {llm.model_id if hasattr(llm, 'model_id') else 'vLLM'}")
    print(f"[TIMING] Model load: {t1 - t0:.2f}s\n")

    if args.once is not None:
        t_start = time.perf_counter()
        code = run_brep_agent(llm, args.once.strip(), verbose=True)
        t_end = time.perf_counter()
        print(f"\n[TIMING] Total agent run: {t_end - t_start:.2f}s")
        print(f"[TIMING] Total (with model load): {t_end - t0:.2f}s")
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

        code = run_brep_agent(llm, prompt, verbose=args.verbose)
        if code:
            print(f"\nGenerated:\n{code}\n")
        else:
            print("\nGeneration failed.\n")


if __name__ == "__main__":
    main()