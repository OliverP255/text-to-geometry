#!/bin/bash
# Reactivate paused Vast.ai instance and build the project.
#
# FIRST-TIME SETUP: Get your API key from https://vast.ai/console/cli/ then run:
#   vastai set api-key <your-key>
#
# Then run this script.

set -e

echo "=== Listing instances ==="
if ! vastai show instances; then
  echo ""
  echo "Auth failed. Run: vastai set api-key <your-key>"
  echo "Get your key from: https://vast.ai/console/cli/"
  exit 1
fi

echo ""
echo "=== Enter your instance ID (e.g. 12345678) to start: ==="
read -r INSTANCE_ID

if [ -z "$INSTANCE_ID" ]; then
  echo "No instance ID provided. Exiting."
  exit 1
fi

echo "Starting instance $INSTANCE_ID..."
vastai start instance "$INSTANCE_ID"

echo "Waiting 30s for instance to come up..."
sleep 30

echo "=== Fetching SSH connection details ==="
vastai ssh-url "$INSTANCE_ID" || true

echo ""
echo "Once the instance is running, SSH in and run:"
echo "  cd /workspace/text-to-geometry"
echo "  rm -rf build && mkdir -p build && cd build"
echo "  cmake .. && make -j\$(nproc)"
echo ""
echo "Or rsync from local first, then build:"
echo "  rsync -avz --exclude build --exclude __pycache__ . root@<IP>:/workspace/text-to-geometry/ -e \"ssh -p <PORT>\""
echo "  ssh -p <PORT> root@<IP> 'cd /workspace/text-to-geometry && rm -rf build && mkdir build && cd build && cmake .. && make -j\$(nproc)'"
