"""
core/shared/aws/pricing/rds_snapshot.py - RDS/Aurora Snapshot 가격 조회

RDS 및 Aurora Snapshot의 GB당 월간 스토리지 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

비용 구조:
    - RDS Snapshot: ~$0.02/GB/월 (리전별 상이)
    - Aurora Snapshot: ~$0.021/GB/월 (리전별 상이)

사용법:
    from core.shared.aws.pricing.rds_snapshot import (
        get_rds_snapshot_price,
        get_rds_snapshot_monthly_cost,
    )

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
    """RDS/Aurora Snapshot 가격을 조회한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {
                "rds_per_gb_monthly": float,     # RDS Snapshot GB당 월간 USD
                "aurora_per_gb_monthly": float,   # Aurora Snapshot GB당 월간 USD
            }
    """
    return pricing_service.get_prices("rds_snapshot", region, refresh)


def get_rds_snapshot_price(
    region: str = "ap-northeast-2",
    is_aurora: bool = False,
) -> float:
    """RDS 또는 Aurora Snapshot의 GB당 월간 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        is_aurora: ``True`` 이면 Aurora 스냅샷 가격, ``False`` 이면 RDS 스냅샷 가격

    Returns:
        GB당 월간 USD (RDS 기본: ``0.02``, Aurora 기본: ``0.021``)
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
    """RDS/Aurora Snapshot의 월간 스토리지 비용을 계산한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        size_gb: 스냅샷 크기 (GB, 기본: ``0.0``)
        is_aurora: ``True`` 이면 Aurora 스냅샷 가격 적용 (기본: ``False``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    per_gb = get_rds_snapshot_price(region, is_aurora)
    return round(per_gb * size_gb, 2)
