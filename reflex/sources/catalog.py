"""Deterministic synthetic catalog. Offline stand-in for a real product feed.

The catalog is generated from a fixed seed so demos and tests are reproducible.
It is NOT training data for the personal model — labels come from the human
(labeling CLI) or from the teacher in distillation.
"""

from __future__ import annotations

import random

from ..schemas import Product
from .base import ProductSource

_CATEGORIES = {
    "home": ["LED Sunset Lamp", "Magnetic Spice Rack", "Foldable Storage Box", "Smart Humidifier"],
    "pets": ["Slow Feeder Bowl", "Pet Hair Remover Roller", "Calming Donut Bed", "GPS Collar Tag"],
    "fitness": ["Resistance Band Set", "Posture Corrector", "Smart Jump Rope", "Massage Gun Mini"],
    "beauty": ["Jade Roller Set", "LED Face Mask", "Hair Straightener Brush", "Electric Blackhead Remover"],
    "kitchen": ["Vegetable Chopper Pro", "Electric Milk Frother", "Silicone Stretch Lids", "Cold Brew Tower"],
    "tech": ["Mini Projector", "Bluetooth Tracker Card", "GaN Fast Charger", "LED Strip Lights"],
}

_SUPPLIERS = ["Shenzhen Bright", "Guangzhou Nova", "Yiwu Direct", "Dongguan Prime", "Ningbo Swift"]


class MockCatalog(ProductSource):
    name = "mock_catalog"

    def __init__(self, seed: int = 7, size: int = 400):
        self.seed = seed
        self.size = size

    def fetch(self, limit: int = 40, seed: int | None = None) -> list[Product]:
        rng = random.Random(seed if seed is not None else self.seed)
        products: list[Product] = []
        cats = list(_CATEGORIES)
        for i in range(min(limit, self.size)):
            cat = cats[i % len(cats)]
            base = rng.choice(_CATEGORIES[cat])
            variant = rng.choice(["Pro", "Plus", "2.0", "Mini", "Max", ""])
            title = f"{base} {variant}".strip()
            cost = round(rng.uniform(2.5, 28.0), 2)
            price = round(cost * rng.uniform(1.8, 4.2), 2)
            products.append(Product(
                id=f"mock-{self.seed}-{i:04d}",
                title=title,
                category=cat,
                price_usd=price,
                cost_usd=cost,
                supplier=rng.choice(_SUPPLIERS),
                rating=round(rng.uniform(3.4, 5.0), 1),
                reviews=rng.randint(12, 48000),
                shipping_days=rng.choice([5, 7, 9, 12, 15, 20]),
                description=f"{title} for {cat}. Ships from {rng.choice(['CN', 'EU warehouse', 'US warehouse'])}.",
                url=f"https://example.com/p/mock-{self.seed}-{i:04d}",
                source=self.name,
            ))
        return products
