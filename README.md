<div align="center">

<h1>SketchCAD</h1>

<h3><b>Text → 3D geometry via signed distance functions (SDFs)</b></h3>

</div>

SketchCAD is an app that turns natural language into executable 3D geometry using WGSL signed distance functions.

It acts as a *sketchpad for engineers* — enabling rapid iteration on complex procedural CAD designs before committing to full B-rep workflows.
=======
[![WebGPU](https://img.shields.io/badge/WebGPU-005A9C?style=flat-square&logo=webgpu&logoColor=white)](https://www.w3.org/TR/webgpu/)
[![WGSL](https://img.shields.io/badge/WGSL-1EAEDB?style=flat-square&labelColor=0d1117)](https://www.w3.org/TR/WGSL/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![vLLM](https://img.shields.io/badge/vLLM-000000?style=flat-square&logoColor=white)](https://github.com/vllm-project/vllm)
[![C++](https://img.shields.io/badge/C%2B%2B-00599C?style=flat-square&logo=c%2B%2B&logoColor=white)](https://isocpp.org/)

---
SketchCAD is an app that turns natural language into **executable 3D geometry**. It's a 'sketchpad for engineers' to build and iterate on specific, potentially complex parts before adding them to their B-Rep workflow.

![Chair demo](chair.gif)

![Demo](chair.gif)
---

## How it works
*Prompt → Geometry spec*
The user describes an object.
An LLM (default: Qwen3-32B-FP8 via vLLM, configurable with T2G_MODEL_ID) generates a single WGSL function:

| Step   | What happens   |
|------|----------------|
| **1** | User describes an object (dimensions, parts, style). |
| **2** | LLM (*default:* `Qwen3-32B-FP8` via vLLM, override with `T2G_MODEL_ID`) outputs `fn map(p: vec3f) -> f32` using the project’s **`sd*`** primitives and **`op*`** CSG helpers. |
| **3** | `server.py` runs WGSL validation, then pushes the scene to the viewer. |
| **4** | WebGPU client ray-marches the field in real time. |

`fn map(p: vec3f) -> f32`

This function defines the entire 3D shape using a fixed library of sd* (primitives) and op* (operations).

*Validation → Render*
The backend (`server.py`) validates the generated WGSL before sending it to the frontend for real-time rendering.

*Constrained generation (optional DSL)*

For weaker or non-finetuned models, the agent can generate a custom DSL instead of raw WGSL:

Enforces structure via grammar-constrained decoding
Reduces syntax errors and invalid geometry
Compiles to SDF via a C++ geometry kernel (`kernel/`)

This provides a more reliable fallback when direct WGSL generation is unstable.

Evaluation tooling

To understand model limitations, we built:

`agent/experiments/` — ~45 CAD-style prompts across multiple difficulty levels
Used to identify failure modes in geometry, proportions, and constraint handling


---

## Why SDFs (and not B-rep)?

SDFs do not replace B-rep for precision assemblies, drawings, or manufacturing-ready models. They are perfect for complex organic or procedural concepts (like gyroids, smooth booleans, repetitive patterns) that are tedious or impossible to produce in classical CAD.


Distance fields rendering is also very parrallelisable and very fast.

We noticed modern LLMs already understood the syntax and structure of writing SDFs in WGSL from pre-training. Mainly from Inigo Quilez's tutorials and examples (https://iquilezles.org/articles/distfunctions/).

We could then use this prior in the model by using the same variable names and structure as Quilez to make output from the LLM more natural. 

In summary: SDFs are perfect for exploring AND quickly iterating on cool CAD designs.

![Gyroid](gyroid.gif)

---

## Benchmark: How well do LLMs design 3D geometry?

A fixed prompt suite of 46 prompts from (`agent/experiments/test_50_prompts.py`) was run across nine open-weight models.
The models we tested were:

Qwen3-32B-FP8 | `Qwen/Qwen3-32B-FP8` 
GLM-4.7-Flash-FP8 | `marksverdhei/GLM-4.7-Flash-FP8` 
DeepSeek-R1-Distill-Qwen-32B | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` 
GLM-Z1-32B-0414 | `THUDM/GLM-Z1-32B-0414`
GLM-4-32B-0414 | `THUDM/GLM-4-32B-0414` 
Qwen3-14B-FP8 | `Qwen/Qwen3-14B-FP8` 
LLaVA-1.6-Mistral-7B | `llava-hf/llava-v1.6-mistral-7b-hf` 
LLaVA-OneVision-Qwen2-7B | `llava-hf/llava-onevision-qwen2-7b-ov-hf` 
Qwen2.5-Coder-32B-Instruct | `Qwen/Qwen2.5-Coder-32B-Instruct` 
We wanted to see the effect of the size of model, and the importance of reasoning and vision capabilities.

We tested them on 5 categories to see how prompting with specific length measurements or with step-by-step design instructions affected the output of the agent.
Categories:
Classic CAD — measurements + numbered steps
Classic CAD — measurements, no steps
Classic CAD — no measurements, no steps
Classic CAD — vague / short
Organic (SDF-friendly)

The outputs were WGSL `map()` functions; quality of the output was scored/rated and summarised in `agent/experiments/50_PROMPTS_RESULTS.md` and figures under `agent/experiments/figures/`.

---

## What's next

Directions suggested by benchmark and product goals:
- Expand library of shapes to include all the main CAD ones
- Need to give LLM 3D vision, either 3d point cloud vision or straight use a VLM because understanidng of proportions isn't optimal at the moment.

After that:
- Add 3D physics simulation and Finite Element Analysis (FEA) 
- Open-ended optimisation features and "Program synthesis" ideas to explore cool shape designs 
