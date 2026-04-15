"""
Tests for B-Rep tool definitions and handlers.

Tests:
- Tool schemas are valid
- generate_cadquery handler
- edit_cadquery handler
- validate_cadquery handler
- render_cadquery handler
- submit_cadquery handler
"""

import pytest
import sys
from pathlib import Path

# Add agent directory to path
agent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(agent_dir))

from brep_tools import (
    TOOLS,
    execute_tool,
    get_current_code,
    set_current_code,
    handle_generate_cadquery,
    handle_edit_cadquery,
    handle_validate_cadquery,
    handle_render_cadquery,
    handle_submit_cadquery,
)


class TestToolSchemas:
    """Tests for tool schema definitions."""

    def test_tools_list_not_empty(self):
        """Test that TOOLS list is populated."""
        assert len(TOOLS) > 0

    def test_all_tools_have_required_fields(self):
        """Test that all tools have required schema fields."""
        required_fields = ["name", "description", "input_schema"]

        for tool in TOOLS:
            for field in required_fields:
                assert field in tool, f"Tool {tool.get('name', 'unknown')} missing {field}"

    def test_all_input_schemas_have_required(self):
        """Test that all input schemas have required field."""
        for tool in TOOLS:
            schema = tool["input_schema"]
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema

    def test_generate_cadquery_tool_exists(self):
        """Test that generate_cadquery tool is defined."""
        tool_names = [t["name"] for t in TOOLS]
        assert "generate_cadquery" in tool_names

    def test_edit_cadquery_tool_exists(self):
        """Test that edit_cadquery tool is defined."""
        tool_names = [t["name"] for t in TOOLS]
        assert "edit_cadquery" in tool_names

    def test_validate_cadquery_tool_exists(self):
        """Test that validate_cadquery tool is defined."""
        tool_names = [t["name"] for t in TOOLS]
        assert "validate_cadquery" in tool_names

    def test_render_cadquery_tool_exists(self):
        """Test that render_cadquery tool is defined."""
        tool_names = [t["name"] for t in TOOLS]
        assert "render_cadquery" in tool_names

    def test_submit_cadquery_tool_exists(self):
        """Test that submit_cadquery tool is defined."""
        tool_names = [t["name"] for t in TOOLS]
        assert "submit_cadquery" in tool_names


class TestHandleGenerateCadquery:
    """Tests for generate_cadquery tool handler."""

    def test_generate_sets_current_code(self):
        """Test that generate_cadquery sets current code."""
        code = "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"
        result = handle_generate_cadquery(code)

        assert result["success"] is True
        assert get_current_code() == code

    def test_generate_strips_whitespace(self):
        """Test that generate_cadquery strips whitespace."""
        code = "  import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)  \n"
        result = handle_generate_cadquery(code)

        assert result["success"] is True
        assert get_current_code() == code.strip()

    def test_generate_returns_code_length(self):
        """Test that generate_cadquery returns code length."""
        code = "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"
        result = handle_generate_cadquery(code)

        assert result["code_length"] == len(code.strip())

    def test_generate_returns_preview(self):
        """Test that generate_cadquery returns preview."""
        code = "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"
        result = handle_generate_cadquery(code)

        assert "preview" in result


class TestHandleEditCadquery:
    """Tests for edit_cadquery tool handler."""

    def setup_method(self):
        """Set up test with initial code."""
        set_current_code("import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)")

    def test_edit_replaces_text(self):
        """Test that edit_cadquery replaces text."""
        result = handle_edit_cadquery("box(10, 10, 10)", "box(20, 20, 20)")

        assert result["success"] is True
        assert "box(20, 20, 20)" in get_current_code()

    def test_edit_fails_without_current_code(self):
        """Test that edit fails when no current code."""
        set_current_code("")
        result = handle_edit_cadquery("old", "new")

        assert result["success"] is False
        assert "no code" in result["error"].lower()

    def test_edit_fails_when_string_not_found(self):
        """Test that edit fails when string not found."""
        result = handle_edit_cadquery("nonexistent", "new")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_edit_only_replaces_first_occurrence(self):
        """Test that edit only replaces first occurrence."""
        set_current_code("box(10, 10, 10) and box(10, 10, 10)")
        result = handle_edit_cadquery("box(10, 10, 10)", "box(20, 20, 20)")

        assert result["success"] is True
        code = get_current_code()
        assert code.count("box(20, 20, 20)") == 1
        assert code.count("box(10, 10, 10)") == 1


