#include "kernel/param_extract.h"
#include <algorithm>
#include <cmath>

namespace kernel {

namespace {

constexpr float kEpsilon = 1e-6f;

}  // namespace

std::vector<float> extractParams(const FlatIR& ir) {
  std::vector<float> params;
  params.reserve(ir.transforms.size() * 6 + ir.spheres.size() +
                 ir.boxes.size() * 3 + ir.planes.size() * 4);

  for (const FlatTransform& t : ir.transforms) {
    params.push_back(t.tx);
    params.push_back(t.ty);
    params.push_back(t.tz);
    params.push_back(t.sx);
    params.push_back(t.sy);
    params.push_back(t.sz);
  }
  for (const FlatSphere& s : ir.spheres) params.push_back(s.r);
  for (const FlatBox& b : ir.boxes) {
    params.push_back(b.hx);
    params.push_back(b.hy);
    params.push_back(b.hz);
  }
  for (const FlatPlane& p : ir.planes) {
    params.push_back(p.nx);
    params.push_back(p.ny);
    params.push_back(p.nz);
    params.push_back(p.d);
  }

  return params;
}

void applyParams(FlatIR& ir, const std::vector<float>& params) {
  size_t idx = 0;

  for (size_t i = 0; i < ir.transforms.size() && idx + 6 <= params.size();
       ++i) {
    ir.transforms[i].tx = params[idx++];
    ir.transforms[i].ty = params[idx++];
    ir.transforms[i].tz = params[idx++];
    ir.transforms[i].sx = std::max(params[idx++], kEpsilon);
    ir.transforms[i].sy = std::max(params[idx++], kEpsilon);
    ir.transforms[i].sz = std::max(params[idx++], kEpsilon);
  }

  for (size_t i = 0; i < ir.spheres.size() && idx < params.size(); ++i) {
    ir.spheres[i].r = std::max(params[idx++], kEpsilon);
  }

  for (size_t i = 0; i < ir.boxes.size() && idx + 3 <= params.size(); ++i) {
    ir.boxes[i].hx = std::max(params[idx++], kEpsilon);
    ir.boxes[i].hy = std::max(params[idx++], kEpsilon);
    ir.boxes[i].hz = std::max(params[idx++], kEpsilon);
  }

  for (size_t i = 0; i < ir.planes.size() && idx + 4 <= params.size(); ++i) {
    ir.planes[i].nx = params[idx++];
    ir.planes[i].ny = params[idx++];
    ir.planes[i].nz = params[idx++];
    ir.planes[i].d = params[idx++];
  }
}

}  // namespace kernel
