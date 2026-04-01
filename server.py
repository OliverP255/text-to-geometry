#!/usr/bin/env python3
"""Scene server: WGSL viewer + optional DSL compile path.

- POST /scene/wgsl — validated WGSL `map()` (used by the fine-tuned agent via /chat).
- POST /scene — constrained DSL string → C++ compile → packed FlatIR (no LLM; separate entry point).
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_root / "build"))
sys.path.insert(0, str(_root / "agent"))

try:
    import text_to_geometry_bindings as t2g
except ImportError as e:
    print(f"Import error: {e}. Run: cmake --build build", file=sys.stderr)
    sys.exit(1)

try:
    from flask import Flask, jsonify, request, send_from_directory
except ImportError:
    print("Install flask: pip install flask", file=sys.stderr)
    sys.exit(1)

try:
    from flask_socketio import SocketIO, emit
except ImportError:
    print("Install flask-socketio: pip install flask-socketio", file=sys.stderr)
    sys.exit(1)

from wgsl_validator import validate_wgsl

try:
    from wgsl_agent import extract_code_block, run_agent
except ImportError:
    extract_code_block = None  # type: ignore[misc, assignment]
    run_agent = None  # type: ignore[misc, assignment]

try:
    from inference import load_llm
except ImportError:
    load_llm = None  # type: ignore[misc, assignment]

_DIST = _root / "web" / "dist"
_ASSETS_DIR = _DIST / "assets"

# Do not use static_url_path="" — it registers a catch-all static route that only allows GET,
# so POST /chat (and similar) incorrectly return 405 Method Not Allowed.
app = Flask(__name__)


@app.after_request
def _cors_headers(response):
    """Allow Vite dev (another origin) to call /chat and load the viewer from :5001."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


_llm = None
_llm_loading = False
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

_DEFAULT_WGSL = """fn map(p: vec3f) -> f32 {
  return sdSphere(p, 1.0);
}"""
_scene_cache: dict = {"type": "wgsl-sdf", "code": _DEFAULT_WGSL}


def get_scene():
    return _scene_cache


@app.route("/")
def index():
    return send_from_directory(_DIST, "index.html")


@app.route("/assets/<path:path>")
def dist_assets(path: str):
    return send_from_directory(_ASSETS_DIR, path)


@app.route("/scene/wgsl", methods=["POST"])
def scene_wgsl():
    try:
        body = request.get_json(force=True, silent=False)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {e}"}), 400
    if not isinstance(body, dict):
        return jsonify({"error": "Expected JSON object"}), 400
    code = body.get("code")
    if not isinstance(code, str) or not code.strip():
        return jsonify({"error": "Missing non-empty 'code'"}), 400
    if extract_code_block is not None:
        code = extract_code_block(code)
    ok, err = validate_wgsl(code)
    if not ok:
        return jsonify({"error": err}), 400
    global _scene_cache
    _scene_cache = {"type": "wgsl-sdf", "code": code}
    socketio.emit("scene", _scene_cache)
    return jsonify({"ok": True, "code_length": len(code)})


@app.route("/scene", methods=["POST"])
def scene_dsl():
    try:
        body = request.get_json(force=True, silent=False)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {e}"}), 400
    if not isinstance(body, dict):
        return jsonify({"error": "Expected JSON object"}), 400
    dsl = body.get("dsl")
    if not isinstance(dsl, str) or not dsl.strip():
        return jsonify({"error": "Missing or empty 'dsl' field"}), 400
    try:
        flatir = t2g.compile(dsl)
        packed = t2g.packForWebGPU(flatir)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    global _scene_cache
    _scene_cache = packed
    socketio.emit("scene", packed)
    return jsonify({"ok": True, "rootTemp": packed.get("rootTemp")})


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    global _llm, _llm_loading, _scene_cache

    if request.method == "OPTIONS":
        return "", 204

    if run_agent is None or load_llm is None:
        return jsonify({"error": "Agent not available (missing imports)"}), 503

    try:
        body = request.get_json(force=True, silent=False)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {e}"}), 400

    prompt = body.get("prompt", "").strip() if isinstance(body, dict) else ""
    if not prompt:
        return jsonify({"error": "Missing non-empty 'prompt'"}), 400

    if _llm is None:
        if _llm_loading:
            return jsonify({"error": "Model is still loading, please wait…"}), 503
        _llm_loading = True
        try:
            model_id = os.environ.get("T2G_MODEL_ID")
            kw = {"model_id": model_id} if model_id else {}
            # WGSL chat is plain text; glm45 + enable_in_reasoning breaks non-JSON completions.
            _llm = load_llm(**kw, structured_outputs_config=None)
        except Exception as e:
            _llm_loading = False
            return jsonify({"error": f"Failed to load model: {e}"}), 500
        _llm_loading = False

    # Do not HTTP POST back into this process (can deadlock or fail); push scene here like /scene/wgsl.
    try:
        code = run_agent(_llm, prompt, attempt_post=False, verbose=False)
    except Exception as e:
        return jsonify({"error": f"Generation failed: {e}"}), 500

    if code is None:
        return jsonify({"error": "Failed to generate valid WGSL after retries"}), 422

    _scene_cache = {"type": "wgsl-sdf", "code": code}
    socketio.emit("scene", _scene_cache)
    return jsonify({"ok": True, "code": code})


@socketio.on("connect")
def on_connect():
    emit("scene", get_scene())


if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=5001,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )
