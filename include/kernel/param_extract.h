#pragma once

#include "kernel/flat_ir.h"
#include <vector>

namespace kernel {

// Extract raw trainable parameters from FlatIR (no constraint projection).
// Order: transforms (6 floats each), spheres (1 each), boxes (3 each), planes (4 each).
std::vector<float> extractParams(const FlatIR& ir);

// Apply params to FlatIR. Converts raw -> physical only at write-back.
// Enforces constraints: r > epsilon, halfExtents > epsilon, scale > epsilon.
void applyParams(FlatIR& ir, const std::vector<float>& params);

}  // namespace kernel
