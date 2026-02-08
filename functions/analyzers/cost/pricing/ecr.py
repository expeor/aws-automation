"""
plugins/cost/pricing/ecr.py - ECR 가격 조회

ECR 비용 계산:
- Storage: ~$0.10/GB/월 (리전별 상이)
- Data Transfer: 별도 청구

PricingService를 사용하여 캐시와 API를 통합 관리합니다.

사용법:
    from functions.analyzers.cost.pricing import get_ecr_storage_price, get_ecr_monthly_cost

    # GB당 월 저장 비용
    per_gb = get_ecr_storage_price("ap-northeast-2")

    # 100GB 이미지 월간 비용
    monthly = get_ecr_monthly_cost("ap-northeast-2", storage_gb=100)
"""

from __future__ import annotations

import logging

from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_ecr_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """ECR 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {"storage_per_gb_monthly": float}
    """
    return pricing_service.get_prices("ecr", region, refresh)


def get_ecr_storage_price(region: str = "ap-northeast-2") -> float:
    """ECR Storage GB당 월 가격

    Args:
        region: AWS 리전

    Returns:
        GB당 월간 USD
    """
    prices = get_ecr_prices(region)
    return prices.get("storage_per_gb_monthly", 0.10)


def get_ecr_monthly_cost(
    region: str = "ap-northeast-2",
    storage_gb: float = 0.0,
) -> float:
    """ECR 월간 비용 계산

    Args:
        region: AWS 리전
        storage_gb: 저장된 이미지 크기 (GB)

    Returns:
        월간 USD 비용
    """
    per_gb = get_ecr_storage_price(region)
    return round(per_gb * storage_gb, 2)
