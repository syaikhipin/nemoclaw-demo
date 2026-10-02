#!/usr/bin/env bash
# Reflex devcontainer setup — runs once when the Codespace is created.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Reflex: creating venv =="
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

echo "== Reflex: training the demo System One head (offline) =="
REFLEX_OFFLINE=1 .venv/bin/python -m scripts.bootstrap

echo ""
echo "Setup done. The dashboard starts automatically — open the forwarded port 8765."
echo "Tip: add OPENAI_API_KEY / EXA_API_KEY as Codespaces secrets and rebuild for the live demo."
