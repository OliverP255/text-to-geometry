#include "kernel/builder.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include "kernel/pack_for_webgpu.h"
#include <gtest/gtest.h>

using namespace kernel;

TEST(PackForWebGPU, TransformLayout) {
  Builder b;
  TransformH t = b.translate({1, 2, 3});
  ShapeH s = b.sphere(0.5f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  PackedFlatIR packed = packForWebGPU(ir);

  // 2 transforms: identity + translate(1,2,3), 12 floats each
  EXPECT_EQ(packed.transforms.size(), 2u * 12u);

  // Identity: tx,ty,tz,0, sx,sy,sz,minScale, qx,qy,qz,qw
  EXPECT_FLOAT_EQ(packed.transforms[0], 0.0f);
  EXPECT_FLOAT_EQ(packed.transforms[1], 0.0f);
  EXPECT_FLOAT_EQ(packed.transforms[2], 0.0f);
  EXPECT_FLOAT_EQ(packed.transforms[3], 0.0f);
  EXPECT_FLOAT_EQ(packed.transforms[4], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[5], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[6], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[7], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[8], 0.0f);   // qx
  EXPECT_FLOAT_EQ(packed.transforms[9], 0.0f);   // qy
  EXPECT_FLOAT_EQ(packed.transforms[10], 0.0f);  // qz
  EXPECT_FLOAT_EQ(packed.transforms[11], 1.0f);  // qw

  // Translate(1,2,3): tx=1,ty=2,tz=3, pad, sx=1,sy=1,sz=1, minScale=1, identity quat
  EXPECT_FLOAT_EQ(packed.transforms[12], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[13], 2.0f);
  EXPECT_FLOAT_EQ(packed.transforms[14], 3.0f);
  EXPECT_FLOAT_EQ(packed.transforms[15], 0.0f);
  EXPECT_FLOAT_EQ(packed.transforms[16], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[17], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[18], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[19], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[20], 0.0f);  // qx
  EXPECT_FLOAT_EQ(packed.transforms[21], 0.0f);  // qy
  EXPECT_FLOAT_EQ(packed.transforms[22], 0.0f);  // qz
  EXPECT_FLOAT_EQ(packed.transforms[23], 1.0f);  // qw
}

TEST(PackForWebGPU, MinScaleComputed) {
  Builder b;
  TransformH t = b.scale({2, 3, 4});
  ShapeH s = b.sphere(0.5f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  PackedFlatIR packed = packForWebGPU(ir);

  // Second transform has scale (2,3,4), minScale = 2
  size_t idx = 12;  // second transform (12 floats per)
  EXPECT_FLOAT_EQ(packed.transforms[idx + 4], 2.0f);
  EXPECT_FLOAT_EQ(packed.transforms[idx + 5], 3.0f);
  EXPECT_FLOAT_EQ(packed.transforms[idx + 6], 4.0f);
  EXPECT_FLOAT_EQ(packed.transforms[idx + 7], 2.0f);  // minScale
}

TEST(PackForWebGPU, SphereLayout) {
  Builder b;
  ShapeH root = b.sphere(1.5f);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  PackedFlatIR packed = packForWebGPU(ir);

  EXPECT_EQ(packed.spheres.size(), 4u);
  EXPECT_FLOAT_EQ(packed.spheres[0], 1.5f);
  EXPECT_FLOAT_EQ(packed.spheres[1], 0.0f);
  EXPECT_FLOAT_EQ(packed.spheres[2], 0.0f);
  EXPECT_FLOAT_EQ(packed.spheres[3], 0.0f);
}

TEST(PackForWebGPU, BoxLayout) {
  Builder b;
  ShapeH root = b.box({0.5f, 0.6f, 0.7f});
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  PackedFlatIR packed = packForWebGPU(ir);

  EXPECT_EQ(packed.boxes.size(), 4u);
  EXPECT_FLOAT_EQ(packed.boxes[0], 0.5f);
  EXPECT_FLOAT_EQ(packed.boxes[1], 0.6f);
  EXPECT_FLOAT_EQ(packed.boxes[2], 0.7f);
  EXPECT_FLOAT_EQ(packed.boxes[3], 0.0f);
}

TEST(PackForWebGPU, CylinderLayout) {
  Builder b;
  ShapeH root = b.cylinder(0.5f, 1.0f);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  PackedFlatIR packed = packForWebGPU(ir);

  EXPECT_EQ(packed.cylinders.size(), 4u);
  EXPECT_FLOAT_EQ(packed.cylinders[0], 0.5f);
  EXPECT_FLOAT_EQ(packed.cylinders[1], 1.0f);
  EXPECT_FLOAT_EQ(packed.cylinders[2], 0.0f);
  EXPECT_FLOAT_EQ(packed.cylinders[3], 0.0f);
}
