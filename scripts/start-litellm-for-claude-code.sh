#!/usr/bin/env bash
# Start the local LiteLLM proxy on 127.0.0.1:4000 so Claude Code can reach it
# (ANTHROPIC_BASE_URL=http://127.0.0.1:4000 in ~/.claude/settings.json).
#
# Usage: ./scripts/start-litellm-for-claude-code.sh
#   Optional: VERTEXAI_PROJECT, LITELLM_MASTER_KEY (default matches settings.json)
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LITELLM_DIR="$ROOT/litellm"
KEY="${LITELLM_MASTER_KEY:-sk-local-litellm-cc}"
LOG="${LITELLM_CC_LOG:-${TMPDIR:-/tmp}/litellm-claude-code.log}"
PIDFILE="${LITELLM_CC_PIDFILE:-${TMPDIR:-/tmp}/litellm-claude-code.pid}"

httprc() {
  curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 \
    -H "Authorization: Bearer ${KEY}" \
    "http://127.0.0.1:4000/v1/models" 2>/dev/null || echo "000"
}

rc="$(httprc)"
if [[ "$rc" == "200" ]]; then
  echo "LiteLLM already reachable on http://127.0.0.1:4000 (GET /v1/models -> 200)."
  exit 0
fi

if [[ ! -f "${LITELLM_DIR}/run.sh" ]]; then
  echo "ERROR: ${LITELLM_DIR}/run.sh not found."
  echo "  This repo gitignored directory must exist locally: create litellm/ from your team copy"
  echo "  (needs config.yaml, requirements.txt, run.sh, optional .vertex-sa.json)."
  exit 1
fi

if [[ -z "${VERTEXAI_PROJECT:-}" ]] && command -v gcloud >/dev/null 2>&1; then
  export VERTEXAI_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
fi
if [[ -z "${VERTEXAI_PROJECT:-}" ]]; then
  echo "ERROR: Set VERTEXAI_PROJECT (GCP project with Vertex AI + GLM MaaS enabled)."
  exit 1
fi

export LITELLM_MASTER_KEY="${KEY}"

echo "Starting LiteLLM in background (log: $LOG)…"
nohup env VERTEXAI_PROJECT="${VERTEXAI_PROJECT}" LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY}" \
  bash -lc "cd \"${LITELLM_DIR}\" && exec bash ./run.sh" >>"${LOG}" 2>&1 &
echo $! >"${PIDFILE}"

for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 1
  rc="$(httprc)"
  if [[ "$rc" == "200" ]]; then
    echo "LiteLLM is up on http://127.0.0.1:4000 (PID $(cat "${PIDFILE}"), log ${LOG})."
    echo "You can start Claude Code now."
    exit 0
  fi
done

echo "ERROR: LiteLLM did not become ready within ~10s. Last HTTP code: ${rc}"
echo "  See log: ${LOG}"
exit 1
