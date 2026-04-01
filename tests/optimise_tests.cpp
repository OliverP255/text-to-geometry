#include "eval_dag.h"
#include "kernel/builder.h"
#include "kernel/node.h"
#include "kernel/optimise.h"
#include <gtest/gtest.h>
#include <vector>

using namespace kernel;

namespace {

const std::vector<Vec3> kSamplePoints = {
    {0, 0, 0},      {1, 0, 0},      {0, 1, 0},      {0, 0, 1},
    {-1, 0, 0},     {0.5f, 0.5f, 0.5f}, {2, 0, 0},  {0, 0, -1},
    {0.3f, -0.3f, 0.2f},
};

void assertSemanticEquiv(const FrozenDAG& input, const OptimisedDAG& opt,
                         const std::vector<Vec3>& points,
                         float eps = 1e-5f) {
  for (const Vec3& p : points) {
    float dIn = eval_dag::evalDAG(input, p);
    float dOpt = eval_dag::evalDAG(opt.view, p);
    EXPECT_NEAR(dIn, dOpt, eps)
        << " at p=(" << p.x << "," << p.y << "," << p.z << ")";
  }
}

}  // namespace

TEST(Optimise, IdentityElisionTranslateZero) {
  Builder b;
  TransformH t = b.translate({0, 0, 0});
  ShapeH s = b.sphere(1.0f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  EXPECT_NE(opt.view.rootId, 0u);
  EXPECT_LT(opt.view.headerCount, dag.headerCount);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(opt.view.headers);
  const NodeHeader& rootH = headers[opt.view.rootId - 1];
  EXPECT_EQ(rootH.opcode, static_cast<uint8_t>(ShapeOp::Sphere));
  EXPECT_EQ(rootH.arity, 0);
}

TEST(Optimise, IdentityElisionScaleOne) {
  Builder b;
  TransformH t = b.scale({1, 1, 1});
  ShapeH s = b.box({1, 1, 1});
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  EXPECT_NE(opt.view.rootId, 0u);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(opt.view.headers);
  const NodeHeader& rootH = headers[opt.view.rootId - 1];
  EXPECT_EQ(rootH.opcode, static_cast<uint8_t>(ShapeOp::Box));
}

TEST(Optimise, NonIdentityPreserved) {
  Builder b;
  TransformH t = b.translate({1, 0, 0});
  ShapeH s = b.sphere(1.0f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  EXPECT_NE(opt.view.rootId, 0u);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(opt.view.headers);
  const NodeHeader& rootH = headers[opt.view.rootId - 1];
  EXPECT_EQ(rootH.opcode, static_cast<uint8_t>(ShapeOp::ApplyTransform));
  EXPECT_EQ(rootH.arity, 2);
}

TEST(Optimise, NestedIdentityElided) {
  Builder b;
  TransformH t0 = b.translate({0, 0, 0});
  TransformH t1 = b.scale({1, 1, 1});
  ShapeH s = b.sphere(1.0f);
  ShapeH inner = b.apply(t0, s);
  ShapeH root = b.apply(t1, inner);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  EXPECT_NE(opt.view.rootId, 0u);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(opt.view.headers);
  const NodeHeader& rootH = headers[opt.view.rootId - 1];
  EXPECT_EQ(rootH.opcode, static_cast<uint8_t>(ShapeOp::Sphere));
}

TEST(Optimise, DedupIdenticalPrimitives) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH root = b.unite(s, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  EXPECT_NE(opt.view.rootId, 0u);
  EXPECT_EQ(opt.view.headerCount, 2u);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(opt.view.headers);
  const NodeHeader& rootH = headers[opt.view.rootId - 1];
  EXPECT_EQ(rootH.opcode, static_cast<uint8_t>(ShapeOp::Union));
  EXPECT_EQ(rootH.in0, rootH.in1);
}

TEST(Optimise, DedupIdenticalSubtrees) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({1, 1, 1});
  ShapeH inner = b.unite(s, bx);
  ShapeH root = b.unite(inner, inner);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  EXPECT_NE(opt.view.rootId, 0u);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(opt.view.headers);
  const NodeHeader& rootH = headers[opt.view.rootId - 1];
  EXPECT_EQ(rootH.opcode, static_cast<uint8_t>(ShapeOp::Union));
  EXPECT_EQ(rootH.in0, rootH.in1);
}

TEST(Optimise, DedupCommutativeCanonical) {
  Builder b;
  ShapeH a = b.sphere(1.0f);
  ShapeH bx = b.box({1, 1, 1});
  ShapeH u1 = b.unite(a, bx);
  ShapeH u2 = b.unite(bx, a);
  ShapeH root = b.unite(u1, u2);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  EXPECT_NE(opt.view.rootId, 0u);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(opt.view.headers);
  const NodeHeader& rootH = headers[opt.view.rootId - 1];
  EXPECT_EQ(rootH.opcode, static_cast<uint8_t>(ShapeOp::Union));
  EXPECT_EQ(rootH.in0, rootH.in1);
}

TEST(Optimise, PassthroughNoOp) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  FrozenDAG dag = {};
  b.freeze(s, dag);
  OptimisedDAG opt = optimise(dag);
  EXPECT_NE(opt.view.rootId, 0u);
  EXPECT_EQ(opt.view.headerCount, dag.headerCount);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(opt.view.headers);
  const NodeHeader& rootH = headers[opt.view.rootId - 1];
  EXPECT_EQ(rootH.opcode, static_cast<uint8_t>(ShapeOp::Sphere));
}

