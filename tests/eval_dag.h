#pragma once

#include "kernel/accum_transform.h"
#include "kernel/builder.h"
#include "kernel/node.h"
#include <cmath>

namespace eval_dag {

inline float sdfSphere(const kernel::Vec3& p, float r) {
  float d = std::sqrt(p.x * p.x + p.y * p.y + p.z * p.z);
  return d - r;
}

inline float sdfBox(const kernel::Vec3& p, const kernel::Vec3& halfExtents) {
  kernel::Vec3 q;
  q.x = std::abs(p.x) - halfExtents.x;
  q.y = std::abs(p.y) - halfExtents.y;
  q.z = std::abs(p.z) - halfExtents.z;
  float outside = std::sqrt(std::max(0.f, q.x) * std::max(0.f, q.x) +
                             std::max(0.f, q.y) * std::max(0.f, q.y) +
                             std::max(0.f, q.z) * std::max(0.f, q.z));
  float inside = std::min(std::max(std::max(q.x, q.y), q.z), 0.f);
  return outside + inside;
}

inline float sdfCylinder(const kernel::Vec3& p, float r, float h) {
  float dx = std::sqrt(p.x * p.x + p.z * p.z) - r;
  float dy = std::abs(p.y) - h;
  float outside = std::sqrt(std::max(0.f, dx) * std::max(0.f, dx) +
                             std::max(0.f, dy) * std::max(0.f, dy));
  float inside = std::min(std::max(dx, dy), 0.f);
  return outside + inside;
}

inline float sdfSmoothUnion(float a, float b, float k) {
  float h = std::max(std::min(0.5f + 0.5f * (b - a) / k, 1.0f), 0.0f);
  return b * (1.f - h) + a * h - k * h * (1.f - h);
}

inline float minScale(const kernel::Vec3& s) {
  return std::min(std::min(s.x, s.y), s.z);
}

inline kernel::Vec3 quatRotateInverse(float qx, float qy, float qz, float qw,
                                       const kernel::Vec3& v) {
  float cx = -qx, cy = -qy, cz = -qz;
  float tx = 2.f * (cy*v.z - cz*v.y);
  float ty = 2.f * (cz*v.x - cx*v.z);
  float tz = 2.f * (cx*v.y - cy*v.x);
  return {
    v.x + qw*tx + (cy*tz - cz*ty),
    v.y + qw*ty + (cz*tx - cx*tz),
    v.z + qw*tz + (cx*ty - cy*tx),
  };
}

namespace {

inline float evalShape(const kernel::FrozenDAG& dag, const kernel::Vec3& p,
                      uint32_t nodeId, const kernel::AccumTransform& accum);

inline float evalDAGNode(const kernel::FrozenDAG& dag, const kernel::Vec3& p,
                        uint32_t nodeId,
                        const kernel::AccumTransform& accum) {
  if (!dag.headers || dag.headerCount == 0 || nodeId == 0) return 1e10f;
  return evalShape(dag, p, nodeId, accum);
}

inline float evalShape(const kernel::FrozenDAG& dag, const kernel::Vec3& p,
                      uint32_t nodeId, const kernel::AccumTransform& accum) {
  using namespace kernel;
  if (nodeId == 0 || nodeId > dag.headerCount) return 1e10f;
  const NodeHeader* headers = reinterpret_cast<const NodeHeader*>(dag.headers);
  const NodeHeader& h = headers[nodeId - 1];
  const uint8_t* payloads = dag.payloads;

  if (h.category == NodeCategory::Shape) {
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Sphere)) {
      Vec3 pTranslated{p.x - accum.translate.x, p.y - accum.translate.y, p.z - accum.translate.z};
      Vec3 pRotated = quatRotateInverse(accum.qx, accum.qy, accum.qz, accum.qw, pTranslated);
      Vec3 pLocal;
      pLocal.x = pRotated.x / accum.scale.x;
      pLocal.y = pRotated.y / accum.scale.y;
      pLocal.z = pRotated.z / accum.scale.z;
      float r = 1.0f;
      if (h.payloadOffset != 0xFFFFFFFFu && payloads) {
        r = reinterpret_cast<const SpherePayload*>(payloads + h.payloadOffset)
                ->r;
      }
      float dLocal = sdfSphere(pLocal, r);
      return dLocal * minScale(accum.scale);
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Box)) {
      Vec3 pTranslated{p.x - accum.translate.x, p.y - accum.translate.y, p.z - accum.translate.z};
      Vec3 pRotated = quatRotateInverse(accum.qx, accum.qy, accum.qz, accum.qw, pTranslated);
      Vec3 pLocal;
      pLocal.x = pRotated.x / accum.scale.x;
      pLocal.y = pRotated.y / accum.scale.y;
      pLocal.z = pRotated.z / accum.scale.z;
      Vec3 halfExtents{1, 1, 1};
      if (h.payloadOffset != 0xFFFFFFFFu && payloads) {
        halfExtents =
            reinterpret_cast<const BoxPayload*>(payloads + h.payloadOffset)
                ->halfExtents;
      }
      float dLocal = sdfBox(pLocal, halfExtents);
      return dLocal * minScale(accum.scale);
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Cylinder)) {
      Vec3 pTranslated{p.x - accum.translate.x, p.y - accum.translate.y, p.z - accum.translate.z};
      Vec3 pRotated = quatRotateInverse(accum.qx, accum.qy, accum.qz, accum.qw, pTranslated);
      Vec3 pLocal;
      pLocal.x = pRotated.x / accum.scale.x;
      pLocal.y = pRotated.y / accum.scale.y;
      pLocal.z = pRotated.z / accum.scale.z;
      float r = 1.0f, halfH = 1.0f;
      if (h.payloadOffset != 0xFFFFFFFFu && payloads) {
        const auto* cp =
            reinterpret_cast<const CylinderPayload*>(payloads + h.payloadOffset);
        r = cp->r;
        halfH = cp->h;
      }
      float dLocal = sdfCylinder(pLocal, r, halfH);
      return dLocal * minScale(accum.scale);
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Union)) {
      uint32_t c0 = h.in0 != 0xFFFFFFFFu ? h.in0 : 0;
      uint32_t c1 = h.in1 != 0xFFFFFFFFu ? h.in1 : 0;
      float a = evalDAGNode(dag, p, c0, accum);
      float b = evalDAGNode(dag, p, c1, accum);
      return std::min(a, b);
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Intersect)) {
      uint32_t c0 = h.in0 != 0xFFFFFFFFu ? h.in0 : 0;
      uint32_t c1 = h.in1 != 0xFFFFFFFFu ? h.in1 : 0;
      float a = evalDAGNode(dag, p, c0, accum);
      float b = evalDAGNode(dag, p, c1, accum);
      return std::max(a, b);
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Subtract)) {
      uint32_t c0 = h.in0 != 0xFFFFFFFFu ? h.in0 : 0;
      uint32_t c1 = h.in1 != 0xFFFFFFFFu ? h.in1 : 0;
      float a = evalDAGNode(dag, p, c0, accum);
      float b = evalDAGNode(dag, p, c1, accum);
      return std::max(a, -b);
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::SmoothUnion)) {
      uint32_t c0 = h.in0 != 0xFFFFFFFFu ? h.in0 : 0;
      uint32_t c1 = h.in1 != 0xFFFFFFFFu ? h.in1 : 0;
      float a = evalDAGNode(dag, p, c0, accum);
      float b = evalDAGNode(dag, p, c1, accum);
      float k = 0.1f;
      if (h.payloadOffset != 0xFFFFFFFFu && payloads) {
        k = reinterpret_cast<const SmoothUnionPayload*>(payloads + h.payloadOffset)->k;
      }
      return sdfSmoothUnion(a, b, k);
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::ApplyTransform)) {
      uint32_t transformId = h.in0 != 0xFFFFFFFFu ? h.in0 : 0;
      uint32_t shapeId = h.in1 != 0xFFFFFFFFu ? h.in1 : 0;
      if (transformId == 0 || shapeId == 0) return 1e10f;

      const NodeHeader& th = headers[transformId - 1];
      if (th.payloadOffset == 0xFFFFFFFFu || !payloads)
        return evalDAGNode(dag, p, shapeId, accum);

      AccumTransform newAccum =
          compose(accum, static_cast<TransformOp>(th.opcode),
                  payloads + th.payloadOffset);
      return evalDAGNode(dag, p, shapeId, newAccum);
    }
  }
  return 1e10f;
}

}  // namespace

inline float evalDAG(const kernel::FrozenDAG& dag, const kernel::Vec3& p) {
  kernel::AccumTransform identity;
  return evalDAGNode(dag, p, dag.rootId, identity);
}

}  // namespace eval_dag
