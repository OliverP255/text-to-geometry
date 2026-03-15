#include "kernel/flat_ir.h"
#include <gtest/gtest.h>

using namespace kernel;

TEST(FlatIR, StructSizes) {
  EXPECT_EQ(sizeof(FlatTransform), 24u) << "6 floats";
  EXPECT_EQ(sizeof(FlatSphere), 4u) << "1 float";
  EXPECT_EQ(sizeof(FlatBox), 12u) << "3 floats";
  EXPECT_EQ(sizeof(FlatPlane), 16u) << "4 floats";
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

  FlatSphere s;
  EXPECT_FLOAT_EQ(s.r, 1.0f);

  FlatBox b;
  EXPECT_FLOAT_EQ(b.hx, 1.0f);
  EXPECT_FLOAT_EQ(b.hy, 1.0f);
  EXPECT_FLOAT_EQ(b.hz, 1.0f);

  FlatPlane p;
  EXPECT_FLOAT_EQ(p.nx, 0.0f);
  EXPECT_FLOAT_EQ(p.ny, 1.0f);
  EXPECT_FLOAT_EQ(p.nz, 0.0f);
  EXPECT_FLOAT_EQ(p.d, 0.0f);

  FlatInstr i;
  EXPECT_EQ(i.op, 0u);
  EXPECT_EQ(i.arg0, 0u);
  EXPECT_EQ(i.arg1, 0u);
  EXPECT_EQ(i.constIdx, 0u);

  FlatIR ir;
  EXPECT_TRUE(ir.instrs.empty());
  EXPECT_TRUE(ir.transforms.empty());
  EXPECT_TRUE(ir.spheres.empty());
  EXPECT_TRUE(ir.boxes.empty());
  EXPECT_TRUE(ir.planes.empty());
  EXPECT_EQ(ir.rootTemp, 0u);
}

TEST(FlatIR, FlatOpValues) {
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::EvalSphere), 0u);
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::EvalBox), 1u);
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::EvalPlane), 2u);
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::CsgUnion), 3u);
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::CsgIntersect), 4u);
  EXPECT_EQ(static_cast<uint32_t>(FlatOp::CsgSubtract), 5u);
}
