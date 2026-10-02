"""LLM chat helpers over the provider chain: GLM (z.ai) -> NVIDIA NIM -> offline.

Keys come from the environment only (GLM_API_KEY / NVIDIA_API_KEY) and are
never written anywhere. Used by negotiation and anywhere else the agent needs
free-form model text (not just the System Two analyst).

In offline mode (REFLEX_OFFLINE=1) chat() returns a deterministic scripted
stand-in labeled "offline" instead of raising — the whole demo, including
drafts and simulated negotiations, runs with no keys.
"""

from __future__ import annotations

import json
import re
import urllib.request

from .config import Settings


def _grab(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else None


_NUM = r"(\d+(?:\.\d+)?)"


def _offline_draft(user: str) -> str:
    supplier = _grab(user, r"Supplier:\s*(.+?)\s*\(") or "Supplier"
    product = _grab(user, r"Product I want to source:\s*(.+?)\s*\(") or "your product"
    price = _grab(user, r"retailing ~\$" + _NUM) or "?"
    return (
        f"Subject: Wholesale inquiry \u2014 {product}\n\n"
        f"Hello {supplier} team,\n\n"
        f"I'm sourcing '{product}' for my EU store (retails ~${price}). "
        f"Could you share your wholesale pricing tiers, MOQ, lead times, "
        f"and whether you offer blind dropshipping?\n\n"
        f"Happy to start with a trial order if the numbers work.\n\n"
        f"Best regards,\n[Your Name] \u2014 [Store]"
    )


def _offline_supplier_turn(user: str) -> str:
    walk = float(_grab(user, r"walk-away unit price is \$" + _NUM) or 30)
    n_buyer = user.count("buyer:")
    offer = max(round(walk * (1.18 - 0.05 * n_buyer), 2), walk)
    deal = n_buyer >= 2
    msg = (f"Thanks for the inquiry. At 200 units I can do ${offer:.2f}/unit \u2014 "
           f"that's close to my floor for this spec. "
           f"Commit to 500 units and I can sharpen the pencil a little more.")
    return json.dumps({"message": msg,
                       "offer_unit_price": offer,
                       "offer_moq": 500 if deal else 200,
                       "deal": deal})


def _offline_buyer_turn(user: str) -> str:
    target = _grab(user, r"target unit price: \$" + _NUM) or "?"
    product = _grab(user, r"Negotiating '([^']+)'") or "this product"
    return (f"Thanks \u2014 I need to land near ${target}/unit to make the EU retail "
            f"work on '{product}'. Meet me close to ${target} and I can commit "
            f"to 500 units with a 30% deposit. What can you do?")


def _offline_chat(messages: list[dict]) -> str:
    system = " ".join(m.get("content", "") for m in messages if m.get("role") == "system")
    user = " ".join(m.get("content", "") for m in messages if m.get("role") == "user")
    if "roleplaying a wholesale supplier" in system:
        return _offline_supplier_turn(user)
    if "buyer-side negotiator" in system:
        if "first-contact outreach" in user:
            return _offline_draft(user)
        return _offline_buyer_turn(user)
    return ("[offline stand-in] No LLM provider configured (REFLEX_OFFLINE=1). "
            "Set GLM_API_KEY or NVIDIA_API_KEY for live responses.")


def _providers(settings: Settings):
    if settings.offline:
        return
    if settings.glm_api_key:
        yield ("glm", settings.glm_base_url, settings.glm_api_key, settings.glm_model)
    if settings.nvidia_api_key:
        yield ("nim", settings.nim_base_url, settings.nvidia_api_key, settings.nim_model)


def chat(messages: list[dict], settings: Settings | None = None,
         temperature: float = 0.3, max_tokens: int = 4096) -> tuple[str, str]:
    """Return (provider_label, text). Raises RuntimeError if no provider works."""
    from .config import SETTINGS
    settings = settings or SETTINGS
    if settings.offline:
        return "offline", _offline_chat(messages)
    errors = []
    for label, base_url, api_key, model in _providers(settings):
        try:
            payload = {"model": model, "messages": messages,
                       "temperature": temperature, "max_tokens": max_tokens}
            req = urllib.request.Request(
                base_url.rstrip("/") + "/chat/completions",
                data=json.dumps(payload).encode(),
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.load(resp)
            msg = body["choices"][0]["message"]
            text = (msg.get("content") or "").strip()
            if not text and msg.get("reasoning_content"):
                text = msg["reasoning_content"].strip()
            if text:
                return label, text
            errors.append(f"{label}: empty response")
        except Exception as exc:
            errors.append(f"{label}: {exc}")
    raise RuntimeError("no LLM provider available (" + "; ".join(errors) + ")")


def chat_json(messages: list[dict], settings: Settings | None = None,
              temperature: float = 0.2) -> tuple[str, dict]:
    """chat() + parse the first {...} JSON object out of the reply."""
    label, text = chat(messages, settings, temperature)
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`").strip()
        if t.startswith("json"):
            t = t[4:].strip()
    data = json.loads(t[t.index("{"): t.rindex("}") + 1])
    return label, data
