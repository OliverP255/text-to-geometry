"""Tests for server API: GET /scene, POST /scene."""

import json
import sys
from pathlib import Path

import pytest

_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_root / "build"))
sys.path.insert(0, str(_root))

# Import after path setup
from server import app


@pytest.fixture
def client():
    return app.test_client()


def test_get_scene_returns_packed_flatir(client):
    """GET /scene returns packed FlatIR with instrs, transforms, spheres."""
    r = client.get("/scene")
    assert r.status_code == 200
    data = r.get_json()
    assert "instrs" in data
    assert "transforms" in data
    assert "spheres" in data
    assert "boxes" in data
    assert "planes" in data
    assert "rootTemp" in data


def test_post_scene_valid_returns_200_and_packed(client):
    """POST /scene with valid semantic FlatIR returns 200 and packed JSON."""
    semantic = {
        "instrs": [{"op": 0, "arg0": 0, "arg1": 0, "constIdx": 0}],
        "transforms": [{"tx": 0, "ty": 0, "tz": 0, "sx": 1, "sy": 1, "sz": 1}],
        "spheres": [{"r": 1}],
        "boxes": [],
        "planes": [],
        "rootTemp": 0,
    }
    r = client.post(
        "/scene",
        data=json.dumps(semantic),
        content_type="application/json",
    )
    assert r.status_code == 200
    data = r.get_json()
    assert "instrs" in data
    assert "transforms" in data
    assert "spheres" in data
    assert data["spheres"] == [1.0, 0.0, 0.0, 0.0]  # packed vec4


def test_post_scene_updates_get_scene(client):
    """After POST, GET /scene returns the same packed data."""
    semantic = {
        "instrs": [{"op": 0, "arg0": 0, "arg1": 0, "constIdx": 0}],
        "transforms": [{"tx": 1, "ty": 2, "tz": 3, "sx": 1, "sy": 1, "sz": 1}],
        "spheres": [{"r": 2.5}],
        "boxes": [],
        "planes": [],
        "rootTemp": 0,
    }
    r_post = client.post(
        "/scene",
        data=json.dumps(semantic),
        content_type="application/json",
    )
    assert r_post.status_code == 200
    posted = r_post.get_json()

    r_get = client.get("/scene")
    assert r_get.status_code == 200
    gotten = r_get.get_json()

    assert gotten == posted
    assert gotten["spheres"] == [2.5, 0.0, 0.0, 0.0]


def test_post_scene_invalid_returns_400(client):
    """POST with invalid body returns 400."""
    # Empty body
    r = client.post("/scene", data="{}", content_type="application/json")
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data

    # Malformed JSON
    r = client.post("/scene", data="{invalid", content_type="application/json")
    assert r.status_code == 400

    # Missing required keys
    r = client.post(
        "/scene",
        data=json.dumps({"instrs": []}),
        content_type="application/json",
    )
    assert r.status_code == 400
