#pragma once

#include "kernel/builder.h"
#include "kernel/node.h"
#include <cstddef>
#include <cstdint>
#include <vector>

namespace kernel {

struct OptimisedDAG {
  std::vector<NodeHeader> headers;
  std::vector<uint8_t> payloads;
  FrozenDAG view;
};

OptimisedDAG optimise(const FrozenDAG& in);

}  // namespace kernel
