"""Digest rendering shared by the loop and the write_digest tool."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from ..config import Settings
from ..memory import Memory


def write_digest_file(settings: Settings, memory: Memory, counts: dict) -> str:
    with sqlite3.connect(memory.path) as conn:
        rows = conn.execute(
            """SELECT p.title,p.price_usd,p.cost_usd,p.url,j.score,
                      j.rationale,j.decided_by
               FROM judgments j JOIN products p ON p.id=j.product_id
               WHERE j.choice='shortlist' ORDER BY j.created DESC LIMIT 25"""
        ).fetchall()
    lines = [f"# Reflex digest — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             f"\nThis cycle: {counts['shortlist']} shortlisted · {counts['pass']} passed · "
             f"{counts['research']} need research.\n"]
    for title, price, cost, url, score, rationale, decided_by in rows:
        margin = (price - cost) / price if price else 0
        lines.append(f"## {title}\n- ${price:.2f} · margin {margin:.0%} · "
                     f"P(sell) {score:.2f} · via {decided_by}\n- {rationale}\n- {url}\n")
    if not rows:
        lines.append("_Nothing shortlisted this cycle._\n")
    lines.append("\n---\n_Reflex recommends; it never transacts (Noul gate)._")
    path = settings.digest_dir / f"digest-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    path.write_text("\n".join(lines))
    return str(path)
