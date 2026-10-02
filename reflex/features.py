"""Feature extraction: product -> numeric vector the System One head consumes.

Features are deliberately legible (price, margin, social proof, logistics,
category) so a human can audit *why* the model leans a certain way, and so the
same vector works for the sklearn reference head and for a future Qwen3-0.6B
typed head (CLM / NanoJev) without changing the agent contract.
"""

from __future__ import annotations

import math
import re

from .schemas import Product

TRENDING_WORDS = {
    "smart", "led", "mini", "pro", "electric", "magnetic", "foldable",
    "wireless", "portable", "2.0", "plus", "max",
}
CATEGORIES = ["home", "pets", "fitness", "beauty", "kitchen", "tech"]


def extract(product: Product) -> dict[str, float]:
    title = product.title.lower()
    words = set(re.findall(r"[a-z0-9.]+", title))
    feats: dict[str, float] = {
        "price": product.price_usd,
        "log_price": math.log1p(product.price_usd),
        "margin": product.margin,
        "rating": product.rating,
        "log_reviews": math.log1p(product.reviews),
        "shipping_days": float(product.shipping_days),
        "title_len": float(len(title)),
        "trending_hits": float(len(words & TRENDING_WORDS)),
        "fast_shipping": 1.0 if product.shipping_days <= 9 else 0.0,
        "high_margin": 1.0 if product.margin >= 0.6 else 0.0,
        "social_proof": 1.0 if (product.rating >= 4.4 and product.reviews >= 1000) else 0.0,
    }
    for cat in CATEGORIES:
        feats[f"cat_{cat}"] = 1.0 if product.category == cat else 0.0
    return feats


FEATURE_NAMES: list[str] = list(extract(Product(
    id="", title="", category="home", price_usd=0, cost_usd=0, supplier="",
    rating=0, reviews=0, shipping_days=0, description="",
)).keys())


def to_vector(product: Product) -> list[float]:
    feats = extract(product)
    return [feats[name] for name in FEATURE_NAMES]
