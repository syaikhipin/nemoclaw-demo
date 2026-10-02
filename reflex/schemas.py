"""Core data schemas. Typed outputs are the contract between System One and the agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Choice = Literal["shortlist", "pass", "research"]
DecidedBy = Literal["system_one", "system_two", "human"]


@dataclass
class Product:
    id: str
    title: str
    category: str
    price_usd: float
    cost_usd: float
    supplier: str
    rating: float          # 0..5
    reviews: int
    shipping_days: int
    description: str
    url: str = ""
    source: str = "catalog"

    @property
    def margin(self) -> float:
        return (self.price_usd - self.cost_usd) / self.price_usd if self.price_usd > 0 else 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Product":
        return cls(**{f: d.get(f, "") for f in
                      ("id", "title", "category", "price_usd", "cost_usd", "supplier",
                       "rating", "reviews", "shipping_days", "description", "url", "source")})


@dataclass
class Judgment:
    """The typed decision emitted for one product."""
    product_id: str
    choice: Choice
    score: float                 # calibrated P("I would sell this")
    confidence: float            # |score - 0.5| * 2, 0..1
    rationale: str
    decided_by: DecidedBy
    model_version: str
    latency_ms: float = 0.0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NoulVerdict:
    """Safety-gate verdict. Noul blocks money movement, always."""
    action: str
    allowed: bool
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)
