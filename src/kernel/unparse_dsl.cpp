#include "kernel/unparse_dsl.h"
#include <cmath>
#include <cstdio>
#include <sstream>
#include <string>
#include <vector>

namespace kernel {

namespace {

constexpr float kEps = 1e-6f;

bool isRotationIdentity(float qx, float qy, float qz, float qw) {
  return std::abs(qx) < kEps && std::abs(qy) < kEps && std::abs(qz) < kEps &&
         std::abs(qw - 1.0f) < kEps;
}

bool isIdentityTransform(float tx, float ty, float tz, float sx, float sy, float sz,
                         float qx, float qy, float qz, float qw) {
  return std::abs(tx) < kEps && std::abs(ty) < kEps && std::abs(tz) < kEps &&
         std::abs(sx - 1.0f) < kEps && std::abs(sy - 1.0f) < kEps &&
         std::abs(sz - 1.0f) < kEps && isRotationIdentity(qx, qy, qz, qw);
}

bool isScaleOne(float sx, float sy, float sz) {
  return std::abs(sx - 1.0f) < kEps && std::abs(sy - 1.0f) < kEps &&
         std::abs(sz - 1.0f) < kEps;
}

bool isTranslateZero(float tx, float ty, float tz) {
  return std::abs(tx) < kEps && std::abs(ty) < kEps && std::abs(tz) < kEps;
}

std::string formatFloat(float v) {
  char buf[32];
  snprintf(buf, sizeof(buf), "%.6g", v);
  return std::string(buf);
}

}  // namespace

std::string unparseDSL(const FlatIR& ir) {
  if (ir.instrs.empty()) return "";

  std::ostringstream out;
  int tVarCount = 0;

  // Build transform var assignments and wrap strings for each transform index
  std::vector<std::string> transformWrap;
  size_t numTransforms = ir.transforms.size();
  transformWrap.resize(numTransforms);

  for (size_t ti = 1; ti < numTransforms; ++ti) {
    const FlatTransform& t = ir.transforms[ti];
    float tx = t.tx, ty = t.ty, tz = t.tz;
    float sx = t.sx, sy = t.sy, sz = t.sz;
    float qx = t.qx, qy = t.qy, qz = t.qz, qw = t.qw;

    if (isIdentityTransform(tx, ty, tz, sx, sy, sz, qx, qy, qz, qw)) {
      transformWrap[ti] = "";
      continue;
    }

    bool hasTranslate = !isTranslateZero(tx, ty, tz);
    bool hasScale = !isScaleOne(sx, sy, sz);
    bool hasRotate = !isRotationIdentity(qx, qy, qz, qw);

    // Build nested apply chain: apply(rotate, apply(scale, apply(translate, %s)))
    std::string wrap = "%s";

    if (hasTranslate) {
      out << "t" << tVarCount << "=translate(x=" << formatFloat(tx) << ",y="
          << formatFloat(ty) << ",z=" << formatFloat(tz) << ")\n";
      wrap = "apply(t" + std::to_string(tVarCount) + ", " + wrap + ")";
      ++tVarCount;
    }
    if (hasScale) {
      out << "t" << tVarCount << "=scale(x=" << formatFloat(sx) << ",y="
          << formatFloat(sy) << ",z=" << formatFloat(sz) << ")\n";
      wrap = "apply(t" + std::to_string(tVarCount) + ", " + wrap + ")";
      ++tVarCount;
    }
    if (hasRotate) {
      out << "t" << tVarCount << "=rotate(x=" << formatFloat(qx) << ",y="
          << formatFloat(qy) << ",z=" << formatFloat(qz) << ",w="
          << formatFloat(qw) << ")\n";
      wrap = "apply(t" + std::to_string(tVarCount) + ", " + wrap + ")";
      ++tVarCount;
    }

    transformWrap[ti] = wrap;
  }

  // resultTemp[i] = DSL temp index for result of instr i.
  // When Eval* has transform, we emit primitive first (extra temp), so result shifts.
  std::vector<size_t> resultTemp(ir.instrs.size());
  size_t nextTemp = 0;
  for (size_t i = 0; i < ir.instrs.size(); ++i) {
    const FlatInstr& instr = ir.instrs[i];
    bool hasTransform =
        (instr.op == static_cast<uint32_t>(FlatOp::EvalSphere) ||
         instr.op == static_cast<uint32_t>(FlatOp::EvalBox) ||
         instr.op == static_cast<uint32_t>(FlatOp::EvalCylinder)) &&
        instr.arg0 < transformWrap.size() && !transformWrap[instr.arg0].empty();
    if (hasTransform) {
      ++nextTemp;  // primitive temp
    }
    resultTemp[i] = nextTemp++;
  }

  // Build shape expressions (primitive string for Eval*, full expr for CSG)
  std::vector<std::string> primitiveExprs(ir.instrs.size());
  std::vector<std::string> shapeExprs(ir.instrs.size());

  for (size_t i = 0; i < ir.instrs.size(); ++i) {
    const FlatInstr& instr = ir.instrs[i];
    std::string prim;

    switch (static_cast<FlatOp>(instr.op)) {
      case FlatOp::EvalSphere: {
        if (instr.constIdx < ir.spheres.size()) {
          prim = "sphere(r=" + formatFloat(ir.spheres[instr.constIdx].r) + ")";
        } else {
          prim = "sphere(r=1)";
        }
        break;
      }
      case FlatOp::EvalBox: {
        if (instr.constIdx < ir.boxes.size()) {
          prim = "box(x=" + formatFloat(ir.boxes[instr.constIdx].hx) + ",y=" +
                 formatFloat(ir.boxes[instr.constIdx].hy) + ",z=" +
                 formatFloat(ir.boxes[instr.constIdx].hz) + ")";
        } else {
          prim = "box(x=1,y=1,z=1)";
        }
        break;
      }
      case FlatOp::EvalCylinder: {
        if (instr.constIdx < ir.cylinders.size()) {
          prim = "cylinder(r=" + formatFloat(ir.cylinders[instr.constIdx].r) +
                 ",h=" + formatFloat(ir.cylinders[instr.constIdx].h) + ")";
        } else {
          prim = "cylinder(r=1,h=1)";
        }
        break;
      }
      case FlatOp::CsgUnion: {
        if (instr.arg0 < resultTemp.size() && instr.arg1 < resultTemp.size()) {
          shapeExprs[i] = "union(s" + std::to_string(resultTemp[instr.arg0]) +
                         ",s" + std::to_string(resultTemp[instr.arg1]) + ")";
        }
        break;
      }
      case FlatOp::CsgIntersect: {
        if (instr.arg0 < resultTemp.size() && instr.arg1 < resultTemp.size()) {
          shapeExprs[i] =
              "intersect(s" + std::to_string(resultTemp[instr.arg0]) + ",s" +
              std::to_string(resultTemp[instr.arg1]) + ")";
        }
        break;
      }
      case FlatOp::CsgSubtract: {
        if (instr.arg0 < resultTemp.size() && instr.arg1 < resultTemp.size()) {
          shapeExprs[i] =
              "subtract(s" + std::to_string(resultTemp[instr.arg0]) + ",s" +
              std::to_string(resultTemp[instr.arg1]) + ")";
        }
        break;
      }
      case FlatOp::CsgSmoothUnion: {
        if (instr.arg0 < resultTemp.size() && instr.arg1 < resultTemp.size()) {
          std::string kStr = "0.1";
          if (instr.constIdx < ir.smoothKs.size())
            kStr = formatFloat(ir.smoothKs[instr.constIdx]);
          shapeExprs[i] =
              "smooth_union(s" + std::to_string(resultTemp[instr.arg0]) + ",s" +
              std::to_string(resultTemp[instr.arg1]) + ",k=" + kStr + ")";
        }
        break;
      }
      default:
        break;
    }

    if (instr.op == static_cast<uint32_t>(FlatOp::EvalSphere) ||
        instr.op == static_cast<uint32_t>(FlatOp::EvalBox) ||
        instr.op == static_cast<uint32_t>(FlatOp::EvalCylinder)) {
      primitiveExprs[i] = prim;
    }
  }

  // Emit shape assignments
  for (size_t i = 0; i < ir.instrs.size(); ++i) {
    const FlatInstr& instr = ir.instrs[i];
    bool hasTransform =
        (instr.op == static_cast<uint32_t>(FlatOp::EvalSphere) ||
         instr.op == static_cast<uint32_t>(FlatOp::EvalBox) ||
         instr.op == static_cast<uint32_t>(FlatOp::EvalCylinder)) &&
        instr.arg0 < transformWrap.size() && !transformWrap[instr.arg0].empty();

    if (instr.op == static_cast<uint32_t>(FlatOp::EvalSphere) ||
        instr.op == static_cast<uint32_t>(FlatOp::EvalBox) ||
        instr.op == static_cast<uint32_t>(FlatOp::EvalCylinder)) {
      if (hasTransform) {
        size_t primTemp = resultTemp[i] - 1;
        size_t resultIdx = resultTemp[i];
        out << "s" << primTemp << "=" << primitiveExprs[i] << "\n";
        const std::string& wrap = transformWrap[instr.arg0];
        size_t pos = wrap.find("%s");
        if (pos != std::string::npos) {
          std::string applyExpr =
              wrap.substr(0, pos) + "s" + std::to_string(primTemp) +
              wrap.substr(pos + 2);
          out << "s" << resultIdx << "=" << applyExpr << "\n";
        }
      } else {
        out << "s" << resultTemp[i] << "=" << primitiveExprs[i] << "\n";
      }
    } else if (!shapeExprs[i].empty()) {
      out << "s" << resultTemp[i] << "=" << shapeExprs[i] << "\n";
    }
  }

  // Emit return
  if (ir.rootTemp < resultTemp.size()) {
    out << "return s" << resultTemp[ir.rootTemp];
  }

  return out.str();
}

}  // namespace kernel
