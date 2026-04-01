#include "eval_dag.h"
#include "eval_flat_ir.h"
#include "kernel/builder.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include "kernel/node.h"
#include "kernel/optimise.h"
#include <cmath>
#include <functional>
#include <gtest/gtest.h>

using namespace kernel;

// --- Tests ---

TEST(Lower, SingleSphere) {
  Builder b;
  ShapeH root = b.sphere(1.0f);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 1u);
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[0].arg0, 0u);  // transformIdx 0 = identity
  EXPECT_EQ(ir.spheres.size(), 1u);
  EXPECT_FLOAT_EQ(ir.spheres[0].r, 1.0f);
  EXPECT_EQ(ir.rootTemp, 0u);
}

TEST(Lower, SingleBox) {
  Builder b;
  ShapeH root = b.box({1, 1, 1});
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 1u);
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalBox));
  EXPECT_EQ(ir.instrs[0].arg0, 0u);
  EXPECT_EQ(ir.boxes.size(), 1u);
  EXPECT_FLOAT_EQ(ir.boxes[0].hx, 1.0f);
  EXPECT_FLOAT_EQ(ir.boxes[0].hy, 1.0f);
  EXPECT_FLOAT_EQ(ir.boxes[0].hz, 1.0f);
  EXPECT_EQ(ir.rootTemp, 0u);
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
  EXPECT_EQ(ir.rootTemp, 0u);
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
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[1].op, static_cast<uint32_t>(FlatOp::EvalBox));
  EXPECT_EQ(ir.instrs[2].op, static_cast<uint32_t>(FlatOp::CsgUnion));
  EXPECT_EQ(ir.rootTemp, 2u);
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
  EXPECT_EQ(ir.instrs[2].op, static_cast<uint32_t>(FlatOp::CsgIntersect));
  EXPECT_EQ(ir.rootTemp, 2u);
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
  EXPECT_EQ(ir.instrs[2].op, static_cast<uint32_t>(FlatOp::CsgSubtract));
  EXPECT_EQ(ir.rootTemp, 2u);
}

TEST(Lower, UnionSameShape) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH root = b.unite(s, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 2u);
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[1].op, static_cast<uint32_t>(FlatOp::CsgUnion));
  EXPECT_EQ(ir.spheres.size(), 1u);
  EXPECT_EQ(ir.rootTemp, 1u);
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
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[0].arg0, 1u);
  EXPECT_EQ(ir.transforms.size(), 2u);  // identity + translate(1,0,0)
  EXPECT_FLOAT_EQ(ir.transforms[1].tx, 1.0f);
  EXPECT_FLOAT_EQ(ir.transforms[1].ty, 0.0f);
  EXPECT_FLOAT_EQ(ir.transforms[1].tz, 0.0f);
  EXPECT_EQ(ir.rootTemp, 0u);
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
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[0].arg0, 1u);
  EXPECT_GE(ir.transforms.size(), 2u);
  EXPECT_EQ(ir.rootTemp, 0u);
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
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[0].arg0, 1u);
  EXPECT_GE(ir.transforms.size(), 2u);
  EXPECT_EQ(ir.rootTemp, 0u);
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
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[1].op, static_cast<uint32_t>(FlatOp::EvalBox));
  EXPECT_EQ(ir.instrs[2].op, static_cast<uint32_t>(FlatOp::CsgUnion));
  EXPECT_EQ(ir.rootTemp, 2u);
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
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[1].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[2].op, static_cast<uint32_t>(FlatOp::CsgUnion));
  EXPECT_EQ(ir.spheres.size(), 2u);  // No dedup: same shape, different transforms
  EXPECT_EQ(ir.rootTemp, 2u);
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
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[0].arg0, 0u);
  EXPECT_EQ(ir.rootTemp, 0u);
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
  EXPECT_EQ(ir.rootTemp, 0u);
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
  EXPECT_EQ(ir.rootTemp, 0u);
}

