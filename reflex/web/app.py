"""Reflex web demo — the claw, demonstrable in a browser.

Run:  .venv/bin/python -m reflex.web.app --port 8765
Then open http://localhost:8765 (or the tunnel URL).

Sections: run a live triage cycle, browse the shortlist, test the Noul gate,
chat with the deep agent (GLM), read the latest digest, see live metrics.
"""

from __future__ import annotations

import argparse
import html
import re
import sqlite3
import time

from flask import Flask, jsonify, render_template, request

from .. import noul
from ..config import Settings
from ..memory import Memory
from ..sources import default_source

_agent = None  # lazy deep agent (GLM)


def get_agent(settings: Settings):
    global _agent
    if _agent is None:
        from ..deepagent.graph import build_agent
        _agent = build_agent(settings)
    return _agent


def md_to_html(md: str) -> str:
    out = []
    for line in md.splitlines():
        if line.startswith("### "):
            out.append(f"<h4>{html.escape(line[4:])}</h4>")
        elif line.startswith("## "):
            out.append(f"<h3>{html.escape(line[3:])}</h3>")
        elif line.startswith("# "):
            out.append(f"<h2>{html.escape(line[2:])}</h2>")
        elif line.strip() == "---":
            out.append("<hr>")
        elif line.startswith("- "):
            item = html.escape(line[2:])
            item = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", item)
            out.append(f"<li>{item}</li>")
        elif line.strip().startswith("_") and line.strip().endswith("_"):
            out.append(f"<p><i>{html.escape(line.strip().strip('_'))}</i></p>")
        elif line.strip():
            out.append(f"<p>{html.escape(line.strip())}</p>")
    return "\n".join(out).replace("</p>\n<li>", "</p>\n<ul>\n<li>").replace("</li>\n<p>", "</li>\n</ul>\n<p>")


