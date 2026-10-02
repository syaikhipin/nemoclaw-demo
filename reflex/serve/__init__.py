"""The long-running claw loop — the deterministic core of Reflex.

One cycle: scan -> System One triage -> escalate the uncertain ones to
System Two -> enforce the Noul gate -> publish digest -> sleep.

This is what the OpenClaw cron job (nemoclaw/scripts/start.sh) invokes, and
what run_forever() keeps alive on a plain machine. The deep-agent harness
wraps the same tools for interactive / subagent-driven operation.
"""

from __future__ import annotations

import time
from datetime import datetime

from .. import noul
from ..config import Settings
from ..memory import Memory
from ..schemas import Judgment
from ..sources.catalog import MockCatalog
from ..system_one import SklearnHead
from ..system_two import SystemTwoAnalyst


def run_cycle(settings: Settings | None = None, limit: int | None = None,
              dry_run: bool = False, source: MockCatalog | None = None) -> dict:
    from ..config import SETTINGS
    settings = settings or SETTINGS
    settings.ensure_dirs()
    memory = Memory(settings)
    source = source or MockCatalog()

    products = source.fetch(limit or settings.scan_limit)
    fresh = memory.unseen(products)
    if not dry_run:
        memory.upsert_products(products)

    try:
        head = SklearnHead.load(settings)
        head_ready = True
    except Exception as exc:
        head_ready = False
        head_error = str(exc)

    judgments: list[Judgment] = []
    analyst = SystemTwoAnalyst(settings)
    n_escalated = 0
    if head_ready:
        judgments = head.judge_batch(fresh)
        # Escalate the uncertain ones to System Two
        for j in judgments:
            if j.choice == "research":
                p = next(p for p in fresh if p.id == j.product_id)
                analysis = analyst.analyze(p)
                n_escalated += 1
                j.choice = {"list": "shortlist", "skip": "pass",
                            "needs_research": "research"}[analysis.verdict]  # type: ignore[assignment]
                j.score = analysis.score
                j.decided_by = "system_two"
                j.rationale = f"System Two ({analyst.describe()}): {analysis.summary}"
                j.extra = {"risks": analysis.risks}
        if not dry_run:
            memory.record_judgments(judgments)

    counts = {"shortlist": 0, "pass": 0, "research": 0}
    for j in judgments:
        counts[j.choice] += 1

    digest_path = ""
    if not dry_run and judgments:
        from .digest import write_digest_file
        digest_path = write_digest_file(settings, memory, counts)

    # The Noul gate is consulted for the cycle's only privileged action:
    # publishing the digest (harmless) vs. anything transactional (blocked).
    gate = noul.check("publish triage digest to owner")

    stats = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "n_scanned": len(fresh),
        "n_shortlisted": counts["shortlist"],
        "n_passed": counts["pass"],
        "n_research": counts["research"],
        "n_escalated": n_escalated,
        "head_ready": head_ready,
        "head_error": "" if head_ready else head_error,
        "digest_path": digest_path,
        "noul_publish_digest": gate.allowed,
        "noul_would_block_order": not noul.check("place bulk order with supplier").allowed,
    }
    if not dry_run:
        memory.record_run(stats)
    return stats


def run_forever(settings: Settings | None = None, interval_hours: float = 6.0) -> None:
    """Keep the claw alive: run a cycle, sleep, repeat. Ctrl-C stops it."""
    from ..config import SETTINGS
    settings = settings or SETTINGS
    print(f"[reflex] claw loop started — cycle every {interval_hours}h. Ctrl-C to stop.")
    while True:
        stats = run_cycle(settings)
        print(f"[reflex] cycle done: scanned={stats['n_scanned']} "
              f"shortlisted={stats['n_shortlisted']} escalated={stats['n_escalated']}")
        time.sleep(interval_hours * 3600)
