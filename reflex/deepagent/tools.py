"""LangChain tools the deep agent (and its subagents) can call.

Every tool is a thin, auditable wrapper over the Reflex core: sources, the
System One head, the System Two analyst, the Noul gate, and durable memory.
"""

from __future__ import annotations

import json
from datetime import datetime

from langchain_core.tools import tool

from .. import noul
from ..config import Settings
from ..memory import Memory
from ..negotiation import draft_outreach as _draft_outreach
from ..negotiation import find_suppliers as _find_suppliers
from ..negotiation import record as _record_negotiation
from ..schemas import Judgment
from ..sources import AmazonFashionSource, default_source
from ..system_one import SklearnHead
from ..system_two import SystemTwoAnalyst


def make_tools(settings: Settings | None = None):
    from ..config import SETTINGS
    settings = settings or SETTINGS
    memory = Memory(settings)
    source = default_source()
    registry: dict[str, object] = {}
    _suppliers: dict[str, dict] = {}

    def _head() -> SklearnHead:
        return SklearnHead.load(settings)

    @tool
    def scan_products(limit: int = 20, seed: int | None = None) -> str:
        """Scan the product source for fresh candidates. Returns JSON list of products."""
        import time as _time
        _seed = seed if seed is not None else int(_time.time()) % 100000
        if isinstance(source, AmazonFashionSource):
            products = source.fetch(limit=settings.scan_limit if limit is None else limit,
                                    seed=_seed)
        else:
            products = source.fetch(limit=settings.scan_limit if limit is None else limit)
        fresh = memory.unseen(products)
        memory.upsert_products(products)
        for p in fresh:
            registry[p.id] = p
        return json.dumps([p.to_dict() for p in fresh])

    @tool
    def system_one_judge(product_ids: list[str]) -> str:
        """Fast personal triage (System One). Returns JSON judgments with
        choice shortlist/pass/research, calibrated score and rationale."""
        head = _head()
        products = [registry[i] for i in product_ids if i in registry]
        judgments = head.judge_batch(products)
        memory.record_judgments(judgments)
        return json.dumps([j.to_dict() for j in judgments])

    @tool
    def deep_dive_analysis(product_id: str) -> str:
        """Slow deliberative analysis (System Two, Hermes via NVIDIA NIM).
        Use only for products the System One head marked 'research'."""
        product = registry.get(product_id)
        if product is None:
            return json.dumps({"error": f"unknown product {product_id}"})
        analysis = SystemTwoAnalyst(settings).analyze(product)
        verdict_to_choice = {"list": "shortlist", "skip": "pass",
                             "needs_research": "research"}
        judgment = Judgment(
            product_id=product.id,
            choice=verdict_to_choice.get(analysis.verdict, "research"),  # type: ignore[arg-type]
            score=analysis.score,
            confidence=round(abs(analysis.score - 0.5) * 2, 3),
            rationale=f"System Two ({'offline' if analysis.offline else 'nim'}): {analysis.summary}",
            decided_by="system_two",
            model_version=SystemTwoAnalyst(settings).describe(),
            extra={"risks": analysis.risks, "offline": analysis.offline},
        )
        memory.record_judgments([judgment])
        return json.dumps({**analysis.to_dict(), "choice": judgment.choice})

    @tool
    def noul_gate(action: str) -> str:
        """Safety gate. MUST be called before any purchase, order, negotiation
        or money movement. Returns allow/block verdict as JSON."""
        return json.dumps(noul.check(action).to_dict())

    @tool
    def record_feedback(product_id: str, would_sell: bool, note: str = "") -> str:
        """Record the owner's verdict on a product. Becomes training data for
        the next System One head — this is how the model stays personal."""
        memory.record_label(product_id, int(would_sell), note)
        return json.dumps({"product_id": product_id, "label": int(would_sell),
                           "note": note, "status": "recorded"})

    @tool
    def find_suppliers(product_id: str, n: int = 5) -> str:
        """NEGOTIATION PHASE: web-search manufacturers/wholesalers for a shortlisted
        product (Exa, SearXNG fallback). Returns JSON supplier candidates."""
        product = registry.get(product_id)
        if product is None:
            return json.dumps({"error": f"unknown product {product_id}"})
        result = _find_suppliers(product, settings, n=n)
        for s in result["suppliers"]:
            _suppliers[s["url"]] = s
        return json.dumps(result)

    @tool
    def draft_outreach(product_id: str, supplier_url: str) -> str:
        """NEGOTIATION PHASE: draft (never send) a first-contact message to a supplier
        found by find_suppliers. Returns the draft as JSON."""
        product = registry.get(product_id)
        supplier = _suppliers.get(supplier_url)
        if product is None or supplier is None:
            return json.dumps({"error": "unknown product or supplier — run find_suppliers first"})
        draft = _draft_outreach(product, supplier, settings)
        _record_negotiation(memory.path, product_id, supplier,
                            "draft", draft["status"], draft)
        return json.dumps(draft)

    @tool
    def write_digest() -> str:
        """Publish the markdown digest of the latest shortlist. Returns the path."""
        stats = memory.stats()
        shortlisted: list[dict] = []
        import sqlite3
        with sqlite3.connect(memory.path) as conn:
            rows = conn.execute(
                """SELECT p.title,p.price_usd,p.cost_usd,p.url,j.score,j.rationale
                   FROM judgments j JOIN products p ON p.id=j.product_id
                   WHERE j.choice='shortlist'
                   ORDER BY j.created DESC LIMIT 25"""
            ).fetchall()
        lines = [f"# Reflex digest — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                 f"\nScanned {stats['products_seen']} products total; "
                 f"{len(rows)} currently shortlisted by your System One model.\n"]
        for title, price, cost, url, score, rationale in rows:
            margin = (price - cost) / price if price else 0
            lines.append(f"## {title}\n- Price ${price:.2f} · margin {margin:.0%} · "
                         f"P(sell) {score:.2f}\n- {rationale}\n- {url}\n")
        if not rows:
            lines.append("_No shortlisted products yet. Run a triage cycle first._\n")
        digest = "\n".join(lines)
        settings.ensure_dirs()
        path = settings.digest_dir / f"digest-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        path.write_text(digest)
        memory.record_run({"n_scanned": stats["products_seen"],
                           "n_shortlisted": len(rows), "digest_path": str(path)})
        return json.dumps({"digest_path": str(path), "n_shortlisted": len(rows)})

    return [scan_products, system_one_judge, deep_dive_analysis,
            noul_gate, record_feedback, find_suppliers, draft_outreach,
            write_digest]
