#include "kernel/param_extract.h"
#include <algorithm>
#include <cmath>

namespace kernel {

namespace {

constexpr float kEpsilon = 1e-6f;

}  // namespace

std::vector<float> extractParams(const FlatIR& ir) {
  std::vector<float> params;
  params.reserve(ir.transforms.size() + ir.spheres.size() + ir.boxes.size() +
                 ir.planes.size());

  for (float v : ir.transforms) params.push_back(v);
  for (float v : ir.spheres) params.push_back(v);
  for (float v : ir.boxes) params.push_back(v);
  for (float v : ir.planes) params.push_back(v);

  return params;
}

void applyParams(FlatIR& ir, const std::vector<float>& params) {
  size_t idx = 0;

  for (size_t i = 0; i < ir.transforms.size() && idx < params.size(); ++i, ++idx) {
    float v = params[idx];
    if (i % 6 >= 3) {  // sx, sy, sz (indices 3,4,5 of each transform)
      v = std::max(v, kEpsilon);
    }
    ir.transforms[i] = v;
  }

  for (size_t i = 0; i < ir.spheres.size() && idx < params.size(); ++i, ++idx) {
    ir.spheres[i] = std::max(params[idx], kEpsilon);
  }

  for (size_t i = 0; i < ir.boxes.size() && idx < params.size(); ++i, ++idx) {
    ir.boxes[i] = std::max(params[idx], kEpsilon);
  }

  for (size_t i = 0; i < ir.planes.size() && idx < params.size(); ++i, ++idx) {
    ir.planes[i] = params[idx];
  }
  // Optionally renormalize plane normals - for now we just apply values
}

}  // namespace kernel
