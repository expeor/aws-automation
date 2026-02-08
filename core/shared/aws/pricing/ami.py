"""
core/shared/aws/pricing/ami.py - Amazon AMI 가격 조회

AMI 자체는 무료이며, 비용은 AMI에 포함된 EBS Snapshot의 스토리지에서 발생합니다.
내부적으로 ``snapshot`` 모듈의 ``get_snapshot_price()`` 에 위임합니다.

비용 구조:
    - AMI 등록/보유: 무료
    - 스냅샷 스토리지: ~$0.05/GB/월 (리전별 상이)

사용법:
    from core.shared.aws.pricing.ami import get_ami_monthly_cost

    # 50GB 스냅샷 포함 AMI의 월간 비용
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
    """AMI 스냅샷 GB당 월 가격을 반환한다.

    EBS Snapshot 가격과 동일하며, ``snapshot.get_snapshot_price()`` 에 위임한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        session: boto3 세션 (현재 사용하지 않으나 인터페이스 호환용)

    Returns:
        GB당 월간 USD 가격 (예: ``0.05``)
    """
    return get_snapshot_price(region)


def get_ami_monthly_cost(
    region: str = "ap-northeast-2",
    total_snapshot_gb: float = 0,
    session: boto3.Session | None = None,
) -> float:
    """AMI에 포함된 스냅샷의 월간 스토리지 비용을 계산한다.

    ``total_snapshot_gb * get_ami_snapshot_price()`` 로 산출한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        total_snapshot_gb: AMI에 포함된 총 스냅샷 크기 (GB)
        session: boto3 세션 (가격 API 조회용, 선택 사항)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    price = get_ami_snapshot_price(region, session)
    return round(total_snapshot_gb * price, 2)


def estimate_savings(
    amis: list[dict],
    region: str = "ap-northeast-2",
    months: int = 12,
    session: boto3.Session | None = None,
) -> dict[str, float | int | str]:
    """AMI 목록을 제거했을 때의 예상 절감액을 계산한다.

    각 AMI의 스냅샷 용량을 합산하여 월간/연간 비용 절감액을 산출한다.

    Args:
        amis: AMI 정보 목록. 각 항목은 ``{"snapshot_gb": float}`` 형식의 딕셔너리
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        months: 절감액 계산 기간 (개월, 기본: 12)
        session: boto3 세션 (가격 API 조회용, 선택 사항)

    Returns:
        절감액 정보 딕셔너리::

            {
                "monthly_total": float,      # 월간 절감액 (USD)
                "annual_total": float,        # 기간 합계 절감액 (USD)
                "ami_count": int,             # AMI 개수
                "total_snapshot_gb": float,   # 총 스냅샷 용량 (GB)
                "region": str,               # 리전
            }
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
