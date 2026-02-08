"""
core/shared/aws/pricing/cloudwatch.py - CloudWatch Logs 가격 조회

CloudWatch Logs의 저장(Storage) 및 수집(Ingestion) 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

비용 구조:
    - Storage: ~$0.03/GB/월 (리전별 상이)
    - Ingestion: ~$0.50/GB (리전별 상이)

사용법:
    from core.shared.aws.pricing.cloudwatch import (
        get_cloudwatch_storage_price,
        get_cloudwatch_monthly_cost,
    )

    # GB당 월 저장 비용
    per_gb = get_cloudwatch_storage_price("ap-northeast-2")

    # 100GB 로그 월간 저장 + 10GB 수집 비용
    monthly = get_cloudwatch_monthly_cost(
        "ap-northeast-2", storage_gb=100, ingestion_gb=10
    )
"""

from __future__ import annotations

import logging

from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_cloudwatch_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """CloudWatch Logs 저장/수집 가격을 조회한다.

    ``PricingService`` 를 통해 캐시 우선 조회하며, 캐시 미스 시 API를 호출한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {
                "storage_per_gb_monthly": float,  # 저장 GB당 월간 USD
                "ingestion_per_gb": float,         # 수집 GB당 USD
            }
    """
    return pricing_service.get_prices("cloudwatch", region, refresh)


def get_cloudwatch_storage_price(region: str = "ap-northeast-2") -> float:
    """CloudWatch Logs 저장 스토리지의 GB당 월간 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        GB당 월간 USD (기본값: ``0.03``)
    """
    prices = get_cloudwatch_prices(region)
    return prices.get("storage_per_gb_monthly", 0.03)


def get_cloudwatch_ingestion_price(region: str = "ap-northeast-2") -> float:
    """CloudWatch Logs 수집(Ingestion) GB당 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        수집 GB당 USD (기본값: ``0.50``)
    """
    prices = get_cloudwatch_prices(region)
    return prices.get("ingestion_per_gb", 0.50)


def get_cloudwatch_monthly_cost(
    region: str = "ap-northeast-2",
    storage_gb: float = 0.0,
    ingestion_gb: float = 0.0,
) -> float:
    """CloudWatch Logs 월간 총 비용을 계산한다.

    ``(storage_gb * 저장 단가) + (ingestion_gb * 수집 단가)`` 로 산출한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        storage_gb: 저장된 로그 총 크기 (GB, 기본: ``0.0``)
        ingestion_gb: 당월 수집된 로그 크기 (GB, 기본: ``0.0``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    prices = get_cloudwatch_prices(region)
    storage_price = prices.get("storage_per_gb_monthly", 0.03)
    ingestion_price = prices.get("ingestion_per_gb", 0.50)

    storage_cost = storage_price * storage_gb
    ingestion_cost = ingestion_price * ingestion_gb

    return round(storage_cost + ingestion_cost, 2)
