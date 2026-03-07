#include "kernel/accum_transform.h"
#include "kernel/flat_ir.h"
#include "kernel/lower.h"
#include "kernel/node.h"
#include <unordered_map>
#include <vector>

namespace kernel {

namespace {

constexpr uint32_t kUnusedChild = 0xFFFFFFFFu;
constexpr uint32_t kInvalidPayload = 0xFFFFFFFFu;

inline const NodeHeader& getHeader(const FrozenDAG& dag, uint32_t id) {
  return reinterpret_cast<const NodeHeader*>(dag.headers)[id - 1];
}

inline const uint8_t* getPayload(const FrozenDAG& dag, const NodeHeader& h) {
  if (h.payloadOffset == kInvalidPayload) return nullptr;
  return dag.payloads + h.payloadOffset;
}

inline uint32_t getChild(const NodeHeader& h, int index) {
  if (index == 0) return h.in0 != kUnusedChild ? h.in0 : 0;
  return h.in1 != kUnusedChild ? h.in1 : 0;
}

bool isIdentity(const AccumTransform& a) {
  return a.translate.x == 0 && a.translate.y == 0 && a.translate.z == 0 &&
         a.scale.x == 1 && a.scale.y == 1 && a.scale.z == 1;
}

uint32_t addTransform(FlatIR& ir, const AccumTransform& accum) {
  if (isIdentity(accum)) return 0;
  for (size_t i = 0; i < ir.transforms.size(); i += 6) {
    if (ir.transforms[i] == accum.translate.x &&
        ir.transforms[i + 1] == accum.translate.y &&
        ir.transforms[i + 2] == accum.translate.z &&
        ir.transforms[i + 3] == accum.scale.x &&
        ir.transforms[i + 4] == accum.scale.y &&
        ir.transforms[i + 5] == accum.scale.z) {
      return static_cast<uint32_t>(i / 6);
    }
  }
  ir.transforms.push_back(accum.translate.x);
  ir.transforms.push_back(accum.translate.y);
  ir.transforms.push_back(accum.translate.z);
  ir.transforms.push_back(accum.scale.x);
  ir.transforms.push_back(accum.scale.y);
  ir.transforms.push_back(accum.scale.z);
  return static_cast<uint32_t>(ir.transforms.size() / 6 - 1);
}

using CacheKey = std::pair<uint32_t, AccumTransform>;

DistTemp emitNode(FlatIR& ir, const FrozenDAG& dag, uint32_t nodeId,
                  const AccumTransform& accum,
                  std::unordered_map<CacheKey, uint32_t, AccumTransformKeyHash>&
                      cache,
                  uint32_t& nextDistTemp) {
  CacheKey key{nodeId, accum};
  auto it = cache.find(key);
  if (it != cache.end()) return DistTemp{it->second};

  if (nodeId == 0 || nodeId > dag.headerCount) return DistTemp{0};

  const NodeHeader& h = getHeader(dag, nodeId);

  if (h.category == NodeCategory::Shape) {
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Sphere)) {
      uint32_t transformIdx = addTransform(ir, accum);
      const uint8_t* payload = getPayload(dag, h);
      float r = 1.0f;
      if (payload) r = reinterpret_cast<const SpherePayload*>(payload)->r;
      uint32_t sphereIdx = static_cast<uint32_t>(ir.spheres.size());
      ir.spheres.push_back(r);

      FlatInstr instr;
      instr.op = FlatOp::EvalSphere;
      instr.arg0 = transformIdx;
      instr.constIdx = sphereIdx;
      ir.instrs.push_back(instr);

      uint32_t temp = nextDistTemp++;
      cache[key] = temp;
      return DistTemp{temp};
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Box)) {
      uint32_t transformIdx = addTransform(ir, accum);
      const uint8_t* payload = getPayload(dag, h);
      Vec3 halfExtents{1, 1, 1};
      if (payload)
        halfExtents = reinterpret_cast<const BoxPayload*>(payload)->halfExtents;
      uint32_t boxIdx = static_cast<uint32_t>(ir.boxes.size() / 3);
      ir.boxes.push_back(halfExtents.x);
      ir.boxes.push_back(halfExtents.y);
      ir.boxes.push_back(halfExtents.z);

      FlatInstr instr;
      instr.op = FlatOp::EvalBox;
      instr.arg0 = transformIdx;
      instr.constIdx = boxIdx;
      ir.instrs.push_back(instr);

      uint32_t temp = nextDistTemp++;
      cache[key] = temp;
      return DistTemp{temp};
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Plane)) {
      uint32_t transformIdx = addTransform(ir, accum);
      const uint8_t* payload = getPayload(dag, h);
      Vec3 normal{0, 1, 0};
      float d = 0;
      if (payload) {
        const auto* p = reinterpret_cast<const PlanePayload*>(payload);
        normal = p->normal;
        d = p->d;
      }
      uint32_t planeIdx = static_cast<uint32_t>(ir.planes.size() / 4);
      ir.planes.push_back(normal.x);
      ir.planes.push_back(normal.y);
      ir.planes.push_back(normal.z);
      ir.planes.push_back(d);

      FlatInstr instr;
      instr.op = FlatOp::EvalPlane;
      instr.arg0 = transformIdx;
      instr.constIdx = planeIdx;
      ir.instrs.push_back(instr);

      uint32_t temp = nextDistTemp++;
      cache[key] = temp;
      return DistTemp{temp};
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Union)) {
      uint32_t c0 = getChild(h, 0);
      uint32_t c1 = getChild(h, 1);
      DistTemp ta = emitNode(ir, dag, c0, accum, cache, nextDistTemp);
      DistTemp tb = emitNode(ir, dag, c1, accum, cache, nextDistTemp);

      FlatInstr instr;
      instr.op = FlatOp::CsgUnion;
      instr.arg0 = ta.id;
      instr.arg1 = tb.id;
      ir.instrs.push_back(instr);

      uint32_t temp = nextDistTemp++;
      cache[key] = temp;
      return DistTemp{temp};
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Intersect)) {
      uint32_t c0 = getChild(h, 0);
      uint32_t c1 = getChild(h, 1);
      DistTemp ta = emitNode(ir, dag, c0, accum, cache, nextDistTemp);
      DistTemp tb = emitNode(ir, dag, c1, accum, cache, nextDistTemp);

      FlatInstr instr;
      instr.op = FlatOp::CsgIntersect;
      instr.arg0 = ta.id;
      instr.arg1 = tb.id;
      ir.instrs.push_back(instr);

      uint32_t temp = nextDistTemp++;
      cache[key] = temp;
      return DistTemp{temp};
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::Subtract)) {
      uint32_t c0 = getChild(h, 0);
      uint32_t c1 = getChild(h, 1);
      DistTemp ta = emitNode(ir, dag, c0, accum, cache, nextDistTemp);
      DistTemp tb = emitNode(ir, dag, c1, accum, cache, nextDistTemp);

      FlatInstr instr;
      instr.op = FlatOp::CsgSubtract;
      instr.arg0 = ta.id;
      instr.arg1 = tb.id;
      ir.instrs.push_back(instr);

      uint32_t temp = nextDistTemp++;
      cache[key] = temp;
      return DistTemp{temp};
    }
    if (h.opcode == static_cast<uint8_t>(ShapeOp::ApplyTransform)) {
      uint32_t transformId = getChild(h, 0);
      uint32_t shapeId = getChild(h, 1);
      if (transformId == 0 || shapeId == 0) return DistTemp{0};

      const NodeHeader& th = getHeader(dag, transformId);
      const uint8_t* tpayload = getPayload(dag, th);
      if (!tpayload) return DistTemp{0};

      AccumTransform newAccum =
          compose(accum, static_cast<TransformOp>(th.opcode), tpayload);
      return emitNode(ir, dag, shapeId, newAccum, cache, nextDistTemp);
    }
  }

  return DistTemp{0};
}

}  // namespace

FlatIR lower(const FrozenDAG& dag) {
  FlatIR ir;
  if (!dag.headers || dag.headerCount == 0 || dag.rootId == 0) {
    ir.rootTemp = DistTemp{0};
    return ir;
  }

  ir.transforms = {0, 0, 0, 1, 1, 1};  // identity at index 0

  std::unordered_map<CacheKey, uint32_t, AccumTransformKeyHash> cache;
  uint32_t nextDistTemp = 0;

  AccumTransform identity;
  ir.rootTemp = emitNode(ir, dag, dag.rootId, identity, cache, nextDistTemp);

  return ir;
}

}  // namespace kernel
