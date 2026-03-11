#include "kernel/unparse_dsl.h"
#include <cmath>
#include <cstdio>
#include <sstream>
#include <string>
#include <vector>

namespace kernel {

namespace {

constexpr float kEps = 1e-6f;

bool isIdentityTransform(float tx, float ty, float tz, float sx, float sy, float sz) {
  return std::abs(tx) < kEps && std::abs(ty) < kEps && std::abs(tz) < kEps &&
         std::abs(sx - 1.0f) < kEps && std::abs(sy - 1.0f) < kEps &&
         std::abs(sz - 1.0f) < kEps;
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
  size_t numTransforms = ir.transforms.size() / 6;
  transformWrap.resize(numTransforms);

  for (size_t ti = 1; ti < numTransforms; ++ti) {
    size_t base = ti * 6;
    if (base + 6 > ir.transforms.size()) break;
    float tx = ir.transforms[base];
    float ty = ir.transforms[base + 1];
    float tz = ir.transforms[base + 2];
    float sx = ir.transforms[base + 3];
    float sy = ir.transforms[base + 4];
    float sz = ir.transforms[base + 5];

    if (isIdentityTransform(tx, ty, tz, sx, sy, sz)) {
      transformWrap[ti] = "";
      continue;
    }

    std::string inner = "%s";  // placeholder for shape
    if (isScaleOne(sx, sy, sz)) {
      out << "t" << tVarCount << "=translate(x=" << formatFloat(tx) << ",y="
          << formatFloat(ty) << ",z=" << formatFloat(tz) << ")\n";
      transformWrap[ti] = "apply(t" + std::to_string(tVarCount) + ", %s)";
      ++tVarCount;
    } else if (isTranslateZero(tx, ty, tz)) {
      out << "t" << tVarCount << "=scale(x=" << formatFloat(sx) << ",y="
          << formatFloat(sy) << ",z=" << formatFloat(sz) << ")\n";
      transformWrap[ti] = "apply(t" + std::to_string(tVarCount) + ", %s)";
      ++tVarCount;
    } else {
      out << "t" << tVarCount << "=translate(x=" << formatFloat(tx) << ",y="
          << formatFloat(ty) << ",z=" << formatFloat(tz) << ")\n";
      out << "t" << (tVarCount + 1) << "=scale(x=" << formatFloat(sx) << ",y="
          << formatFloat(sy) << ",z=" << formatFloat(sz) << ")\n";
      transformWrap[ti] = "apply(t" + std::to_string(tVarCount + 1) +
                          ", apply(t" + std::to_string(tVarCount) + ", %s))";
      tVarCount += 2;
    }
  }

  // resultTemp[i] = DSL temp index for result of instr i.
  // When Eval* has transform, we emit primitive first (extra temp), so result shifts.
  std::vector<size_t> resultTemp(ir.instrs.size());
  size_t nextTemp = 0;
  for (size_t i = 0; i < ir.instrs.size(); ++i) {
    const FlatInstr& instr = ir.instrs[i];
    bool hasTransform =
        (instr.op == FlatOp::EvalSphere || instr.op == FlatOp::EvalBox ||
         instr.op == FlatOp::EvalPlane) &&
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

    switch (instr.op) {
      case FlatOp::EvalSphere: {
        if (instr.constIdx < ir.spheres.size()) {
          prim = "sphere(r=" + formatFloat(ir.spheres[instr.constIdx]) + ")";
        } else {
          prim = "sphere(r=1)";
        }
        break;
      }
      case FlatOp::EvalBox: {
        size_t base = instr.constIdx * 3;
        if (base + 3 <= ir.boxes.size()) {
          prim = "box(x=" + formatFloat(ir.boxes[base]) + ",y=" +
                 formatFloat(ir.boxes[base + 1]) + ",z=" +
                 formatFloat(ir.boxes[base + 2]) + ")";
        } else {
          prim = "box(x=1,y=1,z=1)";
        }
        break;
      }
      case FlatOp::EvalPlane: {
        size_t base = instr.constIdx * 4;
        if (base + 4 <= ir.planes.size()) {
          prim = "plane(nx=" + formatFloat(ir.planes[base]) + ",ny=" +
                 formatFloat(ir.planes[base + 1]) + ",nz=" +
                 formatFloat(ir.planes[base + 2]) + ",d=" +
                 formatFloat(ir.planes[base + 3]) + ")";
        } else {
          prim = "plane(nx=0,ny=1,nz=0,d=0)";
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
      default:
        break;
    }

    if (instr.op == FlatOp::EvalSphere || instr.op == FlatOp::EvalBox ||
        instr.op == FlatOp::EvalPlane) {
      primitiveExprs[i] = prim;
    }
  }

  // Emit shape assignments
  for (size_t i = 0; i < ir.instrs.size(); ++i) {
    const FlatInstr& instr = ir.instrs[i];
    bool hasTransform =
        (instr.op == FlatOp::EvalSphere || instr.op == FlatOp::EvalBox ||
         instr.op == FlatOp::EvalPlane) &&
        instr.arg0 < transformWrap.size() && !transformWrap[instr.arg0].empty();

    if (instr.op == FlatOp::EvalSphere || instr.op == FlatOp::EvalBox ||
        instr.op == FlatOp::EvalPlane) {
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
  if (ir.rootTemp.id < resultTemp.size()) {
    out << "return s" << resultTemp[ir.rootTemp.id];
  }

  return out.str();
}

}  // namespace kernel
