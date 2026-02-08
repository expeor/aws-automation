"""
core/shared/aws/pricing/route53.py - Amazon Route53 가격 조회

Route53 Hosted Zone 보유 비용과 DNS 쿼리 비용을 조회한다.
Route53은 글로벌 서비스이므로 리전 파라미터 없이 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

비용 구조:
    - Hosted Zone: $0.50/월 (첫 25개), $0.10/월 (26개 이상)
    - DNS Query: $0.40 / 100만 쿼리 (Standard)

사용법:
    from core.shared.aws.pricing.route53 import get_hosted_zone_monthly_cost

    # Hosted Zone 1개 월간 비용
    monthly = get_hosted_zone_monthly_cost()

    # 30개 Zone 월간 비용 (25개 * $0.50 + 5개 * $0.10)
    total = get_hosted_zone_monthly_cost(zone_count=30)
"""

from __future__ import annotations

import logging

from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_route53_prices(refresh: bool = False) -> dict[str, float]:
    """Route53 Hosted Zone/쿼리 가격을 조회한다 (글로벌 서비스).

    Route53은 리전이 없으므로 내부적으로 ``"global"`` 키를 사용한다.

    Args:
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {
                "hosted_zone_monthly": float,       # 첫 25개 Zone 월간 USD
                "additional_zone_monthly": float,    # 26번째 이후 Zone 월간 USD
                "query_per_million": float,          # 100만 쿼리당 USD
            }
    """
    # Route53는 글로벌 서비스 - "global" 키 사용
    return pricing_service.get_prices("route53", "global", refresh)


def get_hosted_zone_price(zone_index: int = 1) -> float:
    """Hosted Zone 1개의 월간 가격을 순번에 따라 반환한다.

    Args:
        zone_index: Zone 순번 (1-25: $0.50, 26 이상: $0.10)

    Returns:
        해당 순번 Zone의 월간 USD
    """
    prices = get_route53_prices()
    if zone_index <= 25:
        return prices.get("hosted_zone_monthly", 0.50)
    return prices.get("additional_zone_monthly", 0.10)


def get_query_price() -> float:
    """DNS Standard 쿼리 100만건당 가격을 반환한다.

    Returns:
        100만 쿼리당 USD (기본값: ``0.40``)
    """
    prices = get_route53_prices()
    return prices.get("query_per_million", 0.40)


def get_hosted_zone_monthly_cost(zone_count: int = 1) -> float:
    """Route53 Hosted Zone 보유의 월간 총 비용을 계산한다.

    첫 25개는 $0.50/월, 26번째부터는 $0.10/월로 계산한다.

    Args:
        zone_count: Hosted Zone 개수 (기본: ``1``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    prices = get_route53_prices()
    first_25_price = prices.get("hosted_zone_monthly", 0.50)
    additional_price = prices.get("additional_zone_monthly", 0.10)

    if zone_count <= 25:
        return round(first_25_price * zone_count, 2)

    # 첫 25개 + 추가분
    first_cost = first_25_price * 25
    additional_cost = additional_price * (zone_count - 25)
    return round(first_cost + additional_cost, 2)


def get_query_monthly_cost(queries_millions: float = 0.0) -> float:
    """DNS 쿼리의 월간 비용을 계산한다.

    Args:
        queries_millions: 월간 쿼리 수 (백만 단위, 기본: ``0.0``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    per_million = get_query_price()
    return round(per_million * queries_millions, 2)
