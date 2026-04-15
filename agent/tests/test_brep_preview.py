"""
Tests for B-Rep preview generation (mesh extraction).

Tests:
- Mesh extraction from valid CadQuery code
- Normal computation
- Volume calculation
- Watertight check
- Error handling for invalid code
"""

import pytest
import sys
from pathlib import Path

# Add agent directory to path
agent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(agent_dir))


class TestMeshExtraction:
    """Tests for mesh extraction from CadQuery code."""

    @pytest.fixture(autouse=True)
    def check_cadquery(self):
        """Skip tests if CadQuery is not installed."""
        try:
            import cadquery
        except ImportError:
            pytest.skip("CadQuery not installed")

    def test_box_mesh_extraction(self):
        """Test mesh extraction from a simple box."""
        from brep_preview import get_mesh_json

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 20, 30)
"""
        mesh = get_mesh_json(code)

        assert mesh["type"] == "brep-mesh"
        assert len(mesh["vertices"]) > 0
        assert len(mesh["faces"]) > 0
        assert "bounds" in mesh
        assert "min" in mesh["bounds"]
        assert "max" in mesh["bounds"]

        # Box should have bounds around 10x20x30
        bounds = mesh["bounds"]
        width = bounds["max"][0] - bounds["min"][0]
        depth = bounds["max"][1] - bounds["min"][1]
        height = bounds["max"][2] - bounds["min"][2]

        assert abs(width - 10) < 0.1
        assert abs(depth - 20) < 0.1
        assert abs(height - 30) < 0.1

    def test_cylinder_mesh_extraction(self):
        """Test mesh extraction from a cylinder."""
        from brep_preview import get_mesh_json

        code = """
import cadquery as cq
result = cq.Workplane("XY").circle(5).extrude(10)
"""
        mesh = get_mesh_json(code)

        assert mesh["type"] == "brep-mesh"
        assert len(mesh["vertices"]) > 0
        assert len(mesh["faces"]) > 0

        # Cylinder should be approximately 10 units tall (Z)
        bounds = mesh["bounds"]
        height = bounds["max"][2] - bounds["min"][2]
        assert abs(height - 10) < 0.1

    def test_sphere_mesh_extraction(self):
        """Test mesh extraction from a sphere."""
        from brep_preview import get_mesh_json

        code = """
import cadquery as cq
result = cq.Workplane("XY").sphere(5)
"""
        mesh = get_mesh_json(code)

        assert mesh["type"] == "brep-mesh"
        assert len(mesh["vertices"]) > 0
        assert len(mesh["faces"]) > 0

        # Sphere radius 5 should have diameter ~10 in all directions
        bounds = mesh["bounds"]
        for i in range(3):
            diameter = bounds["max"][i] - bounds["min"][i]
            assert abs(diameter - 10) < 0.5  # Allow some tolerance for tessellation

    def test_normals_computed(self):
        """Test that normals are computed for mesh."""
        from brep_preview import get_mesh_json

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        mesh = get_mesh_json(code)

        assert "normals" in mesh
        assert len(mesh["normals"]) == len(mesh["vertices"])

        # Each normal should be a unit vector (approximately)
        import math
        for normal in mesh["normals"]:
            length = math.sqrt(sum(n*n for n in normal))
            assert abs(length - 1.0) < 0.01

    def test_volume_computed(self):
        """Test that volume is computed."""
        from brep_preview import get_mesh_json

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        mesh = get_mesh_json(code)

        assert "volume_mm3" in mesh
        # 10x10x10 box should have volume ~1000 mm^3
        assert 900 < mesh["volume_mm3"] < 1100

    def test_watertight_check(self):
        """Test that watertight status is checked."""
        from brep_preview import get_mesh_json

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        mesh = get_mesh_json(code)

        assert "is_watertight" in mesh
        assert mesh["is_watertight"] is True

    def test_invalid_code_raises_error(self):
        """Test that invalid code raises ValueError."""
        from brep_preview import get_mesh_json

        code = """
import cadquery as cq
# Missing result variable
shape = cq.Workplane("XY").box(10, 10, 10)
"""
        with pytest.raises(ValueError):
            get_mesh_json(code)

    def test_syntax_error_raises_error(self):
        """Test that syntax error raises ValueError."""
        from brep_preview import get_mesh_json

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10
# Missing closing paren
"""
        with pytest.raises(ValueError):
            get_mesh_json(code)

    def test_forbidden_import_raises_error(self):
        """Test that forbidden import raises ValueError."""
        from brep_preview import get_mesh_json

        code = """
import os
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        with pytest.raises(ValueError):
            get_mesh_json(code)


class TestNormalComputation:
    """Tests for normal computation helper functions."""

    def test_compute_normals_simple_triangle(self):
        """Test normal computation for a simple triangle."""
        from brep_preview import _compute_normals

        vertices = [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
        ]
        faces = [[0, 1, 2]]

        normals = _compute_normals(vertices, faces)

        assert len(normals) == 3
        # Normal should point in +Z direction
        for normal in normals:
            assert abs(normal[2] - 1.0) < 0.01 or normal[2] > 0.9


class TestVolumeComputation:
    """Tests for volume computation helper functions."""

    def test_signed_tetrahedron_volume_box(self):
        """Test signed tetrahedron volume for a box."""
        from brep_preview import _signed_tetrahedron_volume

        # Simple box mesh (approximated)
        vertices = [
            [0, 0, 0],
            [10, 0, 0],
            [10, 10, 0],
            [0, 10, 0],
            [0, 0, 10],
            [10, 0, 10],
            [10, 10, 10],
            [0, 10, 10],
        ]

        # Triangles for box faces (simplified)
        faces = [
            [0, 1, 2], [0, 2, 3],  # bottom
            [4, 5, 6], [4, 6, 7],  # top
            [0, 1, 5], [0, 5, 4],  # front
            [2, 3, 7], [2, 7, 6],  # back
            [0, 3, 7], [0, 7, 4],  # left
            [1, 2, 6], [1, 6, 5],  # right
        ]

        volume = _signed_tetrahedron_volume(vertices, faces)

        # Box is 10x10x10 = 1000 volume
        assert 900 < volume < 1100


class TestWatertightCheck:
    """Tests for watertight check helper functions."""

    def test_watertight_box(self):
        """Test that a closed box is watertight."""
        from brep_preview import _check_watertight_edge_count

        # Box faces - each edge shared by exactly 2 triangles
        faces = [
            [0, 1, 2], [0, 2, 3],
            [4, 5, 6], [4, 6, 7],
            [0, 1, 5], [0, 5, 4],
            [2, 3, 7], [2, 7, 6],
            [0, 3, 7], [0, 7, 4],
            [1, 2, 6], [1, 6, 5],
        ]

        assert _check_watertight_edge_count(faces) is True

    def test_not_watertight_missing_face(self):
        """Test that missing face makes mesh not watertight."""
        from brep_preview import _check_watertight_edge_count

        # Missing one face - some edges have only 1 triangle
        faces = [
            [0, 1, 2], [0, 2, 3],
            [4, 5, 6], [4, 6, 7],
            [0, 1, 5], [0, 5, 4],
            # Missing back face
            [0, 3, 7], [0, 7, 4],
            [1, 2, 6], [1, 6, 5],
        ]

        assert _check_watertight_edge_count(faces) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])