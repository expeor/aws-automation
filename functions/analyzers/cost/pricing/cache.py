"""Backwards-compat shim. Use core.shared.aws.pricing.cache instead."""

from __future__ import annotations

from core.shared.aws.pricing.cache import (  # noqa: F401
    DEFAULT_TTL_DAYS,
    FILE_LOCK_TIMEOUT,
    PriceCache,
    clear_cache,
    get_cache_info,
)
