"""
core/shared/aws/pricing/secretsmanager.py - AWS Secrets Manager 가격 조회

Secrets Manager 시크릿 보유 및 API 호출 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

비용 구조:
    - Secret 보유: ~$0.40/월/시크릿 (리전별 상이)
    - API 호출: ~$0.05 / 10,000 requests

사용법:
    from core.shared.aws.pricing.secretsmanager import get_secret_monthly_cost

    # 10개 시크릿 + API 5만건 월간 비용
    total = get_secret_monthly_cost(
        "ap-northeast-2", secret_count=10, api_calls=50_000
    )
"""

from __future__ import annotations

import logging

from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_secret_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """Secrets Manager 시크릿/API 가격을 조회한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {
                "per_secret_monthly": float,   # 시크릿 1개 월간 USD
                "per_10k_api_calls": float,    # API 10,000건당 USD
            }
    """
    return pricing_service.get_prices("secretsmanager", region, refresh)


def get_secret_price(region: str = "ap-northeast-2") -> float:
    """시크릿 1개의 월간 보유 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        시크릿 1개 월간 USD (기본값: ``0.40``)
    """
    prices = get_secret_prices(region)
    return prices.get("per_secret_monthly", 0.40)


def get_secret_api_price(region: str = "ap-northeast-2") -> float:
    """Secrets Manager API 호출 10,000건당 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        10,000건당 USD (기본값: ``0.05``)
    """
    prices = get_secret_prices(region)
    return prices.get("per_10k_api_calls", 0.05)


def get_secret_monthly_cost(
    region: str = "ap-northeast-2",
    secret_count: int = 1,
    api_calls: int = 0,
) -> float:
    """Secrets Manager 시크릿 보유 + API 호출의 월간 총 비용을 계산한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        secret_count: 시크릿 개수 (기본: ``1``)
        api_calls: 월간 API 호출 수 (기본: ``0``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    prices = get_secret_prices(region)

    per_secret = prices.get("per_secret_monthly", 0.40)
    per_10k_api = prices.get("per_10k_api_calls", 0.05)

    secret_cost = per_secret * secret_count
    api_cost = (api_calls / 10000) * per_10k_api

    return round(secret_cost + api_cost, 2)
