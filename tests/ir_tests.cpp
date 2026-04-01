#include "frontend/ir.h"
#include "kernel/node.h"
#include <gtest/gtest.h>

using namespace frontend;
using namespace kernel;

//make sure single sphere is compiled correctly
TEST(IR, SingleSphere) {
  auto r = compileIR("s0 = sphere(r=1.0)\nreturn s0");
  ASSERT_TRUE(r.ok) << r.error;
  EXPECT_NE(r.dag.rootId, 0u);
  EXPECT_GE(r.dag.headerCount, 1u);
  ASSERT_NE(r.dag.headers, nullptr);
  const NodeHeader* h = reinterpret_cast<const NodeHeader*>(r.dag.headers);
  EXPECT_EQ(h[r.dag.rootId - 1].opcode,
            static_cast<uint8_t>(ShapeOp::Sphere));
}

//make sure other combinations in DSL compile correctly in compileIR
TEST(IR, SphereAndBoxUnion) {
  auto r = compileIR(
      "s0 = sphere(r=1.0)\n"
      "s1 = box(x=1.0, y=1.0, z=1.0)\n"
      "s2 = union(s0, s1)\n"
      "return s2");
  ASSERT_TRUE(r.ok) << r.error;
  EXPECT_NE(r.dag.rootId, 0u);
  EXPECT_GE(r.dag.headerCount, 3u);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  const NodeHeader& root = headers[r.dag.rootId - 1];
  EXPECT_EQ(root.opcode, static_cast<uint8_t>(ShapeOp::Union));
  EXPECT_EQ(root.arity, 2);
}

TEST(IR, TranslateAndApply) {
  auto r = compileIR(
      "s0 = sphere(r=0.5)\n"
      "t0 = translate(x=2.0, y=0.0, z=0.0)\n"
      "s1 = apply(t0, s0)\n"
      "return s1");
  ASSERT_TRUE(r.ok) << r.error;
  EXPECT_NE(r.dag.rootId, 0u);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  const NodeHeader& root = headers[r.dag.rootId - 1];
  EXPECT_EQ(root.opcode, static_cast<uint8_t>(ShapeOp::ApplyTransform));
}

TEST(IR, Subtract) {
  auto r = compileIR(
      "s0 = sphere(r=1.0)\n"
      "s1 = box(x=0.5, y=0.5, z=0.5)\n"
      "s2 = subtract(s0, s1)\n"
      "return s2");
  ASSERT_TRUE(r.ok) << r.error;
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  const NodeHeader& root = headers[r.dag.rootId - 1];
  EXPECT_EQ(root.opcode, static_cast<uint8_t>(ShapeOp::Subtract));
}

TEST(IR, ExplicitReturn) {
  auto r = compileIR(
      "s0 = sphere(r=1.0)\n"
      "s1 = box(x=1.0, y=1.0, z=1.0)\n"
      "s2 = union(s0, s1)\n"
      "return s2");
  ASSERT_TRUE(r.ok) << r.error;
  EXPECT_NE(r.dag.rootId, 0u);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  const NodeHeader& root = headers[r.dag.rootId - 1];
  EXPECT_EQ(root.opcode, static_cast<uint8_t>(ShapeOp::Union));
}

TEST(IRParseErrors, RequireReturn) {
  auto r = compileIR(
      "s0 = sphere(r=1.0)\n"
      "s1 = box(x=1.0, y=1.0, z=1.0)\n"
      "s2 = union(s0, s1)");
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.error.find("return"), std::string::npos);
}

TEST(IR, NaryUnite) {
  auto r = compileIR(
      "s0 = sphere(r=1.0)\n"
      "s1 = box(x=1.0, y=1.0, z=1.0)\n"
      "s2 = cylinder(r=0.5, h=1.0)\n"
      "s3 = union(s0, s1, s2)\n"
      "return s3");
  ASSERT_TRUE(r.ok) << r.error;
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  const NodeHeader& root = headers[r.dag.rootId - 1];
  EXPECT_EQ(root.opcode, static_cast<uint8_t>(ShapeOp::Union));
}

