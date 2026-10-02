#!/usr/bin/env bash
# Reflex x NemoClaw — install: train the demo head, verify the pipeline.
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "== Reflex install =="
export REFLEX_OFFLINE=1
if [ -n "${REFLEX_HOME:-}" ]; then export REFLEX_HOME; fi

.venv/bin/python -m scripts.bootstrap
.venv/bin/python -m pytest tests/ -q

echo ""
echo "Install verified: System One head trained, 7/7 tests green."
echo "Next: bash nemoclaw/scripts/start.sh   (creates the OpenClaw cron job)"
echo "  or: .venv/bin/python -m scripts.run --forever --interval-hours 6"
