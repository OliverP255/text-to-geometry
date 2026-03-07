#pragma once

#include <cstdint>

//Handles are used to identify nodes in the graph. They are unique and immutable.

namespace kernel {

template <typename Tag>
struct Handle {
  uint32_t id = 0;

  bool valid() const { return id != 0; }
  bool operator==(Handle o) const { return id == o.id; }
  bool operator!=(Handle o) const { return id != o.id; }
};

struct ShapeTag {};
struct TransformTag {};
struct FloatTag {};

using ShapeH = Handle<ShapeTag>;
using TransformH = Handle<TransformTag>;
using FloatH = Handle<FloatTag>;

}  // namespace kernel
