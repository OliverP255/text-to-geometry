"""Tests for WGSL validator."""

import pytest
from agent.wgsl_validator import validate_wgsl, validate_wgsl_with_fallback


class TestValidateWgsl:
    """Tests for the validate_wgsl function."""

    def test_valid_simple_sphere(self):
        """Valid simple sphere."""
        code = """
        fn map(p: vec3f) -> f32 {
          return sdSphere(p, 1.0);
        }
        """
        ok, err = validate_wgsl(code)
        assert ok, f"Expected valid, got error: {err}"

    def test_valid_with_translation(self):
        """Valid code with translation."""
        code = """
        fn map(p: vec3f) -> f32 {
          return sdSphere(p - vec3f(0.0, 1.0, 0.0), 1.0);
        }
        """
        ok, err = validate_wgsl(code)
        assert ok, f"Expected valid, got error: {err}"

    def test_valid_with_csg(self):
        """Valid code with CSG operations."""
        code = """
        fn map(p: vec3f) -> f32 {
          let d1 = sdSphere(p, 1.0);
          let d2 = sdBox(p, vec3f(0.5, 0.5, 0.5));
          return opU(d1, d2);
        }
        """
        ok, err = validate_wgsl(code)
        assert ok, f"Expected valid, got error: {err}"

    def test_valid_with_smooth_union(self):
        """Valid code with smooth union."""
        code = """
        fn map(p: vec3f) -> f32 {
          let d1 = sdSphere(p - vec3f(0.0, 0.0, 0.0), 1.0);
          let d2 = sdSphere(p - vec3f(0.0, 1.5, 0.0), 0.7);
          return opSmoothUnion(d1, d2, 0.2);
        }
        """
        ok, err = validate_wgsl(code)
        assert ok, f"Expected valid, got error: {err}"

    def test_valid_with_rotation(self):
        """Valid code with rotation."""
        code = """
        fn map(p: vec3f) -> f32 {
          let q = opRotateX(p, 1.5708);
          return sdTorus(q, vec2f(0.8, 0.2));
        }
        """
        ok, err = validate_wgsl(code)
        assert ok, f"Expected valid, got error: {err}"

    def test_incomplete_placeholder_comment(self):
        """Error when model leaves // ... stub."""
        code = """
        fn map(p: vec3f) -> f32 {
          let s = 10.0;
          let p_scaled = p * s;
          // ...
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "placeholder" in err.lower() or "..." in err

    def test_missing_return_in_map(self):
        """Error when map has no return (invalid WGSL / incomplete generation)."""
        code = """
        fn map(p: vec3f) -> f32 {
          let d = sdSphere(p, 1.0);
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "return" in err.lower()

    def test_missing_map_function(self):
        """Error when map function is missing."""
        code = """
        fn other(p: vec3f) -> f32 {
          return sdSphere(p, 1.0);
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "map" in err.lower()

    def test_multiple_map_functions(self):
        """Error when multiple map functions defined."""
        code = """
        fn map(p: vec3f) -> f32 {
          return sdSphere(p, 1.0);
        }
        fn map(p: vec3f) -> f32 {
          return sdBox(p, vec3f(1.0, 1.0, 1.0));
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "multiple" in err.lower()

    def test_glsl_vec3_type(self):
        """Error when GLSL vec3 type used."""
        code = """
        fn map(p: vec3f) -> f32 {
          let v: vec3 = vec3f(1.0, 0.0, 0.0);
          return sdSphere(p - v, 1.0);
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "vec3" in err
        assert "vec3f" in err

    def test_glsl_float_type(self):
        """Error when GLSL float type used."""
        code = """
        fn map(p: vec3f) -> f32 {
          let r: float = 1.0;
          return sdSphere(p, r);
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "float" in err
        assert "f32" in err

    def test_glsl_mat3_type(self):
        """Error when GLSL mat3 type used."""
        code = """
        fn map(p: vec3f) -> f32 {
          let m: mat3 = mat3x3f();
          return sdSphere(p, 1.0);
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "mat3" in err

    def test_extra_function_definition(self):
        """Error when extra function is defined."""
        code = """
        fn helper(p: vec3f) -> f32 {
          return length(p);
        }
        fn map(p: vec3f) -> f32 {
          return helper(p) - 1.0;
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "helper" in err
        assert "extra" in err.lower() or "only" in err.lower()

    def test_undefined_function(self):
        """Error when undefined function is called."""
        code = """
        fn map(p: vec3f) -> f32 {
          return undefinedFunction(p);
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "undefinedFunction" in err

    def test_forbidden_storage_buffer(self):
        """Error when storage buffer is used."""
        code = """
        fn map(p: vec3f) -> f32 {
          var<storage> x: f32;
          return sdSphere(p, 1.0);
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "storage" in err.lower()

    def test_forbidden_texture_access(self):
        """Error when texture access is used."""
        code = """
        fn map(p: vec3f) -> f32 {
          texture_2d(0);
          return sdSphere(p, 1.0);
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "texture" in err.lower()

    def test_unbalanced_braces(self):
        """Error when braces are unbalanced."""
        code = """
        fn map(p: vec3f) -> f32 {
          return sdSphere(p, 1.0);
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "brace" in err.lower()

    def test_unbalanced_parentheses(self):
        """Error when parentheses are unbalanced."""
        code = """
        fn map(p: vec3f) -> f32 {
          return sdSphere(p, 1.0;
        }
        """
        ok, err = validate_wgsl(code)
        assert not ok
        assert "parenthes" in err.lower()

    def test_code_too_large(self):
        """Error when code exceeds size limit."""
        code = "fn map(p: vec3f) -> f32 { return sdSphere(p, 1.0); }"
        # Repeat to exceed 32KB
        large_code = code + " " * 33000
        ok, err = validate_wgsl(large_code)
        assert not ok
        assert "exceeds" in err.lower()

    def test_empty_code(self):
        """Error when code is empty."""
        code = ""
        ok, err = validate_wgsl(code)
        assert not ok
        assert "empty" in err.lower()

    def test_all_primitives_allowed(self):
        """All SDF primitives are allowed."""
        code = """
        fn map(p: vec3f) -> f32 {
          let d1 = sdSphere(p, 1.0);
          let d2 = sdBox(p, vec3f(1.0, 1.0, 1.0));
          let d3 = sdRoundBox(p, vec3f(1.0, 1.0, 1.0), 0.1);
          let d4 = sdTorus(p, vec2f(1.0, 0.3));
          let d5 = sdCylinder(p, 1.0, 0.5);
          let d6 = sdCapsule(p, vec3f(0.0), vec3f(1.0), 0.5);
          let coneL = sqrt(0.5 * 0.5 + 1.0 * 1.0);
          let d7 = sdCone(p, vec2f(0.5 / coneL, 1.0 / coneL), 1.0);
          let d8 = sdEllipsoid(p, vec3f(1.0, 0.5, 0.5));
          let d9 = sdOctahedron(p, 1.0);
          let d10 = sdHexPrism(p, vec2f(1.0, 0.5));
          return opU(opU(opU(d1, d2), opU(d3, d4)), opU(opU(d5, d6), opU(opU(d7, d8), opU(d9, d10))));
        }
        """
        ok, err = validate_wgsl(code)
        assert ok, f"Expected valid, got error: {err}"

    def test_all_csg_operations_allowed(self):
        """All CSG operations are allowed."""
        code = """
        fn map(p: vec3f) -> f32 {
          let d1 = sdSphere(p - vec3f(-1.0, 0.0, 0.0), 0.5);
          let d2 = sdSphere(p - vec3f(1.0, 0.0, 0.0), 0.5);
          let u = opU(d1, d2);
          let i = opI(d1, d2);
          let s = opS(d1, d2);
          let su = opSmoothUnion(d1, d2, 0.2);
          let si = opSmoothIntersection(d1, d2, 0.2);
          let ss = opSmoothSubtraction(d1, d2, 0.2);
          return u;
        }
        """
        ok, err = validate_wgsl(code)
        assert ok, f"Expected valid, got error: {err}"

    def test_all_transforms_allowed(self):
        """All transform operations are allowed."""
        code = """
        fn map(p: vec3f) -> f32 {
          let rx = opRotateX(p, 0.5);
          let ry = opRotateY(p, 0.5);
          let rz = opRotateZ(p, 0.5);
          let t = opTranslate(p, vec3f(1.0, 0.0, 0.0));
          let s = opScale(p, 2.0);
          let s3 = opScale3(p, vec3f(2.0, 1.0, 1.0));
          return sdSphere(p, 1.0);
        }
        """
        ok, err = validate_wgsl(code)
        assert ok, f"Expected valid, got error: {err}"

    def test_builtin_functions_allowed(self):
        """Built-in WGSL functions are allowed."""
        code = """
        fn map(p: vec3f) -> f32 {
          let d = length(p);
          let a = abs(d);
          let m = min(d, 1.0);
          let mx = max(d, 0.0);
          let c = clamp(d, 0.0, 1.0);
          let s = sin(d);
          let co = cos(d);
          let sq = sqrt(d);
          let n = normalize(p);
          let dotp = dot(p, p);
          let cr = cross(p, vec3f(1.0, 0.0, 0.0));
          return d - 1.0;
        }
        """
        ok, err = validate_wgsl(code)
        assert ok, f"Expected valid, got error: {err}"


class TestValidateWgslWithFallback:
    """Tests for the validate_wgsl_with_fallback function."""

    def test_valid_returns_empty_suggestion(self):
        """Valid code returns empty suggestion."""
        code = """
        fn map(p: vec3f) -> f32 {
          return sdSphere(p, 1.0);
        }
        """
        ok, err, suggestion = validate_wgsl_with_fallback(code)
        assert ok
        assert err == ""
        assert suggestion == ""

    def test_glsl_type_has_suggestion(self):
        """GLSL type error has helpful suggestion."""
        code = """
        fn map(p: vec3f) -> f32 {
          let v: vec3 = vec3f(1.0, 0.0, 0.0);
          return sdSphere(p - v, 1.0);
        }
        """
        ok, err, suggestion = validate_wgsl_with_fallback(code)
        assert not ok
        assert "vec3f" in suggestion
        assert "f32" in suggestion

    def test_extra_function_has_suggestion(self):
        """Extra function error has helpful suggestion."""
        code = """
        fn helper() -> f32 { return 1.0; }
        fn map(p: vec3f) -> f32 {
          return sdSphere(p, helper());
        }
        """
        ok, err, suggestion = validate_wgsl_with_fallback(code)
        assert not ok
        assert "let" in suggestion.lower() or "inside" in suggestion.lower()

    def test_undefined_function_has_suggestion(self):
        """Undefined function error has helpful suggestion."""
        code = """
        fn map(p: vec3f) -> f32 {
          return unknownFunc(p);
        }
        """
        ok, err, suggestion = validate_wgsl_with_fallback(code)
        assert not ok
        assert "SDF" in suggestion or "primitive" in suggestion.lower()