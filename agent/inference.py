"""
JSON scene generation for SDF geometry via vLLM structured output.
Default model: Qwen3-32B-FP8 (`Qwen/Qwen3-32B-FP8`, `DEFAULT_VLLM_MODEL_ID`).
Override with `load_llm(model_id=...)` or env `T2G_MODEL_ID` (used only when `model_id` is omitted).

Qwen3 thinking: OFF by default for chat (`enable_thinking=False`), so WGSL/JSON show progress quickly.
Set `T2G_QWEN_THINKING=1` to enable long internal reasoning first.

Qwen3 + vLLM V1: async scheduling is disabled by default for model IDs containing "qwen3"
(workaround for back-to-back `LLM.chat` calls stalling at "Processed prompts: 0%"). Set
`T2G_VLLM_ASYNC_SCHEDULING=1` to force async scheduling on anyway.

If WGSL/JSON retries approach the context limit, raise it with `T2G_MAX_MODEL_LEN` (e.g. 16384)
when you have headroom — larger values reserve more KV cache.

Override vLLM fraction of GPU memory with `T2G_GPU_MEMORY_UTILIZATION` (e.g. `0.88`) when other
processes hold VRAM or startup reports insufficient free memory.

GLM thinking: ON by default for model IDs containing "glm" (case-insensitive). Uses
`structured_outputs_config` reasoning_parser glm45 + enable_in_reasoning, and
`llm.chat(..., chat_template_kwargs={"enable_thinking": True})`. Disable with env T2G_GLM_THINKING=0.
"""

from __future__ import annotations

import json
import os
from typing import Any

if not (os.environ.get("CUDA_VISIBLE_DEVICES") or "").strip():
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import torch
from vllm import LLM
from vllm.sampling_params import SamplingParams, StructuredOutputsParams

_llm_cache: dict[tuple[Any, ...], LLM] = {}

# load_llm(..., structured_outputs_config=None) must mean "no reasoning parser", not "apply default".
_MISSING_SO: Any = object()

# Default vLLM weights for WGSL + JSON agents (override with T2G_MODEL_ID or load_llm(model_id=...)).
DEFAULT_VLLM_MODEL_ID = "Qwen/Qwen3-32B-FP8"

_THINK_END_MARKERS = ("`</think>`", "</think>")


def _default_max_model_len() -> int:
    env = (os.environ.get("T2G_MAX_MODEL_LEN") or "").strip()
    if env.isdigit():
        return max(256, int(env))
    return 8192


