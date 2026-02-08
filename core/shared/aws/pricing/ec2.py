"""
core/shared/aws/pricing/ec2.py - Amazon EC2 인스턴스 가격 조회

EC2 인스턴스의 On-Demand 시간당/월간 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

조회 조건:
    - OS: Linux, Tenancy: Shared, Pre-installed SW: NA
    - Reserved Instance/Spot 가격은 미포함

사용법:
    from core.shared.aws.pricing.ec2 import get_ec2_price, get_ec2_monthly_cost

    # t3.medium 시간당 가격
    hourly = get_ec2_price("t3.medium", "ap-northeast-2")

    # t3.medium 월간 비용 (730시간 기준)
    monthly = get_ec2_monthly_cost("t3.medium", "ap-northeast-2")
"""

from __future__ import annotations

import logging

from .constants import HOURS_PER_MONTH
from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_ec2_price(
    instance_type: str,
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> float:
    """EC2 인스턴스의 On-Demand 시간당 가격을 조회한다.

    Args:
        instance_type: EC2 인스턴스 타입 (예: ``"t3.medium"``, ``"m5.large"``)
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        시간당 USD 가격. 가격 정보가 없으면 ``0.0``
    """
    prices = pricing_service.get_prices("ec2", region, refresh)

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
    """EC2 인스턴스의 월간 On-Demand 비용을 계산한다.

    ``get_ec2_price() * hours_per_month`` 로 산출한다.

    Args:
        instance_type: EC2 인스턴스 타입 (예: ``"t3.medium"``)
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        hours_per_month: 월간 운영 시간 (기본: ``730``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    hourly = get_ec2_price(instance_type, region)
    return round(hourly * hours_per_month, 2)


def get_ec2_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """리전의 모든 EC2 인스턴스 타입 가격을 조회한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        ``{instance_type: hourly_price}`` 딕셔너리 (예: ``{"t3.medium": 0.0416}``)
    """
    return pricing_service.get_prices("ec2", region, refresh)


# 하위 호환성을 위한 alias
get_ec2_prices_bulk = get_ec2_prices