TEST(Optimise, NodeCountReduced) {
  Builder b;
  TransformH t = b.translate({0, 0, 0});
  ShapeH s = b.sphere(1.0f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  EXPECT_LT(opt.view.headerCount, dag.headerCount);
}

TEST(Optimise, EmptyInvalid) {
  FrozenDAG dag = {};
  dag.rootId = 0;
  dag.headers = nullptr;
  dag.headerCount = 0;
  dag.payloads = nullptr;
  dag.payloadBytes = 0;
  OptimisedDAG opt = optimise(dag);
  EXPECT_EQ(opt.view.rootId, 0u);
  EXPECT_EQ(opt.view.headerCount, 0u);
}

TEST(Optimise, SemanticEquiv_Sphere) {
  Builder b;
  ShapeH root = b.sphere(1.0f);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_Box) {
  Builder b;
  ShapeH root = b.box({1, 1, 1});
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_Union) {
  Builder b;
  ShapeH root = b.unite(b.sphere(1.0f), b.box({0.5f, 0.5f, 0.5f}));
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_Intersect) {
  Builder b;
  ShapeH root = b.intersect(b.sphere(1.0f), b.box({1, 1, 1}));
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_Subtract) {
  Builder b;
  ShapeH root = b.subtract(b.sphere(1.0f), b.box({0.5f, 0.5f, 0.5f}));
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_Translate) {
  Builder b;
  ShapeH root = b.apply(b.translate({1, 0, 0}), b.sphere(0.5f));
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_Scale) {
  Builder b;
  ShapeH root = b.apply(b.scale({2, 2, 2}), b.sphere(0.5f));
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_NestedTransforms) {
  Builder b;
  ShapeH inner = b.apply(b.scale({2, 2, 2}), b.sphere(0.5f));
  ShapeH root = b.apply(b.translate({1, 0, 0}), inner);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_IdentityElided) {
  Builder b;
  ShapeH root = b.apply(b.translate({0, 0, 0}), b.sphere(1.0f));
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_ScaleOneElided) {
  Builder b;
  ShapeH root = b.apply(b.scale({1, 1, 1}), b.box({1, 1, 1}));
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_DedupIdentical) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH root = b.unite(s, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_DedupSubtrees) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({1, 1, 1});
  ShapeH inner = b.unite(s, bx);
  ShapeH root = b.unite(inner, inner);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}

TEST(Optimise, SemanticEquiv_Complex) {
  Builder b;
  TransformH t = b.translate({1, 0, 0});
  ShapeH s = b.sphere(0.5f);
  ShapeH translated = b.apply(t, s);
  ShapeH bx = b.box({1, 1, 1});
  ShapeH cyl = b.cylinder(0.5f, 1.0f);
  ShapeH inter = b.intersect(bx, cyl);
  ShapeH root = b.unite(translated, inter);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  OptimisedDAG opt = optimise(dag);
  assertSemanticEquiv(dag, opt, kSamplePoints);
}
