# Reflex

**A long-running claw agent that triages dropshipping products with a personal
System One decision model — your taste, distilled, running 24/7.**

One sentence: *Reflex learns which products **you** would sell from your own
past decisions, then scans product feeds around the clock and hands you a
shortlist — so you vet 20 winners instead of drowning in 2,000 listings.*

Built for the **NVIDIA Claw Agent Challenge** (Barcelona) on the official stack:
**NemoClaw** quickstart layout · **OpenClaw** skill + cron · **Hermes** via NVIDIA NIM ·
**LangChain Deep Agents** harness.

## How it works

```
                    ┌─────────────────────────────────────────┐
  product feeds ──▶ │  SCOUT subagent: scan_products          │  Deep Agents
                    │        │                                │  harness
                    │        ▼                                │  (planning,
                    │  JUDGE: System One head ──▶ shortlist ──┤   subagents,
                    │    (personal, <50ms, free)      │       │   tools, memory)
                    │        │ research (uncertain)   │ pass  │
                    │        ▼                       │       │
                    │  ANALYST subagent: System Two ──┘       │
                    │    (Hermes 3 on NVIDIA NIM)             │
                    │        │                                │
                    │        ▼                                │
                    │  NOUL gate: blocks money movement  ✋    │
                    └─────────────────────────────────────────┘
                                   │ digest every 6h
                                   ▼
                          owner vets the shortlist,
                    feedback ──▶ becomes training data ──▶ head retrains
```

**The core idea:** dual-process triage. System One — a small model distilled
from *your* "would I sell this?" labels — decides ~97% of products in
milliseconds for free. Only the uncertain ~3% escalate to System Two (Hermes 3
via NVIDIA's free NIM endpoint). It's the FrugalGPT-cascade insight, but the
cheap tier is *personal*: no generic model knows your taste.

**Typed decisions** (Choice / Score / Noul), à la the Jev ecosystem: every
judgment carries `choice` (shortlist/pass/research), a calibrated `score`, and
passes the Noul safety gate — the agent recommends, it never transacts.

## Verified on this machine

```
$ .venv/bin/python -m scripts.bootstrap
[bootstrap] trained on 300 labels (train acc 0.997)
[bootstrap] held-out eval (n=100):
  accuracy: 0.91 | ece: 0.079 | abstention_rate_research: 0.03
  decided_without_llm: 0.97 | mean_latency_ms: 16.0 | p99_latency_ms: 42.4
$ .venv/bin/python -m pytest tests/ -q
7 passed
```

(Seed labels are a documented synthetic persona — a stand-in so the repo runs
offline. The model becomes personal when trained on the owner's labels.)

## Quickstart

```bash
git clone <this-repo> && cd reflex
bash nemoclaw/scripts/onboard.sh    # venv + deps + .env
bash nemoclaw/scripts/install.sh    # trains demo head, runs tests
.venv/bin/python -m scripts.run --limit 40      # one triage cycle
.venv/bin/python -m scripts.run --forever --interval-hours 6  # the claw, 24/7
```

With an LLM key in `.env`, System Two and the deep agent use it; without one,
everything runs offline.

| Provider | Env | Model |
|---|---|---|
| **GLM (z.ai)** — primary for now | `GLM_API_KEY` | `glm-5.3-flash` (`GLM_MODEL`, `GLM_BASE_URL`) |
| **NVIDIA NIM** — later | `NVIDIA_API_KEY` | `nousresearch/hermes-3-llama-3.1-70b` |
| Offline demo | `REFLEX_OFFLINE=1` | scripted stand-in (no network, no key) |

## Web demo

```bash
GLM_API_KEY=... .venv/bin/python -m reflex.web.app --port 8765
# open http://localhost:8765
```

The dashboard runs live triage cycles, shows the shortlist with P(sell) bars and
System One / System Two badges, lets you test the Noul gate, chat with the deep
agent (scout → judge → analyst subagents, powered by GLM), read the latest
digest, and see the held-out eval metrics.

Make it yours:
```bash
.venv/bin/python -m scripts.label    # "would I sell this?" — 300 for the pilot
.venv/bin/python -m scripts.retrain  # your labels always beat teacher labels
```

## Layout

| Path | What |
|---|---|
| `reflex/system_one/` | Personal decision head (Protocol + sklearn reference + distillation) |
| `reflex/system_two/` | Hermes-via-NIM analyst, offline fallback |
| `reflex/deepagent/` | `create_deep_agent` wiring: model, 6 tools, scout/judge/analyst subagents |
| `reflex/serve/` | Long-running claw loop (scan→judge→escalate→digest) |
| `reflex/noul.py` | Safety gate: blocks money movement, always |
| `reflex/memory.py` | SQLite memory: products, judgments, labels, runs |
| `skills/reflex-triage/` | OpenClaw/Hermes skill (NemoClaw recipe style) |
| `nemoclaw/scripts/` | onboard / install / start (OpenClaw cron) |
| `scripts/` | bootstrap, label, retrain, run |
| `eval/` | held-out eval: accuracy, calibration, abstention, latency |
| `docs/` | labeling protocol, Qwen3-0.6B (CLM/NanoJev) upgrade path |

## Why this wins

1. **It actually runs** — end-to-end pipeline, long-running loop, tools, durable
   memory, 7/7 tests green, real eval numbers, not a one-shot prompt.
2. **It's novel** — nobody has published a *personal* on-device System One model
   trained on one user's decision history; the literature review confirmed the gap.
   Personal taste as a distilled decision layer is the moat.
3. **It's useful** — independent sellers drown in feeds; a triage layer that learns
   *your* criteria and cuts vetting from thousands of listings to a daily shortlist
   is something a person acts on every morning.

## Honest limits
- Seed data is synthetic; swap in real labels + a real `ProductSource` before judging.
- The reference head is sklearn-on-CPU by design (trains in seconds anywhere);
  the Qwen3-0.6B typed head path (CLM primary, NanoJev baseline) is specified in
  `docs/clm-head.md` and swaps in via the `DecisionHead` protocol.
- Negotiation / ordering is phase 2 — Noul blocks it today.

License: Apache-2.0
