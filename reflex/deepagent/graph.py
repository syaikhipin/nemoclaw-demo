"""Assemble the Reflex deep agent: harness + model + tools + subagents.

This is the LangChain Deep Agents leg of the stack:
  create_deep_agent(model=Hermes-on-NIM, tools=[...], subagents=[scout, judge, analyst])

The same agent also runs inside the NemoClaw sandbox via the OpenClaw/Hermes
skill in skills/reflex-triage — the harness here is what gives it planning,
subagent delegation, a filesystem, skills and memory out of the box.
"""

from __future__ import annotations

from deepagents import SubAgent, create_deep_agent

from ..config import Settings
from .models import get_chat_model
from .prompts import ANALYST_PROMPT, JUDGE_PROMPT, SCOUT_PROMPT, SYSTEM_PROMPT
from .tools import make_tools


def build_agent(settings: Settings | None = None):
    from ..config import SETTINGS
    settings = settings or SETTINGS
    subagents = [
        SubAgent(name="scout", description="Discover fresh candidate products",
                 prompt=SCOUT_PROMPT),
        SubAgent(name="judge", description="Fast System One triage of products",
                 prompt=JUDGE_PROMPT),
        SubAgent(name="analyst",
                 description="Slow System Two deep dives on uncertain products",
                 prompt=ANALYST_PROMPT),
    ]
    return create_deep_agent(
        model=get_chat_model(settings),
        tools=make_tools(settings),
        subagents=subagents,
        system_prompt=SYSTEM_PROMPT,
        name="reflex",
    )
