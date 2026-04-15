"""
Tests for CadQuery primitives library.

Tests:
- Each primitive returns a valid CadQuery Workplane
- Primitives have correct dimensions
- Primitives can be chained
"""

import pytest
import sys
from pathlib import Path

# Add agent directory to path
agent_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(agent_dir))


class TestBasicSolids:
    """Tests for basic solid primitives."""

    @pytest.fixture(autouse=True)
    def check_cadquery(self):
        """Skip tests if CadQuery is not installed."""
        try:
            import cadquery
        except ImportError:
            pytest.skip("CadQuery not installed")

    def test_box_returns_workplane(self):
        """Test that box() returns a Workplane."""
        from cadquery_primitives import box
        import cadquery as cq

        result = box(10, 20, 30)

        assert isinstance(result, cq.Workplane)

    def test_box_dimensions(self):
        """Test that box has correct dimensions."""
        from cadquery_primitives import box

        result = box(10, 20, 30)
        # Get the bounding box
        solid = result.val()
        bb = solid.BoundingBox()

        assert abs(bb.xlen - 10) < 0.01
        assert abs(bb.ylen - 20) < 0.01
        assert abs(bb.zlen - 30) < 0.01

    def test_cylinder_returns_workplane(self):
        """Test that cylinder() returns a Workplane."""
        from cadquery_primitives import cylinder
        import cadquery as cq

        result = cylinder(5, 10)

        assert isinstance(result, cq.Workplane)

    def test_cylinder_dimensions(self):
        """Test that cylinder has correct dimensions."""
        from cadquery_primitives import cylinder

        result = cylinder(5, 10)
        solid = result.val()
        bb = solid.BoundingBox()

        # Diameter should be ~10 (radius 5)
        assert abs(bb.xlen - 10) < 0.1
        assert abs(bb.ylen - 10) < 0.1
        assert abs(bb.zlen - 10) < 0.01

    def test_cone_returns_workplane(self):
        """Test that cone() returns a Workplane."""
        from cadquery_primitives import cone
        import cadquery as cq

        result = cone(5, 0, 10)

        assert isinstance(result, cq.Workplane)

    def test_sphere_returns_workplane(self):
        """Test that sphere() returns a Workplane."""
        from cadquery_primitives import sphere
        import cadquery as cq

        result = sphere(5)

        assert isinstance(result, cq.Workplane)

    def test_sphere_dimensions(self):
        """Test that sphere has correct dimensions."""
        from cadquery_primitives import sphere

        result = sphere(5)
        solid = result.val()
        bb = solid.BoundingBox()

        # Diameter should be ~10
        assert abs(bb.xlen - 10) < 0.1
        assert abs(bb.ylen - 10) < 0.1
        assert abs(bb.zlen - 10) < 0.1

    def test_torus_returns_workplane(self):
        """Test that torus() returns a Workplane."""
        from cadquery_primitives import torus
        import cadquery as cq

        result = torus(tube_radius=2, ring_radius=5)

        assert isinstance(result, cq.Workplane)


