"""Run one Reflex triage cycle. Entry point for cron / OpenClaw jobs."""

from __future__ import annotations

import argparse
import json

from reflex.config import SETTINGS


def main() -> None:
    ap = argparse.ArgumentParser(description="Reflex triage cycle")
    ap.add_argument("--forever", action="store_true", help="loop until Ctrl-C")
    ap.add_argument("--interval-hours", type=float, default=6.0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from reflex.serve import run_cycle, run_forever
    if args.forever:
        run_forever(SETTINGS, interval_hours=args.interval_hours)
    else:
        stats = run_cycle(SETTINGS, limit=args.limit, dry_run=args.dry_run)
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
