#include "kernel/flat_ir.h"
#include <gtest/gtest.h>

using namespace kernel;

TEST(FlatIR, StructSizes) {
  EXPECT_EQ(sizeof(FlatTransform), 40u) << "10 floats";
  EXPECT_EQ(sizeof(FlatSphere), 4u) << "1 float";
  EXPECT_EQ(sizeof(FlatBox), 12u) << "3 floats";
  EXPECT_EQ(sizeof(FlatCylinder), 8u) << "2 floats";
  EXPECT_EQ(sizeof(FlatInstr), 16u) << "4 uint32_t";
}

TEST(FlatIR, DefaultValues) {
  FlatTransform t;
  EXPECT_FLOAT_EQ(t.tx, 0.0f);
  EXPECT_FLOAT_EQ(t.ty, 0.0f);
  EXPECT_FLOAT_EQ(t.tz, 0.0f);
  EXPECT_FLOAT_EQ(t.sx, 1.0f);
  EXPECT_FLOAT_EQ(t.sy, 1.0f);
  EXPECT_FLOAT_EQ(t.sz, 1.0f);
  EXPECT_FLOAT_EQ(t.qx, 0.0f);
  EXPECT_FLOAT_EQ(t.qy, 0.0f);
  EXPECT_FLOAT_EQ(t.qz, 0.0f);
  EXPECT_FLOAT_EQ(t.qw, 1.0f);

  FlatSphere s;
  EXPECT_FLOAT_EQ(s.r, 1.0f);

  FlatBox b;
  EXPECT_FLOAT_EQ(b.hx, 1.0f);
  EXPECT_FLOAT_EQ(b.hy, 1.0f);
  EXPECT_FLOAT_EQ(b.hz, 1.0f);

  FlatInstr i;
  EXPECT_EQ(i.op, 0u);
  EXPECT_EQ(i.arg0, 0u);
  EXPECT_EQ(i.arg1, 0u);
  EXPECT_EQ(i.constIdx, 0u);

  FlatCylinder c;
  EXPECT_FLOAT_EQ(c.r, 1.0f);
  EXPECT_FLOAT_EQ(c.h, 1.0f);

  FlatIR ir;
  EXPECT_TRUE(ir.instrs.empty());
  EXPECT_TRUE(ir.transforms.empty());
  EXPECT_TRUE(ir.spheres.empty());
  EXPECT_TRUE(ir.boxes.empty());
  EXPECT_TRUE(ir.cylinders.empty());
  EXPECT_TRUE(ir.smoothKs.empty());
  EXPECT_EQ(ir.rootTemp, 0u);
}

TEST(FlatIR, FlatOpValues) {
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::EvalSphere), 0u);
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::EvalBox), 1u);
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::CsgUnion), 2u);
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::CsgIntersect), 3u);
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::CsgSubtract), 4u);
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::EvalCylinder), 5u);
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::CsgSmoothUnion), 6u);
}
