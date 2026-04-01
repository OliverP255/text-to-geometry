#!/usr/bin/env python3
"""Test agent on the CAD prompt suite (46 prompts in 5 category bands)."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "agent"))

from inference import load_llm
from wgsl_agent import run_agent, WGSL_SYSTEM_PROMPT
from wgsl_validator import validate_wgsl

# Category index ranges (prompt indices 1..N after renumber):
# 1–10   Classic CAD — measurements + numbered steps
# 11–20  Classic CAD — same parts, measurements, no steps
# 21–30  Classic CAD — same parts, no measurements, no steps
# 31–40  Classic CAD — same parts, vague / short
# 41–46  Organic (SDF-friendly smooth / curved solids)

PROMPTS = [
    # ── 1–10 Classic CAD — measurements + numbered steps ──────────────
    "L-bracket STEPS: 1) Vertical plate sdBox half-extents (0.055, 0.16, 0.14) center (0.075, 0, 0). 2) Horizontal plate sdBox (0.13, 0.055, 0.14) center (0, -0.075, 0). 3) opU. 4) Subtract optional fillet via sdRoundBox if desired. Units: scene meters.",
    "I-beam STEPS: 1) Web: sdBox (0.04, 0.2, 0.14) at origin. 2) Top flange: sdBox (0.12, 0.025, 0.14) at y=+0.225. 3) Bottom flange: same at y=-0.225. 4) opU all. Symmetric in X.",
    "Gear blank STEPS: 1) Main disc sdCylinder radius 0.28 half-height 0.045. 2) Subtract central hole cylinder r=0.09. 3) Subtract second hole cylinder r=0.045 center offset (+0.11, 0, 0).",
    "Flanged bearing STEPS: 1) Hollow main tube outer r=0.12 inner r=0.08 half-h=0.18. 2) Flange disc sdCylinder r=0.22 half-h=0.02 at y=-0.18. 3) opU tube and flange.",
    "Rivet STEPS: 1) Shank sdCylinder r=0.045 half-h=0.05 along Y. 2) Head sdSphere or sdSphere cap r=0.09 centered at (0, 0.11, 0). 3) opU.",
    "D-pull handle STEPS: 1) Bar sdCylinder radius 0.032, half-length 0.16 along X at y=+0.075. 2) Leg cylinders r=0.032 half-h=0.065 at (±0.16, -0.02, 0). 3) opU three pieces.",
    "Eccentric cam STEPS: 1) Base disc sdCylinder r=0.21 half-h=0.035. 2) Boss sdCylinder r=0.095 half-h=0.055 center (+0.115, 0, 0). 3) opU.",
    "Four-blade fan hub STEPS: 1) Hub sdCylinder r=0.095 half-h=0.055. 2) Blade sdBox (0.24, 0.018, 0.065) along +X. 3) opRotateY 90° and 180° and 270° copies union with hub—or four explicit blade boxes along ±X ±Z. 4) opU all.",
    "Hollow square tube STEPS: 1) Outer sdBox (0.095, 0.26, 0.095). 2) Subtract inner sdBox (0.078, 0.27, 0.078). Y vertical.",
    "Grille plate STEPS: 1) Plate sdBox (0.26, 0.032, 0.18). 2) For i=0..7 subtract slot sdBox (0.012, 0.04, 0.19) center at (-0.105 + i*0.03, 0, 0). Eight slots.",

    # ── 11–20 Classic CAD — measurements, no steps ───────────────────
    "L-bracket: Vertical plate half-extents (0.055, 0.16, 0.14) centered (0.075, 0, 0); horizontal plate (0.13, 0.055, 0.14) at (0, -0.075, 0); union; Y up.",
    "I-beam: Web box (0.04, 0.2, 0.14); top flange box (0.12, 0.025, 0.14) at y=0.225; bottom flange mirror at y=-0.225; union.",
    "Gear blank: Cylinder disc radius 0.28 half-height 0.045 minus central hole radius 0.09 minus offset hole radius 0.045 at (+0.11, 0, 0).",
    "Flanged bearing: Hollow cylinder outer 0.12 inner 0.08 half-height 0.18; union flange cylinder radius 0.22 half-height 0.02 with center at y=-0.18.",
    "Rivet: Shank cylinder radius 0.045 half-height 0.05; head sphere radius 0.09 centered (0, 0.11, 0); union.",
    "D-pull handle: Horizontal cylinder radius 0.032, axis along X, half-length 0.16, center y=0.075; two vertical cylinders same radius half-height 0.065 at x=±0.16, y=-0.02; union.",
    "Eccentric cam: Disc cylinder r=0.21 half-h=0.035 union boss cylinder r=0.095 half-h=0.055 at (+0.115, 0, 0).",
    "Fan hub four blades: Hub cylinder r=0.095 half-h=0.055; four thin box blades length 0.24 width 0.065 thickness 0.036 along +X, -X, +Z, -Z; union.",
    "Hollow square tube: Outer box half-extents (0.095, 0.26, 0.095) minus inner (0.078, 0.27, 0.078).",
    "Grille plate: Plate box (0.26, 0.032, 0.18); eight slot boxes half-extents (0.012, 0.04, 0.19) at x = -0.105 + i*0.03 for i=0..7; subtract all from plate.",

    # ── 21–30 Classic CAD — no measurements, no steps ────────────────
    "L-shaped mounting bracket: two perpendicular flat plates of uniform thickness meeting at ninety degrees, rounded outer corner, Y vertical.",
    "Structural I-beam segment: vertical web with horizontal top and bottom flanges, symmetric, all from box primitives.",
    "Gear blank disc: circular disc with a large central through-hole and one smaller off-center hole for a bolt pattern.",
    "Flanged bearing housing: short hollow shaft with a wider flat flange on one end, axis vertical.",
    "Rivet fastener: short cylindrical shank with a hemispherical or domed head on top.",
    "Cabinet D-pull handle: horizontal grip bar with two short vertical legs down to the mounting plane.",
    "Eccentric cam plate: circular base with a second thicker circular boss offset from the rotation center.",
    "Fan hub: central hub with four identical flat blades radiating along the cardinal horizontal directions, no twist.",
    "Hollow square structural tube: square outer profile with square inner void, long axis vertical.",
    "Perforated grille: flat plate with a row of evenly spaced long narrow through-slots.",

    # ── 31–40 Classic CAD — vague / short ─────────────────────────────
    "Small shelf angle bracket.",
    "Short piece of I-beam.",
    "Drilled gear disc.",
    "Bearing with a flange.",
    "Pop rivet shape.",
    "Drawer pull.",
    "Offset cam for a latch.",
    "Plastic fan wheel blank.",
    "Hollow square leg.",
    "Vent cover with slots.",

    # ── 41–46 Organic (SDF-friendly) ──────────────────────────────────
    "Smooth blob pair: two spheres radius 0.28, centers 0.32 apart on X; combine with smooth union, blend parameter k≈0.12.",
    "Fillet cluster: sdRoundBox main (0.14, 0.14, 0.14) corner radius 0.03 union smooth with sphere radius 0.1 at outer +X+Y+Z corner, k≈0.1.",
    "Ellipsoid egg: axis-aligned ellipsoid semi-axes 0.22, 0.32, 0.18 centered at origin—smooth closed surface.",
    "Triple metaball-style: smooth union of three spheres radii 0.2, 0.18, 0.16 with centers forming a triangle in XZ at slightly different Y, k≈0.08.",
    "Soft pebble: smooth union of sdCapsule along slight diagonal and sphere offset, k≈0.11—one continuous rounded mass.",
    "Domed organic mound: sdSphere radius 0.45 center (0, 0.12, 0) union smooth with wider sdCylinder pedestal radius 0.35 half-height 0.08, k≈0.14.",
]


def main() -> None:
    n_all = len(PROMPTS)
    parser = argparse.ArgumentParser(description=f"Run up to {n_all} WGSL CAD prompts through the agent.")
    parser.add_argument(
        "--post",
        action="store_true",
        help="POST valid WGSL to SCENE_SERVER_URL (default: http://localhost:5001/scene/wgsl)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Retries after validation failure (default: 2)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="vLLM HuggingFace model id (else T2G_MODEL_ID or Qwen3-32B-FP8 default)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for generated .wgsl files (default: agent/experiments/outputs)",
    )
    parser.add_argument(
        "--results-json",
        type=Path,
        default=None,
        help="Write machine-readable summary JSON (default: <output-dir>/results.json if --output-dir set)",
    )
    parser.add_argument(
        "--max-prompts",
        type=int,
        default=None,
        help=f"Only run first K prompts (1..K), for smoke tests (default: all {n_all})",
    )
    args = parser.parse_args()

    exp_dir = Path(__file__).resolve().parent
    out_dir = (args.output_dir or (exp_dir / "outputs")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    results_json = args.results_json
    if results_json is None and args.output_dir is not None:
        results_json = out_dir / "results.json"

    k = args.max_prompts if args.max_prompts is not None else n_all
    k = max(0, min(k, n_all))
    run_prompts = PROMPTS[:k]

    resolved_model = (args.model or os.environ.get("T2G_MODEL_ID") or "").strip() or "Qwen/Qwen3-32B-FP8"
    label = resolved_model.split("/")[-1]

    print(f"Loading LLM: {resolved_model} …")
    llm = load_llm(model_id=resolved_model, structured_outputs_config=None)
    print("LLM loaded.\n")
    if args.post:
        print("POST to scene server: enabled\n")

    results: list[tuple[int, str, str | None, str | None]] = []
    passed = 0
    failed = 0
    returned = 0
    per_prompt: list[dict] = []

    for i, prompt in enumerate(run_prompts, start=1):
        print(f"[{i:2d}/{k}] Testing: {prompt[:60]}...")

        try:
            code = run_agent(
                llm,
                prompt,
                attempt_post=args.post,
                verbose=False,
                max_retries=args.max_retries,
            )

            if code is None:
                print("        FAILED: Agent returned None after retries")
                failed += 1
                results.append((i, prompt, None, "Agent returned None"))
                per_prompt.append(
                    {
                        "n": i,
                        "prompt": prompt,
                        "ok": False,
                        "error": "Agent returned None",
                        "code_len": 0,
                    }
                )
                continue

            returned += 1
            ok, err = validate_wgsl(code)
            if ok:
                print(f"        PASSED ({len(code)} chars)")
                passed += 1
                results.append((i, prompt, code, None))
                per_prompt.append({"n": i, "prompt": prompt, "ok": True, "error": None, "code_len": len(code)})
            else:
                print(f"        FAILED validation: {err}")
                failed += 1
                results.append((i, prompt, code, err))
                per_prompt.append({"n": i, "prompt": prompt, "ok": False, "error": err, "code_len": len(code)})

        except Exception as e:
            print(f"        ERROR: {e}")
            failed += 1
            results.append((i, prompt, None, str(e)))
            per_prompt.append({"n": i, "prompt": prompt, "ok": False, "error": str(e), "code_len": 0})

    print(f"\n{'='*60}")
    print(f"RESULTS: validation_ok {passed}/{k}, agent_returned_code {returned}/{k}")
    print(f"{'='*60}\n")

    if failed > 0:
        print("Issues:")
        for i, prompt, code, err in results:
            if err:
                print(f"  [{i}] {prompt[:50]}...")
                print(f"      {err}")
                if code:
                    print(f"      Code: {code[:100]}...")
                print()

    for i, prompt, code, _ in results:
        safe_name = prompt.split(":")[0].replace(" ", "_").replace("/", "_")[:30]
        out_path = out_dir / f"{i:02d}_{safe_name}.wgsl"
        if code:
            out_path.write_text(
                f"// Prompt: {prompt}\n// Model: {resolved_model}\n// Generated WGSL SDF\n\n{code}",
                encoding="utf-8",
            )
        elif out_path.is_file():
            out_path.unlink()

    if results_json is not None:
        payload = {
            "label": label,
            "model_id": resolved_model,
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "prompt_count": k,
            "validation_passed": passed,
            "agent_returned_code": returned,
            "per_prompt": per_prompt,
        }
        results_json.parent.mkdir(parents=True, exist_ok=True)
        results_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {results_json}")

    print(f"Generated files saved to {out_dir}")


if __name__ == "__main__":
    main()
