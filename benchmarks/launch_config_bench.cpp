#include "kernel/builder.h"
#include "kernel/cuda_renderer.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include "kernel/node.h"
#include <chrono>
#include <cstdio>
#include <vector>

using namespace kernel;

static FlatIR buildBenchScene() {
  Builder b;
  ShapeH s1 = b.sphere(1.0f);
  TransformH t1 = b.translate({2, 0, 0});
  ShapeH s2 = b.apply(t1, b.sphere(0.8f));
  TransformH t2 = b.translate({-2, 0, 0});
  ShapeH s3 = b.apply(t2, b.box({0.6f, 0.6f, 0.6f}));
  ShapeH u1 = b.unite(s1, s2);
  ShapeH u2 = b.unite(u1, s3);
  ShapeH pl = b.plane({0, 1, 0}, 1.5f);
  ShapeH root = b.subtract(u2, pl);
  FrozenDAG dag = {};
  b.freeze(root, dag);
  return lower(dag);
}

int main() {
  FlatIR ir = buildBenchScene();

  CudaRenderer renderer;
  renderer.setScene(ir);

  const int width = 1920;
  const int height = 1080;
  std::vector<unsigned char> framebuf(width * height * 4);

  struct Config {
    unsigned int bx, by;
  };
  Config configs[] = {
      {8, 8}, {16, 8}, {16, 16}, {32, 8}, {32, 16}, {32, 32},
  };

  const int warmupRuns = 3;
  const int benchRuns = 10;

  printf("Launch config benchmark: %dx%d render\n", width, height);
  printf("%-12s  %-10s  %-10s\n", "BlockDim", "Avg (ms)", "Min (ms)");
  printf("-------------------------------------------\n");

  for (const auto& cfg : configs) {
    LaunchConfig lc;
    lc.blockX = cfg.bx;
    lc.blockY = cfg.by;

    for (int i = 0; i < warmupRuns; i++) {
      renderer.render(width, height, 0, 0, 5, 0, 0, 0, framebuf.data(), lc);
    }

    double totalMs = 0;
    double minMs = 1e9;
    for (int i = 0; i < benchRuns; i++) {
      auto t0 = std::chrono::high_resolution_clock::now();
      renderer.render(width, height, 0, 0, 5, 0, 0, 0, framebuf.data(), lc);
      auto t1 = std::chrono::high_resolution_clock::now();
      double ms =
          std::chrono::duration<double, std::milli>(t1 - t0).count();
      totalMs += ms;
      if (ms < minMs) minMs = ms;
    }

    double avgMs = totalMs / benchRuns;
    printf("%3ux%-3u       %8.2f    %8.2f\n", cfg.bx, cfg.by, avgMs, minMs);
  }

  return 0;
}
