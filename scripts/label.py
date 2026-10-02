"""Interactive labeling CLI — this is where the model becomes *personal*.

Each "would I sell this?" verdict is stored in memory and becomes training
data. Target: 1,000-3,000 labels for a strong personal head; 300 is enough
for a first useful pilot.
"""

from __future__ import annotations

from reflex.config import SETTINGS
from reflex.memory import Memory
from reflex.sources.catalog import MockCatalog


def main() -> None:
    settings = SETTINGS
    settings.ensure_dirs()
    memory = Memory(settings)
    labeled_ids = set(memory.get_labels())

    products = [p for p in MockCatalog(seed=7, size=400).fetch(400)
                if p.id not in labeled_ids]
    memory.upsert_products(products)
    print(f"[label] {len(labeled_ids)} already labeled, {len(products)} to go. "
          "y = would sell, n = pass, s = skip, q = quit.\n")

    count = 0
    for p in products:
        print(f"--- {p.title} [{p.category}] ---")
        print(f"  ${p.price_usd:.2f} (cost ${p.cost_usd:.2f}, margin {p.margin:.0%}) | "
              f"{p.rating}/5 ({p.reviews} reviews) | {p.shipping_days}d shipping")
        print(f"  {p.description}")
        ans = input("  would you sell this? [y/n/s/q] ").strip().lower()
        if ans == "q":
            break
        if ans == "s":
            continue
        if ans in ("y", "n"):
            note = input("  note (optional): ").strip()
            memory.record_label(p.id, 1 if ans == "y" else 0, note)
            count += 1
            print(f"  recorded ({count} this session, {len(labeled_ids) + count} total)\n")
    print(f"[label] done — {count} new labels. Retrain with: "
          ".venv/bin/python -m scripts.retrain")


if __name__ == "__main__":
    main()
