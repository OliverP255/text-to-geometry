"""Tests for server API: POST /scene, WebSocket scene events."""

import json
import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "build"))
sys.path.insert(0, str(_root))

# Import after path setup
from server import app, socketio


@pytest.fixture
def client():
    return app.test_client()


def test_post_missing_dsl_returns_400(client):
    """POST without 'dsl' field returns 400."""
    r = client.post("/scene", data="{}", content_type="application/json")
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_post_empty_dsl_returns_400(client):
    """POST with empty 'dsl' string returns 400."""
    r = client.post(
        "/scene",
        data=json.dumps({"dsl": ""}),
        content_type="application/json",
    )
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_post_dsl_valid_returns_200_and_packed(client):
    """POST /scene with valid DSL returns 200 and packed JSON."""
    dsl = "s0=sphere(r=1)\nreturn s0"
    r = client.post(
        "/scene",
        data=json.dumps({"dsl": dsl}),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "instrs" in data
    assert "transforms" in data
    assert "spheres" in data
    assert "boxes" in data
    assert "planes" in data
    assert "rootTemp" in data
    assert data["spheres"] == [1.0, 0.0, 0.0, 0.0]  # packed vec4


def test_post_dsl_invalid_returns_400(client):
    """POST with invalid DSL returns 400."""
    r = client.post(
        "/scene",
        data=json.dumps({"dsl": "invalid syntax"}),
        content_type="application/json",
    )
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data


def test_post_emits_scene(client):
    """POST with valid DSL emits 'scene' event with packed data."""
    socket_client = socketio.test_client(app)
    socket_client.connect()

    dsl = "s0=sphere(r=2)\nreturn s0"
    r = client.post(
        "/scene",
        data=json.dumps({"dsl": dsl}),
        content_type="application/json",
    )
    assert r.status_code == 200
    packed = r.get_json()

    received = socket_client.get_received()
    scene_events = [e for e in received if e["name"] == "scene"]
    assert len(scene_events) >= 1
    assert scene_events[-1]["args"][0] == packed
    assert scene_events[-1]["args"][0]["spheres"] == [2.0, 0.0, 0.0, 0.0]


def test_get_scene_returns_405(client):
    """GET /scene returns 405 Method Not Allowed (route is POST-only)."""
    r = client.get("/scene")
    assert r.status_code == 405


def test_connect_receives_scene(client):
    """WebSocket client receives 'scene' event with packed data on connect."""
    socket_client = socketio.test_client(app)
    socket_client.connect()

    received = socket_client.get_received()
    scene_events = [e for e in received if e["name"] == "scene"]
    assert len(scene_events) == 1
    packed = scene_events[0]["args"][0]
    assert "instrs" in packed
    assert "transforms" in packed
    assert "spheres" in packed


def test_post_invalid_json_returns_400(client):
    """POST with malformed JSON returns 400."""
    r = client.post("/scene", data="{invalid", content_type="application/json")
    assert r.status_code == 400
