"""LLM chat helpers over the provider chain: GLM (z.ai) -> NVIDIA NIM -> error.

Keys come from the environment only (GLM_API_KEY / NVIDIA_API_KEY) and are
never written anywhere. Used by negotiation and anywhere else the agent needs
free-form model text (not just the System Two analyst).
"""

from __future__ import annotations

import json
import urllib.request

from .config import Settings


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
