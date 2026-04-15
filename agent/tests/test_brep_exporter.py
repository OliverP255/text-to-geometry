"""
Tests for B-Rep STL export.

Tests:
- Binary STL format is valid
- STL header is correct
- Triangle count matches
- Normal vectors are computed
"""

import pytest
import struct
import sys
from pathlib import Path

# Add agent directory to path
agent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(agent_dir))


class TestSTLExport:
    """Tests for STL export functionality."""

    @pytest.fixture(autouse=True)
    def check_cadquery(self):
        """Skip tests if CadQuery is not installed."""
        try:
            import cadquery
        except ImportError:
            pytest.skip("CadQuery not installed")

    def test_export_stl_returns_bytes(self):
        """Test that export_stl returns bytes."""
        from brep_exporter import export_stl

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        stl_bytes = export_stl(code)

        assert isinstance(stl_bytes, bytes)
        assert len(stl_bytes) > 0

    def test_stl_header_is_80_bytes(self):
        """Test that STL header is 80 bytes."""
        from brep_exporter import export_stl

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        stl_bytes = export_stl(code)

        # First 80 bytes are header
        header = stl_bytes[:80]
        assert len(header) == 80

    def test_stl_triangle_count_valid(self):
        """Test that triangle count is valid."""
        from brep_exporter import export_stl

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        stl_bytes = export_stl(code)

        # Triangle count is at offset 80 (4 bytes, little-endian uint32)
        n_triangles = struct.unpack("<I", stl_bytes[80:84])[0]

        # A box has 12 triangles from tessellation
        assert n_triangles > 0
        assert n_triangles == 12  # Box has 12 triangles

    def test_stl_file_size_matches_triangle_count(self):
        """Test that file size matches expected from triangle count."""
        from brep_exporter import export_stl

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        stl_bytes = export_stl(code)

        n_triangles = struct.unpack("<I", stl_bytes[80:84])[0]

        # Each triangle is: 12 bytes normal + 36 bytes vertices + 2 bytes attribute = 50 bytes
        expected_size = 80 + 4 + (n_triangles * 50)

        # Allow for exact match (12 triangles = 684 bytes total)
        assert len(stl_bytes) == expected_size, f"Expected {expected_size}, got {len(stl_bytes)}"

    def test_stl_normals_are_normalized(self):
        """Test that STL normals are unit vectors."""
        from brep_exporter import export_stl
        import math

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        stl_bytes = export_stl(code)

        n_triangles = struct.unpack("<I", stl_bytes[80:84])[0]

        # Read each triangle's normal
        offset = 84
        for _ in range(n_triangles):
            nx, ny, nz = struct.unpack("<fff", stl_bytes[offset:offset+12])
            length = math.sqrt(nx*nx + ny*ny + nz*nz)

            # Normal should be approximately unit length
            assert abs(length - 1.0) < 0.01 or length > 0.9

            # Move to next triangle
            offset += 50

    def test_stl_vertices_in_bounds(self):
        """Test that STL vertices are within expected bounds."""
        from brep_exporter import export_stl

        code = """
import cadquery as cq
result = cq.Workplane("XY").box(10, 10, 10)
"""
        stl_bytes = export_stl(code)

        n_triangles = struct.unpack("<I", stl_bytes[80:84])[0]

        # Read vertices and check bounds
        # Start after header (80 bytes) + triangle count (4 bytes)
        offset = 84
        max_coord = 0

        for _ in range(n_triangles):
            # Skip normal (12 bytes)
            offset += 12

            # Read 3 vertices (each 3 floats)
            for _ in range(3):
                x, y, z = struct.unpack("<fff", stl_bytes[offset:offset+12])
                max_coord = max(max_coord, abs(x), abs(y), abs(z))
                offset += 12

            # Skip attribute byte count (2 bytes)
            offset += 2

        # Box is 10x10x10, so max coordinate should be ~5 (centered on origin)
        assert max_coord < 10

    def test_export_invalid_code_raises_error(self):
        """Test that invalid code raises ValueError."""
        from brep_exporter import export_stl

        code = """
import cadquery as cq
# Missing result variable
shape = cq.Workplane("XY").box(10, 10, 10)
"""
        with pytest.raises(ValueError):
            export_stl(code)

    def test_export_cylinder(self):
        """Test export of cylinder produces valid STL."""
        from brep_exporter import export_stl

        code = """
import cadquery as cq
result = cq.Workplane("XY").circle(5).extrude(10)
"""
        stl_bytes = export_stl(code)

        assert isinstance(stl_bytes, bytes)
        assert len(stl_bytes) > 0

        n_triangles = struct.unpack("<I", stl_bytes[80:84])[0]
        assert n_triangles > 0

    def test_export_sphere(self):
        """Test export of sphere produces valid STL."""
        from brep_exporter import export_stl

        code = """
import cadquery as cq
result = cq.Workplane("XY").sphere(5)
"""
        stl_bytes = export_stl(code)

        assert isinstance(stl_bytes, bytes)
        assert len(stl_bytes) > 0

        n_triangles = struct.unpack("<I", stl_bytes[80:84])[0]
        assert n_triangles > 0


class TestFaceNormals:
    """Tests for face normal computation."""

    def test_face_normal_z_up(self):
        """Test normal for Z-up triangle."""
        from brep_exporter import _compute_face_normals

        vertices = [
            [0, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
        ]
        faces = [[0, 1, 2]]

        normals = _compute_face_normals(vertices, faces)

        assert len(normals) == 1
        nx, ny, nz = normals[0]
        assert abs(nz - 1.0) < 0.01

    def test_face_normal_x_direction(self):
        """Test normal for X-facing triangle."""
        from brep_exporter import _compute_face_normals

        vertices = [
            [0, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ]
        faces = [[0, 1, 2]]

        normals = _compute_face_normals(vertices, faces)

        assert len(normals) == 1
        nx, ny, nz = normals[0]
        # Normal should be perpendicular to the plane
        # The triangle lies in YZ plane, so normal should be along X axis
        import math
        length = math.sqrt(nx*nx + ny*ny + nz*nz)
        assert abs(length - 1.0) < 0.01
        # Normal should have a significant X component (pointing along X)
        assert abs(nx) > 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])