TEST(Lower, DeeplyNestedCSG) {
  Builder b;
  ShapeH a = b.sphere(0.5f);
  ShapeH bx = b.box({0.3f, 0.3f, 0.3f});
  ShapeH c = b.cylinder(0.2f, 0.5f);
  ShapeH d = b.sphere(1.0f);
  ShapeH u1 = b.unite(a, bx);
  ShapeH u2 = b.unite(c, d);
  ShapeH root = b.unite(u1, u2);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_GE(ir.instrs.size(), 4u);
  EXPECT_EQ(ir.instrs.back().op, static_cast<uint32_t>(FlatOp::CsgUnion));
  EXPECT_TRUE(ir.rootTemp > 0);
}

TEST(Lower, TripleUnion) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({0.5f, 0.5f, 0.5f});
  ShapeH cyl = b.cylinder(0.2f, 0.5f);
  ShapeH inner = b.unite(bx, cyl);
  ShapeH root = b.unite(s, inner);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  EXPECT_EQ(ir.instrs.size(), 5u);
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[1].op, static_cast<uint32_t>(FlatOp::EvalBox));
  EXPECT_EQ(ir.instrs[2].op, static_cast<uint32_t>(FlatOp::EvalCylinder));
  EXPECT_EQ(ir.instrs[3].op, static_cast<uint32_t>(FlatOp::CsgUnion));
  EXPECT_EQ(ir.instrs[4].op, static_cast<uint32_t>(FlatOp::CsgUnion));
  EXPECT_EQ(ir.rootTemp, 4u);
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
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.instrs[0].arg0, 0u);
  EXPECT_EQ(ir.rootTemp, 0u);
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
  EXPECT_EQ(ir.instrs[0].op, static_cast<uint32_t>(FlatOp::EvalSphere));
  EXPECT_EQ(ir.rootTemp, 0u);
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
    EXPECT_FLOAT_EQ(ir0.transforms[i].tx, ir1.transforms[i].tx);
    EXPECT_FLOAT_EQ(ir0.transforms[i].ty, ir1.transforms[i].ty);
    EXPECT_FLOAT_EQ(ir0.transforms[i].tz, ir1.transforms[i].tz);
    EXPECT_FLOAT_EQ(ir0.transforms[i].sx, ir1.transforms[i].sx);
    EXPECT_FLOAT_EQ(ir0.transforms[i].sy, ir1.transforms[i].sy);
    EXPECT_FLOAT_EQ(ir0.transforms[i].sz, ir1.transforms[i].sz);
  }
  EXPECT_EQ(ir0.spheres.size(), ir1.spheres.size());
  for (size_t i = 0; i < ir0.spheres.size(); ++i)
    EXPECT_FLOAT_EQ(ir0.spheres[i].r, ir1.spheres[i].r);
  EXPECT_EQ(ir0.boxes.size(), ir1.boxes.size());
  for (size_t i = 0; i < ir0.boxes.size(); ++i) {
    EXPECT_FLOAT_EQ(ir0.boxes[i].hx, ir1.boxes[i].hx);
    EXPECT_FLOAT_EQ(ir0.boxes[i].hy, ir1.boxes[i].hy);
    EXPECT_FLOAT_EQ(ir0.boxes[i].hz, ir1.boxes[i].hz);
  }
  EXPECT_EQ(ir0.rootTemp, ir1.rootTemp);
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
      float dIr = eval_flat_ir::evalFlatIR(ir, p);
      EXPECT_NEAR(dDag, dIr, eps) << " at p=(" << p.x << "," << p.y << ","
                                  << p.z << ")";
    }
  };

  testShape([](Builder& b) { return b.sphere(1.0f); });
  testShape([](Builder& b) { return b.box({1, 1, 1}); });
  testShape([](Builder& b) { return b.cylinder(0.5f, 1.0f); });
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
