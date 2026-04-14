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
    'sdCylinderX', 'sdCylinderZ', 'sdHemisphere',
    # CSG operations
    'opU', 'opI', 'opS', 'opSmoothUnion', 'opSmoothIntersection', 'opSmoothSubtraction',
    'opRepPolar', 'opRepLinear', 'opOnion', 'opRound',
    'opU3', 'opU4',
    # Transforms
    'rotX', 'rotY', 'rotZ', 'opRotateX', 'opRotateY', 'opRotateZ',
    'opTranslate', 'opScale', 'opScale3',
    # Domain deformations
    'opTwist', 'opCheapBend',
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
    call_pattern = r'\b(\w+)\s*\('
    all_calls = set(re.findall(call_pattern, code_nocomment))
    undefined = all_calls - ALLOWED_FUNCTIONS - {'map'} - TYPE_CONSTRUCTORS
    if undefined:
        return False, f"Undefined function(s): {', '.join(sorted(undefined))}"

    # --- Phase 2 checks: catch common VLM code-generation bugs ---

    map_body_match = re.search(r'fn\s+map\b[^{]*\{', code_nocomment)
    if map_body_match:
        map_body = code_nocomment[map_body_match.end():]
        depth = 1
        body_end = len(map_body)
        for ci, ch in enumerate(map_body):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    body_end = ci
                    break
        map_body = map_body[:body_end]

        # 2a: Detect dead code after return (multiple returns at top brace depth)
        returns_at_depth_0: list[int] = []
        d = 0
        for rm in re.finditer(r'[\{\}]|\breturn\b', map_body):
            tok = rm.group()
            if tok == '{':
                d += 1
            elif tok == '}':
                d -= 1
            elif tok == 'return' and d == 0:
                returns_at_depth_0.append(rm.start())
        if len(returns_at_depth_0) > 1:
            return False, (
                "Multiple return statements at the same level in map(). "
                "Code after the first return is dead and never executes. "
                "Combine all parts into a single return expression."
            )

        # 2b: Detect variable shadowing (duplicate `let` bindings)
        let_names = re.findall(r'\blet\s+(\w+)\s*=', map_body)
        seen: set[str] = set()
        for name in let_names:
            if name in seen:
                return False, (
                    f"Variable '{name}' is declared twice with `let`. "
                    "Each `let` binding must have a unique name."
                )
            seen.add(name)

    # 2c-extra-0: Detect CSG function wrong arity
    for fn_name, expected in [("opU3", 3), ("opU4", 4), ("opU", 2), ("opS", 2), ("opI", 2)]:
        for fm in re.finditer(rf'\b{fn_name}\s*\(', code_nocomment):
            start = fm.end()
            dp = 1
            ep = len(code_nocomment)
            for ci in range(start, len(code_nocomment)):
                if code_nocomment[ci] == '(':
                    dp += 1
                elif code_nocomment[ci] == ')':
                    dp -= 1
                    if dp == 0:
                        ep = ci
                        break
            arg_str = code_nocomment[start:ep]
            ad = 0
            nc = 0
            for ch in arg_str:
                if ch == '(':
                    ad += 1
                elif ch == ')':
                    ad -= 1
                elif ch == ',' and ad == 0:
                    nc += 1
            na = nc + 1
            if na != expected:
                return False, (
                    f"{fn_name}() called with {na} argument(s) but requires exactly {expected}. "
                    f"For {na} shapes, use nested opU calls instead."
                )

    # 2c-extra: Detect opRepLinear result used as distance (passed to opS/opU/opI)
    rep_vars: set[str] = set()
    for rm in re.finditer(r'\blet\s+(\w+)\s*=\s*opRepLinear\b', code_nocomment):
        rep_vars.add(rm.group(1))
    if rep_vars:
        for rv in rep_vars:
            if re.search(rf'\bop[USI]\s*\([^)]*\b{rv}\b', code_nocomment):
                return False, (
                    f"Variable '{rv}' holds a vec3f from opRepLinear but is passed to a CSG op "
                    f"(opU/opS/opI) which expects f32 distances. "
                    f"opRepLinear returns a modified position — use it to evaluate a primitive: "
                    f"`let q = opRepLinear(p, ...); let d = sdBox(q, ...);`"
                )
            if re.search(rf'\bopRepLinear\s*\(\s*{rv}\b', code_nocomment):
                return False, (
                    f"opRepLinear is called on '{rv}' which is already a repeated position. "
                    f"Do NOT chain opRepLinear calls. Use it once: "
                    f"`let q = opRepLinear(p, spacing, count); let slot = sdBox(q, ...);`"
                )

    # 2c: Detect sdCapsule wrong arity
    for cm in re.finditer(r'\bsdCapsule\s*\(', code_nocomment):
        start = cm.end()
        depth_p = 1
        end_p = len(code_nocomment)
        for ci in range(start, len(code_nocomment)):
            if code_nocomment[ci] == '(':
                depth_p += 1
            elif code_nocomment[ci] == ')':
                depth_p -= 1
                if depth_p == 0:
                    end_p = ci
                    break
        args_str = code_nocomment[start:end_p]
        arg_depth = 0
        n_commas = 0
        for ch in args_str:
            if ch in '(':
                arg_depth += 1
            elif ch in ')':
                arg_depth -= 1
            elif ch == ',' and arg_depth == 0:
                n_commas += 1
        n_args = n_commas + 1
        if n_args != 4:
            return False, (
                f"sdCapsule() called with {n_args} argument(s) but requires exactly 4: "
                "sdCapsule(p, a, b, r) where a and b are vec3f endpoints and r is the radius."
            )

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
    elif "Multiple return" in err or "dead" in err.lower():
        suggestion = "Use a single return at the end: return opU(partA, partB);"
    elif "declared twice" in err:
        suggestion = "Give each let binding a unique name (e.g. blades1, blades2)"
    elif "sdCapsule" in err:
        suggestion = "sdCapsule(p, vec3f(ax,ay,az), vec3f(bx,by,bz), radius)"
    elif "argument" in err and ("opU" in err or "opS" in err or "opI" in err):
        suggestion = "opU takes 2 args, opU3 takes 3, opU4 takes 4. For 5+ shapes nest: opU(opU3(a,b,c), opU(d,e))"

    return False, err, suggestion