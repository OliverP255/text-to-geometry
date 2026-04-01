#pragma once

#include <cstdint>
#include <vector>

namespace kernel {

struct FlatTransform {
  float tx = 0, ty = 0, tz = 0;
  float sx = 1, sy = 1, sz = 1;
  float qx = 0, qy = 0, qz = 0, qw = 1;
};

struct FlatSphere {
  float r = 1.0f;
};

struct FlatBox {
  float hx = 1, hy = 1, hz = 1;
};

struct FlatCylinder {
  float r = 1.0f;
  float h = 1.0f;
};

enum class FlatOp : uint8_t {
  EvalSphere,
  EvalBox,
  CsgUnion,
  CsgIntersect,
  CsgSubtract,
  EvalCylinder,
  CsgSmoothUnion,
};

struct FlatInstr {
  uint32_t op = 0;  // FlatOp as uint32_t (fixed-width)
  uint32_t arg0 = 0;
  uint32_t arg1 = 0;
  uint32_t constIdx = 0;
};

struct FlatIR {
  std::vector<FlatInstr> instrs;
  std::vector<FlatTransform> transforms;
  std::vector<FlatSphere> spheres;
  std::vector<FlatBox> boxes;
  std::vector<FlatCylinder> cylinders;
  std::vector<float> smoothKs;
  uint32_t rootTemp = 0;
};

}  // namespace kernel