def create_app(settings: Settings | None = None) -> Flask:
    from ..config import SETTINGS
    settings = settings or SETTINGS
    settings.ensure_dirs()
    app = Flask(__name__)

    @app.get("/")
    def index():
        mem = Memory(settings)
        return render_template("index.html",
                               provider=settings.llm_provider,
                               offline=settings.offline,
                               stats=mem.stats())

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "provider": settings.llm_provider,
                        "offline": settings.offline})

    @app.post("/api/cycle")
    def cycle():
        from ..serve import run_cycle
        body = request.get_json(force=True, silent=True) or {}
        limit = int(body.get("limit", 24))
        seed = int(time.time()) % 100000  # fresh products every demo run
        src = default_source()
        stats = run_cycle(settings, limit=limit, source=src, seed=seed)
        stats["judgments"] = _recent_judgments(settings, limit=limit)
        return jsonify(stats)

    @app.get("/api/judgments")
    def judgments():
        return jsonify(_recent_judgments(settings))

    @app.get("/api/digest")
    def digest():
        digests = sorted(settings.digest_dir.glob("digest-*.md"))
        if not digests:
            return jsonify({"html": "<p><i>No digest yet — run a triage cycle.</i></p>",
                            "path": None})
        latest = digests[-1]
        return jsonify({"html": md_to_html(latest.read_text()), "path": latest.name})

    @app.get("/api/metrics")
    def metrics():
        mem = Memory(settings)
        out = {"memory": mem.stats(), "eval": None, "provider": settings.llm_provider}
        held_out = [(p, y) for p, y in mem.labeled_products()
                    if _note(mem, p.id).startswith("held-out")]
        if held_out and (settings.model_path.exists()):
            from ..system_one import SklearnHead
            try:
                from eval.evaluate import evaluate
                out["eval"] = evaluate(SklearnHead.load(settings), held_out)
            except Exception as exc:
                out["eval_error"] = str(exc)
        return jsonify(out)

    @app.post("/api/noul")
    def noul_check():
        body = request.get_json(force=True, silent=True) or {}
        verdict = noul.check(body.get("action", ""))
        return jsonify(verdict.to_dict())

    # -- negotiation phase ---------------------------------------------------
    @app.post("/api/negotiate/suppliers")
    def negotiate_suppliers():
        from ..negotiation import find_suppliers
        body = request.get_json(force=True, silent=True) or {}
        product = _get_product(settings, body.get("product_id", ""))
        if product is None:
            return jsonify({"error": "unknown product_id"}), 404
        return jsonify(find_suppliers(product, settings,
                                      n=int(body.get("n", 5))))

    @app.post("/api/negotiate/draft")
    def negotiate_draft():
        from ..negotiation import draft_outreach, record
        body = request.get_json(force=True, silent=True) or {}
        product = _get_product(settings, body.get("product_id", ""))
        supplier = body.get("supplier") or {}
        if product is None or not supplier.get("url"):
            return jsonify({"error": "need product_id and supplier"}), 400
        draft = draft_outreach(product, supplier, settings)
        record(Memory(settings).path, product.id, supplier,
               "draft", draft["status"], draft)
        return jsonify(draft)

    @app.post("/api/negotiate/simulate")
    def negotiate_simulate():
        from ..negotiation import record, simulate
        body = request.get_json(force=True, silent=True) or {}
        product = _get_product(settings, body.get("product_id", ""))
        supplier = body.get("supplier") or {}
        if product is None or not supplier.get("url"):
            return jsonify({"error": "need product_id and supplier"}), 400
        target = float(body.get("target_unit_price") or product.cost_usd)
        try:
            result = simulate(product, supplier, target,
                              rounds=int(body.get("rounds", 3)), settings=settings)
        except Exception as exc:
            return jsonify({"error": f"simulation failed: {exc}"}), 500
        record(Memory(settings).path, product.id, supplier,
               "simulation", result["status"], result)
        return jsonify(result)

    @app.post("/api/agent")
    def agent_chat():
        body = request.get_json(force=True, silent=True) or {}
        message = body.get("message", "").strip()
        if not message:
            return jsonify({"error": "empty message"}), 400
        try:
            agent = get_agent(settings)
            result = agent.invoke(
                {"messages": [{"role": "user", "content": message}]},
                config={"configurable": {"thread_id": f"web-{int(time.time())}"}},
            )
            reply = result["messages"][-1].content
            return jsonify({"reply": reply})
        except Exception as exc:
            return jsonify({"error": f"agent error: {exc}"}), 500

    return app


def _recent_judgments(settings: Settings, limit: int = 50) -> list[dict]:
    mem = Memory(settings)
    with sqlite3.connect(mem.path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT j.product_id, j.choice, j.score, j.confidence, j.rationale,
                      j.decided_by, j.model_version, j.created,
                      p.title, p.price_usd, p.cost_usd, p.url, p.category, p.image_url,
                      p.source
               FROM judgments j JOIN products p ON p.id = j.product_id
               ORDER BY j.created DESC LIMIT ?""", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["margin"] = round((d["price_usd"] - d["cost_usd"]) / d["price_usd"], 3) \
            if d["price_usd"] else 0
        out.append(d)
    return out


def _note(mem: Memory, product_id: str) -> str:
    with sqlite3.connect(mem.path) as conn:
        row = conn.execute("SELECT note FROM labels WHERE product_id=?",
                           (product_id,)).fetchone()
    return row[0] if row else ""


def _get_product(settings: Settings, product_id: str):
    from ..schemas import Product
    mem = Memory(settings)
    with sqlite3.connect(mem.path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d.pop("first_seen", None)
    return Product.from_dict(d)


def main() -> None:
    ap = argparse.ArgumentParser(description="Reflex web demo")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    app = create_app()
    print(f"[reflex-web] demo at http://{args.host}:{args.port} "
          f"(provider: {Settings().llm_provider})")
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
