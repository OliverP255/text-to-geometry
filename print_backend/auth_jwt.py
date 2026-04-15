"""JWT auth and password hashing for print API."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-change-me-in-production")
JWT_ALG = "HS256"
JWT_EXPIRY_H = int(os.environ.get("JWT_EXPIRY_HOURS", "168"))


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def create_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_H),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        return None


def get_bearer_token(auth_header: str | None) -> str | None:
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header[7:].strip() or None


def admin_token_ok(header_val: str | None) -> bool:
    expected = (os.environ.get("PRINT_ADMIN_TOKEN") or "").strip()
    if not expected:
        return False
    return header_val == expected
