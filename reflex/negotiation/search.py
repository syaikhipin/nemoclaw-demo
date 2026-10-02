"""Supplier web search: Exa API first, local SearXNG as fallback.

Keys/URLs come from the environment only (EXA_API_KEY / SEARXNG_URL).
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from ..config import Settings


def search_suppliers(query: str, n: int = 5,
                     settings: Settings | None = None) -> tuple[str, list[dict]]:
    """Return (provider, [{title, url, snippet}]). Provider is exa|searxng|none."""
    from ..config import SETTINGS
    settings = settings or SETTINGS
    if settings.offline:
        return "none", []
    if settings.exa_api_key:
        try:
            return "exa", _exa(query, n, settings.exa_api_key)
        except Exception:
            pass
    if settings.searxng_url:
        try:
            return "searxng", _searxng(query, n, settings.searxng_url)
        except Exception:
            pass
    return "none", []


def _exa(query: str, n: int, api_key: str) -> list[dict]:
    payload = {"query": query, "numResults": n, "type": "auto"}
    req = urllib.request.Request(
        "https://api.exa.ai/search", data=json.dumps(payload).encode(),
        headers={"x-api-key": api_key, "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        body = json.load(r)
    return [{"title": (res.get("title") or "")[:120],
             "url": res.get("url") or "",
             "snippet": (res.get("text") or res.get("snippet") or "")[:400]}
            for res in body.get("results", [])]


def _searxng(query: str, n: int, base_url: str) -> list[dict]:
    qs = urllib.parse.urlencode({"q": query, "format": "json"})
    req = urllib.request.Request(base_url.rstrip("/") + "/search?" + qs,
                                 headers={"User-Agent": "reflex-demo/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    out = []
    for res in body.get("results", [])[:n]:
        out.append({"title": (res.get("title") or "")[:120],
                    "url": res.get("url") or "",
                    "snippet": (res.get("content") or "")[:400]})
    return out
