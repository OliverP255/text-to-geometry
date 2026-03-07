#include "kernel/cuda_renderer.h"
#include <cuda.h>
#include <nvrtc.h>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

namespace kernel {

namespace {

void checkCu(CUresult res, const char* msg) {
  if (res != CUDA_SUCCESS) {
    const char* errStr = nullptr;
    cuGetErrorString(res, &errStr);
    throw std::runtime_error(
        std::string(msg) + ": " + (errStr ? errStr : "unknown CUDA error"));
  }
}

void checkNvrtc(nvrtcResult res, const char* msg, nvrtcProgram prog = nullptr) {
  if (res != NVRTC_SUCCESS) {
    std::string errMsg = std::string(msg) + ": " + nvrtcGetErrorString(res);
    if (prog) {
      size_t logSize = 0;
      nvrtcGetProgramLogSize(*prog, &logSize);
      if (logSize > 1) {
        std::vector<char> log(logSize);
        nvrtcGetProgramLog(*prog, log.data());
        errMsg += "\nCompilation log:\n";
        errMsg += log.data();
      }
    }
    throw std::runtime_error(errMsg);
  }
}

std::vector<char> compileToPTX(const std::string& source) {
  nvrtcProgram prog;
  nvrtcResult res = nvrtcCreateProgram(&prog, source.c_str(),
                                        "sdf_kernel.cu", 0, nullptr, nullptr);
  checkNvrtc(res, "nvrtcCreateProgram");

  const char* opts[] = {"--use_fast_math"};
  res = nvrtcCompileProgram(prog, 1, opts);
  if (res != NVRTC_SUCCESS) {
    size_t logSize = 0;
    nvrtcGetProgramLogSize(prog, &logSize);
    std::string log;
    if (logSize > 1) {
      log.resize(logSize);
      nvrtcGetProgramLog(prog, &log[0]);
    }
    nvrtcDestroyProgram(&prog);
    throw std::runtime_error(
        std::string("NVRTC compilation failed: ") + nvrtcGetErrorString(res) +
        "\n" + log);
  }

  size_t ptxSize = 0;
  checkNvrtc(nvrtcGetPTXSize(prog, &ptxSize), "nvrtcGetPTXSize");
  std::vector<char> ptx(ptxSize);
  checkNvrtc(nvrtcGetPTX(prog, ptx.data()), "nvrtcGetPTX");
  nvrtcDestroyProgram(&prog);

  return ptx;
}

}  // namespace

CudaRenderer::CudaRenderer() {
  CUresult res = cuInit(0);
  checkCu(res, "cuInit");

  CUdevice device;
  checkCu(cuDeviceGet(&device, 0), "cuDeviceGet");

  CUcontext ctx = nullptr;
  checkCu(cuCtxGetCurrent(&ctx), "cuCtxGetCurrent");
  if (!ctx) {
    checkCu(cuCtxCreate(&ctx, 0, device), "cuCtxCreate");
    context_ = ctx;
    ownsContext_ = true;
  }
}

CudaRenderer::~CudaRenderer() {
  cleanup();
  if (ownsContext_ && context_) {
    cuCtxDestroy(static_cast<CUcontext>(context_));
  }
}

void CudaRenderer::cleanup() {
  if (module_) {
    cuModuleUnload(static_cast<CUmodule>(module_));
    module_ = nullptr;
  }
  evalPointsFunc_ = nullptr;
  raymarchFunc_ = nullptr;
}

void CudaRenderer::uploadConstants(const CudaConstantPool& pool) {
  auto mod = static_cast<CUmodule>(module_);

  auto upload = [&](const char* name, const std::vector<float>& data) {
    if (data.empty()) return;
    CUdeviceptr dptr;
    size_t bytes;
    CUresult res = cuModuleGetGlobal(&dptr, &bytes, mod, name);
    checkCu(res, (std::string("cuModuleGetGlobal(") + name + ")").c_str());
    size_t uploadBytes = data.size() * sizeof(float);
    if (uploadBytes > bytes) uploadBytes = bytes;
    checkCu(cuMemcpyHtoD(dptr, data.data(), uploadBytes), "cuMemcpyHtoD");
  };

  upload("c_transforms", pool.transforms);
  upload("c_spheres", pool.spheres);
  upload("c_boxes", pool.boxes);
  upload("c_planes", pool.planes);
}

void CudaRenderer::setScene(const FlatIR& ir) {
  cleanup();

  std::string source = codegenCuda(ir);
  std::vector<char> ptx = compileToPTX(source);

  CUmodule mod;
  checkCu(cuModuleLoadDataEx(&mod, ptx.data(), 0, nullptr, nullptr),
          "cuModuleLoadData");
  module_ = mod;

  checkCu(cuModuleGetFunction(static_cast<CUfunction*>(&evalPointsFunc_), mod,
                               "evalPointsKernel"),
          "cuModuleGetFunction(evalPointsKernel)");

  CUfunction rmFunc;
  CUresult rmRes =
      cuModuleGetFunction(&rmFunc, mod, "raymarchKernel");
  if (rmRes == CUDA_SUCCESS) {
    raymarchFunc_ = rmFunc;
  }

  CudaConstantPool pool = buildConstantPool(ir);
  uploadConstants(pool);
}

void CudaRenderer::evalPoints(const float* points, float* output, int n) {
  if (!evalPointsFunc_ || n <= 0) return;

  CUdeviceptr d_points, d_output;
  size_t pointsBytes = static_cast<size_t>(n) * 3 * sizeof(float);
  size_t outputBytes = static_cast<size_t>(n) * sizeof(float);

  checkCu(cuMemAlloc(&d_points, pointsBytes), "cuMemAlloc(points)");
  checkCu(cuMemAlloc(&d_output, outputBytes), "cuMemAlloc(output)");
  checkCu(cuMemcpyHtoD(d_points, points, pointsBytes), "cuMemcpyHtoD(points)");

  int blockSize = 256;
  int gridSize = (n + blockSize - 1) / blockSize;

  void* args[] = {&d_points, &d_output, &n};
  checkCu(cuLaunchKernel(static_cast<CUfunction>(evalPointsFunc_), gridSize, 1,
                          1, blockSize, 1, 1, 0, nullptr, args, nullptr),
          "cuLaunchKernel(evalPoints)");
  checkCu(cuCtxSynchronize(), "cuCtxSynchronize");

  checkCu(cuMemcpyDtoH(output, d_output, outputBytes), "cuMemcpyDtoH(output)");

  cuMemFree(d_points);
  cuMemFree(d_output);
}

void CudaRenderer::render(int width, int height, float camX, float camY,
                           float camZ, float lookX, float lookY, float lookZ,
                           unsigned char* hostOutput,
                           const LaunchConfig& config, int maxSteps,
                           float maxDist, float epsilon) {
  if (!raymarchFunc_) {
    throw std::runtime_error("raymarchKernel not available; recompile scene");
  }

  size_t numPixels = static_cast<size_t>(width) * height;
  size_t outputBytes = numPixels * 4 * sizeof(unsigned char);

  CUdeviceptr d_output;
  checkCu(cuMemAlloc(&d_output, outputBytes), "cuMemAlloc(render output)");

  void* args[] = {&d_output, &width, &height, &camX, &camY, &camZ,
                  &lookX, &lookY, &lookZ, &maxSteps, &maxDist, &epsilon};

  unsigned int gridX = (width + config.blockX - 1) / config.blockX;
  unsigned int gridY = (height + config.blockY - 1) / config.blockY;

  checkCu(cuLaunchKernel(static_cast<CUfunction>(raymarchFunc_), gridX, gridY,
                          1, config.blockX, config.blockY, 1, 0, nullptr, args,
                          nullptr),
          "cuLaunchKernel(raymarch)");
  checkCu(cuCtxSynchronize(), "cuCtxSynchronize");

  checkCu(cuMemcpyDtoH(hostOutput, d_output, outputBytes),
          "cuMemcpyDtoH(render)");
  cuMemFree(d_output);
}

}  // namespace kernel