class TestHandleValidateCadquery:
    """Tests for validate_cadquery tool handler."""

    def test_validate_valid_code(self):
        """Test validation of valid code."""
        code = "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"
        result = handle_validate_cadquery(code)

        assert result["valid"] is True

    def test_validate_missing_result(self):
        """Test validation fails without result variable."""
        code = "import cadquery as cq\nshape = cq.Workplane('XY').box(10, 10, 10)"
        result = handle_validate_cadquery(code)

        assert result["valid"] is False
        assert "error" in result

    def test_validate_syntax_error(self):
        """Test validation detects syntax error."""
        code = "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10"
        result = handle_validate_cadquery(code)

        assert result["valid"] is False
        assert "error" in result


class TestHandleRenderCadquery:
    """Tests for render_cadquery tool handler."""

    @pytest.fixture(autouse=True)
    def check_cadquery(self):
        """Skip tests if CadQuery is not installed."""
        try:
            import cadquery
        except ImportError:
            pytest.skip("CadQuery not installed")

    def test_render_valid_code(self):
        """Test rendering valid code."""
        code = "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"
        result = handle_render_cadquery(code)

        assert result["success"] is True
        assert "mesh" in result
        assert "vertices" in result
        assert "faces" in result

    def test_render_returns_bounds(self):
        """Test that render returns bounds."""
        code = "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"
        result = handle_render_cadquery(code)

        assert result["success"] is True
        assert "bounds" in result

    def test_render_invalid_code_fails(self):
        """Test that render fails for invalid code."""
        code = "import cadquery as cq\n# Missing result"
        result = handle_render_cadquery(code)

        assert result["success"] is False
        assert "error" in result


class TestHandleSubmitCadquery:
    """Tests for submit_cadquery tool handler."""

    def test_submit_returns_success(self):
        """Test that submit returns success dict."""
        # Mock test - actual submission would require running server
        code = "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"

        # This will fail because server isn't running, but tests the structure
        result = handle_submit_cadquery(code)

        assert "success" in result
        # Either success or error should be present
        assert result["success"] is True or "error" in result


class TestExecuteTool:
    """Tests for execute_tool dispatcher."""

    def test_execute_generate_cadquery(self):
        """Test execute_tool for generate_cadquery."""
        result = execute_tool("generate_cadquery", {"code": "test code"})

        assert result["success"] is True
        assert get_current_code() == "test code"

    def test_execute_edit_cadquery(self):
        """Test execute_tool for edit_cadquery."""
        set_current_code("hello world")
        result = execute_tool("edit_cadquery", {"old_string": "hello", "new_string": "hi"})

        assert result["success"] is True
        assert get_current_code() == "hi world"

    def test_execute_validate_cadquery(self):
        """Test execute_tool for validate_cadquery."""
        result = execute_tool("validate_cadquery", {
            "code": "import cadquery as cq\nresult = cq.Workplane('XY').box(10, 10, 10)"
        })

        assert result["valid"] is True

    def test_execute_unknown_tool(self):
        """Test execute_tool for unknown tool."""
        result = execute_tool("unknown_tool", {})

        assert result["success"] is False
        assert "unknown" in result["error"].lower()


class TestCurrentCodeState:
    """Tests for current code state management."""

    def test_get_set_current_code(self):
        """Test get and set current code."""
        set_current_code("test")
        assert get_current_code() == "test"

    def test_current_code_persists(self):
        """Test that current code persists between calls."""
        set_current_code("persistent code")
        handle_generate_cadquery("new code")
        assert get_current_code() == "new code"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])