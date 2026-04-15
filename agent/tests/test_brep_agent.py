"""
Tests for B-Rep agent.

Tests:
- Code extraction from text responses
- Agent function structure
- MAX_TURNS value
"""

import pytest
import sys
from pathlib import Path

# Add agent directory to path
agent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(agent_dir))


class TestCodeExtraction:
    """Tests for code extraction from text responses."""

    def test_extract_python_code_block(self):
        """Test extraction from ```python code block."""
        from brep_agent import _extract_code_from_text

        text = '''Here's the code:
```python
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
```
That creates a box.'''

        code = _extract_code_from_text(text)
        assert code is not None
        assert "import cadquery" in code
        assert "result" in code

    def test_extract_generic_code_block_with_cadquery(self):
        """Test extraction from generic code block with cadquery."""
        from brep_agent import _extract_code_from_text

        text = '''```
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
```'''

        code = _extract_code_from_text(text)
        assert code is not None
        assert "import cadquery" in code

    def test_extract_from_plain_text_with_import(self):
        """Test extraction from plain text with import cadquery."""
        from brep_agent import _extract_code_from_text

        text = '''import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)'''

        code = _extract_code_from_text(text)
        assert code is not None
        assert "import cadquery" in code

    def test_extract_returns_none_for_no_code(self):
        """Test that extraction returns None for text without code."""
        from brep_agent import _extract_code_from_text

        text = "This is just plain text without any code."

        code = _extract_code_from_text(text)
        assert code is None

    def test_extract_from_result_in_code(self):
        """Test extraction when 'result' variable is in code."""
        from brep_agent import _extract_code_from_text

        text = '''```python
import cadquery as cq
from cadquery_primitives import mounting_plate
result = mounting_plate(100, 60, 8, 6, 10)
```'''

        code = _extract_code_from_text(text)
        assert code is not None
        assert "mounting_plate" in code


class TestAgentConstants:
    """Tests for agent constants and configuration."""

    def test_max_turns_is_10(self):
        """Test that MAX_TURNS is 10 (B-Rep is deterministic)."""
        from brep_agent import MAX_TURNS

        assert MAX_TURNS == 10

    def test_system_prompt_contains_coordinate_conventions(self):
        """Test that system prompt mentions Z-up coordinate system."""
        from brep_agent import SYSTEM_PROMPT

        assert "Z-axis" in SYSTEM_PROMPT or "Z is up" in SYSTEM_PROMPT

    def test_system_prompt_contains_units(self):
        """Test that system prompt mentions millimetres."""
        from brep_agent import SYSTEM_PROMPT

        assert "mm" in SYSTEM_PROMPT or "millimetre" in SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_primitives(self):
        """Test that system prompt mentions high-level primitives."""
        from brep_agent import SYSTEM_PROMPT

        assert "mounting_plate" in SYSTEM_PROMPT or "primitive" in SYSTEM_PROMPT.lower()

    def test_system_prompt_lists_tools(self):
        """Test that system prompt lists available tools."""
        from brep_agent import SYSTEM_PROMPT

        assert "generate_cadquery" in SYSTEM_PROMPT
        assert "validate_cadquery" in SYSTEM_PROMPT
        assert "render_cadquery" in SYSTEM_PROMPT
        assert "submit_cadquery" in SYSTEM_PROMPT


class TestAgentFunctionSignatures:
    """Tests for agent function signatures."""

    def test_run_brep_agent_signature(self):
        """Test run_brep_agent function signature."""
        from brep_agent import run_brep_agent
        import inspect

        sig = inspect.signature(run_brep_agent)
        params = list(sig.parameters.keys())

        assert "llm" in params
        assert "user_prompt" in params
        assert "verbose" in params

    def test_refine_brep_agent_signature(self):
        """Test refine_brep_agent function signature."""
        from brep_agent import refine_brep_agent
        import inspect

        sig = inspect.signature(refine_brep_agent)
        params = list(sig.parameters.keys())

        assert "llm" in params
        assert "current_code" in params
        assert "instruction" in params

    def test_extract_cadquery_block_alias(self):
        """Test that extract_cadquery_block is an alias."""
        from brep_agent import extract_cadquery_block, _extract_code_from_text

        assert extract_cadquery_block is _extract_code_from_text


class TestAgentBackwardCompatibility:
    """Tests for backward compatibility aliases."""

    def test_run_agent_alias(self):
        """Test that run_agent is an alias for run_brep_agent."""
        from brep_agent import run_agent, run_brep_agent

        assert run_agent is run_brep_agent

    def test_refine_agent_alias(self):
        """Test that refine_agent is an alias for refine_brep_agent."""
        from brep_agent import refine_agent, refine_brep_agent

        assert refine_agent is refine_brep_agent


class TestImports:
    """Tests for required imports in the agent module."""

    def test_inference_import(self):
        """Test that inference module is imported."""
        import brep_agent

        assert hasattr(brep_agent, 'load_llm')

    def test_brep_tools_import(self):
        """Test that brep_tools module is imported."""
        import brep_agent

        assert hasattr(brep_agent, 'TOOLS')
        assert hasattr(brep_agent, 'execute_tool')
        assert hasattr(brep_agent, 'get_current_code')
        assert hasattr(brep_agent, 'set_current_code')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])