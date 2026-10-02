"""Product source interface. Swap the mock catalog for a real feed without touching the agent."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas import Product


class ProductSource(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self, limit: int = 40) -> list[Product]:
        """Return up to `limit` candidate products."""
