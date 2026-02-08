"""
functions/analyzers/cost/pricing/rds_snapshot.py - RDS Snapshot 가격 조회

RDS Snapshot 비용 계산:
- RDS: ~$0.02/GB/월 (리전별 상이)
- Aurora: ~$0.021/GB/월 (리전별 상이)

PricingService를 사용하여 캐시와 API를 통합 관리합니다.

사용법:
    from functions.analyzers.cost.pricing import get_rds_snapshot_price, get_rds_snapshot_monthly_cost

    # RDS 스냅샷 GB당 월 가격
    per_gb = get_rds_snapshot_price("ap-northeast-2")

    # Aurora 스냅샷 100GB 월간 비용
    monthly = get_rds_snapshot_monthly_cost("ap-northeast-2", size_gb=100, is_aurora=True)
"""

from __future__ import annotations

import logging

from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_rds_snapshot_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """RDS Snapshot 가격 조회

    Args:
        region: AWS 리전
        refresh: 캐시 무시

    Returns:
        {"rds_per_gb_monthly": float, "aurora_per_gb_monthly": float}
    """
    return pricing_service.get_prices("rds_snapshot", region, refresh)


def get_rds_snapshot_price(
    region: str = "ap-northeast-2",
    is_aurora: bool = False,
) -> float:
    """RDS Snapshot GB당 월 가격

    Args:
        region: AWS 리전
        is_aurora: Aurora 여부

    Returns:
        GB당 월간 USD
    """
    prices = get_rds_snapshot_prices(region)
    if is_aurora:
        return prices.get("aurora_per_gb_monthly", 0.021)
    return prices.get("rds_per_gb_monthly", 0.02)


def get_rds_snapshot_monthly_cost(
    region: str = "ap-northeast-2",
    size_gb: float = 0.0,
    is_aurora: bool = False,
) -> float:
    """RDS Snapshot 월간 비용 계산

    Args:
        region: AWS 리전
        size_gb: 스냅샷 크기 (GB)
        is_aurora: Aurora 여부

    Returns:
        월간 USD 비용
    """
    per_gb = get_rds_snapshot_price(region, is_aurora)
    return round(per_gb * size_gb, 2)
