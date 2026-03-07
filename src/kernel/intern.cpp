#include "kernel/node.h"
#include <cstdint>
#include <cstring>

namespace kernel {
namespace intern {

uint32_t hash(NodeCategory cat, uint8_t opcode, uint32_t child0,
              uint32_t child1, const void* payload, size_t payloadSize) {
  uint32_t h = 0;
  auto mix = [](uint32_t x) {
    x ^= x >> 16;
    x *= 0x85ebca6bu;
    x ^= x >> 13;
    x *= 0xc2b2ae35u;
    x ^= x >> 16;
    return x;
  };
  h = mix(h + static_cast<uint32_t>(cat));
  h = mix(h + opcode);
  h = mix(h + child0);
  h = mix(h + child1);
  if (payload && payloadSize > 0) {
    const uint8_t* p = static_cast<const uint8_t*>(payload);
    for (size_t i = 0; i < payloadSize; ++i) {
      h = mix(h + p[i]);
    }
  }
  return h;
}

bool structuralEqual(const NodeHeader& a, uint32_t child0, uint32_t child1,
                    const void* payload, size_t payloadSize,
                    const uint8_t* payloads, size_t payloadsSize) {
  constexpr uint32_t kUnusedChild = 0xFFFFFFFFu;
  if (a.arity != ((child0 != 0 ? 1 : 0) + (child1 != 0 ? 1 : 0))) return false;
  uint32_t expect0 = child0 != 0 ? child0 : kUnusedChild;
  uint32_t expect1 = child1 != 0 ? child1 : kUnusedChild;
  if (a.in0 != expect0 || a.in1 != expect1) return false;
  constexpr uint32_t kInvalidPayload = 0xFFFFFFFFu;
  if (payload && payloadSize > 0) {
    if (a.payloadOffset == kInvalidPayload) return false;
    if (payloadsSize < a.payloadOffset + payloadSize) return false;
    if (memcmp(payloads + a.payloadOffset, payload, payloadSize) != 0) {
      return false;
    }
  } else if (a.payloadOffset != kInvalidPayload) {
    return false;
  }
  return true;
}

}  // namespace intern
}  // namespace kernel
