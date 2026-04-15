"""Flask blueprint: auth + print jobs API."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, request

from print_backend.auth_jwt import (
    admin_token_ok,
    create_token,
    decode_token,
    get_bearer_token,
    hash_password,
    verify_password,
)
from print_backend.db import get_database_url, get_session_factory, init_db
from print_backend.job_service import process_geometry, read_stl_file, save_stl_to_disk
from print_backend.models import PrintJob, User
from print_backend.notify_discord import notify_new_print_job

bp = Blueprint("print_api", __name__, url_prefix="/api")


def _db_available() -> bool:
    return get_database_url() is not None


def _session():
    factory = get_session_factory()
    if factory is None:
        return None
    return factory()


def _require_user_session():
    """Return (user, db) or None. Caller must db.close() in finally."""
    token = get_bearer_token(request.headers.get("Authorization"))
    if not token:
        return None
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        return None
    db = _session()
    if db is None:
        return None
    user = db.get(User, payload["sub"])
    if not user:
        db.close()
        return None
    return user, db


@bp.route("/auth/register", methods=["POST", "OPTIONS"])
def register():
    if request.method == "OPTIONS":
        return "", 204
    if not _db_available():
        return jsonify({"error": "Database not configured (set DATABASE_URL)"}), 503
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password or len(password) < 8:
        return jsonify({"error": "Valid email and password (min 8 chars) required"}), 400
    db = _session()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 503
    try:
        if db.query(User).filter_by(email=email).first():
            return jsonify({"error": "Email already registered"}), 409
        user = User(email=email, password_hash=hash_password(password))
        db.add(user)
        db.commit()
        db.refresh(user)
        token = create_token(user.id, user.email)
        return jsonify({"token": token, "user": {"id": user.id, "email": user.email}}), 201
    finally:
        db.close()


@bp.route("/auth/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return "", 204
    if not _db_available():
        return jsonify({"error": "Database not configured"}), 503
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    db = _session()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 503
    try:
        user = db.query(User).filter_by(email=email).first()
        if not user or not verify_password(password, user.password_hash):
            return jsonify({"error": "Invalid email or password"}), 401
        token = create_token(user.id, user.email)
        return jsonify({"token": token, "user": {"id": user.id, "email": user.email}})
    finally:
        db.close()


@bp.route("/print-jobs", methods=["POST", "OPTIONS"])
def create_print_job():
    if request.method == "OPTIONS":
        return "", 204
    if not _db_available():
        return jsonify({"error": "Database not configured"}), 503
    out = _require_user_session()
    if not out:
        return jsonify({"error": "Authentication required"}), 401
    user, db = out
    data = request.get_json(silent=True) or {}
    geometry_kind = (data.get("geometry_kind") or "").strip()
    code = data.get("code")
    scale_mm = float(data.get("scale_mm", 50.0))
    material = (data.get("material") or "PLA").strip()
    quality = (data.get("quality") or "normal").strip()
    infill = int(data.get("infill", 20))
    color = (data.get("color") or "").strip() or None
    customer_name = (data.get("customer_name") or "").strip()
    shipping_address = (data.get("shipping_address") or "").strip()
    delivery_speed = (data.get("delivery_speed") or "standard").strip()

    if geometry_kind not in ("wgsl-sdf", "brep"):
        db.close()
        return jsonify({"error": "geometry_kind must be wgsl-sdf or brep"}), 400
    if not code or not isinstance(code, str):
        db.close()
        return jsonify({"error": "code is required"}), 400
    if not customer_name or not shipping_address:
        db.close()
        return jsonify({"error": "customer_name and shipping_address required"}), 400
    if delivery_speed not in ("standard", "next_day", "same_day"):
        db.close()
        return jsonify({"error": "Invalid delivery_speed"}), 400
    if material not in ("PLA", "resin"):
        db.close()
        return jsonify({"error": "material must be PLA or resin"}), 400
    if quality not in ("draft", "normal", "high"):
        db.close()
        return jsonify({"error": "Invalid quality"}), 400

    try:
        stl_bytes, _mesh, meta = process_geometry(
            geometry_kind,
            code,
            scale_mm,
            material=material,
            quality=quality,
            infill=infill,
        )
        if stl_bytes is None:
            return jsonify({"error": "Validation failed", "details": meta.get("errors", [])}), 400

        urgent = delivery_speed == "same_day"
        job = PrintJob(
            user_id=user.id,
            stl_storage_key="",
            geometry_kind=geometry_kind,
            material=material,
            quality=quality,
            infill=infill,
            color=color,
            status="queued",
            customer_name=customer_name,
            shipping_address=shipping_address,
            delivery_speed=delivery_speed,
            urgent=urgent,
            estimated_print_time_h=meta.get("estimated_print_time_h"),
            estimated_cost=meta.get("estimated_cost"),
            routing_hint=meta.get("routing_hint"),
        )
        db.add(job)
        db.flush()
        key = save_stl_to_disk(job.id, stl_bytes)
        job.stl_storage_key = key
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        jid = job.id
        try:
            notify_new_print_job(
                job_id=jid,
                material=material,
                quality=quality,
                delivery_speed=delivery_speed,
                user_email=user.email,
            )
        except Exception:
            pass
        return jsonify({"ok": True, "job": job.to_dict()}), 201
    finally:
        db.close()


@bp.route("/print-jobs/mine", methods=["GET", "OPTIONS"])
def list_my_jobs():
    if request.method == "OPTIONS":
        return "", 204
    if not _db_available():
        return jsonify({"error": "Database not configured"}), 503
    out = _require_user_session()
    if not out:
        return jsonify({"error": "Authentication required"}), 401
    user, db = out
    try:
        jobs = (
            db.query(PrintJob)
            .filter_by(user_id=user.id)
            .order_by(PrintJob.created_at.desc())
            .all()
        )
        return jsonify({"jobs": [j.to_dict() for j in jobs]})
    finally:
        db.close()


@bp.route("/print-jobs", methods=["GET"])
def list_all_jobs():
    if not _db_available():
        return jsonify({"error": "Database not configured"}), 503
    if not admin_token_ok(request.headers.get("X-Print-Admin-Token")):
        return jsonify({"error": "Admin authentication required"}), 401
    status = request.args.get("status")
    db = _session()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 503
    try:
        q = db.query(PrintJob)
        if status:
            q = q.filter_by(status=status)
        jobs = q.order_by(PrintJob.created_at.desc()).limit(500).all()
        return jsonify({"jobs": [j.to_dict() for j in jobs]})
    finally:
        db.close()


@bp.route("/print-jobs/<job_id>", methods=["GET"])
def get_job(job_id: str):
    if not _db_available():
        return jsonify({"error": "Database not configured"}), 503
    db = _session()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 503
    try:
        job = db.get(PrintJob, job_id)
        if not job:
            return jsonify({"error": "Not found"}), 404
        is_admin = admin_token_ok(request.headers.get("X-Print-Admin-Token"))
        if is_admin:
            d = job.to_dict()
            d["stl_download_path"] = f"/api/print-jobs/{job_id}/stl"
            return jsonify({"job": d})

        token = get_bearer_token(request.headers.get("Authorization"))
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        payload = decode_token(token)
        if not payload or "sub" not in payload:
            return jsonify({"error": "Invalid token"}), 401
        user = db.get(User, payload["sub"])
        if not user or user.id != job.user_id:
            return jsonify({"error": "Forbidden"}), 403
        d = job.to_dict()
        d["stl_download_path"] = f"/api/print-jobs/{job_id}/stl"
        return jsonify({"job": d})
    finally:
        db.close()


@bp.route("/print-jobs/<job_id>", methods=["PATCH", "OPTIONS"])
def patch_job(job_id: str):
    if request.method == "OPTIONS":
        return "", 204
    if not _db_available():
        return jsonify({"error": "Database not configured"}), 503
    if not admin_token_ok(request.headers.get("X-Print-Admin-Token")):
        return jsonify({"error": "Admin authentication required"}), 401
    data = request.get_json(silent=True) or {}
    db = _session()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 503
    try:
        job = db.get(PrintJob, job_id)
        if not job:
            return jsonify({"error": "Not found"}), 404
        if "status" in data:
            job.status = data["status"]
        if "assigned_to" in data:
            job.assigned_to = data["assigned_to"]
        if "notes" in data:
            job.notes = data["notes"]
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        return jsonify({"job": job.to_dict()})
    finally:
        db.close()


@bp.route("/print-jobs/<job_id>/stl", methods=["GET"])
def download_stl(job_id: str):
    if not _db_available():
        return jsonify({"error": "Database not configured"}), 503
    db = _session()
    if db is None:
        return jsonify({"error": "Database unavailable"}), 503
    try:
        job = db.get(PrintJob, job_id)
        if not job:
            return jsonify({"error": "Not found"}), 404
        is_admin = admin_token_ok(request.headers.get("X-Print-Admin-Token"))
        if is_admin:
            raw = read_stl_file(job.stl_storage_key)
            if raw is None:
                return jsonify({"error": "STL file missing"}), 404
            return Response(
                raw,
                mimetype="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="print_{job_id}.stl"'},
            )

        token = get_bearer_token(request.headers.get("Authorization"))
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        payload = decode_token(token)
        if not payload or "sub" not in payload:
            return jsonify({"error": "Invalid token"}), 401
        user = db.get(User, payload["sub"])
        if not user or user.id != job.user_id:
            return jsonify({"error": "Forbidden"}), 403
        raw = read_stl_file(job.stl_storage_key)
        if raw is None:
            return jsonify({"error": "STL file missing"}), 404
        return Response(
            raw,
            mimetype="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="print_{job_id}.stl"'},
        )
    finally:
        db.close()


def register_print_routes(app):
    """Register blueprint and create tables."""
    init_db()
    app.register_blueprint(bp)
