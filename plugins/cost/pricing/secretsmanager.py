"""
plugins/cost/pricing/secretsmanager.py - Secrets Manager 가격 조회

Secrets Manager 비용 계산:
- Secret당 월 비용: ~$0.40 (리전별 상이)
- API 호출: ~$0.05/10,000 requests

사용법:
    from plugins.cost.pricing import get_secret_monthly_cost

    # Secret 하나의 월간 비용
    monthly = get_secret_monthly_cost("ap-northeast-2")

    # 여러 Secret의 월간 비용
    total = get_secret_monthly_cost("ap-northeast-2", secret_count=10)
"""

import logging

from .cache import PriceCache
from .fetcher import PricingFetcher

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_cache = PriceCache()


def get_secret_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """Secrets Manager 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {"per_secret_monthly": float, "per_10k_api_calls": float}
    """
    return _get_cached_prices(region, refresh)


def get_secret_price(region: str = "ap-northeast-2") -> float:
    """Secret 하나의 월간 가격

    Args:
        region: AWS 리전

    Returns:
        월간 USD
    """
    prices = get_secret_prices(region)
    return prices.get("per_secret_monthly", 0.40)


def get_secret_api_price(region: str = "ap-northeast-2") -> float:
    """API 호출 10,000건당 가격

    Args:
        region: AWS 리전

    Returns:
        10,000건당 USD
    """
    prices = get_secret_prices(region)
    return prices.get("per_10k_api_calls", 0.05)


def get_secret_monthly_cost(
    region: str = "ap-northeast-2",
    secret_count: int = 1,
    api_calls: int = 0,
) -> float:
    """Secrets Manager 월간 비용 계산

    Args:
        region: AWS 리전
        secret_count: Secret 개수
        api_calls: API 호출 수

    Returns:
        월간 USD 비용
    """
    prices = get_secret_prices(region)

    per_secret = prices.get("per_secret_monthly", 0.40)
    per_10k_api = prices.get("per_10k_api_calls", 0.05)

    secret_cost = per_secret * secret_count
    api_cost = (api_calls / 10000) * per_10k_api

    return round(secret_cost + api_cost, 2)


def _get_cached_prices(region: str, refresh: bool = False) -> dict[str, float]:
    """캐시된 가격 조회 (없으면 API 호출)"""
    if not refresh:
        cached = _cache.get("secretsmanager", region)
        if cached:
            return cached

    # API로 가격 조회
    try:
        fetcher = PricingFetcher()
        prices = fetcher.get_secrets_manager_prices(region)

        if prices and prices.get("per_secret_monthly", 0) > 0:
            _cache.set("secretsmanager", region, prices)
            return prices

    except Exception as e:
        logger.warning(f"Secrets Manager 가격 조회 실패: {e}")

    # 기본값 반환
    return {"per_secret_monthly": 0.40, "per_10k_api_calls": 0.05}
