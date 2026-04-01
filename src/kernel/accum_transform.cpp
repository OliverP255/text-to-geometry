#include "kernel/accum_transform.h"
#include <cmath>

namespace kernel {

namespace {

struct Quat { float x, y, z, w; };

Quat quatMul(Quat a, Quat b) {
  return {
    a.w*b.x + a.x*b.w + a.y*b.z - a.z*b.y,
    a.w*b.y - a.x*b.z + a.y*b.w + a.z*b.x,
    a.w*b.z + a.x*b.y - a.y*b.x + a.z*b.w,
    a.w*b.w - a.x*b.x - a.y*b.y - a.z*b.z,
  };
}

Vec3 quatRotate(Quat q, Vec3 v) {
  // q * v * q^-1  (for unit quaternion, q^-1 = conjugate)
  float tx = 2.f * (q.y*v.z - q.z*v.y);
  float ty = 2.f * (q.z*v.x - q.x*v.z);
  float tz = 2.f * (q.x*v.y - q.y*v.x);
  return {
    v.x + q.w*tx + (q.y*tz - q.z*ty),
    v.y + q.w*ty + (q.z*tx - q.x*tz),
    v.z + q.w*tz + (q.x*ty - q.y*tx),
  };
}

}  // namespace

bool AccumTransform::operator==(const AccumTransform& other) const {
  return translate.x == other.translate.x && translate.y == other.translate.y &&
         translate.z == other.translate.z && scale.x == other.scale.x &&
         scale.y == other.scale.y && scale.z == other.scale.z &&
         qx == other.qx && qy == other.qy && qz == other.qz && qw == other.qw;
}

AccumTransform compose(const AccumTransform& accum, TransformOp op,
                       const void* payload) {
  AccumTransform out = accum;
  if (op == TransformOp::Translate) {
    const auto* p = static_cast<const TranslatePayload*>(payload);
    out.translate.x += p->t.x;
    out.translate.y += p->t.y;
    out.translate.z += p->t.z;
  } else if (op == TransformOp::Scale) {
    const auto* p = static_cast<const ScalePayload*>(payload);
    out.translate.x *= p->s.x;
    out.translate.y *= p->s.y;
    out.translate.z *= p->s.z;
    out.scale.x *= p->s.x;
    out.scale.y *= p->s.y;
    out.scale.z *= p->s.z;
  } else if (op == TransformOp::Rotate) {
    const auto* p = static_cast<const RotatePayload*>(payload);
    Quat qNew{p->x, p->y, p->z, p->w};
    Quat qOld{accum.qx, accum.qy, accum.qz, accum.qw};
    Quat qResult = quatMul(qNew, qOld);
    out.qx = qResult.x;
    out.qy = qResult.y;
    out.qz = qResult.z;
    out.qw = qResult.w;
    Vec3 rotatedT = quatRotate(qNew, accum.translate);
    out.translate = rotatedT;
  }
  return out;
}

size_t AccumTransformKeyHash::operator()(
    const std::pair<uint32_t, AccumTransform>& key) const {
  size_t h = std::hash<uint32_t>{}(key.first);
  auto mix = [](size_t x) {
    x ^= x >> 16;
    x *= 0x85ebca6b;
    x ^= x >> 13;
    x *= 0xc2b2ae35;
    x ^= x >> 16;
    return x;
  };
  const AccumTransform& a = key.second;
  h = mix(h + std::hash<float>{}(a.translate.x));
  h = mix(h + std::hash<float>{}(a.translate.y));
  h = mix(h + std::hash<float>{}(a.translate.z));
  h = mix(h + std::hash<float>{}(a.scale.x));
  h = mix(h + std::hash<float>{}(a.scale.y));
  h = mix(h + std::hash<float>{}(a.scale.z));
  h = mix(h + std::hash<float>{}(a.qx));
  h = mix(h + std::hash<float>{}(a.qy));
  h = mix(h + std::hash<float>{}(a.qz));
  h = mix(h + std::hash<float>{}(a.qw));
  return h;
}

}  // namespace kernel
