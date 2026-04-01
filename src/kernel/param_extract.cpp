#include "kernel/param_extract.h"
#include <algorithm>
#include <cmath>

namespace kernel {

namespace {

constexpr float kEpsilon = 1e-6f;

}  // namespace

std::vector<float> extractParams(const FlatIR& ir) {
  std::vector<float> params;
  params.reserve(ir.transforms.size() * 10 + ir.spheres.size() +
                 ir.boxes.size() * 3 +
                 ir.cylinders.size() * 2 + ir.smoothKs.size());

  for (const FlatTransform& t : ir.transforms) {
    params.push_back(t.tx);
    params.push_back(t.ty);
    params.push_back(t.tz);
    params.push_back(t.sx);
    params.push_back(t.sy);
    params.push_back(t.sz);
    params.push_back(t.qx);
    params.push_back(t.qy);
    params.push_back(t.qz);
    params.push_back(t.qw);
  }
  for (const FlatSphere& s : ir.spheres) params.push_back(s.r);
  for (const FlatBox& b : ir.boxes) {
    params.push_back(b.hx);
    params.push_back(b.hy);
    params.push_back(b.hz);
  }
  for (const FlatCylinder& c : ir.cylinders) {
    params.push_back(c.r);
    params.push_back(c.h);
  }
  for (float k : ir.smoothKs) {
    params.push_back(k);
  }

  return params;
}

void applyParams(FlatIR& ir, const std::vector<float>& params) {
  size_t idx = 0;

  for (size_t i = 0; i < ir.transforms.size() && idx + 10 <= params.size();
       ++i) {
    ir.transforms[i].tx = params[idx++];
    ir.transforms[i].ty = params[idx++];
    ir.transforms[i].tz = params[idx++];
    ir.transforms[i].sx = std::max(params[idx++], kEpsilon);
    ir.transforms[i].sy = std::max(params[idx++], kEpsilon);
    ir.transforms[i].sz = std::max(params[idx++], kEpsilon);
    ir.transforms[i].qx = params[idx++];
    ir.transforms[i].qy = params[idx++];
    ir.transforms[i].qz = params[idx++];
    ir.transforms[i].qw = params[idx++];
  }

  for (size_t i = 0; i < ir.spheres.size() && idx < params.size(); ++i) {
    ir.spheres[i].r = std::max(params[idx++], kEpsilon);
  }

  for (size_t i = 0; i < ir.boxes.size() && idx + 3 <= params.size(); ++i) {
    ir.boxes[i].hx = std::max(params[idx++], kEpsilon);
    ir.boxes[i].hy = std::max(params[idx++], kEpsilon);
    ir.boxes[i].hz = std::max(params[idx++], kEpsilon);
  }

  for (size_t i = 0; i < ir.cylinders.size() && idx + 2 <= params.size(); ++i) {
    ir.cylinders[i].r = std::max(params[idx++], kEpsilon);
    ir.cylinders[i].h = std::max(params[idx++], kEpsilon);
  }

  for (size_t i = 0; i < ir.smoothKs.size() && idx < params.size(); ++i) {
    ir.smoothKs[i] = std::max(params[idx++], kEpsilon);
  }
}

}  // namespace kernel
