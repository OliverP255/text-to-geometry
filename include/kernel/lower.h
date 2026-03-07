#pragma once

#include "kernel/builder.h"
#include "kernel/flat_ir.h"

namespace kernel {

FlatIR lower(const FrozenDAG& dag);

}  // namespace kernel
