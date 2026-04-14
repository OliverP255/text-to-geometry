#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ -x "${ROOT}/.venv/bin/litellm" ]]; then
  PATH="${ROOT}/.venv/bin:${PATH}"
  export PATH
fi
if ! command -v litellm >/dev/null 2>&1; then
  echo "litellm not on PATH. Run: python3 -m venv \"${ROOT}/.venv\" && \"${ROOT}/.venv/bin/pip\" install -r \"${ROOT}/requirements.txt\""
  exit 1
fi

: "${LITELLM_MASTER_KEY:=sk-local-litellm-cc}"
export LITELLM_MASTER_KEY

if [[ -z "${VERTEXAI_PROJECT:-}" ]]; then
  if command -v gcloud >/dev/null 2>&1; then
    VERTEXAI_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
  fi
fi
if [[ -z "${VERTEXAI_PROJECT:-}" ]]; then
  echo "Set VERTEXAI_PROJECT (GCP project with Vertex AI + GLM MaaS enabled)."
  exit 1
fi
export VERTEXAI_PROJECT

export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-$VERTEXAI_PROJECT}"

# VM metadata tokens often lack cloud-platform OAuth scope → Vertex 403 ACCESS_TOKEN_SCOPE_INSUFFICIENT.
# Prefer a dedicated service-account key (full API scope) if present:
if [[ -f "${ROOT}/.vertex-sa.json" ]]; then
  export GOOGLE_APPLICATION_CREDENTIALS="${ROOT}/.vertex-sa.json"
  echo "Using GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS} for Vertex (bypasses narrow GCE scopes)."
fi

ADC_FILE="${HOME}/.config/gcloud/application_default_credentials.json"
on_gce() {
  curl -sf --connect-timeout 1 -H "Metadata-Flavor: Google" \
    "http://169.254.169.254/computeMetadata/v1/instance/id" >/dev/null 2>&1
}

# Vertex uses ADC (not `gcloud auth login`). Stale user ADC → invalid_grant / deleted account.
# On GCE, prefer the VM service account: remove user ADC so google-auth uses metadata credentials.
if on_gce; then
  sa_email="$(
    curl -sf --connect-timeout 1 -H "Metadata-Flavor: Google" \
      "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/email" 2>/dev/null || true
  )"
  echo "Detected GCE. Vertex needs OAuth scope cloud-platform; VM metadata tokens often lack it."
  [[ -n "$sa_email" ]] && echo "  VM default SA: $sa_email (narrow scopes → use litellm/.vertex-sa.json; see config.yaml header)."
  if [[ ! -f "${ROOT}/.vertex-sa.json" && -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
    echo "  WARN: No ${ROOT}/.vertex-sa.json — LiteLLM→Vertex will likely fail with 403 scope/predict errors."
  fi
  if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" && -f "$ADC_FILE" ]]; then
    echo "  User ADC file exists: $ADC_FILE — this overrides the VM SA. If auth fails or gcloud application-default"
    echo "  login crashes with 'Scope has changed', remove it: rm -f \"$ADC_FILE\""
  fi
fi

if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" && -f "$ADC_FILE" ]] && command -v gcloud >/dev/null 2>&1; then
  if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
    echo "ERROR: Application Default Credentials in $ADC_FILE are invalid."
    if on_gce; then
      echo "  On GCE, recommended: delete user ADC so LiteLLM uses the instance service account:"
      echo "    rm -f \"$ADC_FILE\""
      echo "  Then grant that SA Vertex AI User on project $VERTEXAI_PROJECT (see metadata email above)."
    else
      echo "  Fix: gcloud auth application-default revoke && \\"
      echo "    gcloud auth application-default login --scopes=\"https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email\""
    fi
    echo "  Or set GOOGLE_APPLICATION_CREDENTIALS to a service-account JSON key."
    exit 1
  fi
fi

echo "LiteLLM proxy -> Vertex GLM (project=$VERTEXAI_PROJECT)"
echo "Claude Code: export ANTHROPIC_BASE_URL=http://127.0.0.1:4000"
echo "             export ANTHROPIC_AUTH_TOKEN=\"\$LITELLM_MASTER_KEY\"  # same as LITELLM_MASTER_KEY ($LITELLM_MASTER_KEY)"
exec litellm --config "$ROOT/config.yaml" --host 127.0.0.1 --port 4000
