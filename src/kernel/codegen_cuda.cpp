#include "kernel/codegen_cuda.h"
#include <algorithm>
#include <cmath>
#include <sstream>

namespace kernel {

namespace {

void emitConstantDecls(std::ostringstream& os, const FlatIR& ir) {
  size_t numTransforms = ir.transforms.size() / 6;
  size_t numSpheres = ir.spheres.size();
  size_t numBoxes = ir.boxes.size() / 3;
  size_t numPlanes = ir.planes.size() / 4;

  if (numTransforms > 0)
    os << "__constant__ float c_transforms[" << numTransforms * 7 << "];\n";
  if (numSpheres > 0)
    os << "__constant__ float c_spheres[" << numSpheres << "];\n";
  if (numBoxes > 0)
    os << "__constant__ float c_boxes[" << numBoxes * 3 << "];\n";
  if (numPlanes > 0)
    os << "__constant__ float c_planes[" << numPlanes * 4 << "];\n";
  os << "\n";
}

void emitDeviceHelpers(std::ostringstream& os) {
  os << R"(__device__ __forceinline__ float sdfSphere(float3 p, float r) {
  return norm3df(p.x, p.y, p.z) - r;
}

__device__ __forceinline__ float sdfBox(float3 p, float3 h) {
  float qx = fabsf(p.x) - h.x;
  float qy = fabsf(p.y) - h.y;
  float qz = fabsf(p.z) - h.z;
  float ox = fmaxf(qx, 0.f);
  float oy = fmaxf(qy, 0.f);
  float oz = fmaxf(qz, 0.f);
  float outside = norm3df(ox, oy, oz);
  float inside = fminf(fmaxf(fmaxf(qx, qy), qz), 0.f);
  return outside + inside;
}

__device__ __forceinline__ float sdfPlane(float3 p, float3 n, float d) {
  return p.x * n.x + p.y * n.y + p.z * n.z + d;
}

__device__ __forceinline__ float3 xformPoint(float3 p, int ti) {
  float tx = c_transforms[ti * 7 + 0];
  float ty = c_transforms[ti * 7 + 1];
  float tz = c_transforms[ti * 7 + 2];
  float sx = c_transforms[ti * 7 + 3];
  float sy = c_transforms[ti * 7 + 4];
  float sz = c_transforms[ti * 7 + 5];
  return make_float3((p.x - tx) / sx, (p.y - ty) / sy, (p.z - tz) / sz);
}

__device__ __forceinline__ float getMinScale(int ti) {
  return c_transforms[ti * 7 + 6];
}

)";
}

void emitSdfFunction(std::ostringstream& os, const FlatIR& ir) {
  os << "__device__ __forceinline__ float sdf(float3 p) {\n";

  if (ir.instrs.empty()) {
    os << "  return 1e10f;\n}\n\n";
    return;
  }

  for (size_t i = 0; i < ir.instrs.size(); i++) {
    const FlatInstr& instr = ir.instrs[i];
    switch (instr.op) {
      case FlatOp::EvalSphere:
        os << "  float t" << i << " = sdfSphere(xformPoint(p, " << instr.arg0
           << "), c_spheres[" << instr.constIdx << "]) * getMinScale("
           << instr.arg0 << ");\n";
        break;

      case FlatOp::EvalBox:
        os << "  float t" << i << " = sdfBox(xformPoint(p, " << instr.arg0
           << "), make_float3(c_boxes[" << instr.constIdx * 3 << "], c_boxes["
           << instr.constIdx * 3 + 1 << "], c_boxes["
           << instr.constIdx * 3 + 2 << "])) * getMinScale(" << instr.arg0
           << ");\n";
        break;

      case FlatOp::EvalPlane:
        os << "  float t" << i << " = sdfPlane(xformPoint(p, " << instr.arg0
           << "), make_float3(c_planes[" << instr.constIdx * 4 << "], c_planes["
           << instr.constIdx * 4 + 1 << "], c_planes["
           << instr.constIdx * 4 + 2 << "]), c_planes["
           << instr.constIdx * 4 + 3 << "]) * getMinScale(" << instr.arg0
           << ");\n";
        break;

      case FlatOp::CsgUnion:
        os << "  float t" << i << " = fminf(t" << instr.arg0 << ", t"
           << instr.arg1 << ");\n";
        break;

      case FlatOp::CsgIntersect:
        os << "  float t" << i << " = fmaxf(t" << instr.arg0 << ", t"
           << instr.arg1 << ");\n";
        break;

      case FlatOp::CsgSubtract:
        os << "  float t" << i << " = fmaxf(t" << instr.arg0 << ", -t"
           << instr.arg1 << ");\n";
        break;
    }
  }

  os << "  return t" << ir.rootTemp.id << ";\n}\n\n";
}

void emitEvalPointsKernel(std::ostringstream& os) {
  os << R"(extern "C" __global__ void evalPointsKernel(const float3* points, float* out, int n) {
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= n) return;
  out[i] = sdf(points[i]);
}

)";
}

