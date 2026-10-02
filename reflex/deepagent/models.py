"""Chat-model selection for the deep agent.

Production: Hermes 3 via NVIDIA NIM (build.nvidia.com, OpenAI-compatible).
  Needs NVIDIA_API_KEY (free at build.nvidia.com).
Offline/demo: a scripted deterministic stand-in so the harness, tools and
  subagents can be exercised end-to-end with no network and no key.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from ..config import Settings


class ScriptedDemoModel(BaseChatModel):
    """Deterministic offline model: calls scan_products once, then summarizes.

    It proves the deep-agent graph, middleware and tool plumbing run
    end-to-end. It is not intelligent — production uses Hermes on NIM.
    """

    @property
    def _llm_type(self) -> str:
        return "reflex-scripted-demo"

    def bind_tools(self, tools, **kwargs):  # noqa: ANN001, ANN202
        """Scripted model ignores tool schemas — its call script is fixed."""
        return self

    def _generate(self, messages: list, stop: list[str] | None = None,
                  run_manager: Any = None, **kwargs: Any) -> ChatResult:
        tool_done = any(isinstance(m, ToolMessage) for m in messages)
        if tool_done:
            text = ("Demo cycle complete. I scanned fresh products with scan_products. "
                    "With Hermes on NVIDIA NIM I would now run system_one_judge on them, "
                    "escalate the uncertain ones with deep_dive_analysis, enforce the "
                    "Noul gate, and publish the digest with write_digest.")
            msg = AIMessage(content=text)
        else:
            msg = AIMessage(
                content="",
                tool_calls=[{"name": "scan_products", "args": {"limit": 5},
                             "id": "call_scan_1", "type": "tool_call"}],
            )
        return ChatResult(generations=[ChatGeneration(message=msg)])


def get_chat_model(settings: Settings | None = None) -> BaseChatModel:
    from ..config import SETTINGS
    settings = settings or SETTINGS
    if settings.has_nim:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.nim_model,
            base_url=settings.nim_base_url,
            api_key=settings.nvidia_api_key,
            temperature=0.2,
        )
    if settings.offline:
        return ScriptedDemoModel()
    raise RuntimeError(
        "No chat model configured. Set NVIDIA_API_KEY (Hermes via NVIDIA NIM) "
        "or REFLEX_OFFLINE=1 for the scripted demo model."
    )
