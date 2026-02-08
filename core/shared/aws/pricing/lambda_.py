"""
core/shared/aws/pricing/lambda_.py - AWS Lambda 가격 조회

Lambda의 요청(Request), 실행 시간(Duration), Provisioned Concurrency 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

비용 구조:
    - Request: $0.20 / 100만 요청 (무료 티어: 월 100만 요청)
    - Duration: $0.0000166667 / GB-초 (무료 티어: 월 40만 GB-초)
    - Provisioned Concurrency: $0.000004646 / GB-시간

사용법:
    from core.shared.aws.pricing.lambda_ import get_lambda_monthly_cost

    # 월 100만 호출, 256MB, 200ms 평균 실행 시간
    cost = get_lambda_monthly_cost(
        region="ap-northeast-2",
        invocations=1_000_000,
        avg_duration_ms=200,
        memory_mb=256,
    )

Note:
    파일명이 ``lambda_.py`` 인 이유는 ``lambda`` 가 Python 예약어이기 때문이다.
"""

from __future__ import annotations

import logging

from .constants import (
    HOURS_PER_MONTH,
    LAMBDA_FREE_TIER_GB_SECONDS,
    LAMBDA_FREE_TIER_REQUESTS,
)
from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_lambda_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """Lambda 요청/실행/Provisioned Concurrency 가격을 조회한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {
                "request_per_million": float,                    # 100만 요청당 USD
                "duration_per_gb_second": float,                 # GB-초당 USD
                "provisioned_concurrency_per_gb_hour": float,    # Provisioned GB-시간당 USD
            }
    """
    return pricing_service.get_prices("lambda", region, refresh)


def get_lambda_request_price(region: str = "ap-northeast-2") -> float:
    """Lambda 요청(Request) 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        100만 요청당 USD (기본값: ``0.20``)
    """
    prices = get_lambda_prices(region)
    return prices.get("request_per_million", 0.20)


def get_lambda_duration_price(region: str = "ap-northeast-2") -> float:
    """Lambda 실행 시간(Duration) GB-초당 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        GB-초당 USD (기본값: ``0.0000166667``)
    """
    prices = get_lambda_prices(region)
    return prices.get("duration_per_gb_second", 0.0000166667)


def get_lambda_provisioned_price(region: str = "ap-northeast-2") -> float:
    """Lambda Provisioned Concurrency GB-시간당 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        GB-시간당 USD (기본값: ``0.000004646``)
    """
    prices = get_lambda_prices(region)
    return prices.get("provisioned_concurrency_per_gb_hour", 0.000004646)


def get_lambda_monthly_cost(
    region: str = "ap-northeast-2",
    invocations: int = 0,
    avg_duration_ms: float = 0.0,
    memory_mb: int = 128,
    include_free_tier: bool = True,
) -> float:
    """Lambda 함수의 월간 요청+실행 시간 비용을 계산한다.

    ``request_cost + duration_cost`` 로 산출하며, 프리 티어 적용 시
    무료 요청(100만)과 무료 GB-초(40만)를 차감한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        invocations: 월간 호출 수 (기본: ``0``)
        avg_duration_ms: 평균 실행 시간 (밀리초, 기본: ``0.0``)
        memory_mb: 할당 메모리 (MB, 기본: ``128``)
        include_free_tier: 프리 티어 적용 여부 (기본: ``True``)

    Returns:
        월간 USD 비용 (소수점 4자리 반올림)
    """
    prices = get_lambda_prices(region)

    # 요청 비용
    billable_requests = invocations
    if include_free_tier:
        billable_requests = max(0, invocations - LAMBDA_FREE_TIER_REQUESTS)
    request_cost = (billable_requests / 1_000_000) * prices.get("request_per_million", 0.20)

    # 실행 시간 비용 (GB-초 단위)
    # 메모리 MB -> GB, 시간 ms -> 초
    gb_seconds = (memory_mb / 1024) * (avg_duration_ms / 1000) * invocations
    billable_gb_seconds = gb_seconds
    if include_free_tier:
        billable_gb_seconds = max(0, gb_seconds - LAMBDA_FREE_TIER_GB_SECONDS)
    duration_cost = billable_gb_seconds * prices.get("duration_per_gb_second", 0.0000166667)

    return round(request_cost + duration_cost, 4)


