#!/usr/bin/env python3
"""
Scene server: bridges the agent to the WebGPU viewer.

- POST /scene  — receives packed FlatIR JSON from the agent and broadcasts it
                 to all connected browser clients via Socket.IO.
- Socket.IO    — browser clients connect and receive "scene" events.

Usage:
    python server/scene_server.py            # port 5001 (default)
    PORT=8080 python server/scene_server.py  # custom port

The Vite dev server (web/) proxies /socket.io to this server (see web/vite.config.ts).
"""

import os

from flask import Flask, request, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
app.config["SECRET_KEY"] = "t2g-dev"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

_last_scene: dict | None = None


@app.route("/scene", methods=["POST"])
def receive_scene():
    """Accept packed FlatIR from the agent, broadcast to all connected viewers."""
    global _last_scene
    data = request.get_json(force=True)
    if not data or "instrs" not in data:
        return jsonify({"error": "invalid scene: missing 'instrs'"}), 400

    _last_scene = data
    socketio.emit("scene", data)
    n_instrs = len(data.get("instrs", []))
    return jsonify({"ok": True, "instrs": n_instrs})


@socketio.on("connect")
def on_connect():
    """When a viewer connects, send the last known scene (if any) so it renders immediately."""
    if _last_scene is not None:
        socketio.emit("scene", _last_scene, to=request.sid)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "has_scene": _last_scene is not None})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Scene server starting on http://0.0.0.0:{port}")
    print(f"  POST /scene   — push packed FlatIR from agent")
    print(f"  Socket.IO     — browser viewers connect here")
    print(f"  GET  /health  — health check")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, use_reloader=False)
