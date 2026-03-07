#include "eval_dag.h"
#include "kernel/builder.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include "kernel/node.h"
#include "kernel/optimise.h"
#include <cmath>
#include <functional>
#include <gtest/gtest.h>

using namespace kernel;

// --- FlatIR interpreter for semantic equivalence test ---
// Each EVAL produces a temp, each CSG consumes two temps and produces one.
static float evalFlatIRImpl(const FlatIR& ir, const Vec3& p) {
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

// Wrapper that handles empty IR
float evalFlatIR(const FlatIR& ir, const Vec3& p) {
  if (ir.instrs.empty()) return 1e10f;
  return evalFlatIRImpl(ir, p);
}

// --- Tests ---

TEST(Lower, SingleSphere) {
  Builder b;
  ShapeH root = b.sphere(1.0f);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 1u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[0].arg0, 0u);  // transformIdx 0 = identity
  EXPECT_EQ(ir.spheres.size(), 1u);
  EXPECT_FLOAT_EQ(ir.spheres[0], 1.0f);
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, SingleBox) {
  Builder b;
  ShapeH root = b.box({1, 1, 1});
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 1u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalBox);
  EXPECT_EQ(ir.instrs[0].arg0, 0u);
  EXPECT_EQ(ir.boxes.size(), 3u);
  EXPECT_FLOAT_EQ(ir.boxes[0], 1.0f);
  EXPECT_FLOAT_EQ(ir.boxes[1], 1.0f);
  EXPECT_FLOAT_EQ(ir.boxes[2], 1.0f);
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, SinglePlane) {
  Builder b;
  ShapeH root = b.plane({0, 1, 0}, 0);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 1u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalPlane);
  EXPECT_EQ(ir.instrs[0].arg0, 0u);
  EXPECT_EQ(ir.planes.size(), 4u);
  EXPECT_FLOAT_EQ(ir.planes[0], 0.0f);
  EXPECT_FLOAT_EQ(ir.planes[1], 1.0f);
  EXPECT_FLOAT_EQ(ir.planes[2], 0.0f);
  EXPECT_FLOAT_EQ(ir.planes[3], 0.0f);
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, EmptyDAG) {
  FrozenDAG dag = {};
  dag.rootId = 0;
  dag.headers = nullptr;
  dag.headerCount = 0;
  dag.payloads = nullptr;
  dag.payloadBytes = 0;

  FlatIR ir = lower(dag);

  EXPECT_TRUE(ir.instrs.empty());
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, Union) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({0.5f, 0.5f, 0.5f});
  ShapeH root = b.unite(s, bx);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 3u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[1].op, FlatOp::EvalBox);
  EXPECT_EQ(ir.instrs[2].op, FlatOp::CsgUnion);
  EXPECT_EQ(ir.rootTemp.id, 2u);
}

TEST(Lower, Intersect) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({1, 1, 1});
  ShapeH root = b.intersect(s, bx);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 3u);
  EXPECT_EQ(ir.instrs[2].op, FlatOp::CsgIntersect);
  EXPECT_EQ(ir.rootTemp.id, 2u);
}

TEST(Lower, Subtract) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({0.5f, 0.5f, 0.5f});
  ShapeH root = b.subtract(s, bx);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 3u);
  EXPECT_EQ(ir.instrs[2].op, FlatOp::CsgSubtract);
  EXPECT_EQ(ir.rootTemp.id, 2u);
}

TEST(Lower, UnionSameShape) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH root = b.unite(s, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 2u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[1].op, FlatOp::CsgUnion);
  EXPECT_EQ(ir.spheres.size(), 1u);
  EXPECT_EQ(ir.rootTemp.id, 1u);
}

