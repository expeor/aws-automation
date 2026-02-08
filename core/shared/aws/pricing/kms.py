"""
core/shared/aws/pricing/kms.py - AWS KMS 가격 조회

KMS(Key Management Service) 키 보유 및 API 요청 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

비용 구조:
    - Customer Managed Key(CMK): ~$1.00/월/키 (리전별 상이)
    - AWS Managed Key: 무료 (AWS 서비스가 자동 생성)
    - API 요청: ~$0.03 / 10,000 requests

사용법:
    from core.shared.aws.pricing.kms import get_kms_key_monthly_cost

    # CMK 5개 + API 10만건 월간 비용
    total = get_kms_key_monthly_cost(
        "ap-northeast-2", key_count=5, requests=100_000
    )
"""

from __future__ import annotations

import logging

from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_kms_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """KMS 키 보유 및 API 요청 가격을 조회한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {
                "customer_key_monthly": float,  # CMK 월간 보유 비용 (USD)
                "per_10k_requests": float,       # API 10,000건당 비용 (USD)
            }
    """
    return pricing_service.get_prices("kms", region, refresh)


def get_kms_key_price(
    region: str = "ap-northeast-2",
    key_type: str = "CUSTOMER",
) -> float:
    """KMS 키 1개의 월간 보유 가격을 반환한다.

    AWS Managed Key는 무료(``0.0``)이고, Customer Managed Key만 비용 발생.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        key_type: ``"CUSTOMER"`` (CMK) 또는 ``"AWS"`` (AWS Managed, 무료)

    Returns:
        키 1개 월간 USD (CMK 기본: ``1.0``, AWS Managed: ``0.0``)
    """
    if key_type.upper() == "AWS":
        return 0.0

    prices = get_kms_prices(region)
    return prices.get("customer_key_monthly", 1.0)


def get_kms_request_price(region: str = "ap-northeast-2") -> float:
    """KMS API 요청 10,000건당 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        10,000건당 USD (기본값: ``0.03``)
    """
    prices = get_kms_prices(region)
    return prices.get("per_10k_requests", 0.03)


def get_kms_key_monthly_cost(
    region: str = "ap-northeast-2",
    key_count: int = 1,
    key_type: str = "CUSTOMER",
    requests: int = 0,
) -> float:
    """KMS 키 보유 + API 요청의 월간 총 비용을 계산한다.

    ``(key_price * key_count) + (requests / 10000 * request_price)`` 로 산출한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        key_count: 키 개수 (기본: ``1``)
        key_type: ``"CUSTOMER"`` 또는 ``"AWS"`` (기본: ``"CUSTOMER"``)
        requests: 월간 API 요청 수 (기본: ``0``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
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
