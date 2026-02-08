"""
functions/analyzers/cost/pricing/cloudwatch.py - CloudWatch Logs 가격 조회

CloudWatch Logs 비용 계산:
- Storage: ~$0.03/GB/월 (리전별 상이)
- Ingestion: ~$0.50/GB

PricingService를 사용하여 캐시와 API를 통합 관리합니다.

사용법:
    from functions.analyzers.cost.pricing import get_cloudwatch_storage_price, get_cloudwatch_monthly_cost

    # GB당 월 저장 비용
    per_gb = get_cloudwatch_storage_price("ap-northeast-2")

    # 100GB 로그 월간 저장 비용
    monthly = get_cloudwatch_monthly_cost("ap-northeast-2", storage_gb=100)
"""

from __future__ import annotations

import logging

from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_cloudwatch_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """CloudWatch Logs 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {"storage_per_gb_monthly": float, "ingestion_per_gb": float}
    """
    return pricing_service.get_prices("cloudwatch", region, refresh)


def get_cloudwatch_storage_price(region: str = "ap-northeast-2") -> float:
    """CloudWatch Logs Storage GB당 월 가격

    Args:
        region: AWS 리전

    Returns:
        GB당 월간 USD
    """
    prices = get_cloudwatch_prices(region)
    return prices.get("storage_per_gb_monthly", 0.03)


def get_cloudwatch_ingestion_price(region: str = "ap-northeast-2") -> float:
    """CloudWatch Logs Ingestion GB당 가격

    Args:
        region: AWS 리전

    Returns:
        GB당 USD
    """
    prices = get_cloudwatch_prices(region)
    return prices.get("ingestion_per_gb", 0.50)


def get_cloudwatch_monthly_cost(
    region: str = "ap-northeast-2",
    storage_gb: float = 0.0,
    ingestion_gb: float = 0.0,
) -> float:
    """CloudWatch Logs 월간 비용 계산

    Args:
        region: AWS 리전
        storage_gb: 저장된 로그 크기 (GB)
        ingestion_gb: 수집된 로그 크기 (GB)

    Returns:
        월간 USD 비용
    """
    prices = get_cloudwatch_prices(region)
    storage_price = prices.get("storage_per_gb_monthly", 0.03)
    ingestion_price = prices.get("ingestion_per_gb", 0.50)

    storage_cost = storage_price * storage_gb
    ingestion_cost = ingestion_price * ingestion_gb

    return round(storage_cost + ingestion_cost, 2)
