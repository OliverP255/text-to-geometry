"""
CadQuery code validation and sandboxed execution.

Uses a whitelist-based security approach (not blacklist) and executes code
in a subprocess with timeout and resource limits to protect the main process.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional, Tuple

# Maximum code size (32KB)
MAX_CODE_SIZE = 32768

# Execution timeout in seconds
EXECUTION_TIMEOUT = 30

# Whitelist of allowed imports
ALLOWED_IMPORTS = {
    "cadquery",
    "math",
    "cadquery_primitives",
}

# Whitelist of allowed builtins
ALLOWED_BUILTINS = {
    "len", "range", "enumerate", "zip", "list", "dict", "tuple",
    "float", "int", "str", "bool", "abs", "min", "max", "sum", "round",
    "True", "False", "None",
}

# Blocked dunder attributes
BLOCKED_DUNDER = {
    "__builtins__", "__import__", "__class__", "__bases__", "__subclasses__",
    "__mro__", "__globals__", "__code__", "__dict__", "__getattribute__",
}


class SecurityVisitor(ast.NodeVisitor):
    """AST visitor that enforces whitelist-based security rules."""

    def __init__(self):
        self.errors: list[str] = []
        self.imports: set[str] = set()
        self.has_result_var = False

    def visit_Import(self, node: ast.Import) -> None:
        """Check import statements against whitelist."""
        for alias in node.names:
            module = alias.name.split(".")[0]
            self.imports.add(module)
            if module not in ALLOWED_IMPORTS:
                self.errors.append(f"Forbidden import: '{module}'. Allowed: {sorted(ALLOWED_IMPORTS)}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from...import statements against whitelist."""
        if node.module:
            module = node.module.split(".")[0]
            self.imports.add(module)
            if module not in ALLOWED_IMPORTS:
                self.errors.append(f"Forbidden import: '{module}'. Allowed: {sorted(ALLOWED_IMPORTS)}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check for blocked dunder attribute access."""
        if node.attr in BLOCKED_DUNDER:
            self.errors.append(f"Blocked attribute access: '{node.attr}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check for blocked function calls."""
        # Check for blocked builtins called as functions
        if isinstance(node.func, ast.Name):
            if node.func.id in {"exec", "eval", "compile", "open", "__import__"}:
                self.errors.append(f"Blocked function call: '{node.func.id}'")
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Check for blocked dunder names and result variable."""
        # Check for blocked dunder names used as identifiers
        if node.id in BLOCKED_DUNDER:
            self.errors.append(f"Blocked name access: '{node.id}'")

        # Check for result variable assignment
        if node.id == "result":
            # Check if this is a store context (assignment target)
            if isinstance(node.ctx, ast.Store):
                self.has_result_var = True
        self.generic_visit(node)


def validate_cadquery_code(code: str) -> Tuple[bool, str, str]:
    """
    Validate CadQuery code for syntax and security.

    Returns:
        (is_valid, error_message, suggestion)
    """
    # Size check
    if len(code) > MAX_CODE_SIZE:
        return False, f"Code exceeds {MAX_CODE_SIZE} byte limit", ""

    # Empty check
    if not code.strip():
        return False, "Code is empty", ""

    # Parse AST
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        suggestion = _syntax_suggestion(e)
        return False, f"Syntax error: {e}", suggestion

    # Security check via AST visitor
    visitor = SecurityVisitor()
    visitor.visit(tree)

    if visitor.errors:
        return False, visitor.errors[0], ""

    # Check for result variable
    if not visitor.has_result_var:
        return False, "No 'result' variable found", "Assign your final shape to a variable named 'result'"

    return True, "", ""


def _syntax_suggestion(error: SyntaxError) -> str:
    """Generate helpful suggestions for common syntax errors."""
    msg = str(error).lower()
    if "unmatched" in msg and "(" in msg:
        return "Check for missing closing parentheses"
    if "unmatched" in msg and "[" in msg:
        return "Check for missing closing brackets"
    if "invalid syntax" in msg:
        return "Check for typos, missing colons, or incorrect indentation"
    if "unexpected eof" in msg:
        return "Code appears incomplete - check for missing closing brackets or quotes"
    return ""


# =============================================================================
# Subprocess Sandbox Execution
# =============================================================================

# Python code that runs in subprocess to execute CadQuery code safely
_SANDBOX_CODE = r'''
import sys
import json

# Read code from stdin
code = sys.stdin.read()

# Execute the code with a controlled namespace
namespace = {}

try:
    exec(code, namespace)
except Exception as e:
    print(json.dumps({"error": str(e), "type": type(e).__name__}), file=sys.stderr)
    sys.exit(1)

# Extract result
if "result" not in namespace:
    print(json.dumps({"error": "No 'result' variable found"}), file=sys.stderr)
    sys.exit(1)

result = namespace["result"]

# Check if it's a CadQuery object
try:
    import cadquery as cq
    if not isinstance(result, (cq.Workplane, cq.Solid, cq.Compound, cq.Shape)):
        print(json.dumps({"error": "'result' must be a CadQuery object"}), file=sys.stderr)
        sys.exit(1)
except Exception as e:
    print(json.dumps({"error": f"Failed to validate result type: {e}"}), file=sys.stderr)
    sys.exit(1)

# Extract mesh data
try:
    # Get the solid/shape
    if hasattr(result, "val"):
        shape = result.val()
    else:
        shape = result

    # Tessellate to get mesh
    mesh = shape.tessellate(0.1)  # tolerance in mm

    # mesh is (vertices, faces)
    vertices = [[v.x, v.y, v.z] for v in mesh[0]]
    faces = [[int(f[0]), int(f[1]), int(f[2])] for f in mesh[1]]

    # Calculate bounds
    if vertices:
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        zs = [v[2] for v in vertices]
        bounds = {
            "min": [min(xs), min(ys), min(zs)],
            "max": [max(xs), max(ys), max(zs)],
        }
    else:
        bounds = {"min": [0, 0, 0], "max": [0, 0, 0]}

    # Output as JSON
    output = {
        "vertices": vertices,
        "faces": faces,
        "bounds": bounds,
    }
    print(json.dumps(output))

except Exception as e:
    import traceback
    print(json.dumps({"error": f"Mesh extraction failed: {e}\n{traceback.format_exc()}"}), file=sys.stderr)
    sys.exit(1)
'''


def execute_cadquery_in_subprocess(code: str, timeout: int = EXECUTION_TIMEOUT) -> Tuple[Optional[dict], Optional[str]]:
    """
    Execute CadQuery code in a subprocess sandbox.

    Args:
        code: CadQuery Python code to execute
        timeout: Maximum execution time in seconds

    Returns:
        (result_dict, error_message)
    """
    # First validate the code
    ok, err, suggestion = validate_cadquery_code(code)
    if not ok:
        return None, f"{err}. {suggestion}" if suggestion else err

    # Find the Python interpreter in the current venv
    python = sys.executable

    try:
        result = subprocess.run(
            [python, "-c", _SANDBOX_CODE],
            input=code,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path(__file__).parent),  # Run from agent directory for imports
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            # Try to parse JSON error
            try:
                error_data = json.loads(error_msg)
                return None, error_data.get("error", error_msg)
            except json.JSONDecodeError:
                return None, error_msg

        # Parse the output
        try:
            output = json.loads(result.stdout)
            return output, None
        except json.JSONDecodeError as e:
            return None, f"Failed to parse output: {e}"

    except subprocess.TimeoutExpired:
        return None, f"Execution timed out after {timeout} seconds"

    except Exception as e:
        return None, f"Execution failed: {e}"


def validate_cadquery_with_fallback(code: str) -> Tuple[bool, str, str]:
    """
    Validate CadQuery code with helpful suggestions.
    Returns (is_valid, error_message, suggestion).
    """
    return validate_cadquery_code(code)