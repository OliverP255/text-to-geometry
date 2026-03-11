#pragma once

#include "eval_dag.h"
#include "kernel/flat_ir.h"
#include "kernel/node.h"
#include <vector>

namespace eval_flat_ir {

inline float evalFlatIRImpl(const kernel::FlatIR& ir, const kernel::Vec3& p) {
  using namespace kernel;
  std::vector<float> temps;
  temps.reserve(ir.instrs.size() + 1);

  for (const FlatInstr& instr : ir.instrs) {
    if (instr.op == FlatOp::EvalSphere) {
      uint32_t ti = instr.arg0;
      float tx = 0, ty = 0, tz = 0, sx = 1, sy = 1, sz = 1;
      if (ti * 6 + 6 <= ir.transforms.size()) {
        tx = ir.transforms[ti * 6 + 0];
        ty = ir.transforms[ti * 6 + 1];
        tz = ir.transforms[ti * 6 + 2];
        sx = ir.transforms[ti * 6 + 3];
        sy = ir.transforms[ti * 6 + 4];
        sz = ir.transforms[ti * 6 + 5];
      }
      Vec3 pLocal;
      pLocal.x = (p.x - tx) / sx;
      pLocal.y = (p.y - ty) / sy;
      pLocal.z = (p.z - tz) / sz;
      float r =
          (instr.constIdx < ir.spheres.size()) ? ir.spheres[instr.constIdx]
                                               : 1.0f;
      float dLocal = eval_dag::sdfSphere(pLocal, r);
      float scaleFactor = eval_dag::minScale({sx, sy, sz});
      temps.push_back(dLocal * scaleFactor);
    } else if (instr.op == FlatOp::EvalBox) {
      uint32_t ti = instr.arg0;
      float tx = 0, ty = 0, tz = 0, sx = 1, sy = 1, sz = 1;
      if (ti * 6 + 6 <= ir.transforms.size()) {
        tx = ir.transforms[ti * 6 + 0];
        ty = ir.transforms[ti * 6 + 1];
        tz = ir.transforms[ti * 6 + 2];
        sx = ir.transforms[ti * 6 + 3];
        sy = ir.transforms[ti * 6 + 4];
        sz = ir.transforms[ti * 6 + 5];
      }
      Vec3 pLocal;
      pLocal.x = (p.x - tx) / sx;
      pLocal.y = (p.y - ty) / sy;
      pLocal.z = (p.z - tz) / sz;
      Vec3 halfExtents{1, 1, 1};
      if (instr.constIdx * 3 + 3 <= ir.boxes.size()) {
        halfExtents.x = ir.boxes[instr.constIdx * 3 + 0];
        halfExtents.y = ir.boxes[instr.constIdx * 3 + 1];
        halfExtents.z = ir.boxes[instr.constIdx * 3 + 2];
      }
      float dLocal = eval_dag::sdfBox(pLocal, halfExtents);
      float scaleFactor = eval_dag::minScale({sx, sy, sz});
      temps.push_back(dLocal * scaleFactor);
    } else if (instr.op == FlatOp::EvalPlane) {
      uint32_t ti = instr.arg0;
      float tx = 0, ty = 0, tz = 0, sx = 1, sy = 1, sz = 1;
      if (ti * 6 + 6 <= ir.transforms.size()) {
        tx = ir.transforms[ti * 6 + 0];
        ty = ir.transforms[ti * 6 + 1];
        tz = ir.transforms[ti * 6 + 2];
        sx = ir.transforms[ti * 6 + 3];
        sy = ir.transforms[ti * 6 + 4];
        sz = ir.transforms[ti * 6 + 5];
      }
      Vec3 pLocal;
      pLocal.x = (p.x - tx) / sx;
      pLocal.y = (p.y - ty) / sy;
      pLocal.z = (p.z - tz) / sz;
      Vec3 normal{0, 1, 0};
      float d = 0;
      if (instr.constIdx * 4 + 4 <= ir.planes.size()) {
        normal.x = ir.planes[instr.constIdx * 4 + 0];
        normal.y = ir.planes[instr.constIdx * 4 + 1];
        normal.z = ir.planes[instr.constIdx * 4 + 2];
        d = ir.planes[instr.constIdx * 4 + 3];
      }
      float dLocal = eval_dag::sdfPlane(pLocal, normal, d);
      float scaleFactor = eval_dag::minScale({sx, sy, sz});
      temps.push_back(dLocal * scaleFactor);
    } else if (instr.op == FlatOp::CsgUnion) {
      float a = (instr.arg0 < temps.size()) ? temps[instr.arg0] : 1e10f;
      float b = (instr.arg1 < temps.size()) ? temps[instr.arg1] : 1e10f;
      temps.push_back(std::min(a, b));
    } else if (instr.op == FlatOp::CsgIntersect) {
      float a = (instr.arg0 < temps.size()) ? temps[instr.arg0] : 1e10f;
      float b = (instr.arg1 < temps.size()) ? temps[instr.arg1] : 1e10f;
      temps.push_back(std::max(a, b));
    } else if (instr.op == FlatOp::CsgSubtract) {
      float a = (instr.arg0 < temps.size()) ? temps[instr.arg0] : 1e10f;
      float b = (instr.arg1 < temps.size()) ? temps[instr.arg1] : 1e10f;
      temps.push_back(std::max(a, -b));
    }
  }

  if (ir.rootTemp.id < temps.size())
    return temps[ir.rootTemp.id];
  return 1e10f;
}

inline float evalFlatIR(const kernel::FlatIR& ir, const kernel::Vec3& p) {
  if (ir.instrs.empty()) return 1e10f;
  return evalFlatIRImpl(ir, p);
}

}  // namespace eval_flat_ir
