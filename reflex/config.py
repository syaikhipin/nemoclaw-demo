"""Environment-driven configuration. Everything tunable lives here, not in code."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _home() -> Path:
    return Path(os.environ.get("REFLEX_HOME", "~/.reflex")).expanduser()


@dataclass(frozen=True)
class Settings:
    home: Path = field(default_factory=_home)
    offline: bool = os.environ.get("REFLEX_OFFLINE", "0") == "1"
    nvidia_api_key: str = os.environ.get("NVIDIA_API_KEY", "")
    nim_model: str = os.environ.get("NIM_MODEL", "nousresearch/hermes-3-llama-3.1-70b")
    nim_base_url: str = os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    # OpenAI-compatible LLM — primary provider. Point at ANY OpenAI-compatible
    # endpoint (custom proxy, local server, another vendor); legacy GLM_* vars
    # are still honored as a fallback so old setups keep working.
    openai_api_key: str = os.environ.get("OPENAI_API_KEY") or os.environ.get("GLM_API_KEY", "")
    openai_base_url: str = os.environ.get("OPENAI_BASE_URL") or os.environ.get("GLM_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = os.environ.get("OPENAI_MODEL") or os.environ.get("GLM_MODEL", "gpt-4o-mini")
    # Exa (web search) — supplier discovery for negotiation.
    exa_api_key: str = os.environ.get("EXA_API_KEY", "")
    searxng_url: str = os.environ.get("SEARXNG_URL", "")
    shortlist_at: float = float(os.environ.get("REFLEX_SHORTLIST_AT", "0.65"))
    pass_below: float = float(os.environ.get("REFLEX_PASS_BELOW", "0.35"))
    scan_limit: int = int(os.environ.get("REFLEX_SCAN_LIMIT", "40"))
    model_path: Path = field(init=False)
    db_path: Path = field(init=False)
    digest_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "home", Path(self.home).expanduser())
        object.__setattr__(self, "model_path", self.home / "system_one_head.joblib")
        object.__setattr__(self, "db_path", self.home / "memory.db")
        object.__setattr__(self, "digest_dir", self.home / "digests")

    def ensure_dirs(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        self.digest_dir.mkdir(parents=True, exist_ok=True)

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key) and not self.offline

    @property
    def has_nim(self) -> bool:
        return bool(self.nvidia_api_key) and not self.offline

    @property
    def llm_provider(self) -> str:
        """Provider priority: OpenAI-compatible endpoint first, NVIDIA NIM later, offline last."""
        if self.has_openai:
            return f"openai:{self.openai_model}"
        if self.has_nim:
            return f"nim:{self.nim_model}"
        return "offline"


SETTINGS = Settings()