TEST(Lower, TranslateSphere) {
  Builder b;
  TransformH t = b.translate({1, 0, 0});
  ShapeH s = b.sphere(0.5f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 1u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[0].arg0, 1u);
  EXPECT_EQ(ir.transforms.size(), 12u);
  EXPECT_FLOAT_EQ(ir.transforms[6], 1.0f);
  EXPECT_FLOAT_EQ(ir.transforms[7], 0.0f);
  EXPECT_FLOAT_EQ(ir.transforms[8], 0.0f);
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, ScaleSphere) {
  Builder b;
  TransformH t = b.scale({2, 2, 2});
  ShapeH s = b.sphere(0.5f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 1u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[0].arg0, 1u);
  EXPECT_GE(ir.transforms.size(), 12u);
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, NestedTransforms) {
  Builder b;
  TransformH t0 = b.translate({1, 0, 0});
  TransformH t1 = b.scale({2, 2, 2});
  ShapeH s = b.sphere(0.5f);
  ShapeH inner = b.apply(t1, s);
  ShapeH root = b.apply(t0, inner);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 1u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[0].arg0, 1u);
  EXPECT_GE(ir.transforms.size(), 12u);
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, MixedUnion) {
  Builder b;
  TransformH t = b.translate({1, 0, 0});
  ShapeH s = b.sphere(0.5f);
  ShapeH translated = b.apply(t, s);
  ShapeH bx = b.box({1, 1, 1});
  ShapeH root = b.unite(translated, bx);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 3u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[1].op, FlatOp::EvalBox);
  EXPECT_EQ(ir.instrs[2].op, FlatOp::CsgUnion);
  EXPECT_EQ(ir.rootTemp.id, 2u);
}

TEST(Lower, SameNodeDifferentTransforms) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  TransformH t1 = b.translate({1, 0, 0});
  TransformH t2 = b.translate({-1, 0, 0});
  ShapeH a = b.apply(t1, s);
  ShapeH b_ = b.apply(t2, s);
  ShapeH root = b.unite(a, b_);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 3u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[1].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[2].op, FlatOp::CsgUnion);
  EXPECT_EQ(ir.spheres.size(), 2u);  // No dedup: same shape, different transforms
  EXPECT_EQ(ir.rootTemp.id, 2u);
}

TEST(Lower, IdentityTransform) {
  Builder b;
  TransformH t = b.translate({0, 0, 0});
  ShapeH s = b.sphere(1.0f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 1u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[0].arg0, 0u);
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, NullHeaders) {
  FrozenDAG dag = {};
  dag.rootId = 1;
  dag.headers = nullptr;
  dag.headerCount = 0;
  dag.payloads = nullptr;
  dag.payloadBytes = 0;

  FlatIR ir = lower(dag);

  EXPECT_TRUE(ir.instrs.empty());
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, ZeroHeaderCount) {
  FrozenDAG dag = {};
  dag.rootId = 1;
  dag.headers = reinterpret_cast<const uint8_t*>(&dag);
  dag.headerCount = 0;
  dag.payloads = nullptr;
  dag.payloadBytes = 0;

  FlatIR ir = lower(dag);

  EXPECT_TRUE(ir.instrs.empty());
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, DeeplyNestedCSG) {
  Builder b;
  ShapeH a = b.sphere(0.5f);
  ShapeH bx = b.box({0.3f, 0.3f, 0.3f});
  ShapeH c = b.plane({0, 1, 0}, 0);
  ShapeH d = b.sphere(1.0f);
  ShapeH u1 = b.unite(a, bx);
  ShapeH u2 = b.unite(c, d);
  ShapeH root = b.unite(u1, u2);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_GE(ir.instrs.size(), 4u);
  EXPECT_EQ(ir.instrs.back().op, FlatOp::CsgUnion);
  EXPECT_TRUE(ir.rootTemp.id > 0);
}

TEST(Lower, TripleUnion) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({0.5f, 0.5f, 0.5f});
  ShapeH pl = b.plane({0, 1, 0}, 0);
  ShapeH inner = b.unite(bx, pl);
  ShapeH root = b.unite(s, inner);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 5u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[1].op, FlatOp::EvalBox);
  EXPECT_EQ(ir.instrs[2].op, FlatOp::EvalPlane);
  EXPECT_EQ(ir.instrs[3].op, FlatOp::CsgUnion);
  EXPECT_EQ(ir.instrs[4].op, FlatOp::CsgUnion);
  EXPECT_EQ(ir.rootTemp.id, 4u);
}

