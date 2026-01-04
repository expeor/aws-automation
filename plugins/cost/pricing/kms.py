"""
plugins/cost/pricing/kms.py - KMS 가격 조회

KMS 비용 계산:
- Customer Managed Key: ~$1.00/월 (리전별 상이)
- AWS Managed Key: 무료 (AWS 서비스가 생성)
- API 요청: ~$0.03/10,000 requests

사용법:
    from plugins.cost.pricing import get_kms_key_monthly_cost

    # Customer Managed Key 월간 비용
    monthly = get_kms_key_monthly_cost("ap-northeast-2")

    # 여러 Key의 월간 비용
    total = get_kms_key_monthly_cost("ap-northeast-2", key_count=5)
"""

import logging

from .cache import PriceCache
from .fetcher import PricingFetcher

logger = logging.getLogger(__name__)

# 모듈 레벨 캐시
_cache = PriceCache()


def get_kms_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """KMS 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {"customer_key_monthly": float, "per_10k_requests": float}
    """
    return _get_cached_prices(region, refresh)


def get_kms_key_price(
    region: str = "ap-northeast-2",
    key_type: str = "CUSTOMER",
) -> float:
    """KMS Key 월간 가격

    Args:
        region: AWS 리전
        key_type: CUSTOMER 또는 AWS (AWS Managed는 무료)

    Returns:
        월간 USD
    """
    if key_type.upper() == "AWS":
        return 0.0

    prices = get_kms_prices(region)
    return prices.get("customer_key_monthly", 1.0)


def get_kms_request_price(region: str = "ap-northeast-2") -> float:
    """KMS API 요청 10,000건당 가격

    Args:
        region: AWS 리전

    Returns:
        10,000건당 USD
    """
    prices = get_kms_prices(region)
    return prices.get("per_10k_requests", 0.03)


def get_kms_key_monthly_cost(
    region: str = "ap-northeast-2",
    key_count: int = 1,
    key_type: str = "CUSTOMER",
    requests: int = 0,
) -> float:
    """KMS 월간 비용 계산

    Args:
        region: AWS 리전
        key_count: Key 개수
        key_type: CUSTOMER 또는 AWS
        requests: API 요청 수

    Returns:
        월간 USD 비용
    """
    # AWS Managed Key는 무료
    if key_type.upper() == "AWS":
        key_cost = 0.0
    else:
        prices = get_kms_prices(region)
        per_key = prices.get("customer_key_monthly", 1.0)
        key_cost = per_key * key_count

    # 요청 비용
    request_price = get_kms_request_price(region)
    request_cost = (requests / 10000) * request_price

    return round(key_cost + request_cost, 2)


def _get_cached_prices(region: str, refresh: bool = False) -> dict[str, float]:
    """캐시된 가격 조회 (없으면 API 호출)"""
    if not refresh:
        cached = _cache.get("kms", region)
        if cached:
            return cached

    # API로 가격 조회
    try:
        fetcher = PricingFetcher()
        prices = fetcher.get_kms_prices(region)

        if prices and prices.get("customer_key_monthly", 0) > 0:
            _cache.set("kms", region, prices)
            return prices

    except Exception as e:
        logger.warning(f"KMS 가격 조회 실패: {e}")

    # 기본값 반환
    return {"customer_key_monthly": 1.0, "per_10k_requests": 0.03}
