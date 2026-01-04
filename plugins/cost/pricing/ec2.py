"""
core/pricing/ec2.py - EC2 가격 조회

EC2 인스턴스 시간당/월간 비용을 조회합니다.
캐시를 사용하여 API 호출을 최소화합니다.

사용법:
    from core.pricing import get_ec2_price, get_ec2_monthly_cost

    # 시간당 가격
    hourly = get_ec2_price("t3.medium", "ap-northeast-2")

    # 월간 비용 (시간당 * 730시간)
    monthly = get_ec2_monthly_cost("t3.medium", "ap-northeast-2")
"""

import logging

from .cache import PriceCache
from .fetcher import PricingFetcher

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_cache = PriceCache()

# 월간 시간 (평균)
HOURS_PER_MONTH = 730


def get_ec2_price(
    instance_type: str,
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> float:
    """EC2 인스턴스 시간당 가격 조회

    Args:
        instance_type: 인스턴스 타입 (예: "t3.medium")
        region: AWS 리전 (기본: ap-northeast-2)
        refresh: 캐시 무시하고 새로 조회

    Returns:
        시간당 USD 가격 (조회 실패 시 0.0)
    """
    prices = _get_cached_prices(region, refresh)

    if instance_type in prices:
        return prices[instance_type]

    # 가격 정보 없음
    logger.debug(f"가격 정보 없음: {instance_type}/{region}")
    return 0.0


def get_ec2_monthly_cost(
    instance_type: str,
    region: str = "ap-northeast-2",
    hours_per_month: int = HOURS_PER_MONTH,
) -> float:
    """EC2 인스턴스 월간 비용 계산

    Args:
        instance_type: 인스턴스 타입
        region: AWS 리전
        hours_per_month: 월간 운영 시간 (기본: 730)

    Returns:
        월간 USD 비용
    """
    hourly = get_ec2_price(instance_type, region)
    return round(hourly * hours_per_month, 2)


def get_ec2_prices_bulk(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """리전의 모든 EC2 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {instance_type: hourly_price} 딕셔너리
    """
    return _get_cached_prices(region, refresh)


def _get_cached_prices(region: str, refresh: bool = False) -> dict[str, float]:
    """캐시된 가격 조회 (없으면 API 호출)"""
    if not refresh:
        cached = _cache.get("ec2", region)
        if cached:
            return cached

    # API로 가격 조회
    try:
        fetcher = PricingFetcher()
        prices = fetcher.get_ec2_prices(region)

        if prices:
            _cache.set("ec2", region, prices)
            return prices

    except Exception as e:
        logger.warning(f"EC2 가격 조회 실패: {e}")

    return {}
