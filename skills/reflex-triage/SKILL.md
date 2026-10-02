# Reflex Triage — skill for OpenClaw / Hermes / Deep Agents (NemoClaw)

## What this is
Reflex is a long-running claw agent that triages dropshipping products for an
independent e-commerce seller. Fast judgments run on the owner's **personal
System One decision model** (a small head distilled from their own "would I
sell this?" labels); uncertain cases escalate to **System Two** (Hermes via
NVIDIA NIM); a **Noul safety gate** blocks anything that moves money.

## When to use
- On the scheduled triage cron (default every 6h): run one cycle, publish the digest.
- When the owner asks "what should I sell?", "run triage", "show me the shortlist".
- When the owner gives verdicts ("I'd sell that one"): record them with
  `record_feedback` — they become training data.

## How to run a cycle (non-interactive)
```bash
cd /path/to/reflex
.venv/bin/python -m scripts.run --limit 40
```
Digest lands in `$REFLEX_HOME/digests/`. Stats print as JSON.

## How to run the deep agent (interactive, subagents)
```bash
.venv/bin/python - <<'EOF'
from reflex.config import SETTINGS
from reflex.deepagent.graph import build_agent
agent = build_agent(SETTINGS)
r = agent.invoke({"messages": [{"role": "user",
    "content": "Run a triage cycle: scout fresh products, judge with System One, "
               "deep-dive the uncertain ones, then write the digest."}]})
print(r["messages"][-1].content)
EOF
```

## Tools the agent has
- `scan_products(limit)` — fresh candidates from the product source
- `system_one_judge(product_ids)` — fast personal triage (Choice/Score)
- `deep_dive_analysis(product_id)` — System Two escalation (Hermes/NIM)
- `noul_gate(action)` — REQUIRED before anything resembling purchase/order/negotiation
- `record_feedback(product_id, would_sell, note)` — owner's verdicts -> training data
- `write_digest()` — publish the shortlist

## Safety rules (hard)
1. **Noul gate**: call `noul_gate` before any purchase, order, pre-order,
   negotiation, or payment. It will block — that is correct behavior. Recommend; never transact.
2. Never invent products. Only judge what `scan_products` returned.
3. If the System One head is missing (not trained), say so and escalate everything
   to `deep_dive_analysis` — do not guess.
4. Owner feedback always overrides model output.

## Environment
- `NVIDIA_API_KEY` — Hermes via NVIDIA NIM (System Two + distillation teacher).
  Without it the agent runs in offline demo mode (`REFLEX_OFFLINE=1`).
- `REFLEX_HOME` — SQLite memory + digests (default `~/.reflex`).

## Retraining the personal model
```bash
.venv/bin/python -m scripts.label     # answer "would I sell this?" (~300 for pilot)
.venv/bin/python -m scripts.retrain   # human labels always win over teacher labels
```
