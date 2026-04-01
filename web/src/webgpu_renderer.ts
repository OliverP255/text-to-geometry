import type { PackedFlatIR, WGSLSdfScene } from './types';


const SDF_LIBRARY_WGSL = String.raw`
fn sdSphere(p: vec3f, s: f32) -> f32 { return length(p) - s; }
fn sdBox(p: vec3f, b: vec3f) -> f32 {
  let q = abs(p) - b;
  return length(max(q, vec3f(0.0))) + min(max(q.x, max(q.y, q.z)), 0.0);
}
fn sdRoundBox(p: vec3f, b: vec3f, r: f32) -> f32 {
  let q = abs(p) - b + r;
  return length(max(q, vec3f(0.0))) + min(max(q.x, max(q.y, q.z)), 0.0) - r;
}
fn sdTorus(p: vec3f, t: vec2f) -> f32 {
  let q = vec2f(length(p.xz) - t.x, p.y);
  return length(q) - t.y;
}
fn sdCylinder(p: vec3f, h: f32, r: f32) -> f32 {
  let d = abs(vec2f(length(p.xz), p.y)) - vec2f(r, h);
  return min(max(d.x, d.y), 0.0) + length(max(d, vec2f(0.0)));
}
fn sdCapsule(p: vec3f, a: vec3f, b: vec3f, r: f32) -> f32 {
  let pa = p - a;
  let ba = b - a;
  let h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
  return length(pa - ba * h) - r;
}
fn sdCone(p: vec3f, h: f32, r: f32) -> f32 {
  let q = vec2f(length(p.xz), p.y);
  let tip = q - vec2f(0.0, h);
  let mantle = q - r * q.y / h;
  let d = max(tip.x, tip.y);
  return sqrt(min(dot(tip, tip), dot(mantle, mantle))) * sign(d);
}
fn sdEllipsoid(p: vec3f, r: vec3f) -> f32 {
  let k0 = length(p / r);
  let k1 = length(p / (r * r));
  return k0 * (k0 - 1.0) / k1;
}
fn sdOctahedron(p: vec3f, s: f32) -> f32 {
  let q = abs(p);
  return (q.x + q.y + q.z - s) * 0.57735027;
}
fn sdHexPrism(p: vec3f, h: vec2f) -> f32 {
  let k = vec3f(-0.8660254, 0.5, 0.57735);
  var q = abs(p);
  let qxy = q.xy - 2.0 * min(dot(k.xy, q.xy), 0.0) * k.xy;
  q = vec3f(qxy.x, qxy.y, q.z);
  let d = vec2f(
    length(qxy - vec2f(clamp(q.x, -k.z * h.x, k.z * h.x), h.x)) * sign(q.y - h.x),
    q.z - h.y
  );
  return min(max(d.x, d.y), 0.0) + length(max(d, vec2f(0.0)));
}
fn opU(d1: f32, d2: f32) -> f32 { return min(d1, d2); }
fn opI(d1: f32, d2: f32) -> f32 { return max(d1, d2); }
fn opS(d1: f32, d2: f32) -> f32 { return max(d1, -d2); }
fn opSmoothUnion(d1: f32, d2: f32, k: f32) -> f32 {
  let h = clamp(0.5 + 0.5 * (d2 - d1) / k, 0.0, 1.0);
  return mix(d2, d1, h) - k * h * (1.0 - h);
}
fn opSmoothIntersection(d1: f32, d2: f32, k: f32) -> f32 {
  let h = clamp(0.5 - 0.5 * (d2 - d1) / k, 0.0, 1.0);
  return mix(d2, d1, h) + k * h * (1.0 - h);
}
fn opSmoothSubtraction(d1: f32, d2: f32, k: f32) -> f32 {
  let h = clamp(0.5 - 0.5 * (d2 + d1) / k, 0.0, 1.0);
  return mix(d2, -d1, h) + k * h * (1.0 - h);
}
fn rotX(a: f32) -> mat3x3f {
  let c = cos(a); let s = sin(a);
  return mat3x3f(vec3f(1,0,0), vec3f(0,c,s), vec3f(0,-s,c));
}
fn rotY(a: f32) -> mat3x3f {
  let c = cos(a); let s = sin(a);
  return mat3x3f(vec3f(c,0,-s), vec3f(0,1,0), vec3f(s,0,c));
}
fn rotZ(a: f32) -> mat3x3f {
  let c = cos(a); let s = sin(a);
  return mat3x3f(vec3f(c,s,0), vec3f(-s,c,0), vec3f(0,0,1));
}
fn opRotateX(p: vec3f, a: f32) -> vec3f { return rotX(a) * p; }
fn opRotateY(p: vec3f, a: f32) -> vec3f { return rotY(a) * p; }
fn opRotateZ(p: vec3f, a: f32) -> vec3f { return rotZ(a) * p; }
fn opTranslate(p: vec3f, t: vec3f) -> vec3f { return p - t; }
fn opScale(p: vec3f, s: f32) -> vec3f { return p / s; }
fn opScale3(p: vec3f, s: vec3f) -> vec3f { return p / s; }
fn opRepPolar(p: vec3f, n: f32) -> vec3f {
  let an = 6.283185307179586476925286766559 / max(n, 1.0);
  let a = atan2(p.z, p.x);
  let r = length(p.xz);
  let na = an * floor(0.5 + a / an);
  let ca = a - na;
  return vec3f(cos(ca) * r, p.y, sin(ca) * r);
}
fn opOnion(d: f32, t: f32) -> f32 { return abs(d) - t; }
`;

