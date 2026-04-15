"""
Tests for B-Rep security sandbox and validation.

Tests:
- Valid CadQuery code passes validation
- Syntax errors are detected
- Forbidden imports are blocked
- Forbidden builtins are blocked
- Dunder attribute access is blocked
- Result variable is required
"""

import pytest
import sys
from pathlib import Path

# Add agent directory to path
agent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(agent_dir))

from brep_validator import validate_cadquery_code, SecurityVisitor


class TestSecurityVisitor:
    """Tests for the AST security visitor."""

    def test_valid_import_cadquery(self):
        """Valid import: cadquery should be allowed."""
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert len(visitor.errors) == 0
        assert 'cadquery' in visitor.imports
        assert visitor.has_result_var

    def test_valid_import_math(self):
        """Valid import: math should be allowed."""
        code = """
import math
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert len(visitor.errors) == 0

    def test_forbidden_import_os(self):
        """Forbidden import: os should be blocked."""
        code = """
import os
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert len(visitor.errors) > 0
        assert 'os' in visitor.errors[0].lower() or 'forbidden' in visitor.errors[0].lower()

    def test_forbidden_import_subprocess(self):
        """Forbidden import: subprocess should be blocked."""
        code = """
import subprocess
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert len(visitor.errors) > 0

    def test_forbidden_import_socket(self):
        """Forbidden import: socket should be blocked."""
        code = """
import socket
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert len(visitor.errors) > 0

    def test_forbidden_builtin_exec(self):
        """Forbidden builtin: exec should be blocked."""
        code = """
import cadquery as cq
exec("print('hello')")
result = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert len(visitor.errors) > 0
        assert 'exec' in visitor.errors[0].lower()

    def test_forbidden_builtin_eval(self):
        """Forbidden builtin: eval should be blocked."""
        code = """
import cadquery as cq
x = eval("1+1")
result = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert len(visitor.errors) > 0

    def test_forbidden_dunder_builtins(self):
        """Blocked attribute: __builtins__ should be blocked."""
        code = """
import cadquery as cq
x = __builtins__
result = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert len(visitor.errors) > 0

    def test_forbidden_dunder_import(self):
        """Blocked attribute: __import__ should be blocked."""
        code = """
import cadquery as cq
x = __import__
result = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert len(visitor.errors) > 0

    def test_missing_result_variable(self):
        """Code without 'result' variable should fail."""
        code = """
import cadquery as cq
shape = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert not visitor.has_result_var


class TestValidateCadqueryCode:
    """Tests for the validate_cadquery_code function."""

    def test_valid_code_passes(self):
        """Valid CadQuery code should pass validation."""
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 20, 30)
"""
        ok, err, suggestion = validate_cadquery_code(code)
        assert ok is True
        assert err == ""

    def test_syntax_error_detected(self):
        """Syntax errors should be detected."""
        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 20, 30
# Missing closing paren
"""
        ok, err, suggestion = validate_cadquery_code(code)
        assert ok is False
        assert "syntax" in err.lower()

    def test_empty_code_fails(self):
        """Empty code should fail."""
        code = ""
        ok, err, suggestion = validate_cadquery_code(code)
        assert ok is False
        assert "empty" in err.lower()

    def test_code_too_large_fails(self):
        """Code exceeding size limit should fail."""
        code = "import cadquery as cq\nresult = cq.Workplane('XY').box(1,1,1)\n" + "x" * 40000
        ok, err, suggestion = validate_cadquery_code(code)
        assert ok is False
        assert "exceeds" in err.lower() or "limit" in err.lower()

    def test_forbidden_import_fails(self):
        """Code with forbidden import should fail."""
        code = """
import os
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        ok, err, suggestion = validate_cadquery_code(code)
        assert ok is False
        assert "forbidden" in err.lower() or "os" in err.lower()

    def test_missing_result_fails(self):
        """Code without result variable should fail."""
        code = """
import cadquery as cq
shape = cq.Workplane("XY").box(10, 10, 10)
"""
        ok, err, suggestion = validate_cadquery_code(code)
        assert ok is False
        assert "result" in err.lower()


class TestEdgeCases:
    """Edge case tests for the validator."""

    def test_import_from_cadquery(self):
        """from cadquery import ... should be allowed."""
        code = """
from cadquery import Workplane
result = Workplane("XY").box(10, 10, 10)
"""
        ok, err, suggestion = validate_cadquery_code(code)
        assert ok is True

    def test_from_import_forbidden_module(self):
        """from forbidden_module import ... should be blocked."""
        code = """
from os import path
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        ok, err, suggestion = validate_cadquery_code(code)
        assert ok is False

    def test_nested_attribute_access(self):
        """Nested dunder access should be blocked."""
        code = """
import cadquery as cq
x = obj.__class__.__bases__
result = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert len(visitor.errors) > 0

    def test_result_in_string_literal(self):
        """'result' in a string should not count as variable."""
        code = """
import cadquery as cq
comment = "the result should be a box"
shape = cq.Workplane("XY").box(10, 10, 10)
"""
        visitor = SecurityVisitor()
        visitor.visit(__import__('ast').parse(code))
        assert not visitor.has_result_var


if __name__ == "__main__":
    pytest.main([__file__, "-v"])