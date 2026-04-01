"""Tests for WGSL agent functions."""

import pytest
from agent.wgsl_agent import extract_code_block, _error_feedback


class TestExtractCodeBlock:
    """Tests for extract_code_block function."""

    def test_wgsl_code_block(self):
        """Extract from ```wgsl ... ``` block."""
        text = """Here's the code:
```wgsl
fn map(p: vec3f) -> f32 {
  return sdSphere(p, 1.0);
}
```
Hope that helps!"""
        result = extract_code_block(text)
        assert "fn map(p: vec3f) -> f32" in result
        assert "sdSphere" in result
        assert "```" not in result

    def test_generic_code_block(self):
        """Extract from ``` ... ``` block without language tag."""
        text = """```fn map(p: vec3f) -> f32 {
  return sdBox(p, vec3f(1.0, 1.0, 1.0));
}```"""
        result = extract_code_block(text)
        assert "fn map(p: vec3f) -> f32" in result
        assert "sdBox" in result

    def test_plain_code(self):
        """Return as-is when no code block markers."""
        text = "fn map(p: vec3f) -> f32 {\n  return sdSphere(p, 1.0);\n}"
        result = extract_code_block(text)
        assert result == text.strip()

    def test_double_backtick_wgsl_prefix(self):
        """Strip GLM-style ``wgsl prefix (two backticks) without closing fence."""
        text = "``wgsl\nfn map(p: vec3f) -> f32 {\n  return sdSphere(p, 1.0);\n}\n```"
        result = extract_code_block(text)
        assert result.startswith("fn map")
        assert "sdSphere" in result
        assert "``" not in result
        assert "```" not in result

    def test_junk_before_fn_map(self):
        """Slice from fn map when model emits preamble text."""
        text = 'Here:\nfn map(p: vec3f) -> f32 { return sdSphere(p, 1.0); }'
        result = extract_code_block(text)
        assert result.startswith("fn map")

    def test_empty_input(self):
        """Handle empty input."""
        assert extract_code_block("") == ""
        assert extract_code_block("   ") == ""

    def test_multiple_code_blocks(self):
        """Extract first code block when multiple present."""
        text = """```wgsl
fn map(p: vec3f) -> f32 {
  return sdSphere(p, 1.0);
}
```

Another block:
```
some other code
```"""
        result = extract_code_block(text)
        assert "fn map(p: vec3f) -> f32" in result
        assert "some other code" not in result


class TestErrorFeedback:
    """Tests for _error_feedback function."""

    def test_basic_error(self):
        """Basic error message."""
        result = _error_feedback("Syntax error", "Unexpected token")
        assert "Error: Syntax error" in result
        assert "Unexpected token" in result
        assert "Please fix" in result

    def test_with_suggestion(self):
        """Error with suggestion."""
        result = _error_feedback(
            "Invalid WGSL",
            "GLSL type used",
            suggestion="Use vec3f instead of vec3"
        )
        assert "Suggestion:" in result
        assert "vec3f" in result

    def test_with_code(self):
        """Error with code snippet."""
        code = "fn map(p: vec3f) -> f32 { return unknownFunc(p); }"
        result = _error_feedback("Undefined function", "unknownFunc", code=code)
        assert "Your code:" in result
        assert "unknownFunc" in result

    def test_full_error(self):
        """Error with all components."""
        result = _error_feedback(
            "Validation failed",
            "Extra function defined: helper",
            suggestion="Define helper logic inside map()",
            code="fn helper() -> f32 { return 1.0; }\nfn map(p: vec3f) -> f32 { return helper(); }"
        )
        assert "Error: Validation failed" in result
        assert "Extra function" in result
        assert "Suggestion:" in result
        assert "Your code:" in result
        assert "Please fix" in result


class TestPostWgslScene:
    """Tests for post_wgsl_scene function."""

    def test_post_success(self, monkeypatch):
        """Successful POST."""
        import urllib.request
        from agent.wgsl_agent import post_wgsl_scene

        class MockResponse:
            status = 200
            def read(self): return b'{"ok": true}'
            def __enter__(self): return self
            def __exit__(self, *args): pass

        def mock_urlopen(req, timeout=10):
            return MockResponse()

        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
        ok, err = post_wgsl_scene("fn map(p: vec3f) -> f32 { return 1.0; }")
        assert ok is True
        assert err is None

    def test_post_http_error(self, monkeypatch):
        """HTTP error response."""
        import urllib.request
        from agent.wgsl_agent import post_wgsl_scene

        class MockResponse:
            status = 400
            def read(self): return b'{"error": "Invalid WGSL"}'
            def __enter__(self): return self
            def __exit__(self, *args): pass

        def mock_urlopen(req, timeout=10):
            return MockResponse()

        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
        ok, err = post_wgsl_scene("fn map(p: vec3f) -> f32 { return 1.0; }")
        assert ok is False
        assert "400" in err

    def test_post_connection_error(self, monkeypatch):
        """Connection error."""
        import urllib.request
        import urllib.error
        from agent.wgsl_agent import post_wgsl_scene

        def mock_urlopen(req, timeout=10):
            raise urllib.error.URLError("Connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
        ok, err = post_wgsl_scene("fn map(p: vec3f) -> f32 { return 1.0; }")
        assert ok is False
        assert "Connection refused" in err