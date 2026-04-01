#!/usr/bin/env python3
"""
Run test_50_prompts.py once per model in benchmark_models.BENCHMARK_MODELS (subprocess per model
so vLLM releases GPU memory between runs).

Usage (from repo root):
  .venv/bin/python3 agent/experiments/run_multi_llm_benchmark.py
  .venv/bin/python3 agent/experiments/run_multi_llm_benchmark.py --max-prompts 2   # smoke test

Then:
  .venv/bin/python3 agent/experiments/aggregate_benchmark_ratings.py
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _remove_hf_model_cache(model_id: str) -> None:
    """Drop this repo from the local Hugging Face hub cache (frees disk for the next download)."""
    try:
        from huggingface_hub import scan_cache_dir
    except ImportError:
        return
    try:
        info = scan_cache_dir()
    except Exception as e:
        print(f"  (HF cache scan skipped: {e})")
        return
    hashes: list[str] = []
    for repo in info.repos:
        if repo.repo_type == "model" and repo.repo_id == model_id:
            hashes.extend(r.commit_hash for r in repo.revisions)
    if not hashes:
        return
    try:
        strat = info.delete_revisions(*hashes)
        print(f"  HF cache: removed {model_id} (~{strat.expected_freed_size_str})")
        strat.execute()
    except Exception as e:
        print(f"  WARNING: HF cache cleanup failed: {e}")


def _free_disk_gib(path: Path) -> float:
    st = os.statvfs(str(path))
    return st.f_bavail * st.f_frsize / (1024.0**3)


def _kill_gpu_compute_processes() -> None:
    """Free VRAM for the next vLLM child (orphan EngineCore if the parent was SIGKILL'd)."""
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-compute-apps=pid",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return
    for tok in out.replace(",", " ").split():
        t = tok.strip()
        if not t.isdigit():
            continue
        pid = int(t)
        if pid <= 1:
            continue
        try:
            os.kill(pid, 9)
        except (ProcessLookupError, PermissionError):
            pass


def _clear_vllm_disk_cache() -> None:
    root = Path(os.environ.get("VLLM_CACHE_ROOT") or (Path.home() / ".cache" / "vllm"))
    if not root.is_dir():
        return
    try:
        for child in root.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            elif child.is_file():
                child.unlink(missing_ok=True)
        print("  vLLM disk cache cleared.")
    except Exception as e:
        print(f"  WARNING: vLLM cache cleanup failed: {e}")

_agent_root = Path(__file__).resolve().parent.parent
_repo_root = _agent_root.parent
_test_script = Path(__file__).resolve().parent / "test_50_prompts.py"
_out_root = Path(__file__).resolve().parent / "outputs" / "by_model"
_log_dir = Path(__file__).resolve().parent / "logs"


def main() -> None:
    sys.path.insert(0, str(_agent_root))
    from experiments.benchmark_models import BENCHMARK_MODELS, model_slug

    parser = argparse.ArgumentParser(description="Run WGSL prompt suite for each benchmark model.")
    parser.add_argument("--max-prompts", type=int, default=None, help="Limit prompts per model (smoke test)")
    parser.add_argument("--start-at", type=int, default=0, help="Skip first N models in the list")
    parser.add_argument(
        "--no-cleanup-between",
        action="store_true",
        help="Do not delete HF weights / vLLM disk cache after each model (uses more disk)",
    )
    parser.add_argument(
        "--skip-gpu-reset",
        action="store_true",
        help="Do not SIGKILL processes listed by nvidia-smi before each model (unsafe if GPU is shared)",
    )
    args = parser.parse_args()

    _out_root.mkdir(parents=True, exist_ok=True)
    _log_dir.mkdir(parents=True, exist_ok=True)

    need_gib = 28.0
    free_gib = _free_disk_gib(_repo_root)
    if free_gib < need_gib:
        print(
            f"ERROR: need at least ~{need_gib:.0f} GiB free on {_repo_root} for one 32B download; "
            f"have {free_gib:.1f} GiB. Clear ~/.cache/huggingface/hub or set HF_HOME to a larger volume."
        )
        sys.exit(1)

    manifest = {
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "max_prompts": args.max_prompts,
        "models": [],
    }

    py = sys.executable
    for idx, (label, model_id) in enumerate(BENCHMARK_MODELS):
        if idx < args.start_at:
            continue
        slug = model_slug(model_id)
        out_dir = _out_root / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        results_path = out_dir / "results.json"
        log_path = _log_dir / f"benchmark_{slug}.log"

        cmd = [
            py,
            str(_test_script),
            "--model",
            model_id,
            "--output-dir",
            str(out_dir),
            "--results-json",
            str(results_path),
        ]
        if args.max_prompts is not None:
            cmd.extend(["--max-prompts", str(args.max_prompts)])

        print(f"\n{'='*60}\n[{idx + 1}/{len(BENCHMARK_MODELS)}] {label}\n  model_id={model_id}\n  log={log_path}\n{'='*60}\n")

        if not args.skip_gpu_reset:
            _kill_gpu_compute_processes()
            time.sleep(2)

        t0 = time.perf_counter()
        with open(log_path, "w", encoding="utf-8") as logf:
            logf.write(f"cmd: {' '.join(cmd)}\n\n")
            logf.flush()
            p = subprocess.run(
                cmd,
                cwd=str(_repo_root),
                stdout=logf,
                stderr=subprocess.STDOUT,
                text=True,
            )
        elapsed = time.perf_counter() - t0

        entry = {
            "label": label,
            "model_id": model_id,
            "slug": slug,
            "returncode": p.returncode,
            "seconds": round(elapsed, 1),
            "results_json": str(results_path),
            "log": str(log_path),
        }
        manifest["models"].append(entry)

        if p.returncode != 0:
            print(f"WARNING: model {label} exited {p.returncode} — see {log_path}")
        elif results_path.is_file():
            try:
                data = json.loads(results_path.read_text(encoding="utf-8"))
                print(
                    f"  validation_ok: {data.get('validation_passed', '?')}/"
                    f"{data.get('prompt_count', '?')} in {elapsed:.0f}s"
                )
            except Exception as e:
                print(f"  (could not read results.json: {e})")

        if not args.no_cleanup_between:
            print("  Cleaning up model weights / caches …")
            _remove_hf_model_cache(model_id)
            _clear_vllm_disk_cache()
            gc.collect()

    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
    manifest_path = _out_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote {manifest_path}")


if __name__ == "__main__":
    main()
