"""
core/shared/aws/pricing/dynamodb.py - Amazon DynamoDB 가격 조회

DynamoDB의 Provisioned/On-Demand 모드별 비용과 스토리지 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

비용 구조 (ap-northeast-2 기준):
    - On-Demand (PAY_PER_REQUEST):
      - 쓰기: $1.25 / 100만 WRU
      - 읽기: $0.25 / 100만 RRU
    - Provisioned:
      - WCU: $0.00065/시간 (~$0.47/월)
      - RCU: $0.00013/시간 (~$0.095/월)
    - Storage: $0.25 / GB / 월

사용법:
    from core.shared.aws.pricing.dynamodb import get_dynamodb_monthly_cost

    # Provisioned 테이블 월간 비용
    cost = get_dynamodb_monthly_cost(
        region="ap-northeast-2",
        billing_mode="PROVISIONED",
        rcu=10, wcu=5, storage_gb=1.5,
    )

    # On-Demand 테이블 월간 비용
    cost = get_dynamodb_monthly_cost(
        region="ap-northeast-2",
        billing_mode="PAY_PER_REQUEST",
        read_requests=1_000_000, write_requests=500_000,
        storage_gb=10,
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
    """DynamoDB Provisioned/On-Demand/Storage 가격을 조회한다.

    ``PricingService`` 를 통해 캐시 우선 조회하며, 캐시 미스 시 API를 호출한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {
                "rcu_per_hour": float,        # Provisioned RCU 시간당 가격
                "wcu_per_hour": float,        # Provisioned WCU 시간당 가격
                "read_per_million": float,    # On-Demand 읽기 100만건당 가격
                "write_per_million": float,   # On-Demand 쓰기 100만건당 가격
                "storage_per_gb": float,      # 스토리지 GB당 월간 가격
            }
    """
    return pricing_service.get_prices("dynamodb", region, refresh)


def get_dynamodb_provisioned_price(
    region: str = "ap-northeast-2",
    capacity_type: str = "read",
) -> float:
    """Provisioned Capacity 유닛의 시간당 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        capacity_type: ``"read"`` (RCU) 또는 ``"write"`` (WCU)

    Returns:
        시간당 USD (RCU 기본: ``0.00013``, WCU 기본: ``0.00065``)
    """
    prices = get_dynamodb_prices(region)
    if capacity_type.lower() == "write":
        return prices.get("wcu_per_hour", 0.00065)
    return prices.get("rcu_per_hour", 0.00013)


def get_dynamodb_ondemand_price(
    region: str = "ap-northeast-2",
    request_type: str = "read",
) -> float:
    """On-Demand 모드의 100만 요청당 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        request_type: ``"read"`` (RRU) 또는 ``"write"`` (WRU)

    Returns:
        100만 요청당 USD (읽기 기본: ``0.25``, 쓰기 기본: ``1.25``)
    """
    prices = get_dynamodb_prices(region)
    if request_type.lower() == "write":
        return prices.get("write_per_million", 1.25)
    return prices.get("read_per_million", 0.25)


def get_dynamodb_storage_price(region: str = "ap-northeast-2") -> float:
    """DynamoDB 스토리지 GB당 월간 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        GB당 월간 USD (기본: ``0.25``)
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
    """DynamoDB 테이블의 월간 총 비용을 계산한다.

    ``billing_mode`` 에 따라 Provisioned(RCU/WCU 시간당) 또는
    On-Demand(요청당) 비용을 산출하고, 스토리지 비용을 합산한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        billing_mode: ``"PROVISIONED"`` 또는 ``"PAY_PER_REQUEST"``
        rcu: Provisioned Read Capacity Units (Provisioned 모드)
        wcu: Provisioned Write Capacity Units (Provisioned 모드)
        read_requests: 월간 읽기 요청 수 (On-Demand 모드)
        write_requests: 월간 쓰기 요청 수 (On-Demand 모드)
        storage_gb: 스토리지 용량 (GB)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
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
    """현재 소비량 기준으로 Provisioned 모드 전환 시 예상 비용을 계산한다.

    평균 소비 RCU/WCU에 10% 여유분을 더한 권장 용량으로 비용을 산출한다.

    Args:
        region: AWS 리전 코드
        avg_consumed_rcu: CloudWatch 기준 평균 소비 RCU (초당)
        avg_consumed_wcu: CloudWatch 기준 평균 소비 WCU (초당)
        storage_gb: 테이블 스토리지 용량 (GB)

    Returns:
        예상 월간 USD 비용 (10% 여유분 포함, 소수점 2자리 반올림)
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
    """현재 소비량 기준으로 On-Demand 모드 전환 시 예상 비용을 계산한다.

    초당 RCU/WCU를 월간 요청 수로 환산(30일 * 24h * 3600s)하여 비용을 산출한다.

    Args:
        region: AWS 리전 코드
        avg_consumed_rcu: CloudWatch 기준 평균 소비 RCU (초당)
        avg_consumed_wcu: CloudWatch 기준 평균 소비 WCU (초당)
        storage_gb: 테이블 스토리지 용량 (GB)

    Returns:
        예상 월간 USD 비용 (소수점 2자리 반올림)
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
