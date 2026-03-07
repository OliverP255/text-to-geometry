#include "kernel/builder.h"
#include "kernel/codegen_cuda.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include "kernel/node.h"
#include <cmath>
#include <gtest/gtest.h>
#include <string>

using namespace kernel;

// ---------------------------------------------------------------------------
// Codegen string validation tests (no CUDA required)
// ---------------------------------------------------------------------------

static FlatIR makeSphereIR() {
  Builder b;
  ShapeH root = b.sphere(1.0f);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  return lower(dag);
}

static FlatIR makeUnionIR() {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({0.5f, 0.5f, 0.5f});
  ShapeH root = b.unite(s, bx);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  return lower(dag);
}

static FlatIR makeTranslatedSphereIR() {
  Builder b;
  TransformH t = b.translate({1, 0, 0});
  ShapeH s = b.sphere(0.5f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  return lower(dag);
}

static FlatIR makeSubtractIR() {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({0.5f, 0.5f, 0.5f});
  ShapeH root = b.subtract(s, bx);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  return lower(dag);
}

static FlatIR makePlaneIR() {
  Builder b;
  ShapeH root = b.plane({0, 1, 0}, 0);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  return lower(dag);
}

static FlatIR makeComplexIR() {
  Builder b;
  TransformH t0 = b.translate({1, 0, 0});
  TransformH t1 = b.scale({2, 2, 2});
  ShapeH s = b.sphere(0.5f);
  ShapeH inner = b.apply(t1, s);
  ShapeH outer = b.apply(t0, inner);
  ShapeH bx = b.box({1, 1, 1});
  ShapeH root = b.unite(outer, bx);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  return lower(dag);
}

TEST(CodegenCuda, SphereContainsSdfFunction) {
  FlatIR ir = makeSphereIR();
  std::string src = codegenCuda(ir);
  EXPECT_NE(src.find("__device__"), std::string::npos);
  EXPECT_NE(src.find("float sdf(float3 p)"), std::string::npos);
  EXPECT_NE(src.find("sdfSphere"), std::string::npos);
  EXPECT_NE(src.find("c_transforms"), std::string::npos);
  EXPECT_NE(src.find("c_spheres"), std::string::npos);
  EXPECT_NE(src.find("evalPointsKernel"), std::string::npos);
  EXPECT_NE(src.find("raymarchKernel"), std::string::npos);
}

TEST(CodegenCuda, UnionContainsCsgOps) {
  FlatIR ir = makeUnionIR();
  std::string src = codegenCuda(ir);
  EXPECT_NE(src.find("fminf(t"), std::string::npos);
  EXPECT_NE(src.find("c_spheres"), std::string::npos);
  EXPECT_NE(src.find("c_boxes"), std::string::npos);
}

TEST(CodegenCuda, SubtractContainsNegation) {
  FlatIR ir = makeSubtractIR();
  std::string src = codegenCuda(ir);
  EXPECT_NE(src.find("fmaxf(t"), std::string::npos);
  EXPECT_NE(src.find(", -t"), std::string::npos);
}

TEST(CodegenCuda, PlaneContainsPlaneOps) {
  FlatIR ir = makePlaneIR();
  std::string src = codegenCuda(ir);
  EXPECT_NE(src.find("sdfPlane"), std::string::npos);
  EXPECT_NE(src.find("c_planes"), std::string::npos);
}

TEST(CodegenCuda, TransformedSphereUsesNonIdentityTransform) {
  FlatIR ir = makeTranslatedSphereIR();
  std::string src = codegenCuda(ir);
  EXPECT_NE(src.find("xformPoint(p, 1)"), std::string::npos);
}

TEST(CodegenCuda, ComplexSceneHasMultipleTemps) {
  FlatIR ir = makeComplexIR();
  std::string src = codegenCuda(ir);
  EXPECT_NE(src.find("float t0"), std::string::npos);
  EXPECT_NE(src.find("float t1"), std::string::npos);
  EXPECT_NE(src.find("float t2"), std::string::npos);
}

TEST(CodegenCuda, EmptyIRProducesValidSource) {
  FlatIR ir;
  ir.rootTemp = DistTemp{0};
  std::string src = codegenCuda(ir);
  EXPECT_NE(src.find("return 1e10f"), std::string::npos);
}

TEST(CodegenCuda, ConstantPoolTransforms7Floats) {
  FlatIR ir = makeTranslatedSphereIR();
  CudaConstantPool pool = buildConstantPool(ir);

  ASSERT_EQ(ir.transforms.size(), 12u);  // 2 transforms * 6 floats
  ASSERT_EQ(pool.transforms.size(), 14u);  // 2 transforms * 7 floats

  EXPECT_FLOAT_EQ(pool.transforms[0], 0.f);  // identity tx
  EXPECT_FLOAT_EQ(pool.transforms[1], 0.f);  // identity ty
  EXPECT_FLOAT_EQ(pool.transforms[2], 0.f);  // identity tz
  EXPECT_FLOAT_EQ(pool.transforms[3], 1.f);  // identity sx
  EXPECT_FLOAT_EQ(pool.transforms[4], 1.f);  // identity sy
  EXPECT_FLOAT_EQ(pool.transforms[5], 1.f);  // identity sz
  EXPECT_FLOAT_EQ(pool.transforms[6], 1.f);  // identity minScale

  EXPECT_FLOAT_EQ(pool.transforms[7], 1.f);   // translate tx
  EXPECT_FLOAT_EQ(pool.transforms[8], 0.f);   // translate ty
  EXPECT_FLOAT_EQ(pool.transforms[9], 0.f);   // translate tz
  EXPECT_FLOAT_EQ(pool.transforms[10], 1.f);  // translate sx
  EXPECT_FLOAT_EQ(pool.transforms[11], 1.f);  // translate sy
  EXPECT_FLOAT_EQ(pool.transforms[12], 1.f);  // translate sz
  EXPECT_FLOAT_EQ(pool.transforms[13], 1.f);  // translate minScale
}

TEST(CodegenCuda, ConstantPoolMinScaleComputed) {
  Builder b;
  TransformH t = b.scale({2, 3, 4});
  ShapeH s = b.sphere(1.0f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  FlatIR ir = lower(dag);

  CudaConstantPool pool = buildConstantPool(ir);

  size_t numTransforms = pool.transforms.size() / 7;
  ASSERT_GE(numTransforms, 2u);
  EXPECT_FLOAT_EQ(pool.transforms[1 * 7 + 6], 2.f);
}

TEST(CodegenCuda, ConstantPoolPreservesData) {
  FlatIR ir = makeUnionIR();
  CudaConstantPool pool = buildConstantPool(ir);

  EXPECT_EQ(pool.spheres.size(), ir.spheres.size());
  EXPECT_EQ(pool.boxes.size(), ir.boxes.size());
  EXPECT_EQ(pool.planes.size(), ir.planes.size());

  for (size_t i = 0; i < pool.spheres.size(); i++)
    EXPECT_FLOAT_EQ(pool.spheres[i], ir.spheres[i]);
  for (size_t i = 0; i < pool.boxes.size(); i++)
    EXPECT_FLOAT_EQ(pool.boxes[i], ir.boxes[i]);
}

TEST(CodegenCuda, UsesGpuMathIntrinsics) {
  FlatIR ir = makeSphereIR();
  std::string src = codegenCuda(ir);
  EXPECT_NE(src.find("norm3df"), std::string::npos);
  EXPECT_NE(src.find("fabsf"), std::string::npos);
  EXPECT_NE(src.find("fmaxf"), std::string::npos);
  EXPECT_NE(src.find("fminf"), std::string::npos);
}

TEST(CodegenCuda, RaymarchKernelHasLaunchBounds) {
  FlatIR ir = makeSphereIR();
  std::string src = codegenCuda(ir);
  EXPECT_NE(src.find("__launch_bounds__"), std::string::npos);
}

TEST(CodegenCuda, RaymarchKernelHasPragmaUnroll) {
  FlatIR ir = makeSphereIR();
  std::string src = codegenCuda(ir);
  EXPECT_NE(src.find("#pragma unroll"), std::string::npos);
}

TEST(CodegenCuda, RaymarchKernelTakesMaxStepsParam) {
  FlatIR ir = makeSphereIR();
  std::string src = codegenCuda(ir);
  EXPECT_NE(src.find("int maxSteps"), std::string::npos);
  EXPECT_NE(src.find("float maxDist"), std::string::npos);
  EXPECT_NE(src.find("float epsilon"), std::string::npos);
}

TEST(CodegenCuda, ConstantArraySizesMatchIR) {
  FlatIR ir = makeComplexIR();
  std::string src = codegenCuda(ir);

  size_t numTransforms = ir.transforms.size() / 6;
  size_t numSpheres = ir.spheres.size();
  size_t numBoxes = ir.boxes.size() / 3;

  std::string expectedTransforms =
      "c_transforms[" + std::to_string(numTransforms * 7) + "]";
  std::string expectedSpheres =
      "c_spheres[" + std::to_string(numSpheres) + "]";
  std::string expectedBoxes =
      "c_boxes[" + std::to_string(numBoxes * 3) + "]";

  EXPECT_NE(src.find(expectedTransforms), std::string::npos);
  EXPECT_NE(src.find(expectedSpheres), std::string::npos);
  EXPECT_NE(src.find(expectedBoxes), std::string::npos);
}
