#include "eval_dag.h"
#include "eval_flat_ir.h"
#include "frontend/ir.h"
#include "kernel/builder.h"
#include "kernel/cuda_renderer.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include "kernel/node.h"
#include <cmath>
#include <gtest/gtest.h>
#include <vector>

using namespace kernel;

// ---------------------------------------------------------------------------
// FlatIR helpers (reuse pattern from codegen_cuda_tests)
// ---------------------------------------------------------------------------

static FlatIR makeEmptyIR() {
  FlatIR ir;
  ir.rootTemp = DistTemp{0};
  return ir;
}

static FlatIR makeSphereIR() {
  Builder b;
  ShapeH root = b.sphere(1.0f);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  return lower(dag);
}

static FlatIR makeSphereIR(float r) {
  Builder b;
  ShapeH root = b.sphere(r);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  return lower(dag);
}

static FlatIR makeBoxIR() {
  Builder b;
  ShapeH root = b.box({1.0f, 1.0f, 1.0f});
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

static FlatIR makeUnionIR() {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({0.5f, 0.5f, 0.5f});
  ShapeH root = b.unite(s, bx);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  return lower(dag);
}

static FlatIR makeIntersectIR() {
  Builder b;
  ShapeH s = b.sphere(1.0f);
  ShapeH bx = b.box({1.0f, 1.0f, 1.0f});
  ShapeH root = b.intersect(s, bx);
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

static FlatIR makeTranslatedSphereIR() {
  Builder b;
  TransformH t = b.translate({1, 0, 0});
  ShapeH s = b.sphere(0.5f);
  ShapeH root = b.apply(t, s);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  return lower(dag);
}

static FlatIR makeScaledSphereIR() {
  Builder b;
  TransformH t = b.scale({2, 2, 2});
  ShapeH s = b.sphere(0.5f);
  ShapeH root = b.apply(t, s);
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

// ---------------------------------------------------------------------------
// SetScene tests (Stage 4 - NVRTC compile)
// ---------------------------------------------------------------------------

TEST(SetScene, EmptyIR) {
  FlatIR ir = makeEmptyIR();
  CudaRenderer renderer;
  EXPECT_NO_THROW(renderer.setScene(ir));
}

TEST(SetScene, Sphere) {
  FlatIR ir = makeSphereIR();
  CudaRenderer renderer;
  renderer.setScene(ir);
  EXPECT_TRUE(renderer.isReady());
}

TEST(SetScene, Box) {
  FlatIR ir = makeBoxIR();
  CudaRenderer renderer;
  renderer.setScene(ir);
  EXPECT_TRUE(renderer.isReady());
}

TEST(SetScene, Plane) {
  FlatIR ir = makePlaneIR();
  CudaRenderer renderer;
  renderer.setScene(ir);
  EXPECT_TRUE(renderer.isReady());
}

TEST(SetScene, Union) {
  FlatIR ir = makeUnionIR();
  CudaRenderer renderer;
  renderer.setScene(ir);
  EXPECT_TRUE(renderer.isReady());
}

TEST(SetScene, Intersect) {
  FlatIR ir = makeIntersectIR();
  CudaRenderer renderer;
  renderer.setScene(ir);
  EXPECT_TRUE(renderer.isReady());
}

TEST(SetScene, Subtract) {
  FlatIR ir = makeSubtractIR();
  CudaRenderer renderer;
  renderer.setScene(ir);
  EXPECT_TRUE(renderer.isReady());
}

TEST(SetScene, Translate) {
  FlatIR ir = makeTranslatedSphereIR();
  CudaRenderer renderer;
  renderer.setScene(ir);
  EXPECT_TRUE(renderer.isReady());
}

TEST(SetScene, Scale) {
  FlatIR ir = makeScaledSphereIR();
  CudaRenderer renderer;
  renderer.setScene(ir);
  EXPECT_TRUE(renderer.isReady());
}

TEST(SetScene, Complex) {
  FlatIR ir = makeComplexIR();
  CudaRenderer renderer;
  renderer.setScene(ir);
  EXPECT_TRUE(renderer.isReady());
}

// ---------------------------------------------------------------------------
// EvalPoints tests (Stage 5 - GPU vs CPU)
// ---------------------------------------------------------------------------

static const Vec3 kSamplePoints[] = {
    {0, 0, 0},       {1, 0, 0},       {0, 1, 0},       {0, 0, 1},
    {-1, 0, 0},      {0.5f, 0.5f, 0.5f}, {2, 0, 0},    {0, 0, -1},
    {0.3f, -0.3f, 0.2f},
};
static constexpr int kNumSamplePoints =
    sizeof(kSamplePoints) / sizeof(kSamplePoints[0]);

TEST(EvalPoints, SphereMatchesCPU) {
  FlatIR ir = makeSphereIR();
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<float> points(kNumSamplePoints * 3);
  for (int i = 0; i < kNumSamplePoints; i++) {
    points[i * 3 + 0] = kSamplePoints[i].x;
    points[i * 3 + 1] = kSamplePoints[i].y;
    points[i * 3 + 2] = kSamplePoints[i].z;
  }

  std::vector<float> gpuOut(kNumSamplePoints);
  renderer.evalPoints(points.data(), gpuOut.data(), kNumSamplePoints);

  for (int i = 0; i < kNumSamplePoints; i++) {
    float cpu = eval_flat_ir::evalFlatIR(ir, kSamplePoints[i]);
    EXPECT_NEAR(gpuOut[i], cpu, 1e-3f)
        << "at point (" << kSamplePoints[i].x << "," << kSamplePoints[i].y
        << "," << kSamplePoints[i].z << ")";
  }
}

TEST(EvalPoints, BoxMatchesCPU) {
  FlatIR ir = makeBoxIR();
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<float> points(kNumSamplePoints * 3);
  for (int i = 0; i < kNumSamplePoints; i++) {
    points[i * 3 + 0] = kSamplePoints[i].x;
    points[i * 3 + 1] = kSamplePoints[i].y;
    points[i * 3 + 2] = kSamplePoints[i].z;
  }

  std::vector<float> gpuOut(kNumSamplePoints);
  renderer.evalPoints(points.data(), gpuOut.data(), kNumSamplePoints);

  for (int i = 0; i < kNumSamplePoints; i++) {
    float cpu = eval_flat_ir::evalFlatIR(ir, kSamplePoints[i]);
    EXPECT_NEAR(gpuOut[i], cpu, 1e-3f)
        << "at point (" << kSamplePoints[i].x << "," << kSamplePoints[i].y
        << "," << kSamplePoints[i].z << ")";
  }
}

TEST(EvalPoints, UnionMatchesCPU) {
  FlatIR ir = makeUnionIR();
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<float> points(kNumSamplePoints * 3);
  for (int i = 0; i < kNumSamplePoints; i++) {
    points[i * 3 + 0] = kSamplePoints[i].x;
    points[i * 3 + 1] = kSamplePoints[i].y;
    points[i * 3 + 2] = kSamplePoints[i].z;
  }

  std::vector<float> gpuOut(kNumSamplePoints);
  renderer.evalPoints(points.data(), gpuOut.data(), kNumSamplePoints);

  for (int i = 0; i < kNumSamplePoints; i++) {
    float cpu = eval_flat_ir::evalFlatIR(ir, kSamplePoints[i]);
    EXPECT_NEAR(gpuOut[i], cpu, 1e-3f)
        << "at point (" << kSamplePoints[i].x << "," << kSamplePoints[i].y
        << "," << kSamplePoints[i].z << ")";
  }
}

TEST(EvalPoints, TranslatedMatchesCPU) {
  FlatIR ir = makeTranslatedSphereIR();
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<float> points(kNumSamplePoints * 3);
  for (int i = 0; i < kNumSamplePoints; i++) {
    points[i * 3 + 0] = kSamplePoints[i].x;
    points[i * 3 + 1] = kSamplePoints[i].y;
    points[i * 3 + 2] = kSamplePoints[i].z;
  }

  std::vector<float> gpuOut(kNumSamplePoints);
  renderer.evalPoints(points.data(), gpuOut.data(), kNumSamplePoints);

  for (int i = 0; i < kNumSamplePoints; i++) {
    float cpu = eval_flat_ir::evalFlatIR(ir, kSamplePoints[i]);
    EXPECT_NEAR(gpuOut[i], cpu, 1e-3f)
        << "at point (" << kSamplePoints[i].x << "," << kSamplePoints[i].y
        << "," << kSamplePoints[i].z << ")";
  }
}

TEST(EvalPoints, InsideSphereNegative) {
  FlatIR ir = makeSphereIR(1.0f);
  CudaRenderer renderer;
  renderer.setScene(ir);

  float points[3] = {0, 0, 0};
  float out;
  renderer.evalPoints(points, &out, 1);
  EXPECT_LT(out, 0.f) << "point (0,0,0) is inside sphere(1), SDF should be negative";
}

TEST(EvalPoints, OutsideSpherePositive) {
  FlatIR ir = makeSphereIR(1.0f);
  CudaRenderer renderer;
  renderer.setScene(ir);

  float points[3] = {2, 0, 0};
  float out;
  renderer.evalPoints(points, &out, 1);
  EXPECT_GT(out, 0.f) << "point (2,0,0) is outside sphere(1), SDF should be positive";
}

// ---------------------------------------------------------------------------
// Render tests (Stage 6 - Raymarch)
// ---------------------------------------------------------------------------

static constexpr int kRenderW = 64;
static constexpr int kRenderH = 64;
static constexpr unsigned char kSkyR = 30;
static constexpr unsigned char kSkyG = 30;
static constexpr unsigned char kSkyB = 40;
static constexpr unsigned char kSkyA = 255;

TEST(Render, ProducesValidBuffer) {
  FlatIR ir = makeSphereIR();
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<unsigned char> framebuf(kRenderW * kRenderH * 4);
  renderer.render(kRenderW, kRenderH, 0, 0, 5, 0, 0, 0, framebuf.data());

  EXPECT_EQ(framebuf.size(), static_cast<size_t>(kRenderW * kRenderH * 4));
}

TEST(Render, CenterHitsSphere) {
  FlatIR ir = makeSphereIR(1.0f);
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<unsigned char> framebuf(kRenderW * kRenderH * 4);
  renderer.render(kRenderW, kRenderH, 0, 0, 5, 0, 0, 0, framebuf.data());

  int cx = kRenderW / 2;
  int cy = kRenderH / 2;
  int idx = (cy * kRenderW + cx) * 4;
  EXPECT_NE(framebuf[idx], kSkyR);
  EXPECT_NE(framebuf[idx + 1], kSkyG);
  EXPECT_NE(framebuf[idx + 2], kSkyB);
}

TEST(Render, CornersAreSky) {
  FlatIR ir = makeSphereIR(0.1f);
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<unsigned char> framebuf(kRenderW * kRenderH * 4);
  renderer.render(kRenderW, kRenderH, 0, 0, 5, 0, 0, 0, framebuf.data());

  auto checkCorner = [&](int x, int y) {
    int idx = (y * kRenderW + x) * 4;
    EXPECT_EQ(framebuf[idx], kSkyR) << "corner (" << x << "," << y << ") R";
    EXPECT_EQ(framebuf[idx + 1], kSkyG) << "corner (" << x << "," << y << ") G";
    EXPECT_EQ(framebuf[idx + 2], kSkyB) << "corner (" << x << "," << y << ") B";
    EXPECT_EQ(framebuf[idx + 3], kSkyA) << "corner (" << x << "," << y << ") A";
  };
  checkCorner(0, 0);
  checkCorner(kRenderW - 1, 0);
  checkCorner(0, kRenderH - 1);
  checkCorner(kRenderW - 1, kRenderH - 1);
}

TEST(Render, Alpha255) {
  FlatIR ir = makeSphereIR();
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<unsigned char> framebuf(kRenderW * kRenderH * 4);
  renderer.render(kRenderW, kRenderH, 0, 0, 5, 0, 0, 0, framebuf.data());

  for (size_t i = 3; i < framebuf.size(); i += 4) {
    EXPECT_EQ(framebuf[i], 255) << "pixel " << (i / 4) << " alpha";
  }
}

TEST(Render, Deterministic) {
  FlatIR ir = makeSphereIR();
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<unsigned char> buf1(kRenderW * kRenderH * 4);
  std::vector<unsigned char> buf2(kRenderW * kRenderH * 4);
  renderer.render(kRenderW, kRenderH, 0, 0, 5, 0, 0, 0, buf1.data());
  renderer.render(kRenderW, kRenderH, 0, 0, 5, 0, 0, 0, buf2.data());

  EXPECT_EQ(buf1, buf2) << "two renders should be byte-identical";
}

// ---------------------------------------------------------------------------
// Full pipeline tests (Stage 7)
// ---------------------------------------------------------------------------

static const char* kDefaultDSL = R"(
s0 = sphere(r=1.0)
s1 = box(x=0.5, y=0.5, z=0.5)
s2 = union(s0, s1)
return s2
)";

TEST(FullPipeline, DefaultScene) {
  auto result = frontend::compileIR(kDefaultDSL);
  ASSERT_TRUE(result.ok) << result.error;

  FlatIR ir = lower(result.dag);
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<unsigned char> framebuf(kRenderW * kRenderH * 4);
  EXPECT_NO_THROW(
      renderer.render(kRenderW, kRenderH, 0, 0, 5, 0, 0, 0, framebuf.data()));

  EXPECT_FALSE(framebuf.empty());
}

TEST(FullPipeline, SphereOnly) {
  const char* dsl = "s0 = sphere(r=1.0)\nreturn s0";
  auto result = frontend::compileIR(dsl);
  ASSERT_TRUE(result.ok) << result.error;

  FlatIR ir = lower(result.dag);
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<unsigned char> framebuf(kRenderW * kRenderH * 4);
  renderer.render(kRenderW, kRenderH, 0, 0, 5, 0, 0, 0, framebuf.data());

  int cx = kRenderW / 2;
  int cy = kRenderH / 2;
  int idx = (cy * kRenderW + cx) * 4;
  EXPECT_NE(framebuf[idx], kSkyR);
  EXPECT_NE(framebuf[idx + 1], kSkyG);
  EXPECT_NE(framebuf[idx + 2], kSkyB);
}

TEST(FullPipeline, Plane) {
  const char* dsl =
      "s0 = plane(nx=0.0, ny=1.0, nz=0.0, d=0.0)\nreturn s0";
  auto result = frontend::compileIR(dsl);
  ASSERT_TRUE(result.ok) << result.error;

  FlatIR ir = lower(result.dag);
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<unsigned char> framebuf(kRenderW * kRenderH * 4);
  EXPECT_NO_THROW(
      renderer.render(kRenderW, kRenderH, 0, 0, 5, 0, 0, 0, framebuf.data()));
}

TEST(FullPipeline, Subtract) {
  const char* dsl =
      "s0 = sphere(r=1.0)\n"
      "s1 = box(x=0.5, y=0.5, z=0.5)\n"
      "s2 = subtract(s0, s1)\n"
      "return s2";
  auto result = frontend::compileIR(dsl);
  ASSERT_TRUE(result.ok) << result.error;

  FlatIR ir = lower(result.dag);
  CudaRenderer renderer;
  renderer.setScene(ir);

  std::vector<unsigned char> framebuf(kRenderW * kRenderH * 4);
  renderer.render(kRenderW, kRenderH, 0, 0, 5, 0, 0, 0, framebuf.data());

  int cx = kRenderW / 2;
  int cy = kRenderH / 2;
  int idx = (cy * kRenderW + cx) * 4;
  unsigned char centerR = framebuf[idx];
  unsigned char centerG = framebuf[idx + 1];
  unsigned char centerB = framebuf[idx + 2];

  const char* unionDsl =
      "s0 = sphere(r=1.0)\n"
      "s1 = box(x=0.5, y=0.5, z=0.5)\n"
      "s2 = union(s0, s1)\n"
      "return s2";
  auto unionResult = frontend::compileIR(unionDsl);
  ASSERT_TRUE(unionResult.ok) << unionResult.error;
  FlatIR unionIr = lower(unionResult.dag);
  CudaRenderer unionRenderer;
  unionRenderer.setScene(unionIr);
  std::vector<unsigned char> unionBuf(kRenderW * kRenderH * 4);
  unionRenderer.render(kRenderW, kRenderH, 0, 0, 5, 0, 0, 0, unionBuf.data());

  unsigned char unionCenterR = unionBuf[idx];
  unsigned char unionCenterG = unionBuf[idx + 1];
  unsigned char unionCenterB = unionBuf[idx + 2];

  EXPECT_FALSE(centerR == unionCenterR && centerG == unionCenterG &&
               centerB == unionCenterB)
      << "subtract center pixel should differ from union";
}
