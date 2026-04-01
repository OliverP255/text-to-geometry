#include "kernel/builder.h"
#include "kernel/node.h"
#include <gtest/gtest.h>
#include <vector>

using namespace kernel;

TEST(DagBuilderInterning, SameShapeSameHandle) {
  Builder b;
  ShapeH s1 = b.sphere(1.0f);
  ShapeH s2 = b.sphere(1.0f);
  EXPECT_EQ(s1.id, s2.id) << "rebuilding same shape should return same handle";
}

TEST(DagBuilderInterning, DifferentShapeDifferentHandle) {
  Builder b;
  ShapeH s1 = b.sphere(1.0f);
  ShapeH s2 = b.sphere(2.0f);
  EXPECT_NE(s1.id, s2.id) << "different shapes should have different handles";
}

TEST(DagBuilderInterning, UnionCommutativeCanonicalization) {
  Builder b;
  ShapeH a = b.sphere(1.0f);
  ShapeH b_ = b.box({1, 1, 1});
  ShapeH u1 = b.unite(a, b_);
  ShapeH u2 = b.unite(b_, a);
  EXPECT_EQ(u1.id, u2.id)
      << "unite(a,b) and unite(b,a) should intern identically";
}

TEST(DagBuilderInterning, IntersectCommutativeCanonicalization) {
  Builder b;
  ShapeH a = b.sphere(1.0f);
  ShapeH b_ = b.box({1, 1, 1});
  ShapeH i1 = b.intersect(a, b_);
  ShapeH i2 = b.intersect(b_, a);
  EXPECT_EQ(i1.id, i2.id)
      << "intersect(a,b) and intersect(b,a) should intern identically";
}

TEST(DagBuilderInterning, SubtractNotCommutative) {
  Builder b;
  ShapeH a = b.sphere(1.0f);
  ShapeH b_ = b.box({1, 1, 1});
  ShapeH s1 = b.subtract(a, b_);
  ShapeH s2 = b.subtract(b_, a);
  EXPECT_NE(s1.id, s2.id) << "subtract(a,b) and subtract(b,a) differ";
}

TEST(DagBuilderInterning, TransformDeduplication) {
  Builder b;
  TransformH t1 = b.translate({1, 0, 0});
  TransformH t2 = b.translate({1, 0, 0});
  EXPECT_EQ(t1.id, t2.id) << "same transform payload should deduplicate";
}

TEST(DagBuilderInterning, ApplyTransformDeduplication) {
  Builder b;
  TransformH t = b.translate({1, 0, 0});
  ShapeH s = b.sphere(0.5f);
  ShapeH a1 = b.apply(t, s);
  ShapeH a2 = b.apply(t, s);
  EXPECT_EQ(a1.id, a2.id)
      << "apply(same transform, same shape) should deduplicate";
}

TEST(DagBuilderFreeze, FreezeSealsBuilder) {
  Builder b;
  ShapeH root = b.sphere(1.0f);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  EXPECT_TRUE(b.isFrozen());
  EXPECT_EQ(dag.rootId, root.id);
  EXPECT_GT(dag.headerCount, 0u);
  EXPECT_NE(dag.headers, nullptr);
}

TEST(DagBuilderFreeze, FreezePreventsFurtherConstruction) {
  Builder b;
  ShapeH root = b.sphere(1.0f);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  ShapeH after = b.sphere(2.0f);
  EXPECT_FALSE(after.valid())
      << "construction after freeze should return invalid";
}

TEST(DagBuilderFreeze, FrozenDagLayout) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({0.5f, 0.5f, 0.5f});
  ShapeH root = b.unite(s, bx);
  FrozenDAG dag = {};
  b.freeze(root, dag);

  EXPECT_NE(dag.rootId, 0u);
  EXPECT_NE(dag.headers, nullptr);
  EXPECT_GE(dag.headerCount, 3u);  // sphere, box, union
  EXPECT_NE(dag.payloads, nullptr);
  EXPECT_GE(dag.payloadBytes, sizeof(SpherePayload) + sizeof(BoxPayload));

  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(dag.headers);
  const NodeHeader& rootHeader = headers[dag.rootId - 1];
  EXPECT_EQ(rootHeader.category, NodeCategory::Shape);
  EXPECT_EQ(rootHeader.opcode, static_cast<uint8_t>(ShapeOp::Union));
  EXPECT_EQ(rootHeader.arity, 2);
  EXPECT_EQ(rootHeader.in0, s.id) << "union children stored inline in header";
  EXPECT_EQ(rootHeader.in1, bx.id);
}

TEST(DagBuilderPrimitives, CylinderAndBox) {
  Builder b;
  ShapeH c = b.cylinder(0.5f, 1.0f);
  ShapeH bx = b.box({1, 1, 1});
  EXPECT_TRUE(c.valid());
  EXPECT_TRUE(bx.valid());
  ShapeH u = b.unite(c, bx);
  EXPECT_TRUE(u.valid());
}

TEST(DagBuilderNary, UniteSingle) {
  Builder b;
  ShapeH a = b.sphere(1.0f);
  ShapeH u = b.unite(std::vector<ShapeH>{a});
  EXPECT_EQ(u.id, a.id) << "unite({a}) should return a";
}

TEST(DagBuilderNary, IntersectSingle) {
  Builder b;
  ShapeH a = b.box({1, 1, 1});
  ShapeH i = b.intersect(std::vector<ShapeH>{a});
  EXPECT_EQ(i.id, a.id) << "intersect({a}) should return a";
}

TEST(DagBuilderNary, UniteBalanced) {
  Builder b;
  ShapeH a = b.sphere(1.0f);
  ShapeH b_ = b.box({1, 1, 1});
  ShapeH c = b.cylinder(0.3f, 0.5f);
  ShapeH d = b.box({0.5f, 0.5f, 0.5f});
  ShapeH u = b.unite(std::vector<ShapeH>{a, b_, c, d});
  EXPECT_TRUE(u.valid());
  FrozenDAG dag = {};
  b.freeze(u, dag);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(dag.headers);
  const NodeHeader& root = headers[dag.rootId - 1];
  EXPECT_EQ(root.opcode, static_cast<uint8_t>(ShapeOp::Union));
  EXPECT_EQ(root.arity, 2);
  EXPECT_NE(root.in0, 0xFFFFFFFFu);
  EXPECT_NE(root.in1, 0xFFFFFFFFu);
  EXPECT_EQ(headers[root.in0 - 1].opcode,
            static_cast<uint8_t>(ShapeOp::Union));
  EXPECT_EQ(headers[root.in1 - 1].opcode,
            static_cast<uint8_t>(ShapeOp::Union));
}

TEST(DagBuilderNary, IntersectBalanced) {
  Builder b;
  ShapeH a = b.sphere(1.0f);
  ShapeH b_ = b.box({1, 1, 1});
  ShapeH i = b.intersect(std::vector<ShapeH>{a, b_});
  EXPECT_TRUE(i.valid());
  EXPECT_EQ(i.id, b.intersect(a, b_).id);
}
