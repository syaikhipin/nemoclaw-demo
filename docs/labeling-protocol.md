# Labeling protocol — "would I sell this?"

The System One head is a mirror of your commercial taste. Garbage labels in,
garbage triage out. This protocol keeps the 1–3k labels you produce consistent
enough to distill.

## Before you label
Write down your selling criteria (one page, keep it next to you while labeling):
1. **Target market** — who buys? (country, age band, income feel)
2. **Categories** — in-scope / out-of-scope (e.g. no supplements, no replicas)
3. **Margin floor** — minimum landed margin (suggestion: 55%)
4. **Shipping ceiling** — max acceptable days (suggestion: 9, or EU/US warehouse)
5. **Social-proof floor** — e.g. ≥4.4★ with ≥1,000 reviews, or a plan to build it
6. **Price band** — e.g. $15–$60 sweet spot for impulse dropshipping
7. **Daily review capacity** — how many shortlisted products you can actually vet

These same criteria become the System Two analyst's rubric (see
`reflex/system_two/__init__.py::_SELLING_CRITERIA`).

## The question
For each product, answer exactly one binary question:

> **"Would I list this in my store tomorrow?"**

- `y` — yes, it clears my criteria and I'd spend ad money testing it
- `n` — no, fails a criterion or my gut says no
- `s` — skip (can't tell from the listing; these are the honest ones)
- optional note — *why*, in a few words ("thin margin", "saturated", "great gift angle")

## Discipline
- Label in sessions of 50–100; fatigue shows up as noise after that.
- Don't look at the model's current score while labeling — label blind.
- Don't relabel old items when your criteria evolve; version the criteria and
  note the date instead. Criteria drift is data, not error.
- Keep a 70–100 item held-out set you never train on (bootstrap does this for
  the seed labels; do the same for yours: label first, split after).

## Volume targets
- **300** — pilot: a useful head, the challenge demo minimum
- **1,000** — solid personal specialist
- **3,000** — diminishing returns for most single-category sellers; spend the
  time on the held-out eval instead
