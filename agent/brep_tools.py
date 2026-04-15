"""
Tool definitions and handlers for the B-Rep CadQuery agent.

The agent uses these tools to generate, validate, render, and submit CadQuery code.
Mirrors the structure of tools.py for consistency.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Ensure agent directory is on path for imports
_agent_dir = Path(__file__).resolve().parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

from brep_validator import validate_cadquery_code
from brep_preview import execute_cadquery_code, get_mesh_json

# Default server URL for B-Rep scenes
SERVER_URL = os.environ.get("SCENE_SERVER_URL", "http://localhost:5001/scene/brep")


def post_brep_scene(code: str, url: str = SERVER_URL) -> tuple[bool, Optional[str]]:
    """POST CadQuery code to the scene server. Returns (ok, error_message)."""
    import urllib.error
    import urllib.request

    data = json.dumps({"code": code}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
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
        "name": "generate_cadquery",
        "description": "Generate CadQuery Python code. Call this first with your complete script that creates a 'result' variable.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Complete CadQuery Python code with import and result variable",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "edit_cadquery",
        "description": "Edit existing CadQuery code with find/replace. Use for incremental changes like adjusting dimensions or hole positions.",
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
        "name": "validate_cadquery",
        "description": "Check CadQuery code for syntax errors and safety issues. Returns validation result with error details if invalid.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "CadQuery code to validate",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "render_cadquery",
        "description": "Generate mesh data from CadQuery code for visual verification. Returns mesh JSON with vertices, faces, and bounds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "CadQuery code to render",
                },
            },
            "required": ["code"],
        },
    },
    {
        "name": "submit_cadquery",
        "description": "Submit final CadQuery code to the viewer. Call only when you are satisfied with the shape.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Final CadQuery code to submit",
                },
            },
            "required": ["code"],
        },
    },
]


# Global state for current code (used by edit_cadquery)
_current_code: str = ""


def get_current_code() -> str:
    """Get the current CadQuery code state."""
    return _current_code


def set_current_code(code: str) -> None:
    """Set the current CadQuery code state."""
    global _current_code
    _current_code = code


def handle_generate_cadquery(code: str) -> dict[str, Any]:
    """Handle generate_cadquery tool call."""
    global _current_code
    _current_code = code.strip()
    return {
        "success": True,
        "code_length": len(_current_code),
        "preview": _current_code[:100] + "..." if len(_current_code) > 100 else _current_code,
    }


def handle_edit_cadquery(old_string: str, new_string: str) -> dict[str, Any]:
    """Handle edit_cadquery tool call."""
    global _current_code

    if not _current_code:
        return {"success": False, "error": "No code to edit. Call generate_cadquery first."}

    if old_string not in _current_code:
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


def handle_validate_cadquery(code: str) -> dict[str, Any]:
    """Handle validate_cadquery tool call."""
    ok, err, suggestion = validate_cadquery_code(code)

    result: dict[str, Any] = {
        "valid": ok,
    }

    if not ok:
        result["error"] = err
        if suggestion:
            result["suggestion"] = suggestion

    return result


def handle_render_cadquery(code: str) -> dict[str, Any]:
    """Handle render_cadquery tool call."""
    try:
        mesh_data = get_mesh_json(code)
        return {
            "success": True,
            "mesh": mesh_data,
            "vertices": len(mesh_data.get("vertices", [])),
            "faces": len(mesh_data.get("faces", [])),
            "bounds": mesh_data.get("bounds"),
            "volume_mm3": mesh_data.get("volume_mm3"),
            "is_watertight": mesh_data.get("is_watertight"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Mesh generation failed: {str(e)}",
        }


def handle_submit_cadquery(code: str, server_url: str | None = None) -> dict[str, Any]:
    """Handle submit_cadquery tool call."""
    try:
        ok, err = post_brep_scene(code, url=server_url) if server_url else post_brep_scene(code)
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

    if name == "generate_cadquery":
        return handle_generate_cadquery(input_dict["code"])

    elif name == "edit_cadquery":
        return handle_edit_cadquery(input_dict["old_string"], input_dict["new_string"])

    elif name == "validate_cadquery":
        return handle_validate_cadquery(input_dict["code"])

    elif name == "render_cadquery":
        return handle_render_cadquery(input_dict["code"])

    elif name == "submit_cadquery":
        return handle_submit_cadquery(input_dict["code"], server_url)

    else:
        return {"success": False, "error": f"Unknown tool: {name}"}