#pragma once

#include "kernel/codegen_cuda.h"
#include "kernel/flat_ir.h"
#include <string>

namespace kernel {

struct LaunchConfig {
  unsigned int blockX = 16;
  unsigned int blockY = 16;
};

struct SceneBounds {
  float minX = -10.f, minY = -10.f, minZ = -10.f;
  float maxX = 10.f, maxY = 10.f, maxZ = 10.f;
};

class CudaRenderer {
 public:
  CudaRenderer();
  ~CudaRenderer();

  CudaRenderer(const CudaRenderer&) = delete;
  CudaRenderer& operator=(const CudaRenderer&) = delete;

  // Compile scene: codegen + NVRTC + upload constant pools.
  // Call again when scene changes.
  void setScene(const FlatIR& ir);

  // Evaluate SDF at N points. Host pointers in, host pointers out.
  // points: N * 3 floats (x,y,z interleaved), output: N floats.
  void evalPoints(const float* points, float* output, int n);

  // Raymarch render. Writes RGBA (uchar4) to hostOutput, row-major.
  void render(int width, int height, float camX, float camY, float camZ,
              float lookX, float lookY, float lookZ, unsigned char* hostOutput,
              const LaunchConfig& config = {},
              int maxSteps = 128, float maxDist = 100.f, float epsilon = 1e-4f);

  bool isReady() const { return module_ != nullptr; }

 private:
  void cleanup();
  void uploadConstants(const CudaConstantPool& pool);

  void* module_ = nullptr;           // CUmodule
  void* evalPointsFunc_ = nullptr;   // CUfunction
  void* raymarchFunc_ = nullptr;     // CUfunction
  void* context_ = nullptr;          // CUcontext
  bool ownsContext_ = false;
};

}  // namespace kernel
