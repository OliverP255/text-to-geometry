#!/usr/bin/env bash
# Append one score line per minute while BENCH_PID is running (or until results.json exists).
set -euo pipefail
LOG="${1:?log path}"
OUTFILE="${2:?score log path}"
BENCH_PID="${3:?benchmark pid}"
RESULTS_JSON="${4:-}"

while kill -0 "$BENCH_PID" 2>/dev/null; do
  passed=$(grep -c '^\s\+PASSED ' "$LOG" 2>/dev/null || true)
  failed=$(grep -c 'FAILED: Agent returned None after retries' "$LOG" 2>/dev/null || true)
  total=$((passed + failed))
  if [[ "$total" -gt 0 ]]; then
    pct=$((100 * passed / total))
  else
    pct=0
  fi
  echo "$(date -Is) completed=${total}/46 validation_ok=${passed} validation_fail=${failed} pass_rate=${pct}%" >>"$OUTFILE"
  sleep 60
done

passed=$(grep -c '^\s\+PASSED ' "$LOG" 2>/dev/null || true)
failed=$(grep -c 'FAILED: Agent returned None after retries' "$LOG" 2>/dev/null || true)
total=$((passed + failed))
if [[ -n "$RESULTS_JSON" && -f "$RESULTS_JSON" ]]; then
  echo "$(date -Is) FINAL from results.json (benchmark exited)" >>"$OUTFILE"
  head -5 "$RESULTS_JSON" >>"$OUTFILE" 2>/dev/null || true
elif [[ "$total" -gt 0 ]]; then
  pct=$((100 * passed / total))
  echo "$(date -Is) FINAL from log completed=${total} validation_ok=${passed} validation_fail=${failed} pass_rate=${pct}%" >>"$OUTFILE"
fi
