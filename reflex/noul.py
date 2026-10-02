"""Noul — the safety gate. Blocks money movement, always.

Any action that would move money, place an order, or commit the user to a
seller is denied by default. The agent may *recommend*; it may never *transact*.
The gate sits in front of the tool layer so neither System One, System Two,
nor a subagent can route around it.
"""

from __future__ import annotations

import re

from .schemas import NoulVerdict

_BLOCKED = re.compile(
    r"\b(buy|purchase|order|checkout|pay|payment|transfer|wire|deposit|"
    r"pre-?order|bulk (buy|order|deal)|negotiat\w* (price|deal|bulk)|"
    r"send money|charge (my|the) card|place .*order)\b",
    re.IGNORECASE,
)


def check(action: str) -> NoulVerdict:
    """Return allowed=False for anything that moves money or commits funds."""
    action = action.strip()
    if not action:
        return NoulVerdict(action=action, allowed=False, reason="empty action")
    if _BLOCKED.search(action):
        return NoulVerdict(
            action=action, allowed=False,
            reason=("Noul safety gate: this action would move money or commit funds. "
                    "Reflex recommends; it never transacts. Negotiation module is phase 2."),
        )
    return NoulVerdict(action=action, allowed=True, reason="no money movement detected")
