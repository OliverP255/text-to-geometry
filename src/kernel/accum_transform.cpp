#include "kernel/accum_transform.h"

namespace kernel {

bool AccumTransform::operator==(const AccumTransform& other) const {
  return translate.x == other.translate.x && translate.y == other.translate.y &&
         translate.z == other.translate.z && scale.x == other.scale.x &&
         scale.y == other.scale.y && scale.z == other.scale.z;
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
  return h;
}

}  // namespace kernel
