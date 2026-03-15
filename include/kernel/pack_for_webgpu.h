#pragma once

#include "kernel/flat_ir.h"
#include <vector>

namespace kernel {

/** WGSL-aligned packed form for WebGPU buffer upload.
 * Transforms: 8 floats each (vec4 pos + vec4 scale with minScale).
 * Spheres, boxes, planes: 4 floats each (vec4).
 */
struct PackedFlatIR {
  std::vector<FlatInstr> instrs;
  std::vector<float> transforms;  // 8 per: tx,ty,tz,0, sx,sy,sz,minScale
  std::vector<float> spheres;     // 4 per: r,0,0,0
  std::vector<float> boxes;        // 4 per: hx,hy,hz,0
  std::vector<float> planes;       // 4 per: nx,ny,nz,d
  uint32_t rootTemp = 0;
};

PackedFlatIR packForWebGPU(const FlatIR& ir);

}  // namespace kernel
