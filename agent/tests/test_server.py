"""Tests for server endpoints."""

import json
import pytest


class TestSceneWgslEndpoint:
    """Tests for /scene/wgsl endpoint."""

    @pytest.fixture
    def app(self):
        """Create test app."""
        from server import app, socketio
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_valid_wgsl(self, client):
        """Valid WGSL code returns success."""
        code = "fn map(p: vec3f) -> f32 { return sdSphere(p, 1.0); }"
        response = client.post(
            "/scene/wgsl",
            data=json.dumps({"code": code}),
            content_type="application/json"
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["ok"] is True
        assert data["code_length"] == len(code)

    def test_missing_code_field(self, client):
        """Missing code field returns error."""
        response = client.post(
            "/scene/wgsl",
            data=json.dumps({"other": "data"}),
            content_type="application/json"
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_empty_code(self, client):
        """Empty code returns error."""
        response = client.post(
            "/scene/wgsl",
            data=json.dumps({"code": ""}),
            content_type="application/json"
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_invalid_wgsl_missing_map(self, client):
        """Invalid WGSL (missing map function) returns error."""
        response = client.post(
            "/scene/wgsl",
            data=json.dumps({"code": "fn other(p: vec3f) -> f32 { return 1.0; }"}),
            content_type="application/json"
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "map" in data["error"].lower()

    def test_invalid_wgsl_glsl_type(self, client):
        """Invalid WGSL (GLSL type) returns error."""
        response = client.post(
            "/scene/wgsl",
            data=json.dumps({"code": "fn map(p: vec3f) -> f32 { let v: vec3 = vec3f(1.0, 0.0, 0.0); return sdSphere(p, 1.0); }"}),
            content_type="application/json"
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "vec3" in data["error"]

    def test_invalid_json(self, client):
        """Invalid JSON returns error."""
        response = client.post(
            "/scene/wgsl",
            data="not valid json",
            content_type="application/json"
        )
        assert response.status_code == 400

    def test_valid_wgsl_with_csg(self, client):
        """Valid WGSL with CSG operations."""
        code = """
        fn map(p: vec3f) -> f32 {
          let d1 = sdSphere(p, 1.0);
          let d2 = sdBox(p, vec3f(0.5, 0.5, 0.5));
          return opU(d1, d2);
        }
        """
        response = client.post(
            "/scene/wgsl",
            data=json.dumps({"code": code}),
            content_type="application/json"
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["ok"] is True

    def test_valid_wgsl_with_transforms(self, client):
        """Valid WGSL with transform helpers."""
        code = """
        fn map(p: vec3f) -> f32 {
          let q = opRotateY(p, 1.5708);
          return sdTorus(q - vec3f(0.0, 0.5, 0.0), vec2f(0.8, 0.2));
        }
        """
        response = client.post(
            "/scene/wgsl",
            data=json.dumps({"code": code}),
            content_type="application/json"
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["ok"] is True


class TestIndexEndpoint:
    """Tests for index endpoint."""

    @pytest.fixture
    def app(self):
        """Create test app."""
        from server import app
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_index_returns_html(self, client):
        """Index endpoint returns HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"html" in response.data.lower() or response.content_type.startswith("text/html")