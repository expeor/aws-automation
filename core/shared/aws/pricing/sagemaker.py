"""
core/shared/aws/pricing/sagemaker.py - Amazon SageMaker Endpoint 가격 조회

SageMaker Endpoint(Inference) 인스턴스의 시간당/월간 비용을 조회한다.
``PricingService`` 를 통해 캐시/API/fallback을 자동 관리한다.
API 미조회 시 ``constants.py`` 의 기본 가격(50+ 인스턴스 타입)을 사용한다.

사용법:
    from core.shared.aws.pricing.sagemaker import get_sagemaker_price, get_sagemaker_monthly_cost

    # ml.m5.large 시간당 가격
    hourly = get_sagemaker_price("ml.m5.large", "ap-northeast-2")

    # ml.g5.xlarge 2인스턴스 월간 비용
    monthly = get_sagemaker_monthly_cost(
        "ml.g5.xlarge", "ap-northeast-2", instance_count=2
    )
"""

from __future__ import annotations

import logging

from .constants import DEFAULT_PRICES, HOURS_PER_MONTH
from .utils import pricing_service

logger = logging.getLogger(__name__)

# SageMaker 기본 가격 (API 미조회 시 fallback)
_SAGEMAKER_DEFAULT_PRICES = DEFAULT_PRICES.get("sagemaker", {})

# 알 수 없는 인스턴스 타입의 기본 가격
_UNKNOWN_INSTANCE_DEFAULT_PRICE = 0.50


def get_sagemaker_price(
    instance_type: str,
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> float:
    """SageMaker Endpoint 인스턴스의 시간당 가격을 조회한다.

    PricingService 캐시 -> API -> ``constants.DEFAULT_PRICES["sagemaker"]``
    순서로 가격을 찾으며, 모두 실패하면 ``0.50`` 을 반환한다.

    Args:
        instance_type: 인스턴스 타입 (예: ``"ml.m5.large"``, ``"ml.g5.xlarge"``)
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        시간당 USD 가격. 알 수 없는 타입이면 기본값 ``0.50``
    """
    prices = pricing_service.get_prices("sagemaker", region, refresh)

    if instance_type in prices:
        return prices[instance_type]

    # API에서 못 찾으면 기본 가격 맵 확인
    if instance_type in _SAGEMAKER_DEFAULT_PRICES:
        return _SAGEMAKER_DEFAULT_PRICES[instance_type]

    # 가격 정보 없음 - 기본값 반환
    logger.debug(f"SageMaker 가격 정보 없음: {instance_type}/{region}")
    return _UNKNOWN_INSTANCE_DEFAULT_PRICE


def get_sagemaker_monthly_cost(
    instance_type: str,
    region: str = "ap-northeast-2",
    instance_count: int = 1,
    hours_per_month: int = HOURS_PER_MONTH,
) -> float:
    """SageMaker Endpoint의 월간 비용을 계산한다.

    ``hourly_price * hours_per_month * instance_count`` 로 산출한다.

    Args:
        instance_type: 인스턴스 타입 (예: ``"ml.m5.large"``)
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        instance_count: Endpoint 인스턴스 수 (기본: ``1``)
        hours_per_month: 월간 운영 시간 (기본: ``730``)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    hourly = get_sagemaker_price(instance_type, region)
    return round(hourly * hours_per_month * instance_count, 2)


def get_sagemaker_prices(
    region: str = "ap-northeast-2",
    refresh: bool = False,
) -> dict[str, float]:
    """리전의 모든 SageMaker 인스턴스 타입 가격을 조회한다.

    API 결과와 ``constants.DEFAULT_PRICES["sagemaker"]`` 를 병합하여 반환한다
    (API 가격이 우선).

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회

    Returns:
        ``{instance_type: hourly_price}`` 딕셔너리
    """
    prices = pricing_service.get_prices("sagemaker", region, refresh)
    # 기본 가격과 병합 (API 가격 우선)
    return {**_SAGEMAKER_DEFAULT_PRICES, **prices}


# 하위 호환성을 위한 alias
get_sagemaker_prices_bulk = get_sagemaker_prices
