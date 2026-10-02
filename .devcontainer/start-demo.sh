#!/usr/bin/env bash
# Reflex devcontainer start — launches the dashboard on every Codespace start.
# No API keys? Runs the offline demo. Keys present (Codespaces secrets)? Goes live.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -z "${GLM_API_KEY:-}" ]; then
  export REFLEX_OFFLINE=1
  MODE="offline demo mode (no API keys — add GLM_API_KEY / EXA_API_KEY as Codespaces secrets for live)"
else
  MODE="live mode"
fi
export REFLEX_HOME="${REFLEX_HOME:-/tmp/reflex-demo}"

# Don't start twice.
if [ -f /tmp/reflex-demo.pid ] && kill -0 "$(cat /tmp/reflex-demo.pid)" 2>/dev/null; then
  echo "Reflex dashboard already running."
  exit 0
fi

nohup .venv/bin/python -m reflex.web.app --port 8765 > /tmp/reflex-demo.log 2>&1 &
echo $! > /tmp/reflex-demo.pid
echo "Reflex dashboard starting on port 8765 — ${MODE}."
echo "Open the forwarded port in the Ports tab. Log: /tmp/reflex-demo.log"
