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

from werkzeug_socketio_compat import SocketIOCompatWSGIRequestHandler

from wgsl_validator import validate_wgsl

try:
    from wgsl_agent import extract_code_block, run_agent, refine_agent
except ImportError:
    extract_code_block = None  # type: ignore[misc, assignment]
    run_agent = None  # type: ignore[misc, assignment]
    refine_agent = None  # type: ignore[misc, assignment]

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
_last_code: str | None = None
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


def _preload_llm():
    """Load the LLM at startup so the first /chat request is fast."""
    global _llm, _llm_loading
    if load_llm is None:
        return
    _llm_loading = True
    try:
        model_id = os.environ.get("T2G_MODEL_ID")
        kw = {"model_id": model_id} if model_id else {}
        _llm = load_llm(**kw, structured_outputs_config=None)
        print("LLM pre-loaded and ready.")
    except Exception as e:
        print(f"[WARN] LLM pre-load failed: {e}")
    _llm_loading = False

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

    result: dict = {}

    # Run generation directly (threading + immediate join adds overhead with no benefit)
    try:
        result["code"] = run_agent(_llm, prompt, verbose=True)
    except Exception as e:
        result["error"] = str(e)

    if "error" in result:
        return jsonify({"error": f"Generation failed: {result['error']}"}), 500

    code = result.get("code")
    if code is None:
        return jsonify({"error": "Failed to generate valid WGSL after retries"}), 422

    global _last_code
    _last_code = code
    _scene_cache = {"type": "wgsl-sdf", "code": code}
    socketio.emit("scene", _scene_cache)
    return jsonify({"ok": True, "code": code})


@app.route("/refine", methods=["POST", "OPTIONS"])
def refine():
    global _llm, _llm_loading, _scene_cache, _last_code

    if request.method == "OPTIONS":
        return "", 204

    if refine_agent is None or load_llm is None:
        return jsonify({"error": "Agent not available (missing imports)"}), 503

    try:
        body = request.get_json(force=True, silent=False)
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {e}"}), 400

    instruction = body.get("instruction", "").strip() if isinstance(body, dict) else ""
    if not instruction:
        return jsonify({"error": "Missing non-empty 'instruction'"}), 400

    current_code = body.get("code", "").strip() if isinstance(body, dict) else ""
    if not current_code:
        current_code = _last_code
    if not current_code:
        return jsonify({"error": "No current code to refine. Generate something first with /chat."}), 400

    if _llm is None:
        if _llm_loading:
            return jsonify({"error": "Model is still loading, please wait…"}), 503
        _llm_loading = True
        try:
            model_id = os.environ.get("T2G_MODEL_ID")
            kw = {"model_id": model_id} if model_id else {}
            _llm = load_llm(**kw, structured_outputs_config=None)
        except Exception as e:
            _llm_loading = False
            return jsonify({"error": f"Failed to load model: {e}"}), 500
        _llm_loading = False

    result: dict = {}

    # Run refinement directly (threading + immediate join adds overhead with no benefit)
    try:
        result["code"] = refine_agent(_llm, current_code, instruction, verbose=True)
    except Exception as e:
        result["error"] = str(e)

    if "error" in result:
        return jsonify({"error": f"Refinement failed: {result['error']}"}), 500

    code = result.get("code")
    if code is None:
        return jsonify({"error": "Refinement failed"}), 422

    _last_code = code
    _scene_cache = {"type": "wgsl-sdf", "code": code}
    socketio.emit("scene", _scene_cache)
    return jsonify({"ok": True, "code": code})


# -----------------------------------------------------------------------------
# STL Export Endpoints
# -----------------------------------------------------------------------------

try:
    from flask import Response
    from mesh_exporter import generate_stl, preview_mesh
except ImportError as e:
    print(f"[WARN] Mesh exporter not available: {e}", file=sys.stderr)
    generate_stl = None  # type: ignore[misc, assignment]
    preview_mesh = None  # type: ignore[misc, assignment]