def _default_async_scheduling_for_model(model_id: str) -> bool | None:
    """Return False to disable vLLM async scheduling, True to enable, None to use vLLM defaults."""
    v = (os.environ.get("T2G_VLLM_ASYNC_SCHEDULING") or "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    if "qwen3" in model_id.lower():
        return False
    return None


def _assert_nvml_sees_gpu() -> None:
    """Fail early if NVML cannot see a GPU (vLLM would give an opaque error later)."""
    try:
        from vllm.utils.import_utils import import_pynvml

        pynvml = import_pynvml()
        pynvml.nvmlInit()
        try:
            n = int(pynvml.nvmlDeviceGetCount())
        finally:
            pynvml.nvmlShutdown()
    except Exception as e:
        raise RuntimeError(
            "vLLM needs an NVIDIA GPU visible to the driver (NVML), same as nvidia-smi.\n"
            "Run: nvidia-smi\n"
            "On GCP, confirm a GPU is attached and NVIDIA drivers are installed.\n"
            f"NVML error: {e}"
        ) from e
    if n < 1:
        raise RuntimeError(
            "NVML reports 0 GPUs — vLLM cannot use CUDA.\n"
            "Fix the VM/driver until `nvidia-smi` lists a GPU."
        )


def glm_thinking_enabled(model_id: str) -> bool:
    """Whether to use chat-template thinking + glm45 reasoning parser (GLM family only)."""
    if "glm" not in model_id.lower():
        return False
    v = os.environ.get("T2G_GLM_THINKING", "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def qwen3_thinking_enabled(model_id: str) -> bool:
    """Qwen3 chat templates support enable_thinking; default OFF for fast WGSL/JSON (set T2G_QWEN_THINKING=1 to enable)."""
    if "qwen3" not in model_id.lower():
        return False
    v = os.environ.get("T2G_QWEN_THINKING", "0").strip().lower()
    return v in ("1", "true", "yes", "on")


def chat_kwargs_for_model(model_id: str) -> dict[str, Any]:
    """vLLM llm.chat(..., **return) extras: GLM thinking on; Qwen3 thinking off by default."""
    if glm_thinking_enabled(model_id):
        return {"chat_template_kwargs": {"enable_thinking": True}}
    if qwen3_thinking_enabled(model_id):
        return {"chat_template_kwargs": {"enable_thinking": True}}
    if "qwen3" in model_id.lower():
        return {"chat_template_kwargs": {"enable_thinking": False}}
    return {}


def strip_visible_thinking(text: str) -> str:
    """Keep only the final answer after the last thinking end marker, if present."""
    t = text.strip()
    for m in _THINK_END_MARKERS:
        if m in t:
            return t.rsplit(m, 1)[-1].strip()
    return t


def default_structured_outputs_for_model(model_id: str) -> dict[str, Any] | None:
    """GLM-4.7 family: use reasoning_parser glm45 + enable_in_reasoning."""
    if not glm_thinking_enabled(model_id):
        return None
    return {"reasoning_parser": "glm45", "enable_in_reasoning": True}


def load_llm(
    model_id: str | None = None,
    tensor_parallel_size: int = 1,
    max_model_len: int | None = None,
    enable_prefix_caching: bool = True,
    gpu_memory_utilization: float = 0.95,
    structured_outputs_config: Any = _MISSING_SO,
    **kwargs,
) -> LLM:
    """Load (or reuse cached) vLLM instance.

    Model resolution: ``model_id`` argument if non-empty, else ``T2G_MODEL_ID``, else
    ``DEFAULT_VLLM_MODEL_ID`` (Qwen3-32B-FP8).

    For GLM models, thinking + structured output reasoning follow the upstream vLLM recipe
    (reasoning_parser glm45, enable_in_reasoning) unless disabled via T2G_GLM_THINKING=0 or
    by passing structured_outputs_config explicitly.
    """
    mid = (model_id or "").strip() or (os.environ.get("T2G_MODEL_ID") or "").strip()
    if not mid:
        mid = DEFAULT_VLLM_MODEL_ID

    if max_model_len is None:
        max_model_len = _default_max_model_len()

    async_scheduling = kwargs.pop("async_scheduling", None)
    if async_scheduling is None:
        resolved_async = _default_async_scheduling_for_model(mid)
    else:
        resolved_async = async_scheduling

    if not torch.cuda.is_available():
        raise RuntimeError(
            "PyTorch does not see a GPU (torch.cuda.is_available() is False).\n"
            "Check: nvidia-smi"
        )
    if torch.cuda.device_count() < 1:
        raise RuntimeError("torch.cuda.device_count() is 0 — no CUDA device to run vLLM.")
    _assert_nvml_sees_gpu()

    kwargs_so = kwargs.pop("structured_outputs_config", None)
    if structured_outputs_config is _MISSING_SO:
        structured_outputs_config = kwargs_so
        if structured_outputs_config is None:
            structured_outputs_config = default_structured_outputs_for_model(mid)

    reason_key: tuple[Any, ...]
    if isinstance(structured_outputs_config, dict):
        reason_key = (
            structured_outputs_config.get("reasoning_parser", "") or "",
            bool(structured_outputs_config.get("enable_in_reasoning", False)),
        )
    elif structured_outputs_config is None:
        reason_key = ("", False)
    else:
        reason_key = ("custom", True)

    cache_key = (mid, tensor_parallel_size, max_model_len, reason_key, resolved_async)
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    mem_util = gpu_memory_utilization
    _env_mu = (os.environ.get("T2G_GPU_MEMORY_UTILIZATION") or "").strip()
    if _env_mu:
        try:
            mem_util = float(_env_mu)
        except ValueError:
            pass

    llm_kwargs: dict[str, Any] = dict(
        model=mid,
        trust_remote_code=True,
        tensor_parallel_size=tensor_parallel_size,
        max_model_len=max_model_len,
        enable_prefix_caching=enable_prefix_caching,
        enable_chunked_prefill=True,
        gpu_memory_utilization=mem_util,
        **kwargs,
    )
    if resolved_async is not None:
        llm_kwargs["async_scheduling"] = resolved_async
    if structured_outputs_config is not None:
        llm_kwargs["structured_outputs_config"] = structured_outputs_config

    llm = LLM(**llm_kwargs)
    _llm_cache[cache_key] = llm
    return llm


def generate_scene_json(
    messages: list[dict[str, str]],
    llm: LLM,
    json_schema: dict,
    max_new_tokens: int = 4096,
    temperature: float = 0.6,
    top_p: float = 0.95,
) -> dict:
    """Generate a scene JSON object from chat messages using structured output.

    Uses StructuredOutputsParams(json=...) so the model's raw output is guaranteed
    to be valid JSON matching the schema. GLM thinking is stripped before parsing.
    """
    structured = StructuredOutputsParams(json=json.dumps(json_schema))
    sampling = SamplingParams(
        structured_outputs=structured,
        max_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
    )

    mid = llm.model_config.model
    chat_kwargs = chat_kwargs_for_model(mid)

    outputs = llm.chat(messages, sampling_params=sampling, **chat_kwargs)
    text = outputs[0].outputs[0].text
    text = strip_visible_thinking(text)
    return json.loads(text)


def generate_wgsl_code(
    messages: list[dict[str, str]],
    llm: LLM,
    max_new_tokens: int = 3072,
    temperature: float = 0.7,
    top_p: float = 0.95,
) -> str:
    """Generate WGSL SDF code from chat messages (plain text, no structured output).

    The model should output a `fn map(p: vec3f) -> f32` function.
    GLM thinking markers are stripped if present.
    Qwen3: thinking is off by default (see T2G_QWEN_THINKING) so generation returns quickly.
    Override max decode length with env ``T2G_WGSL_MAX_TOKENS`` (integer) if set.
    """
    mt = max_new_tokens
    _mt_env = (os.environ.get("T2G_WGSL_MAX_TOKENS") or "").strip()
    if _mt_env.isdigit():
        mt = max(256, int(_mt_env))

    sampling = SamplingParams(
        max_tokens=mt,
        temperature=temperature,
        top_p=top_p,
    )

    mid = llm.model_config.model
    chat_kwargs = chat_kwargs_for_model(mid)
    # GLM + enable_thinking spends max_tokens inside thinking; WGSL `fn map` then truncates or
    # never appears. Plain-text WGSL needs a direct answer (JSON path keeps thinking on).
    if glm_thinking_enabled(mid):
        chat_kwargs = {"chat_template_kwargs": {"enable_thinking": False}}

    outputs = llm.chat(messages, sampling_params=sampling, **chat_kwargs)
    text = outputs[0].outputs[0].text
    return strip_visible_thinking(text)
