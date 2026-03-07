#include "kernel/optimise.h"
#include "kernel/intern.h"
#include <algorithm>
#include <cstring>
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

bool isIdentityTransform(const FrozenDAG& dag, uint32_t transformId) {
  const NodeHeader& h = getHeader(dag, transformId);
  if (h.category != NodeCategory::Transform) return false;
  const uint8_t* payload = getPayload(dag, h);
  if (!payload) return false;
  if (h.opcode == static_cast<uint8_t>(TransformOp::Translate)) {
    const auto* p = reinterpret_cast<const TranslatePayload*>(payload);
    return p->t.x == 0 && p->t.y == 0 && p->t.z == 0;
  }
  if (h.opcode == static_cast<uint8_t>(TransformOp::Scale)) {
    const auto* p = reinterpret_cast<const ScalePayload*>(payload);
    return p->s.x == 1 && p->s.y == 1 && p->s.z == 1;
  }
  return false;
}

void postOrderVisit(const FrozenDAG& dag, uint32_t id,
                    std::vector<uint32_t>& order, std::vector<bool>& visited) {
  if (id == 0 || id > dag.headerCount) return;
  if (visited[id - 1]) return;
  visited[id - 1] = true;
  const NodeHeader& h = getHeader(dag, id);
  uint32_t c0 = getChild(h, 0);
  uint32_t c1 = getChild(h, 1);
  if (c0) postOrderVisit(dag, c0, order, visited);
  if (c1 && c1 != c0) postOrderVisit(dag, c1, order, visited);
  order.push_back(id);
}

}  // namespace

