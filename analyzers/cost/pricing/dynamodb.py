"""
plugins/cost/pricing/dynamodb.py - DynamoDB 가격 조회

DynamoDB 비용 구성:
- On-Demand (PAY_PER_REQUEST):
  - 쓰기: $1.25 per million WRU (ap-northeast-2 기준)
  - 읽기: $0.25 per million RRU
- Provisioned:
  - WCU: $0.00065 per hour (~$0.47/월)
  - RCU: $0.00013 per hour (~$0.095/월)
- Storage: $0.25 per GB per month

PricingService를 사용하여 캐시와 API를 통합 관리합니다.

사용법:
    from analyzers.cost.pricing import get_dynamodb_monthly_cost

    # Provisioned 테이블 월간 비용
    cost = get_dynamodb_monthly_cost(
        region="ap-northeast-2",
        billing_mode="PROVISIONED",
        rcu=10,
        wcu=5,
        storage_gb=1.5
    )

    # On-Demand 테이블 월간 비용
    cost = get_dynamodb_monthly_cost(
        region="ap-northeast-2",
        billing_mode="PAY_PER_REQUEST",
        read_requests=1000000,
        write_requests=500000,
        storage_gb=10
    )
"""

from __future__ import annotations

import logging

from .constants import HOURS_PER_MONTH
from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_dynamodb_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """DynamoDB 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {
            "rcu_per_hour": float,
            "wcu_per_hour": float,
            "read_per_million": float,
            "write_per_million": float,
            "storage_per_gb": float,
        }
    """
    return pricing_service.get_prices("dynamodb", region, refresh)


def get_dynamodb_provisioned_price(
    region: str = "ap-northeast-2",
    capacity_type: str = "read",
) -> float:
    """Provisioned Capacity 시간당 가격

    Args:
        region: AWS 리전
        capacity_type: "read" (RCU) 또는 "write" (WCU)

    Returns:
        시간당 USD
    """
    prices = get_dynamodb_prices(region)
    if capacity_type.lower() == "write":
        return prices.get("wcu_per_hour", 0.00065)
    return prices.get("rcu_per_hour", 0.00013)


def get_dynamodb_ondemand_price(
    region: str = "ap-northeast-2",
    request_type: str = "read",
) -> float:
    """On-Demand 100만 요청당 가격

    Args:
        region: AWS 리전
        request_type: "read" 또는 "write"

    Returns:
        100만 요청당 USD
    """
    prices = get_dynamodb_prices(region)
    if request_type.lower() == "write":
        return prices.get("write_per_million", 1.25)
    return prices.get("read_per_million", 0.25)


def get_dynamodb_storage_price(region: str = "ap-northeast-2") -> float:
    """Storage GB당 월간 가격

    Args:
        region: AWS 리전

    Returns:
        GB당 월간 USD
    """
    prices = get_dynamodb_prices(region)
    return prices.get("storage_per_gb", 0.25)


def get_dynamodb_monthly_cost(
    region: str = "ap-northeast-2",
    billing_mode: str = "PROVISIONED",
    rcu: int = 0,
    wcu: int = 0,
    read_requests: int = 0,
    write_requests: int = 0,
    storage_gb: float = 0.0,
) -> float:
    """DynamoDB 월간 비용 계산

    Args:
        region: AWS 리전
        billing_mode: "PROVISIONED" 또는 "PAY_PER_REQUEST"
        rcu: Read Capacity Units (Provisioned)
        wcu: Write Capacity Units (Provisioned)
        read_requests: 읽기 요청 수 (On-Demand)
        write_requests: 쓰기 요청 수 (On-Demand)
        storage_gb: 스토리지 용량 (GB)

    Returns:
        월간 USD 비용
    """
    prices = get_dynamodb_prices(region)
    total = 0.0

    # 용량/요청 비용
    if billing_mode == "PAY_PER_REQUEST":
        # On-Demand
        read_cost = (read_requests / 1_000_000) * prices.get("read_per_million", 0.25)
        write_cost = (write_requests / 1_000_000) * prices.get("write_per_million", 1.25)
        total += read_cost + write_cost
    else:
        # Provisioned
        rcu_cost = rcu * prices.get("rcu_per_hour", 0.00013) * HOURS_PER_MONTH
        wcu_cost = wcu * prices.get("wcu_per_hour", 0.00065) * HOURS_PER_MONTH
        total += rcu_cost + wcu_cost

    # 스토리지 비용
    storage_cost = storage_gb * prices.get("storage_per_gb", 0.25)
    total += storage_cost

    return round(total, 2)


def estimate_provisioned_cost(
    region: str,
    avg_consumed_rcu: float,
    avg_consumed_wcu: float,
    storage_gb: float,
) -> float:
    """현재 사용량 기준 Provisioned 예상 비용

    Args:
        region: AWS 리전
        avg_consumed_rcu: 평균 소비 RCU
        avg_consumed_wcu: 평균 소비 WCU
        storage_gb: 스토리지 용량

    Returns:
        예상 월간 비용 (10% 여유분 포함)
    """
    # 10% 여유분을 더해 권장 용량 계산
    recommended_rcu = int(avg_consumed_rcu * 1.1) + 1
    recommended_wcu = int(avg_consumed_wcu * 1.1) + 1

    return get_dynamodb_monthly_cost(
        region=region,
        billing_mode="PROVISIONED",
        rcu=recommended_rcu,
        wcu=recommended_wcu,
        storage_gb=storage_gb,
    )


def estimate_ondemand_cost(
    region: str,
    avg_consumed_rcu: float,
    avg_consumed_wcu: float,
    storage_gb: float,
) -> float:
    """현재 사용량 기준 On-Demand 예상 비용

    RCU/WCU를 요청 수로 환산 (초당 → 월간)

    Args:
        region: AWS 리전
        avg_consumed_rcu: 평균 소비 RCU (초당)
        avg_consumed_wcu: 평균 소비 WCU (초당)
        storage_gb: 스토리지 용량

    Returns:
        예상 월간 비용
    """
    # 초당 용량 → 월간 요청 수 변환 (30일 * 24시간 * 3600초)
    seconds_per_month = 30 * 24 * 3600
    read_requests = avg_consumed_rcu * seconds_per_month
    write_requests = avg_consumed_wcu * seconds_per_month

    return get_dynamodb_monthly_cost(
        region=region,
        billing_mode="PAY_PER_REQUEST",
        read_requests=int(read_requests),
        write_requests=int(write_requests),
        storage_gb=storage_gb,
    )
