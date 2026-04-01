# Experiments

**Host requirement:** Enough free disk space for Hugging Face cache and vLLM (tens of GB). If the disk is full, model downloads and engine startup will fail.

**Question:** Which open-weight model produces the best WGSL SDF `map()` for CAD-style prompts?

**Prompt suite:** `test_50_prompts.py` — **46** prompts in five bands (classic CAD × four ablations + organic). See comments at top of that file for index ranges.

## Nine benchmark models (vLLM Hugging Face IDs)

| # | Report label | `model_id` |
|---|----------------|------------|
| 1 | Qwen3-32B-FP8 | `Qwen/Qwen3-32B-FP8` |
| 2 | GLM-4.7-Flash-FP8 | `marksverdhei/GLM-4.7-Flash-FP8` |
| 3 | DeepSeek-R1-Distill-Qwen-32B | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` |
| 4 | GLM-Z1-32B-0414 | `THUDM/GLM-Z1-32B-0414` |
| 5 | GLM-4-32B-0414 | `THUDM/GLM-4-32B-0414` |
| 6 | Qwen3-14B-FP8 | `Qwen/Qwen3-14B-FP8` |
| 7 | LLaVA-1.6-Mistral-7B | `llava-hf/llava-v1.6-mistral-7b-hf` |
| 8 | LLaVA-OneVision-Qwen2-7B | `llava-hf/llava-onevision-qwen2-7b-ov-hf` |
| 9 | Qwen2.5-Coder-32B-Instruct | `Qwen/Qwen2.5-Coder-32B-Instruct` |

*Omitted from the nine-run list (not standard text SDF codegen):* `BlenderLLM`, and generic “Qwen/Qwen3-32B” without FP8 (we use the FP8 checkpoint above).

## How to run

From repo root (GPU machine, weights cached or downloadable):

```bash
.venv/bin/python3 agent/experiments/run_multi_llm_benchmark.py
```

Smoke test (2 prompts × 9 models):

```bash
.venv/bin/python3 agent/experiments/run_multi_llm_benchmark.py --max-prompts 2
```

Outputs per model: `agent/experiments/outputs/by_model/<model_slug>/` plus `results.json`. Logs: `agent/experiments/logs/`.

## Ratings (automated)

```bash
.venv/bin/python3 agent/experiments/aggregate_benchmark_ratings.py
```

Writes `BENCHMARK_RATINGS.md` and `benchmark_aggregate.json` — **validation pass rate** through `wgsl_validator` and letter **grade**.
