"""
functions/analyzers/cost/pricing/elb.py - Elastic Load Balancer 가격 조회

ELB 비용 계산 (리전별 상이):
- ALB: ~$0.0225/시간 = ~$16.43/월
- NLB: ~$0.0225/시간 = ~$16.43/월
- GLB: ~$0.0125/시간 = ~$9.13/월
- CLB: ~$0.025/시간 = ~$18.25/월

PricingService를 사용하여 캐시와 API를 통합 관리합니다.

사용법:
    from functions.analyzers.cost.pricing import get_elb_hourly_price, get_elb_monthly_cost

    # ALB 시간당 가격
    hourly = get_elb_hourly_price("ap-northeast-2", "application")

    # ALB 월간 비용
    monthly = get_elb_monthly_cost("ap-northeast-2", "application")
"""

from __future__ import annotations

import logging

from .constants import HOURS_PER_MONTH
from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_elb_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """ELB 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {"alb_hourly": float, "nlb_hourly": float, "glb_hourly": float, "clb_hourly": float}
    """
    return pricing_service.get_prices("elb", region, refresh)


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