TEST(IR, Scale) {
  auto r = compileIR(
      "s0 = box(x=1.0, y=1.0, z=1.0)\n"
      "t0 = scale(x=2.0, y=2.0, z=2.0)\n"
      "s1 = apply(t0, s0)\n"
      "return s1");
  ASSERT_TRUE(r.ok) << r.error;
}

TEST(IRParseErrors, UnknownOp) {
  auto r = compileIR("s0 = foo(r=1.0)");
  EXPECT_FALSE(r.ok);
  EXPECT_FALSE(r.error.empty());
  EXPECT_NE(r.error.find("unknown"), std::string::npos);
}

TEST(IRParseErrors, UndefinedRef) {
  auto r = compileIR("s0 = union(s1, s2)\nreturn s0");
  EXPECT_FALSE(r.ok);
  EXPECT_FALSE(r.error.empty());
}

TEST(IRParseErrors, ApplyTypeMismatch) {
  auto r = compileIR(
      "s0 = sphere(r=1.0)\n"
      "s1 = apply(s0, s0)\n"
      "return s1");
  EXPECT_FALSE(r.ok);
  EXPECT_FALSE(r.error.empty());
}

TEST(IRParseErrors, Lex) {
  auto r = compileIR("s0 = sphere(r=1.0)\nq0 = box(x=1,y=1,z=1)");
  EXPECT_FALSE(r.ok);
  EXPECT_FALSE(r.error.empty());
  EXPECT_NE(r.error.find("sN"), std::string::npos);
}

TEST(IRParseErrors, TrailingContent) {
  auto r = compileIR(
      "s0 = sphere(r=1.0)\n"
      "return s0\n"
      "x");
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.error.find("unexpected"), std::string::npos);
}

TEST(IR, NegativeNum) {
  auto r = compileIR(
      "s0 = sphere(r=1.0)\n"
      "t0 = translate(x=0.0, y=-1.0, z=0.0)\n"
      "s1 = apply(t0, s0)\n"
      "return s1");
  ASSERT_TRUE(r.ok) << r.error;
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  EXPECT_EQ(headers[r.dag.rootId - 1].opcode,
            static_cast<uint8_t>(ShapeOp::ApplyTransform));
}

TEST(IRParseErrors, InfRejected) {
  auto r = compileIR("s0 = sphere(r=1e99)\nreturn s0");
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.error.find("invalid"), std::string::npos);
}

TEST(IRParseErrors, NanRejected) {
  auto r = compileIR("s0 = sphere(r=nan)\nreturn s0");
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.error.find("number"), std::string::npos);
}

TEST(IR, Rotate) {
  auto r = compileIR(
      "s0 = sphere(r=1.0)\n"
      "t0 = rotate(x=0.0, y=0.707, z=0.0, w=0.707)\n"
      "s1 = apply(t0, s0)\n"
      "return s1");
  ASSERT_TRUE(r.ok) << r.error;
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  EXPECT_EQ(headers[r.dag.rootId - 1].opcode,
            static_cast<uint8_t>(ShapeOp::ApplyTransform));
}

TEST(IR, Cylinder) {
  auto r = compileIR("s0 = cylinder(r=0.2, h=1.0)\nreturn s0");
  ASSERT_TRUE(r.ok) << r.error;
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  EXPECT_EQ(headers[r.dag.rootId - 1].opcode,
            static_cast<uint8_t>(ShapeOp::Cylinder));
}

TEST(IR, SmoothUnion) {
  auto r = compileIR(
      "s0 = sphere(r=1.0)\n"
      "s1 = box(x=1.0, y=1.0, z=1.0)\n"
      "s2 = smooth_union(s0, s1, k=0.3)\n"
      "return s2");
  ASSERT_TRUE(r.ok) << r.error;
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  EXPECT_EQ(headers[r.dag.rootId - 1].opcode,
            static_cast<uint8_t>(ShapeOp::SmoothUnion));
}