def get_lambda_provisioned_monthly_cost(
    region: str = "ap-northeast-2",
    memory_mb: int = 128,
    provisioned_concurrency: int = 0,
    hours: int = HOURS_PER_MONTH,
) -> float:
    """Lambda Provisioned Concurrency의 월간 비용을 계산한다.

    ``(memory_mb/1024) * provisioned_concurrency * hours * gb_hour_price`` 로 산출한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        memory_mb: 할당 메모리 (MB, 기본: ``128``)
        provisioned_concurrency: Provisioned Concurrency 인스턴스 수 (기본: ``0``)
        hours: 활성 시간 (기본: ``730`` = 한 달)

    Returns:
        월간 USD 비용 (소수점 4자리 반올림). ``provisioned_concurrency <= 0`` 이면 ``0.0``
    """
    if provisioned_concurrency <= 0:
        return 0.0

    prices = get_lambda_prices(region)

    # GB-시간 계산
    gb_hours = (memory_mb / 1024) * provisioned_concurrency * hours
    cost = gb_hours * prices.get("provisioned_concurrency_per_gb_hour", 0.000004646)

    return round(cost, 4)


def estimate_lambda_cost(
    region: str = "ap-northeast-2",
    invocations: int = 0,
    avg_duration_ms: float = 0.0,
    memory_mb: int = 128,
    provisioned_concurrency: int = 0,
    include_free_tier: bool = True,
) -> dict[str, float]:
    """Lambda 함수의 종합 비용(요청+실행+Provisioned)을 항목별로 추정한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        invocations: 월간 호출 수 (기본: ``0``)
        avg_duration_ms: 평균 실행 시간 (밀리초, 기본: ``0.0``)
        memory_mb: 할당 메모리 (MB, 기본: ``128``)
        provisioned_concurrency: Provisioned Concurrency 수 (기본: ``0``)
        include_free_tier: 프리 티어 적용 여부 (기본: ``True``)

    Returns:
        항목별 비용 딕셔너리 (소수점 4자리 반올림)::

            {
                "request_cost": float,       # 요청 비용
                "duration_cost": float,      # 실행 시간 비용
                "provisioned_cost": float,   # Provisioned Concurrency 비용
                "total_cost": float,         # 합계
            }
    """
    prices = get_lambda_prices(region)

    # 요청 비용
    billable_requests = invocations
    if include_free_tier:
        billable_requests = max(0, invocations - LAMBDA_FREE_TIER_REQUESTS)
    request_cost = (billable_requests / 1_000_000) * prices.get("request_per_million", 0.20)

    # 실행 시간 비용
    gb_seconds = (memory_mb / 1024) * (avg_duration_ms / 1000) * invocations
    billable_gb_seconds = gb_seconds
    if include_free_tier:
        billable_gb_seconds = max(0, gb_seconds - LAMBDA_FREE_TIER_GB_SECONDS)
    duration_cost = billable_gb_seconds * prices.get("duration_per_gb_second", 0.0000166667)

    # Provisioned Concurrency 비용
    provisioned_cost = 0.0
    if provisioned_concurrency > 0:
        gb_hours = (memory_mb / 1024) * provisioned_concurrency * HOURS_PER_MONTH
        provisioned_cost = gb_hours * prices.get("provisioned_concurrency_per_gb_hour", 0.000004646)

    total = request_cost + duration_cost + provisioned_cost

    return {
        "request_cost": round(request_cost, 4),
        "duration_cost": round(duration_cost, 4),
        "provisioned_cost": round(provisioned_cost, 4),
        "total_cost": round(total, 4),
    }
