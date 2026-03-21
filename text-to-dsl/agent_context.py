"""Persistent prompts and sampling defaults for the LLM agent (text-to-dsl)."""

from __future__ import annotations

# Rich guide prepended to every agent LLM call; phase prompts stay short after this block.
AGENT_DSL_GUIDE = """You are authoring SDF (signed distance field) scenes in a small text DSL used by a compiler and WebGPU viewer.

DSL syntax:
- Shape variables: s0, s1, s2, ... in definition order. Transform variables: t0, t1, ...
- Primitives: sphere(r=NUM), box(x=NUM, y=NUM, z=NUM), plane(nx=NUM, ny=NUM, nz=NUM, d=NUM)
- Transforms: translate(x=NUM, y=NUM, z=NUM), scale(x=NUM, y=NUM, z=NUM)
- CSG: union(sA, sB, ...), intersect(...), subtract(sA, sB) — union/intersect need two or more shapes
- apply(tN, sM) applies transform tN to shape sM
- End with a single return sK (root shape). Comments: # or // to end of line

Rules:
- For any phase that emits DSL, output ONLY valid DSL — no LaTeX, no markdown essays, no proofs, no prose outside comments.
- Stay within these primitives and ops; do not invent cylinders or other ops not listed.

"""

# Appended after AGENT_DSL_GUIDE for plan and rewrite_plan only.
PLAN_RUBRIC_SUFFIX = """Plan phase:
- Plain English, short numbered or ordered steps.
- Refer to shapes as s0, s1, ... and transforms as t0, t1, ... in order.
- Do not use LaTeX or markdown section headings; do not work unrelated math homework — only a build plan for the DSL above.

"""

# Per-phase generation limits (max_model_len in load_llm is 1024 — avoid huge prompts).
AGENT_MAX_TOKENS_PLAN = 256
AGENT_MAX_TOKENS_DSL = 224
AGENT_MAX_TOKENS_CHOICE = 16
AGENT_MAX_TOKENS_EDIT = 256

AGENT_TEMP_PLAN = 0.2
AGENT_TEMP_DSL = 0.15
AGENT_TEMP_CHOICE = 0.1
AGENT_TEMP_EDIT = 0.15
