"""Headless SDF renderer using wgpu-py (Dawn backend).

Renders a WGSL `fn map(p: vec3f) -> f32` function into a PNG image without
requiring a browser or display. Uses the same raymarching/shading pipeline
as the web frontend.
"""

from __future__ import annotations

import io
import math
import struct
from pathlib import Path
from typing import Sequence

import wgpu
from PIL import Image

_AGENT_DIR = Path(__file__).resolve().parent
_SDF_LIBRARY = (_AGENT_DIR / "sdf_library.wgsl").read_text(encoding="utf-8")

_RAYMARCH_TAIL = r"""
struct Uniforms {
  resolution: vec2f,
  _pad0: vec2f,
  cameraPos: vec3f,
  _pad1: f32,
  cameraRight: vec3f,
  _pad2: f32,
  cameraUp: vec3f,
  _pad3: f32,
  cameraFwd: vec3f,
  fov: f32,
  _rootTemp: u32,
  _time: f32,
}

@group(0) @binding(0) var<uniform> u: Uniforms;
@group(0) @binding(1) var outImage: texture_storage_2d<rgba8unorm, write>;

const MAX_STEPS = 224u;
const MAX_DIST  = 120.0;
const MARCH_RELAX = 0.88;
const MIN_MARCH = 0.00005;
const SURF_DIST = 0.001;
const NORM_EPS  = 0.001;
const KEY_DIR   = vec3f(0.6, 0.8, -0.4);
const FILL_DIR  = vec3f(-0.5, 0.3, 0.6);
const KEY_COL   = vec3f(1.0, 0.96, 0.88);
const FILL_COL  = vec3f(0.35, 0.45, 0.7);
const RIM_COL   = vec3f(0.55, 0.65, 0.85);
const AMB_COL   = vec3f(0.10, 0.11, 0.15);
const MAT_COL   = vec3f(0.95, 0.6, 0.25);

fn calcNormal(p: vec3f) -> vec3f {
  let e = vec2f(NORM_EPS, 0.0);
  return normalize(vec3f(
    map(p + e.xyy) - map(p - e.xyy),
    map(p + e.yxy) - map(p - e.yxy),
    map(p + e.yyx) - map(p - e.yyx)
  ));
}
fn march(ro: vec3f, rd: vec3f) -> f32 {
  var t = 0.0;
  for (var i = 0u; i < MAX_STEPS; i++) {
    let d = map(ro + rd * t);
    if (d < SURF_DIST * (1.0 + t * 0.1)) { return t; }
    if (t > MAX_DIST) { break; }
    let step = max(d * MARCH_RELAX, MIN_MARCH);
    t += step;
  }
  return -1.0;
}
fn softShadow(ro: vec3f, rd: vec3f, tmin: f32, tmax: f32, k: f32) -> f32 {
  var res = 1.0;
  var t = tmin;
  for (var i = 0u; i < 16u; i++) {
    let h = map(ro + rd * t);
    res = min(res, k * h / t);
    t += clamp(h, 0.04, 0.4);
    if (res < 0.005 || t > tmax) { break; }
  }
  return clamp(res, 0.0, 1.0);
}
fn calcAO(p: vec3f, n: vec3f) -> f32 {
  var occ = 0.0;
  var w = 1.0;
  for (var i = 0u; i < 3u; i++) {
    let h = 0.03 + 0.15 * f32(i);
    let d = map(p + n * h);
    occ += (h - d) * w;
    w *= 0.65;
  }
  return clamp(1.0 - 1.8 * occ, 0.0, 1.0);
}
fn background(rd: vec3f) -> vec3f {
  let t = 0.5 + 0.5 * rd.y;
  let sky  = mix(vec3f(0.12, 0.14, 0.2), vec3f(0.04, 0.045, 0.08), t);
  let glow = exp(-8.0 * max(rd.y + 0.1, 0.0)) * vec3f(0.1, 0.07, 0.05);
  return sky + glow;
}
@compute @workgroup_size(8, 8)
fn main(@builtin(global_invocation_id) id: vec3u) {
  let dims = textureDimensions(outImage);
  if (id.x >= dims.x || id.y >= dims.y) { return; }
  let px = vec2f(f32(id.x), f32(id.y));
  let res = vec2f(f32(dims.x), f32(dims.y));
  let uv = (px + 0.5 - 0.5 * res) / res.y;
  let halfFov = tan(u.fov * 0.5);
  let rd = normalize(u.cameraRight * uv.x * halfFov + u.cameraUp * -uv.y * halfFov + u.cameraFwd);
  let ro = u.cameraPos;
  let tSdf = march(ro, rd);
  var col: vec3f;
  if (tSdf >= 0.0) {
    let p = ro + rd * tSdf;
    let n = calcNormal(p);
    let v = -rd;
    let ao = calcAO(p, n);
    let keyL = normalize(KEY_DIR);
    let diff = max(dot(n, keyL), 0.0);
    let shad = softShadow(p + n * 0.003, keyL, 0.02, 16.0, 8.0);
    let h = normalize(keyL + v);
    let spec = pow(max(dot(n, h), 0.0), 48.0) * diff * shad;
    let fill = max(dot(n, normalize(FILL_DIR)), 0.0);
    let rim  = pow(1.0 - max(dot(n, v), 0.0), 3.0);
    var light = MAT_COL * KEY_COL * diff * shad * 0.9;
    light += MAT_COL * FILL_COL * fill * 0.62;
    light += RIM_COL * rim * 0.35;
    light += MAT_COL * AMB_COL * (0.58 + 0.42 * n.y);
    light += vec3f(0.9, 0.95, 1.0) * spec * 0.6;
    light *= 0.22 + 0.78 * ao;
    col = light;
  } else {
    col = background(rd);
  }
  col = pow(col, vec3f(1.0 / 2.2));
  let ctr = (px + 0.5) / res - 0.5;
  let vig = 1.0 - 0.22 * dot(ctr, ctr);
  col *= vig;
  col = clamp(col, vec3f(0.0), vec3f(1.0));
  textureStore(outImage, vec2i(i32(id.x), i32(id.y)), vec4f(col, 1.0));
}
"""

