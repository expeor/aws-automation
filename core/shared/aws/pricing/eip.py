"""
core/shared/aws/pricing/eip.py - Elastic IP 가격 조회

미연결(유휴) Elastic IP의 시간당/월간 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

비용 구조:
    - 미연결 EIP: ~$0.005/시간 = ~$3.65/월 (리전별 상이)
    - 연결된 EIP: 무료 (첫 번째만, 추가 EIP는 비용 발생)

사용법:
    from core.shared.aws.pricing.eip import get_eip_hourly_price, get_eip_monthly_cost

    # 미연결 EIP 시간당 가격
    hourly = get_eip_hourly_price("ap-northeast-2")

    # 미연결 EIP 월간 비용
    monthly = get_eip_monthly_cost("ap-northeast-2")
"""

from __future__ import annotations

import logging

from .constants import HOURS_PER_MONTH
from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_eip_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """Elastic IP 유형별 시간당 가격을 조회한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {
                "unused_hourly": float,       # 미연결 EIP 시간당 USD
                "additional_hourly": float,   # 추가 EIP 시간당 USD
            }
    """
    return pricing_service.get_prices("eip", region, refresh)


def get_eip_hourly_price(region: str = "ap-northeast-2") -> float:
    """미연결(유휴) Elastic IP의 시간당 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        시간당 USD (기본값: ``0.005``)
    """
    prices = get_eip_prices(region)
    return prices.get("unused_hourly", 0.005)


def get_eip_monthly_cost(
    region: str = "ap-northeast-2",
    hours: int = HOURS_PER_MONTH,
) -> float:
    """미연결(유휴) Elastic IP의 월간 비용을 계산한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        hours: 유휴 시간 (기본: ``730`` = 한 달)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    hourly = get_eip_hourly_price(region)
    return round(hourly * hours, 2)
