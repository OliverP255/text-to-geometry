#!/usr/bin/env bash
# Install NVIDIA GPU drivers on Google Compute Engine (Debian/Ubuntu).
# Use when: lspci shows an NVIDIA GPU but `nvidia-smi` is missing.
#
# Run:  bash scripts/install_gpu_driver_gce.sh
# If the tool reboots the host, SSH back in and run the same command again until it prints success.
#
# Docs: https://cloud.google.com/compute/docs/gpus/install-drivers-gpu
set -euo pipefail

CUDA_INSTALLER_URL="${CUDA_INSTALLER_URL:-https://github.com/GoogleCloudPlatform/compute-gpu-installation/releases/download/cuda-installer-v1.8.1/cuda_installer.pyz}"
TMP="${TMPDIR:-/tmp}/cuda_installer.pyz"

echo "==> Downloading Google cuda_installer"
curl -fsSL -o "$TMP" "$CUDA_INSTALLER_URL"

echo "==> Installing NVIDIA driver (binary, production branch). May reboot — re-run this script after boot if needed."
sudo DEBIAN_FRONTEND=noninteractive python3 "$TMP" install_driver \
  --installation-mode binary \
  --installation-branch prod

if command -v nvidia-smi &>/dev/null; then
  nvidia-smi -L
  echo "==> Driver OK"
else
  echo "==> If installation finished but nvidia-smi is still missing, reboot and run this script again."
fi
