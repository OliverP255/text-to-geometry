#pragma once

#include "kernel/node.h"
#include <cstddef>
#include <cstdint>

namespace kernel {
namespace intern {

uint32_t hash(NodeCategory cat, uint8_t opcode, uint32_t child0,
              uint32_t child1, const void* payload, size_t payloadSize);

bool structuralEqual(const NodeHeader& a, uint32_t child0, uint32_t child1,
                     const void* payload, size_t payloadSize,
                     const uint8_t* payloads, size_t payloadsSize);

}  // namespace intern
}  // namespace kernel
