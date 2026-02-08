"""
core/shared/aws/pricing/vpc_endpoint.py - VPC Endpoint 가격 조회

VPC Endpoint(Interface/Gateway)의 시간당/월간 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

비용 구조:
    - Interface Endpoint: ~$0.01/hour (리전별 상이) + 데이터 처리 ~$0.01/GB
    - Gateway Endpoint (S3, DynamoDB): 무료 (시간당 및 데이터 처리 모두 $0.00)

사용법:
    from core.shared.aws.pricing.vpc_endpoint import (
        get_endpoint_hourly_price,
        get_endpoint_monthly_cost,
    )

    # Interface Endpoint 시간당 가격
    hourly = get_endpoint_hourly_price("ap-northeast-2")

    # 월간 고정 비용
    monthly = get_endpoint_monthly_cost("ap-northeast-2")

    # 데이터 처리 비용 포함 (100GB)
    total = get_endpoint_monthly_cost("ap-northeast-2", data_processed_gb=100)
"""

from __future__ import annotations

import logging

from .constants import HOURS_PER_MONTH
from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_endpoint_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """VPC Endpoint 가격을 조회한다.

    ``PricingService`` 를 통해 캐시 -> API -> fallback(constants) 순서로
    가격을 찾는다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {
                "interface_hourly": float,  # Interface Endpoint 시간당 USD
                "gateway_hourly": float,    # Gateway Endpoint 시간당 USD (항상 0.0)
                "data_per_gb": float,       # 데이터 처리 GB당 USD
            }
    """
    return pricing_service.get_prices("vpc_endpoint", region, refresh)


def get_endpoint_hourly_price(
    region: str = "ap-northeast-2",
    endpoint_type: str = "Interface",
) -> float:
    """VPC Endpoint 시간당 가격을 반환한다.

    ``endpoint_type`` 에 따라 Interface(~$0.01/hour) 또는 Gateway($0.00) 가격을
    반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        endpoint_type: 엔드포인트 타입 (``"Interface"`` 또는 ``"Gateway"``)

    Returns:
        시간당 USD. Gateway 타입이면 ``0.0``, Interface 타입의 기본값은 ``0.01``
    """
    prices = get_endpoint_prices(region)
    if endpoint_type.lower() == "gateway":
        return prices.get("gateway_hourly", 0.0)
    return prices.get("interface_hourly", 0.01)


def get_endpoint_data_price(region: str = "ap-northeast-2") -> float:
    """VPC Endpoint 데이터 처리 GB당 가격을 반환한다.

    Interface Endpoint를 통해 처리된 데이터에 대한 GB당 과금 가격이다.
    Gateway Endpoint(S3, DynamoDB)는 데이터 처리 비용이 없다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        GB당 USD (기본값: ``0.01``)
    """
    prices = get_endpoint_prices(region)
    return prices.get("data_per_gb", 0.01)


def get_endpoint_monthly_cost(
    region: str = "ap-northeast-2",
    endpoint_type: str = "Interface",
    hours: int = HOURS_PER_MONTH,
    data_processed_gb: float = 0.0,
) -> float:
    """VPC Endpoint의 월간 총 비용을 계산한다.

    ``hourly * hours + data_per_gb * data_processed_gb`` 로 산출한다.
    Gateway Endpoint는 항상 ``0.0`` 을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        endpoint_type: 엔드포인트 타입 (``"Interface"`` 또는 ``"Gateway"``)
        hours: 월간 가동 시간 (기본: ``730`` = 24h x 30.4d)
        data_processed_gb: 월간 처리 데이터량 (GB, 기본: ``0.0``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림). Gateway 타입이면 ``0.0``
    """
    prices = get_endpoint_prices(region)

    # Gateway Endpoint는 무료
    if endpoint_type.lower() == "gateway":
        return 0.0

    # Interface Endpoint
    hourly = prices.get("interface_hourly", 0.01)
    data_price = prices.get("data_per_gb", 0.01)

    fixed_cost = hourly * hours
    data_cost = data_price * data_processed_gb

    return round(fixed_cost + data_cost, 2)


def get_endpoint_monthly_fixed_cost(
    region: str = "ap-northeast-2",
    endpoint_type: str = "Interface",
) -> float:
    """VPC Endpoint 월간 고정 비용을 반환한다 (데이터 처리 비용 제외).

    ``get_endpoint_monthly_cost()`` 에 ``data_processed_gb=0`` 을 전달하여
    시간당 과금만으로 계산한 월간 고정 비용을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        endpoint_type: 엔드포인트 타입 (``"Interface"`` 또는 ``"Gateway"``)

    Returns:
        월간 고정 USD 비용. Gateway 타입이면 ``0.0``
    """
    return get_endpoint_monthly_cost(region, endpoint_type, hours=HOURS_PER_MONTH, data_processed_gb=0)
