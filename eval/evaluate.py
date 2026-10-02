"""Held-out evaluation for the System One head.

Reports what the judges (and Julio) actually care about:
- accuracy on the held-out set
- calibration (expected calibration error) — is P(sell)=0.8 right 80% of the time?
- abstention rate (choice == "research") — what fraction escalates to System Two
- latency — System One must be ~instant
- cost proxy — fraction of products decided without any LLM call
"""

from __future__ import annotations

import numpy as np

from reflex.schemas import Product
from reflex.system_one import SklearnHead


def expected_calibration_error(y_true: np.ndarray, probs: np.ndarray,
                               n_bins: int = 10) -> float:
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        mask = (probs > lo) & (probs <= hi)
        if mask.sum() == 0:
            continue
        acc = y_true[mask].mean()
        conf = probs[mask].mean()
        ece += (mask.sum() / len(probs)) * abs(acc - conf)
    return float(ece)


def evaluate(head: SklearnHead, eval_items: list[tuple[Product, int]]) -> dict:
    products = [p for p, _ in eval_items]
    y_true = np.array([y for _, y in eval_items])
    judgments = head.judge_batch(products)
    probs = np.array([j.score for j in judgments])
    preds = (probs >= 0.5).astype(int)
    latencies = [j.latency_ms for j in judgments]

    choices = [j.choice for j in judgments]
    return {
        "n": len(eval_items),
        "accuracy": round(float((preds == y_true).mean()), 4),
        "ece": round(expected_calibration_error(y_true, probs), 4),
        "abstention_rate_research": round(choices.count("research") / len(choices), 4),
        "shortlist_rate": round(choices.count("shortlist") / len(choices), 4),
        "decided_without_llm": round(
            sum(1 for j in judgments if j.choice in ("shortlist", "pass")) / len(judgments), 4),
        "mean_latency_ms": round(float(np.mean(latencies)), 3),
        "p99_latency_ms": round(float(np.percentile(latencies, 99)), 3),
        "model_version": head.version,
    }
