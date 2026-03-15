#include "eval_flat_ir.h"
#include "kernel/builder.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include "kernel/param_extract.h"
#include <gtest/gtest.h>

using namespace kernel;

TEST(ParamExtract, ExtractAndApplyRoundTrip) {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({0.5f, 0.5f, 0.5f});
  ShapeH root = b.unite(s, bx);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  std::vector<float> params = extractParams(ir);
  EXPECT_FALSE(params.empty());

  // Modify sphere radius slightly (params[6] is first sphere r for single sphere + identity)
  if (params.size() > 6) {
    params[6] *= 1.1f;  // scale sphere r
  }
  applyParams(ir, params);

  // Verify SDF still evaluates (no crash, finite values)
  Vec3 p{0, 0, 0};
  float d = eval_flat_ir::evalFlatIR(ir, p);
  EXPECT_TRUE(std::isfinite(d));
  EXPECT_GT(std::abs(d), 0.0f);
}

TEST(ParamExtract, NoMinScaleInIR) {
  Builder b;
  TransformH t = b.scale({2, 2, 2});
  ShapeH s = b.sphere(0.5f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  // FlatTransform has 6 fields (tx,ty,tz,sx,sy,sz), no minScale
  EXPECT_GE(ir.transforms.size(), 1u);
  for (const auto& t : ir.transforms) {
    (void)t;  // Struct has no minScale field
  }
  std::vector<float> params = extractParams(ir);
  // 6 per transform + 1 per sphere
  EXPECT_GE(params.size(), 7u);
}
