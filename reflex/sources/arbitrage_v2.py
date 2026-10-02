"""v2 arbitrage source — ID -> EU deal pairs.

Each record is one *deal*: an ID (home-market) sourcing cost against an EU
retail price. The seed dataset (data/v2-arbitrage-pairs.jsonl) is ILLUSTRATIVE
— plausible pairs used for the demo and for training the head's margin-gap
instinct. Real marketplace adapters (ID marketplaces -> EU retail feeds)
plug in behind this same ProductSource interface; the agent contract
(fetch -> list[Product]) does not change.

Mapping onto Product:
  price_usd = EU retail price (what the buyer pays)
  cost_usd  = ID landed sourcing cost (what we pay)
  margin    = the arbitrage gap the head learns to judge
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

from ..schemas import Product
from .base import ProductSource

DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "v2-arbitrage-pairs.jsonl"


class ArbitrageSource(ProductSource):
    name = "v2-arbitrage"

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else DATA_PATH
        self._pairs: list[dict] | None = None

    def _load(self) -> list[dict]:
        if self._pairs is None:
            pairs = []
            with open(self.path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        pairs.append(json.loads(line))
            self._pairs = pairs
        return self._pairs

    def __len__(self) -> int:  # noqa: D105
        return len(self._load())

    def fetch(self, limit: int = 40, seed: int | None = None) -> list[Product]:
        pairs = list(self._load())
        rng = random.Random(seed if seed is not None else int(time.time()) % 100000)
        rng.shuffle(pairs)
        out = []
        for p in pairs[:limit]:
            eu = float(p["eu_price_usd"])
            cost = float(p["id_cost_usd"])
            mult = round(eu / cost, 1) if cost > 0 else 0.0
            out.append(Product(
                id=p["id"], title=p["title"], category=p["category"],
                price_usd=eu, cost_usd=cost,
                supplier="ID marketplace (illustrative)",
                rating=float(p.get("rating", 0)), reviews=int(p.get("reviews", 0)),
                shipping_days=int(p.get("shipping_days", 14)),
                description=(f"{p.get('description', '')} "
                             f"[Illustrative v2 pair: ID ${cost:.2f} -> EU ${eu:.2f} "
                             f"= {mult}x margin]"),
                url="", image_url="", source="v2-arbitrage",
            ))
        return out