const WGSL_FLATIR_FULL = String.raw`
fn sdSphere(p: vec3f, s: f32) -> f32 { return length(p) - s; }
fn sdBox(p: vec3f, b: vec3f) -> f32 {
  let q = abs(p) - b;
  return length(max(q, vec3f(0.0))) + min(max(q.x, max(q.y, q.z)), 0.0);
}
fn sdRoundBox(p: vec3f, b: vec3f, r: f32) -> f32 {
  let q = abs(p) - b + r;
  return length(max(q, vec3f(0.0))) + min(max(q.x, max(q.y, q.z)), 0.0) - r;
}
fn sdTorus(p: vec3f, t: vec2f) -> f32 {
  let q = vec2f(length(p.xz) - t.x, p.y);
  return length(q) - t.y;
}
fn sdCylinder(p: vec3f, h: f32, r: f32) -> f32 {
  let d = abs(vec2f(length(p.xz), p.y)) - vec2f(r, h);
  return min(max(d.x, d.y), 0.0) + length(max(d, vec2f(0.0)));
}
fn sdCapsule(p: vec3f, a: vec3f, b: vec3f, r: f32) -> f32 {
  let pa = p - a;
  let ba = b - a;
  let h = clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0);
  return length(pa - ba * h) - r;
}
fn sdCone(p: vec3f, h: f32, r: f32) -> f32 {
  let q = vec2f(length(p.xz), p.y);
  let tip = q - vec2f(0.0, h);
  let mantle = q - r * q.y / h;
  let d = max(tip.x, tip.y);
  return sqrt(min(dot(tip, tip), dot(mantle, mantle))) * sign(d);
}
fn sdEllipsoid(p: vec3f, r: vec3f) -> f32 {
  let k0 = length(p / r);
  let k1 = length(p / (r * r));
  return k0 * (k0 - 1.0) / k1;
}
fn sdOctahedron(p: vec3f, s: f32) -> f32 {
  let q = abs(p);
  return (q.x + q.y + q.z - s) * 0.57735027;
}
fn sdHexPrism(p: vec3f, h: vec2f) -> f32 {
  let k = vec3f(-0.8660254, 0.5, 0.57735);
  var q = abs(p);
  let qxy = q.xy - 2.0 * min(dot(k.xy, q.xy), 0.0) * k.xy;
  q = vec3f(qxy.x, qxy.y, q.z);
  let d = vec2f(
    length(qxy - vec2f(clamp(q.x, -k.z * h.x, k.z * h.x), h.x)) * sign(q.y - h.x),
    q.z - h.y
  );
  return min(max(d.x, d.y), 0.0) + length(max(d, vec2f(0.0)));
}
fn opU(d1: f32, d2: f32) -> f32 { return min(d1, d2); }
fn opI(d1: f32, d2: f32) -> f32 { return max(d1, d2); }
fn opS(d1: f32, d2: f32) -> f32 { return max(d1, -d2); }
fn opSmoothUnion(d1: f32, d2: f32, k: f32) -> f32 {
  let h = clamp(0.5 + 0.5 * (d2 - d1) / k, 0.0, 1.0);
  return mix(d2, d1, h) - k * h * (1.0 - h);
}
fn opSmoothIntersection(d1: f32, d2: f32, k: f32) -> f32 {
  let h = clamp(0.5 - 0.5 * (d2 - d1) / k, 0.0, 1.0);
  return mix(d2, d1, h) + k * h * (1.0 - h);
}
fn opSmoothSubtraction(d1: f32, d2: f32, k: f32) -> f32 {
  let h = clamp(0.5 - 0.5 * (d2 + d1) / k, 0.0, 1.0);
  return mix(d2, -d1, h) + k * h * (1.0 - h);
}
fn rotX(a: f32) -> mat3x3f {
  let c = cos(a); let s = sin(a);
  return mat3x3f(vec3f(1,0,0), vec3f(0,c,s), vec3f(0,-s,c));
}
fn rotY(a: f32) -> mat3x3f {
  let c = cos(a); let s = sin(a);
  return mat3x3f(vec3f(c,0,-s), vec3f(0,1,0), vec3f(s,0,c));
}
fn rotZ(a: f32) -> mat3x3f {
  let c = cos(a); let s = sin(a);
  return mat3x3f(vec3f(c,s,0), vec3f(-s,c,0), vec3f(0,0,1));
}
fn opRotateX(p: vec3f, a: f32) -> vec3f { return rotX(a) * p; }
fn opRotateY(p: vec3f, a: f32) -> vec3f { return rotY(a) * p; }
fn opRotateZ(p: vec3f, a: f32) -> vec3f { return rotZ(a) * p; }
fn opTranslate(p: vec3f, t: vec3f) -> vec3f { return p - t; }
fn opScale(p: vec3f, s: f32) -> vec3f { return p / s; }
fn opScale3(p: vec3f, s: vec3f) -> vec3f { return p / s; }

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
  rootTemp: u32,
  time: f32,
}

@group(0) @binding(0) var<uniform> u: Uniforms;
@group(0) @binding(1) var<storage, read> transforms: array<vec4f>;
@group(0) @binding(2) var<storage, read> spheres: array<vec4f>;
@group(0) @binding(3) var<storage, read> boxes: array<vec4f>;
@group(0) @binding(4) var<storage, read> instrs: array<vec4u>;
@group(0) @binding(5) var<storage, read> cylinders: array<vec4f>;
@group(0) @binding(6) var<storage, read> smoothKs: array<vec4f>;
@group(0) @binding(7) var outImage: texture_storage_2d<rgba8unorm, write>;

fn rotateByQuatInverse(v: vec3f, q: vec4f) -> vec3f {
  let cq = vec3f(-q.x, -q.y, -q.z);
  let t = 2.0 * cross(cq, v);
  return v + q.w * t + cross(cq, t);
}
fn minScale(s: vec3f) -> f32 { return min(s.x, min(s.y, s.z)); }
fn sdfCylinderY(p: vec3f, r: f32, h: f32) -> f32 {
  let d = abs(vec2f(length(p.xz), p.y)) - vec2f(r, h);
  return min(max(d.x, d.y), 0.0) + length(max(d, vec2f(0.0)));
}
fn evalSdf(p: vec3f) -> f32 {
  var temps: array<f32, 64>;
  var tempCount = 0u;
  let ni = arrayLength(&instrs);
  for (var i = 0u; i < ni; i++) {
    let instr = instrs[i];
    let op = instr.x;
    let arg0 = instr.y;
    let arg1 = instr.z;
    let ci = instr.w;
    if (op == 0u) {
      let ti = arg0;
      let pos = transforms[ti * 3u];
      let scl = transforms[ti * 3u + 1u];
      let quat = transforms[ti * 3u + 2u];
      let pL = rotateByQuatInverse((p - pos.xyz), quat) / scl.xyz;
      temps[tempCount] = sdSphere(pL, spheres[ci].x) * minScale(scl.xyz);
      tempCount++;
    } else if (op == 1u) {
      let ti = arg0;
      let pos = transforms[ti * 3u];
      let scl = transforms[ti * 3u + 1u];
      let quat = transforms[ti * 3u + 2u];
      let pL = rotateByQuatInverse((p - pos.xyz), quat) / scl.xyz;
      temps[tempCount] = sdBox(pL, boxes[ci].xyz) * minScale(scl.xyz);
      tempCount++;
    } else if (op == 2u) {
      temps[tempCount] = min(
        select(1e10, temps[arg0], arg0 < tempCount),
        select(1e10, temps[arg1], arg1 < tempCount));
      tempCount++;
    } else if (op == 3u) {
      temps[tempCount] = max(
        select(1e10, temps[arg0], arg0 < tempCount),
        select(1e10, temps[arg1], arg1 < tempCount));
      tempCount++;
    } else if (op == 4u) {
      temps[tempCount] = max(
        select(1e10, temps[arg0], arg0 < tempCount),
        -select(1e10, temps[arg1], arg1 < tempCount));
      tempCount++;
    } else if (op == 5u) {
      let ti = arg0;
      let pos = transforms[ti * 3u];
      let scl = transforms[ti * 3u + 1u];
      let quat = transforms[ti * 3u + 2u];
      let pL = rotateByQuatInverse((p - pos.xyz), quat) / scl.xyz;
      temps[tempCount] = sdfCylinderY(pL, cylinders[ci].x, cylinders[ci].y) * minScale(scl.xyz);
      tempCount++;
    } else if (op == 6u) {
      let k = smoothKs[ci].x;
      temps[tempCount] = opSmoothUnion(
        select(1e10, temps[arg0], arg0 < tempCount),
        select(1e10, temps[arg1], arg1 < tempCount),
        k);
      tempCount++;
    }
  }
  return select(1e10, temps[u.rootTemp], u.rootTemp < tempCount);
}
fn map(p: vec3f) -> f32 { return evalSdf(p); }

const MAX_STEPS = 96u;
const MAX_DIST  = 60.0;
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
    t += d;
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
    light += MAT_COL * FILL_COL * fill * 0.5;
    light += RIM_COL * rim * 0.35;
    light += MAT_COL * AMB_COL * (0.5 + 0.5 * n.y);
    light += vec3f(0.9, 0.95, 1.0) * spec * 0.6;
    light *= ao;
    col = light;
  } else {
    col = background(rd);
  }
  col = pow(col, vec3f(1.0 / 2.2));
  let ctr = (px + 0.5) / res - 0.5;
  let vig = 1.0 - 0.3 * dot(ctr, ctr);
  col *= vig;
  col = clamp(col, vec3f(0.0), vec3f(1.0));
  textureStore(outImage, vec2i(i32(id.x), i32(id.y)), vec4f(col, 1.0));
}
`.replace(
  'const MAT_COL   = vec3f(0.95, 0.6, 0.25);',
  `const MAT_COL   = vec3f(0.95, 0.6, 0.25);`,
);

