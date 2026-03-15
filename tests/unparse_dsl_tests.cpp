#include "eval_flat_ir.h"
#include "frontend/ir.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include "kernel/optimise.h"
#include "kernel/unparse_dsl.h"
#include <gtest/gtest.h>
#include <string>

using namespace kernel;
using namespace frontend;

static FlatIR compileAndLower(const std::string& dsl) {
  auto result = compileIR(dsl.c_str());
  EXPECT_TRUE(result.ok) << "Compile failed: " << result.error;
  auto opt = optimise(result.dag);
  return lower(opt.view);
}

TEST(UnparseDSL, EmptyFlatIR) {
  FlatIR ir;
  std::string out = unparseDSL(ir);
  EXPECT_TRUE(out.empty());
}

TEST(UnparseDSL, SingleSphereRoundTrip) {
  std::string dsl = "s0 = sphere(r=1.0)\nreturn s0";
  FlatIR ir = compileAndLower(dsl);
  std::string unparsed = unparseDSL(ir);
  EXPECT_FALSE(unparsed.empty());

  FlatIR ir2 = compileAndLower(unparsed);
  EXPECT_EQ(ir.instrs.size(), ir2.instrs.size());
  EXPECT_EQ(ir.instrs[0].op, ir2.instrs[0].op);
  EXPECT_EQ(ir.rootTemp, ir2.rootTemp);
  EXPECT_EQ(ir.spheres.size(), ir2.spheres.size());
  EXPECT_FLOAT_EQ(ir.spheres[0].r, ir2.spheres[0].r);
}

TEST(UnparseDSL, UnionRoundTrip) {
  std::string dsl =
      "s0 = sphere(r=1.0)\n"
      "s1 = box(x=0.5, y=0.5, z=0.5)\n"
      "s2 = union(s0, s1)\n"
      "return s2";
  FlatIR ir = compileAndLower(dsl);
  std::string unparsed = unparseDSL(ir);
  EXPECT_FALSE(unparsed.empty());

  FlatIR ir2 = compileAndLower(unparsed);
  EXPECT_EQ(ir.instrs.size(), ir2.instrs.size());
  EXPECT_EQ(ir.rootTemp, ir2.rootTemp);
  for (size_t i = 0; i < ir.instrs.size(); ++i) {
    EXPECT_EQ(static_cast<int>(ir.instrs[i].op),
              static_cast<int>(ir2.instrs[i].op));
  }
}

TEST(UnparseDSL, TranslateAndApplyRoundTrip) {
  std::string dsl =
      "s0 = sphere(r=0.5)\n"
      "t0 = translate(x=2.0, y=0.0, z=0.0)\n"
      "s1 = apply(t0, s0)\n"
      "return s1";
  FlatIR ir = compileAndLower(dsl);
  std::string unparsed = unparseDSL(ir);
  EXPECT_FALSE(unparsed.empty());

  FlatIR ir2 = compileAndLower(unparsed);
  EXPECT_EQ(ir.instrs.size(), ir2.instrs.size());
  EXPECT_EQ(ir.rootTemp, ir2.rootTemp);
}

TEST(UnparseDSL, UnparsedDSLEvaluatesCorrectly) {
  std::string dsl = "s0 = sphere(r=1.0)\nreturn s0";
  FlatIR ir = compileAndLower(dsl);
  std::string unparsed = unparseDSL(ir);
  FlatIR ir2 = compileAndLower(unparsed);

  kernel::Vec3 origin = {0, 0, 0};
  float d1 = eval_flat_ir::evalFlatIRImpl(ir, origin);
  float d2 = eval_flat_ir::evalFlatIRImpl(ir2, origin);
  EXPECT_FLOAT_EQ(d1, d2);
}
