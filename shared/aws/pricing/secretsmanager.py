"""
plugins/cost/pricing/secretsmanager.py - Secrets Manager 가격 조회

Secrets Manager 비용 계산:
- Secret당 월 비용: ~$0.40 (리전별 상이)
- API 호출: ~$0.05/10,000 requests

PricingService를 사용하여 캐시와 API를 통합 관리합니다.

사용법:
    from plugins.cost.pricing import get_secret_monthly_cost

    # Secret 하나의 월간 비용
    monthly = get_secret_monthly_cost("ap-northeast-2")

    # 여러 Secret의 월간 비용
    total = get_secret_monthly_cost("ap-northeast-2", secret_count=10)
"""

from __future__ import annotations

import logging

from .utils import pricing_service

logger = logging.getLogger(__name__)


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
    return pricing_service.get_prices("secretsmanager", region, refresh)


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