@app.route("/export/stl", methods=["POST", "OPTIONS"])
def export_stl():
    """Generate and return STL file for current scene."""
    if request.method == "OPTIONS":
        return "", 204

    if generate_stl is None:
        return jsonify({"error": "Mesh exporter not available (missing dependencies)"}), 503

    try:
        body = request.get_json(force=True, silent=True) or {}
    except Exception:
        body = {}

    code = body.get("code") or _last_code
    scale_mm = float(body.get("scale_mm", 50.0))

    if not code:
        return jsonify({"error": "No scene to export"}), 400

    try:
        stl_bytes = generate_stl(code, resolution=256, scale_mm=scale_mm)
        return Response(
            stl_bytes,
            mimetype="application/octet-stream",
            headers={"Content-Disposition": "attachment; filename=shape.stl"}
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Mesh generation failed: {e}"}), 500


@app.route("/export/preview", methods=["POST", "OPTIONS"])
def export_preview():
    """Return mesh metadata without full STL for UI size display."""
    if request.method == "OPTIONS":
        return "", 204

    if preview_mesh is None:
        return jsonify({"error": "Mesh exporter not available (missing dependencies)"}), 503

    try:
        body = request.get_json(force=True, silent=True) or {}
    except Exception:
        body = {}

    code = body.get("code") or _last_code
    scale_mm = float(body.get("scale_mm", 50.0))

    if not code:
        return jsonify({"error": "No scene to preview"}), 400

    try:
        bounds, mesh = preview_mesh(code, resolution=64, scale_mm=scale_mm)
        dims = mesh.bounds[1] - mesh.bounds[0]
        return jsonify({
            "dimensions_mm": dims.tolist(),
            "triangle_count": len(mesh.faces),
            "is_watertight": mesh.is_watertight,
        })
    except Exception as e:
        return jsonify({"error": f"Preview failed: {e}"}), 500


@socketio.on("connect")
def on_connect():
    emit("scene", get_scene())


@socketio.on("chat")
def on_chat(data):
    """Socket.IO chat: lower latency than HTTP (no preflight, no thread overhead).
    Emits 'scene' on success or 'chat_error' on failure."""
    global _last_code, _scene_cache

    prompt = (data.get("prompt", "") if isinstance(data, dict) else "").strip()
    if not prompt:
        emit("chat_error", {"error": "Missing prompt"})
        return

    if _llm is None:
        emit("chat_error", {"error": "Model not loaded"})
        return

    if run_agent is None:
        emit("chat_error", {"error": "Agent not available"})
        return

    emit("chat_status", {"status": "generating"})

    try:
        code = run_agent(_llm, prompt, verbose=True)
    except Exception as e:
        emit("chat_error", {"error": str(e)})
        return

    if code is None:
        emit("chat_error", {"error": "Failed to generate valid WGSL"})
        return

    _last_code = code
    _scene_cache = {"type": "wgsl-sdf", "code": code}
    emit("scene", _scene_cache)
    emit("chat_done", {"code": code})


@socketio.on("refine")
def on_refine(data):
    """Socket.IO refinement: takes instruction + optional code."""
    global _last_code, _scene_cache

    instruction = (data.get("instruction", "") if isinstance(data, dict) else "").strip()
    if not instruction:
        emit("chat_error", {"error": "Missing instruction"})
        return

    current_code = (data.get("code", "") if isinstance(data, dict) else "").strip() or _last_code
    if not current_code:
        emit("chat_error", {"error": "No code to refine"})
        return

    if _llm is None or refine_agent is None:
        emit("chat_error", {"error": "Agent not available"})
        return

    emit("chat_status", {"status": "refining"})

    try:
        code = refine_agent(_llm, current_code, instruction, verbose=True)
    except Exception as e:
        emit("chat_error", {"error": str(e)})
        return

    if code:
        _last_code = code
        _scene_cache = {"type": "wgsl-sdf", "code": code}
        emit("scene", _scene_cache)
        emit("chat_done", {"code": code})


if __name__ == "__main__":
    _preload_llm()
    socketio.run(
        app,
        host="0.0.0.0",
        port=5001,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
        request_handler=SocketIOCompatWSGIRequestHandler,
    )
