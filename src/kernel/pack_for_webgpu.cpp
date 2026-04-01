#include "kernel/pack_for_webgpu.h"
#include <algorithm>

namespace kernel {

PackedFlatIR packForWebGPU(const FlatIR& ir) {
  PackedFlatIR out;
  out.instrs = ir.instrs;
  out.rootTemp = ir.rootTemp;

  out.transforms.reserve(ir.transforms.size() * 12);
  for (const FlatTransform& t : ir.transforms) {
    float minScale = std::min({t.sx, t.sy, t.sz});
    out.transforms.push_back(t.tx);
    out.transforms.push_back(t.ty);
    out.transforms.push_back(t.tz);
    out.transforms.push_back(0.0f);
    out.transforms.push_back(t.sx);
    out.transforms.push_back(t.sy);
    out.transforms.push_back(t.sz);
    out.transforms.push_back(minScale);
    out.transforms.push_back(t.qx);
    out.transforms.push_back(t.qy);
    out.transforms.push_back(t.qz);
    out.transforms.push_back(t.qw);
  }

  out.spheres.reserve(ir.spheres.size() * 4);
  for (const FlatSphere& s : ir.spheres) {
    out.spheres.push_back(s.r);
    out.spheres.push_back(0.0f);
    out.spheres.push_back(0.0f);
    out.spheres.push_back(0.0f);
  }

  out.boxes.reserve(ir.boxes.size() * 4);
  for (const FlatBox& b : ir.boxes) {
    out.boxes.push_back(b.hx);
    out.boxes.push_back(b.hy);
    out.boxes.push_back(b.hz);
    out.boxes.push_back(0.0f);
  }

  out.cylinders.reserve(ir.cylinders.size() * 4);
  for (const FlatCylinder& c : ir.cylinders) {
    out.cylinders.push_back(c.r);
    out.cylinders.push_back(c.h);
    out.cylinders.push_back(0.0f);
    out.cylinders.push_back(0.0f);
  }

  out.smoothKs.reserve(ir.smoothKs.size() * 4);
  for (float k : ir.smoothKs) {
    out.smoothKs.push_back(k);
    out.smoothKs.push_back(0.0f);
    out.smoothKs.push_back(0.0f);
    out.smoothKs.push_back(0.0f);
  }

  return out;
}

}  // namespace kernel
