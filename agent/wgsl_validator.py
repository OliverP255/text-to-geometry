"""WGSL validation for agent-generated SDF code."""

import re
from typing import Tuple

MAX_CODE_SIZE = 32768  # 32KB limit


def _strip_wgsl_line_comments(code: str) -> str:
    """Remove // comments so prose like `walls (no door)` is not parsed as calls."""
    out_lines: list[str] = []
    for line in code.splitlines():
        out_lines.append(line.split("//", 1)[0])
    return "\n".join(out_lines)


# Patterns that indicate GLSL syntax (not WGSL)
GLSL_TYPE_PATTERNS = [
    (r'\bvec3\b(?!\s*\()', 'GLSL type "vec3" used - use "vec3f" in WGSL'),
    (r'\bvec2\b(?!\s*\()', 'GLSL type "vec2" used - use "vec2f" in WGSL'),
    (r'\bvec4\b(?!\s*\()', 'GLSL type "vec4" used - use "vec4f" in WGSL'),
    (r'\bmat3\b', 'GLSL type "mat3" used - use "mat3x3f" in WGSL'),
    (r'\bmat4\b', 'GLSL type "mat4" used - use "mat4x4f" in WGSL'),
    (r'\bfloat\b(?!\s*\()', 'GLSL type "float" used - use "f32" in WGSL'),
    (r'\bint\b(?!\s*\()', 'GLSL type "int" used - use "i32" in WGSL'),
]

# Patterns that are forbidden for security/safety
FORBIDDEN_PATTERNS = [
    (r'var<storage', 'storage buffers not allowed'),
    (r'var<uniform', 'uniform buffers not allowed'),
    (r'texture_', 'texture access not allowed'),
    (r'\batomic\b', 'atomic operations not allowed'),
    (r'\bworkgroup\b', 'workgroup variables not allowed'),
    (r'@group\(1\)', 'only @group(0) is allowed'),
    (r'@binding\(', '@binding attributes not allowed'),
]

# Functions that are allowed (from SDF library + map)
ALLOWED_FUNCTIONS = {
    # Primitives
    'sdSphere', 'sdBox', 'sdRoundBox', 'sdTorus', 'sdCylinder',
    'sdCapsule', 'sdCone', 'sdEllipsoid', 'sdOctahedron', 'sdHexPrism',
    # CSG operations
    'opU', 'opI', 'opS', 'opSmoothUnion', 'opSmoothIntersection', 'opSmoothSubtraction',
    'opRepPolar', 'opOnion',
    # Transforms
    'rotX', 'rotY', 'rotZ', 'opRotateX', 'opRotateY', 'opRotateZ',
    'opTranslate', 'opScale', 'opScale3',
    # Built-in WGSL
    'min', 'max', 'abs', 'sqrt', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',
    'length', 'distance', 'dot', 'cross', 'normalize', 'reflect', 'clamp',
    'mix', 'step', 'smoothstep', 'sign', 'floor', 'ceil', 'round', 'trunc',
    'fract', 'mod', 'pow', 'exp', 'log', 'exp2', 'log2',
    'select', 'arrayLength', 'unpack4x8snorm', 'pack4x8snorm',
}

# Type constructors that look like function calls
TYPE_CONSTRUCTORS = {'vec3f', 'vec2f', 'vec4f', 'mat3x3f', 'mat4x4f', 'f32', 'i32', 'u32', 'bool'}


def validate_wgsl(code: str) -> Tuple[bool, str]:
    """
    Validate WGSL code for correctness and safety.
    Returns (is_valid, error_message).
    """
    # Size check
    if len(code) > MAX_CODE_SIZE:
        return False, f"Code exceeds {MAX_CODE_SIZE} byte limit"

    # Empty check
    if not code.strip():
        return False, "Code is empty"

    # Balanced braces
    if code.count('{') != code.count('}'):
        return False, f"Unbalanced braces: {code.count('{')} open, {code.count('}')} close"
    if code.count('(') != code.count(')'):
        return False, f"Unbalanced parentheses: {code.count('(')} open, {code.count(')')} close"

    # Require exactly one map function with correct signature
    map_pattern = r'fn\s+map\s*\(\s*p\s*:\s*vec3f\s*\)\s*->\s*f32'
    map_matches = list(re.finditer(map_pattern, code))
    if len(map_matches) == 0:
        return False, "Must define 'fn map(p: vec3f) -> f32'"
    if len(map_matches) > 1:
        return False, "Multiple 'map' functions defined - only one allowed"

    if re.search(r"//\s*\.\.\.", code):
        return (
            False,
            "Remove placeholder comments (// ...); implement the full distance field and return it",
        )

    tail_after_map = code[map_matches[0].end() :]
    if not re.search(r"\breturn\b", tail_after_map):
        return (
            False,
            "map() must include a return statement that produces the signed distance (f32)",
        )

    # Check for GLSL type leakage
    for pattern, msg in GLSL_TYPE_PATTERNS:
        if re.search(pattern, code):
            return False, msg

    # Check for forbidden patterns
    for pattern, msg in FORBIDDEN_PATTERNS:
        if re.search(pattern, code):
            return False, f"Forbidden: {msg}"

    # Check for extra function definitions (agent should only define 'map')
    code_nocomment = _strip_wgsl_line_comments(code)
    fn_pattern = r'fn\s+(\w+)\s*\('
    defined_functions = re.findall(fn_pattern, code_nocomment)
    extra_functions = [f for f in defined_functions if f != 'map']
    if extra_functions:
        return False, f"Extra function(s) defined: {', '.join(extra_functions)}. Only 'map' should be defined."

    # Check for undefined function calls (not in allowed list)
    # Find all function calls: word followed by (
    call_pattern = r'\b(\w+)\s*\('
    all_calls = set(re.findall(call_pattern, code_nocomment))
    undefined = all_calls - ALLOWED_FUNCTIONS - {'map'} - TYPE_CONSTRUCTORS
    if undefined:
        return False, f"Undefined function(s): {', '.join(sorted(undefined))}"

    return True, ""


def validate_wgsl_with_fallback(code: str) -> Tuple[bool, str, str]:
    """
    Validate with helpful suggestions for common errors.
    Returns (is_valid, error_message, suggestion).
    """
    ok, err = validate_wgsl(code)
    if ok:
        return True, "", ""

    # Add helpful suggestions for common mistakes
    suggestion = ""
    if "vec3" in err or "float" in err or "mat3" in err or "GLSL" in err:
        suggestion = "Remember: WGSL uses vec3f, vec2f, f32, mat3x3f (with f suffix)"
    elif "Extra function" in err:
        suggestion = "Define helper logic inside map() using let bindings"
    elif "Undefined function" in err:
        suggestion = "Use only the provided SDF primitives and operations"

    return False, err, suggestion