UNIFORM_SIZE = 96  # bytes, must match struct Uniforms layout


def _camera_vectors(
    theta: float, phi: float, radius: float,
    target: tuple[float, float, float], fov: float,
) -> bytes:
    ct, st = math.cos(theta), math.sin(theta)
    cp, sp = math.cos(phi), math.sin(phi)
    eye = (
        target[0] + radius * cp * st,
        target[1] + radius * sp,
        target[2] + radius * cp * ct,
    )
    fwd = [target[i] - eye[i] for i in range(3)]
    flen = math.sqrt(sum(f * f for f in fwd))
    fwd = [f / flen for f in fwd]
    up = [0.0, 1.0, 0.0]
    right = [
        fwd[1] * up[2] - fwd[2] * up[1],
        fwd[2] * up[0] - fwd[0] * up[2],
        fwd[0] * up[1] - fwd[1] * up[0],
    ]
    rlen = math.sqrt(sum(r * r for r in right))
    right = [r / rlen for r in right]
    cam_up = [
        right[1] * fwd[2] - right[2] * fwd[1],
        right[2] * fwd[0] - right[0] * fwd[2],
        right[0] * fwd[1] - right[1] * fwd[0],
    ]
    return right, cam_up, fwd, eye


def _pack_uniforms(
    width: int, height: int,
    theta: float, phi: float, radius: float,
    target: tuple[float, float, float], fov: float,
) -> bytes:
    right, cam_up, fwd, eye = _camera_vectors(theta, phi, radius, target, fov)
    buf = bytearray(UNIFORM_SIZE)
    struct.pack_into("ff", buf, 0, float(width), float(height))
    struct.pack_into("fff", buf, 16, eye[0], eye[1], eye[2])
    struct.pack_into("fff", buf, 32, right[0], right[1], right[2])
    struct.pack_into("fff", buf, 48, cam_up[0], cam_up[1], cam_up[2])
    struct.pack_into("fff", buf, 64, fwd[0], fwd[1], fwd[2])
    struct.pack_into("f", buf, 76, fov)
    struct.pack_into("I", buf, 80, 0)
    struct.pack_into("f", buf, 84, 0.0)
    return bytes(buf)


