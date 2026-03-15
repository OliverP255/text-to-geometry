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

  // 2 transforms: identity + translate(1,2,3)
  EXPECT_EQ(packed.transforms.size(), 2u * 8u);

  // Identity: tx,ty,tz,0, sx,sy,sz,minScale
  EXPECT_FLOAT_EQ(packed.transforms[0], 0.0f);
  EXPECT_FLOAT_EQ(packed.transforms[1], 0.0f);
  EXPECT_FLOAT_EQ(packed.transforms[2], 0.0f);
  EXPECT_FLOAT_EQ(packed.transforms[3], 0.0f);
  EXPECT_FLOAT_EQ(packed.transforms[4], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[5], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[6], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[7], 1.0f);

  // Translate(1,2,3): tx=1,ty=2,tz=3, pad, sx=1,sy=1,sz=1, minScale=1
  EXPECT_FLOAT_EQ(packed.transforms[8], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[9], 2.0f);
  EXPECT_FLOAT_EQ(packed.transforms[10], 3.0f);
  EXPECT_FLOAT_EQ(packed.transforms[11], 0.0f);
  EXPECT_FLOAT_EQ(packed.transforms[12], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[13], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[14], 1.0f);
  EXPECT_FLOAT_EQ(packed.transforms[15], 1.0f);
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
  size_t idx = 8;  // second transform
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

TEST(PackForWebGPU, PlaneLayout) {
  Builder b;
  ShapeH root = b.plane({0, 1, 0}, 0.5f);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  PackedFlatIR packed = packForWebGPU(ir);

  EXPECT_EQ(packed.planes.size(), 4u);
  EXPECT_FLOAT_EQ(packed.planes[0], 0.0f);
  EXPECT_FLOAT_EQ(packed.planes[1], 1.0f);
  EXPECT_FLOAT_EQ(packed.planes[2], 0.0f);
  EXPECT_FLOAT_EQ(packed.planes[3], 0.5f);
}