OptimisedDAG optimise(const FrozenDAG& in) {
  OptimisedDAG out;
  if (!in.headers || in.headerCount == 0 || in.rootId == 0) {
    out.view.rootId = 0;
    out.view.headers = nullptr;
    out.view.headerCount = 0;
    out.view.payloads = nullptr;
    out.view.payloadBytes = 0;
    return out;
  }

  std::vector<uint32_t> postOrder;
  postOrder.reserve(in.headerCount);
  std::vector<bool> visited(in.headerCount, false);
  postOrderVisit(in, in.rootId, postOrder, visited);

  std::vector<uint32_t> oldToNew(in.headerCount + 1, 0);

  for (uint32_t oldId : postOrder) {
    const NodeHeader& h = getHeader(in, oldId);
    uint32_t newC0 = 0, newC1 = 0;

    if (h.arity >= 1) newC0 = oldToNew[getChild(h, 0)];
    if (h.arity >= 2) newC1 = oldToNew[getChild(h, 1)];

    if (h.category == NodeCategory::Shape &&
        h.opcode == static_cast<uint8_t>(ShapeOp::ApplyTransform) && newC0 &&
        isIdentityTransform(in, getChild(h, 0))) {
      oldToNew[oldId] = newC1;
      continue;
    }

    NodeHeader newH = h;
    newH.in0 = newC0 ? newC0 : kUnusedChild;
    newH.in1 = newC1 ? newC1 : kUnusedChild;
    newH.payloadOffset = kInvalidPayload;

    size_t payloadSize = 0;
    const uint8_t* srcPayload = getPayload(in, h);
    if (srcPayload) {
      if (h.category == NodeCategory::Shape) {
        if (h.opcode == static_cast<uint8_t>(ShapeOp::Sphere))
          payloadSize = sizeof(SpherePayload);
        else if (h.opcode == static_cast<uint8_t>(ShapeOp::Box))
          payloadSize = sizeof(BoxPayload);
        else if (h.opcode == static_cast<uint8_t>(ShapeOp::Plane))
          payloadSize = sizeof(PlanePayload);
      } else if (h.category == NodeCategory::Transform) {
        if (h.opcode == static_cast<uint8_t>(TransformOp::Translate))
          payloadSize = sizeof(TranslatePayload);
        else if (h.opcode == static_cast<uint8_t>(TransformOp::Scale))
          payloadSize = sizeof(ScalePayload);
      }
    }

    if (payloadSize > 0) {
      newH.payloadOffset = static_cast<uint32_t>(out.payloads.size());
      out.payloads.insert(out.payloads.end(), srcPayload,
                           srcPayload + payloadSize);
    }

    out.headers.push_back(newH);
    oldToNew[oldId] = static_cast<uint32_t>(out.headers.size());
  }

  uint32_t newRoot = oldToNew[in.rootId];
  if (newRoot == 0 || newRoot > out.headers.size()) {
    out.view.rootId = 0;
  } else {
    out.view.rootId = newRoot;
  }
  out.view.headers = reinterpret_cast<const uint8_t*>(out.headers.data());
  out.view.headerCount = out.headers.size();
  out.view.payloads =
      out.payloads.empty() ? nullptr : out.payloads.data();
  out.view.payloadBytes = out.payloads.size();

  std::vector<NodeHeader> dedupHeaders;
  std::vector<uint8_t> dedupPayloads;
  std::vector<uint32_t> canon(out.headers.size() + 1, 0);
  std::unordered_map<uint32_t, uint32_t> hashToCanon;

  std::vector<uint32_t> dedupPostOrder;
  dedupPostOrder.reserve(out.headers.size());
  std::vector<bool> dedupVisited(out.headers.size(), false);
  auto visit = [&](uint32_t id, auto& self) -> void {
    if (id == 0 || id > out.headers.size()) return;
    if (dedupVisited[id - 1]) return;
    dedupVisited[id - 1] = true;
    const NodeHeader& h = out.headers[id - 1];
    uint32_t c0 = h.in0 != kUnusedChild ? h.in0 : 0;
    uint32_t c1 = h.in1 != kUnusedChild ? h.in1 : 0;
    if (c0) self(c0, self);
    if (c1 && c1 != c0) self(c1, self);
    dedupPostOrder.push_back(id);
  };
  visit(out.view.rootId, visit);

  for (uint32_t id : dedupPostOrder) {
    const NodeHeader& h = out.headers[id - 1];
    uint32_t canon0 = canon[h.in0 != kUnusedChild ? h.in0 : 0];
    uint32_t canon1 = canon[h.in1 != kUnusedChild ? h.in1 : 0];

    if (h.opcode == static_cast<uint8_t>(ShapeOp::Union) ||
        h.opcode == static_cast<uint8_t>(ShapeOp::Intersect)) {
      if (canon0 > canon1) std::swap(canon0, canon1);
    }

    const uint8_t* payload = nullptr;
    size_t payloadSize = 0;
    if (h.payloadOffset != kInvalidPayload) {
      payload = out.payloads.data() + h.payloadOffset;
      if (h.category == NodeCategory::Shape) {
        if (h.opcode == static_cast<uint8_t>(ShapeOp::Sphere))
          payloadSize = sizeof(SpherePayload);
        else if (h.opcode == static_cast<uint8_t>(ShapeOp::Box))
          payloadSize = sizeof(BoxPayload);
        else if (h.opcode == static_cast<uint8_t>(ShapeOp::Plane))
          payloadSize = sizeof(PlanePayload);
      } else if (h.category == NodeCategory::Transform) {
        if (h.opcode == static_cast<uint8_t>(TransformOp::Translate))
          payloadSize = sizeof(TranslatePayload);
        else if (h.opcode == static_cast<uint8_t>(TransformOp::Scale))
          payloadSize = sizeof(ScalePayload);
      }
    }

    uint32_t key = intern::hash(h.category, h.opcode, canon0, canon1,
                                payload, payloadSize);

    uint32_t existing = 0;
    auto it = hashToCanon.find(key);
    if (it != hashToCanon.end()) {
      uint32_t candId = it->second;
      const NodeHeader& cand = dedupHeaders[candId - 1];
      uint32_t ec0 = cand.in0 != kUnusedChild ? cand.in0 : 0;
      uint32_t ec1 = cand.in1 != kUnusedChild ? cand.in1 : 0;
      if (intern::structuralEqual(cand, canon0 ? canon0 : 0,
                                 canon1 ? canon1 : 0, payload, payloadSize,
                                 dedupPayloads.data(), dedupPayloads.size())) {
        existing = candId;
      }
    }

    if (existing) {
      canon[id] = existing;
    } else {
      NodeHeader newH = h;
      newH.in0 = canon0 ? canon0 : kUnusedChild;
      newH.in1 = canon1 ? canon1 : kUnusedChild;
      newH.payloadOffset = kInvalidPayload;

      if (payloadSize > 0) {
        newH.payloadOffset = static_cast<uint32_t>(dedupPayloads.size());
        dedupPayloads.insert(dedupPayloads.end(), payload,
                            payload + payloadSize);
      }

      dedupHeaders.push_back(newH);
      uint32_t newId = static_cast<uint32_t>(dedupHeaders.size());
      canon[id] = newId;
      hashToCanon[key] = newId;
    }
  }

  out.headers = std::move(dedupHeaders);
  out.payloads = std::move(dedupPayloads);
  out.view.rootId = canon[out.view.rootId];
  out.view.headers = reinterpret_cast<const uint8_t*>(out.headers.data());
  out.view.headerCount = out.headers.size();
  out.view.payloads =
      out.payloads.empty() ? nullptr : out.payloads.data();
  out.view.payloadBytes = out.payloads.size();

  return out;
}

}  // namespace kernel
