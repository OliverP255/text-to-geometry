# SketchCAD
### Turn any idea into a professional-grade, 3D-printable physical product in minutes. No CAD experience required.

<div align="center" style="padding: 28px 16px;">
<img src="chair.gif" alt="Demo" width="480">
</div>

[![WebGPU](https://img.shields.io/badge/WebGPU-005A9C?style=flat-square&logo=webgpu&logoColor=white)](https://gpuweb.github.io/gpuweb/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![vLLM](https://img.shields.io/badge/vLLM-000000?style=flat-square&logoColor=white)](https://vllm.ai)
[![C++](https://img.shields.io/badge/C%2B%2B-00599C?style=flat-square&logo=c%2B%2B&logoColor=white)](https://isocpp.org)




## The Problem

The consumer 3D printing market has a fundamental tool gap.

Making a custom physical object today requires either expensive engineering software with a months-long learning curve, or accepting the severe limitations of beginner tools that can only produce blocky, primitive geometry. Mainstream CAD tools like SolidWorks, Fusion 360, AutoCAD are built on technology that is 20+ years old, designed for professional engineers, and completely inaccessible to anyone without significant training.

The gap between "I have an idea for a physical object" and "I have a printable file" is enormous for most people. 

SketchCAD closes that gap entirely.

---

## What SketchCAD Does

You describe what you want. SketcCAD builds it and gives you a file you can print.

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

I benchmarked all the top open source models for my task of generating 3D geometry in WGSL. Here were the results.

A fixed benchmark of **46 prompts** across five difficulty categories was run against nine open-weight models. WGSL validity was checked programmatically; geometric accuracy was rated (from both the code and 2D image of the result) by Claude Opus 4.6 on a 1–5 scale.

| Model | Valid WGSL % | Mean Accuracy | Grade |
|---|---|---|---|
| Qwen2.5-Coder-32B-Instruct | 100.0% | 4.35 | A |
| Qwen3-14B-FP8 | 100.0% | 4.28 | A |
| Qwen3-32B-FP8 | 100.0% | 4.15 | A |
| GLM-4.7-Flash-FP8 | 100.0% | 4.00 | A |
| GLM-4-32B-0414 | 100.0% | 3.96 | A |
| DeepSeek-R1-Distill-Qwen-32B | 100.0% | 3.87 | A |
| GLM-Z1-32B-0414 | 67.4% | 3.02 | C |
| llava-v1.6-mistral-7b-hf | 95.7% | 2.37 | B |
| llava-onevision-qwen2-7b-ov-hf | 82.6% | 2.15 | B |

**Prompt categories tested:**

- **B1** — Classic CAD with specified dimensions + numbered steps
- **B2** — Classic CAD with specified dimensions, no steps
- **B3** — Classic CAD, no dimensions specified
- **B4** — Vague / short prompts
- **B5** — Organic / SDF-native shapes (smooth blending, gyroids, procedural)

The dominant failure mode across all models was precise spatial reasoning (e.g. writing incorrect half-extents, wrong positional offsets, rotation errors) rather than syntax failures. 

**Finding:** Qwen2.5-Coder-32B-Instruct outperforms both larger Qwen3 models, demonstrating that code-specialised training is more valuable than raw scale for this task. The model also produced the most creative solutions for complex SDF compositions.


---

## Roadmap

### Current (v0)
- [x] Natural language → WGSL SDF generation
- [x] Real-time WebGPU ray marching preview
- [x] Multi-model benchmark (46 prompts, 9 models)
- [x] Grammar-constrained DSL fallback for weaker models
- [x] SDF → STL export pipeline
- [x] Mesh repair for slicer compatibility

### Near term
- [x] VLM vision feedback — agent sees rendered output and self-corrects geometric errors
- [ ] Parametric layer — named, editable parameters extracted from generated WGSL
- [ ] Extended primitive library — gears, threads, snap fits, knurling
- [ ] Print-on-demand integration — order physical prints directly from the interface
- [ ] Example gallery — curated prompts demonstrating SDF-native geometry

### Medium term
- [ ] Hybrid B-Rep + SDF engine — precise dimensions for structural features, SDF for organic surfaces
- [ ] Voxel FEA — basic structural analysis to validate wall thickness and load-bearing geometry
- [ ] Manufacturing constraint awareness — automatic overhang detection, minimum feature size warnings

### Long term
- [ ] Physics-driven design — simulation results feeding geometry as field operations
- [ ] Topology optimisation — SDF-native TO using density field methods
- [ ] Full generative design pipeline — from engineering specification to optimised physical part


---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- GPU with WebGPU support (Chrome 113+ or Edge 113+)
- vLLM-compatible GPU for local inference (or set `T2G_MODEL_ID` to use an API endpoint)

### Installation

```bash
git clone https://github.com/OliverP255/text-to-geometry
cd text-to-geometry

# Install Python dependencies
pip install -r agent/requirements.txt

# Install frontend dependencies
cd web && npm install && npm run build && cd ..

# Start the server
python server.py
```

Open `http://localhost:5001` in a WebGPU-enabled browser.

### Configuration

```bash
# Use a different model
T2G_MODEL_ID=Qwen/Qwen2.5-Coder-32B-Instruct python server.py

# Use an external API endpoint
T2G_API_BASE=https://your-endpoint.com python server.py
```

---

## Project Structure

```
text-to-geometry/
├── agent/                  # LLM agent and inference pipeline
│   ├── experiments/        # Benchmark suite (46 prompts, 9 models)
│   └── headless_renderer.py # GPU SDF evaluation via wgpu-py
├── bindings/               # Python bindings for C++ kernel
├── include/                # C++ SDF primitive headers
├── src/                    # C++ geometry kernel source
│   ├── primitives/         # sdSphere, sdBox, sdCylinder, etc.
│   └── operations/         # opUnion, opSmoothUnion, etc.
├── server/                 # Flask server and API routes
├── web/                    # TypeScript frontend
│   └── src/main.ts         # WebGPU renderer and UI
├── tests/                  # Geometry and pipeline tests
├── server.py               # Entry point
└── architecture.md         # Detailed architecture documentation
```

---


The SDF primitive library and ray marching implementation are deeply influenced by the work of [Inigo Quilez](https://iquilezles.org/articles/distfunctions/), whose tutorials and Shadertoy examples form the canonical reference for SDF-based geometry. The deliberate use of iq's naming conventions in this codebase is intentional and it aligns the generation target with the representation that frontier language models understand best.


For commercial use / collaboration, please reach out!
