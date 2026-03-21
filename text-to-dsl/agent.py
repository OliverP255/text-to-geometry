#!/usr/bin/env python3
"""
LLM Agent: plan -> write DSL -> choose-and-edit loop until submit.
Usage: python agent.py

Prompts for shape descriptions, plans, generates DSL, allows edits. Type 'quit' or 'exit' to stop.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Add build/ and text-to-dsl/ for t2g and inference
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "build"))
sys.path.insert(0, str(_root / "text-to-dsl"))

import text_to_geometry_bindings as t2g
from agent_edits import apply_edits
from agent_tools import evaluate_loss, optimise_params_for_target
from inference import generate_dsl, generate_with_grammar, load_llm, warmup_prefix_cache
from target_sdf import sphere_target

_agent_dir = Path(__file__).resolve().parent
_default_dsl = _agent_dir / "workspace" / "scene.dsl"
_default_plan = _agent_dir / "workspace" / "plan"
DSL_PATH = Path(os.environ.get("AGENT_DSL_FILE", str(_default_dsl)))
PLAN_PATH = Path(os.environ.get("AGENT_PLAN_FILE", str(_default_plan)))
FLATIR_PATH = DSL_PATH.with_suffix(".pkl")
SERVER_URL = os.environ.get("SCENE_SERVER_URL", "http://localhost:5001/scene")
GRAMMAR_PLAN = _agent_dir / "grammar_plan.gbnf"
GRAMMAR_DSL = _agent_dir / "grammar_dsl.gbnf"
GRAMMAR_CHOICE_INFERENCE = _agent_dir / "grammar_choice_inference.gbnf"
GRAMMAR_CHOICE_TRAINING = _agent_dir / "grammar_choice_training.gbnf"
GRAMMAR_EDIT_PLAN = _agent_dir / "grammar_edit_plan.gbnf"
GRAMMAR_EDIT_DSL = _agent_dir / "grammar_edit_dsl.gbnf"

VALID_CHOICES_INFERENCE = {"edit_plan", "edit_dsl", "rewrite_plan", "rewrite_dsl", "submit"}
VALID_CHOICES_TRAINING = VALID_CHOICES_INFERENCE | {"eval_loss", "optimise_dsl"}


def parse_choice(text: str, training: bool = False) -> str:
    """Parse choice string, strip whitespace, validate."""
    choice = text.strip().lower()
    valid = VALID_CHOICES_TRAINING if training else VALID_CHOICES_INFERENCE
    if choice not in valid:
        raise ValueError(f"Unknown choice: {choice!r}")
    return choice


def parse_edit_json(text: str, tool: str) -> dict:
    """Parse edit JSON, validate tool and edits."""
    d = json.loads(text)
    if d.get("tool") != tool:
        raise ValueError(f"Expected tool={tool!r}, got {d.get('tool')!r}")
    if "edits" not in d:
        raise ValueError("Missing 'edits' key")
    return d


def _post_dsl(dsl: str) -> None:
    """POST DSL to SCENE_SERVER_URL. Server compiles and packs."""
    data = json.dumps({"dsl": dsl}).encode("utf-8")
    req = urllib.request.Request(
        SERVER_URL,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10):
        pass


def run_agent(
    llm,
    user_input: str,
    dsl_path: Path,
    plan_path: Path,
    training_mode: bool = False,
) -> None:
    """
    Linear flow: plan phase -> write DSL phase -> choose-and-edit loop until submit.
    """
    dsl_path = Path(dsl_path)
    plan_path = Path(plan_path)
    dsl_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.parent.mkdir(parents=True, exist_ok=True)

    # Plan phase
    plan_prompt = "Plan out the DSL: " + user_input
    plan_content = generate_with_grammar(plan_prompt, GRAMMAR_PLAN, llm=llm, max_new_tokens=256)
    plan_path.write_text(plan_content.strip())

    # Write DSL phase
    write_prompt = "Write the DSL from the plan:\n\n" + plan_content.strip()
    dsl = generate_with_grammar(write_prompt, GRAMMAR_DSL, llm=llm, max_new_tokens=128)
    dsl = dsl.strip()
    dsl_path.write_text(dsl)

    # POST inline (auto-render)
    try:
        _post_dsl(dsl)
    except urllib.error.URLError as e:
        print(f"Server POST failed: {e}", file=sys.stderr)

    # Choose-and-edit loop
    choice_grammar = GRAMMAR_CHOICE_TRAINING if training_mode else GRAMMAR_CHOICE_INFERENCE
    while True:
        plan_content = plan_path.read_text()
        dsl = dsl_path.read_text()
        choice_prompt = (
            "Choose one of: edit plan, edit dsl, rewrite plan, rewrite dsl"
            + (" or submit final DSL" if not training_mode else ", evaluate loss, optimise dsl, or submit final DSL")
            + "\n\nPlan:\n"
            + plan_content
            + "\n\nDSL:\n"
            + dsl
            + "\n\nChoice:"
        )
        choice_text = generate_with_grammar(choice_prompt, choice_grammar, llm=llm, max_new_tokens=16)
        try:
            choice = parse_choice(choice_text, training=training_mode)
        except ValueError as e:
            print(f"Choice parse error: {e}", file=sys.stderr)
            continue

        if choice == "submit":
            break

        if choice == "edit_plan":
            edit_prompt = "Provide edits to the plan (find/replace only):\n\n" + plan_content + "\n\nJSON:"
            edit_text = generate_with_grammar(edit_prompt, GRAMMAR_EDIT_PLAN, llm=llm, max_new_tokens=256)
            try:
                d = parse_edit_json(edit_text.strip(), "edit_plan")
                plan_content = apply_edits(plan_content, d["edits"])
                plan_path.write_text(plan_content)
            except (ValueError, json.JSONDecodeError) as e:
                print(f"Edit error (returned to agent): {e}", file=sys.stderr)
            continue

        if choice == "edit_dsl":
            edit_prompt = "Provide edits to the DSL (find/replace only):\n\n" + dsl + "\n\nJSON:"
            edit_text = generate_with_grammar(edit_prompt, GRAMMAR_EDIT_DSL, llm=llm, max_new_tokens=256)
            try:
                d = parse_edit_json(edit_text.strip(), "edit_dsl")
                dsl = apply_edits(dsl, d["edits"])
                dsl_path.write_text(dsl)
                try:
                    _post_dsl(dsl)
                except urllib.error.URLError as e:
                    print(f"Server POST failed: {e}", file=sys.stderr)
            except (ValueError, json.JSONDecodeError) as e:
                print(f"Edit error (returned to agent): {e}", file=sys.stderr)
            continue

        if choice == "rewrite_plan":
            plan_prompt = "Plan out the DSL: " + user_input
            plan_content = generate_with_grammar(plan_prompt, GRAMMAR_PLAN, llm=llm, max_new_tokens=256)
            plan_path.write_text(plan_content.strip())
            continue

        if choice == "rewrite_dsl":
            plan_content = plan_path.read_text()
            write_prompt = "Write the DSL from the plan:\n\n" + plan_content + "\n\n"
            dsl = generate_with_grammar(write_prompt, GRAMMAR_DSL, llm=llm, max_new_tokens=128)
            dsl = dsl.strip()
            dsl_path.write_text(dsl)
            try:
                _post_dsl(dsl)
            except urllib.error.URLError as e:
                print(f"Server POST failed: {e}", file=sys.stderr)
            continue

        if choice == "eval_loss" and training_mode:
            target = sphere_target(radius=1.0)
            loss = evaluate_loss(dsl, target, seed=42)
            print(f"eval_loss: {loss:.6f}", file=sys.stderr)
            continue

        if choice == "optimise_dsl" and training_mode:
            target = sphere_target(radius=1.0)
            result = optimise_params_for_target(dsl, target, steps=500)
            dsl = t2g.unparseDSL(result)
            dsl_path.write_text(dsl)
            try:
                _post_dsl(dsl)
            except urllib.error.URLError as e:
                print(f"Server POST failed: {e}", file=sys.stderr)
            continue

    print(f"\nPlan:\n{plan_path.read_text()}\n")
    print(f"DSL:\n{dsl_path.read_text()}\n")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LLM Agent: plan -> write DSL -> choose-and-edit loop")
    parser.add_argument("--training", action="store_true", help="Enable training tools (eval_loss, optimise_dsl)")
    args = parser.parse_args()

    model_id = "mratsim/GLM-4.7-Flash-FP8"
    print(f"Loading model {model_id}...")
    llm = load_llm(model_id=model_id)
    print("Warming up prefix cache...")
    warmup_prefix_cache(llm)
    print("Ready. Describe a shape. Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            prompt = input("Input: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not prompt:
            continue
        if prompt.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break

        run_agent(llm, prompt, DSL_PATH, PLAN_PATH, training_mode=args.training)


if __name__ == "__main__":
    main()
