"""Chat-model selection for the deep agent.

Provider priority: GLM on z.ai first, Hermes via NVIDIA NIM second,
scripted offline stand-in last (REFLEX_OFFLINE=1).
"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from ..config import Settings

# This machine's NO_PROXY/no_proxy contain bracketed IPv6 literals ([::1], …)
# which crash httpx's proxy parsing ("Invalid port: ':1]'"). Strip the
# bracketed entries — localhost/127.0.0.1/::1 remain covered unbracketed.
for _var in ("NO_PROXY", "no_proxy"):
    _val = os.environ.get(_var, "")
    if "[" in _val:
        os.environ[_var] = ",".join(p for p in _val.split(",") if "[" not in p)


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
    if settings.offline:
        return ScriptedDemoModel()
    if settings.glm_api_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.glm_model,
            base_url=settings.glm_base_url,
            api_key=settings.glm_api_key,
            temperature=0.2,
            max_tokens=2000,
        )
    if settings.nvidia_api_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.nim_model,
            base_url=settings.nim_base_url,
            api_key=settings.nvidia_api_key,
            temperature=0.2,
        )
    raise RuntimeError(
        "No chat model configured. Set GLM_API_KEY (z.ai) or NVIDIA_API_KEY "
        "(Hermes via NVIDIA NIM), or REFLEX_OFFLINE=1 for the scripted demo model."
    )
