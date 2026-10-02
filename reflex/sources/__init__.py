import os

from .arbitrage_v2 import ArbitrageSource
from .base import ProductSource
from .catalog import MockCatalog

try:
    from .amazon_fashion import AmazonFashionSource
except ImportError:  # pragma: no cover
    AmazonFashionSource = None  # type: ignore[assignment]

__all__ = ["ProductSource", "MockCatalog", "AmazonFashionSource",
           "ArbitrageSource", "default_source"]


def default_source() -> ProductSource:
    """v2 ID->EU arbitrage pairs by default (REFLEX_SOURCE=amazon|mock to override)."""
    want = os.environ.get("REFLEX_SOURCE", "v2").lower()
    if want == "amazon":
        return _amazon_or_mock()
    if want == "mock":
        return MockCatalog()
    # default: v2 arbitrage
    try:
        src = ArbitrageSource()
        if len(src) > 0:
            return src
    except Exception:
        pass
    return _amazon_or_mock()


def _amazon_or_mock() -> ProductSource:
    if AmazonFashionSource is not None:
        try:
            src = AmazonFashionSource()
            if len(src) > 0:
                return src
        except Exception:
            pass
    return MockCatalog()
