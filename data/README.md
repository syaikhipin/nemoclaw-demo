# Data

This repo ships **no real product data and no real personal labels** — and that
is deliberate. The personal System One model is only personal once it trains
on *your* decisions.

## What runs out of the box
- `reflex/sources/catalog.py` — a deterministic synthetic catalog (offline stand-in
  for a real feed: AliExpress/CJ Dropshipping API, etc.).
- `scripts/bootstrap.py` — generates 400 products + 300 labels from a documented
  **synthetic persona** (a stand-in for the owner's taste), trains the head, and
  holds out 100 products for eval.

## Making it yours (the part that matters for the challenge)
1. `.venv/bin/python -m scripts.label` — answer "would I sell this?" for ~300
   products (pilot) up to 1,000–3,000 (strong). See `docs/labeling-protocol.md`.
2. `.venv/bin/python -m scripts.retrain` — trains on your labels. Human labels
   always override teacher/persona labels for the same product.
3. Point `reflex/sources/` at a real feed by implementing `ProductSource`.

## Labeling protocol (summary)
Binary question per product: **"would I sell this?"** — yes/no, optional note.
Target markets, categories, margin floors and shipping ceilings are yours to set;
write them down first (they become the System Two analyst's rubric too).
Aim for a 70–100 item held-out set you never train on.
