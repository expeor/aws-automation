"""
plugins/cost/pricing/ami.py - Amazon AMI 가격 조회

AMI 비용 계산:
- AMI 자체는 무료, 스냅샷 스토리지 비용만 발생
- EBS Snapshot 가격 기반 계산

사용법:
    from analyzers.cost.pricing.ami import get_ami_monthly_cost

    # 월간 비용 (스냅샷 기반)
    monthly = get_ami_monthly_cost("ap-northeast-2", total_snapshot_gb=50)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .snapshot import get_snapshot_price

if TYPE_CHECKING:
    import boto3

logger = logging.getLogger(__name__)


def get_ami_snapshot_price(
    region: str = "ap-northeast-2",
    session: boto3.Session | None = None,  # noqa: ARG001
) -> float:
    """AMI 스냅샷 GB당 월 가격 (EBS Snapshot 가격과 동일)"""
    return get_snapshot_price(region)


def get_ami_monthly_cost(
    region: str = "ap-northeast-2",
    total_snapshot_gb: float = 0,
    session: boto3.Session | None = None,
) -> float:
    """AMI 월간 비용 계산

    Args:
        region: AWS 리전
        total_snapshot_gb: AMI에 포함된 총 스냅샷 크기 (GB)
        session: boto3 세션

    Returns:
        월간 USD 비용
    """
    price = get_ami_snapshot_price(region, session)
    return round(total_snapshot_gb * price, 2)


def estimate_savings(
    amis: list[dict],
    region: str = "ap-northeast-2",
    months: int = 12,
    session: boto3.Session | None = None,
) -> dict[str, float | int | str]:
    """AMI 제거 시 예상 절감액 계산

    Args:
        amis: AMI 목록 [{"snapshot_gb": 50}, ...]
        region: AWS 리전
        months: 계산 기간 (개월)
        session: boto3 세션

    Returns:
        절감액 정보 딕셔너리
    """
    total_snapshot_gb = sum(ami.get("snapshot_gb", 0) for ami in amis)
    monthly_total = get_ami_monthly_cost(region, total_snapshot_gb, session)
    annual_total = monthly_total * months

    return {
        "monthly_total": round(monthly_total, 2),
        "annual_total": round(annual_total, 2),
        "ami_count": len(amis),
        "total_snapshot_gb": total_snapshot_gb,
        "region": region,
    }
