#!/usr/bin/env bash
# Reflex x NemoClaw — onboard: verify prerequisites, no side effects.
set -euo pipefail

echo "== Reflex onboard =="
command -v docker >/dev/null 2>&1 || { echo "WARN: docker not found (needed for the NemoClaw sandbox)"; }
command -v nemoclaw >/dev/null 2>&1 || { echo "WARN: 'nemoclaw' CLI not found — install it first:"; echo "  curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash"; }
command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 required"; exit 1; }

if [ ! -d ".venv" ]; then
  echo "Creating Python venv and installing dependencies..."
  python3 -m venv .venv
  .venv/bin/pip install -q -e .
else
  echo "venv already present."
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env — add your NVIDIA_API_KEY (free at https://build.nvidia.com)."
fi

echo "OK. Next: bash nemoclaw/scripts/install.sh"
