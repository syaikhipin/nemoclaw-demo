from .base import ProductSource
from .catalog import MockCatalog

try:
    from .amazon_fashion import AmazonFashionSource
except ImportError:  # pragma: no cover
    AmazonFashionSource = None  # type: ignore[assignment]

__all__ = ["ProductSource", "MockCatalog", "AmazonFashionSource", "default_source"]


def default_source() -> ProductSource:
    """Prefer the real Amazon fashion dataset; fall back to the mock catalog."""
    if AmazonFashionSource is not None:
        try:
            src = AmazonFashionSource()
            if len(src) > 0:
                return src
        except Exception:
            pass
    return MockCatalog()
