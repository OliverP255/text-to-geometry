#pragma once

#include "kernel/handle.h"
#include <cstdint>

namespace kernel {

struct Vec3 {
  float x = 0, y = 0, z = 0;
  float& operator[](int i) { return (&x)[i]; }
  float operator[](int i) const { return (&x)[i]; }
};

// Node category for type dispatch
enum class NodeCategory : uint8_t {
  Shape,
  Transform,
  Float,
};

// Shape opcodes
enum class ShapeOp : uint8_t {
  Sphere,
  Box,
  Plane,
  Union,
  Intersect,
  Subtract,
  ApplyTransform,
};

// Transform opcodes
enum class TransformOp : uint8_t {
  Translate,
  Scale,
};

// Float opcodes (minimal; for future scalar params)
enum class FloatOp : uint8_t {
  Literal,
};

// Payload structs (POD)
struct SpherePayload {
  float r = 1.0f;
};

struct BoxPayload {
  Vec3 halfExtents{1, 1, 1};
};

struct PlanePayload {
  Vec3 normal{0, 1, 0};
  float d = 0;
};

struct TranslatePayload {
  Vec3 t{0, 0, 0};
};

struct ScalePayload {
  Vec3 s{1, 1, 1};
};

// Compact node header for arena storage. Children stored inline.
struct NodeHeader {
  NodeCategory category = NodeCategory::Shape;
  uint8_t opcode = 0;
  uint8_t arity = 0;
  uint8_t pad = 0;
  uint32_t in0 = 0xFFFFFFFFu;   // first child; 0xFFFFFFFF if unused
  uint32_t in1 = 0xFFFFFFFFu;   // second child; 0xFFFFFFFF if unused
  uint32_t payloadOffset = 0;   // byte offset into payloads (0xFFFFFFFF = none)
};

}  // namespace kernel
