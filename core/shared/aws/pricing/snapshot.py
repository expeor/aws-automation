"""
core/shared/aws/pricing/snapshot.py - EBS Snapshot 가격 조회

EBS Snapshot의 GB당 월간 스토리지 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

비용 구조:
    - Storage: ~$0.05/GB/월 (리전별 상이)

사용법:
    from core.shared.aws.pricing.snapshot import get_snapshot_price, get_snapshot_monthly_cost

    # GB당 월 가격
    per_gb = get_snapshot_price("ap-northeast-2")

    # 100GB 스냅샷 월간 비용
    monthly = get_snapshot_monthly_cost("ap-northeast-2", size_gb=100)
"""

from __future__ import annotations

import logging

from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_snapshot_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """EBS Snapshot 스토리지 가격을 조회한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {"storage_per_gb_monthly": float}  # GB당 월간 USD
    """
    return pricing_service.get_prices("snapshot", region, refresh)


def get_snapshot_price(region: str = "ap-northeast-2") -> float:
    """EBS Snapshot GB당 월간 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        GB당 월간 USD (기본값: ``0.05``)
    """
    prices = get_snapshot_prices(region)
    return prices.get("storage_per_gb_monthly", 0.05)


def get_snapshot_monthly_cost(
    region: str = "ap-northeast-2",
    size_gb: float = 0.0,
) -> float:
    """EBS Snapshot의 월간 스토리지 비용을 계산한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        size_gb: 스냅샷 크기 (GB, 기본: ``0.0``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    per_gb = get_snapshot_price(region)
    return round(per_gb * size_gb, 2)
