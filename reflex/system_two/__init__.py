"""System Two — the slow, deliberative analyst.

In production this is Hermes 3 served by NVIDIA NIM (build.nvidia.com,
OpenAI-compatible endpoint, free key). Uncertain System One judgments
(choice == "research") escalate here for a deep dive.

Offline (REFLEX_OFFLINE=1 or no key) it degrades to a transparent heuristic
analyst so the whole pipeline still runs end-to-end. Offline verdicts are
always marked offline=True and decided_by="system_two".
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings
from ..schemas import Product


@dataclass
class Analysis:
    product_id: str
    score: float          # 0..1 sellability
    verdict: str          # "list" | "skip" | "needs_research"
    summary: str
    risks: list[str]
    offline: bool = False

    def to_dict(self) -> dict:
        return {"product_id": self.product_id, "score": self.score,
                "verdict": self.verdict, "summary": self.summary,
                "risks": self.risks, "offline": self.offline}


_SELLING_CRITERIA = """You are the System Two analyst for Reflex, a product-triage agent for an
independent e-commerce seller. Score how sellable a dropshipping product is.

Hard rules (a product failing any of these should score below 0.4):
- Landed margin below 50% is weak; below 35% is a skip.
- Shipping over 12 days is a major risk unless EU/US warehouse stock exists.
- Rating below 4.0 or fewer than 50 reviews with rating below 4.3 is weak social proof.
- Prohibited: weapons, medical devices making health claims, replicas/counterfeits.

Reply in exactly this JSON shape: {"score": 0.0-1.0, "verdict": "list|skip|needs_research",
"summary": "one sentence", "risks": ["..."]}.
"""


class SystemTwoAnalyst:
    def __init__(self, settings: Settings | None = None):
        from ..config import SETTINGS
        self.settings = settings or SETTINGS

    def describe(self) -> str:
        return self.settings.llm_provider if self.settings.llm_provider != "offline" \
            else "offline-heuristic"

    def _providers(self):
        """Yield (label, base_url, api_key, model) in priority order: GLM, then NIM."""
        s = self.settings
        if s.offline:
            return
        if s.glm_api_key:
            yield ("glm", s.glm_base_url, s.glm_api_key, s.glm_model)
        if s.nvidia_api_key:
            yield ("nim", s.nim_base_url, s.nvidia_api_key, s.nim_model)

    def analyze(self, product: Product) -> Analysis:
        last_error = ""
        for label, base_url, api_key, model in self._providers():
            try:
                return self._chat_analyze(product, label, base_url, api_key, model)
            except Exception as exc:  # try next provider, never break the pipeline
                last_error = f"{label}_error: {exc}"
        return self._offline_analyze(product, note=last_error)

    # -- OpenAI-compatible chat providers (GLM on z.ai, Hermes on NVIDIA NIM) --
    def _chat_analyze(self, product: Product, label: str,
                      base_url: str, api_key: str, model: str) -> Analysis:
        import json
        import urllib.request

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _SELLING_CRITERIA},
                {"role": "user", "content": (
                    f"Title: {product.title}\nCategory: {product.category}\n"
                    f"Price: ${product.price_usd:.2f} | Cost: ${product.cost_usd:.2f} "
                    f"| Margin: {product.margin:.0%}\n"
                    f"Rating: {product.rating}/5 from {product.reviews} reviews | "
                    f"Shipping: {product.shipping_days} days\n"
                    f"Supplier: {product.supplier}\nDescription: {product.description}")},
            ],
            "temperature": 0.2,
            # reasoning models spend tokens thinking — budget generously
            "max_tokens": 4096,
        }
        req = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.load(resp)
        message = body["choices"][0]["message"]
        text = message.get("content") or ""
        if "{" not in text and message.get("reasoning_content"):
            # last resort: the verdict sometimes lands in the thinking trace
            text = message["reasoning_content"]
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text[text.index("{"): text.rindex("}") + 1])
        return Analysis(product_id=product.id, score=float(data["score"]),
                        verdict=data["verdict"], summary=data["summary"],
                        risks=list(data.get("risks", [])), offline=False)

    # -- Offline fallback -----------------------------------------------------
    def _offline_analyze(self, product: Product, note: str = "") -> Analysis:
        score = 0.5
        risks: list[str] = []
        if product.margin >= 0.6:
            score += 0.2
        elif product.margin < 0.35:
            score -= 0.25
            risks.append(f"thin margin {product.margin:.0%}")
        if product.shipping_days <= 9:
            score += 0.1
        elif product.shipping_days > 12:
            score -= 0.2
            risks.append(f"slow shipping ({product.shipping_days}d)")
        if product.rating >= 4.4 and product.reviews >= 1000:
            score += 0.15
        elif product.rating < 4.0:
            score -= 0.15
            risks.append(f"weak rating {product.rating}/5")
        score = max(0.0, min(1.0, score))
        verdict = "list" if score >= 0.65 else ("skip" if score <= 0.4 else "needs_research")
        summary = (f"Offline heuristic: margin {product.margin:.0%}, "
                   f"{product.rating}/5 ({product.reviews} reviews), {product.shipping_days}d shipping. "
                   + note).strip()
        return Analysis(product_id=product.id, score=round(score, 3), verdict=verdict,
                        summary=summary, risks=risks, offline=True)
