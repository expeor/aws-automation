"""
plugins/cost/pricing/route53.py - Route53 가격 조회

Route53 비용 계산 (글로벌 서비스):
- Hosted Zone: $0.50/월 (첫 25개), $0.10/월 (추가)
- DNS Query: $0.40/백만 쿼리 (Standard)

사용법:
    from plugins.cost.pricing import get_hosted_zone_monthly_cost

    # Hosted Zone 하나의 월간 비용
    monthly = get_hosted_zone_monthly_cost()

    # 여러 Zone의 월간 비용
    total = get_hosted_zone_monthly_cost(zone_count=30)
"""

import logging

from .cache import PriceCache
from .fetcher import PricingFetcher

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_cache = PriceCache()


def get_route53_prices(refresh: bool = False) -> dict[str, float]:
    """Route53 가격 조회 (글로벌 서비스)

    Args:
        refresh: 캐시 무시

    Returns:
        {"hosted_zone_monthly": float, "additional_zone_monthly": float, "query_per_million": float}
    """
    return _get_cached_prices(refresh)


def get_hosted_zone_price(zone_index: int = 1) -> float:
    """Hosted Zone 월간 가격

    Args:
        zone_index: Zone 순번 (1-25: $0.50, 26+: $0.10)

    Returns:
        월간 USD
    """
    prices = get_route53_prices()
    if zone_index <= 25:
        return prices.get("hosted_zone_monthly", 0.50)
    return prices.get("additional_zone_monthly", 0.10)


def get_query_price() -> float:
    """DNS 쿼리 백만건당 가격

    Returns:
        백만건당 USD
    """
    prices = get_route53_prices()
    return prices.get("query_per_million", 0.40)


def get_hosted_zone_monthly_cost(zone_count: int = 1) -> float:
    """Route53 Hosted Zone 월간 비용 계산

    Args:
        zone_count: Zone 개수

    Returns:
        월간 USD 비용
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
    """DNS 쿼리 월간 비용 계산

    Args:
        queries_millions: 쿼리 수 (백만 단위)

    Returns:
        월간 USD 비용
    """
    per_million = get_query_price()
    return round(per_million * queries_millions, 2)


def _get_cached_prices(refresh: bool = False) -> dict[str, float]:
    """캐시된 가격 조회 (없으면 API 호출)"""
    # Route53는 글로벌 서비스 - "global" 키 사용
    if not refresh:
        cached = _cache.get("route53", "global")
        if cached:
            return cached

    # API로 가격 조회
    try:
        fetcher = PricingFetcher()
        prices = fetcher.get_route53_prices()

        if prices and prices.get("hosted_zone_monthly", 0) > 0:
            _cache.set("route53", "global", prices)
            return prices

    except Exception as e:
        logger.warning(f"Route53 가격 조회 실패: {e}")

    # 기본값 반환
    return {
        "hosted_zone_monthly": 0.50,
        "additional_zone_monthly": 0.10,
        "query_per_million": 0.40,
    }
