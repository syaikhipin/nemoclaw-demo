"""Distillation: a large teacher (Hermes via NVIDIA NIM) labels products,
the small System One head learns to imitate those judgments.

This is *policy distillation* for the cold-start problem: before Julio has
labeled 1-3k products himself, the teacher provides draft labels. The
personal labels (from scripts/label.py) always take precedence — when both
exist for a product, the human label wins. That ordering is what keeps the
model *personal* instead of *a smaller copy of the teacher*.
"""

from __future__ import annotations

from ..config import Settings
from ..schemas import Product
from ..system_two import SystemTwoAnalyst
from .train import train_from_labeled


def distill(products: list[Product], human_labels: dict[str, int] | None = None,
            settings: Settings | None = None, teacher_threshold: float = 0.6):
    """Label `products` with the teacher, merge human labels, train the head.

    Returns (head, report) where report includes how many labels came from
    the human vs the teacher.
    """
    from ..config import SETTINGS
    settings = settings or SETTINGS
    human_labels = human_labels or {}
    analyst = SystemTwoAnalyst(settings)

    X_products, y = [], []
    n_human = n_teacher = 0
    for p in products:
        if p.id in human_labels:
            X_products.append(p)
            y.append(int(human_labels[p.id]))
            n_human += 1
            continue
        analysis = analyst.analyze(p)
        X_products.append(p)
        y.append(1 if analysis.score >= teacher_threshold else 0)
        n_teacher += 1

    head, report = train_from_labeled(X_products, y, settings)
    report.update({"n_human_labels": n_human, "n_teacher_labels": n_teacher,
                   "teacher": analyst.describe()})
    return head, report
