"""
Hugging Face model IDs for agent/experiments/EXPERIMENTS.md (9 text/code models).

LLaVA checkpoints are vision-heavy; they may still answer text-only chat. BlenderLLM is omitted
(not a standard causal LM on HF for vLLM in the same way as the others).

Adjust `model_id` strings if your mirror uses different repos.
"""

from __future__ import annotations

# (short label for reports, vLLM HuggingFace model id)
BENCHMARK_MODELS: list[tuple[str, str]] = [
    ("Qwen3-32B-FP8", "Qwen/Qwen3-32B-FP8"),
    ("GLM-4.7-Flash-FP8", "marksverdhei/GLM-4.7-Flash-FP8"),
    ("DeepSeek-R1-Distill-Qwen-32B", "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"),
    ("GLM-Z1-32B-0414", "THUDM/GLM-Z1-32B-0414"),
    # Official THUDM id is gated (401/404 without HF token); zai-org mirror is the same weights, public.
    ("GLM-4-32B-0414", "zai-org/GLM-4-32B-0414"),
    ("Qwen3-14B-FP8", "Qwen/Qwen3-14B-FP8"),
    ("LLaVA-1.6-Mistral-7B", "llava-hf/llava-v1.6-mistral-7b-hf"),
    ("LLaVA-OneVision-Qwen2-7B", "llava-hf/llava-onevision-qwen2-7b-ov-hf"),
    ("Qwen2.5-Coder-32B-Instruct", "Qwen/Qwen2.5-Coder-32B-Instruct"),
]


def model_slug(model_id: str) -> str:
    return model_id.replace("/", "_").replace(":", "_")
