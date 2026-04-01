#pragma once

#include "kernel/handle.h"
#include "kernel/node.h"
#include <cstddef>
#include <cstdint>
#include <unordered_map>
#include <vector>

namespace kernel {

// Read-only view of frozen DAG for lowering. Children stored inline in headers.
struct FrozenDAG {
  uint32_t rootId = 0;  // root Shape node ID for lowering
  const uint8_t* headers = nullptr;
  size_t headerCount = 0;
  const uint8_t* payloads = nullptr;
  size_t payloadBytes = 0;
};

class Builder {
 public:
  Builder() = default;
  ~Builder() = default;

  Builder(const Builder&) = delete;
  Builder& operator=(const Builder&) = delete;

  // Primitives
  ShapeH sphere(float r);
  ShapeH box(Vec3 halfExtents);
  ShapeH cylinder(float r, float h);

  // Transforms
  TransformH translate(Vec3 t);
  TransformH scale(Vec3 s);
  TransformH rotate(float x, float y, float z, float w);

  // Composition
  ShapeH apply(TransformH t, ShapeH s);
  ShapeH unite(ShapeH a, ShapeH b);
  ShapeH unite(const std::vector<ShapeH>& shapes);
  ShapeH intersect(ShapeH a, ShapeH b);
  ShapeH intersect(const std::vector<ShapeH>& shapes);
  ShapeH subtract(ShapeH a, ShapeH b);
  ShapeH smoothUnite(ShapeH a, ShapeH b, float k);

  // Freeze: seal builder, return root handles and read-only DAG view.
  // After freeze(), no further construction is allowed.
  // roots: output array of root ShapeH to expose (caller provides storage)
  void freeze(ShapeH root, FrozenDAG& out);

  // Check if builder is frozen
  bool isFrozen() const { return frozen_; }

 private:
  ShapeH internShape(ShapeOp op, uint32_t child0, uint32_t child1,
                     const void* payload, size_t payloadSize);
  TransformH internTransform(TransformOp op, const void* payload,
                            size_t payloadSize);

  uint32_t allocNode(NodeCategory cat, uint8_t opcode, uint32_t child0,
                     uint32_t child1, const void* payload, size_t payloadSize);
  uint32_t findExisting(NodeCategory cat, uint8_t opcode, uint32_t child0,
                        uint32_t child1, const void* payload,
                        size_t payloadSize);

  uint32_t hashNode(NodeCategory cat, uint8_t opcode, uint32_t child0,
                    uint32_t child1, const void* payload,
                    size_t payloadSize) const;

  ShapeH uniteBalanced(const ShapeH* shapes, size_t lo, size_t hi);
  ShapeH intersectBalanced(const ShapeH* shapes, size_t lo, size_t hi);

  bool frozen_ = false;
  std::vector<NodeHeader> headers_;
  std::vector<uint8_t> payloads_;
  std::unordered_map<uint32_t, uint32_t> internMap_;  // hash -> node id
};

}  // namespace kernel
