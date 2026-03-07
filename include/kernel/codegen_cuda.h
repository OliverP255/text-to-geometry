#pragma once

#include "kernel/flat_ir.h"
#include <string>
#include <vector>

namespace kernel {

struct CudaConstantPool {
  std::vector<float> transforms;  // 7 floats per entry (tx,ty,tz,sx,sy,sz,minScale)
  std::vector<float> spheres;     // 1 float per entry (r)
  std::vector<float> boxes;       // 3 floats per entry (halfExtents)
  std::vector<float> planes;      // 4 floats per entry (normal + d)
};

// Generate CUDA source from FlatIR. Contains __constant__ declarations,
// device helpers, sdf(), evalPointsKernel, and optionally raymarchKernel.
std::string codegenCuda(const FlatIR& ir);

// Build the host-side constant pool with precomputed minScale per transform.
// Upload this data to the __constant__ symbols after NVRTC compilation.
CudaConstantPool buildConstantPool(const FlatIR& ir);

}  // namespace kernel
