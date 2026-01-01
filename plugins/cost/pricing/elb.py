"""
plugins/cost/pricing/elb.py - Elastic Load Balancer 가격 조회

ELB 비용 계산 (리전별 상이):
- ALB: ~$0.0225/시간 = ~$16.43/월
- NLB: ~$0.0225/시간 = ~$16.43/월
- GLB: ~$0.0125/시간 = ~$9.13/월
- CLB: ~$0.025/시간 = ~$18.25/월

사용법:
    from plugins.cost.pricing import get_elb_hourly_price, get_elb_monthly_cost

    # ALB 시간당 가격
    hourly = get_elb_hourly_price("ap-northeast-2", "application")

    # ALB 월간 비용
    monthly = get_elb_monthly_cost("ap-northeast-2", "application")
"""

import logging
from typing import Dict

from .cache import PriceCache
from .fetcher import PricingFetcher

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_cache = PriceCache()

# 월 평균 시간
HOURS_PER_MONTH = 730


def get_elb_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> Dict[str, float]:
    """ELB 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {"alb_hourly": float, "nlb_hourly": float, "glb_hourly": float, "clb_hourly": float}
    """
    return _get_cached_prices(region, refresh)


def get_elb_hourly_price(
    region: str = "ap-northeast-2",
    lb_type: str = "application",
) -> float:
    """ELB 시간당 가격

    Args:
        region: AWS 리전
        lb_type: application, network, gateway, classic

    Returns:
        시간당 USD
    """
    prices = get_elb_prices(region)
    type_map = {
        "application": "alb_hourly",
        "network": "nlb_hourly",
        "gateway": "glb_hourly",
        "classic": "clb_hourly",
    }
    key = type_map.get(lb_type.lower(), "alb_hourly")
    return prices.get(key, 0.0225)


def get_elb_monthly_cost(
    region: str = "ap-northeast-2",
    lb_type: str = "application",
    hours: int = HOURS_PER_MONTH,
) -> float:
    """ELB 월간 고정 비용 (LCU 비용 제외)

    Args:
        region: AWS 리전
        lb_type: application, network, gateway, classic
        hours: 가동 시간 (기본: 730시간)

    Returns:
        월간 USD 비용
    """
    hourly = get_elb_hourly_price(region, lb_type)
    return round(hourly * hours, 2)


def _get_cached_prices(region: str, refresh: bool = False) -> Dict[str, float]:
    """캐시된 가격 조회 (없으면 API 호출)"""
    if not refresh:
        cached = _cache.get("elb", region)
        if cached:
            return cached

    # API로 가격 조회
    try:
        fetcher = PricingFetcher()
        prices = fetcher.get_elb_prices(region)

        if prices and prices.get("alb_hourly", 0) > 0:
            _cache.set("elb", region, prices)
            return prices

    except Exception as e:
        logger.warning(f"ELB 가격 조회 실패: {e}")

    # 기본값 반환
    return {
        "alb_hourly": 0.0225,
        "nlb_hourly": 0.0225,
        "glb_hourly": 0.0125,
        "clb_hourly": 0.025,
    }
