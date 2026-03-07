#pragma once

#include <cstdint>
#include <vector>

namespace kernel {

struct DistTemp {
  uint32_t id = 0;
};

enum class FlatOp : uint8_t {
  EvalSphere,
  EvalBox,
  EvalPlane,
  CsgUnion,
  CsgIntersect,
  CsgSubtract,
};

struct FlatInstr {
  FlatOp op = FlatOp::EvalSphere;
  uint32_t arg0 = 0;   // transform_idx for EVAL_*; DistTemp for CSG
  uint32_t arg1 = 0;   // DistTemp for CSG; unused for EVAL_*
  uint32_t constIdx = 0;  // sphereIdx, boxIdx, or planeIdx for EVAL_*
};

struct FlatIR {
  std::vector<FlatInstr> instrs;
  std::vector<float> transforms;  // 6 floats per entry (tx,ty,tz,sx,sy,sz)
  std::vector<float> spheres;     // 1 float per entry (r)
  std::vector<float> boxes;       // 3 floats per entry (halfExtents)
  std::vector<float> planes;      // 4 floats per entry (normal + d)
  DistTemp rootTemp;
};

}  // namespace kernel
