"""Amazon fashion product source — the real dataset behind
qdrant-labs/demo-ecommerce-search (McAuley-Lab/Amazon-Reviews-2023,
meta_Clothing_Shoes_and_Jewelry.jsonl).

Real fields used as-is: title, price, average_rating, rating_number, store,
categories, images, parent_asin.
Synthesized deterministically (seeded by ASIN, documented here): cost_usd
(dropship sourcing-cost estimate) and shipping_days. Everything derived from
real data is preferred; the synthetic fields exist because a triage model
needs landed-cost and logistics signals the metadata doesn't carry.
"""

from __future__ import annotations

import ast
import hashlib
import json
import random
import time
from pathlib import Path

from ..schemas import Product
from .base import ProductSource

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "amazon_fashion.jsonl"


def _seeded(asin: str, salt: str) -> random.Random:
    h = hashlib.sha256(f"{asin}:{salt}".encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def _image_url(raw: object) -> str:
    if not raw:
        return ""
    try:
        items = ast.literal_eval(raw) if isinstance(raw, str) else raw
        if isinstance(items, list) and items:
            first = items[0]
            if isinstance(first, dict):
                return first.get("hi_res") or first.get("large") or first.get("thumb") or ""
    except Exception:
        pass
    return ""


def _category(categories: list) -> str:
    if not categories:
        return "fashion"
    leaf = str(categories[-1]).strip() or "fashion"
    return leaf[:60]


class AmazonFashionSource(ProductSource):
    """Real Amazon fashion products. fetch() returns random unseen-friendly samples."""

    name = "amazon_fashion"
    path: Path = DATA_PATH

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else self.path
        if not self.path.exists():
            raise FileNotFoundError(
                f"Amazon dataset not found at {self.path}. "
                "Run: .venv/bin/python -m scripts.fetch_amazon_data")
        self._products: list[Product] | None = None

    def _load(self) -> list[Product]:
        if self._products is not None:
            return self._products
        products: list[Product] = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                title = (d.get("title") or "").strip()
                price = d.get("price")
                asin = d.get("parent_asin") or ""
                if not title or not asin or not isinstance(price, (int, float)) or price <= 0:
                    continue
                margin = _seeded(asin, "margin").uniform(0.45, 0.72)  # synthetic sourcing cost
                cost = round(price * (1 - margin), 2)
                shipping = _seeded(asin, "ship").choice([5, 7, 9, 12, 14])  # synthetic
                feats = d.get("features") or []
                desc = " | ".join(str(x) for x in feats[:6]) or str(d.get("description") or "")
                rating = d.get("average_rating") or 0.0
                reviews = d.get("rating_number") or 0
                products.append(Product(
                    id=f"amz-{asin}",
                    title=title[:220],
                    category=_category(d.get("categories") or []),
                    price_usd=round(float(price), 2),
                    cost_usd=cost,
                    supplier=str(d.get("store") or "Amazon marketplace")[:60],
                    rating=float(rating) if rating else 0.0,
                    reviews=int(reviews) if reviews else 0,
                    shipping_days=shipping,
                    description=desc[:600],
                    url=f"https://www.amazon.com/dp/{asin}",
                    image_url=_image_url(d.get("images")),
                    source=self.name,
                ))
        self._products = products
        return products

    def __len__(self) -> int:
        return len(self._load())

    def fetch(self, limit: int = 40, seed: int | None = None) -> list[Product]:
        rng = random.Random(seed if seed is not None else int(time.time()) % 100000)
        pool = self._load()
        if limit >= len(pool):
            return list(pool)
        return rng.sample(pool, limit)
