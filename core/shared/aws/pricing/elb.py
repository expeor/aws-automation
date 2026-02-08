"""
core/shared/aws/pricing/elb.py - Elastic Load Balancer 가격 조회

ELB 타입별(ALB/NLB/GLB/CLB) 시간당 고정 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.
LCU(Load Balancer Capacity Unit) 비용은 사용량에 따라 별도 발생하며 이 모듈에서 미포함.

비용 구조 (ap-northeast-2 기준, 시간당 고정 비용):
    - ALB: ~$0.0225/시간 (~$16.43/월)
    - NLB: ~$0.0225/시간 (~$16.43/월)
    - GLB: ~$0.0125/시간 (~$9.13/월)
    - CLB: ~$0.025/시간 (~$18.25/월)

사용법:
    from core.shared.aws.pricing.elb import get_elb_hourly_price, get_elb_monthly_cost

    # ALB 시간당 가격
    hourly = get_elb_hourly_price("ap-northeast-2", "application")

    # ALB 월간 고정 비용
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
    """ELB 타입별 시간당 가격을 조회한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {
                "alb_hourly": float,   # Application LB 시간당 USD
                "nlb_hourly": float,   # Network LB 시간당 USD
                "glb_hourly": float,   # Gateway LB 시간당 USD
                "clb_hourly": float,   # Classic LB 시간당 USD
            }
    """
    return pricing_service.get_prices("elb", region, refresh)


def get_elb_hourly_price(
    region: str = "ap-northeast-2",
    lb_type: str = "application",
) -> float:
    """ELB 특정 타입의 시간당 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        lb_type: LB 타입 (``"application"``, ``"network"``, ``"gateway"``, ``"classic"``)

    Returns:
        시간당 USD (기본값: ``0.0225``)
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
    """ELB의 월간 고정 비용을 계산한다 (LCU 비용 제외).

    ``hourly_price * hours`` 로 산출한다. LCU 기반 변동 비용은 미포함.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        lb_type: LB 타입 (``"application"``, ``"network"``, ``"gateway"``, ``"classic"``)
        hours: 가동 시간 (기본: ``730`` = 한 달)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    hourly = get_elb_hourly_price(region, lb_type)
    return round(hourly * hours, 2)
