"""
core/pricing/ebs.py - EBS 가격 조회

EBS 볼륨 GB당 월간 비용을 조회합니다.

사용법:
    from core.pricing import get_ebs_price, get_ebs_monthly_cost

    # GB당 월 가격
    price_per_gb = get_ebs_price("gp3", "ap-northeast-2")

    # 100GB 볼륨 월간 비용
    monthly = get_ebs_monthly_cost("gp3", 100, "ap-northeast-2")
"""

import logging

from .cache import PriceCache
from .fetcher import PricingFetcher

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_cache = PriceCache()


def get_ebs_price(
    volume_type: str,
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> float:
    """EBS 볼륨 GB당 월 가격 조회

    Args:
        volume_type: 볼륨 타입 (gp2, gp3, io1, io2, st1, sc1, standard)
        region: AWS 리전 (기본: ap-northeast-2)
        refresh: 캐시 무시하고 새로 조회

    Returns:
        GB당 월 USD 가격 (조회 실패 시 0.0)
    """
    prices = _get_cached_prices(region, refresh)

    if volume_type in prices:
        return prices[volume_type]

    # 가격 정보 없음
    logger.debug(f"EBS 가격 정보 없음: {volume_type}/{region}")
    return 0.0


def get_ebs_monthly_cost(
    volume_type: str,
    size_gb: int,
    region: str = "ap-northeast-2",
) -> float:
    """EBS 볼륨 월간 비용 계산

    Args:
        volume_type: 볼륨 타입
        size_gb: 볼륨 크기 (GB)
        region: AWS 리전

    Returns:
        월간 USD 비용
    """
    price_per_gb = get_ebs_price(volume_type, region)
    return round(price_per_gb * size_gb, 2)


def get_ebs_prices_bulk(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """리전의 모든 EBS 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {volume_type: gb_monthly_price} 딕셔너리
    """
    return _get_cached_prices(region, refresh)


def _get_cached_prices(region: str, refresh: bool = False) -> dict[str, float]:
    """캐시된 가격 조회 (없으면 API 호출)"""
    if not refresh:
        cached = _cache.get("ebs", region)
        if cached:
            return cached

    # API로 가격 조회
    try:
        fetcher = PricingFetcher()
        prices = fetcher.get_ebs_prices(region)

        if prices:
            _cache.set("ebs", region, prices)
            return prices

    except Exception as e:
        logger.warning(f"EBS 가격 조회 실패: {e}")

    return {}
