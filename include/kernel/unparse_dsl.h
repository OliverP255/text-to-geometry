#pragma once

#include "kernel/flat_ir.h"
#include <string>

namespace kernel {

// Convert FlatIR to DSL script text.
std::string unparseDSL(const FlatIR& ir);

}  // namespace kernel