TEST(Lower, ScaleOne) {
  Builder b;
  TransformH t = b.scale({1, 1, 1});
  ShapeH s = b.sphere(1.0f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 1u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.instrs[0].arg0, 0u);
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, OptimisedThenLower) {
  Builder b;
  TransformH t = b.translate({0, 0, 0});
  ShapeH s = b.sphere(1.0f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  FlatIR ir = lower(opt.view);

  EXPECT_GE(ir.instrs.size(), 1u);
  EXPECT_EQ(ir.instrs[0].op, FlatOp::EvalSphere);
  EXPECT_EQ(ir.rootTemp.id, 0u);
}

TEST(Lower, LoweringIsDeterministic) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({0.5f, 0.5f, 0.5f});
  TransformH t = b.translate({1, 0, 0});
  ShapeH translated = b.apply(t, s);
  ShapeH root = b.unite(translated, bx);
  FrozenDAG dag = {};
  b.freeze(root, dag);

  FlatIR ir0 = lower(dag);
  FlatIR ir1 = lower(dag);
  FlatIR ir2 = lower(dag);

  EXPECT_EQ(ir0.instrs.size(), ir1.instrs.size());
  EXPECT_EQ(ir1.instrs.size(), ir2.instrs.size());

  for (size_t i = 0; i < ir0.instrs.size(); ++i) {
    EXPECT_EQ(ir0.instrs[i].op, ir1.instrs[i].op);
    EXPECT_EQ(ir0.instrs[i].arg0, ir1.instrs[i].arg0);
    EXPECT_EQ(ir0.instrs[i].arg1, ir1.instrs[i].arg1);
    EXPECT_EQ(ir0.instrs[i].constIdx, ir1.instrs[i].constIdx);
  }

  EXPECT_EQ(ir0.transforms.size(), ir1.transforms.size());
  for (size_t i = 0; i < ir0.transforms.size(); ++i) {
    EXPECT_FLOAT_EQ(ir0.transforms[i], ir1.transforms[i]);
  }
  EXPECT_EQ(ir0.spheres, ir1.spheres);
  EXPECT_EQ(ir0.boxes, ir1.boxes);
  EXPECT_EQ(ir0.planes, ir1.planes);
  EXPECT_EQ(ir0.rootTemp.id, ir1.rootTemp.id);
}

TEST(Lower, SemanticEquivalenceAtSamplePoints) {
  const float eps = 1e-5f;
  std::vector<Vec3> samplePoints = {
      {0, 0, 0},      {1, 0, 0},      {0, 1, 0},
      {0, 0, 1},      {-1, 0, 0},     {0.5f, 0.5f, 0.5f},
      {2, 0, 0},      {0, 0, -1},     {0.3f, -0.3f, 0.2f},
  };

  auto testShape = [&](const std::function<ShapeH(Builder&)>& build) {
    Builder b;
    ShapeH root = build(b);
    FrozenDAG dag = {};
    b.freeze(root, dag);
    FlatIR ir = lower(dag);
    for (const Vec3& p : samplePoints) {
      float dDag = eval_dag::evalDAG(dag, p);
      float dIr = evalFlatIR(ir, p);
      EXPECT_NEAR(dDag, dIr, eps) << " at p=(" << p.x << "," << p.y << ","
                                  << p.z << ")";
    }
  };

  testShape([](Builder& b) { return b.sphere(1.0f); });
  testShape([](Builder& b) { return b.box({1, 1, 1}); });
  testShape([](Builder& b) { return b.plane({0, 1, 0}, 0); });
  testShape([](Builder& b) {
    return b.unite(b.sphere(1.0f), b.box({0.5f, 0.5f, 0.5f}));
  });
  testShape([](Builder& b) {
    return b.apply(b.translate({1, 0, 0}), b.sphere(0.5f));
  });
  testShape([](Builder& b) {
    return b.apply(b.scale({2, 2, 2}), b.sphere(0.5f));
  });
  // Nested mixed transforms: translate then scale
  testShape([](Builder& b) {
    ShapeH inner = b.apply(b.scale({2, 2, 2}), b.sphere(0.5f));
    return b.apply(b.translate({1, 0, 0}), inner);
  });
  // Nested mixed transforms: scale then translate
  testShape([](Builder& b) {
    ShapeH inner = b.apply(b.translate({1, 0, 0}), b.sphere(0.5f));
    return b.apply(b.scale({2, 2, 2}), inner);
  });
}
