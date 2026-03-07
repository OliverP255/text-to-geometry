// validate_dsl - CLI to validate DSL from stdin using compileIR
// Exit 0 on success, 1 on parse error. Prints error to stderr on failure.

#include "frontend/ir.h"
#include <iostream>
#include <string>

int main() {
  std::string input;
  for (std::string line; std::getline(std::cin, line);) {
    if (!input.empty()) input += '\n';
    input += line;
  }

  auto result = frontend::compileIR(input.c_str());

  if (result.ok) {
    return 0;
  }

  if (!result.error.empty()) {
    std::cerr << result.error;
    if (result.line > 0) {
      std::cerr << " (line " << result.line << ")";
    }
    std::cerr << std::endl;
  }
  return 1;
}
