"""
core/shared/aws/pricing/ecr.py - Amazon ECR 스토리지 가격 조회

ECR(Elastic Container Registry) 이미지 스토리지 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

비용 구조:
    - Storage: ~$0.10/GB/월 (리전별 상이)
    - Data Transfer: 별도 청구 (이 모듈에서는 미포함)

사용법:
    from core.shared.aws.pricing.ecr import get_ecr_storage_price, get_ecr_monthly_cost

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
    """ECR 스토리지 가격을 조회한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        가격 딕셔너리::

            {"storage_per_gb_monthly": float}  # GB당 월간 USD
    """
    return pricing_service.get_prices("ecr", region, refresh)


def get_ecr_storage_price(region: str = "ap-northeast-2") -> float:
    """ECR 이미지 스토리지 GB당 월간 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        GB당 월간 USD (기본값: ``0.10``)
    """
    prices = get_ecr_prices(region)
    return prices.get("storage_per_gb_monthly", 0.10)


def get_ecr_monthly_cost(
    region: str = "ap-northeast-2",
    storage_gb: float = 0.0,
) -> float:
    """ECR 이미지 스토리지의 월간 비용을 계산한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        storage_gb: 저장된 컨테이너 이미지 총 크기 (GB, 기본: ``0.0``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    per_gb = get_ecr_storage_price(region)
    return round(per_gb * storage_gb, 2)
