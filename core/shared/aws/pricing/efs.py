"""
core/shared/aws/pricing/efs.py - Amazon EFS 가격 조회

EFS(Elastic File System) Storage Class별 GB당 월간 비용을 조회한다.
Pricing API 직접 호출 후, 실패 시 하드코딩 가격으로 fallback한다.

비용 구조 (ap-northeast-2 기준):
    - Standard: $0.30/GB/월
    - Infrequent Access (IA): $0.016/GB/월
    - Archive: $0.008/GB/월
    - Throughput: Provisioned 모드 시 추가 비용 (이 모듈에서 미포함)

사용법:
    from core.shared.aws.pricing.efs import get_efs_monthly_cost

    # Standard 100GB 월간 비용
    monthly = get_efs_monthly_cost("ap-northeast-2", storage_gb=100)

    # IA 500GB 월간 비용
    monthly = get_efs_monthly_cost("ap-northeast-2", storage_gb=500, storage_class="ia")
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from botocore.exceptions import BotoCoreError, ClientError

from core.parallel import get_client

if TYPE_CHECKING:
    import boto3

logger = logging.getLogger(__name__)

PRICING_API_REGION = "us-east-1"

# EFS 리전별 가격 (USD per GB-month) - 2025년 기준
# https://aws.amazon.com/efs/pricing/
EFS_PRICES: dict[str, dict[str, float]] = {
    "ap-northeast-2": {"standard": 0.30, "ia": 0.016, "archive": 0.008},
    "ap-northeast-1": {"standard": 0.30, "ia": 0.016, "archive": 0.008},
    "ap-southeast-1": {"standard": 0.30, "ia": 0.016, "archive": 0.008},
    "us-east-1": {"standard": 0.30, "ia": 0.016, "archive": 0.008},
    "us-west-2": {"standard": 0.30, "ia": 0.016, "archive": 0.008},
    "eu-west-1": {"standard": 0.30, "ia": 0.016, "archive": 0.008},
    "eu-central-1": {"standard": 0.30, "ia": 0.016, "archive": 0.008},
}

DEFAULT_PRICES = {"standard": 0.30, "ia": 0.016, "archive": 0.008}


def get_efs_prices_from_api(session: boto3.Session, region: str) -> dict[str, float]:
    """AWS Pricing API를 통해 EFS Storage Class별 가격을 조회한다.

    Args:
        session: boto3 세션
        region: 대상 AWS 리전 코드

    Returns:
        Storage Class별 GB당 월간 가격 딕셔너리 (예: ``{"standard": 0.30, "ia": 0.016}``).
        조회 실패 시 빈 딕셔너리.
    """
    try:
        pricing = get_client(session, "pricing", region_name=PRICING_API_REGION)
        response = pricing.get_products(
            ServiceCode="AmazonEFS",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
            ],
            MaxResults=30,
        )

        prices: dict[str, float] = {}

        for price_item in response.get("PriceList", []):
            data = json.loads(price_item) if isinstance(price_item, str) else price_item
            attrs = data.get("product", {}).get("attributes", {})
            terms = data.get("terms", {}).get("OnDemand", {})

            storage_class = attrs.get("storageClass", "").lower()
            usage_type = attrs.get("usagetype", "").lower()

            for term in terms.values():
                for dim in term.get("priceDimensions", {}).values():
                    price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    if price > 0:
                        if "standard" in storage_class or "standard" in usage_type:
                            prices["standard"] = price
                        elif "infrequent" in storage_class or "-ia" in usage_type:
                            prices["ia"] = price
                        elif "archive" in storage_class:
                            prices["archive"] = price

        if prices:
            logger.info(f"EFS 가격 조회 완료 (API): {region}")
            return prices

    except (ClientError, BotoCoreError) as e:
        logger.debug(f"EFS 가격 API 조회 실패 [{region}]: {e}")

    return {}


def get_efs_prices(region: str = "ap-northeast-2", session: boto3.Session | None = None) -> dict[str, float]:
    """EFS Storage Class별 가격을 조회한다.

    ``session`` 이 제공되면 Pricing API를 우선 호출하고,
    실패 시 하드코딩된 ``EFS_PRICES`` 에서 fallback한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        ``{"standard": float, "ia": float, "archive": float}`` 형식의 딕셔너리
    """
    if session:
        api_prices = get_efs_prices_from_api(session, region)
        if api_prices:
            return api_prices

    return EFS_PRICES.get(region, DEFAULT_PRICES)


def get_efs_storage_price(
    region: str = "ap-northeast-2",
    storage_class: str = "standard",
    session: boto3.Session | None = None,
) -> float:
    """EFS 특정 Storage Class의 GB당 월간 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        storage_class: Storage Class (``"standard"``, ``"ia"``, ``"archive"``, 기본: ``"standard"``)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        GB당 월간 USD (Standard 기본: ``0.30``)
    """
    prices = get_efs_prices(region, session)
    return prices.get(storage_class.lower(), prices.get("standard", 0.30))


def get_efs_monthly_cost(
    region: str = "ap-northeast-2",
    storage_gb: float = 0,
    storage_class: str = "standard",
    session: boto3.Session | None = None,
) -> float:
    """EFS 파일시스템의 월간 스토리지 비용을 계산한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        storage_gb: 저장된 데이터 크기 (GB, 기본: ``0``)
        storage_class: Storage Class (``"standard"``, ``"ia"``, ``"archive"``, 기본: ``"standard"``)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    price = get_efs_storage_price(region, storage_class, session)
    return round(storage_gb * price, 2)
