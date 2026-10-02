# Upgrade path: Qwen3-0.6B typed head (CLM / NanoJev)

The shipped `SklearnHead` is the *reference* System One implementation: it trains
in seconds on CPU and proves the architecture end-to-end. The challenge-grade
upgrade is a 0.6B language-model head with typed Choice/Score/Noul outputs,
following the OpenJev ecosystem (CLM as primary codebase, NanoJev as baseline).

## Why the swap is clean
`DecisionHead` is a Protocol (`reflex/system_one/__init__.py`):

```python
class DecisionHead(Protocol):
    version: str
    def judge(self, product: Product) -> Judgment: ...
    def judge_batch(self, products: list[Product]) -> list[Judgment]: ...
```

The agent, tools, loop, memory and eval only ever touch `judge`/`judge_batch`.
A new head just implements the Protocol and gets loaded by the same
`SklearnHead.load` call site (rename to `load_head`).

## What the 0.6B head looks like
- **Backbone**: frozen Qwen3-0.6B (runs on-device, ~1.2GB Q8).
- **Heads**: three typed projections trained on your labels —
  `Choice` (shortlist/pass/research), `Score` (calibrated sellability),
  `Noul` (money-movement veto, trained on blocked-action examples).
- **Training data**: the same `(product, label)` pairs from `scripts/label.py`,
  rendered as prompt→typed-output examples; teacher traces from Hermes
  (distillation) as augmentation. Human labels always win.
- **Codebase**: CLM (Apache-2.0, TypeSafe-compatible API, frozen Qwen3-8B
  encoder + trainable heads — swap encoder to Qwen3-0.6B) or NanoJev
  (typed heads directly on Qwen3-0.6B) as the comparison baseline.

## Suggested eval additions for the 0.6B head
- Head-to-head vs `sklearn-hgb-v1` on the same 70–100 item held-out set:
  accuracy, ECE, abstention rate, and *disagreement analysis* (where the LM
  head beats features, usually on title/description nuance).
- Latency budget: p99 < 500ms on-device, else it isn't System One anymore.

## What stays the same
Everything else. The personal-data story — labels from the owner's own
decisions, human-over-teacher precedence, the labeling protocol — is
model-agnostic. That is the actual moat, not the parameter count.
