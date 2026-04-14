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
fn opRepLinear(p: vec3f, spacing: f32, count: f32) -> vec3f {
  let halfN = (count - 1.0) * 0.5;
  let cellX = clamp(round(p.x / spacing), -halfN, halfN);
  return vec3f(p.x - spacing * cellX, p.y, p.z);
}
fn opOnion(d: f32, t: f32) -> f32 { return abs(d) - t; }
fn opRound(d: f32, r: f32) -> f32 { return d - r; }
fn opU3(a: f32, b: f32, c: f32) -> f32 { return min(a, min(b, c)); }
fn opU4(a: f32, b: f32, c: f32, d: f32) -> f32 { return min(min(a, b), min(c, d)); }
fn sdCylinderX(p: vec3f, h: f32, r: f32) -> f32 {
  let d = abs(vec2f(length(p.yz), p.x)) - vec2f(r, h);
  return min(max(d.x, d.y), 0.0) + length(max(d, vec2f(0.0)));
}
fn sdCylinderZ(p: vec3f, h: f32, r: f32) -> f32 {
  let d = abs(vec2f(length(p.xy), p.z)) - vec2f(r, h);
  return min(max(d.x, d.y), 0.0) + length(max(d, vec2f(0.0)));
}
fn sdHemisphere(p: vec3f, r: f32) -> f32 {
  return max(length(p) - r, -p.y);
}
fn opTwist(p: vec3f, k: f32) -> vec3f {
  let c = cos(k * p.y);
  let s = sin(k * p.y);
  return vec3f(c * p.x - s * p.z, p.y, s * p.x + c * p.z);
}
fn opCheapBend(p: vec3f, k: f32) -> vec3f {
  let c = cos(k * p.x);
  let s = sin(k * p.x);
  return vec3f(c * p.x - s * p.y, s * p.x + c * p.y, p.z);
}
// IQ exact cone: c = vec2f(sin(α), cos(α)) for apex half-angle α; h = height (tip at y=h, base in y=0 plane).
fn sdCone(p: vec3f, c: vec2f, h: f32) -> f32 {
  let cy = select(c.y, sign(c.y) * 1e-7, abs(c.y) < 1e-7);
  let q = h * vec2f(c.x / cy, -1.0);
  let w = vec2f(length(p.xz), p.y);
  let a = w - q * clamp(dot(w, q) / dot(q, q), 0.0, 1.0);
  let qx = select(q.x, sign(q.x) * 1e-7, abs(q.x) < 1e-7);
  let b = w - q * vec2f(clamp(w.x / qx, 0.0, 1.0), 1.0);
  let k = sign(q.y);
  let d = min(dot(a, a), dot(b, b));
  let s = max(k * (w.x * q.y - w.y * q.x), k * (w.y - q.y));
  return sqrt(d) * sign(s);
}