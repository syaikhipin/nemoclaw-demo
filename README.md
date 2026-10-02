# ⚡ Reflex — the agent that finds your one winning product

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/syaikhipin/nemoclaw-demo)
&nbsp;·&nbsp; 🌐 **[Live site with animated demo →](https://syaikhipin.github.io/nemoclaw-demo/)**

**It watches what you search for, hunts the price gap between local sourcing and EU prices, and negotiates the deal.**

> *The same leather tote costs $12 to source locally and sells for €45 in the EU. That gap is a business — if you can find it before everyone else does. Reflex finds it, checks the math, and works the deal.*

Built for the **NVIDIA Claw Agent Challenge** (Barcelona).

---

## The idea, in plain words

Cross-border arbitrage is simple: **buy where it's cheap, sell where it's expensive.** The hard part was never the idea — it's the search. Thousands of products, shifting prices, suppliers to vet, deals to negotiate. One person can't watch it all.

So instead of asking you to triage 2,000 products, Reflex flips the job around:

1. **It starts from your top searches.** What you keep looking up is your edge — the niche you actually understand. The agent hunts there, not in generic "trending products" lists.
2. **It scans for the gap.** For products in your space, it compares local sourcing cost against EU retail price and does the margin math.
3. **It picks the one.** Not a list of fifty maybes — the single best risk-adjusted opportunity.
4. **It works the deal.** Finds suppliers, drafts first outreach, and rehearses the negotiation against a simulated supplier — so you walk into the real conversation knowing your numbers.
5. **It never spends your money.** Research, drafts, and simulated deals are all fair game; moving real money needs your explicit approval. *Reflex recommends; it never transacts.*

---

## The novelty: your deal criteria, distilled

This is the heart of the entry, and it's easiest to understand through the human brain.

### Two speeds of thinking

Psychologist Daniel Kahneman showed humans think in two systems: **System 1** — fast, instinctive, the gut feeling of an expert who has "seen this a thousand times" — and **System 2** — slow, deliberate, the careful analysis you do before committing money.

Reflex works the same way:

| | System One 🟢 | System Two 🔵 |
|---|---|---|
| **What** | Your distilled deal instinct | A large AI analyst (GLM / Hermes) |
| **Speed** | ~16 milliseconds | ~10–60 seconds |
| **Cost** | Free, runs on your laptop | Paid API call |
| **Handles** | Screening thousands of candidates | Verifying the one opportunity |

The fast gut screens every candidate gap. Only the winner gets escalated to the expensive brain for verification. That's how you watch a whole market without a whole-market AI bill.

### "Distilled" — what does that actually mean?

Think of it like making an espresso from a pot of coffee: you keep all the flavor, lose the volume.

1. **You teach.** You answer one simple question — *"would I work this deal?"* — a few hundred times. That's the entire training program.
2. **A big AI assists** (the "teacher"). Before you've labeled enough, a large model drafts preliminary judgments so the system works on day one.
3. **Your labels always win.** Wherever you and the teacher disagree, your verdict overrides. This is the crucial part: **the final model is a compressed copy of your judgment, not a smaller copy of the teacher.** Your margin floor, your risk appetite, the categories you trust — distilled into a model no bigger than a photo.
4. **The result is tiny and fast.** It runs on a laptop CPU and judges a candidate in ~16ms — about as fast as you blinking.

### Why nobody else has this

Price trackers watch *everyone's* market. Review scores aggregate *strangers'* opinions. Reflex learns from **one person's deal history: yours**. Your competitor can buy the same AI subscription — they cannot download your taste in deals. In our literature review we found no published personal, on-device decision model trained on a single user's decision history. That's the gap this entry fills.

### Decisions you can audit

Every verdict comes back **typed**, not as a rambling paragraph:

- **Choice:** `shortlist` · `pass` · `research` (needs a closer look)
- **Score:** a calibrated probability — "P(you'd work this deal) = 0.94"
- **Rationale:** which signals mattered most (margin gap, shipping time, competition…)

And the **Noul safety gate** sits in front of everything consequential: the agent can research, draft, and negotiate — but it can never move money or commit funds without you.

---

## Watch it work

Real run, real Amazon products (fashion dataset), live in the browser demo:

**1 · The hunt.** One click scans 24 fresh products, shortlists 22, and escalates 1 to System Two for a closer look. This is the fast gut doing in seconds what used to take an evening of scrolling.

![Triage cycle results](demo-shots/shot2-shortlist.png)

**2 · The pick.** Each candidate gets a calibrated score — P(you'd work this deal) — with a System One/System Two badge showing which brain made the call.

**3 · Working the deal.** For the winner, the agent searches the live web for suppliers — here it found the brand's own storefront — and drafts first-contact outreach. Drafts are never sent automatically.

![Supplier search and outreach draft](demo-shots/shot4-draft.png)

**4 · The negotiation table.** The AI roleplays the supplier for multi-round negotiation. This session was real back-and-forth: supplier opened at $42.50/unit defending quality, your side anchored at $26.50 citing competing quotes, and they traded volume-for-price down to $38.25 vs $30.50. No deal — the gap was genuine, and the agent said so instead of inventing agreement. That's the rehearsal before you spend a cent.

![Simulated negotiation transcript](demo-shots/shot5-simulation.png)

**5 · Talk to the claw.** The deep agent (scout → judge → analyst subagents) takes plain-English instructions: *"scan 4 fresh products, judge them, find suppliers for your top pick and draft outreach."* It did — then noted, unprompted, that no money moved so no safety approval was needed.

---

## Try it yourself

**One click, no setup:** [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/syaikhipin/nemoclaw-demo) — the dashboard starts automatically in offline demo mode; add free `GLM_API_KEY` / `EXA_API_KEY` as Codespaces secrets and rebuild for the live version.

**Or locally:**

```bash
git clone https://github.com/syaikhipin/nemoclaw-demo.git && cd nemoclaw-demo
bash nemoclaw/scripts/onboard.sh     # creates venv, installs dependencies
bash nemoclaw/scripts/install.sh     # trains the demo head, runs the test suite

# web demo (the screenshots above)
GLM_API_KEY=your-key EXA_API_KEY=your-key \
  .venv/bin/python -m reflex.web.app --port 8765
# open http://localhost:8765
```

Keys are free: GLM at [z.ai](https://z.ai), Exa at [exa.ai](https://exa.ai). Without keys, everything still runs in offline demo mode (`REFLEX_OFFLINE=1`).

Make it *yours* — this is where the magic happens:

```bash
.venv/bin/python -m scripts.label      # "would I work this deal?" — 300 for the pilot
.venv/bin/python -m scripts.retrain    # your labels always beat the teacher's
```

Your deal criteria live in `labeling-config.yaml` (EU market, margin-gap rubric) — correct any line and it becomes v2.

---

## Under the hood (for the technical reader)

**Stack:** NemoClaw recipe layout · OpenClaw skill + cron · GLM (z.ai) primary, Hermes via NVIDIA NIM next · LangChain Deep Agents harness (`create_deep_agent`, scout/judge/analyst subagents, 6+ tools) · Exa for supplier search · SQLite memory.

**Verified numbers** (held-out set, n=100): accuracy **0.91**, calibration error **0.079**, **97%** of products decided with zero LLM calls, p99 latency **42ms**. Test suite: **7/7 green.**

**Repo layout:**

| Path | What |
|---|---|
| `reflex/system_one/` | The distilled head — `DecisionHead` protocol + calibrated reference model + teacher-distillation pipeline |
| `reflex/system_two/` | Slow analyst (GLM → Hermes/NIM → offline fallback) |
| `reflex/negotiation/` | Exa supplier search, GLM outreach drafts, simulated multi-round negotiation |
| `reflex/deepagent/` | Deep-agents harness: model selection, tools, subagent prompts |
| `reflex/serve/` | The long-running claw loop (scan → judge → escalate → digest) |
| `reflex/noul.py` | Safety gate: talk allowed, money movement blocked |
| `reflex/memory.py` | Durable SQLite memory: products, judgments, labels, negotiations, runs |
| `reflex/web/` | The browser demo dashboard |
| `skills/reflex-triage/` | OpenClaw/Hermes skill definition |
| `nemoclaw/scripts/` | `onboard` / `install` / `start` (OpenClaw cron for 24/7) |
| `scripts/` | `bootstrap`, `label`, `retrain`, `run`, `fetch_amazon_data` |
| `eval/` | Held-out evaluation: accuracy, calibration, abstention, latency |
| `docs/` | Labeling protocol · Qwen3-0.6B (CLM/NanoJev) upgrade path |

**Product data:** real Amazon fashion products (the dataset behind [qdrant-labs/demo-ecommerce-search](https://github.com/qdrant-labs/demo-ecommerce-search), 40k-slice via `scripts/fetch_amazon_data.py`). Titles, prices, ratings, images are real; sourcing cost and shipping days are deterministic documented estimates.

---

## Honest limits

- The demo head trains on a synthetic persona's labels; it becomes *personal* only after you label (~300 pilot, 1–3k for pro).
- Ingesting your actual search history to seed the hunting ground is the design target; the current demo personalizes through your labels.
- Sourcing costs in the demo are estimates, not supplier quotes — margin math is indicative until a real quote lands.
- Negotiations are simulated rehearsals; Noul blocks real transactions until you approve.
- The reference head is CPU-friendly by design (trains in seconds anywhere); the Qwen3-0.6B typed-head path (CLM primary, NanoJev baseline) is specified in `docs/clm-head.md` and swaps in via the `DecisionHead` protocol.

---

*Reflex recommends; it never transacts.* · License: Apache-2.0
