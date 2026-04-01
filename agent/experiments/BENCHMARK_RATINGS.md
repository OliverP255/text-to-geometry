# LLM benchmark — automated ratings

**Status (runner environment):** The benchmark was **not executed to completion** here: the root filesystem was **100% full** (`No space left on device` during a model download). Cached weights present include `Qwen3-32B-FP8` and `GLM-4.7-Flash-FP8` under `~/.cache/huggingface/hub/`, but vLLM still needs free space for runtime.

**After freeing disk space**, run from repo root:

```bash
.venv/bin/python3 agent/experiments/run_multi_llm_benchmark.py
.venv/bin/python3 agent/experiments/aggregate_benchmark_ratings.py
```

Optional offline-only attempt (if every shard is already cached):

```bash
export HF_HUB_OFFLINE=1
.venv/bin/python3 agent/experiments/run_multi_llm_benchmark.py
```

---

## Rating methodology

| Metric | Meaning |
|--------|--------|
| **Valid WGSL %** | `wgsl_validator` accepts `fn map(p: vec3f) -> f32` (whitelist, single map, etc.) |
| **Any code %** | Agent returned non-`None` WGSL at least once (before or after validation) |
| **Mean len (valid)** | Average character length of **validator-passing** `map()` bodies |
| **Grade** | A≥90% valid, B≥75%, C≥50%, D≥25%, F&lt;25% valid |

---

## Leaderboard

*(Regenerate this table with `aggregate_benchmark_ratings.py` after runs finish.)*

| Rank | Model | Valid WGSL % | Any code % | Mean len (valid) | Grade |
|------|-------|-------------|------------|------------------|-------|
| — | *pending run* | — | — | — | — |
