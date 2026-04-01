#pragma once

#include "kernel/node.h"
#include <cstdint>
#include <functional>
#include <utility>

namespace kernel {

// AccumTransform(t, s): world-to-local map
// Point: p_local = (p - t) / s  (component-wise)
// Distance: d_world = d_local * min(s)
// Identity: t=0, s=(1,1,1)
struct AccumTransform {
  Vec3 translate{0, 0, 0};
  Vec3 scale{1, 1, 1};
  float qx = 0, qy = 0, qz = 0, qw = 1;  // quaternion (identity)

  bool operator==(const AccumTransform& other) const;
};

AccumTransform compose(const AccumTransform& accum, TransformOp op,
                       const void* payload);

// Hash functor for (nodeId, AccumTransform) cache key.
// Hashes nodeId and all 6 floats; use with full struct as key for equality.
struct AccumTransformKeyHash {
  size_t operator()(const std::pair<uint32_t, AccumTransform>& key) const;
};

}  // namespace kernel