const BLIT_WGSL = String.raw`
@group(0) @binding(0) var src: texture_2d<f32>;
@group(0) @binding(1) var samp: sampler;
struct Varyings {
  @builtin(position) pos: vec4f,
  @location(0) uv: vec2f,
}
@vertex fn vs(@builtin(vertex_index) i: u32) -> Varyings {
  let corners = array(vec2f(-1,-1), vec2f(3,-1), vec2f(-1,3));
  let p = corners[i];
  var o: Varyings;
  o.pos = vec4f(p, 0, 1);
  o.uv = p * 0.5 + 0.5;
  o.uv.y = 1.0 - o.uv.y;
  return o;
}
@fragment fn fs(v: Varyings) -> @location(0) vec4f {
  return textureSampleLevel(src, samp, v.uv, 0.0);
}
`;

const UNIFORM_SIZE = 96;
const RENDER_SCALE = 1.0;
const DEFAULT_MAP = String.raw`fn map(p: vec3f) -> f32 { return sdSphere(p, 1.0); }`;

/** Strip markdown fences from model output (```wgsl, ``wgsl typos, trailing ```). */
function sanitizeWgslUserCode(code: string): string {
  let s = code
    .replace(/^\uFEFF/, '')
    .replace(/[\u2018\u2019\u201a\u201b]/g, '`')
    .trim();
  for (let i = 0; i < 8; i++) {
    const prev = s;
    s = s.replace(/^`{3,}[\w]*\s*\r?\n?/m, '').trimStart();
    s = s.replace(/^`{2}wgsl(?:\s*\r?\n|\s+)/i, '').trimStart();
    s = s.replace(/^`+\s*\r?\n/m, '').trimStart();
    if (s === prev) break;
  }
  const end = s.lastIndexOf('```');
  if (end >= 0) s = s.slice(0, end);
  s = s.trim();
  const mapSig = /\bfn\s+map\s*\(\s*p\s*:\s*vec3f\s*\)\s*->\s*f32/;
  const m = s.match(mapSig);
  if (m && m.index !== undefined && m.index > 0) {
    s = s.slice(m.index).trim();
  }
  return s;
}

function assembleUserWgsl(userMap: string): string {
  const userTail = String.raw`
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
  rootTemp: u32,
  time: f32,
}

@group(0) @binding(0) var<uniform> u: Uniforms;
@group(0) @binding(1) var outImage: texture_storage_2d<rgba8unorm, write>;

const MAX_STEPS = 96u;
const MAX_DIST  = 60.0;
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
    t += d;
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
    light += MAT_COL * FILL_COL * fill * 0.5;
    light += RIM_COL * rim * 0.35;
    light += MAT_COL * AMB_COL * (0.5 + 0.5 * n.y);
    light += vec3f(0.9, 0.95, 1.0) * spec * 0.6;
    light *= ao;
    col = light;
  } else {
    col = background(rd);
  }
  col = pow(col, vec3f(1.0 / 2.2));
  let ctr = (px + 0.5) / res - 0.5;
  let vig = 1.0 - 0.3 * dot(ctr, ctr);
  col *= vig;
  col = clamp(col, vec3f(0.0), vec3f(1.0));
  textureStore(outImage, vec2i(i32(id.x), i32(id.y)), vec4f(col, 1.0));
}
`.replace(
    'const MAT_COL   = vec3f(0.95, 0.6, 0.25);',
    `const MAT_COL   = vec3f(0.95, 0.6, 0.25);`,
  );
  return SDF_LIBRARY_WGSL + '\n' + userMap + '\n' + userTail;
}


interface OrbitCamera {
  theta: number;
  phi: number;
  radius: number;
  target: [number, number, number];
  fov: number;
}

type SceneMode = 'wgsl' | 'flatir';

export class WebGPURenderer {
  private device!: GPUDevice;
  private wgslPipeline!: GPUComputePipeline;
  private flatirPipeline!: GPUComputePipeline;
  private blitPipeline!: GPURenderPipeline;
  private canvasContext!: GPUCanvasContext;
  private canvasFormat!: GPUTextureFormat;
  private startTime = performance.now();

  private uniformBuf!: GPUBuffer;
  private uniformData = new ArrayBuffer(UNIFORM_SIZE);
  private uniformF32 = new Float32Array(this.uniformData);
  private uniformU32 = new Uint32Array(this.uniformData);

  private sceneBuffers: {
    transform: GPUBuffer;
    sphere: GPUBuffer;
    box: GPUBuffer;
    instr: GPUBuffer;
    cylinder: GPUBuffer;
    smoothK: GPUBuffer;
    rootTemp: number;
  } | null = null;

  private computeTexture: GPUTexture | null = null;
  private computeTextureW = 0;
  private computeTextureH = 0;
  private sampler!: GPUSampler;

  private sceneMode: SceneMode = 'wgsl';
  needsCompute = true;

  private cam: OrbitCamera = {
    theta: 0.4,
    phi: 0.35,
    radius: 6,
    target: [0, 0.3, 0],
    fov: 1.0,
  };

  private dragging = false;
  private lastMouse = [0, 0];

  async init(canvas: HTMLCanvasElement): Promise<boolean> {
    const adapter = await navigator.gpu?.requestAdapter();
    if (!adapter) return false;
    this.device = await adapter.requestDevice();
    if (!this.device) return false;

    this.canvasContext = canvas.getContext('webgpu')!;
    if (!this.canvasContext) return false;

    this.canvasFormat = navigator.gpu.getPreferredCanvasFormat();
    this.canvasContext.configure({ device: this.device, format: this.canvasFormat, alphaMode: 'opaque' });

    const flatMod = this.device.createShaderModule({ code: WGSL_FLATIR_FULL });
    this.flatirPipeline = this.device.createComputePipeline({
      layout: 'auto',
      compute: { module: flatMod, entryPoint: 'main' },
    });

    const wgslMod = this.device.createShaderModule({ code: assembleUserWgsl(DEFAULT_MAP) });
    this.wgslPipeline = this.device.createComputePipeline({
      layout: 'auto',
      compute: { module: wgslMod, entryPoint: 'main' },
    });

    const blitMod = this.device.createShaderModule({ code: BLIT_WGSL });
    this.blitPipeline = this.device.createRenderPipeline({
      layout: 'auto',
      vertex: { module: blitMod, entryPoint: 'vs' },
      fragment: {
        module: blitMod,
        entryPoint: 'fs',
        targets: [{ format: this.canvasFormat }],
      },
      primitive: { topology: 'triangle-list' },
    });

    this.uniformBuf = this.device.createBuffer({
      size: UNIFORM_SIZE,
      usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
    });

    this.sampler = this.device.createSampler({ magFilter: 'linear', minFilter: 'linear' });

    this.initInput(canvas);
    this.needsCompute = true;
    return true;
  }

  private markComputeDirty(): void {
    this.needsCompute = true;
  }

  private initInput(canvas: HTMLCanvasElement): void {
    canvas.addEventListener('pointerdown', (e) => {
      this.dragging = true;
      this.lastMouse = [e.clientX, e.clientY];
      canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener('pointermove', (e) => {
      if (!this.dragging) return;
      const dx = e.clientX - this.lastMouse[0];
      const dy = e.clientY - this.lastMouse[1];
      this.lastMouse = [e.clientX, e.clientY];
      this.cam.theta -= dx * 0.005;
      this.cam.phi = Math.max(-1.2, Math.min(1.2, this.cam.phi + dy * 0.005));
      this.markComputeDirty();
    });
    canvas.addEventListener('pointerup', () => { this.dragging = false; });
    canvas.addEventListener('pointercancel', () => { this.dragging = false; });
    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.cam.radius = Math.max(1.5, Math.min(40, this.cam.radius * (1 + e.deltaY * 0.001)));
      this.markComputeDirty();
    }, { passive: false });
  }

  private getCameraVectors(): { pos: Float32Array; right: Float32Array; up: Float32Array; fwd: Float32Array } {
    const { theta, phi, radius, target } = this.cam;
    const ct = Math.cos(theta), st = Math.sin(theta);
    const cp = Math.cos(phi), sp = Math.sin(phi);
    const eye = [
      target[0] + radius * cp * st,
      target[1] + radius * sp,
      target[2] + radius * cp * ct,
    ];
    const fwd = [target[0] - eye[0], target[1] - eye[1], target[2] - eye[2]];
    const len = Math.sqrt(fwd[0] ** 2 + fwd[1] ** 2 + fwd[2] ** 2);
    fwd[0] /= len; fwd[1] /= len; fwd[2] /= len;
    const worldUp = [0, 1, 0];
    const right = [
      fwd[1] * worldUp[2] - fwd[2] * worldUp[1],
      fwd[2] * worldUp[0] - fwd[0] * worldUp[2],
      fwd[0] * worldUp[1] - fwd[1] * worldUp[0],
    ];
    const rLen = Math.sqrt(right[0] ** 2 + right[1] ** 2 + right[2] ** 2);
    right[0] /= rLen; right[1] /= rLen; right[2] /= rLen;
    const up = [
      right[1] * fwd[2] - right[2] * fwd[1],
      right[2] * fwd[0] - right[0] * fwd[2],
      right[0] * fwd[1] - right[1] * fwd[0],
    ];
    return {
      pos: new Float32Array(eye),
      right: new Float32Array(right),
      up: new Float32Array(up),
      fwd: new Float32Array(fwd),
    };
  }

  private makeBuffer(data: Float32Array | Uint32Array, usage: number): GPUBuffer {
    const b = this.device.createBuffer({
      size: Math.max(data.byteLength, 16),
      usage: usage | GPUBufferUsage.COPY_DST,
    });
    this.device.queue.writeBuffer(b, 0, data.buffer, data.byteOffset, data.byteLength);
    return b;
  }

  setWgslScene(scene: WGSLSdfScene): void {
    const userMap = sanitizeWgslUserCode(scene.code);
    if (!/fn\s+map\s*\(\s*p\s*:\s*vec3f\s*\)\s*->\s*f32/.test(userMap)) {
      return;
    }
    try {
      const code = assembleUserWgsl(userMap);
      const mod = this.device.createShaderModule({ code });
      this.wgslPipeline = this.device.createComputePipeline({
        layout: 'auto',
        compute: { module: mod, entryPoint: 'main' },
      });
      this.sceneMode = 'wgsl';
      if (this.sceneBuffers) {
        this.sceneBuffers.transform.destroy();
        this.sceneBuffers.sphere.destroy();
        this.sceneBuffers.box.destroy();
        this.sceneBuffers.instr.destroy();
        this.sceneBuffers.cylinder.destroy();
        this.sceneBuffers.smoothK.destroy();
        this.sceneBuffers = null;
      }
      this.markComputeDirty();
    } catch {
      /* invalid WGSL: keep previous pipeline */
    }
  }

  setScene(scene: PackedFlatIR): void {
    if (!scene?.instrs || !Array.isArray(scene.instrs)) {
      return;
    }
    if (this.sceneBuffers) {
      this.sceneBuffers.transform.destroy();
      this.sceneBuffers.sphere.destroy();
      this.sceneBuffers.box.destroy();
      this.sceneBuffers.instr.destroy();
      this.sceneBuffers.cylinder.destroy();
      this.sceneBuffers.smoothK.destroy();
    }
    const { instrs, transforms, spheres, boxes, cylinders, smoothKs, rootTemp } = scene;
    const instrData = new Uint32Array(instrs.length * 4);
    for (let i = 0; i < instrs.length; i++) {
      instrData[i * 4] = instrs[i].op;
      instrData[i * 4 + 1] = instrs[i].arg0;
      instrData[i * 4 + 2] = instrs[i].arg1;
      instrData[i * 4 + 3] = instrs[i].constIdx;
    }
    const S = GPUBufferUsage.STORAGE;
    this.sceneBuffers = {
      transform: this.makeBuffer(new Float32Array(transforms), S),
      sphere: this.makeBuffer(new Float32Array(spheres), S),
      box: this.makeBuffer(new Float32Array(boxes), S),
      instr: this.makeBuffer(instrData, S),
      cylinder: this.makeBuffer(new Float32Array(cylinders?.length ? cylinders : [0, 0, 0, 0]), S),
      smoothK: this.makeBuffer(new Float32Array(smoothKs?.length ? smoothKs : [0, 0, 0, 0]), S),
      rootTemp,
    };
    this.sceneMode = 'flatir';
    this.markComputeDirty();
  }

  private ensureComputeTexture(w: number, h: number): GPUTexture {
    if (this.computeTexture && this.computeTextureW === w && this.computeTextureH === h) {
      return this.computeTexture;
    }
    if (this.computeTexture) this.computeTexture.destroy();
    this.computeTexture = this.device.createTexture({
      size: [w, h, 1],
      format: 'rgba8unorm',
      usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.TEXTURE_BINDING,
    });
    this.computeTextureW = w;
    this.computeTextureH = h;
    return this.computeTexture;
  }

  private writeUniforms(rw: number, rh: number, rootTemp: number): void {
    const camVecs = this.getCameraVectors();
    const time = (performance.now() - this.startTime) * 0.001;
    const uf = this.uniformF32;
    const uu = this.uniformU32;
    uf[0] = rw; uf[1] = rh;
    uf[4] = camVecs.pos[0]; uf[5] = camVecs.pos[1]; uf[6] = camVecs.pos[2];
    uf[8] = camVecs.right[0]; uf[9] = camVecs.right[1]; uf[10] = camVecs.right[2];
    uf[12] = camVecs.up[0]; uf[13] = camVecs.up[1]; uf[14] = camVecs.up[2];
    uf[16] = camVecs.fwd[0]; uf[17] = camVecs.fwd[1]; uf[18] = camVecs.fwd[2];
    uf[19] = this.cam.fov;
    uu[20] = rootTemp;
    uf[21] = time;
    this.device.queue.writeBuffer(this.uniformBuf, 0, this.uniformData);
  }

  render(): void {
    if (!this.device) return;
    if (this.sceneMode === 'flatir' && !this.sceneBuffers) return;

    const canvas = this.canvasContext.canvas;
    const canvasW = canvas.width;
    const canvasH = canvas.height;
    if (canvasW === 0 || canvasH === 0) return;

    const rw = Math.max(1, Math.floor(canvasW * RENDER_SCALE));
    const rh = Math.max(1, Math.floor(canvasH * RENDER_SCALE));
    const computeTex = this.ensureComputeTexture(rw, rh);

    const encoder = this.device.createCommandEncoder();

    if (this.needsCompute) {
      const pipeline = this.sceneMode === 'flatir' ? this.flatirPipeline : this.wgslPipeline;
      const rootTemp = this.sceneMode === 'flatir' && this.sceneBuffers ? this.sceneBuffers.rootTemp : 0;
      this.writeUniforms(rw, rh, rootTemp);

      if (this.sceneMode === 'flatir' && this.sceneBuffers) {
        const sb = this.sceneBuffers;
        const bg = this.device.createBindGroup({
          layout: pipeline.getBindGroupLayout(0),
          entries: [
            { binding: 0, resource: { buffer: this.uniformBuf } },
            { binding: 1, resource: { buffer: sb.transform } },
            { binding: 2, resource: { buffer: sb.sphere } },
            { binding: 3, resource: { buffer: sb.box } },
            { binding: 4, resource: { buffer: sb.instr } },
            { binding: 5, resource: { buffer: sb.cylinder } },
            { binding: 6, resource: { buffer: sb.smoothK } },
            { binding: 7, resource: computeTex.createView() },
          ],
        });
        const cpass = encoder.beginComputePass();
        cpass.setPipeline(pipeline);
        cpass.setBindGroup(0, bg);
        cpass.dispatchWorkgroups(Math.ceil(rw / 8), Math.ceil(rh / 8));
        cpass.end();
      } else {
        const bg = this.device.createBindGroup({
          layout: pipeline.getBindGroupLayout(0),
          entries: [
            { binding: 0, resource: { buffer: this.uniformBuf } },
            { binding: 1, resource: computeTex.createView() },
          ],
        });
        const cpass = encoder.beginComputePass();
        cpass.setPipeline(pipeline);
        cpass.setBindGroup(0, bg);
        cpass.dispatchWorkgroups(Math.ceil(rw / 8), Math.ceil(rh / 8));
        cpass.end();
      }
      this.needsCompute = false;
    }

    const canvasTexture = this.canvasContext.getCurrentTexture();
    const blitBg = this.device.createBindGroup({
      layout: this.blitPipeline.getBindGroupLayout(0),
      entries: [
        { binding: 0, resource: computeTex.createView() },
        { binding: 1, resource: this.sampler },
      ],
    });
    const rpass = encoder.beginRenderPass({
      colorAttachments: [{
        view: canvasTexture.createView(),
        loadOp: 'clear',
        storeOp: 'store',
        clearValue: { r: 0, g: 0, b: 0, a: 1 },
      }],
    });
    rpass.setPipeline(this.blitPipeline);
    rpass.setBindGroup(0, blitBg);
    rpass.draw(3);
    rpass.end();

    this.device.queue.submit([encoder.finish()]);
  }

  handleResize(): void {
    this.markComputeDirty();
  }
}
