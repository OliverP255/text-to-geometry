#!/usr/bin/env python3
"""
Web frontend for SDF viewer. Serves a page with auto-refreshing render.
Run on GPU with: python serve_viewer.py
Access via SSH tunnel: ssh -L 8000:localhost:8000 user@gpu
Then open http://localhost:8000
"""

import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from flask import Flask, Response

app = Flask(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent
VIEWER_PATH = PROJECT_ROOT / "build" / "sdf_viewer"
CACHE_DIR = Path(tempfile.gettempdir()) / "sdf_viewer_cache"
CACHE_PATH = CACHE_DIR / "frame.png"
CACHE_TTL = 1.0  # seconds
_cache_lock = threading.Lock()
_cached_bytes: bytes | None = None
_cache_time: float = 0


def render_frame() -> bytes | None:
    """Run sdf_viewer, convert PPM to PNG, return PNG bytes. Returns None on error."""
    if not VIEWER_PATH.is_file() or not os.access(VIEWER_PATH, os.X_OK):
        return None

    with tempfile.NamedTemporaryFile(suffix=".ppm", delete=False) as ppm_f:
        ppm_path = ppm_f.name
    try:
        result = subprocess.run(
            [str(VIEWER_PATH), "--output", ppm_path],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None

        from PIL import Image

        img = Image.open(ppm_path)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        png_temp = CACHE_DIR / "frame.tmp.png"
        img.save(png_temp, "PNG")
        png_temp.rename(CACHE_PATH)
        with open(CACHE_PATH, "rb") as f:
            return f.read()
    except Exception:
        return None
    finally:
        if os.path.exists(ppm_path):
            os.unlink(ppm_path)


@app.route("/")
def index():
    html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>SDF Viewer</title>
  <meta http-equiv="refresh" content="2">
</head>
<body>
  <h1>SDF Viewer</h1>
  <img src="/frame" alt="SDF render" style="max-width:100%;" />
</body>
</html>"""
    return Response(html, mimetype="text/html")


@app.route("/frame")
def frame():
    global _cached_bytes, _cache_time
    now = time.monotonic()
    with _cache_lock:
        if _cached_bytes is not None and (now - _cache_time) < CACHE_TTL:
            return Response(_cached_bytes, mimetype="image/png")
    png_bytes = render_frame()
    if png_bytes is None:
        return Response("Viewer not found or render failed", status=500)
    with _cache_lock:
        _cached_bytes = png_bytes
        _cache_time = time.monotonic()
    return Response(png_bytes, mimetype="image/png")


def main():
    if not VIEWER_PATH.is_file():
        print(f"Error: {VIEWER_PATH} not found. Build the project first.")
        return 1
    print(f"Serving at http://localhost:8000")
    print("Use SSH -L 8080:localhost:8000 to tunnel from your Mac")
    app.run(host="0.0.0.0", port=8000, debug=False)


if __name__ == "__main__":
    exit(main() or 0)
