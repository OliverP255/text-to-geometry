"""
Tool definitions and handlers for the WGSL SDF agent.

The agent uses these tools to generate, validate, render, and submit WGSL code.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

# Ensure agent directory is on path for imports
_agent_dir = Path(__file__).resolve().parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

from wgsl_validator import validate_wgsl_with_fallback

# Import render function (optional - may fail if wgpu not available)
try:
    from headless_renderer import render_sdf_multiview_png
    _RENDER_AVAILABLE = True
except ImportError:
    _RENDER_AVAILABLE = False

# Default server URL
SERVER_URL = os.environ.get("SCENE_SERVER_URL", "http://localhost:5001/scene/wgsl")


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


# Tool schemas for Anthropic/Vertex API
TOOLS = [
    {
        "name": "generate_wgsl",
        "description": "Generate WGSL SDF code. Call this first with your complete fn map(p: vec3f) -> f32 code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Complete WGSL code: fn map(p: vec3f) -> f32 { ... }",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "edit_wgsl",
        "description": "Edit existing WGSL code with find/replace. Use for incremental changes like adjusting sizes, positions, or blend amounts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "old_string": {
                    "type": "string",
                    "description": "Exact text to find and replace",
                },
                "new_string": {
                    "type": "string",
                    "description": "Replacement text",
                },
            },
            "required": ["old_string", "new_string"],
        },
    },
    {
        "name": "validate_wgsl",
        "description": "Check WGSL code for syntax errors. Returns validation result with error details if invalid.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "WGSL code to validate",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "render_wgsl",
        "description": "Render WGSL code to an image (4 views: front, top, side, back). Use to visually verify the shape matches your intent.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "WGSL code to render",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "submit_wgsl",
        "description": "Submit final WGSL code to the viewer. Call only when you are satisfied with the shape.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Final WGSL code to submit",
                },
            },
            "required": ["code"],
        },
    },
]


# Global state for current code (used by edit_wgsl)
_current_code: str = ""


def get_current_code() -> str:
    """Get the current WGSL code state."""
    return _current_code


def set_current_code(code: str) -> None:
    """Set the current WGSL code state."""
    global _current_code
    _current_code = code


def handle_generate_wgsl(code: str) -> dict[str, Any]:
    """Handle generate_wgsl tool call."""
    global _current_code
    _current_code = code.strip()
    return {
        "success": True,
        "code_length": len(_current_code),
        "preview": _current_code[:100] + "..." if len(_current_code) > 100 else _current_code,
    }


def handle_edit_wgsl(old_string: str, new_string: str) -> dict[str, Any]:
    """Handle edit_wgsl tool call."""
    global _current_code

    if not _current_code:
        return {"success": False, "error": "No code to edit. Call generate_wgsl first."}

    if old_string not in _current_code:
        # Try to find a close match
        return {
            "success": False,
            "error": f"String not found in current code. Make sure to copy the exact text.",
            "search_preview": old_string[:50] + "..." if len(old_string) > 50 else old_string,
        }

    _current_code = _current_code.replace(old_string, new_string, 1)
    return {
        "success": True,
        "code_length": len(_current_code),
        "preview": _current_code[:100] + "..." if len(_current_code) > 100 else _current_code,
    }


def handle_validate_wgsl(code: str) -> dict[str, Any]:
    """Handle validate_wgsl tool call."""
    ok, err, suggestion = validate_wgsl_with_fallback(code)

    result: dict[str, Any] = {
        "valid": ok,
    }

    if not ok:
        result["error"] = err
        if suggestion:
            result["suggestion"] = suggestion

    return result


def handle_render_wgsl(code: str) -> dict[str, Any]:
    """Handle render_wgsl tool call."""
    if not _RENDER_AVAILABLE:
        return {
            "success": False,
            "error": "Rendering not available (wgpu not installed). Skip this step.",
        }

    try:
        png_bytes = render_sdf_multiview_png(code)
        b64 = base64.b64encode(png_bytes).decode("ascii")
        return {
            "success": True,
            "image_base64": b64,
            "image_size_bytes": len(png_bytes),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Render failed: {str(e)}",
        }


def handle_submit_wgsl(code: str, server_url: str | None = None) -> dict[str, Any]:
    """Handle submit_wgsl tool call."""
    try:
        ok, err = post_wgsl_scene(code, url=server_url) if server_url else post_wgsl_scene(code)
        return {
            "success": ok,
            "error": err if not ok else None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def execute_tool(name: str, input_dict: dict[str, Any], server_url: str | None = None) -> dict[str, Any]:
    """Execute a tool by name with the given input."""

    if name == "generate_wgsl":
        return handle_generate_wgsl(input_dict["code"])

    elif name == "edit_wgsl":
        return handle_edit_wgsl(input_dict["old_string"], input_dict["new_string"])

    elif name == "validate_wgsl":
        return handle_validate_wgsl(input_dict["code"])

    elif name == "render_wgsl":
        return handle_render_wgsl(input_dict["code"])

    elif name == "submit_wgsl":
        return handle_submit_wgsl(input_dict["code"], server_url)

    else:
        return {"success": False, "error": f"Unknown tool: {name}"}