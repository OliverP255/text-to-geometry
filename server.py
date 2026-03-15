#!/usr/bin/env python3
"""Minimal backend: POST /scene accepts DSL; WebSocket delivers scene on connect and after POST."""

import json
import sys
from pathlib import Path

# Add build for text_to_geometry_bindings
_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_root / "build"))

try:
    import text_to_geometry_bindings as t2g
except ImportError as e:
    print(f"Import error: {e}. Run: cmake --build build", file=sys.stderr)
    sys.exit(1)

try:
    from flask import Flask, jsonify, request
except ImportError:
    print("Install flask: pip install flask", file=sys.stderr)
    sys.exit(1)

try:
    from flask_socketio import SocketIO, emit
except ImportError:
    print("Install flask-socketio: pip install flask-socketio", file=sys.stderr)
    sys.exit(1)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", transports=["websocket"])

# Default scene: compile DSL and pack for WebGPU
_DEFAULT_DSL = "s0=sphere(r=1)\nreturn s0"
_scene_cache = None


def get_scene():
    global _scene_cache
    if _scene_cache is None:
        flatir = t2g.compile(_DEFAULT_DSL)
        _scene_cache = t2g.packForWebGPU(flatir)
    return _scene_cache


@app.route("/scene", methods=["POST"])
def scene():
    # POST: accept DSL only; compile -> pack -> store -> emit -> return
    try:
        body = request.get_json(force=True, silent=False)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {e}"}), 400

    if body is None:
        return jsonify({"error": "Invalid JSON: body required"}), 400

    dsl = body.get("dsl") if isinstance(body, dict) else None
    if not isinstance(dsl, str) or not dsl.strip():
        return jsonify({"error": "Missing or empty 'dsl' field"}), 400

    try:
        semantic = t2g.compile(dsl)
        packed = t2g.packForWebGPU(semantic)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    global _scene_cache
    _scene_cache = packed
    socketio.emit("scene", packed)
    return jsonify(packed)


@socketio.on("connect")
def on_connect():
    emit("scene", get_scene())


if __name__ == "__main__":
    socketio.run(app, port=5001, debug=True, allow_unsafe_werkzeug=True)
