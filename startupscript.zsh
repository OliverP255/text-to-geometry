set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/OliverP255/text-to-geometry.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/text-to-geometry}"
PYTHON="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-$INSTALL_DIR/.venv}"

NPROC="$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"

if [[ -n "${1:-}" && "${1}" != -* && "${1}" != http* && "${1}" != https* ]]; then
  INSTALL_DIR="$(realpath "${1}")"
fi
if [[ "${1:-}" == http* ]] || [[ "${1:-}" == https* ]]; then
  REPO_URL="${1}"
elif [[ "${2:-}" == http* ]] || [[ "${2:-}" == https* ]]; then
  REPO_URL="${2}"
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

TORCH_INDEX="https://download.pytorch.org/whl/cu121"
echo "==> Installing PyTorch (CUDA 12.1) from $TORCH_INDEX"
pip install --no-cache-dir torch --index-url "$TORCH_INDEX"

echo "==> text-to-dsl/requirements.txt (skip duplicate torch line — already installed above)"
REQS_TMP="${INSTALL_DIR}/.t2g-reqs-no-torch.txt"
grep -vE '^[[:space:]]*torch[[:space:]]*(#.*)?$' text-to-dsl/requirements.txt > "$REQS_TMP"
pip install --no-cache-dir -r "$REQS_TMP"

echo "==> Upgrading transformers + huggingface-hub for GLM-4.7 (agent model)"
pip install --no-cache-dir -U 'transformers>=5.3' 'huggingface-hub>=0.28'

echo "==> Verify PyTorch (vLLM may have upgraded torch; must still import)"
python3 -c 'import torch; print("torch OK:", torch.__version__)'
if command -v nvidia-smi &>/dev/null; then
  echo "==> GPUs (nvidia-smi -L)"
  nvidia-smi -L || true
else
  echo "WARN: nvidia-smi not found — vLLM/agent needs an NVIDIA driver + GPU on this machine."
  if lspci 2>/dev/null | grep -qi nvidia; then
    echo "     PCI shows NVIDIA — on GCE run once: bash $INSTALL_DIR/scripts/install_gpu_driver_gce.sh"
    echo "     (Re-run after reboot if the installer asks.)"
  fi
fi
echo "==> CUDA device count (PyTorch)"
python3 -c 'import torch; print("torch.cuda.device_count():", torch.cuda.device_count())' || true

echo "==> CMake build (C++ + pybind)"
mkdir -p build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$NPROC"

echo "Done:"
echo "  source $VENV_DIR/bin/activate"
echo "  cd $INSTALL_DIR/text-to-dsl && python agent.py"
echo ""
echo "GPU VM without driver: bash $INSTALL_DIR/scripts/install_gpu_driver_gce.sh"
