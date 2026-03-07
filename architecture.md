# GPU SDF Kernel Architecture

Minimal, fast geometry kernel. All shapes reduce to `f(x,y,z) -> d`. Optimised for GPU execution.

---

## Pipeline Overview

```
DAG Builder → Optimise → Lower → Codegen → GPU
     (host)    (host)   (host)   (host)   (device)
```

---

## 1. DAG Builder (Host)

**Role:** Build an immutable shape graph with typed handles.

- **Storage:** Append-only arena. Dense node IDs. Headers + edges + payloads.
- **Handles:** `ShapeH`, `TransformH` only. No raw IDs in the API.
- **Nodes:** Primitives (Sphere, Box, Plane), CSG (Union, Intersect, Subtract), ApplyTransform.
- **Interning:** Hash-cons at build time. Canonicalise commutative ops (sort children).
- **Boundary:** `freeze()` locks the graph. Output: root handles + read-only arena.

**Out:** Immutable DAG in host RAM.

---

## 2. Optimise (Host)

**Role:** Cheap passes over the frozen DAG before lowering. No heavy algebra.

| Pass | What it does |
|------|--------------|
| Constant fold | Collapse literal-only subgraphs (e.g. `scale(1,1,1)` → identity). |
| Identity elision | Remove no-op transforms. `ApplyTransform(identity, s)` → `s`. |
| Dead prune | Remove nodes unreachable from root. |

**Rule:** Only transformations that are obviously safe and cheap. No symbolic simplification.

**Out:** Smaller, cleaner DAG. Same semantics.

---

## 3. Lower (Host)

**Role:** Flatten the DAG into a linear instruction stream.

- Topologically sort nodes. Each value computed once, in dependency order.
- Emit SSA-like temporaries: `t0 = ..., t1 = ..., return tN`.
- Normalise: transforms become "compute local p, evaluate primitive at p".
- Pack into a compact buffer: opcodes, args, constants.

**Out:** Flat IR (instruction array + constant pool). Ready for codegen.

---

## 4. Codegen (Host)

**Role:** Turn flat IR into GPU code.

- **Strategy:** Scene-specific codegen. One shader per scene. No interpretation.
- **Output:** WGSL (or CUDA/Metal) source string.
- **Content:** Straight-line `fn sdf(p: vec3f) -> f32 { ... }` with no branches where possible.
- Driver compiles to GPU binary. No instruction buffer upload.

**Out:** Compiled shader. Cached until scene changes.

---

## 5. GPU (Device)

**Role:** Evaluate SDF at many points in parallel.

- Each thread: compute `p`, call `sdf(p)`, use result.
- **Raymarch:** `p = origin + t * dir`, step by `sdf(p)`, repeat until hit or miss.
- **Grid:** One thread per voxel. `d = sdf(p)`.
- All `float32`. Branchless primitives and CSG (`min`, `max`).

**Out:** Distance field, pixels, or mesh data.

---

## Data Flow

```
User API
   │
   ▼
┌─────────────┐
│ DAG Builder │  typed handles, interning
└──────┬──────┘
       │ freeze()
       ▼
┌─────────────┐
│  Optimise   │  constant fold, identity elision, dead prune
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Lower     │  DAG → flat IR (opcodes, args, constants)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Codegen    │  flat IR → WGSL/CUDA/Metal source
└──────┬──────┘
       │ compile (driver)
       ▼
┌─────────────┐
│    GPU     │  sdf(p) evaluated per thread
└─────────────┘
```

---

## Memory Transfer

| When | What | Direction |
|------|------|-----------|
| Scene change | Shader binary (from codegen) | Host → Device |
| Per frame | Ray/grid input, uniforms | Host → Device |
| Per frame | Output buffer (optional readback) | Device → Host |

DAG, optimised DAG, flat IR: all stay on host. Never uploaded.

---

## Speed Principles

1. **Flatten early.** DAG is for authoring; flat IR is for execution.
2. **Codegen, don't interpret.** Specialised shader per scene beats generic interpreter.
3. **Straight-line code.** `min`/`max` for CSG. Avoid branches in hot path.
4. **float32 everywhere.** No doubles.
5. **Precompute inverses.** Transforms store inverse at build time; evaluation does inverse-point mapping only.
6. **Minimal optimisation.** Only passes that clearly reduce work. No speculative simplification.

---

## V1 Scope

**In:** Sphere, Box, Plane. Translate, Scale. Union, Intersect, Subtract. Binary CSG only.

**Out:** Constant fold, identity elision, dead prune. Flat IR. WGSL codegen. Raymarch or grid sampler.

**Not in v1:** Smooth CSG, rotations, generic math, materials, serialisation, n-ary CSG flattening.
