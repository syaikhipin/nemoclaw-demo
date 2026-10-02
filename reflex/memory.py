"""Durable memory: SQLite store for products, judgments, labels, feedback, runs.

The agent is long-running; memory is what makes each cycle smarter than the
last: seen products are never re-scanned, human feedback becomes training
data, and digests accumulate into a reviewable history.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from .config import Settings
from .schemas import Judgment, Product

_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY, title TEXT, category TEXT, price_usd REAL, cost_usd REAL,
    supplier TEXT, rating REAL, reviews INTEGER, shipping_days INTEGER,
    description TEXT, url TEXT, image_url TEXT DEFAULT '', source TEXT, first_seen REAL
);
CREATE TABLE IF NOT EXISTS judgments (
    id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT, choice TEXT, score REAL,
    confidence REAL, rationale TEXT, decided_by TEXT, model_version TEXT,
    latency_ms REAL, created REAL
);
CREATE TABLE IF NOT EXISTS labels (
    product_id TEXT PRIMARY KEY, label INTEGER, note TEXT, created REAL
);
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, started REAL, n_scanned INTEGER,
    n_shortlisted INTEGER, n_passed INTEGER, n_research INTEGER, digest_path TEXT
);
"""


class Memory:
    def __init__(self, settings: Settings | None = None):
        from .config import SETTINGS
        self.settings = settings or SETTINGS
        self.path = self.settings.db_path

    def _connect(self) -> sqlite3.Connection:
        self.settings.ensure_dirs()
        conn = sqlite3.connect(self.path)
        conn.executescript(_SCHEMA)
        return conn

    # -- products ------------------------------------------------------------
    def upsert_products(self, products: list[Product]) -> int:
        now = time.time()
        with self._connect() as conn:
            cur = conn.executemany(
                """INSERT INTO products
                   (id,title,category,price_usd,cost_usd,supplier,rating,reviews,
                    shipping_days,description,url,image_url,source,first_seen)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO NOTHING""",
                [(p.id, p.title, p.category, p.price_usd, p.cost_usd, p.supplier,
                  p.rating, p.reviews, p.shipping_days, p.description, p.url,
                  p.image_url, p.source, now) for p in products],
            )
            return cur.rowcount

    def unseen(self, products: list[Product]) -> list[Product]:
        with self._connect() as conn:
            seen = {r[0] for r in conn.execute("SELECT id FROM products")}
        return [p for p in products if p.id not in seen]

    def unjudged(self, products: list[Product]) -> list[Product]:
        """Products the System One head has not judged yet.

        Training labels (bootstrap) upsert products without judging them,
        so "seen" is the wrong filter for a triage cycle — this is the
        right one.
        """
        with self._connect() as conn:
            judged = {r[0] for r in
                      conn.execute("SELECT DISTINCT product_id FROM judgments")}
        return [p for p in products if p.id not in judged]

    # -- judgments -----------------------------------------------------------
    def record_judgments(self, judgments: list[Judgment]) -> None:
        now = time.time()
        with self._connect() as conn:
            conn.executemany(
                """INSERT INTO judgments
                   (product_id,choice,score,confidence,rationale,decided_by,
                    model_version,latency_ms,created)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                [(j.product_id, j.choice, j.score, j.confidence, j.rationale,
                  j.decided_by, j.model_version, j.latency_ms, now) for j in judgments],
            )

    # -- labels / feedback ---------------------------------------------------
    def record_label(self, product_id: str, label: int, note: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO labels (product_id,label,note,created) VALUES (?,?,?,?)"
                " ON CONFLICT(product_id) DO UPDATE SET label=excluded.label,"
                " note=excluded.note, created=excluded.created",
                (product_id, int(label), note, time.time()),
            )

    def get_labels(self) -> dict[str, int]:
        with self._connect() as conn:
            return {r[0]: r[1] for r in conn.execute("SELECT product_id,label FROM labels")}

    def labeled_products(self) -> list[tuple[Product, int]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT p.*, l.label FROM products p
                   JOIN labels l ON l.product_id = p.id"""
            ).fetchall()
        cols = ["id", "title", "category", "price_usd", "cost_usd", "supplier",
                "rating", "reviews", "shipping_days", "description", "url",
                "image_url", "source", "first_seen"]
        out = []
        for r in rows:
            d = dict(zip(cols, r[:-1]))
            out.append((Product.from_dict(d), int(r[-1])))
        return out

    # -- runs ----------------------------------------------------------------
    def record_run(self, stats: dict) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO runs (started,n_scanned,n_shortlisted,n_passed,n_research,digest_path)"
                " VALUES (?,?,?,?,?,?)",
                (time.time(), stats.get("n_scanned", 0), stats.get("n_shortlisted", 0),
                 stats.get("n_passed", 0), stats.get("n_research", 0),
                 stats.get("digest_path", "")),
            )
            return cur.lastrowid

    def stats(self) -> dict:
        with self._connect() as conn:
            q = lambda s: conn.execute(s).fetchone()[0]  # noqa: E731
            return {
                "products_seen": q("SELECT COUNT(*) FROM products"),
                "judgments": q("SELECT COUNT(*) FROM judgments"),
                "labels": q("SELECT COUNT(*) FROM labels"),
                "runs": q("SELECT COUNT(*) FROM runs"),
                "shortlist_rate": q("SELECT AVG(choice='shortlist') FROM judgments"),
            }
