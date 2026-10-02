"""Negotiation phase — supplier discovery to simulated deal table.

Pipeline:
  1. find_suppliers(product)  — Exa/SearXNG web search for manufacturers/wholesalers
  2. draft_outreach(product, supplier) — the LLM drafts the first-contact message (DRAFT ONLY)
  3. simulate(product, supplier, target) — the LLM roleplays the supplier for N rounds;
     ends with proposed terms. Clearly labeled SIMULATED — no real contact happens.

Safety: drafting and simulating are allowed. Anything that moves money or
contacts a real supplier still goes through the Noul gate and is blocked
until the owner approves.
"""

from __future__ import annotations

import json
import sqlite3
import time

from .. import llm
from ..config import Settings
from ..schemas import Product
from .search import search_suppliers

_NEGOTIATOR_SYS = """You are the buyer-side negotiator for Reflex, an independent e-commerce
seller. You are sharp, polite, and firm. You never reveal the seller's maximum
budget. You anchor low, concede slowly, and always trade concessions
("if you can do X, I can commit to Y units"). Keep messages under 120 words."""

_SUPPLIER_SYS = """You are roleplaying a wholesale supplier in a SIMULATED negotiation
for training/demo purposes. You are professional and margin-conscious: you
start ~18% above your walk-away price, concede in shrinking steps, and care
about order volume and payment terms. Never break character. Keep replies under
120 words. Reply in exactly this JSON shape:
{"message": "<your reply to the buyer>", "offer_unit_price": <number or null>,
 "offer_moq": <number or null>, "deal": <true|false>}."""


def find_suppliers(product: Product, settings: Settings | None = None,
                   n: int = 5) -> dict:
    from ..config import SETTINGS
    settings = settings or SETTINGS
    query = f"{product.title} {product.category} wholesale supplier manufacturer"
    provider, results = search_suppliers(query, n=n, settings=settings)
    return {"provider": provider, "query": query, "suppliers": results}


def draft_outreach(product: Product, supplier: dict,
                   settings: Settings | None = None) -> dict:
    """Draft (never send) the first-contact message to a supplier."""
    from ..config import SETTINGS
    settings = settings or SETTINGS
    label, text = llm.chat([
        {"role": "system", "content": _NEGOTIATOR_SYS},
        {"role": "user", "content": (
            f"Write a first-contact outreach message to this supplier:\n"
            f"Supplier: {supplier.get('title')} ({supplier.get('url')})\n"
            f"Context: {supplier.get('snippet', '')[:300]}\n\n"
            f"Product I want to source: {product.title} ({product.category}), "
            f"currently retailing ~${product.price_usd:.2f}.\n"
            f"Goal: introduce my store, ask for wholesale pricing tiers, MOQ, "
            f"lead time and whether they do blind dropshipping. "
            f"Professional, concise. Return ONLY the message text.")},
    ], settings)
    return {"draft": text, "provider": label, "status": "draft — not sent",
            "supplier": supplier}


def simulate(product: Product, supplier: dict, target_unit_price: float,
             rounds: int = 3, settings: Settings | None = None) -> dict:
    """Simulated negotiation: the LLM plays the supplier, our negotiator plays buyer."""
    from ..config import SETTINGS
    settings = settings or SETTINGS
    transcript: list[dict] = []
    buyer_history: list[dict] = []
    supplier_history: list[dict] = []
    walk_away = round(target_unit_price * 1.18, 2)

    buyer_open = (f"Hi — I'm sourcing '{product.title}' for my store "
                  f"(retails ~${product.price_usd:.2f}). What's your best unit "
                  f"price at 200 units, and your MOQ?")
    transcript.append({"role": "buyer", "message": buyer_open})
    buyer_history.append({"role": "user", "content": buyer_open})
    deal: dict | None = None

    for r in range(rounds):
        # supplier turn (roleplayed)
        _, s_json = llm.chat_json([
            {"role": "system", "content": _SUPPLIER_SYS},
            {"role": "user", "content": (
                f"Product: {product.title}. Your walk-away unit price is ${walk_away:.2f} "
                f"(never go below). Conversation so far:\n" +
                "\n".join(f"{t['role']}: {t['message']}" for t in transcript) +
                "\nRespond to the buyer's last message.")},
        ], settings)
        transcript.append({"role": "supplier (simulated)", "message": s_json["message"],
                           "offer": {k: s_json.get(k) for k in
                                     ("offer_unit_price", "offer_moq")}})
        supplier_history.append({"role": "user", "content": s_json["message"]})
        if s_json.get("deal"):
            deal = {"unit_price": s_json.get("offer_unit_price"),
                    "moq": s_json.get("offer_moq"), "round": r + 1}
            break
        # buyer turn
        _, b_text = llm.chat([
            {"role": "system", "content": _NEGOTIATOR_SYS},
            {"role": "user", "content": (
                f"Negotiating '{product.title}'. My target unit price: ${target_unit_price:.2f}. "
                f"Conversation so far:\n" +
                "\n".join(f"{t['role']}: {t['message']}" for t in transcript) +
                "\nWrite your next reply. Push toward the target without revealing it.")},
        ], settings)
        transcript.append({"role": "buyer", "message": b_text})

    return {"transcript": transcript, "deal": deal,
            "target_unit_price": target_unit_price,
            "status": "simulated — no real supplier contacted",
            "supplier": {"title": supplier.get("title"), "url": supplier.get("url")}}


# -- persistence --------------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS negotiations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT, supplier_title TEXT,
    supplier_url TEXT, kind TEXT, status TEXT, payload TEXT, created REAL
);
"""


def record(memory_db_path: str, product_id: str, supplier: dict,
           kind: str, status: str, payload: dict) -> int:
    with sqlite3.connect(memory_db_path) as conn:
        conn.execute(_SCHEMA)
        cur = conn.execute(
            "INSERT INTO negotiations (product_id,supplier_title,supplier_url,kind,status,payload,created)"
            " VALUES (?,?,?,?,?,?,?)",
            (product_id, supplier.get("title", ""), supplier.get("url", ""),
             kind, status, json.dumps(payload), time.time()))
        return cur.lastrowid
