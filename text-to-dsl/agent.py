#!/usr/bin/env python3
"""
LLM Agent: plan -> write DSL -> choose-and-edit loop until submit.
Usage: python agent.py

Prompts for shape descriptions, plans, generates DSL, allows edits. Type 'quit' or 'exit' to stop.

If you run `python3 agent.py` with system Python, we re-exec using repo `.venv` when present
(so torch/vLLM import). Set T2G_NO_VENV_REEXEC=1 to disable.
"""

import os
import sys
from pathlib import Path




_reexec_with_repo_venv_if_needed()

import json
import urllib.error
import urllib.request

# Add build/ and text-to-dsl/ for t2g and inference
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "build"))
sys.path.insert(0, str(_root / "text-to-dsl"))

import text_to_geometry_bindings as t2g
from agent_context import (
    AGENT_DSL_GUIDE,
    AGENT_MAX_TOKENS_CHOICE,
    AGENT_MAX_TOKENS_DSL,
    AGENT_MAX_TOKENS_EDIT,
    AGENT_MAX_TOKENS_PLAN,
    AGENT_TEMP_CHOICE,
    AGENT_TEMP_DSL,
    AGENT_TEMP_EDIT,
    AGENT_TEMP_PLAN,
    PLAN_RUBRIC_SUFFIX,
)
from agent_edits import apply_edits
from agent_tools import evaluate_loss, optimise_params_for_target
from inference import generate_with_grammar, load_llm, validate_dsl, warmup_prefix_cache

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

PREFIX_ALL = AGENT_DSL_GUIDE.rstrip() + "\n\n"
PREFIX_PLAN = PREFIX_ALL + PLAN_RUBRIC_SUFFIX.rstrip() + "\n\n"


def get_training_target_sdf():
    """Target SDF for eval_loss / optimise_dsl. Hardcoded for now; swap for real targets later."""
    from target_sdf import sphere_target

    return sphere_target(radius=1.0)


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


def _truncate(s: str, n: int = 220) -> str:
    s = s.replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 3] + "..."


def _dsl_compile_status(dsl: str) -> tuple[bool, str]:
    ok, err = validate_dsl(dsl)
    if not ok:
        return False, err or "validate_dsl failed"
    try:
        t2g.compile(dsl)
    except ValueError as e:
        return False, str(e)
    return True, ""


