"""
plugins/cost/pricing/lambda_.py - Lambda 가격 조회

Lambda 비용 계산:
- Request: 100만 요청당 $0.20
- Duration: GB-초당 $0.0000166667
- Provisioned Concurrency: GB-시간당 $0.000004646

사용법:
    from plugins.cost.pricing import get_lambda_prices, get_lambda_monthly_cost

    # 가격 조회
    prices = get_lambda_prices("ap-northeast-2")

    # 월간 비용 계산
    cost = get_lambda_monthly_cost(
        region="ap-northeast-2",
        invocations=1_000_000,         # 월 100만 호출
        avg_duration_ms=200,           # 평균 실행 시간 200ms
        memory_mb=256,                 # 메모리 256MB
    )

주의: 파일명이 lambda_.py인 이유는 'lambda'가 Python 예약어이기 때문입니다.
"""

import logging

from .cache import PriceCache
from .fetcher import PricingFetcher

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_cache = PriceCache()

# 상수
HOURS_PER_MONTH = 730
FREE_TIER_REQUESTS = 1_000_000  # 월 100만 요청 무료
FREE_TIER_GB_SECONDS = 400_000  # 월 40만 GB-초 무료


def get_lambda_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """Lambda 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {
            "request_per_million": float,
            "duration_per_gb_second": float,
            "provisioned_concurrency_per_gb_hour": float,
        }
    """
    return _get_cached_prices(region, refresh)


def get_lambda_request_price(region: str = "ap-northeast-2") -> float:
    """Lambda 요청 가격 (100만 요청당)

    Args:
        region: AWS 리전

    Returns:
        100만 요청당 USD
    """
    prices = get_lambda_prices(region)
    return prices.get("request_per_million", 0.20)


def get_lambda_duration_price(region: str = "ap-northeast-2") -> float:
    """Lambda 실행 시간 가격 (GB-초당)

    Args:
        region: AWS 리전

    Returns:
        GB-초당 USD
    """
    prices = get_lambda_prices(region)
    return prices.get("duration_per_gb_second", 0.0000166667)


def get_lambda_provisioned_price(region: str = "ap-northeast-2") -> float:
    """Lambda Provisioned Concurrency 가격 (GB-시간당)

    Args:
        region: AWS 리전

    Returns:
        GB-시간당 USD
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
    """Lambda 월간 비용 계산

    Args:
        region: AWS 리전
        invocations: 월간 호출 수
        avg_duration_ms: 평균 실행 시간 (밀리초)
        memory_mb: 할당 메모리 (MB)
        include_free_tier: 프리 티어 적용 여부

    Returns:
        월간 USD 비용
    """
    prices = get_lambda_prices(region)

    # 요청 비용
    billable_requests = invocations
    if include_free_tier:
        billable_requests = max(0, invocations - FREE_TIER_REQUESTS)
    request_cost = (billable_requests / 1_000_000) * prices.get("request_per_million", 0.20)

    # 실행 시간 비용 (GB-초 단위)
    # 메모리 MB -> GB, 시간 ms -> 초
    gb_seconds = (memory_mb / 1024) * (avg_duration_ms / 1000) * invocations
    billable_gb_seconds = gb_seconds
    if include_free_tier:
        billable_gb_seconds = max(0, gb_seconds - FREE_TIER_GB_SECONDS)
    duration_cost = billable_gb_seconds * prices.get("duration_per_gb_second", 0.0000166667)

    return round(request_cost + duration_cost, 4)


def get_lambda_provisioned_monthly_cost(
    region: str = "ap-northeast-2",
    memory_mb: int = 128,
    provisioned_concurrency: int = 0,
    hours: int = HOURS_PER_MONTH,
) -> float:
    """Lambda Provisioned Concurrency 월간 비용

    Args:
        region: AWS 리전
        memory_mb: 할당 메모리 (MB)
        provisioned_concurrency: Provisioned Concurrency 수
        hours: 활성 시간 (기본: 730시간)

    Returns:
        월간 USD 비용
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
    """Lambda 종합 비용 추정

    Args:
        region: AWS 리전
        invocations: 월간 호출 수
        avg_duration_ms: 평균 실행 시간 (밀리초)
        memory_mb: 할당 메모리 (MB)
        provisioned_concurrency: Provisioned Concurrency 수
        include_free_tier: 프리 티어 적용 여부

    Returns:
        {
            "request_cost": float,
            "duration_cost": float,
            "provisioned_cost": float,
            "total_cost": float,
        }
    """
    prices = get_lambda_prices(region)

    # 요청 비용
    billable_requests = invocations
    if include_free_tier:
        billable_requests = max(0, invocations - FREE_TIER_REQUESTS)
    request_cost = (billable_requests / 1_000_000) * prices.get("request_per_million", 0.20)

    # 실행 시간 비용
    gb_seconds = (memory_mb / 1024) * (avg_duration_ms / 1000) * invocations
    billable_gb_seconds = gb_seconds
    if include_free_tier:
        billable_gb_seconds = max(0, gb_seconds - FREE_TIER_GB_SECONDS)
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


def _get_cached_prices(region: str, refresh: bool = False) -> dict[str, float]:
    """캐시된 가격 조회 (없으면 API 호출)"""
    if not refresh:
        cached = _cache.get("lambda", region)
        if cached:
            return cached

    # API로 가격 조회
    try:
        fetcher = PricingFetcher()
        prices = fetcher.get_lambda_prices(region)

        if prices and prices.get("request_per_million", 0) > 0:
            _cache.set("lambda", region, prices)
            return prices

    except Exception as e:
        logger.warning(f"Lambda 가격 조회 실패: {e}")

    # 기본값 반환
    return {
        "request_per_million": 0.20,
        "duration_per_gb_second": 0.0000166667,
        "provisioned_concurrency_per_gb_hour": 0.000004646,
    }
