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
    if (instr.op == static_cast<uint32_t>(FlatOp::EvalSphere)) {
      uint32_t ti = instr.arg0;
      float tx = 0, ty = 0, tz = 0, sx = 1, sy = 1, sz = 1;
      float qx = 0, qy = 0, qz = 0, qw = 1;
      if (ti < ir.transforms.size()) {
        const FlatTransform& t = ir.transforms[ti];
        tx = t.tx; ty = t.ty; tz = t.tz;
        sx = t.sx; sy = t.sy; sz = t.sz;
        qx = t.qx; qy = t.qy; qz = t.qz; qw = t.qw;
      }
      Vec3 pT{p.x - tx, p.y - ty, p.z - tz};
      Vec3 pR = eval_dag::quatRotateInverse(qx, qy, qz, qw, pT);
      Vec3 pLocal;
      pLocal.x = pR.x / sx;
      pLocal.y = pR.y / sy;
      pLocal.z = pR.z / sz;
      float r =
          (instr.constIdx < ir.spheres.size()) ? ir.spheres[instr.constIdx].r
                                               : 1.0f;
      float dLocal = eval_dag::sdfSphere(pLocal, r);
      float scaleFactor = eval_dag::minScale({sx, sy, sz});
      temps.push_back(dLocal * scaleFactor);
    } else if (instr.op == static_cast<uint32_t>(FlatOp::EvalBox)) {
      uint32_t ti = instr.arg0;
      float tx = 0, ty = 0, tz = 0, sx = 1, sy = 1, sz = 1;
      float qx = 0, qy = 0, qz = 0, qw = 1;
      if (ti < ir.transforms.size()) {
        const FlatTransform& t = ir.transforms[ti];
        tx = t.tx; ty = t.ty; tz = t.tz;
        sx = t.sx; sy = t.sy; sz = t.sz;
        qx = t.qx; qy = t.qy; qz = t.qz; qw = t.qw;
      }
      Vec3 pT{p.x - tx, p.y - ty, p.z - tz};
      Vec3 pR = eval_dag::quatRotateInverse(qx, qy, qz, qw, pT);
      Vec3 pLocal;
      pLocal.x = pR.x / sx;
      pLocal.y = pR.y / sy;
      pLocal.z = pR.z / sz;
      Vec3 halfExtents{1, 1, 1};
      if (instr.constIdx < ir.boxes.size()) {
        halfExtents.x = ir.boxes[instr.constIdx].hx;
        halfExtents.y = ir.boxes[instr.constIdx].hy;
        halfExtents.z = ir.boxes[instr.constIdx].hz;
      }
      float dLocal = eval_dag::sdfBox(pLocal, halfExtents);
      float scaleFactor = eval_dag::minScale({sx, sy, sz});
      temps.push_back(dLocal * scaleFactor);
    } else if (instr.op == static_cast<uint32_t>(FlatOp::CsgUnion)) {
      float a = (instr.arg0 < temps.size()) ? temps[instr.arg0] : 1e10f;
      float b = (instr.arg1 < temps.size()) ? temps[instr.arg1] : 1e10f;
      temps.push_back(std::min(a, b));
    } else if (instr.op == static_cast<uint32_t>(FlatOp::CsgIntersect)) {
      float a = (instr.arg0 < temps.size()) ? temps[instr.arg0] : 1e10f;
      float b = (instr.arg1 < temps.size()) ? temps[instr.arg1] : 1e10f;
      temps.push_back(std::max(a, b));
    } else if (instr.op == static_cast<uint32_t>(FlatOp::CsgSubtract)) {
      float a = (instr.arg0 < temps.size()) ? temps[instr.arg0] : 1e10f;
      float b = (instr.arg1 < temps.size()) ? temps[instr.arg1] : 1e10f;
      temps.push_back(std::max(a, -b));
    } else if (instr.op == static_cast<uint32_t>(FlatOp::EvalCylinder)) {
      uint32_t ti = instr.arg0;
      float tx = 0, ty = 0, tz = 0, sx = 1, sy = 1, sz = 1;
      float qx = 0, qy = 0, qz = 0, qw = 1;
      if (ti < ir.transforms.size()) {
        const FlatTransform& t = ir.transforms[ti];
        tx = t.tx; ty = t.ty; tz = t.tz;
        sx = t.sx; sy = t.sy; sz = t.sz;
        qx = t.qx; qy = t.qy; qz = t.qz; qw = t.qw;
      }
      Vec3 pT{p.x - tx, p.y - ty, p.z - tz};
      Vec3 pR = eval_dag::quatRotateInverse(qx, qy, qz, qw, pT);
      Vec3 pLocal;
      pLocal.x = pR.x / sx;
      pLocal.y = pR.y / sy;
      pLocal.z = pR.z / sz;
      float r = 1.0f, h = 1.0f;
      if (instr.constIdx < ir.cylinders.size()) {
        r = ir.cylinders[instr.constIdx].r;
        h = ir.cylinders[instr.constIdx].h;
      }
      float dLocal = eval_dag::sdfCylinder(pLocal, r, h);
      float scaleFactor = eval_dag::minScale({sx, sy, sz});
      temps.push_back(dLocal * scaleFactor);
    } else if (instr.op == static_cast<uint32_t>(FlatOp::CsgSmoothUnion)) {
      float a = (instr.arg0 < temps.size()) ? temps[instr.arg0] : 1e10f;
      float b = (instr.arg1 < temps.size()) ? temps[instr.arg1] : 1e10f;
      float k = 0.1f;
      if (instr.constIdx < ir.smoothKs.size())
        k = ir.smoothKs[instr.constIdx];
      temps.push_back(eval_dag::sdfSmoothUnion(a, b, k));
    }
  }

  if (ir.rootTemp < temps.size())
    return temps[ir.rootTemp];
  return 1e10f;
}

inline float evalFlatIR(const kernel::FlatIR& ir, const kernel::Vec3& p) {
  if (ir.instrs.empty()) return 1e10f;
  return evalFlatIRImpl(ir, p);
}

}  // namespace eval_flat_ir
