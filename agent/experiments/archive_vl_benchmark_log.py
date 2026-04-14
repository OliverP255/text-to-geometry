#!/usr/bin/env python3
"""Parse benchmark log into results-style JSON (partial runs OK). Usage:
python agent/experiments/archive_vl_benchmark_log.py <log_path> <out_json_path>
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: archive_vl_benchmark_log.py LOG.json OUT.json", file=sys.stderr)
        sys.exit(2)
    log_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    text = log_path.read_text(encoding="utf-8", errors="replace")

    # model_id from first "Loading LLM:"
    m_load = re.search(r"Loading LLM:\s*(\S+)\s", text)
    model_id = m_load.group(1) if m_load else "unknown"

    per_prompt: list[dict] = []
    cur_n: int | None = None
    cur_prompt: str | None = None

    for line in text.splitlines():
        m_t = re.match(r"\[\s*(\d+)/\d+\]\s+Testing:\s+(.+)", line)
        if m_t:
            cur_n = int(m_t.group(1))
            cur_prompt = m_t.group(2).strip()
            continue
        m_p = re.match(r"\s+PASSED\s+\((\d+)\s+chars?\)", line)
        if m_p and cur_n is not None and cur_prompt is not None:
            per_prompt.append(
                {
                    "n": cur_n,
                    "prompt": cur_prompt,
                    "ok": True,
                    "error": None,
                    "code_len": int(m_p.group(1)),
                }
            )
            cur_n, cur_prompt = None, None
            continue
        m_f = re.match(r"\s+FAILED:\s+(.+)", line)
        if m_f and cur_n is not None and cur_prompt is not None:
            per_prompt.append(
                {
                    "n": cur_n,
                    "prompt": cur_prompt,
                    "ok": False,
                    "error": m_f.group(1).strip(),
                    "code_len": 0,
                }
            )
            cur_n, cur_prompt = None, None

    passed = sum(1 for x in per_prompt if x["ok"])
    total_done = len(per_prompt)
    last_testing = None
    for line in reversed(text.splitlines()):
        m_t = re.match(r"\[\s*(\d+)/(\d+)\]\s+Testing:", line)
        if m_t:
            last_testing = (int(m_t.group(1)), int(m_t.group(2)))
            break

    payload = {
        "archived_utc": datetime.now(timezone.utc).isoformat(),
        "source_log": str(log_path.resolve()),
        "model_id": model_id,
        "thinking_mode": "ON (default for *Thinking* checkpoint: enable_thinking via qwen3_thinking_enabled)",
        "note": "Run was incomplete in log: last 'Testing' line may exceed recorded per_prompt outcomes.",
        "last_seen_testing_line": list(last_testing) if last_testing else None,
        "prompt_count_recorded": total_done,
        "validation_passed": passed,
        "validation_failed": total_done - passed,
        "per_prompt": sorted(per_prompt, key=lambda x: x["n"]),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path} ({total_done} prompts, {passed} ok)")


if __name__ == "__main__":
    main()
