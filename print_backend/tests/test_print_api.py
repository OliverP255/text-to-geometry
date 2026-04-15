"""API tests with SQLite and mocked STL pipeline."""

from __future__ import annotations

from unittest.mock import patch

import pytest


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_login_and_create_job(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "u@test.com", "password": "password12"},
    )
    assert r.status_code == 201, r.get_json()
    token = r.get_json()["token"]

    r2 = client.post(
        "/api/auth/login",
        json={"email": "u@test.com", "password": "password12"},
    )
    assert r2.status_code == 200
    assert r2.get_json()["token"]

    fake_stl = b"solid test\nendsolid test\n"

    def fake_process(*_a, **_kw):
        return fake_stl, None, {
            "estimated_print_time_h": 1.0,
            "estimated_cost": 12.34,
            "routing_hint": "local",
            "errors": [],
        }

    with patch("print_backend.routes_api.process_geometry", side_effect=fake_process):
        with patch("print_backend.routes_api.notify_new_print_job"):
            r3 = client.post(
                "/api/print-jobs",
                headers=_auth_header(token),
                json={
                    "geometry_kind": "wgsl-sdf",
                    "code": "fn map(p: vec3f) -> f32 { return 1.0; }",
                    "scale_mm": 50,
                    "material": "PLA",
                    "quality": "normal",
                    "infill": 20,
                    "customer_name": "Test User",
                    "shipping_address": "1 Test St",
                    "delivery_speed": "standard",
                },
            )
    assert r3.status_code == 201, r3.get_json()
    job = r3.get_json()["job"]
    jid = job["id"]
    assert job["status"] == "queued"
    assert job["stl_storage_key"].endswith(".stl")

    r4 = client.get("/api/print-jobs/mine", headers=_auth_header(token))
    assert r4.status_code == 200
    ids = [j["id"] for j in r4.get_json()["jobs"]]
    assert jid in ids

    r5 = client.get(f"/api/print-jobs/{jid}", headers=_auth_header(token))
    assert r5.status_code == 200
    assert r5.get_json()["job"]["id"] == jid

    r6 = client.get(
        f"/api/print-jobs/{jid}/stl",
        headers=_auth_header(token),
    )
    assert r6.status_code == 200
    assert r6.data == fake_stl

    ra = client.get(
        "/api/print-jobs",
        headers={"X-Print-Admin-Token": "test-admin-token"},
    )
    assert ra.status_code == 200
    admin_ids = [j["id"] for j in ra.get_json()["jobs"]]
    assert jid in admin_ids

    rp = client.patch(
        f"/api/print-jobs/{jid}",
        headers={"X-Print-Admin-Token": "test-admin-token", "Content-Type": "application/json"},
        json={"status": "printing", "notes": "ok", "assigned_to": "printer-a"},
    )
    assert rp.status_code == 200
    assert rp.get_json()["job"]["status"] == "printing"


def test_create_job_requires_auth(client):
    r = client.post(
        "/api/print-jobs",
        json={"geometry_kind": "wgsl-sdf", "code": "x"},
    )
    assert r.status_code == 401
