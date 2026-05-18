# SketchCAD
### Turn any idea into a professional-grade, 3D-printable physical product in minutes. No CAD experience required.

[![WebGPU](https://img.shields.io/badge/WebGPU-005A9C?style=flat-square&logo=webgpu&logoColor=white)](https://gpuweb.github.io/gpuweb/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![vLLM](https://img.shields.io/badge/vLLM-000000?style=flat-square&logoColor=white)](https://vllm.ai)
[![C++](https://img.shields.io/badge/C%2B%2B-00599C?style=flat-square&logo=c%2B%2B&logoColor=white)](https://isocpp.org)



<div align="center" style="padding: 28px 16px;">
<img src="chair.gif" alt="Demo" width="480">
</div>


## The Problem

The consumer 3D printing market has a fundamental tool gap.

Making a custom physical object today requires either expensive engineering software with a months-long learning curve, or accepting the severe limitations of beginner tools that can only produce blocky, primitive geometry. Mainstream CAD tools like SolidWorks, Fusion 360, AutoCAD are built on technology that is 20+ years old, designed for professional engineers, and completely inaccessible to anyone without significant training.

The gap between "I have an idea for a physical object" and "I have a printable file" is enormous for most people. 

SketchCAD closes that gap entirely.

---

## What SketchCAD Does

You describe what you want. SketchCAD builds it and gives you a file you can print.

```html
          "A vase with a twisting body and a voronoi texture on the surface"
                                          │
                                          ▼
                        AI agent generates 3D geometry in real time
                                          │
                                          ▼
                  WebGPU ray marcher renders it instantly in your browser
                                          │
                                          ▼
                            Download STL  or  3D print directly
```

The kinds of objects SketchCAD excels at (organic shapes, surface textures, procedural structures, smooth blending between parts) are either impossible or require hours of expert work in traditional CAD tools. SketchCAD can generate them in seconds.


| Tool | Representation | AI interface | Organic geometry | Beginner-accessible |
|---|---|---|---|---|
| Fusion 360 | B-Rep | Limited copilot | Poor | No |
| Tinkercad | CSG/B-Rep | None | Very poor | Yes |
| nTop | Implicit/SDF | None | Excellent | No |
| Shap-E / Point-E | Mesh diffusion | Text | Moderate | Yes |
| **SketchCAD** | **SDF (WGSL)** | **Natural language** | **Excellent** | **Yes** |


---

## Why the Technology Is Different

### The representation problem with existing CAD

Every major CAD tool uses **Boundary Representation (B-Rep)**, geometry defined by its surface boundaries: vertices, edges, and faces. B-Rep is precise and manufacturable, but it has fundamental limitations:

- Boolean operations frequently fail on complex geometry
- Organic shapes, smooth blending, and surface textures are extremely difficult to produce
- Lattice structures, gyroids, and procedural infill are essentially impossible
- The geometry representation resists automation or continuous deformation since it was designed for humans clicking on faces, and not for AI agents generating geometry from text

### Signed Distance Functions: a modern alternative

SketchCAD's geometry engine is built on **Signed Distance Functions (SDFs)**, a mathematical representation where every point in 3D space stores its distance to the nearest surface. Negative values are inside the geometry, positive values are outside, and zero marks the surface itself.

```wgsl
fn map(p: vec3f) -> f32 {
    // Every point in space evaluated against this function
    // defines the entire geometry
    let sphere = sdSphere(p, 1.0);
    let box    = sdBox(p - vec3(1.5, 0.0, 0.0), vec3(0.8, 0.6, 0.4));
    return opSmoothUnion(sphere, box, 0.3);  // smooth blend between shapes
}
```

SDFs make previously difficult operations trivial:

| Operation | B-Rep | SDF |
|---|---|---|
| Smooth blending between shapes | Hours of expert work | `opSmoothUnion(a, b, k)` |
| Surface texture / noise | Requires displacement maps | `sdf(p) + noise(p)` |
| Infinite repetition | Impossible | `mod(p, cell_size)` |
| Gyroid / TPMS lattice | Essentially impossible | One analytical equation |
| Twist / bend deformation | Complex swept profiles | `sdf(warp(p))` |
| Boolean operations | Frequently fails | Always correct |

### Why SDFs are the right target for AI generation

Language models have been trained on enormous amounts of SDF code, primarily from Inigo Quilez's tutorials and the Shadertoy community. They already understand the structure, syntax, and compositional patterns of SDF geometry in a way they do not understand B-Rep construction sequences.

By targeting WGSL (the WebGPU shading language) using iq-style conventions, SketchCAD exploits this prior in frontier models to generate geometrically accurate 3D shapes directly from natural language - something that is not feasible with B-Rep.

---

## Benchmark: LLM Geometry Generation

A fixed benchmark of **46 prompts** across five difficulty categories was run against leading open-weight code models. WGSL validity was checked programmatically; geometric accuracy was rated on a 1–5 scale from generated code and rendered output.

| Model | Valid WGSL % | Mean accuracy (1–5) |
|---|---|---|
| Qwen2.5-Coder-32B-Instruct | 100% | **4.35** |
| Qwen3-14B-FP8 | 100% | 4.28 |
| Qwen3-32B-FP8 | 100% | 4.15 |
| GLM-4.7-Flash-FP8 | 100% | 4.00 |
| GLM-4-32B-0414 | 100% | 3.96 |
| DeepSeek-R1-Distill-Qwen-32B | 100% | 3.87 |

**Prompt categories:** classic CAD with dimensions and steps (B1–B2), CAD without dimensions (B3–B4), and organic / SDF-native shapes (B5).

**Finding:** Qwen2.5-Coder-32B-Instruct outperforms larger Qwen3 variants on this task—code-specialised training beats raw scale for WGSL SDF generation.

Full aggregate results: `agent/experiments/benchmark_aggregate.json`. Prompt suite: `agent/experiments/test_prompts.py`.


---

## Project Structure

```
text-to-geometry/
├── agent/                  # LLM agents, WGSL validator, mesh export
│   ├── experiments/        # Benchmark prompts + aggregate results
│   └── headless_renderer.py
├── bindings/               # pybind11 → C++ geometry kernel
├── include/                # C++ headers (kernel, frontend DSL)
├── src/
│   ├── kernel/             # FlatIR, lower, optimise, pack for WebGPU
│   └── frontend/           # DSL lexer/parser
├── print_backend/          # Print job API, auth, estimates
├── templates/              # Admin print-jobs UI
├── web/                    # TypeScript + Vite frontend
│   └── src/main.ts         # WebGPU viewer and prompt UI
├── tests/                  # C++ and Python tests
├── server.py               # Flask + Socket.IO entry point
└── chair.gif               # Demo render
```

NOTE: The DSL is currently no longer used in the agent loop because stronger models generally perform better using either WGSL or CADQuery as syntax is more familiar

---


The SDF primitive library and ray marching implementation are deeply influenced by the work of [Inigo Quilez](https://iquilezles.org/articles/distfunctions/), whose tutorials and Shadertoy examples form the canonical reference for SDF-based geometry. The deliberate use of iq's naming conventions in this codebase is intentional and it aligns the generation target with the representation that frontier language models understand best.


For commercial use / collaboration, please reach out!