void emitRaymarchKernel(std::ostringstream& os) {
  os << R"(
__device__ __forceinline__ float3 computeNormal(float3 p, float eps) {
  float dx = sdf(make_float3(p.x + eps, p.y, p.z))
           - sdf(make_float3(p.x - eps, p.y, p.z));
  float dy = sdf(make_float3(p.x, p.y + eps, p.z))
           - sdf(make_float3(p.x, p.y - eps, p.z));
  float dz = sdf(make_float3(p.x, p.y, p.z + eps))
           - sdf(make_float3(p.x, p.y, p.z - eps));
  float len = norm3df(dx, dy, dz);
  if (len < 1e-10f) return make_float3(0.f, 1.f, 0.f);
  float inv = 1.f / len;
  return make_float3(dx * inv, dy * inv, dz * inv);
}

extern "C"
__launch_bounds__(256, 4)
__global__ void raymarchKernel(
    unsigned char* output,
    int width, int height,
    float camX, float camY, float camZ,
    float lookX, float lookY, float lookZ,
    int maxSteps, float maxDist, float epsilon)
{
  int x = blockIdx.x * blockDim.x + threadIdx.x;
  int y = blockIdx.y * blockDim.y + threadIdx.y;
  if (x >= width || y >= height) return;

  float3 cam = make_float3(camX, camY, camZ);
  float3 look = make_float3(lookX, lookY, lookZ);

  float3 fwd = make_float3(look.x - cam.x, look.y - cam.y, look.z - cam.z);
  float fwdLen = norm3df(fwd.x, fwd.y, fwd.z);
  if (fwdLen < 1e-8f) fwdLen = 1.f;
  float invFwd = 1.f / fwdLen;
  fwd.x *= invFwd; fwd.y *= invFwd; fwd.z *= invFwd;

  float3 worldUp = make_float3(0.f, 1.f, 0.f);
  float3 right;
  right.x = fwd.y * worldUp.z - fwd.z * worldUp.y;
  right.y = fwd.z * worldUp.x - fwd.x * worldUp.z;
  right.z = fwd.x * worldUp.y - fwd.y * worldUp.x;
  float rLen = norm3df(right.x, right.y, right.z);
  if (rLen < 1e-8f) {
    worldUp = make_float3(0.f, 0.f, 1.f);
    right.x = fwd.y * worldUp.z - fwd.z * worldUp.y;
    right.y = fwd.z * worldUp.x - fwd.x * worldUp.z;
    right.z = fwd.x * worldUp.y - fwd.y * worldUp.x;
    rLen = norm3df(right.x, right.y, right.z);
  }
  float invR = 1.f / rLen;
  right.x *= invR; right.y *= invR; right.z *= invR;

  float3 up;
  up.x = right.y * fwd.z - right.z * fwd.y;
  up.y = right.z * fwd.x - right.x * fwd.z;
  up.z = right.x * fwd.y - right.y * fwd.x;

  float aspect = (float)width / (float)height;
  float fov = 1.0f;
  float u = (2.f * ((float)x + 0.5f) / (float)width - 1.f) * aspect * fov;
  float v = (1.f - 2.f * ((float)y + 0.5f) / (float)height) * fov;

  float3 dir;
  dir.x = fwd.x + u * right.x + v * up.x;
  dir.y = fwd.y + u * right.y + v * up.y;
  dir.z = fwd.z + u * right.z + v * up.z;
  float dLen = norm3df(dir.x, dir.y, dir.z);
  float invD = 1.f / dLen;
  dir.x *= invD; dir.y *= invD; dir.z *= invD;

  float t = 0.f;
  bool hit = false;

  #pragma unroll 4
  for (int i = 0; i < maxSteps; i++) {
    float3 p = make_float3(cam.x + t * dir.x, cam.y + t * dir.y, cam.z + t * dir.z);
    float d = sdf(p);
    if (d < epsilon) { hit = true; break; }
    t += d;
    if (t > maxDist) break;
  }

  int idx = (y * width + x) * 4;
  if (hit) {
    float3 p = make_float3(cam.x + t * dir.x, cam.y + t * dir.y, cam.z + t * dir.z);
    float3 n = computeNormal(p, epsilon * 2.f);
    float3 lightDir = make_float3(0.577f, 0.577f, 0.577f);
    float diffuse = fmaxf(0.f, n.x * lightDir.x + n.y * lightDir.y + n.z * lightDir.z);
    float ambient = 0.15f;
    float shade = fminf(ambient + diffuse * 0.85f, 1.f);
    unsigned char c = (unsigned char)(shade * 255.f);
    output[idx + 0] = c;
    output[idx + 1] = c;
    output[idx + 2] = c;
    output[idx + 3] = 255;
  } else {
    output[idx + 0] = 30;
    output[idx + 1] = 30;
    output[idx + 2] = 40;
    output[idx + 3] = 255;
  }
}

)";
}

}  // namespace

std::string codegenCuda(const FlatIR& ir) {
  std::ostringstream os;

  emitConstantDecls(os, ir);
  emitDeviceHelpers(os);
  emitSdfFunction(os, ir);
  emitEvalPointsKernel(os);
  emitRaymarchKernel(os);

  return os.str();
}

CudaConstantPool buildConstantPool(const FlatIR& ir) {
  CudaConstantPool pool;

  size_t numTransforms = ir.transforms.size() / 6;
  pool.transforms.resize(numTransforms * 7);
  for (size_t i = 0; i < numTransforms; i++) {
    float sx = ir.transforms[i * 6 + 3];
    float sy = ir.transforms[i * 6 + 4];
    float sz = ir.transforms[i * 6 + 5];
    pool.transforms[i * 7 + 0] = ir.transforms[i * 6 + 0];
    pool.transforms[i * 7 + 1] = ir.transforms[i * 6 + 1];
    pool.transforms[i * 7 + 2] = ir.transforms[i * 6 + 2];
    pool.transforms[i * 7 + 3] = sx;
    pool.transforms[i * 7 + 4] = sy;
    pool.transforms[i * 7 + 5] = sz;
    pool.transforms[i * 7 + 6] = std::min({sx, sy, sz});
  }

  pool.spheres = ir.spheres;
  pool.boxes = ir.boxes;
  pool.planes = ir.planes;

  return pool;
}

}  // namespace kernel
