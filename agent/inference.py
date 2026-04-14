"""
JSON scene generation for SDF geometry via vLLM structured output.
Default model: Qwen2.5-Coder-32B-Instruct AWQ (`Qwen/Qwen2.5-Coder-32B-Instruct-AWQ`, `DEFAULT_VLLM_MODEL_ID`).
Override with `load_llm(model_id=...)` or env `T2G_MODEL_ID` (used only when `model_id` is omitted).

Qwen3 thinking: OFF by default for plain Qwen3 (`enable_thinking=False`), so WGSL/JSON return quickly.
Set `T2G_QWEN_THINKING=1` to force reasoning on; Thinking-tuned ids (e.g. ``*Thinking*`` in the HF name)
default to ON unless `T2G_QWEN_THINKING=0`.

Qwen3 + vLLM V1: async scheduling is disabled by default for model IDs containing "qwen3"
(workaround for back-to-back `LLM.chat` calls stalling at "Processed prompts: 0%"). Set
`T2G_VLLM_ASYNC_SCHEDULING=1` to force async scheduling on anyway.

If WGSL/JSON retries approach the context limit, raise it with `T2G_MAX_MODEL_LEN` (e.g. 16384)
when you have headroom — larger values reserve more KV cache.

After each ``llm.chat`` call, a one-line summary is printed: prompt/generated token counts,
wall-clock tok/s, and vLLM decode tok/s when metrics are available. Set ``T2G_SILENT_LLM_STATS=1``
to disable.

Override vLLM fraction of GPU memory with `T2G_GPU_MEMORY_UTILIZATION` (e.g. `0.88`) when other
processes hold VRAM or startup reports insufficient free memory.

GLM thinking: ON by default for model IDs containing "glm" (case-insensitive). Uses
`structured_outputs_config` reasoning_parser glm45 + enable_in_reasoning, and
`llm.chat(..., chat_template_kwargs={"enable_thinking": True})`. Disable with env T2G_GLM_THINKING=0.

Claude extended thinking: Set `T2G_CLAUDE_BUDGET_TOKENS` (e.g., 4096) to enable extended thinking
for Claude Opus 4.x models via Vertex AI or LiteLLM. Minimum is 1024 tokens. Thinking blocks are
automatically stripped from the response.

BACKEND SELECTION:
Set `T2G_BACKEND=vertex` to use Vertex AI Claude (anthropic library) instead of vLLM.
For Vertex AI, set `T2G_VERTEX_PROJECT_ID` and optionally `T2G_VERTEX_LOCATION` (default: ``global``).
For Vertex AI, `T2G_MODEL_ID` should be the Claude model name (e.g., `claude-opus-4-6`).

Set `T2G_BACKEND=litellm` to call an Anthropic-compatible HTTP API (e.g. local LiteLLM
``./litellm/run.sh`` → Vertex GLM). Set ``ANTHROPIC_BASE_URL`` (default ``http://127.0.0.1:4000``)
and ``ANTHROPIC_AUTH_TOKEN`` or ``LITELLM_MASTER_KEY``. ``T2G_MODEL_ID`` should match a
``model_name`` in ``litellm/config.yaml`` (e.g. ``glm-5``).

On GCE VMs, default instance tokens often lack `cloud-platform` OAuth scope → 403
``ACCESS_TOKEN_SCOPE_INSUFFICIENT``. Set ``GOOGLE_APPLICATION_CREDENTIALS`` to a service-account
JSON with ``roles/aiplatform.user``, or place the same key LiteLLM uses at
``litellm/.vertex-sa.json``. Grant that SA ``roles/aiplatform.user`` on the target GCP project
(including cross-project if the key lives under another ``project_id``).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# Backend selection (default: litellm for Claude Opus via local proxy)
T2G_BACKEND = os.environ.get("T2G_BACKEND", "litellm").lower().strip()

# Default model for LiteLLM/Vertex backend
DEFAULT_MODEL_ID = "claude-opus-4-6"

# Vertex AI request timeout (seconds). Default 120s.
T2G_VERTEX_TIMEOUT = float(os.environ.get("T2G_VERTEX_TIMEOUT", "120").strip() or "120")

_VERTEX_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)


def _vertex_service_account_credentials() -> Any | None:
    """Credentials for AnthropicVertex when GCE metadata tokens lack cloud-platform scope.

    Resolution order:
      1. ``T2G_VERTEX_CREDENTIALS`` (path to JSON)
      2. ``GOOGLE_APPLICATION_CREDENTIALS``
      3. ``<repo>/litellm/.vertex-sa.json``

    The service account must have ``roles/aiplatform.user`` on ``T2G_VERTEX_PROJECT_ID``
    (same project as the key or cross-project IAM).
    """
    explicit_t2g = (os.environ.get("T2G_VERTEX_CREDENTIALS") or "").strip()
    path = (os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    if explicit_t2g:
        path = explicit_t2g
    elif not path:
        cand = Path(__file__).resolve().parent.parent / "litellm" / ".vertex-sa.json"
        if cand.is_file():
            path = str(cand)
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None

    try:
        from google.oauth2 import service_account
    except ImportError as e:
        raise ImportError(
            "Vertex backend needs google-auth for service-account JSON. "
            "Install: pip install google-auth"
        ) from e
    return service_account.Credentials.from_service_account_file(
        str(p),
        scopes=list(_VERTEX_SCOPES),
    )


@runtime_checkable
class LLMBackend(Protocol):
    """Protocol for LLM backends (vLLM or Anthropic/Vertex)."""

    @property
    def model_id(self) -> str:
        """Return the model identifier."""
        ...

    def chat(
        self,
        messages: list[dict],
        *,
        system: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
    ) -> str:
        """Generate a response from chat messages. Returns the text content."""
        ...


def _anthropic_sampling_kwargs_for_model(
    model_id: str, temperature: float, top_p: float
) -> dict[str, Any]:
    """Claude 4.6 on Vertex returns 400 if both ``temperature`` and ``top_p`` are set."""
    m = model_id.lower()
    if "-4-6" in m and m.startswith("claude-"):
        return {"temperature": temperature}
    return {"temperature": temperature, "top_p": top_p}


def _default_budget_tokens() -> int | None:
    """Get extended thinking budget from T2G_CLAUDE_BUDGET_TOKENS env var.

    Minimum is 1024 per Anthropic docs. Returns None if not set.
    Deprecated on 4.6 models - use effort parameter instead.
    """
    env = (os.environ.get("T2G_CLAUDE_BUDGET_TOKENS") or "").strip()
    if env and env.isdigit():
        return max(1024, int(env))
    return None


def _default_effort() -> str | None:
    """Get thinking effort from T2G_CLAUDE_EFFORT env var.

    Values: "low", "medium", "high", "max" (Opus only).
    Default is "medium" for Claude 4.6 models via litellm/vertex backend.
    Medium effort skips thinking for simple requests.
    """
    env = (os.environ.get("T2G_CLAUDE_EFFORT") or "").strip().lower()
    if env in ("low", "medium", "high", "max"):
        return env
    # Default to "medium" - skips thinking for simple requests
    backend = os.environ.get("T2G_BACKEND", "litellm").lower().strip()
    if backend in ("litellm", "vertex"):
        return "medium"
    return None


# ---------------------------------------------------------------------------
# Vertex AI Claude Backend
# ---------------------------------------------------------------------------

class VertexAIClaudeBackend:
    """Anthropic Claude via Vertex AI."""

    def __init__(
        self,
        model_id: str = "claude-opus-4-6",
        project_id: str | None = None,
        location: str | None = None,
        timeout: float | None = None,
    ):
        try:
            import anthropic
        except ImportError as e:
            raise ImportError(
                "anthropic package required for Vertex AI backend. "
                "Install with: pip install anthropic>=0.40.0"
            ) from e

        self._model_id = model_id
        self._timeout = timeout if timeout is not None else T2G_VERTEX_TIMEOUT

        # Get project_id and location from args or environment
        self._project_id = project_id or os.environ.get("T2G_VERTEX_PROJECT_ID")
        # Global endpoint matches current Vertex Claude 4.x model garden defaults; regional IDs
        # (e.g. us-east5) often 404 for the same model name.
        self._location = location or os.environ.get("T2G_VERTEX_LOCATION", "global")

        if not self._project_id:
            # Try to get from gcloud config
            try:
                import subprocess
                result = subprocess.run(
                    ["gcloud", "config", "get-value", "project"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    self._project_id = result.stdout.strip()
            except Exception:
                pass

        if not self._project_id:
            raise ValueError(
                "Vertex AI project ID required. Set T2G_VERTEX_PROJECT_ID or configure gcloud."
            )

        creds = _vertex_service_account_credentials()
        kw: dict[str, Any] = dict(project_id=self._project_id, region=self._location)
        if creds is not None:
            kw["credentials"] = creds

        # Create Anthropic client for Vertex AI
        self._client = anthropic.AnthropicVertex(**kw)

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def supports_tools(self) -> bool:
        """Indicates this backend supports Anthropic-style tool calls."""
        return True

    def chat(
        self,
        messages: list[dict],
        *,
        system: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
        stream: bool = False,
        budget_tokens: int | None = None,  # deprecated, for backward compat
        effort: str | None = None,  # "low" | "medium" | "high" | "max"
        disable_thinking: bool = False,  # If True, disable thinking entirely
        tools: list[dict] | None = None,
    ) -> str | Any:
        """Generate a response from chat messages using Claude.

        Args:
            messages: Chat messages in OpenAI/Anthropic format.
            system: System prompt (optional).
            max_tokens: Maximum tokens to generate.
            temperature: Sampling temperature.
            top_p: Top-p sampling (ignored for Claude 4.6 models).
            stream: If True, stream tokens and print progress (for perceived latency).
            budget_tokens: Extended thinking budget (deprecated on 4.6, use effort instead).
            effort: Thinking effort level for adaptive thinking ("low", "medium", "high", "max").
                    "medium" is recommended - skips thinking for simple requests.
            disable_thinking: If True, disable thinking entirely (for fast first-turn responses).
            tools: List of tool definitions for function calling.

        Returns:
            If tools is None: The generated text content (thinking blocks are stripped).
            If tools is provided: The full response object for processing tool calls.
        """
        # Extract system message if present in messages
        system_content = system
        chat_messages = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system" and system_content is None:
                system_content = content
            elif role in ("user", "assistant"):
                chat_messages.append({
                    "role": role,
                    "content": content,
                })

        t0 = time.perf_counter()

        import anthropic as anthropic_mod

        max_attempts = max(
            1, int((os.environ.get("T2G_VERTEX_RETRY_MAX") or "4").strip() or "4")
        )
        base_delay = float(
            (os.environ.get("T2G_VERTEX_RETRY_BASE_S") or "3.0").strip() or "3.0"
        )
        response = None
        last_exc: BaseException | None = None
        samp = _anthropic_sampling_kwargs_for_model(
            self._model_id, temperature, top_p
        )
        for attempt in range(max_attempts):
            try:
                api_kwargs: dict[str, Any] = {
                    "model": self._model_id,
                    "max_tokens": max_tokens,
                    "system": system_content or "",
                    "messages": chat_messages,
                    "timeout": self._timeout,
                    **samp,
                }
                # Thinking configuration
                thinking_enabled = False
                if disable_thinking:
                    # Disable thinking entirely for fast responses
                    api_kwargs["thinking"] = {"type": "disabled"}
                    thinking_enabled = True
                else:
                    # Adaptive thinking (recommended for 4.6 models)
                    # Apply default effort if not specified
                    resolved_effort = effort if effort is not None else _default_effort()
                    if resolved_effort is not None:
                        api_kwargs["thinking"] = {"type": "adaptive"}
                        api_kwargs["output_config"] = {"effort": resolved_effort}
                        thinking_enabled = True
                    elif budget_tokens is not None:
                        # Fallback for older models (deprecated on 4.6)
                        api_kwargs["budget_tokens"] = budget_tokens
                        thinking_enabled = True

                # Claude 4.6 requires temperature=1 when thinking is enabled
                if thinking_enabled and "temperature" in api_kwargs:
                    api_kwargs["temperature"] = 1.0

                if tools is not None:
                    api_kwargs["tools"] = tools

                response = self._client.messages.create(**api_kwargs)
                break
            except anthropic_mod.RateLimitError as e:
                last_exc = e
                if attempt + 1 >= max_attempts:
                    raise
                delay = base_delay * (2**attempt)
                silent = (os.environ.get("T2G_SILENT_LLM_STATS") or "").strip().lower() in (
                    "1",
                    "true",
                    "yes",
                    "on",
                )
                if not silent:
                    print(
                        f"[LLM] Vertex 429 quota/rate limit — retry "
                        f"{attempt + 1}/{max_attempts} after {delay:.1f}s…",
                        flush=True,
                    )
                time.sleep(delay)

        if response is None:
            raise last_exc or RuntimeError("Vertex messages.create returned no response")

        elapsed = time.perf_counter() - t0

        # Log stats
        usage = response.usage
        n_input = usage.input_tokens if usage else 0
        n_output = usage.output_tokens if usage else 0
        _log_chat_stats("claude", n_input, n_output, elapsed)

        # If tools were provided, return full response for tool processing
        if tools is not None:
            return response

        # Otherwise, extract text from response (skip thinking blocks)
        text = ""
        for block in response.content:
            # Extended thinking responses have 'thinking' type blocks we skip
            if getattr(block, "type", None) == "text":
                text += block.text
            elif hasattr(block, "text") and getattr(block, "type", None) != "thinking":
                text += block.text

        return text

    def chat_stream(
        self,
        messages: list[dict],
        *,
        system: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
    ) -> str:
        """Stream response from Claude, printing tokens as they arrive.

        This provides better perceived latency for long-running generations.
        Returns the complete text after streaming finishes.
        """
        import anthropic as anthropic_mod

        system_content = system
        chat_messages = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system" and system_content is None:
                system_content = content
            elif role in ("user", "assistant"):
                chat_messages.append({"role": role, "content": content})

        t0 = time.perf_counter()
        samp = _anthropic_sampling_kwargs_for_model(self._model_id, temperature, top_p)

        silent = (os.environ.get("T2G_SILENT_LLM_STATS") or "").strip().lower() in (
            "1", "true", "yes", "on"
        )

        text_parts: list[str] = []
        n_input = 0
        n_output = 0

        with self._client.messages.stream(
            model=self._model_id,
            max_tokens=max_tokens,
            system=system_content or "",
            messages=chat_messages,
            timeout=self._timeout,
            **samp,
        ) as stream:
            for event in stream:
                if event.type == "content_block_delta" and hasattr(event, "delta"):
                    delta = event.delta
                    if hasattr(delta, "text"):
                        chunk = delta.text
                        text_parts.append(chunk)
                        if not silent:
                            print(chunk, end="", flush=True)
                elif event.type == "message_start":
                    if hasattr(event, "message") and hasattr(event.message, "usage"):
                        n_input = getattr(event.message.usage, "input_tokens", 0) or 0

            # Get final message for output token count
            final_msg = stream.get_final_message()
            n_output = getattr(final_msg.usage, "output_tokens", 0) or 0

        elapsed = time.perf_counter() - t0
        if not silent:
            print()  # Newline after streaming

        text = "".join(text_parts)
        _log_chat_stats("claude_stream", n_input, n_output, elapsed)
        return text


class AnthropicHttpBackend:
    """Anthropic Messages API over HTTP (e.g. LiteLLM proxy to Vertex GLM)."""

    def __init__(
        self,
        model_id: str,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        try:
            import anthropic
        except ImportError as e:
            raise ImportError(
                "HTTP Anthropic backend needs anthropic. pip install anthropic>=0.40.0"
            ) from e

        self._model_id = model_id
        self._timeout = T2G_VERTEX_TIMEOUT  # Share timeout config with Vertex backend
        bu = (
            base_url
            or os.environ.get("ANTHROPIC_BASE_URL")
            or "http://127.0.0.1:4000"
        ).rstrip("/")
        key = (
            api_key
            or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            or os.environ.get("LITELLM_MASTER_KEY")
            or "sk-local-litellm-cc"
        ).strip()
        if not key:
            raise ValueError(
                "T2G_BACKEND=litellm requires ANTHROPIC_AUTH_TOKEN or "
                "LITELLM_MASTER_KEY (same as LiteLLM master_key)."
            )
        self._client = anthropic.Anthropic(api_key=key, base_url=bu, timeout=self._timeout)

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def supports_tools(self) -> bool:
        """Indicates this backend supports Anthropic-style tool calls."""
        return True

    def chat(
        self,
        messages: list[dict],
        *,
        system: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
        budget_tokens: int | None = None,  # deprecated, for backward compat
        effort: str | None = None,  # "low" | "medium" | "high" | "max"
        disable_thinking: bool = False,  # If True, disable thinking entirely
        tools: list[dict] | None = None,
    ) -> str | Any:
        system_content = system
        chat_messages: list[dict] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system" and system_content is None:
                system_content = content
            elif role in ("user", "assistant"):
                chat_messages.append({"role": role, "content": content})

        t0 = time.perf_counter()
        import anthropic as anthropic_mod

        max_attempts = max(
            1, int((os.environ.get("T2G_VERTEX_RETRY_MAX") or "4").strip() or "4")
        )
        base_delay = float(
            (os.environ.get("T2G_VERTEX_RETRY_BASE_S") or "3.0").strip() or "3.0"
        )
        samp = _anthropic_sampling_kwargs_for_model(
            self._model_id, temperature, top_p
        )
        response = None
        last_exc: BaseException | None = None
        for attempt in range(max_attempts):
            try:
                api_kwargs: dict[str, Any] = {
                    "model": self._model_id,
                    "max_tokens": max_tokens,
                    "system": system_content or "",
                    "messages": chat_messages,
                    "timeout": self._timeout,
                    **samp,
                }
                # Thinking configuration
                thinking_enabled = False
                if disable_thinking:
                    # Disable thinking entirely for fast responses
                    api_kwargs["thinking"] = {"type": "disabled"}
                    thinking_enabled = True
                else:
                    # Adaptive thinking (recommended for 4.6 models)
                    # Apply default effort if not specified
                    resolved_effort = effort if effort is not None else _default_effort()
                    if resolved_effort is not None:
                        api_kwargs["thinking"] = {"type": "adaptive"}
                        api_kwargs["output_config"] = {"effort": resolved_effort}
                        thinking_enabled = True
                    elif budget_tokens is not None:
                        # Fallback for older models (deprecated on 4.6)
                        api_kwargs["budget_tokens"] = budget_tokens
                        thinking_enabled = True

                # Claude 4.6 requires temperature=1 when thinking is enabled
                if thinking_enabled and "temperature" in api_kwargs:
                    api_kwargs["temperature"] = 1.0

                if tools is not None:
                    api_kwargs["tools"] = tools

                response = self._client.messages.create(**api_kwargs)
                break
            except anthropic_mod.RateLimitError as e:
                last_exc = e
                if attempt + 1 >= max_attempts:
                    raise
                delay = base_delay * (2**attempt)
                silent = (os.environ.get("T2G_SILENT_LLM_STATS") or "").strip().lower() in (
                    "1",
                    "true",
                    "yes",
                    "on",
                )
                if not silent:
                    print(
                        f"[LLM] 429 rate limit — retry "
                        f"{attempt + 1}/{max_attempts} after {delay:.1f}s…",
                        flush=True,
                    )
                time.sleep(delay)

        if response is None:
            raise last_exc or RuntimeError("messages.create returned no response")

        elapsed = time.perf_counter() - t0
        usage = response.usage
        n_input = usage.input_tokens if usage else 0
        n_output = usage.output_tokens if usage else 0
        _log_chat_stats("http", n_input, n_output, elapsed)

        # If tools were provided, return full response for tool processing
        if tools is not None:
            return response

        # Otherwise, extract text from response (skip thinking blocks)
        text = ""
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text += block.text
            elif hasattr(block, "text") and getattr(block, "type", None) != "thinking":
                text += block.text
        return text


def _log_chat_stats(label: str, n_prompt: int, n_gen: int, wall_seconds: float) -> None:
    """Print token counts and throughput after chat (one line, flushed)."""
    v = (os.environ.get("T2G_SILENT_LLM_STATS") or "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return
    parts = [
        f"{label}: {n_prompt} prompt + {n_gen} new toks",
        f"{wall_seconds * 1000.0:.0f}ms wall",
    ]
    if wall_seconds > 0 and n_gen > 0:
        parts.append(f"{n_gen / wall_seconds:.1f} tok/s (wall)")
    print("[LLM] " + " | ".join(parts), flush=True)


def _is_litellm_http_backend() -> bool:
    """Anthropic-compatible HTTP proxy (e.g. LiteLLM)."""
    backend = os.environ.get("T2G_BACKEND", "litellm").lower().strip()
    return backend in ("litellm", "litellm_proxy", "anthropic_http")


def _is_vertex_backend() -> bool:
    """Check if Vertex AI backend is selected."""
    backend = os.environ.get("T2G_BACKEND", "litellm").lower().strip()
    return backend in ("vertex", "vertexai", "anthropic", "claude")


def load_litellm_http_llm(model_id: str | None = None) -> AnthropicHttpBackend:
    """LiteLLM / Anthropic HTTP Messages API."""
    mid = (model_id or "").strip() or (os.environ.get("T2G_MODEL_ID") or "").strip()
    if not mid:
        mid = DEFAULT_MODEL_ID
    return AnthropicHttpBackend(model_id=mid)


def load_vertex_llm(
    model_id: str | None = None,
    project_id: str | None = None,
    location: str | None = None,
    timeout: float | None = None,
) -> VertexAIClaudeBackend:
    """Load Vertex AI Claude backend.

    Args:
        model_id: Claude model ID (e.g., 'claude-opus-4-6').
        project_id: GCP project ID (falls back to T2G_VERTEX_PROJECT_ID or gcloud config).
        location: Vertex AI location (defaults to 'global').
        timeout: Request timeout in seconds (defaults to T2G_VERTEX_TIMEOUT env var, or 120s).
    """
    mid = (model_id or "").strip() or (os.environ.get("T2G_MODEL_ID") or "").strip()
    if not mid:
        mid = "claude-opus-4-6"

    return VertexAIClaudeBackend(
        model_id=mid,
        project_id=project_id,
        location=location,
        timeout=timeout,
    )

if not (os.environ.get("CUDA_VISIBLE_DEVICES") or "").strip():
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"

_vllm_bundle: tuple[Any, Any, Any, Any] | None = None
_llm_cache: dict[tuple[Any, ...], Any] = {}


def _get_vllm_bundle() -> tuple[Any, Any, Any, Any]:
    """Import torch/vLLM only when the vLLM code path runs (Vertex backend skips this)."""
    global _vllm_bundle
    if _vllm_bundle is None:
        import torch
        from vllm import LLM as VllmLLM
        from vllm.sampling_params import SamplingParams, StructuredOutputsParams

        _vllm_bundle = (torch, VllmLLM, SamplingParams, StructuredOutputsParams)
    return _vllm_bundle

# load_llm(..., structured_outputs_config=None) must mean "no reasoning parser", not "apply default".
_MISSING_SO: Any = object()

# Default vLLM weights for WGSL + JSON agents (override with T2G_MODEL_ID or load_llm(model_id=...)).
DEFAULT_VLLM_MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct-AWQ"

# Qwen3/Qwen3.5 end reasoning with </think> (vLLM qwen3_reasoning_parser).
_THINK_END_MARKERS = (
    "</redacted_thinking>",
    "`</redacted_thinking>`",
)


def _default_max_model_len() -> int:
    env = (os.environ.get("T2G_MAX_MODEL_LEN") or "").strip()
    if env.isdigit():
        return max(256, int(env))
    return 16384


def _default_async_scheduling_for_model(model_id: str) -> bool | None:
    """Return False to disable vLLM async scheduling, True to enable, None to use vLLM defaults."""
    v = (os.environ.get("T2G_VLLM_ASYNC_SCHEDULING") or "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    if "qwen3" in model_id.lower():
        return False
    mid = model_id.lower()
    if "internvl" in mid or "intern_vit" in mid:
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
    """Whether Qwen3 chat uses enable_thinking (reasoning channel).

    Env ``T2G_QWEN_THINKING``: force on (1) or off (0). If unset: off for generic Qwen3, on when the
    model id looks Thinking-tuned (substring ``thinking``), so WGSL is not buried in long plain prose.
    """
    if "qwen3" not in model_id.lower():
        return False
    v = os.environ.get("T2G_QWEN_THINKING", "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    if v in ("1", "true", "yes", "on"):
        return True
    return "thinking" in model_id.lower()


def chat_kwargs_for_model(model_id: str, *, multimodal: bool = False) -> dict[str, Any]:
    """vLLM llm.chat() extras.

    Set ``multimodal=True`` when the messages contain image_url content;
    this skips ``chat_template_content_format="string"`` which would
    prevent vLLM from routing images to the vision encoder.
    """
    kw: dict[str, Any] = {}
    if glm_thinking_enabled(model_id):
        kw["chat_template_kwargs"] = {"enable_thinking": True}
    elif qwen3_thinking_enabled(model_id):
        kw["chat_template_kwargs"] = {"enable_thinking": True}
    elif "qwen3" in model_id.lower():
        kw["chat_template_kwargs"] = {"enable_thinking": False}
    mid_lower = model_id.lower()
    if not multimodal and ("internvl" in mid_lower or "intern_vit" in mid_lower):
        kw["chat_template_content_format"] = "string"
    return kw


def log_chat_generation_stats(
    outputs: list[Any],
    wall_seconds: float,
    *,
    label: str = "chat",
) -> None:
    """Print token counts and throughput after ``llm.chat`` (one line, flushed).

    Uses vLLM ``RequestOutput.metrics`` (``RequestStateStats``) when present for decode timing;
    otherwise only wall-clock rates.
    """
    v = (os.environ.get("T2G_SILENT_LLM_STATS") or "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return
    if not outputs:
        return
    ro = outputs[0]
    gen = ro.outputs[0]
    n_gen = len(gen.token_ids)
    pti = ro.prompt_token_ids
    n_pre = len(pti) if pti is not None else 0
    parts = [
        f"{label}: {n_pre} prompt + {n_gen} new toks",
        f"{wall_seconds * 1000.0:.0f}ms wall",
    ]
    if wall_seconds > 0 and n_gen > 0:
        parts.append(f"{n_gen / wall_seconds:.1f} tok/s (wall)")
    m = getattr(ro, "metrics", None)
    if m is not None:
        ft = float(getattr(m, "first_token_ts", 0.0) or 0.0)
        lt = float(getattr(m, "last_token_ts", 0.0) or 0.0)
        n_m = int(getattr(m, "num_generation_tokens", 0) or 0)
        if lt > ft and n_m > 0:
            parts.append(f"{n_m / (lt - ft):.1f} tok/s (decode)")
        ftl = getattr(m, "first_token_latency", None)
        if isinstance(ftl, (int, float)) and ftl > 0:
            parts.append(f"TTFT {ftl * 1000.0:.0f}ms")
    print("[LLM] " + " | ".join(parts), flush=True)


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
) -> Any:
    """Load (or reuse cached) vLLM instance OR Vertex AI Claude backend.

    Backend selection: Set `T2G_BACKEND=vertex` to use Vertex AI Claude.
    For Vertex AI, set `T2G_VERTEX_PROJECT_ID` and optionally `T2G_VERTEX_LOCATION`.

    Model resolution: ``model_id`` argument if non-empty, else ``T2G_MODEL_ID``, else
    ``DEFAULT_VLLM_MODEL_ID`` (Qwen2.5-Coder-32B-Instruct-AWQ) for vLLM, or
    `claude-opus-4-6` for Vertex AI.

    For GLM models, thinking + structured output reasoning follow the upstream vLLM recipe
    (reasoning_parser glm45, enable_in_reasoning) unless disabled via T2G_GLM_THINKING=0 or
    by passing structured_outputs_config explicitly.
    """
    if _is_litellm_http_backend():
        return load_litellm_http_llm(model_id=model_id)
    # Dispatch to Vertex AI backend if requested
    if _is_vertex_backend():
        return load_vertex_llm(model_id=model_id)

    mid = (model_id or "").strip() or (os.environ.get("T2G_MODEL_ID") or "").strip()
    if not mid:
        mid = DEFAULT_VLLM_MODEL_ID

    torch, LLM, _, _ = _get_vllm_bundle()

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

    enforce_eager = kwargs.pop("enforce_eager", None)
    if enforce_eager is None:
        _ee = (os.environ.get("T2G_ENFORCE_EAGER") or "").strip().lower()
        if _ee in ("1", "true", "yes", "on"):
            enforce_eager = True

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
    if llm_kwargs.get("quantization") is None and "awq" in mid.lower():
        llm_kwargs["quantization"] = "awq_marlin"
    if enforce_eager:
        llm_kwargs["enforce_eager"] = True
    if resolved_async is not None:
        llm_kwargs["async_scheduling"] = resolved_async
    if structured_outputs_config is not None:
        llm_kwargs["structured_outputs_config"] = structured_outputs_config

    llm = LLM(**llm_kwargs)
    _llm_cache[cache_key] = llm
    return llm


def generate_scene_json(
    messages: list[dict[str, str]],
    llm: Any,
    json_schema: dict,
    max_new_tokens: int = 4096,
    temperature: float = 0.6,
    top_p: float = 0.95,
) -> dict:
    """Generate a scene JSON object from chat messages using structured output.

    Uses StructuredOutputsParams(json=...) so the model's raw output is guaranteed
    to be valid JSON matching the schema. GLM thinking is stripped before parsing.
    """
    _, _, SamplingParams, StructuredOutputsParams = _get_vllm_bundle()
    structured = StructuredOutputsParams(json=json.dumps(json_schema))
    sampling = SamplingParams(
        structured_outputs=structured,
        max_tokens=max_new_tokens,
        temperature=temperature,
        top_p=top_p,
    )

    mid = llm.model_config.model
    chat_kwargs = chat_kwargs_for_model(mid)

    t0 = time.perf_counter()
    outputs = llm.chat(messages, sampling_params=sampling, **chat_kwargs)
    log_chat_generation_stats(outputs, time.perf_counter() - t0, label="json_scene")
    text = outputs[0].outputs[0].text
    text = strip_visible_thinking(text)
    return json.loads(text)


def generate_wgsl_code(
    messages: list[dict[str, str]],
    llm: Any,
    max_new_tokens: int = 512,
    temperature: float = 0.7,
    top_p: float = 0.95,
) -> str:
    """Generate WGSL SDF code from chat messages (plain text, no structured output).

    Works with both vLLM and Vertex AI Claude backends.
    Default is 512 tokens — WGSL map() functions are typically 50-300 tokens.
    Override with env ``T2G_WGSL_MAX_TOKENS``.
    """
    mt = max_new_tokens
    _mt_env = (os.environ.get("T2G_WGSL_MAX_TOKENS") or "").strip()
    if _mt_env.isdigit():
        mt = max(256, int(_mt_env))

    # Anthropic Messages API (Vertex or HTTP / LiteLLM proxy)
    if isinstance(llm, (VertexAIClaudeBackend, AnthropicHttpBackend)):
        # Extract system message for Claude
        system_msg = None
        chat_messages = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system" and system_msg is None:
                system_msg = content
            elif role in ("user", "assistant"):
                chat_messages.append({"role": role, "content": content})

        # Get extended thinking budget from env (Opus 4.x only)
        budget = _default_budget_tokens()

        text = llm.chat(
            chat_messages,
            system=system_msg,
            max_tokens=mt,
            temperature=temperature,
            top_p=top_p,
            budget_tokens=budget,
        )
        return strip_visible_thinking(text)

    # vLLM backend
    _, _, SamplingParams, _ = _get_vllm_bundle()
    mid = llm.model_config.model
    if not _mt_env.isdigit() and qwen3_thinking_enabled(mid):
        mt = max(mt, 6144)

    sampling = SamplingParams(
        max_tokens=mt,
        temperature=temperature,
        top_p=top_p,
    )

    chat_kwargs = chat_kwargs_for_model(mid)
    # GLM + enable_thinking spends max_tokens inside thinking; WGSL `fn map` then truncates or
    # never appears. Plain-text WGSL needs a direct answer (JSON path keeps thinking on).
    if glm_thinking_enabled(mid):
        chat_kwargs = {"chat_template_kwargs": {"enable_thinking": False}}

    t0 = time.perf_counter()
    outputs = llm.chat(messages, sampling_params=sampling, **chat_kwargs)
    log_chat_generation_stats(outputs, time.perf_counter() - t0, label="wgsl")
    text = outputs[0].outputs[0].text
    return strip_visible_thinking(text)