class TestEnhancedSolids:
    """Tests for enhanced solid primitives."""

    @pytest.fixture(autouse=True)
    def check_cadquery(self):
        """Skip tests if CadQuery is not installed."""
        try:
            import cadquery
        except ImportError:
            pytest.skip("CadQuery not installed")

    def test_rounded_box_returns_workplane(self):
        """Test that rounded_box() returns a Workplane."""
        from cadquery_primitives import rounded_box
        import cadquery as cq

        result = rounded_box(10, 20, 30, 2)

        assert isinstance(result, cq.Workplane)

    def test_rounded_box_dimensions(self):
        """Test that rounded_box has correct dimensions."""
        from cadquery_primitives import rounded_box

        result = rounded_box(10, 20, 30, 2)
        solid = result.val()
        bb = solid.BoundingBox()

        assert abs(bb.xlen - 10) < 0.1
        assert abs(bb.ylen - 20) < 0.1
        assert abs(bb.zlen - 30) < 0.1

    def test_tube_returns_workplane(self):
        """Test that tube() returns a Workplane."""
        from cadquery_primitives import tube
        import cadquery as cq

        result = tube(outer_radius=10, inner_radius=5, height=20)

        assert isinstance(result, cq.Workplane)

    def test_tube_is_hollow(self):
        """Test that tube is hollow."""
        from cadquery_primitives import tube

        result = tube(outer_radius=10, inner_radius=5, height=20)
        solid = result.val()

        # Tube should have volume less than solid cylinder
        import math
        expected_outer = math.pi * 10**2 * 20
        expected_inner = math.pi * 5**2 * 20
        expected_tube = expected_outer - expected_inner

        # Volume should be close to expected
        actual_volume = solid.Volume()
        assert abs(actual_volume - expected_tube) / expected_tube < 0.1

    def test_hollow_box_returns_workplane(self):
        """Test that hollow_box() returns a Workplane."""
        from cadquery_primitives import hollow_box
        import cadquery as cq

        result = hollow_box(10, 10, 10, 1)

        assert isinstance(result, cq.Workplane)


class TestPlatesAndBrackets:
    """Tests for plates and brackets."""

    @pytest.fixture(autouse=True)
    def check_cadquery(self):
        """Skip tests if CadQuery is not installed."""
        try:
            import cadquery
        except ImportError:
            pytest.skip("CadQuery not installed")

    def test_mounting_plate_returns_workplane(self):
        """Test that mounting_plate() returns a Workplane."""
        from cadquery_primitives import mounting_plate
        import cadquery as cq

        result = mounting_plate(100, 60, 8, 6, 10)

        assert isinstance(result, cq.Workplane)

    def test_mounting_plate_dimensions(self):
        """Test that mounting_plate has correct dimensions."""
        from cadquery_primitives import mounting_plate

        result = mounting_plate(100, 60, 8, 6, 10)
        solid = result.val()
        bb = solid.BoundingBox()

        assert abs(bb.xlen - 100) < 0.1
        assert abs(bb.ylen - 60) < 0.1
        assert abs(bb.zlen - 8) < 0.1

    def test_mounting_plate_has_holes(self):
        """Test that mounting_plate has holes."""
        from cadquery_primitives import mounting_plate

        result = mounting_plate(100, 60, 8, 6, 10)

        # Default is 4 corner holes (2x2 grid)
        # Volume should be less than solid plate
        solid_plate = 100 * 60 * 8
        actual_volume = result.val().Volume()

        assert actual_volume < solid_plate

    def test_mounting_plate_custom_grid(self):
        """Test mounting_plate with custom hole grid."""
        from cadquery_primitives import mounting_plate

        result = mounting_plate(100, 60, 8, 6, 10, (3, 2))
        solid = result.val()

        # Should have 6 holes (3x2)
        # Volume should be even less
        solid_plate = 100 * 60 * 8
        actual_volume = solid.Volume()

        assert actual_volume < solid_plate

    def test_corner_bracket_returns_workplane(self):
        """Test that corner_bracket() returns a Workplane."""
        from cadquery_primitives import corner_bracket
        import cadquery as cq

        result = corner_bracket(50, 40, 5, 6)

        assert isinstance(result, cq.Workplane)


