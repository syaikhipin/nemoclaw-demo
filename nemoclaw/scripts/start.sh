#!/usr/bin/env bash
# Reflex x NemoClaw — start: schedule the long-running claw.
#
# Preferred: inside the NemoClaw sandbox, create an OpenClaw cron job that runs
# a triage cycle every 6 hours. Fallback: run the loop directly on this machine.
set -euo pipefail
cd "$(dirname "$0")/../.."

REFLEX_DIR="$(pwd)"
CRON_SCHEDULE="${REFLEX_CRON_SCHEDULE:-0 */6 * * *}"

if command -v openclaw >/dev/null 2>&1; then
  echo "== Creating OpenClaw cron job (every 6h) =="
  openclaw cron create \
    --name "reflex-triage" \
    --schedule "$CRON_SCHEDULE" \
    --command "cd $REFLEX_DIR && .venv/bin/python -m scripts.run --limit 40" \
    || { echo "Cron creation needs approval: run 'nemoclaw <sandbox> connect', approve the"; echo "operator.admin scope request, then rerun this script."; exit 1; }
  echo "Cron job 'reflex-triage' created. Digests land in \$REFLEX_HOME/digests/."
else
  echo "'openclaw' CLI not found — starting the local long-running loop instead."
  echo "(Inside the NemoClaw sandbox this script creates a cron job; see SKILL.md.)"
  exec .venv/bin/python -m scripts.run --forever --interval-hours 6
fi
