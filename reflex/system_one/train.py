"""Training entry point: labels -> fitted System One head."""

from __future__ import annotations

import numpy as np

from .. import features as F
from ..config import Settings
from ..schemas import Product
from . import SklearnHead


def train_from_labeled(products: list[Product], labels: list[int],
                       settings: Settings | None = None) -> tuple[SklearnHead, dict]:
    """Train the head on (product, 0/1 "would I sell this?") pairs."""
    assert len(products) == len(labels) and len(products) > 0, "need labeled examples"
    X = np.array([F.to_vector(p) for p in products], dtype=float)
    y = np.array(labels, dtype=int)
    head = SklearnHead(settings)
    report = head.train(X, y)
    return head, report