class TestHolesAndFeatures:
    """Tests for holes and features."""

    @pytest.fixture(autouse=True)
    def check_cadquery(self):
        """Skip tests if CadQuery is not installed."""
        try:
            import cadquery
        except ImportError:
            pytest.skip("CadQuery not installed")

    def test_counterbore_hole_returns_workplane(self):
        """Test that counterbore_hole() returns a Workplane."""
        from cadquery_primitives import box, counterbore_hole
        import cadquery as cq

        solid = box(20, 20, 10)
        result = counterbore_hole(solid, 5, 10, 3)

        assert isinstance(result, cq.Workplane)

    def test_countersink_hole_returns_workplane(self):
        """Test that countersink_hole() returns a Workplane."""
        from cadquery_primitives import box, countersink_hole
        import cadquery as cq

        solid = box(20, 20, 10)
        result = countersink_hole(solid, 5, 10, 82)

        assert isinstance(result, cq.Workplane)

    def test_slot_returns_workplane(self):
        """Test that slot() returns a Workplane."""
        from cadquery_primitives import box, slot
        import cadquery as cq

        solid = box(50, 30, 10)
        result = slot(solid, 20, 5, 5)

        assert isinstance(result, cq.Workplane)


class TestPatterns:
    """Tests for pattern functions."""

    @pytest.fixture(autouse=True)
    def check_cadquery(self):
        """Skip tests if CadQuery is not installed."""
        try:
            import cadquery
        except ImportError:
            pytest.skip("CadQuery not installed")

    def test_circular_pattern_returns_workplane(self):
        """Test that circular_pattern() returns a Workplane."""
        from cadquery_primitives import cylinder, circular_pattern
        import cadquery as cq

        solid = cylinder(5, 10)
        result = circular_pattern(solid, 20, 6)

        assert isinstance(result, cq.Workplane)


class TestProfileOperations:
    """Tests for profile-based operations."""

    @pytest.fixture(autouse=True)
    def check_cadquery(self):
        """Skip tests if CadQuery is not installed."""
        try:
            import cadquery
        except ImportError:
            pytest.skip("CadQuery not installed")

    def test_extruded_profile_returns_workplane(self):
        """Test that extruded_profile() returns a Workplane."""
        from cadquery_primitives import extruded_profile
        import cadquery as cq

        points = [(0, 0), (10, 0), (10, 5), (0, 5)]
        result = extruded_profile(points, 20)

        assert isinstance(result, cq.Workplane)

    def test_extruded_profile_dimensions(self):
        """Test extruded_profile has correct dimensions."""
        from cadquery_primitives import extruded_profile

        points = [(0, 0), (10, 0), (10, 5), (0, 5)]
        result = extruded_profile(points, 20)
        solid = result.val()
        bb = solid.BoundingBox()

        # Profile is 10x5, extruded 20
        assert bb.xlen <= 10.1
        assert bb.ylen <= 5.1
        assert abs(bb.zlen - 20) < 0.1

    def test_revolved_profile_returns_workplane(self):
        """Test that revolved_profile() returns a Workplane."""
        from cadquery_primitives import revolved_profile
        import cadquery as cq

        # x = radius, y = height
        points = [(5, 0), (10, 0), (10, 20), (5, 20)]
        result = revolved_profile(points, 360)

        assert isinstance(result, cq.Workplane)


class TestChaining:
    """Tests that primitives can be chained with CadQuery operations."""

    @pytest.fixture(autouse=True)
    def check_cadquery(self):
        """Skip tests if CadQuery is not installed."""
        try:
            import cadquery
        except ImportError:
            pytest.skip("CadQuery not installed")

    def test_chain_with_hole(self):
        """Test chaining primitive with hole operation."""
        from cadquery_primitives import rounded_box
        import cadquery as cq

        result = rounded_box(50, 50, 10, 5).faces(">Z").hole(10)

        assert isinstance(result, cq.Workplane)

    def test_chain_with_fillet(self):
        """Test chaining primitive with fillet operation."""
        from cadquery_primitives import box
        import cadquery as cq

        result = box(20, 20, 10).edges("|Z").fillet(2)

        assert isinstance(result, cq.Workplane)

    def test_chain_with_cut(self):
        """Test chaining primitive with cut operation."""
        from cadquery_primitives import box, cylinder
        import cadquery as cq

        main = box(30, 30, 20)
        hole = cylinder(5, 30)
        result = main.cut(hole)

        assert isinstance(result, cq.Workplane)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])