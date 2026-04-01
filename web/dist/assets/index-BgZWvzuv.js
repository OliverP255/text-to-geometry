(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const n of document.querySelectorAll('link[rel="modulepreload"]'))s(n);new MutationObserver(n=>{for(const i of n)if(i.type==="childList")for(const o of i.addedNodes)o.tagName==="LINK"&&o.rel==="modulepreload"&&s(o)}).observe(document,{childList:!0,subtree:!0});function t(n){const i={};return n.integrity&&(i.integrity=n.integrity),n.referrerPolicy&&(i.referrerPolicy=n.referrerPolicy),n.crossOrigin==="use-credentials"?i.credentials="include":n.crossOrigin==="anonymous"?i.credentials="omit":i.credentials="same-origin",i}function s(n){if(n.ep)return;n.ep=!0;const i=t(n);fetch(n.href,i)}})();const ve=String.raw`
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
`,_e=String.raw`
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
`.replace("const MAT_COL   = vec3f(0.95, 0.6, 0.25);","const MAT_COL   = vec3f(0.95, 0.6, 0.25);"),be=String.raw`
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
`,G=96,J=1,xe=String.raw`fn map(p: vec3f) -> f32 { return sdSphere(p, 1.0); }`;function we(r){let e=r.replace(/^\uFEFF/,"").replace(/[\u2018\u2019\u201a\u201b]/g,"`").trim();for(let i=0;i<8;i++){const o=e;if(e=e.replace(/^`{3,}[\w]*\s*\r?\n?/m,"").trimStart(),e=e.replace(/^`{2}wgsl(?:\s*\r?\n|\s+)/i,"").trimStart(),e=e.replace(/^`+\s*\r?\n/m,"").trimStart(),e===o)break}const t=e.lastIndexOf("```");t>=0&&(e=e.slice(0,t)),e=e.trim();const s=/\bfn\s+map\s*\(\s*p\s*:\s*vec3f\s*\)\s*->\s*f32/,n=e.match(s);return n&&n.index!==void 0&&n.index>0&&(e=e.slice(n.index).trim()),e}function Q(r){const e=String.raw`
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
`.replace("const MAT_COL   = vec3f(0.95, 0.6, 0.25);","const MAT_COL   = vec3f(0.95, 0.6, 0.25);");return ve+`
`+r+`
`+e}class ke{constructor(){this.startTime=performance.now(),this.uniformData=new ArrayBuffer(G),this.uniformF32=new Float32Array(this.uniformData),this.uniformU32=new Uint32Array(this.uniformData),this.sceneBuffers=null,this.computeTexture=null,this.computeTextureW=0,this.computeTextureH=0,this.sceneMode="wgsl",this.needsCompute=!0,this.cam={theta:.4,phi:.35,radius:6,target:[0,.3,0],fov:1},this.dragging=!1,this.lastMouse=[0,0]}async init(e){var o;const t=await((o=navigator.gpu)==null?void 0:o.requestAdapter());if(!t||(this.device=await t.requestDevice(),!this.device)||(this.canvasContext=e.getContext("webgpu"),!this.canvasContext))return!1;this.canvasFormat=navigator.gpu.getPreferredCanvasFormat(),this.canvasContext.configure({device:this.device,format:this.canvasFormat,alphaMode:"opaque"});const s=this.device.createShaderModule({code:_e});this.flatirPipeline=this.device.createComputePipeline({layout:"auto",compute:{module:s,entryPoint:"main"}});const n=this.device.createShaderModule({code:Q(xe)});this.wgslPipeline=this.device.createComputePipeline({layout:"auto",compute:{module:n,entryPoint:"main"}});const i=this.device.createShaderModule({code:be});return this.blitPipeline=this.device.createRenderPipeline({layout:"auto",vertex:{module:i,entryPoint:"vs"},fragment:{module:i,entryPoint:"fs",targets:[{format:this.canvasFormat}]},primitive:{topology:"triangle-list"}}),this.uniformBuf=this.device.createBuffer({size:G,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST}),this.sampler=this.device.createSampler({magFilter:"linear",minFilter:"linear"}),this.initInput(e),this.needsCompute=!0,!0}markComputeDirty(){this.needsCompute=!0}initInput(e){e.addEventListener("pointerdown",t=>{this.dragging=!0,this.lastMouse=[t.clientX,t.clientY],e.setPointerCapture(t.pointerId)}),e.addEventListener("pointermove",t=>{if(!this.dragging)return;const s=t.clientX-this.lastMouse[0],n=t.clientY-this.lastMouse[1];this.lastMouse=[t.clientX,t.clientY],this.cam.theta-=s*.005,this.cam.phi=Math.max(-1.2,Math.min(1.2,this.cam.phi+n*.005)),this.markComputeDirty()}),e.addEventListener("pointerup",()=>{this.dragging=!1}),e.addEventListener("pointercancel",()=>{this.dragging=!1}),e.addEventListener("wheel",t=>{t.preventDefault(),this.cam.radius=Math.max(1.5,Math.min(40,this.cam.radius*(1+t.deltaY*.001))),this.markComputeDirty()},{passive:!1})}getCameraVectors(){const{theta:e,phi:t,radius:s,target:n}=this.cam,i=Math.cos(e),o=Math.sin(e),a=Math.cos(t),f=Math.sin(t),l=[n[0]+s*a*o,n[1]+s*f,n[2]+s*a*i],c=[n[0]-l[0],n[1]-l[1],n[2]-l[2]],u=Math.sqrt(c[0]**2+c[1]**2+c[2]**2);c[0]/=u,c[1]/=u,c[2]/=u;const m=[0,1,0],p=[c[1]*m[2]-c[2]*m[1],c[2]*m[0]-c[0]*m[2],c[0]*m[1]-c[1]*m[0]],_=Math.sqrt(p[0]**2+p[1]**2+p[2]**2);p[0]/=_,p[1]/=_,p[2]/=_;const k=[p[1]*c[2]-p[2]*c[1],p[2]*c[0]-p[0]*c[2],p[0]*c[1]-p[1]*c[0]];return{pos:new Float32Array(l),right:new Float32Array(p),up:new Float32Array(k),fwd:new Float32Array(c)}}makeBuffer(e,t){const s=this.device.createBuffer({size:Math.max(e.byteLength,16),usage:t|GPUBufferUsage.COPY_DST});return this.device.queue.writeBuffer(s,0,e.buffer,e.byteOffset,e.byteLength),s}setWgslScene(e){const t=we(e.code);if(/fn\s+map\s*\(\s*p\s*:\s*vec3f\s*\)\s*->\s*f32/.test(t))try{const s=Q(t),n=this.device.createShaderModule({code:s});this.wgslPipeline=this.device.createComputePipeline({layout:"auto",compute:{module:n,entryPoint:"main"}}),this.sceneMode="wgsl",this.sceneBuffers&&(this.sceneBuffers.transform.destroy(),this.sceneBuffers.sphere.destroy(),this.sceneBuffers.box.destroy(),this.sceneBuffers.instr.destroy(),this.sceneBuffers.cylinder.destroy(),this.sceneBuffers.smoothK.destroy(),this.sceneBuffers=null),this.markComputeDirty()}catch{}}setScene(e){if(!(e!=null&&e.instrs)||!Array.isArray(e.instrs))return;this.sceneBuffers&&(this.sceneBuffers.transform.destroy(),this.sceneBuffers.sphere.destroy(),this.sceneBuffers.box.destroy(),this.sceneBuffers.instr.destroy(),this.sceneBuffers.cylinder.destroy(),this.sceneBuffers.smoothK.destroy());const{instrs:t,transforms:s,spheres:n,boxes:i,cylinders:o,smoothKs:a,rootTemp:f}=e,l=new Uint32Array(t.length*4);for(let u=0;u<t.length;u++)l[u*4]=t[u].op,l[u*4+1]=t[u].arg0,l[u*4+2]=t[u].arg1,l[u*4+3]=t[u].constIdx;const c=GPUBufferUsage.STORAGE;this.sceneBuffers={transform:this.makeBuffer(new Float32Array(s),c),sphere:this.makeBuffer(new Float32Array(n),c),box:this.makeBuffer(new Float32Array(i),c),instr:this.makeBuffer(l,c),cylinder:this.makeBuffer(new Float32Array(o!=null&&o.length?o:[0,0,0,0]),c),smoothK:this.makeBuffer(new Float32Array(a!=null&&a.length?a:[0,0,0,0]),c),rootTemp:f},this.sceneMode="flatir",this.markComputeDirty()}ensureComputeTexture(e,t){return this.computeTexture&&this.computeTextureW===e&&this.computeTextureH===t?this.computeTexture:(this.computeTexture&&this.computeTexture.destroy(),this.computeTexture=this.device.createTexture({size:[e,t,1],format:"rgba8unorm",usage:GPUTextureUsage.STORAGE_BINDING|GPUTextureUsage.TEXTURE_BINDING}),this.computeTextureW=e,this.computeTextureH=t,this.computeTexture)}writeUniforms(e,t,s){const n=this.getCameraVectors(),i=(performance.now()-this.startTime)*.001,o=this.uniformF32,a=this.uniformU32;o[0]=e,o[1]=t,o[4]=n.pos[0],o[5]=n.pos[1],o[6]=n.pos[2],o[8]=n.right[0],o[9]=n.right[1],o[10]=n.right[2],o[12]=n.up[0],o[13]=n.up[1],o[14]=n.up[2],o[16]=n.fwd[0],o[17]=n.fwd[1],o[18]=n.fwd[2],o[19]=this.cam.fov,a[20]=s,o[21]=i,this.device.queue.writeBuffer(this.uniformBuf,0,this.uniformData)}render(){if(!this.device||this.sceneMode==="flatir"&&!this.sceneBuffers)return;const e=this.canvasContext.canvas,t=e.width,s=e.height;if(t===0||s===0)return;const n=Math.max(1,Math.floor(t*J)),i=Math.max(1,Math.floor(s*J)),o=this.ensureComputeTexture(n,i),a=this.device.createCommandEncoder();if(this.needsCompute){const u=this.sceneMode==="flatir"?this.flatirPipeline:this.wgslPipeline,m=this.sceneMode==="flatir"&&this.sceneBuffers?this.sceneBuffers.rootTemp:0;if(this.writeUniforms(n,i,m),this.sceneMode==="flatir"&&this.sceneBuffers){const p=this.sceneBuffers,_=this.device.createBindGroup({layout:u.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:this.uniformBuf}},{binding:1,resource:{buffer:p.transform}},{binding:2,resource:{buffer:p.sphere}},{binding:3,resource:{buffer:p.box}},{binding:4,resource:{buffer:p.instr}},{binding:5,resource:{buffer:p.cylinder}},{binding:6,resource:{buffer:p.smoothK}},{binding:7,resource:o.createView()}]}),k=a.beginComputePass();k.setPipeline(u),k.setBindGroup(0,_),k.dispatchWorkgroups(Math.ceil(n/8),Math.ceil(i/8)),k.end()}else{const p=this.device.createBindGroup({layout:u.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:this.uniformBuf}},{binding:1,resource:o.createView()}]}),_=a.beginComputePass();_.setPipeline(u),_.setBindGroup(0,p),_.dispatchWorkgroups(Math.ceil(n/8),Math.ceil(i/8)),_.end()}this.needsCompute=!1}const f=this.canvasContext.getCurrentTexture(),l=this.device.createBindGroup({layout:this.blitPipeline.getBindGroupLayout(0),entries:[{binding:0,resource:o.createView()},{binding:1,resource:this.sampler}]}),c=a.beginRenderPass({colorAttachments:[{view:f.createView(),loadOp:"clear",storeOp:"store",clearValue:{r:0,g:0,b:0,a:1}}]});c.setPipeline(this.blitPipeline),c.setBindGroup(0,l),c.draw(3),c.end(),this.device.queue.submit([a.finish()])}handleResize(){this.markComputeDirty()}}const x=Object.create(null);x.open="0";x.close="1";x.ping="2";x.pong="3";x.message="4";x.upgrade="5";x.noop="6";const B=Object.create(null);Object.keys(x).forEach(r=>{B[x[r]]=r});const D={type:"error",data:"parser error"},ne=typeof Blob=="function"||typeof Blob<"u"&&Object.prototype.toString.call(Blob)==="[object BlobConstructor]",ie=typeof ArrayBuffer=="function",oe=r=>typeof ArrayBuffer.isView=="function"?ArrayBuffer.isView(r):r&&r.buffer instanceof ArrayBuffer,Y=({type:r,data:e},t,s)=>ne&&e instanceof Blob?t?s(e):Z(e,s):ie&&(e instanceof ArrayBuffer||oe(e))?t?s(e):Z(new Blob([e]),s):s(x[r]+(e||"")),Z=(r,e)=>{const t=new FileReader;return t.onload=function(){const s=t.result.split(",")[1];e("b"+(s||""))},t.readAsDataURL(r)};function j(r){return r instanceof Uint8Array?r:r instanceof ArrayBuffer?new Uint8Array(r):new Uint8Array(r.buffer,r.byteOffset,r.byteLength)}let N;function Se(r,e){if(ne&&r.data instanceof Blob)return r.data.arrayBuffer().then(j).then(e);if(ie&&(r.data instanceof ArrayBuffer||oe(r.data)))return e(j(r.data));Y(r,!1,t=>{N||(N=new TextEncoder),e(N.encode(t))})}const ee="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/",T=typeof Uint8Array>"u"?[]:new Uint8Array(256);for(let r=0;r<ee.length;r++)T[ee.charCodeAt(r)]=r;const Ee=r=>{let e=r.length*.75,t=r.length,s,n=0,i,o,a,f;r[r.length-1]==="="&&(e--,r[r.length-2]==="="&&e--);const l=new ArrayBuffer(e),c=new Uint8Array(l);for(s=0;s<t;s+=4)i=T[r.charCodeAt(s)],o=T[r.charCodeAt(s+1)],a=T[r.charCodeAt(s+2)],f=T[r.charCodeAt(s+3)],c[n++]=i<<2|o>>4,c[n++]=(o&15)<<4|a>>2,c[n++]=(a&3)<<6|f&63;return l},Te=typeof ArrayBuffer=="function",H=(r,e)=>{if(typeof r!="string")return{type:"message",data:ae(r,e)};const t=r.charAt(0);return t==="b"?{type:"message",data:Ce(r.substring(1),e)}:B[t]?r.length>1?{type:B[t],data:r.substring(1)}:{type:B[t]}:D},Ce=(r,e)=>{if(Te){const t=Ee(r);return ae(t,e)}else return{base64:!0,data:r}},ae=(r,e)=>{switch(e){case"blob":return r instanceof Blob?r:new Blob([r]);case"arraybuffer":default:return r instanceof ArrayBuffer?r:r.buffer}},ce="",Ae=(r,e)=>{const t=r.length,s=new Array(t);let n=0;r.forEach((i,o)=>{Y(i,!1,a=>{s[o]=a,++n===t&&e(s.join(ce))})})},Be=(r,e)=>{const t=r.split(ce),s=[];for(let n=0;n<t.length;n++){const i=H(t[n],e);if(s.push(i),i.type==="error")break}return s};function Oe(){return new TransformStream({transform(r,e){Se(r,t=>{const s=t.length;let n;if(s<126)n=new Uint8Array(1),new DataView(n.buffer).setUint8(0,s);else if(s<65536){n=new Uint8Array(3);const i=new DataView(n.buffer);i.setUint8(0,126),i.setUint16(1,s)}else{n=new Uint8Array(9);const i=new DataView(n.buffer);i.setUint8(0,127),i.setBigUint64(1,BigInt(s))}r.data&&typeof r.data!="string"&&(n[0]|=128),e.enqueue(n),e.enqueue(t)})}})}let M;function C(r){return r.reduce((e,t)=>e+t.length,0)}function A(r,e){if(r[0].length===e)return r.shift();const t=new Uint8Array(e);let s=0;for(let n=0;n<e;n++)t[n]=r[0][s++],s===r[0].length&&(r.shift(),s=0);return r.length&&s<r[0].length&&(r[0]=r[0].slice(s)),t}function Re(r,e){M||(M=new TextDecoder);const t=[];let s=0,n=-1,i=!1;return new TransformStream({transform(o,a){for(t.push(o);;){if(s===0){if(C(t)<1)break;const f=A(t,1);i=(f[0]&128)===128,n=f[0]&127,n<126?s=3:n===126?s=1:s=2}else if(s===1){if(C(t)<2)break;const f=A(t,2);n=new DataView(f.buffer,f.byteOffset,f.length).getUint16(0),s=3}else if(s===2){if(C(t)<8)break;const f=A(t,8),l=new DataView(f.buffer,f.byteOffset,f.length),c=l.getUint32(0);if(c>Math.pow(2,21)-1){a.enqueue(D);break}n=c*Math.pow(2,32)+l.getUint32(4),s=3}else{if(C(t)<n)break;const f=A(t,n);a.enqueue(H(i?f:M.decode(f),e)),s=0}if(n===0||n>r){a.enqueue(D);break}}}})}const fe=4;function d(r){if(r)return Le(r)}function Le(r){for(var e in d.prototype)r[e]=d.prototype[e];return r}d.prototype.on=d.prototype.addEventListener=function(r,e){return this._callbacks=this._callbacks||{},(this._callbacks["$"+r]=this._callbacks["$"+r]||[]).push(e),this};d.prototype.once=function(r,e){function t(){this.off(r,t),e.apply(this,arguments)}return t.fn=e,this.on(r,t),this};d.prototype.off=d.prototype.removeListener=d.prototype.removeAllListeners=d.prototype.removeEventListener=function(r,e){if(this._callbacks=this._callbacks||{},arguments.length==0)return this._callbacks={},this;var t=this._callbacks["$"+r];if(!t)return this;if(arguments.length==1)return delete this._callbacks["$"+r],this;for(var s,n=0;n<t.length;n++)if(s=t[n],s===e||s.fn===e){t.splice(n,1);break}return t.length===0&&delete this._callbacks["$"+r],this};d.prototype.emit=function(r){this._callbacks=this._callbacks||{};for(var e=new Array(arguments.length-1),t=this._callbacks["$"+r],s=1;s<arguments.length;s++)e[s-1]=arguments[s];if(t){t=t.slice(0);for(var s=0,n=t.length;s<n;++s)t[s].apply(this,e)}return this};d.prototype.emitReserved=d.prototype.emit;d.prototype.listeners=function(r){return this._callbacks=this._callbacks||{},this._callbacks["$"+r]||[]};d.prototype.hasListeners=function(r){return!!this.listeners(r).length};const q=typeof Promise=="function"&&typeof Promise.resolve=="function"?e=>Promise.resolve().then(e):(e,t)=>t(e,0),g=typeof self<"u"?self:typeof window<"u"?window:Function("return this")(),qe="arraybuffer";function he(r,...e){return e.reduce((t,s)=>(r.hasOwnProperty(s)&&(t[s]=r[s]),t),{})}const Pe=g.setTimeout,Ne=g.clearTimeout;function P(r,e){e.useNativeTimers?(r.setTimeoutFn=Pe.bind(g),r.clearTimeoutFn=Ne.bind(g)):(r.setTimeoutFn=g.setTimeout.bind(g),r.clearTimeoutFn=g.clearTimeout.bind(g))}const Me=1.33;function Ie(r){return typeof r=="string"?De(r):Math.ceil((r.byteLength||r.size)*Me)}function De(r){let e=0,t=0;for(let s=0,n=r.length;s<n;s++)e=r.charCodeAt(s),e<128?t+=1:e<2048?t+=2:e<55296||e>=57344?t+=3:(s++,t+=4);return t}function ue(){return Date.now().toString(36).substring(3)+Math.random().toString(36).substring(2,5)}function Ue(r){let e="";for(let t in r)r.hasOwnProperty(t)&&(e.length&&(e+="&"),e+=encodeURIComponent(t)+"="+encodeURIComponent(r[t]));return e}function Fe(r){let e={},t=r.split("&");for(let s=0,n=t.length;s<n;s++){let i=t[s].split("=");e[decodeURIComponent(i[0])]=decodeURIComponent(i[1])}return e}class ze extends Error{constructor(e,t,s){super(e),this.description=t,this.context=s,this.type="TransportError"}}class K extends d{constructor(e){super(),this.writable=!1,P(this,e),this.opts=e,this.query=e.query,this.socket=e.socket,this.supportsBinary=!e.forceBase64}onError(e,t,s){return super.emitReserved("error",new ze(e,t,s)),this}open(){return this.readyState="opening",this.doOpen(),this}close(){return(this.readyState==="opening"||this.readyState==="open")&&(this.doClose(),this.onClose()),this}send(e){this.readyState==="open"&&this.write(e)}onOpen(){this.readyState="open",this.writable=!0,super.emitReserved("open")}onData(e){const t=H(e,this.socket.binaryType);this.onPacket(t)}onPacket(e){super.emitReserved("packet",e)}onClose(e){this.readyState="closed",super.emitReserved("close",e)}pause(e){}createUri(e,t={}){return e+"://"+this._hostname()+this._port()+this.opts.path+this._query(t)}_hostname(){const e=this.opts.hostname;return e.indexOf(":")===-1?e:"["+e+"]"}_port(){return this.opts.port&&(this.opts.secure&&Number(this.opts.port)!==443||!this.opts.secure&&Number(this.opts.port)!==80)?":"+this.opts.port:""}_query(e){const t=Ue(e);return t.length?"?"+t:""}}class Ve extends K{constructor(){super(...arguments),this._polling=!1}get name(){return"polling"}doOpen(){this._poll()}pause(e){this.readyState="pausing";const t=()=>{this.readyState="paused",e()};if(this._polling||!this.writable){let s=0;this._polling&&(s++,this.once("pollComplete",function(){--s||t()})),this.writable||(s++,this.once("drain",function(){--s||t()}))}else t()}_poll(){this._polling=!0,this.doPoll(),this.emitReserved("poll")}onData(e){const t=s=>{if(this.readyState==="opening"&&s.type==="open"&&this.onOpen(),s.type==="close")return this.onClose({description:"transport closed by the server"}),!1;this.onPacket(s)};Be(e,this.socket.binaryType).forEach(t),this.readyState!=="closed"&&(this._polling=!1,this.emitReserved("pollComplete"),this.readyState==="open"&&this._poll())}doClose(){const e=()=>{this.write([{type:"close"}])};this.readyState==="open"?e():this.once("open",e)}write(e){this.writable=!1,Ae(e,t=>{this.doWrite(t,()=>{this.writable=!0,this.emitReserved("drain")})})}uri(){const e=this.opts.secure?"https":"http",t=this.query||{};return this.opts.timestampRequests!==!1&&(t[this.opts.timestampParam]=ue()),!this.supportsBinary&&!t.sid&&(t.b64=1),this.createUri(e,t)}}let le=!1;try{le=typeof XMLHttpRequest<"u"&&"withCredentials"in new XMLHttpRequest}catch{}const We=le;function Ye(){}class He extends Ve{constructor(e){if(super(e),typeof location<"u"){const t=location.protocol==="https:";let s=location.port;s||(s=t?"443":"80"),this.xd=typeof location<"u"&&e.hostname!==location.hostname||s!==e.port}}doWrite(e,t){const s=this.request({method:"POST",data:e});s.on("success",t),s.on("error",(n,i)=>{this.onError("xhr post error",n,i)})}doPoll(){const e=this.request();e.on("data",this.onData.bind(this)),e.on("error",(t,s)=>{this.onError("xhr poll error",t,s)}),this.pollXhr=e}}class b extends d{constructor(e,t,s){super(),this.createRequest=e,P(this,s),this._opts=s,this._method=s.method||"GET",this._uri=t,this._data=s.data!==void 0?s.data:null,this._create()}_create(){var e;const t=he(this._opts,"agent","pfx","key","passphrase","cert","ca","ciphers","rejectUnauthorized","autoUnref");t.xdomain=!!this._opts.xd;const s=this._xhr=this.createRequest(t);try{s.open(this._method,this._uri,!0);try{if(this._opts.extraHeaders){s.setDisableHeaderCheck&&s.setDisableHeaderCheck(!0);for(let n in this._opts.extraHeaders)this._opts.extraHeaders.hasOwnProperty(n)&&s.setRequestHeader(n,this._opts.extraHeaders[n])}}catch{}if(this._method==="POST")try{s.setRequestHeader("Content-type","text/plain;charset=UTF-8")}catch{}try{s.setRequestHeader("Accept","*/*")}catch{}(e=this._opts.cookieJar)===null||e===void 0||e.addCookies(s),"withCredentials"in s&&(s.withCredentials=this._opts.withCredentials),this._opts.requestTimeout&&(s.timeout=this._opts.requestTimeout),s.onreadystatechange=()=>{var n;s.readyState===3&&((n=this._opts.cookieJar)===null||n===void 0||n.parseCookies(s.getResponseHeader("set-cookie"))),s.readyState===4&&(s.status===200||s.status===1223?this._onLoad():this.setTimeoutFn(()=>{this._onError(typeof s.status=="number"?s.status:0)},0))},s.send(this._data)}catch(n){this.setTimeoutFn(()=>{this._onError(n)},0);return}typeof document<"u"&&(this._index=b.requestsCount++,b.requests[this._index]=this)}_onError(e){this.emitReserved("error",e,this._xhr),this._cleanup(!0)}_cleanup(e){if(!(typeof this._xhr>"u"||this._xhr===null)){if(this._xhr.onreadystatechange=Ye,e)try{this._xhr.abort()}catch{}typeof document<"u"&&delete b.requests[this._index],this._xhr=null}}_onLoad(){const e=this._xhr.responseText;e!==null&&(this.emitReserved("data",e),this.emitReserved("success"),this._cleanup())}abort(){this._cleanup()}}b.requestsCount=0;b.requests={};if(typeof document<"u"){if(typeof attachEvent=="function")attachEvent("onunload",te);else if(typeof addEventListener=="function"){const r="onpagehide"in g?"pagehide":"unload";addEventListener(r,te,!1)}}function te(){for(let r in b.requests)b.requests.hasOwnProperty(r)&&b.requests[r].abort()}const Ke=function(){const r=pe({xdomain:!1});return r&&r.responseType!==null}();class Xe extends He{constructor(e){super(e);const t=e&&e.forceBase64;this.supportsBinary=Ke&&!t}request(e={}){return Object.assign(e,{xd:this.xd},this.opts),new b(pe,this.uri(),e)}}function pe(r){const e=r.xdomain;try{if(typeof XMLHttpRequest<"u"&&(!e||We))return new XMLHttpRequest}catch{}if(!e)try{return new g[["Active"].concat("Object").join("X")]("Microsoft.XMLHTTP")}catch{}}const de=typeof navigator<"u"&&typeof navigator.product=="string"&&navigator.product.toLowerCase()==="reactnative";class $e extends K{get name(){return"websocket"}doOpen(){const e=this.uri(),t=this.opts.protocols,s=de?{}:he(this.opts,"agent","perMessageDeflate","pfx","key","passphrase","cert","ca","ciphers","rejectUnauthorized","localAddress","protocolVersion","origin","maxPayload","family","checkServerIdentity");this.opts.extraHeaders&&(s.headers=this.opts.extraHeaders);try{this.ws=this.createSocket(e,t,s)}catch(n){return this.emitReserved("error",n)}this.ws.binaryType=this.socket.binaryType,this.addEventListeners()}addEventListeners(){this.ws.onopen=()=>{this.opts.autoUnref&&this.ws._socket.unref(),this.onOpen()},this.ws.onclose=e=>this.onClose({description:"websocket connection closed",context:e}),this.ws.onmessage=e=>this.onData(e.data),this.ws.onerror=e=>this.onError("websocket error",e)}write(e){this.writable=!1;for(let t=0;t<e.length;t++){const s=e[t],n=t===e.length-1;Y(s,this.supportsBinary,i=>{try{this.doWrite(s,i)}catch{}n&&q(()=>{this.writable=!0,this.emitReserved("drain")},this.setTimeoutFn)})}}doClose(){typeof this.ws<"u"&&(this.ws.onerror=()=>{},this.ws.close(),this.ws=null)}uri(){const e=this.opts.secure?"wss":"ws",t=this.query||{};return this.opts.timestampRequests&&(t[this.opts.timestampParam]=ue()),this.supportsBinary||(t.b64=1),this.createUri(e,t)}}const I=g.WebSocket||g.MozWebSocket;class Ge extends $e{createSocket(e,t,s){return de?new I(e,t,s):t?new I(e,t):new I(e)}doWrite(e,t){this.ws.send(t)}}class Je extends K{get name(){return"webtransport"}doOpen(){try{this._transport=new WebTransport(this.createUri("https"),this.opts.transportOptions[this.name])}catch(e){return this.emitReserved("error",e)}this._transport.closed.then(()=>{this.onClose()}).catch(e=>{this.onError("webtransport error",e)}),this._transport.ready.then(()=>{this._transport.createBidirectionalStream().then(e=>{const t=Re(Number.MAX_SAFE_INTEGER,this.socket.binaryType),s=e.readable.pipeThrough(t).getReader(),n=Oe();n.readable.pipeTo(e.writable),this._writer=n.writable.getWriter();const i=()=>{s.read().then(({done:a,value:f})=>{a||(this.onPacket(f),i())}).catch(a=>{})};i();const o={type:"open"};this.query.sid&&(o.data=`{"sid":"${this.query.sid}"}`),this._writer.write(o).then(()=>this.onOpen())})})}write(e){this.writable=!1;for(let t=0;t<e.length;t++){const s=e[t],n=t===e.length-1;this._writer.write(s).then(()=>{n&&q(()=>{this.writable=!0,this.emitReserved("drain")},this.setTimeoutFn)})}}doClose(){var e;(e=this._transport)===null||e===void 0||e.close()}}const Qe={websocket:Ge,webtransport:Je,polling:Xe},Ze=/^(?:(?![^:@\/?#]+:[^:@\/]*@)(http|https|ws|wss):\/\/)?((?:(([^:@\/?#]*)(?::([^:@\/?#]*))?)?@)?((?:[a-f0-9]{0,4}:){2,7}[a-f0-9]{0,4}|[^:\/?#]*)(?::(\d*))?)(((\/(?:[^?#](?![^?#\/]*\.[^?#\/.]+(?:[?#]|$)))*\/?)?([^?#\/]*))(?:\?([^#]*))?(?:#(.*))?)/,je=["source","protocol","authority","userInfo","user","password","host","port","relative","path","directory","file","query","anchor"];function U(r){if(r.length>8e3)throw"URI too long";const e=r,t=r.indexOf("["),s=r.indexOf("]");t!=-1&&s!=-1&&(r=r.substring(0,t)+r.substring(t,s).replace(/:/g,";")+r.substring(s,r.length));let n=Ze.exec(r||""),i={},o=14;for(;o--;)i[je[o]]=n[o]||"";return t!=-1&&s!=-1&&(i.source=e,i.host=i.host.substring(1,i.host.length-1).replace(/;/g,":"),i.authority=i.authority.replace("[","").replace("]","").replace(/;/g,":"),i.ipv6uri=!0),i.pathNames=et(i,i.path),i.queryKey=tt(i,i.query),i}function et(r,e){const t=/\/{2,9}/g,s=e.replace(t,"/").split("/");return(e.slice(0,1)=="/"||e.length===0)&&s.splice(0,1),e.slice(-1)=="/"&&s.splice(s.length-1,1),s}function tt(r,e){const t={};return e.replace(/(?:^|&)([^&=]*)=?([^&]*)/g,function(s,n,i){n&&(t[n]=i)}),t}const F=typeof addEventListener=="function"&&typeof removeEventListener=="function",O=[];F&&addEventListener("offline",()=>{O.forEach(r=>r())},!1);class w extends d{constructor(e,t){if(super(),this.binaryType=qe,this.writeBuffer=[],this._prevBufferLen=0,this._pingInterval=-1,this._pingTimeout=-1,this._maxPayload=-1,this._pingTimeoutTime=1/0,e&&typeof e=="object"&&(t=e,e=null),e){const s=U(e);t.hostname=s.host,t.secure=s.protocol==="https"||s.protocol==="wss",t.port=s.port,s.query&&(t.query=s.query)}else t.host&&(t.hostname=U(t.host).host);P(this,t),this.secure=t.secure!=null?t.secure:typeof location<"u"&&location.protocol==="https:",t.hostname&&!t.port&&(t.port=this.secure?"443":"80"),this.hostname=t.hostname||(typeof location<"u"?location.hostname:"localhost"),this.port=t.port||(typeof location<"u"&&location.port?location.port:this.secure?"443":"80"),this.transports=[],this._transportsByName={},t.transports.forEach(s=>{const n=s.prototype.name;this.transports.push(n),this._transportsByName[n]=s}),this.opts=Object.assign({path:"/engine.io",agent:!1,withCredentials:!1,upgrade:!0,timestampParam:"t",rememberUpgrade:!1,addTrailingSlash:!0,rejectUnauthorized:!0,perMessageDeflate:{threshold:1024},transportOptions:{},closeOnBeforeunload:!1},t),this.opts.path=this.opts.path.replace(/\/$/,"")+(this.opts.addTrailingSlash?"/":""),typeof this.opts.query=="string"&&(this.opts.query=Fe(this.opts.query)),F&&(this.opts.closeOnBeforeunload&&(this._beforeunloadEventListener=()=>{this.transport&&(this.transport.removeAllListeners(),this.transport.close())},addEventListener("beforeunload",this._beforeunloadEventListener,!1)),this.hostname!=="localhost"&&(this._offlineEventListener=()=>{this._onClose("transport close",{description:"network connection lost"})},O.push(this._offlineEventListener))),this.opts.withCredentials&&(this._cookieJar=void 0),this._open()}createTransport(e){const t=Object.assign({},this.opts.query);t.EIO=fe,t.transport=e,this.id&&(t.sid=this.id);const s=Object.assign({},this.opts,{query:t,socket:this,hostname:this.hostname,secure:this.secure,port:this.port},this.opts.transportOptions[e]);return new this._transportsByName[e](s)}_open(){if(this.transports.length===0){this.setTimeoutFn(()=>{this.emitReserved("error","No transports available")},0);return}const e=this.opts.rememberUpgrade&&w.priorWebsocketSuccess&&this.transports.indexOf("websocket")!==-1?"websocket":this.transports[0];this.readyState="opening";const t=this.createTransport(e);t.open(),this.setTransport(t)}setTransport(e){this.transport&&this.transport.removeAllListeners(),this.transport=e,e.on("drain",this._onDrain.bind(this)).on("packet",this._onPacket.bind(this)).on("error",this._onError.bind(this)).on("close",t=>this._onClose("transport close",t))}onOpen(){this.readyState="open",w.priorWebsocketSuccess=this.transport.name==="websocket",this.emitReserved("open"),this.flush()}_onPacket(e){if(this.readyState==="opening"||this.readyState==="open"||this.readyState==="closing")switch(this.emitReserved("packet",e),this.emitReserved("heartbeat"),e.type){case"open":this.onHandshake(JSON.parse(e.data));break;case"ping":this._sendPacket("pong"),this.emitReserved("ping"),this.emitReserved("pong"),this._resetPingTimeout();break;case"error":const t=new Error("server error");t.code=e.data,this._onError(t);break;case"message":this.emitReserved("data",e.data),this.emitReserved("message",e.data);break}}onHandshake(e){this.emitReserved("handshake",e),this.id=e.sid,this.transport.query.sid=e.sid,this._pingInterval=e.pingInterval,this._pingTimeout=e.pingTimeout,this._maxPayload=e.maxPayload,this.onOpen(),this.readyState!=="closed"&&this._resetPingTimeout()}_resetPingTimeout(){this.clearTimeoutFn(this._pingTimeoutTimer);const e=this._pingInterval+this._pingTimeout;this._pingTimeoutTime=Date.now()+e,this._pingTimeoutTimer=this.setTimeoutFn(()=>{this._onClose("ping timeout")},e),this.opts.autoUnref&&this._pingTimeoutTimer.unref()}_onDrain(){this.writeBuffer.splice(0,this._prevBufferLen),this._prevBufferLen=0,this.writeBuffer.length===0?this.emitReserved("drain"):this.flush()}flush(){if(this.readyState!=="closed"&&this.transport.writable&&!this.upgrading&&this.writeBuffer.length){const e=this._getWritablePackets();this.transport.send(e),this._prevBufferLen=e.length,this.emitReserved("flush")}}_getWritablePackets(){if(!(this._maxPayload&&this.transport.name==="polling"&&this.writeBuffer.length>1))return this.writeBuffer;let t=1;for(let s=0;s<this.writeBuffer.length;s++){const n=this.writeBuffer[s].data;if(n&&(t+=Ie(n)),s>0&&t>this._maxPayload)return this.writeBuffer.slice(0,s);t+=2}return this.writeBuffer}_hasPingExpired(){if(!this._pingTimeoutTime)return!0;const e=Date.now()>this._pingTimeoutTime;return e&&(this._pingTimeoutTime=0,q(()=>{this._onClose("ping timeout")},this.setTimeoutFn)),e}write(e,t,s){return this._sendPacket("message",e,t,s),this}send(e,t,s){return this._sendPacket("message",e,t,s),this}_sendPacket(e,t,s,n){if(typeof t=="function"&&(n=t,t=void 0),typeof s=="function"&&(n=s,s=null),this.readyState==="closing"||this.readyState==="closed")return;s=s||{},s.compress=s.compress!==!1;const i={type:e,data:t,options:s};this.emitReserved("packetCreate",i),this.writeBuffer.push(i),n&&this.once("flush",n),this.flush()}close(){const e=()=>{this._onClose("forced close"),this.transport.close()},t=()=>{this.off("upgrade",t),this.off("upgradeError",t),e()},s=()=>{this.once("upgrade",t),this.once("upgradeError",t)};return(this.readyState==="opening"||this.readyState==="open")&&(this.readyState="closing",this.writeBuffer.length?this.once("drain",()=>{this.upgrading?s():e()}):this.upgrading?s():e()),this}_onError(e){if(w.priorWebsocketSuccess=!1,this.opts.tryAllTransports&&this.transports.length>1&&this.readyState==="opening")return this.transports.shift(),this._open();this.emitReserved("error",e),this._onClose("transport error",e)}_onClose(e,t){if(this.readyState==="opening"||this.readyState==="open"||this.readyState==="closing"){if(this.clearTimeoutFn(this._pingTimeoutTimer),this.transport.removeAllListeners("close"),this.transport.close(),this.transport.removeAllListeners(),F&&(this._beforeunloadEventListener&&removeEventListener("beforeunload",this._beforeunloadEventListener,!1),this._offlineEventListener)){const s=O.indexOf(this._offlineEventListener);s!==-1&&O.splice(s,1)}this.readyState="closed",this.id=null,this.emitReserved("close",e,t),this.writeBuffer=[],this._prevBufferLen=0}}}w.protocol=fe;class st extends w{constructor(){super(...arguments),this._upgrades=[]}onOpen(){if(super.onOpen(),this.readyState==="open"&&this.opts.upgrade)for(let e=0;e<this._upgrades.length;e++)this._probe(this._upgrades[e])}_probe(e){let t=this.createTransport(e),s=!1;w.priorWebsocketSuccess=!1;const n=()=>{s||(t.send([{type:"ping",data:"probe"}]),t.once("packet",u=>{if(!s)if(u.type==="pong"&&u.data==="probe"){if(this.upgrading=!0,this.emitReserved("upgrading",t),!t)return;w.priorWebsocketSuccess=t.name==="websocket",this.transport.pause(()=>{s||this.readyState!=="closed"&&(c(),this.setTransport(t),t.send([{type:"upgrade"}]),this.emitReserved("upgrade",t),t=null,this.upgrading=!1,this.flush())})}else{const m=new Error("probe error");m.transport=t.name,this.emitReserved("upgradeError",m)}}))};function i(){s||(s=!0,c(),t.close(),t=null)}const o=u=>{const m=new Error("probe error: "+u);m.transport=t.name,i(),this.emitReserved("upgradeError",m)};function a(){o("transport closed")}function f(){o("socket closed")}function l(u){t&&u.name!==t.name&&i()}const c=()=>{t.removeListener("open",n),t.removeListener("error",o),t.removeListener("close",a),this.off("close",f),this.off("upgrading",l)};t.once("open",n),t.once("error",o),t.once("close",a),this.once("close",f),this.once("upgrading",l),this._upgrades.indexOf("webtransport")!==-1&&e!=="webtransport"?this.setTimeoutFn(()=>{s||t.open()},200):t.open()}onHandshake(e){this._upgrades=this._filterUpgrades(e.upgrades),super.onHandshake(e)}_filterUpgrades(e){const t=[];for(let s=0;s<e.length;s++)~this.transports.indexOf(e[s])&&t.push(e[s]);return t}}let rt=class extends st{constructor(e,t={}){const s=typeof e=="object"?e:t;(!s.transports||s.transports&&typeof s.transports[0]=="string")&&(s.transports=(s.transports||["polling","websocket","webtransport"]).map(n=>Qe[n]).filter(n=>!!n)),super(e,s)}};function nt(r,e="",t){let s=r;t=t||typeof location<"u"&&location,r==null&&(r=t.protocol+"//"+t.host),typeof r=="string"&&(r.charAt(0)==="/"&&(r.charAt(1)==="/"?r=t.protocol+r:r=t.host+r),/^(https?|wss?):\/\//.test(r)||(typeof t<"u"?r=t.protocol+"//"+r:r="https://"+r),s=U(r)),s.port||(/^(http|ws)$/.test(s.protocol)?s.port="80":/^(http|ws)s$/.test(s.protocol)&&(s.port="443")),s.path=s.path||"/";const i=s.host.indexOf(":")!==-1?"["+s.host+"]":s.host;return s.id=s.protocol+"://"+i+":"+s.port+e,s.href=s.protocol+"://"+i+(t&&t.port===s.port?"":":"+s.port),s}const it=typeof ArrayBuffer=="function",ot=r=>typeof ArrayBuffer.isView=="function"?ArrayBuffer.isView(r):r.buffer instanceof ArrayBuffer,me=Object.prototype.toString,at=typeof Blob=="function"||typeof Blob<"u"&&me.call(Blob)==="[object BlobConstructor]",ct=typeof File=="function"||typeof File<"u"&&me.call(File)==="[object FileConstructor]";function X(r){return it&&(r instanceof ArrayBuffer||ot(r))||at&&r instanceof Blob||ct&&r instanceof File}function R(r,e){if(!r||typeof r!="object")return!1;if(Array.isArray(r)){for(let t=0,s=r.length;t<s;t++)if(R(r[t]))return!0;return!1}if(X(r))return!0;if(r.toJSON&&typeof r.toJSON=="function"&&arguments.length===1)return R(r.toJSON(),!0);for(const t in r)if(Object.prototype.hasOwnProperty.call(r,t)&&R(r[t]))return!0;return!1}function ft(r){const e=[],t=r.data,s=r;return s.data=z(t,e),s.attachments=e.length,{packet:s,buffers:e}}function z(r,e){if(!r)return r;if(X(r)){const t={_placeholder:!0,num:e.length};return e.push(r),t}else if(Array.isArray(r)){const t=new Array(r.length);for(let s=0;s<r.length;s++)t[s]=z(r[s],e);return t}else if(typeof r=="object"&&!(r instanceof Date)){const t={};for(const s in r)Object.prototype.hasOwnProperty.call(r,s)&&(t[s]=z(r[s],e));return t}return r}function ht(r,e){return r.data=V(r.data,e),delete r.attachments,r}function V(r,e){if(!r)return r;if(r&&r._placeholder===!0){if(typeof r.num=="number"&&r.num>=0&&r.num<e.length)return e[r.num];throw new Error("illegal attachments")}else if(Array.isArray(r))for(let t=0;t<r.length;t++)r[t]=V(r[t],e);else if(typeof r=="object")for(const t in r)Object.prototype.hasOwnProperty.call(r,t)&&(r[t]=V(r[t],e));return r}const ut=["connect","connect_error","disconnect","disconnecting","newListener","removeListener"];var h;(function(r){r[r.CONNECT=0]="CONNECT",r[r.DISCONNECT=1]="DISCONNECT",r[r.EVENT=2]="EVENT",r[r.ACK=3]="ACK",r[r.CONNECT_ERROR=4]="CONNECT_ERROR",r[r.BINARY_EVENT=5]="BINARY_EVENT",r[r.BINARY_ACK=6]="BINARY_ACK"})(h||(h={}));class lt{constructor(e){this.replacer=e}encode(e){return(e.type===h.EVENT||e.type===h.ACK)&&R(e)?this.encodeAsBinary({type:e.type===h.EVENT?h.BINARY_EVENT:h.BINARY_ACK,nsp:e.nsp,data:e.data,id:e.id}):[this.encodeAsString(e)]}encodeAsString(e){let t=""+e.type;return(e.type===h.BINARY_EVENT||e.type===h.BINARY_ACK)&&(t+=e.attachments+"-"),e.nsp&&e.nsp!=="/"&&(t+=e.nsp+","),e.id!=null&&(t+=e.id),e.data!=null&&(t+=JSON.stringify(e.data,this.replacer)),t}encodeAsBinary(e){const t=ft(e),s=this.encodeAsString(t.packet),n=t.buffers;return n.unshift(s),n}}class $ extends d{constructor(e){super(),this.reviver=e}add(e){let t;if(typeof e=="string"){if(this.reconstructor)throw new Error("got plaintext data when reconstructing a packet");t=this.decodeString(e);const s=t.type===h.BINARY_EVENT;s||t.type===h.BINARY_ACK?(t.type=s?h.EVENT:h.ACK,this.reconstructor=new pt(t),t.attachments===0&&super.emitReserved("decoded",t)):super.emitReserved("decoded",t)}else if(X(e)||e.base64)if(this.reconstructor)t=this.reconstructor.takeBinaryData(e),t&&(this.reconstructor=null,super.emitReserved("decoded",t));else throw new Error("got binary data when not reconstructing a packet");else throw new Error("Unknown type: "+e)}decodeString(e){let t=0;const s={type:Number(e.charAt(0))};if(h[s.type]===void 0)throw new Error("unknown packet type "+s.type);if(s.type===h.BINARY_EVENT||s.type===h.BINARY_ACK){const i=t+1;for(;e.charAt(++t)!=="-"&&t!=e.length;);const o=e.substring(i,t);if(o!=Number(o)||e.charAt(t)!=="-")throw new Error("Illegal attachments");s.attachments=Number(o)}if(e.charAt(t+1)==="/"){const i=t+1;for(;++t&&!(e.charAt(t)===","||t===e.length););s.nsp=e.substring(i,t)}else s.nsp="/";const n=e.charAt(t+1);if(n!==""&&Number(n)==n){const i=t+1;for(;++t;){const o=e.charAt(t);if(o==null||Number(o)!=o){--t;break}if(t===e.length)break}s.id=Number(e.substring(i,t+1))}if(e.charAt(++t)){const i=this.tryParse(e.substr(t));if($.isPayloadValid(s.type,i))s.data=i;else throw new Error("invalid payload")}return s}tryParse(e){try{return JSON.parse(e,this.reviver)}catch{return!1}}static isPayloadValid(e,t){switch(e){case h.CONNECT:return se(t);case h.DISCONNECT:return t===void 0;case h.CONNECT_ERROR:return typeof t=="string"||se(t);case h.EVENT:case h.BINARY_EVENT:return Array.isArray(t)&&(typeof t[0]=="number"||typeof t[0]=="string"&&ut.indexOf(t[0])===-1);case h.ACK:case h.BINARY_ACK:return Array.isArray(t)}}destroy(){this.reconstructor&&(this.reconstructor.finishedReconstruction(),this.reconstructor=null)}}class pt{constructor(e){this.packet=e,this.buffers=[],this.reconPack=e}takeBinaryData(e){if(this.buffers.push(e),this.buffers.length===this.reconPack.attachments){const t=ht(this.reconPack,this.buffers);return this.finishedReconstruction(),t}return null}finishedReconstruction(){this.reconPack=null,this.buffers=[]}}function se(r){return Object.prototype.toString.call(r)==="[object Object]"}const dt=Object.freeze(Object.defineProperty({__proto__:null,Decoder:$,Encoder:lt,get PacketType(){return h}},Symbol.toStringTag,{value:"Module"}));function v(r,e,t){return r.on(e,t),function(){r.off(e,t)}}const mt=Object.freeze({connect:1,connect_error:1,disconnect:1,disconnecting:1,newListener:1,removeListener:1});class ye extends d{constructor(e,t,s){super(),this.connected=!1,this.recovered=!1,this.receiveBuffer=[],this.sendBuffer=[],this._queue=[],this._queueSeq=0,this.ids=0,this.acks={},this.flags={},this.io=e,this.nsp=t,s&&s.auth&&(this.auth=s.auth),this._opts=Object.assign({},s),this.io._autoConnect&&this.open()}get disconnected(){return!this.connected}subEvents(){if(this.subs)return;const e=this.io;this.subs=[v(e,"open",this.onopen.bind(this)),v(e,"packet",this.onpacket.bind(this)),v(e,"error",this.onerror.bind(this)),v(e,"close",this.onclose.bind(this))]}get active(){return!!this.subs}connect(){return this.connected?this:(this.subEvents(),this.io._reconnecting||this.io.open(),this.io._readyState==="open"&&this.onopen(),this)}open(){return this.connect()}send(...e){return e.unshift("message"),this.emit.apply(this,e),this}emit(e,...t){var s,n,i;if(mt.hasOwnProperty(e))throw new Error('"'+e.toString()+'" is a reserved event name');if(t.unshift(e),this._opts.retries&&!this.flags.fromQueue&&!this.flags.volatile)return this._addToQueue(t),this;const o={type:h.EVENT,data:t};if(o.options={},o.options.compress=this.flags.compress!==!1,typeof t[t.length-1]=="function"){const c=this.ids++,u=t.pop();this._registerAckCallback(c,u),o.id=c}const a=(n=(s=this.io.engine)===null||s===void 0?void 0:s.transport)===null||n===void 0?void 0:n.writable,f=this.connected&&!(!((i=this.io.engine)===null||i===void 0)&&i._hasPingExpired());return this.flags.volatile&&!a||(f?(this.notifyOutgoingListeners(o),this.packet(o)):this.sendBuffer.push(o)),this.flags={},this}_registerAckCallback(e,t){var s;const n=(s=this.flags.timeout)!==null&&s!==void 0?s:this._opts.ackTimeout;if(n===void 0){this.acks[e]=t;return}const i=this.io.setTimeoutFn(()=>{delete this.acks[e];for(let a=0;a<this.sendBuffer.length;a++)this.sendBuffer[a].id===e&&this.sendBuffer.splice(a,1);t.call(this,new Error("operation has timed out"))},n),o=(...a)=>{this.io.clearTimeoutFn(i),t.apply(this,a)};o.withError=!0,this.acks[e]=o}emitWithAck(e,...t){return new Promise((s,n)=>{const i=(o,a)=>o?n(o):s(a);i.withError=!0,t.push(i),this.emit(e,...t)})}_addToQueue(e){let t;typeof e[e.length-1]=="function"&&(t=e.pop());const s={id:this._queueSeq++,tryCount:0,pending:!1,args:e,flags:Object.assign({fromQueue:!0},this.flags)};e.push((n,...i)=>(this._queue[0],n!==null?s.tryCount>this._opts.retries&&(this._queue.shift(),t&&t(n)):(this._queue.shift(),t&&t(null,...i)),s.pending=!1,this._drainQueue())),this._queue.push(s),this._drainQueue()}_drainQueue(e=!1){if(!this.connected||this._queue.length===0)return;const t=this._queue[0];t.pending&&!e||(t.pending=!0,t.tryCount++,this.flags=t.flags,this.emit.apply(this,t.args))}packet(e){e.nsp=this.nsp,this.io._packet(e)}onopen(){typeof this.auth=="function"?this.auth(e=>{this._sendConnectPacket(e)}):this._sendConnectPacket(this.auth)}_sendConnectPacket(e){this.packet({type:h.CONNECT,data:this._pid?Object.assign({pid:this._pid,offset:this._lastOffset},e):e})}onerror(e){this.connected||this.emitReserved("connect_error",e)}onclose(e,t){this.connected=!1,delete this.id,this.emitReserved("disconnect",e,t),this._clearAcks()}_clearAcks(){Object.keys(this.acks).forEach(e=>{if(!this.sendBuffer.some(s=>String(s.id)===e)){const s=this.acks[e];delete this.acks[e],s.withError&&s.call(this,new Error("socket has been disconnected"))}})}onpacket(e){if(e.nsp===this.nsp)switch(e.type){case h.CONNECT:e.data&&e.data.sid?this.onconnect(e.data.sid,e.data.pid):this.emitReserved("connect_error",new Error("It seems you are trying to reach a Socket.IO server in v2.x with a v3.x client, but they are not compatible (more information here: https://socket.io/docs/v3/migrating-from-2-x-to-3-0/)"));break;case h.EVENT:case h.BINARY_EVENT:this.onevent(e);break;case h.ACK:case h.BINARY_ACK:this.onack(e);break;case h.DISCONNECT:this.ondisconnect();break;case h.CONNECT_ERROR:this.destroy();const s=new Error(e.data.message);s.data=e.data.data,this.emitReserved("connect_error",s);break}}onevent(e){const t=e.data||[];e.id!=null&&t.push(this.ack(e.id)),this.connected?this.emitEvent(t):this.receiveBuffer.push(Object.freeze(t))}emitEvent(e){if(this._anyListeners&&this._anyListeners.length){const t=this._anyListeners.slice();for(const s of t)s.apply(this,e)}super.emit.apply(this,e),this._pid&&e.length&&typeof e[e.length-1]=="string"&&(this._lastOffset=e[e.length-1])}ack(e){const t=this;let s=!1;return function(...n){s||(s=!0,t.packet({type:h.ACK,id:e,data:n}))}}onack(e){const t=this.acks[e.id];typeof t=="function"&&(delete this.acks[e.id],t.withError&&e.data.unshift(null),t.apply(this,e.data))}onconnect(e,t){this.id=e,this.recovered=t&&this._pid===t,this._pid=t,this.connected=!0,this.emitBuffered(),this._drainQueue(!0),this.emitReserved("connect")}emitBuffered(){this.receiveBuffer.forEach(e=>this.emitEvent(e)),this.receiveBuffer=[],this.sendBuffer.forEach(e=>{this.notifyOutgoingListeners(e),this.packet(e)}),this.sendBuffer=[]}ondisconnect(){this.destroy(),this.onclose("io server disconnect")}destroy(){this.subs&&(this.subs.forEach(e=>e()),this.subs=void 0),this.io._destroy(this)}disconnect(){return this.connected&&this.packet({type:h.DISCONNECT}),this.destroy(),this.connected&&this.onclose("io client disconnect"),this}close(){return this.disconnect()}compress(e){return this.flags.compress=e,this}get volatile(){return this.flags.volatile=!0,this}timeout(e){return this.flags.timeout=e,this}onAny(e){return this._anyListeners=this._anyListeners||[],this._anyListeners.push(e),this}prependAny(e){return this._anyListeners=this._anyListeners||[],this._anyListeners.unshift(e),this}offAny(e){if(!this._anyListeners)return this;if(e){const t=this._anyListeners;for(let s=0;s<t.length;s++)if(e===t[s])return t.splice(s,1),this}else this._anyListeners=[];return this}listenersAny(){return this._anyListeners||[]}onAnyOutgoing(e){return this._anyOutgoingListeners=this._anyOutgoingListeners||[],this._anyOutgoingListeners.push(e),this}prependAnyOutgoing(e){return this._anyOutgoingListeners=this._anyOutgoingListeners||[],this._anyOutgoingListeners.unshift(e),this}offAnyOutgoing(e){if(!this._anyOutgoingListeners)return this;if(e){const t=this._anyOutgoingListeners;for(let s=0;s<t.length;s++)if(e===t[s])return t.splice(s,1),this}else this._anyOutgoingListeners=[];return this}listenersAnyOutgoing(){return this._anyOutgoingListeners||[]}notifyOutgoingListeners(e){if(this._anyOutgoingListeners&&this._anyOutgoingListeners.length){const t=this._anyOutgoingListeners.slice();for(const s of t)s.apply(this,e.data)}}}function S(r){r=r||{},this.ms=r.min||100,this.max=r.max||1e4,this.factor=r.factor||2,this.jitter=r.jitter>0&&r.jitter<=1?r.jitter:0,this.attempts=0}S.prototype.duration=function(){var r=this.ms*Math.pow(this.factor,this.attempts++);if(this.jitter){var e=Math.random(),t=Math.floor(e*this.jitter*r);r=Math.floor(e*10)&1?r+t:r-t}return Math.min(r,this.max)|0};S.prototype.reset=function(){this.attempts=0};S.prototype.setMin=function(r){this.ms=r};S.prototype.setMax=function(r){this.max=r};S.prototype.setJitter=function(r){this.jitter=r};class W extends d{constructor(e,t){var s;super(),this.nsps={},this.subs=[],e&&typeof e=="object"&&(t=e,e=void 0),t=t||{},t.path=t.path||"/socket.io",this.opts=t,P(this,t),this.reconnection(t.reconnection!==!1),this.reconnectionAttempts(t.reconnectionAttempts||1/0),this.reconnectionDelay(t.reconnectionDelay||1e3),this.reconnectionDelayMax(t.reconnectionDelayMax||5e3),this.randomizationFactor((s=t.randomizationFactor)!==null&&s!==void 0?s:.5),this.backoff=new S({min:this.reconnectionDelay(),max:this.reconnectionDelayMax(),jitter:this.randomizationFactor()}),this.timeout(t.timeout==null?2e4:t.timeout),this._readyState="closed",this.uri=e;const n=t.parser||dt;this.encoder=new n.Encoder,this.decoder=new n.Decoder,this._autoConnect=t.autoConnect!==!1,this._autoConnect&&this.open()}reconnection(e){return arguments.length?(this._reconnection=!!e,e||(this.skipReconnect=!0),this):this._reconnection}reconnectionAttempts(e){return e===void 0?this._reconnectionAttempts:(this._reconnectionAttempts=e,this)}reconnectionDelay(e){var t;return e===void 0?this._reconnectionDelay:(this._reconnectionDelay=e,(t=this.backoff)===null||t===void 0||t.setMin(e),this)}randomizationFactor(e){var t;return e===void 0?this._randomizationFactor:(this._randomizationFactor=e,(t=this.backoff)===null||t===void 0||t.setJitter(e),this)}reconnectionDelayMax(e){var t;return e===void 0?this._reconnectionDelayMax:(this._reconnectionDelayMax=e,(t=this.backoff)===null||t===void 0||t.setMax(e),this)}timeout(e){return arguments.length?(this._timeout=e,this):this._timeout}maybeReconnectOnOpen(){!this._reconnecting&&this._reconnection&&this.backoff.attempts===0&&this.reconnect()}open(e){if(~this._readyState.indexOf("open"))return this;this.engine=new rt(this.uri,this.opts);const t=this.engine,s=this;this._readyState="opening",this.skipReconnect=!1;const n=v(t,"open",function(){s.onopen(),e&&e()}),i=a=>{this.cleanup(),this._readyState="closed",this.emitReserved("error",a),e?e(a):this.maybeReconnectOnOpen()},o=v(t,"error",i);if(this._timeout!==!1){const a=this._timeout,f=this.setTimeoutFn(()=>{n(),i(new Error("timeout")),t.close()},a);this.opts.autoUnref&&f.unref(),this.subs.push(()=>{this.clearTimeoutFn(f)})}return this.subs.push(n),this.subs.push(o),this}connect(e){return this.open(e)}onopen(){this.cleanup(),this._readyState="open",this.emitReserved("open");const e=this.engine;this.subs.push(v(e,"ping",this.onping.bind(this)),v(e,"data",this.ondata.bind(this)),v(e,"error",this.onerror.bind(this)),v(e,"close",this.onclose.bind(this)),v(this.decoder,"decoded",this.ondecoded.bind(this)))}onping(){this.emitReserved("ping")}ondata(e){try{this.decoder.add(e)}catch(t){this.onclose("parse error",t)}}ondecoded(e){q(()=>{this.emitReserved("packet",e)},this.setTimeoutFn)}onerror(e){this.emitReserved("error",e)}socket(e,t){let s=this.nsps[e];return s?this._autoConnect&&!s.active&&s.connect():(s=new ye(this,e,t),this.nsps[e]=s),s}_destroy(e){const t=Object.keys(this.nsps);for(const s of t)if(this.nsps[s].active)return;this._close()}_packet(e){const t=this.encoder.encode(e);for(let s=0;s<t.length;s++)this.engine.write(t[s],e.options)}cleanup(){this.subs.forEach(e=>e()),this.subs.length=0,this.decoder.destroy()}_close(){this.skipReconnect=!0,this._reconnecting=!1,this.onclose("forced close")}disconnect(){return this._close()}onclose(e,t){var s;this.cleanup(),(s=this.engine)===null||s===void 0||s.close(),this.backoff.reset(),this._readyState="closed",this.emitReserved("close",e,t),this._reconnection&&!this.skipReconnect&&this.reconnect()}reconnect(){if(this._reconnecting||this.skipReconnect)return this;const e=this;if(this.backoff.attempts>=this._reconnectionAttempts)this.backoff.reset(),this.emitReserved("reconnect_failed"),this._reconnecting=!1;else{const t=this.backoff.duration();this._reconnecting=!0;const s=this.setTimeoutFn(()=>{e.skipReconnect||(this.emitReserved("reconnect_attempt",e.backoff.attempts),!e.skipReconnect&&e.open(n=>{n?(e._reconnecting=!1,e.reconnect(),this.emitReserved("reconnect_error",n)):e.onreconnect()}))},t);this.opts.autoUnref&&s.unref(),this.subs.push(()=>{this.clearTimeoutFn(s)})}}onreconnect(){const e=this.backoff.attempts;this._reconnecting=!1,this.backoff.reset(),this.emitReserved("reconnect",e)}}const E={};function L(r,e){typeof r=="object"&&(e=r,r=void 0),e=e||{};const t=nt(r,e.path||"/socket.io"),s=t.source,n=t.id,i=t.path,o=E[n]&&i in E[n].nsps,a=e.forceNew||e["force new connection"]||e.multiplex===!1||o;let f;return a?f=new W(s,e):(E[n]||(E[n]=new W(s,e)),f=E[n]),t.query&&!e.query&&(e.query=t.queryKey),f.socket(t.path,e)}Object.assign(L,{Manager:W,Socket:ye,io:L,connect:L});function ge(){return typeof window<"u"?window.location.origin:"http://127.0.0.1:5001"}function yt(r,e,t){const s=L(ge(),{path:"/socket.io",transports:["websocket","polling"]});s.on("connect",()=>{e==null||e()}),s.on("scene",n=>{r(n)}),s.on("connect_error",n=>{t==null||t(n)})}const gt={type:"wgsl-sdf",code:"fn map(p: vec3f) -> f32 { return sdSphere(p, 1.0); }"};function vt(r){return typeof r=="object"&&r!==null&&r.type==="wgsl-sdf"&&typeof r.code=="string"}function y(r){const e=document.getElementById("status");e&&(e.innerHTML=r)}function _t(r){return r.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}function re(r){const e=document.getElementById("prompt-bar"),t=document.getElementById("prompt-input"),s=document.getElementById("prompt-send");let n=!1;const i=ge();async function o(){const a=t.value.trim();if(!(!a||n)){n=!0,s.disabled=!0,e.classList.add("loading"),t.placeholder="Generating…";try{const f=await fetch(`${i}/chat`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt:a})}),l=await f.text();let c={};try{c=l?JSON.parse(l):{}}catch{t.placeholder=`Server error (${f.status})`,y(`<span class="err">chat: bad JSON (${f.status})</span>`),setTimeout(()=>{t.placeholder="Describe a shape…"},4e3);return}if(f.ok&&c.ok&&typeof c.code=="string"&&c.code.trim()){t.value="",t.placeholder="Describe a shape…";const u={type:"wgsl-sdf",code:c.code};r?(r.setWgslScene(u),y(`<span class="ok">scene</span> · wgsl (${c.code.length} chars)`)):y(`<span class="ok">scene ok</span> · wgsl (${c.code.length} chars) — <span class="err">no WebGPU preview</span>`)}else{const u=c.error||`Request failed (${f.status})`;t.placeholder=u.slice(0,80),y(`<span class="err">${_t(u)}</span>`),setTimeout(()=>{t.placeholder="Describe a shape…"},6e3)}}catch{t.placeholder=`Can’t reach ${i} — run: python3 server.py`,y(`<span class="err">no server at ${i}</span>`),setTimeout(()=>{t.placeholder="Describe a shape…"},6e3)}finally{n=!1,s.disabled=!1,e.classList.remove("loading"),t.focus()}}}s.addEventListener("click",o),t.addEventListener("keydown",a=>{a.key==="Enter"&&(a.preventDefault(),o())})}async function bt(){const r=document.getElementById("canvas");if(!r){y('<span class="err">canvas not found</span>');return}const e=new ke;if(y("initialising WebGPU…"),!await e.init(r)){y('<span class="err">WebGPU not supported</span> · prompt bar still talks to server'),re(null);return}let s;const n=()=>{const o=Math.min(window.devicePixelRatio??1,2);r.width=Math.floor(r.clientWidth*o),r.height=Math.floor(r.clientHeight*o),e.handleResize()};n(),window.addEventListener("resize",()=>{clearTimeout(s),s=setTimeout(n,50)}),e.setWgslScene(gt),y('<span class="ok">gpu ready</span> · connecting…'),re(e),yt(o=>{var a;if(vt(o))e.setWgslScene(o),y(`<span class="ok">live</span> · wgsl (${o.code.length} chars)`);else{e.setScene(o);const f=((a=o.instrs)==null?void 0:a.length)??0;y(`<span class="ok">live</span> · ${f} ops (flatir)`)}},()=>y('<span class="ok">connected</span> · waiting for scene…'),o=>y(`<span class="err">socket: ${o.message}</span>`));const i=()=>{e.render(),requestAnimationFrame(i)};requestAnimationFrame(i)}bt();
