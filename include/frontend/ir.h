#pragma once

#include "kernel/builder.h"
#include <string>
#include <vector>

namespace frontend {

struct CompileResult {
  bool ok = false;
  kernel::FrozenDAG dag;
  std::string error;
  int line = 0;
  std::vector<uint8_t> dagHeaders;   // owns header data
  std::vector<uint8_t> dagPayloads;  // owns payload data
};

CompileResult compileIR(const char* source);

}  // namespace frontend
