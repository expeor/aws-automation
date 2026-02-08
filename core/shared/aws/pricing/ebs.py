"""
core/shared/aws/pricing/ebs.py - Amazon EBS 볼륨 가격 조회

EBS 볼륨 타입별 GB당 월간 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.

지원 볼륨 타입:
    gp2, gp3, io1, io2, st1, sc1, standard (Magnetic)

사용법:
    from core.shared.aws.pricing.ebs import get_ebs_price, get_ebs_monthly_cost

    # gp3 GB당 월 가격
    price_per_gb = get_ebs_price("gp3", "ap-northeast-2")

    # 100GB gp3 볼륨 월간 비용
    monthly = get_ebs_monthly_cost("gp3", 100, "ap-northeast-2")
"""

from __future__ import annotations

import logging

from .utils import pricing_service

logger = logging.getLogger(__name__)


def get_ebs_price(
    volume_type: str,
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> float:
    """EBS 볼륨 타입의 GB당 월간 가격을 조회한다.

    Args:
        volume_type: EBS 볼륨 타입 (``"gp2"``, ``"gp3"``, ``"io1"``,
            ``"io2"``, ``"st1"``, ``"sc1"``, ``"standard"``)
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        GB당 월간 USD 가격. 가격 정보가 없으면 ``0.0``
    """
    prices = pricing_service.get_prices("ebs", region, refresh)

    if volume_type in prices:
        return prices[volume_type]

    # 가격 정보 없음
    logger.debug(f"EBS 가격 정보 없음: {volume_type}/{region}")
    return 0.0


def get_ebs_monthly_cost(
    volume_type: str,
    size_gb: int,
    region: str = "ap-northeast-2",
) -> float:
    """EBS 볼륨의 월간 스토리지 비용을 계산한다.

    ``size_gb * get_ebs_price()`` 로 산출한다. IOPS/Throughput 추가 비용은 미포함.

    Args:
        volume_type: EBS 볼륨 타입 (예: ``"gp3"``)
        size_gb: 볼륨 크기 (GB)
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    price_per_gb = get_ebs_price(volume_type, region)
    return round(price_per_gb * size_gb, 2)


def get_ebs_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """리전의 모든 EBS 볼륨 타입 가격을 조회한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        ``{volume_type: gb_monthly_price}`` 딕셔너리 (예: ``{"gp3": 0.08, "gp2": 0.10}``)
    """
    return pricing_service.get_prices("ebs", region, refresh)


# 하위 호환성을 위한 alias
get_ebs_prices_bulk = get_ebs_prices
