"""Retrain the System One head on real labels (human labels win over seed labels)."""

from __future__ import annotations

from reflex.config import SETTINGS
from reflex.memory import Memory
from reflex.system_one.train import train_from_labeled


def main() -> None:
    settings = SETTINGS
    memory = Memory(settings)
    items = [(p, y) for p, y in memory.labeled_products()
             if "held-out" not in _note_of(memory, p.id)]
    if len(items) < 20:
        raise SystemExit(f"[retrain] only {len(items)} usable labels — need >= 20.")
    head, report = train_from_labeled([p for p, _ in items],
                                     [y for _, y in items], settings)
    head.save()
    print(f"[retrain] trained on {report['n']} personal labels, "
          f"train acc {report['train_accuracy']:.3f} -> {settings.model_path}")


def _note_of(memory: Memory, product_id: str) -> str:
    import sqlite3
    with sqlite3.connect(memory.path) as conn:
        row = conn.execute("SELECT note FROM labels WHERE product_id=?",
                           (product_id,)).fetchone()
    return row[0] if row else ""


if __name__ == "__main__":
    main()
