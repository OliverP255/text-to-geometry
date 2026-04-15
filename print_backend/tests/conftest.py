"""Pytest fixtures for print API tests."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from flask import Flask

from print_backend.db import reset_engine


@pytest.fixture
def app(tmp_path) -> Generator[Flask, None, None]:
    db_path = tmp_path / "test.db"
    uploads = tmp_path / "uploads"
    uploads.mkdir()

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.resolve().as_posix()}"
    os.environ["JWT_SECRET"] = "test-jwt-secret-at-least-32-bytes-long"
    os.environ["PRINT_ADMIN_TOKEN"] = "test-admin-token"
    os.environ["PRINT_UPLOAD_DIR"] = str(uploads)

    reset_engine()

    from print_backend.routes_api import register_print_routes

    application = Flask(__name__)
    register_print_routes(application)
    application.config["TESTING"] = True

    yield application

    reset_engine()


@pytest.fixture
def client(app: Flask):
    return app.test_client()
