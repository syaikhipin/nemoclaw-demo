"""System One decision head — the fast, personal, on-device judge.

Contract (mirrors the Jev typed-output idea: Choice / Score / Noul):
  judge(product) -> Judgment(choice, score, confidence, rationale, decided_by="system_one")

The reference implementation is a calibrated gradient-boosting classifier on
legible product features. It trains in seconds on CPU from 1-3k personal
"would I sell this?" labels and scores a product in <1ms — the whole point of
System One: fast, cheap, personal.

`DecisionHead` is a Protocol so the sklearn head can be swapped for a
Qwen3-0.6B typed head (CLM / NanoJev, see docs/clm-head.md) with zero changes
to the agent.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Protocol

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier

from .. import features as F
from ..config import Settings
from ..schemas import Choice, Judgment, Product

VERSION = "sklearn-hgb-v1"


class DecisionHead(Protocol):
    version: str

    def judge(self, product: Product) -> Judgment: ...
    def judge_batch(self, products: list[Product]) -> list[Judgment]: ...


def _choice_for(score: float, settings: Settings) -> Choice:
    if score >= settings.shortlist_at:
        return "shortlist"
    if score <= settings.pass_below:
        return "pass"
    return "research"


class SklearnHead:
    """Calibrated gradient boosting head trained on personal labels."""

    version = VERSION

    def __init__(self, settings: Settings | None = None):
        from ..config import SETTINGS
        self.settings = settings or SETTINGS
        base = HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.06, max_leaf_nodes=31,
            min_samples_leaf=20, l2_regularization=1.0, random_state=7,
        )
        self.model = CalibratedClassifierCV(base, method="sigmoid", cv=3)
        self._fitted = False

    def train(self, X: np.ndarray, y: np.ndarray) -> dict:
        # Platt calibration needs enough data to fit the sigmoid; on tiny
        # label sets it collapses, so we calibrate only when n >= 60.
        n = len(y)
        if n >= 60:
            self.model = CalibratedClassifierCV(self.model.estimator, method="sigmoid", cv=3)
        else:
            self.model = self.model.estimator
        self.model.fit(X, y)
        self._fitted = True
        train_acc = float(self.model.score(X, y))
        return {"train_accuracy": train_acc, "n": int(len(y)),
                "positive_rate": float(np.mean(y)), "version": self.version}

    def _score(self, product: Product) -> float:
        if not self._fitted:
            raise RuntimeError("Head not trained. Run scripts/bootstrap.py or train on your labels first.")
        x = np.array([F.to_vector(product)], dtype=float)
        return float(self.model.predict_proba(x)[0, 1])

    def judge(self, product: Product) -> Judgment:
        t0 = time.perf_counter()
        score = self._score(product)
        latency_ms = (time.perf_counter() - t0) * 1000
        choice = _choice_for(score, self.settings)
        feats = F.extract(product)
        top = sorted(feats.items(), key=lambda kv: abs(kv[1]), reverse=True)[:3]
        rationale = (f"System One ({self.version}): P(sell)={score:.2f} -> {choice}. "
                     f"Strongest signals: " + ", ".join(f"{k}={v:.2f}" for k, v in top) + ".")
        return Judgment(
            product_id=product.id, choice=choice, score=score,
            confidence=round(abs(score - 0.5) * 2, 3), rationale=rationale,
            decided_by="system_one", model_version=self.version, latency_ms=latency_ms,
        )

    def judge_batch(self, products: list[Product]) -> list[Judgment]:
        return [self.judge(p) for p in products]

    def save(self, path: Path | None = None) -> Path:
        path = path or self.settings.model_path
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self.model, "version": self.version}, path)
        return path

    @classmethod
    def load(cls, settings: Settings | None = None, path: Path | None = None) -> "SklearnHead":
        from ..config import SETTINGS
        settings = settings or SETTINGS
        path = path or settings.model_path
        head = cls(settings)
        blob = joblib.load(path)
        head.model = blob["model"]
        head.version = blob.get("version", VERSION)
        head._fitted = True
        return head