_device_cache: wgpu.GPUDevice | None = None


def _get_device() -> wgpu.GPUDevice:
    global _device_cache
    if _device_cache is not None:
        return _device_cache
    adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
    _device_cache = adapter.request_device_sync()
    return _device_cache


def _render_single_view(
    device: wgpu.GPUDevice,
    shader_code: str,
    width: int,
    height: int,
    theta: float,
    phi: float,
    radius: float = 6.0,
    target: tuple[float, float, float] = (0.0, 0.3, 0.0),
    fov: float = 1.0,
) -> bytes:
    """Dispatch the compute shader and read back RGBA pixels."""
    pipeline = device.create_compute_pipeline(
        layout="auto",
        compute={"module": device.create_shader_module(code=shader_code), "entry_point": "main"},
    )

    uniform_data = _pack_uniforms(width, height, theta, phi, radius, target, fov)
    uniform_buf = device.create_buffer_with_data(data=uniform_data, usage=wgpu.BufferUsage.UNIFORM)

    out_tex = device.create_texture(
        size=(width, height, 1),
        format=wgpu.TextureFormat.rgba8unorm,
        usage=wgpu.TextureUsage.STORAGE_BINDING | wgpu.TextureUsage.COPY_SRC,
    )

    bind_group = device.create_bind_group(
        layout=pipeline.get_bind_group_layout(0),
        entries=[
            {"binding": 0, "resource": {"buffer": uniform_buf}},
            {"binding": 1, "resource": out_tex.create_view()},
        ],
    )

    encoder = device.create_command_encoder()
    cpass = encoder.begin_compute_pass()
    cpass.set_pipeline(pipeline)
    cpass.set_bind_group(0, bind_group)
    cpass.dispatch_workgroups(math.ceil(width / 8), math.ceil(height / 8))
    cpass.end()
    device.queue.submit([encoder.finish()])

    raw = device.queue.read_texture(
        {"texture": out_tex},
        {"bytes_per_row": width * 4, "rows_per_image": height},
        (width, height, 1),
    )
    pixels = bytes(raw)

    out_tex.destroy()
    uniform_buf.destroy()

    return pixels


CameraView = tuple[float, float]  # (theta, phi)

DEFAULT_VIEWS: list[CameraView] = [
    (0.4, 0.35),     # front-right
    (0.0, 1.4),      # top-down
    (1.57, 0.2),     # side
    (3.14, 0.3),     # back
]


def render_sdf_to_png(
    wgsl_map_code: str,
    width: int = 512,
    height: int = 512,
    views: Sequence[CameraView] | None = None,
    radius: float = 6.0,
    target: tuple[float, float, float] = (0.0, 0.3, 0.0),
    fov: float = 1.0,
) -> bytes:
    """Render the SDF map function to a PNG image.

    If multiple views are provided, they are tiled horizontally into one image.
    Returns PNG-encoded bytes.
    """
    if views is None:
        views = [(0.4, 0.35)]

    shader_code = _SDF_LIBRARY + "\n" + wgsl_map_code + "\n" + _RAYMARCH_TAIL
    device = _get_device()

    images: list[Image.Image] = []
    for theta, phi in views:
        pixels = _render_single_view(
            device, shader_code, width, height, theta, phi, radius, target, fov,
        )
        img = Image.frombytes("RGBA", (width, height), pixels)
        images.append(img)

    if len(images) == 1:
        result = images[0]
    else:
        total_w = width * len(images)
        result = Image.new("RGBA", (total_w, height))
        for i, img in enumerate(images):
            result.paste(img, (i * width, 0))

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()


def render_sdf_multiview_png(
    wgsl_map_code: str,
    width: int = 512,
    height: int = 512,
) -> bytes:
    """Render from 4 standard views (front, top, side, back) tiled into one PNG."""
    return render_sdf_to_png(
        wgsl_map_code, width=width, height=height, views=DEFAULT_VIEWS,
    )
