"""
plugins/cost/pricing/ecr.py - ECR 가격 조회

ECR 비용 계산:
- Storage: ~$0.10/GB/월 (리전별 상이)
- Data Transfer: 별도 청구

사용법:
    from plugins.cost.pricing import get_ecr_storage_price, get_ecr_monthly_cost

    # GB당 월 저장 비용
    per_gb = get_ecr_storage_price("ap-northeast-2")

    # 100GB 이미지 월간 비용
    monthly = get_ecr_monthly_cost("ap-northeast-2", storage_gb=100)
"""

import logging

from .cache import PriceCache
from .fetcher import PricingFetcher

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_cache = PriceCache()


def get_ecr_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """ECR 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {"storage_per_gb_monthly": float}
    """
    return _get_cached_prices(region, refresh)


def get_ecr_storage_price(region: str = "ap-northeast-2") -> float:
    """ECR Storage GB당 월 가격

    Args:
        region: AWS 리전

    Returns:
        GB당 월간 USD
    """
    prices = get_ecr_prices(region)
    return prices.get("storage_per_gb_monthly", 0.10)


def get_ecr_monthly_cost(
    region: str = "ap-northeast-2",
    storage_gb: float = 0.0,
) -> float:
    """ECR 월간 비용 계산

    Args:
        region: AWS 리전
        storage_gb: 저장된 이미지 크기 (GB)

    Returns:
        월간 USD 비용
    """
    per_gb = get_ecr_storage_price(region)
    return round(per_gb * storage_gb, 2)


def _get_cached_prices(region: str, refresh: bool = False) -> dict[str, float]:
    """캐시된 가격 조회 (없으면 API 호출)"""
    if not refresh:
        cached = _cache.get("ecr", region)
        if cached:
            return cached

    # API로 가격 조회
    try:
        fetcher = PricingFetcher()
        prices = fetcher.get_ecr_prices(region)

        if prices and prices.get("storage_per_gb_monthly", 0) > 0:
            _cache.set("ecr", region, prices)
            return prices

    except Exception as e:
        logger.warning(f"ECR 가격 조회 실패: {e}")

    # 기본값 반환
    return {"storage_per_gb_monthly": 0.10}
