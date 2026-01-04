"""
plugins/cost/pricing/snapshot.py - EBS Snapshot 가격 조회

EBS Snapshot 비용 계산:
- Storage: ~$0.05/GB/월 (리전별 상이)

사용법:
    from plugins.cost.pricing import get_snapshot_price, get_snapshot_monthly_cost

    # GB당 월 가격
    per_gb = get_snapshot_price("ap-northeast-2")

    # 100GB 스냅샷 월간 비용
    monthly = get_snapshot_monthly_cost("ap-northeast-2", size_gb=100)
"""

import logging

from .cache import PriceCache
from .fetcher import PricingFetcher

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_cache = PriceCache()


def get_snapshot_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """EBS Snapshot 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {"storage_per_gb_monthly": float}
    """
    return _get_cached_prices(region, refresh)


def get_snapshot_price(region: str = "ap-northeast-2") -> float:
    """EBS Snapshot GB당 월 가격

    Args:
        region: AWS 리전

    Returns:
        GB당 월간 USD
    """
    prices = get_snapshot_prices(region)
    return prices.get("storage_per_gb_monthly", 0.05)


def get_snapshot_monthly_cost(
    region: str = "ap-northeast-2",
    size_gb: float = 0.0,
) -> float:
    """EBS Snapshot 월간 비용 계산

    Args:
        region: AWS 리전
        size_gb: 스냅샷 크기 (GB)

    Returns:
        월간 USD 비용
    """
    per_gb = get_snapshot_price(region)
    return round(per_gb * size_gb, 2)


def _get_cached_prices(region: str, refresh: bool = False) -> dict[str, float]:
    """캐시된 가격 조회 (없으면 API 호출)"""
    if not refresh:
        cached = _cache.get("snapshot", region)
        if cached:
            return cached

    # API로 가격 조회
    try:
        fetcher = PricingFetcher()
        prices = fetcher.get_snapshot_prices(region)

        if prices and prices.get("storage_per_gb_monthly", 0) > 0:
            _cache.set("snapshot", region, prices)
            return prices

    except Exception as e:
        logger.warning(f"EBS Snapshot 가격 조회 실패: {e}")

    # 기본값 반환
    return {"storage_per_gb_monthly": 0.05}
