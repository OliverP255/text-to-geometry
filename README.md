<div align="center">

<h1>SketchCAD</h1>

<h3><b>Text → 3D geometry via signed distance functions (SDFs)</b></h3>

[![WebGPU](https://img.shields.io/badge/WebGPU-005A9C?style=flat-square&logo=webgpu&logoColor=white)](https://www.w3.org/TR/webgpu/)
[![WGSL](https://img.shields.io/badge/WGSL-1EAEDB?style=flat-square&labelColor=0d1117)](https://www.w3.org/TR/WGSL/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![vLLM](https://img.shields.io/badge/vLLM-000000?style=flat-square&logoColor=white)](https://github.com/vllm-project/vllm)
[![C++](https://img.shields.io/badge/C%2B%2B-00599C?style=flat-square&logo=c%2B%2B&logoColor=white)](https://isocpp.org/)

---
SketchCAD is an app that turns natural language into **executable 3D geometry**. It's a 'sketchpad for engineers' to build and iterate on specific, potentially complex parts before adding them to their B-Rep workflow.

![Chair demo](chair.gif)

---

## How it works

| Step | What happens |
|------|----------------|
| **1 · Prompt** | User describes an object (dimensions, parts, style). |
| **2 · Generate** | LLM (*default:* `Qwen3-32B-FP8` via vLLM, override with `T2G_MODEL_ID`) outputs `fn map(p: vec3f) -> f32` using the project’s **`sd*`** primitives and **`op*`** CSG helpers. |
| **3 · Validate** | `server.py` runs WGSL validation, then pushes the scene to the viewer. |
| **4 · Render** | WebGPU client ray-marches the field in real time. |

**Optional · constrained DSL**  
For models that struggle with raw WGSL, a **narrow DSL** + grammar-constrained decoding can target the C++ kernel in `kernel/` instead—tighter structure, fewer syntax failures.

**Evaluation · `agent/experiments/`**  
~**45 CAD-style prompts** at multiple difficulty levels to study failure modes (geometry, proportions, constraints). Details in [`EXPERIMENTS.md`](agent/experiments/EXPERIMENTS.md).

---

## Why SDFs (not B-rep first)?

- **B-rep** still wins for **precision assemblies**, drawings, and manufacturing-ready data.
- **SDFs** shine for **organic / procedural** shapes (gyroids, smooth booleans, repetition) that are awkward in classical CAD.
- **Rendering** parallelises well; **distance fields** map naturally to GPU ray marching.
- **LLM prior:** models already echo **Inigo Quilez**-style WGSL/GLSL from the open web—[`iquilezles.org` distance functions](https://iquilezles.org/articles/distfunctions/) align with our runtime library.

In short: **explore and iterate fast** on concept geometry; graduate to B-rep when you need engineering rigor.

![Gyroid](gyroid.gif)

---

## Benchmark: LLMs as 3D designers

We ran **46 prompts** from [`agent/experiments/test_50_prompts.py`](agent/experiments/test_50_prompts.py) on **nine** open-weight models:

| Model | Hugging Face id |
|--------|------------------|
| Qwen3-32B-FP8 | `Qwen/Qwen3-32B-FP8` |
| GLM-4.7-Flash-FP8 | `marksverdhei/GLM-4.7-Flash-FP8` |
| DeepSeek-R1-Distill-Qwen-32B | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` |
| GLM-Z1-32B-0414 | `THUDM/GLM-Z1-32B-0414` |
| GLM-4-32B-0414 | `THUDM/GLM-4-32B-0414` |
| Qwen3-14B-FP8 | `Qwen/Qwen3-14B-FP8` |
| LLaVA-1.6-Mistral-7B | `llava-hf/llava-v1.6-mistral-7b-hf` |
| LLaVA-OneVision-Qwen2-7B | `llava-hf/llava-onevision-qwen2-7b-ov-hf` |
| Qwen2.5-Coder-32B-Instruct | `Qwen/Qwen2.5-Coder-32B-Instruct` |

**Prompt bands:** Classic CAD (with/without measurements & step lists), short/vague prompts, and organic SDF-friendly tasks.  
**Outputs:** WGSL `map()` snippets; quality notes and plots in [`50_PROMPTS_RESULTS.md`](agent/experiments/50_PROMPTS_RESULTS.md) and [`figures/`](agent/experiments/figures/).

---

## What’s next

- Broader **primitive / CAD coverage** in prompts and libraries.
- **3D / vision grounding** (point clouds or a VLM) to improve **proportions**.
- **Physics & FEA** hooks for “sketch → analyse”.
- **Open-ended optimisation** and program-synthesis-style exploration of shape space.
