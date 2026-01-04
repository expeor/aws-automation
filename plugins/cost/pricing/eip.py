"""
plugins/cost/pricing/eip.py - Elastic IP 가격 조회

Elastic IP 비용 계산:
- 미연결 EIP: ~$0.005/시간 = ~$3.60/월 (리전별 상이)
- 연결된 EIP: 무료 (첫 번째만, 추가 EIP는 비용 발생)

사용법:
    from plugins.cost.pricing import get_eip_hourly_price, get_eip_monthly_cost

    # 미연결 EIP 시간당 가격
    hourly = get_eip_hourly_price("ap-northeast-2")

    # 미연결 EIP 월간 비용
    monthly = get_eip_monthly_cost("ap-northeast-2")
"""

import logging

from .cache import PriceCache
from .fetcher import PricingFetcher

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_cache = PriceCache()

# 월 평균 시간
HOURS_PER_MONTH = 730


def get_eip_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """Elastic IP 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {"unused_hourly": float, "additional_hourly": float}
    """
    return _get_cached_prices(region, refresh)


def get_eip_hourly_price(region: str = "ap-northeast-2") -> float:
    """미연결 EIP 시간당 가격

    Args:
        region: AWS 리전

    Returns:
        시간당 USD
    """
    prices = get_eip_prices(region)
    return prices.get("unused_hourly", 0.005)


def get_eip_monthly_cost(
    region: str = "ap-northeast-2",
    hours: int = HOURS_PER_MONTH,
) -> float:
    """미연결 EIP 월간 비용

    Args:
        region: AWS 리전
        hours: 가동 시간 (기본: 730시간)

    Returns:
        월간 USD 비용
    """
    hourly = get_eip_hourly_price(region)
    return round(hourly * hours, 2)


def _get_cached_prices(region: str, refresh: bool = False) -> dict[str, float]:
    """캐시된 가격 조회 (없으면 API 호출)"""
    if not refresh:
        cached = _cache.get("eip", region)
        if cached:
            return cached

    # API로 가격 조회
    try:
        fetcher = PricingFetcher()
        prices = fetcher.get_eip_prices(region)

        if prices and prices.get("unused_hourly", 0) > 0:
            _cache.set("eip", region, prices)
            return prices

    except Exception as e:
        logger.warning(f"EIP 가격 조회 실패: {e}")

    # 기본값 반환
    return {"unused_hourly": 0.005, "additional_hourly": 0.005}