def _post_dsl(dsl: str) -> tuple[bool, str | None]:
    """POST DSL to SCENE_SERVER_URL. Returns (ok, error_message)."""
    data = json.dumps({"dsl": dsl}).encode("utf-8")
    req = urllib.request.Request(
        SERVER_URL,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                body = resp.read().decode()
                try:
                    msg = json.loads(body).get("error", body)
                except json.JSONDecodeError:
                    msg = body or f"HTTP {resp.status}"
                return False, str(msg)[:500]
            return True, None
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            msg = json.loads(body).get("error", body)
        except json.JSONDecodeError:
            msg = body or str(e)
        return False, str(msg)[:500]
    except urllib.error.URLError as e:
        reason = getattr(e, "reason", None)
        return False, str(reason if reason is not None else e)


def _format_status(
    compile_ok: bool | None,
    compile_err: str,
    post_ok: bool | None,
    post_err: str | None,
    edit_err: str,
    tool_result: str,
    policy_hint: str,
) -> str:
    lines = ["Status:"]
    if compile_ok is True:
        lines.append("- compile: ok")
    elif compile_ok is False:
        lines.append(f"- compile: failed ({_truncate(compile_err)})")
    if post_ok is True:
        lines.append("- server_post: ok")
    elif post_ok is False:
        lines.append(f"- server_post: failed ({_truncate(post_err or '')})")
    elif post_ok is None and compile_ok is False:
        lines.append("- server_post: skipped (compile failed)")
    if edit_err:
        lines.append(f"- last_edit: failed ({_truncate(edit_err)})")
    if tool_result:
        lines.append(f"- tools: {tool_result}")
    if policy_hint:
        lines.append(f"- policy: {policy_hint}")
    return "\n".join(lines) + "\n\n"


def _choice_policy_hint(
    consec_compile_fail: int,
    consec_edit_fail: int,
    compile_ok: bool | None,
    post_ok: bool | None,
) -> str:
    parts = []
    if consec_compile_fail >= 2:
        parts.append("Compile failed repeatedly; prefer rewrite_dsl or rewrite_plan.")
    if consec_edit_fail >= 2:
        parts.append("Edits failed repeatedly; prefer rewrite_dsl or rewrite_plan.")
    if compile_ok is True and post_ok is True:
        parts.append("Compile and server post succeeded; submit if the shape matches the user request.")
    return " ".join(parts)


def _agent_log(verbose: bool, phase: str, detail: str = "") -> None:
    if detail:
        print(f"[agent] {phase}: {detail}", file=sys.stderr)
    else:
        print(f"[agent] {phase}", file=sys.stderr)


def _vprint(verbose: bool, *args, **kwargs) -> None:
    if verbose:
        print(*args, **kwargs)


def _gen(
    llm,
    prompt: str,
    grammar_path: Path,
    *,
    persistent_prefix: str,
    max_new_tokens: int,
    temperature: float,
    verbose: bool,
    phase: str,
) -> str:
    _vprint(verbose, "---", phase, "---")
    _vprint(verbose, persistent_prefix[:200] + ("..." if len(persistent_prefix) > 200 else ""))
    _vprint(verbose, prompt)
    out = generate_with_grammar(
        prompt,
        grammar_path,
        llm=llm,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        persistent_prefix=persistent_prefix,
    )
    _vprint(verbose, out)
    _vprint(verbose, "--- end", phase, "---")
    return out


def run_agent(
    llm,
    user_input: str,
    dsl_path: Path,
    plan_path: Path,
    training_mode: bool = False,
    verbose: bool = False,
) -> None:
    """
    Linear flow: plan phase -> write DSL phase -> choose-and-edit loop until submit.
    """
    dsl_path = Path(dsl_path)
    plan_path = Path(plan_path)
    dsl_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.parent.mkdir(parents=True, exist_ok=True)

    compile_ok: bool | None = None
    compile_err = ""
    post_ok: bool | None = None
    post_err: str | None = None
    edit_err = ""
    tool_result = ""
    consec_compile_fail = 0
    consec_edit_fail = 0

    def refresh_dsl_pipeline(dsl_text: str, attempt_post: bool) -> None:
        nonlocal compile_ok, compile_err, post_ok, post_err, consec_compile_fail, consec_edit_fail
        cok, cerr = _dsl_compile_status(dsl_text)
        compile_ok, compile_err = cok, cerr
        if cok:
            consec_compile_fail = 0
        else:
            consec_compile_fail += 1
        if not attempt_post:
            return
        if cok:
            pok, perr = _post_dsl(dsl_text)
            post_ok, post_err = pok, perr
            _agent_log(verbose, "post", "ok" if pok else _truncate(perr or ""))
            if pok:
                consec_edit_fail = 0
        else:
            post_ok, post_err = None, None

    # Plan phase
    plan_body = "Plan out the DSL: " + user_input
    plan_content = _gen(
        llm,
        plan_body,
        GRAMMAR_PLAN,
        persistent_prefix=PREFIX_PLAN,
        max_new_tokens=AGENT_MAX_TOKENS_PLAN,
        temperature=AGENT_TEMP_PLAN,
        verbose=verbose,
        phase="plan",
    )
    plan_path.write_text(plan_content.strip())

    # Write DSL phase
    write_body = "Write the DSL from the plan:\n\n" + plan_content.strip()
    dsl = _gen(
        llm,
        write_body,
        GRAMMAR_DSL,
        persistent_prefix=PREFIX_ALL,
        max_new_tokens=AGENT_MAX_TOKENS_DSL,
        temperature=AGENT_TEMP_DSL,
        verbose=verbose,
        phase="write_dsl",
    )
    dsl = dsl.strip()
    dsl_path.write_text(dsl)
    refresh_dsl_pipeline(dsl, attempt_post=True)
    _agent_log(verbose, "compile", "ok" if compile_ok else _truncate(compile_err))

    choice_grammar = GRAMMAR_CHOICE_TRAINING if training_mode else GRAMMAR_CHOICE_INFERENCE

    while True:
        plan_content = plan_path.read_text()
        dsl = dsl_path.read_text()
        policy = _choice_policy_hint(consec_compile_fail, consec_edit_fail, compile_ok, post_ok)
        status = _format_status(compile_ok, compile_err, post_ok, post_err, edit_err, tool_result, policy)
        choice_body = (
            status
            + "Choose one of: edit_plan, edit_dsl, rewrite_plan, rewrite_dsl"
            + (" or submit final DSL" if not training_mode else ", evaluate loss, optimise dsl, or submit final DSL")
            + "\n\nPlan:\n"
            + plan_content
            + "\n\nDSL:\n"
            + dsl
            + "\n\nChoice:"
        )
        choice_text = _gen(
            llm,
            choice_body,
            choice_grammar,
            persistent_prefix=PREFIX_ALL,
            max_new_tokens=AGENT_MAX_TOKENS_CHOICE,
            temperature=AGENT_TEMP_CHOICE,
            verbose=verbose,
            phase="choice",
        )

        try:
            choice = parse_choice(choice_text, training=training_mode)
        except ValueError as e:
            print(f"Choice parse error: {e}", file=sys.stderr)
            continue

        edit_err = ""
        tool_result = ""

        if choice == "submit":
            _agent_log(verbose, "submit")
            break

        if choice == "edit_plan":
            extra = status if (compile_ok is False or post_ok is False) else ""
            edit_body = extra + "Provide edits to the plan (find/replace only):\n\n" + plan_content + "\n\nJSON:"
            edit_text = _gen(
                llm,
                edit_body,
                GRAMMAR_EDIT_PLAN,
                persistent_prefix=PREFIX_ALL,
                max_new_tokens=AGENT_MAX_TOKENS_EDIT,
                temperature=AGENT_TEMP_EDIT,
                verbose=verbose,
                phase="edit_plan",
            )
            try:
                d = parse_edit_json(edit_text.strip(), "edit_plan")
                plan_content = apply_edits(plan_content, d["edits"])
                plan_path.write_text(plan_content)
                consec_edit_fail = 0
            except (ValueError, json.JSONDecodeError) as e:
                edit_err = str(e)
                consec_edit_fail += 1
                print(f"Edit error (returned to agent): {e}", file=sys.stderr)
            continue

        if choice == "edit_dsl":
            extra = status if (compile_ok is False or post_ok is False) else ""
            edit_body = extra + "Provide edits to the DSL (find/replace only):\n\n" + dsl + "\n\nJSON:"
            edit_text = _gen(
                llm,
                edit_body,
                GRAMMAR_EDIT_DSL,
                persistent_prefix=PREFIX_ALL,
                max_new_tokens=AGENT_MAX_TOKENS_EDIT,
                temperature=AGENT_TEMP_EDIT,
                verbose=verbose,
                phase="edit_dsl",
            )
            try:
                d = parse_edit_json(edit_text.strip(), "edit_dsl")
                dsl = apply_edits(dsl, d["edits"])
                dsl_path.write_text(dsl)
                consec_edit_fail = 0
                refresh_dsl_pipeline(dsl, attempt_post=True)
                _agent_log(verbose, "compile", "ok" if compile_ok else _truncate(compile_err))
            except (ValueError, json.JSONDecodeError) as e:
                edit_err = str(e)
                consec_edit_fail += 1
                print(f"Edit error (returned to agent): {e}", file=sys.stderr)
            continue

        if choice == "rewrite_plan":
            plan_body = "Plan out the DSL: " + user_input
            plan_content = _gen(
                llm,
                plan_body,
                GRAMMAR_PLAN,
                persistent_prefix=PREFIX_PLAN,
                max_new_tokens=AGENT_MAX_TOKENS_PLAN,
                temperature=AGENT_TEMP_PLAN,
                verbose=verbose,
                phase="rewrite_plan",
            )
            plan_path.write_text(plan_content.strip())
            continue

        if choice == "rewrite_dsl":
            plan_content = plan_path.read_text()
            extra = status if (compile_ok is False or post_ok is False) else ""
            write_body = extra + "Write the DSL from the plan:\n\n" + plan_content.strip() + "\n\n"
            dsl = _gen(
                llm,
                write_body,
                GRAMMAR_DSL,
                persistent_prefix=PREFIX_ALL,
                max_new_tokens=AGENT_MAX_TOKENS_DSL,
                temperature=AGENT_TEMP_DSL,
                verbose=verbose,
                phase="rewrite_dsl",
            )
            dsl = dsl.strip()
            dsl_path.write_text(dsl)
            refresh_dsl_pipeline(dsl, attempt_post=True)
            _agent_log(verbose, "compile", "ok" if compile_ok else _truncate(compile_err))
            continue

        if choice == "eval_loss" and training_mode:
            target = get_training_target_sdf()
            loss = evaluate_loss(dsl, target, seed=42)
            tool_result = f"eval_loss={loss:.6f}"
            print(tool_result, file=sys.stderr)
            _agent_log(verbose, "eval_loss", tool_result)
            continue

        if choice == "optimise_dsl" and training_mode:
            target = get_training_target_sdf()
            result = optimise_params_for_target(dsl, target, steps=500)
            dsl = t2g.unparseDSL(result)
            dsl_path.write_text(dsl)
            tool_result = "optimise_dsl=ok (steps=500)"
            _agent_log(verbose, "optimise_dsl", tool_result)
            refresh_dsl_pipeline(dsl, attempt_post=True)
            continue

    print(f"\nPlan:\n{plan_path.read_text()}\n")
    print(f"DSL:\n{dsl_path.read_text()}\n")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="LLM Agent: plan -> write DSL -> choose-and-edit loop")
    parser.add_argument("--training", action="store_true", help="Enable training tools (eval_loss, optimise_dsl)")
    parser.add_argument("--verbose", action="store_true", help="Print full prompts and raw model output")
    args = parser.parse_args()

    verbose = args.verbose or os.environ.get("T2G_AGENT_VERBOSE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )

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

        run_agent(llm, prompt, DSL_PATH, PLAN_PATH, training_mode=args.training, verbose=verbose)


if __name__ == "__main__":
    main()
