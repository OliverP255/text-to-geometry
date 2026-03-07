#include "frontend/ir.h"
#include "kernel/node.h"
#include <gtest/gtest.h>

using namespace frontend;
using namespace kernel;

//make sure single sphere is compiled correctly
TEST(IR, SingleSphere) {
  auto r = compileIR("%0 = sphere(1.0)\nreturn %0");
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
      "%0 = sphere(1.0)\n"
      "%1 = box(1.0, 1.0, 1.0)\n"
      "%2 = unite(%0, %1)\n"
      "return %2");
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
      "%0 = sphere(0.5)\n"
      "%1 = translate(2.0, 0.0, 0.0)\n"
      "%2 = apply(%1, %0)\n"
      "return %2");
  ASSERT_TRUE(r.ok) << r.error;
  EXPECT_NE(r.dag.rootId, 0u);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  const NodeHeader& root = headers[r.dag.rootId - 1];
  EXPECT_EQ(root.opcode, static_cast<uint8_t>(ShapeOp::ApplyTransform));
}

TEST(IR, Subtract) {
  auto r = compileIR(
      "%0 = sphere(1.0)\n"
      "%1 = box(0.5, 0.5, 0.5)\n"
      "%2 = subtract(%0, %1)\n"
      "return %2");
  ASSERT_TRUE(r.ok) << r.error;
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  const NodeHeader& root = headers[r.dag.rootId - 1];
  EXPECT_EQ(root.opcode, static_cast<uint8_t>(ShapeOp::Subtract));
}

TEST(IR, ExplicitReturn) {
  auto r = compileIR(
      "%0 = sphere(1.0)\n"
      "%1 = box(1.0, 1.0, 1.0)\n"
      "%2 = unite(%0, %1)\n"
      "return %2");
  ASSERT_TRUE(r.ok) << r.error;
  EXPECT_NE(r.dag.rootId, 0u);
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  const NodeHeader& root = headers[r.dag.rootId - 1];
  EXPECT_EQ(root.opcode, static_cast<uint8_t>(ShapeOp::Union));
}

TEST(IRParseErrors, RequireReturn) {
  auto r = compileIR(
      "%0 = sphere(1.0)\n"
      "%1 = box(1.0, 1.0, 1.0)\n"
      "%2 = unite(%0, %1)");
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.error.find("return"), std::string::npos);
}

TEST(IR, NaryUnite) {
  auto r = compileIR(
      "%0 = sphere(1.0)\n"
      "%1 = box(1.0, 1.0, 1.0)\n"
      "%2 = plane(0.0, 1.0, 0.0, 0.0)\n"
      "%3 = unite(%0, %1, %2)\n"
      "return %3");
  ASSERT_TRUE(r.ok) << r.error;
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  const NodeHeader& root = headers[r.dag.rootId - 1];
  EXPECT_EQ(root.opcode, static_cast<uint8_t>(ShapeOp::Union));
}

TEST(IR, Plane) {
  auto r = compileIR("%0 = plane(0.0, 1.0, 0.0, 0.0)\nreturn %0");
  ASSERT_TRUE(r.ok) << r.error;
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  EXPECT_EQ(headers[r.dag.rootId - 1].opcode,
            static_cast<uint8_t>(ShapeOp::Plane));
}

TEST(IR, Scale) {
  auto r = compileIR(
      "%0 = box(1.0, 1.0, 1.0)\n"
      "%1 = scale(2.0, 2.0, 2.0)\n"
      "%2 = apply(%1, %0)\n"
      "return %2");
  ASSERT_TRUE(r.ok) << r.error;
}

TEST(IRParseErrors, UnknownOp) {
  auto r = compileIR("%0 = foo(1.0)");
  EXPECT_FALSE(r.ok);
  EXPECT_FALSE(r.error.empty());
  EXPECT_NE(r.error.find("unknown"), std::string::npos);
}

TEST(IRParseErrors, UndefinedRef) {
  auto r = compileIR("%0 = unite(%1, %2)\nreturn %0");
  EXPECT_FALSE(r.ok);
  EXPECT_FALSE(r.error.empty());
}

TEST(IRParseErrors, ApplyTypeMismatch) {
  auto r = compileIR(
      "%0 = sphere(1.0)\n"
      "%1 = apply(%0, %0)\n"
      "return %1");
  EXPECT_FALSE(r.ok);
  EXPECT_FALSE(r.error.empty());
}

TEST(IRParseErrors, Lex) {
  auto r = compileIR("%0 = sphere(1.0)\n%x = box(1,1,1)");
  EXPECT_FALSE(r.ok);
  EXPECT_FALSE(r.error.empty());
  EXPECT_NE(r.error.find("digit"), std::string::npos);
}

TEST(IRParseErrors, TrailingContent) {
  auto r = compileIR(
      "%0 = sphere(1.0)\n"
      "return %0\n"
      "x");
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.error.find("unexpected"), std::string::npos);
}

TEST(IR, NegativeNum) {
  auto r = compileIR(
      "%0 = plane(0.0, -1.0, 0.0, 0.0)\n"
      "return %0");
  ASSERT_TRUE(r.ok) << r.error;
  const NodeHeader* headers =
      reinterpret_cast<const NodeHeader*>(r.dag.headers);
  EXPECT_EQ(headers[r.dag.rootId - 1].opcode,
            static_cast<uint8_t>(ShapeOp::Plane));
}

TEST(IRParseErrors, InfRejected) {
  auto r = compileIR("%0 = sphere(1e99)\nreturn %0");
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.error.find("invalid"), std::string::npos);
}

TEST(IRParseErrors, NanRejected) {
  auto r = compileIR("%0 = sphere(nan)\nreturn %0");
  EXPECT_FALSE(r.ok);
  EXPECT_NE(r.error.find("number"), std::string::npos);
}
