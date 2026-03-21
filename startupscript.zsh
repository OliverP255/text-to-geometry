#!/usr/bin/env zsh
# Clone repo, install system + Python deps (downloads only), build C++/pybind and web. No swap/disk checks/tests.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/OliverP255/text-to-geometry.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/text-to-geometry}"
PYTHON="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-$INSTALL_DIR/.venv}"

NPROC="$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"

if [[ "${1:-}" == -* ]] || [[ -n "${1:-}" && "${1}" != http* ]]; then
  INSTALL_DIR="$(realpath "${1:-$INSTALL_DIR}")"
fi
if [[ "${1:-}" == http* ]] || [[ "${2:-}" == http* ]]; then
  REPO_URL="${1:-$REPO_URL}"
fi

echo "==> Install dir: $INSTALL_DIR"
echo "==> Repo: $REPO_URL"

if command -v apt-get &>/dev/null; then
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends \
    git build-essential cmake \
    nodejs npm \
    "$PYTHON" "${PYTHON}-venv" "${PYTHON}-dev" "${PYTHON}-pip"
fi

if ! "$PYTHON" -m pip --version &>/dev/null; then
  echo "ERROR: pip missing for $PYTHON. Install ${PYTHON}-pip (e.g. apt install python3-pip)."
  exit 1
fi

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  git clone "$REPO_URL" "$INSTALL_DIR"
else
  git -C "$INSTALL_DIR" pull --ff-only || true
fi
cd "$INSTALL_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON" -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
python3 -m pip install -U pip

export PYTHONUNBUFFERED=1

# PyTorch first: CUDA 12.1 wheels from pytorch.org (required for agent_tools / vLLM stack)
TORCH_INDEX="https://download.pytorch.org/whl/cu121"
echo "==> Installing PyTorch (CUDA 12.1) from $TORCH_INDEX"
pip install --no-cache-dir torch --index-url "$TORCH_INDEX"

echo "==> text-to-dsl/requirements.txt (skip duplicate torch line — already installed above)"
# Use repo dir, not /tmp — some GCP/OS Login setups deny writing /tmp for redirects
REQS_TMP="${INSTALL_DIR}/.t2g-reqs-no-torch.txt"
grep -vE '^[[:space:]]*torch[[:space:]]*(#.*)?$' text-to-dsl/requirements.txt > "$REQS_TMP"
pip install --no-cache-dir -r "$REQS_TMP"

echo "==> Verify PyTorch (vLLM may have upgraded torch; must still import)"
python3 -c "import torch; print('torch OK:', torch.__version__)"

echo "==> CMake build (C++ + pybind)"
mkdir -p build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$NPROC"

if command -v npm &>/dev/null && [[ -f web/package.json ]]; then
  echo "==> Web (npm ci + build)"
  (cd web && npm ci && npm run build)
fi

echo ""
echo "Done:"
echo "  source $VENV_DIR/bin/activate"
echo "  cd $INSTALL_DIR/text-to-dsl && python agent.py"
