#include "kernel/builder.h"
#include "kernel/intern.h"
#include <cstring>

namespace kernel {

uint32_t Builder::hashNode(NodeCategory cat, uint8_t opcode, uint32_t child0,
                           uint32_t child1, const void* payload,
                           size_t payloadSize) const {
  return intern::hash(cat, opcode, child0, child1, payload, payloadSize);
}

uint32_t Builder::allocNode(NodeCategory cat, uint8_t opcode, uint32_t child0,
                            uint32_t child1, const void* payload,
                            size_t payloadSize) {
  constexpr uint32_t kInvalidPayload = 0xFFFFFFFFu;
  constexpr uint32_t kUnusedChild = 0xFFFFFFFFu;
  NodeHeader h;
  h.category = cat;
  h.opcode = opcode;
  h.arity = (child0 != 0 ? 1 : 0) + (child1 != 0 ? 1 : 0);
  h.in0 = child0 != 0 ? child0 : kUnusedChild;
  h.in1 = child1 != 0 ? child1 : kUnusedChild;
  h.payloadOffset =
      payloadSize > 0 ? static_cast<uint32_t>(payloads_.size()) : kInvalidPayload;

  if (payload && payloadSize > 0) {
    const uint8_t* src = static_cast<const uint8_t*>(payload);
    payloads_.insert(payloads_.end(), src, src + payloadSize);
  }

  headers_.push_back(h);
  return static_cast<uint32_t>(headers_.size());
}

uint32_t Builder::findExisting(NodeCategory cat, uint8_t opcode,
                               uint32_t child0, uint32_t child1,
                               const void* payload, size_t payloadSize) {
  uint32_t key = hashNode(cat, opcode, child0, child1, payload, payloadSize);
  auto it = internMap_.find(key);
  if (it == internMap_.end()) return 0;

  uint32_t id = it->second;
  if (id == 0 || id > headers_.size()) return 0;
  const NodeHeader& existing = headers_[id - 1];
  if (existing.category != cat || existing.opcode != opcode) return 0;
  if (!intern::structuralEqual(existing, child0, child1, payload, payloadSize,
                               payloads_.data(), payloads_.size())) {
    return 0;
  }
  return id;
}

TransformH Builder::internTransform(TransformOp op, const void* payload,
                                   size_t payloadSize) {
  uint8_t opcode = static_cast<uint8_t>(op);
  uint32_t id = findExisting(NodeCategory::Transform, opcode, 0, 0, payload,
                            payloadSize);
  if (id == 0) {
    id = allocNode(NodeCategory::Transform, opcode, 0, 0, payload,
                   payloadSize);
    internMap_[hashNode(NodeCategory::Transform, opcode, 0, 0, payload,
                       payloadSize)] = id;
  }
  TransformH h;
  h.id = id;
  return h;
}

ShapeH Builder::internShape(ShapeOp op, uint32_t child0, uint32_t child1,
                           const void* payload, size_t payloadSize) {
  // Canonicalize: sort children for commutative ops
  if (op == ShapeOp::Union || op == ShapeOp::Intersect) {
    if (child0 > child1) std::swap(child0, child1);
  }

  uint8_t opcode = static_cast<uint8_t>(op);
  uint32_t id = findExisting(NodeCategory::Shape, opcode, child0, child1,
                            payload, payloadSize);
  if (id == 0) {
    id = allocNode(NodeCategory::Shape, opcode, child0, child1, payload,
                   payloadSize);
    internMap_[hashNode(NodeCategory::Shape, opcode, child0, child1, payload,
                       payloadSize)] = id;
  }
  ShapeH h;
  h.id = id;
  return h;
}

ShapeH Builder::sphere(float r) {
  if (frozen_) return ShapeH{};
  SpherePayload p;
  p.r = r;
  return internShape(ShapeOp::Sphere, 0, 0, &p, sizeof(p));
}

ShapeH Builder::box(Vec3 halfExtents) {
  if (frozen_) return ShapeH{};
  BoxPayload p;
  p.halfExtents = halfExtents;
  return internShape(ShapeOp::Box, 0, 0, &p, sizeof(p));
}

ShapeH Builder::plane(Vec3 normal, float d) {
  if (frozen_) return ShapeH{};
  PlanePayload p;
  p.normal = normal;
  p.d = d;
  return internShape(ShapeOp::Plane, 0, 0, &p, sizeof(p));
}

TransformH Builder::translate(Vec3 t) {
  if (frozen_) return TransformH{};
  TranslatePayload p;
  p.t = t;
  return internTransform(TransformOp::Translate, &p, sizeof(p));
}

TransformH Builder::scale(Vec3 s) {
  if (frozen_) return TransformH{};
  ScalePayload p;
  p.s = s;
  return internTransform(TransformOp::Scale, &p, sizeof(p));
}

ShapeH Builder::apply(TransformH t, ShapeH s) {
  if (frozen_ || !t.valid() || !s.valid()) return ShapeH{};
  return internShape(ShapeOp::ApplyTransform, t.id, s.id, nullptr, 0);
}

ShapeH Builder::unite(ShapeH a, ShapeH b) {
  if (frozen_ || !a.valid() || !b.valid()) return ShapeH{};
  return internShape(ShapeOp::Union, a.id, b.id, nullptr, 0);
}

ShapeH Builder::intersect(ShapeH a, ShapeH b) {
  if (frozen_ || !a.valid() || !b.valid()) return ShapeH{};
  return internShape(ShapeOp::Intersect, a.id, b.id, nullptr, 0);
}

ShapeH Builder::subtract(ShapeH a, ShapeH b) {
  if (frozen_ || !a.valid() || !b.valid()) return ShapeH{};
  return internShape(ShapeOp::Subtract, a.id, b.id, nullptr, 0);
}

ShapeH Builder::uniteBalanced(const ShapeH* shapes, size_t lo, size_t hi) {
  if (lo == hi) return shapes[lo];
  size_t mid = lo + (hi - lo) / 2;
  return unite(uniteBalanced(shapes, lo, mid), uniteBalanced(shapes, mid + 1, hi));
}

ShapeH Builder::intersectBalanced(const ShapeH* shapes, size_t lo, size_t hi) {
  if (lo == hi) return shapes[lo];
  size_t mid = lo + (hi - lo) / 2;
  return intersect(intersectBalanced(shapes, lo, mid),
                   intersectBalanced(shapes, mid + 1, hi));
}

ShapeH Builder::unite(const std::vector<ShapeH>& shapes) {
  if (frozen_) return ShapeH{};
  std::vector<ShapeH> valid;
  valid.reserve(shapes.size());
  for (ShapeH s : shapes) {
    if (s.valid()) valid.push_back(s);
  }
  if (valid.empty()) return ShapeH{};
  if (valid.size() == 1) return valid[0];
  return uniteBalanced(valid.data(), 0, valid.size() - 1);
}

ShapeH Builder::intersect(const std::vector<ShapeH>& shapes) {
  if (frozen_) return ShapeH{};
  std::vector<ShapeH> valid;
  valid.reserve(shapes.size());
  for (ShapeH s : shapes) {
    if (s.valid()) valid.push_back(s);
  }
  if (valid.empty()) return ShapeH{};
  if (valid.size() == 1) return valid[0];
  return intersectBalanced(valid.data(), 0, valid.size() - 1);
}

void Builder::freeze(ShapeH root, FrozenDAG& out) {
  if (frozen_) return;
  frozen_ = true;

  out.rootId = root.id;
  out.headers =
      headers_.empty()
          ? nullptr
          : reinterpret_cast<const uint8_t*>(headers_.data());
  out.headerCount = headers_.size();
  out.payloads = payloads_.empty() ? nullptr : payloads_.data();
  out.payloadBytes = payloads_.size();
}

}  // namespace kernel

