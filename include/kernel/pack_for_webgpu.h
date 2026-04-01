#pragma once

#include "kernel/flat_ir.h"
#include <vector>

namespace kernel {

/** WGSL-aligned packed form for WebGPU buffer upload.
 * Transforms: 12 floats each (vec4 pos + vec4 scale/minScale + vec4 quat).
 * Spheres, boxes, cylinders: 4 floats each (vec4).
 */
struct PackedFlatIR {
  std::vector<FlatInstr> instrs;
  std::vector<float> transforms;  // 12 per: tx,ty,tz,0, sx,sy,sz,minScale, qx,qy,qz,qw
  std::vector<float> spheres;     // 4 per: r,0,0,0
  std::vector<float> boxes;        // 4 per: hx,hy,hz,0
  std::vector<float> cylinders;    // 4 per: r,h,0,0
  std::vector<float> smoothKs;     // 4 per: k,0,0,0
  uint32_t rootTemp = 0;
};

PackedFlatIR packForWebGPU(const FlatIR& ir);

}  // namespace kernel
