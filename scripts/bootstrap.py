"""Bootstrap: seed catalog -> seed labels -> train head -> evaluate.

The seed labels come from a *synthetic persona* — a documented stand-in for
Julio's taste, used only so the repo runs end-to-end out of the box. Replace
them with real labels from scripts/label.py ("would I sell this?"); the
personal model is only personal once it trains on the owner's decisions.
"""

from __future__ import annotations

import random

from reflex import features as F
from reflex.config import SETTINGS
from reflex.memory import Memory
from reflex.schemas import Product
from reflex.sources import default_source
from reflex.system_one.train import train_from_labeled

PERSONA = (
    "synthetic-persona-v1: prefers margin>=55%, shipping<=9d, rating>=4.4 with "
    "1000+ reviews; avoids thin margins and slow shipping. STAND-IN ONLY."
)


def persona_label(product: Product, rng: random.Random) -> int:
    score = 0.0
    score += 2.0 if product.margin >= 0.55 else (-1.5 if product.margin < 0.35 else 0.0)
    score += 1.5 if product.shipping_days <= 9 else (-1.5 if product.shipping_days > 12 else 0.0)
    score += 1.5 if (product.rating >= 4.4 and product.reviews >= 1000) else 0.0
    score += 0.5 if product.price_usd <= 40 else -0.5
    score += rng.uniform(-0.6, 0.6)  # human noise
    return 1 if score > 1.0 else 0


def main() -> None:
    settings = SETTINGS
    settings.ensure_dirs()
    rng = random.Random(42)

    catalog = default_source()
    products = catalog.fetch(400)
    print(f"[bootstrap] source: {catalog.name} ({len(catalog)} products available)")
    memory = Memory(settings)
    memory.upsert_products(products)

    labeled = [(p, persona_label(p, rng)) for p in products]
    rng.shuffle(labeled)
    train_items, eval_items = labeled[:300], labeled[300:400]
    for p, y in eval_items:  # held-out set stays in memory, flagged by note
        memory.record_label(p.id, y, note="held-out eval (" + PERSONA + ")")

    head, report = train_from_labeled([p for p, _ in train_items],
                                     [y for _, y in train_items], settings)
    head.save()
    print(f"[bootstrap] trained on {report['n']} labels "
          f"(train acc {report['train_accuracy']:.3f}) -> {settings.model_path}")

    from eval.evaluate import evaluate
    eval_report = evaluate(head, eval_items)
    print("[bootstrap] held-out eval:")
    for k, v in eval_report.items():
        print(f"  {k}: {v}")
    print(f"[bootstrap] persona: {PERSONA}")
    print("[bootstrap] next: run scripts/label.py to add YOUR labels, retrain, and make it personal.")


if __name__ == "__main__":
    main()
