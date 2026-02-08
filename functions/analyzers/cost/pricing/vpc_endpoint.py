"""
plugins/cost/pricing/vpc_endpoint.py - VPC Endpoint 가격 조회

VPC Endpoint 비용 계산:
- Interface Endpoint: 시간당 ~$0.01 (리전별 상이) + 데이터 처리 비용
- Gateway Endpoint (S3, DynamoDB): 무료

PricingService를 사용하여 캐시와 API를 통합 관리합니다.

사용법:
    from functions.analyzers.cost.pricing import get_endpoint_hourly_price, get_endpoint_monthly_cost

    # Interface Endpoint 시간당 가격
    hourly = get_endpoint_hourly_price("ap-northeast-2")

    # 월간 고정 비용
    monthly = get_endpoint_monthly_cost("ap-northeast-2")

    # 데이터 처리 비용 포함
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
    """VPC Endpoint 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {"interface_hourly": float, "gateway_hourly": float, "data_per_gb": float}
    """
    return pricing_service.get_prices("vpc_endpoint", region, refresh)


def get_endpoint_hourly_price(
    region: str = "ap-northeast-2",
    endpoint_type: str = "Interface",
) -> float:
    """VPC Endpoint 시간당 가격

    Args:
        region: AWS 리전
        endpoint_type: Interface 또는 Gateway

    Returns:
        시간당 USD
    """
    prices = get_endpoint_prices(region)
    if endpoint_type.lower() == "gateway":
        return prices.get("gateway_hourly", 0.0)
    return prices.get("interface_hourly", 0.01)


def get_endpoint_data_price(region: str = "ap-northeast-2") -> float:
    """VPC Endpoint 데이터 처리 GB당 가격

    Args:
        region: AWS 리전

    Returns:
        GB당 USD
    """
    prices = get_endpoint_prices(region)
    return prices.get("data_per_gb", 0.01)


def get_endpoint_monthly_cost(
    region: str = "ap-northeast-2",
    endpoint_type: str = "Interface",
    hours: int = HOURS_PER_MONTH,
    data_processed_gb: float = 0.0,
) -> float:
    """VPC Endpoint 월간 비용 계산

    Args:
        region: AWS 리전
        endpoint_type: Interface 또는 Gateway
        hours: 가동 시간 (기본: 730시간)
        data_processed_gb: 처리된 데이터량 (GB)

    Returns:
        월간 USD 비용
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
    """VPC Endpoint 월간 고정 비용 (데이터 비용 제외)

    Args:
        region: AWS 리전
        endpoint_type: Interface 또는 Gateway

    Returns:
        월간 고정 USD 비용
    """
    return get_endpoint_monthly_cost(region, endpoint_type, hours=HOURS_PER_MONTH, data_processed_gb=0)
