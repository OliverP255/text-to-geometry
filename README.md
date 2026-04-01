<div align="center">

<h1>SketchCAD</h1>

<h4>Text → 3D geometry via signed distance functions (SDFs)</h4>  
</div>

<p align="center">
<img src="https://img.shields.io/badge/WebGPU-005A9C?style=flat-square&logo=webgpu&logoColor=white)">
<img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/vLLM-000000?style=flat-square&logoColor=white">
<img src="https://img.shields.io/badge/C%2B%2B-00599C?style=flat-square&logo=c%2B%2B&logoColor=white">
</p>  


SketchCAD is a 'sketchpad for engineers' to quickly build and iterate on  parts just by using natural language. 
It lets you use the speed and flexibility of SDFs to create potentially highly complex or procedural CAD models that can't be produced in regular B-Rep CAD software. 

<div align="center" style="padding: 28px 16px;">
<img src="chair.gif" alt="Demo" width="480">
</div>


## How it works


| Step   | What happens   |
|------|----------------|
| **1** | User describes an object (dimensions, parts, style). |
| **2** | **LLM** (*default:* `Qwen3-32B-FP8` via **vLLM**, override with `T2G_MODEL_ID`) outputs `fn map(p: vec3f) -> f32` using the project’s `sd*` primitives and `op*` CSG helpers. |
| **3** | `server.py` runs **WGSL** validation, then pushes the scene to the viewer. |
| **4** | **WebGPU** client ray-marches the field in real time. |

For weaker or non-finetuned models, the agent can generate a more constrained, custom **DSL** instead of raw WGSL.
When using the DSL, I enforce structure via **grammar-constrained decoding** to reduce syntax errors and invalid geometry. I also compile to SDF via a custom C++ geometry kernel (`kernel/`)

This provides a more reliable fallback when direct **WGSL** generation isn't reliable.

To further understand model limitations, I also built:
`agent/experiments/` — ~**45 CAD-style prompts** across multiple difficulty levels and categories. The LLMs' Results were then rated in terms of accuracy and recorded.

---

## Why **SDFs** (and not **B-rep**)?

**SDFs** do not replace **B-rep** for precision assemblies, drawings, or manufacturing-ready models. They are perfect for complex organic or procedural concepts (like gyroids, smooth booleans, repetitive patterns) that are tedious or impossible to produce in classical CAD.

Distance fields rendering is also very parrallelisable and very fast.

I noticed modern LLMs already understood the syntax and structure of writing SDFs in **WGSL** from pre-training. Mainly from **Inigo Quilez**'s tutorials and examples (https://iquilezles.org/articles/distfunctions/).

I could then use this prior in the model by using the same variable names and structure as Quilez to make output from the **LLM** more natural. 

In summary: SDFs are perfect for **exploring AND quickly iterating on cool CAD designs.**

<div align="center" style="padding: 28px 16px;">
<img src="gyroid.gif" alt="Gyroid" width="480">
</div>

---

## Benchmark: How well do LLMs design 3D geometry?

A fixed prompt suite of **46 prompts** from (`agent/experiments/test_50_prompts.py`) was run across **nine open-weight models**.

I also tested them on **5 categories of prompts**: Classic CAD with specified dimensions + numbered steps (B1), Classic CAD with specified dimensions + no steps (B2), Classic CAD with no specified dimnensions + no steps (B3), Classic CAD with vague / short prompt (B4), Organic (SDF-friendly) (B5).

The outputs were **WGSL** `map()` functions and I rated how well each model followed syntax over and used Claude Opus 4.6 to rate the accuracy of each result against the prompt, Claude even added notes for each model and prompt.

**CONCLUSION:**

The biggest issues the top models faced were small geometry mistakes e.g. wrong half-extent values or rotations in wrong direction. This was kind of expected and can be improved by giving the agents vision capabilities.

<div align="center">


<table>
<thead>
<tr><th>Model</th><th>Valid WGSL %</th><th>Mean Output Accuracy</th><th>Grade</th></tr>
</thead>
<tbody>
<tr><td>Qwen2.5-Coder-32B-Instruct</td><td>100.0%</td><td>4.35</td><td>A</td></tr>
<tr><td>Qwen3-14B-FP8</td><td>100.0%</td><td>4.28</td><td>A</td></tr>
<tr><td>Qwen3-32B-FP8</td><td>100.0%</td><td>4.15</td><td>A</td></tr>
<tr><td>GLM-4.7-Flash-FP8</td><td>100.0%</td><td>4.00</td><td>A</td></tr>
<tr><td>GLM-4-32B-0414</td><td>100.0%</td><td>3.96</td><td>A</td></tr>
<tr><td>DeepSeek-R1-Distill-Qwen-32B</td><td>100.0%</td><td>3.87</td><td>A</td></tr>
<tr><td>GLM-Z1-32B-0414</td><td>67.4%</td><td>3.02</td><td>C</td></tr>
<tr><td>llava-v1.6-mistral-7b-hf</td><td>95.7%</td><td>2.37</td><td>A</td></tr>
<tr><td>llava-onevision-qwen2-7b-ov-hf</td><td>82.6%</td><td>2.15</td><td>B</td></tr>
</tbody>
</table>
</div>

Qwen2.5-Coder-32B-Instruct was the best overall model. 


Interestingly, Qwen2.5-Coder beat both sizes of Qwen3 models and even produced some genuinely creative solutions for making CAD designs with SDF primitives. The smaller Qwen3 model also beat the larger one by a noticeable amount. 



<div align="center">
<img src="agent/experiments/figures/benchmark_band_spaghetti.png" alt="Line chart of mean fidelity across prompt bands B1 through B5 for each model" width="800">

</div>




---

## What's next?

Short term:
- Expand library of shapes to include all the main CAD objects (gears etc.)
- Need to give LLM 3D vision, either 3d point cloud vision or straight up use a **VLM** because understanding of proportions isn't optimal at the moment.

After that:
- Add 3D physics simulation and **Finite Element Analysis (FEA)** 
- Open-ended optimisation features and "**Program synthesis**" ideas to explore cool shape designs 
