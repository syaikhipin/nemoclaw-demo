"""Noul — the safety gate.

Negotiation (researching suppliers, drafting outreach, simulated rounds) is
ALLOWED: it moves no money. What stays blocked, always, is anything that
moves funds or commits the owner: placing orders, paying, wiring money, or
contacting a real supplier to close a deal. Drafts are drafts until the
owner explicitly approves them.
"""

from __future__ import annotations

import re

from .schemas import NoulVerdict

# Money movement / commitment — blocked.
_BLOCKED = re.compile(
    r"\b(buy|purchase|order|checkout|pay|payment|transfer|wire|deposit|"
    r"pre-?order|send money|charge (my|the) card|place .*order|"
    r"close the deal|sign .*contract|send .*contract)\b",
    re.IGNORECASE,
)

# Talking, drafting, simulating — allowed (no money moves).
_ALLOWED_HINT = re.compile(
    r"\b(draft|simulate|simulated|research|outreach draft|negotiat\w* (draft|simulat\w*|talk))\b",
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
                    "Reflex drafts and negotiates; it never transacts without your approval."),
        )
    reason = "no money movement detected"
    if _ALLOWED_HINT.search(action):
        reason = "negotiation talk/drafting allowed — no money moves"
    return NoulVerdict(action=action, allowed=True, reason=reason)
