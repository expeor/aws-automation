"""
plugins/cost/pricing/efs.py - Amazon EFS 가격 조회

EFS 비용 계산:
- Standard Storage: GB당 월 $0.30
- Infrequent Access: GB당 월 $0.016
- Throughput: 추가 비용 (Provisioned 모드)

사용법:
    from plugins.cost.pricing.efs import get_efs_monthly_cost

    # 월간 비용
    monthly = get_efs_monthly_cost("ap-northeast-2", storage_gb=100)
"""

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


def get_efs_prices_from_api(session: "boto3.Session", region: str) -> dict[str, float]:
    """Pricing API를 통해 EFS 가격 조회"""
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


def get_efs_prices(region: str = "ap-northeast-2", session: "boto3.Session | None" = None) -> dict[str, float]:
    """EFS 가격 조회"""
    if session:
        api_prices = get_efs_prices_from_api(session, region)
        if api_prices:
            return api_prices

    return EFS_PRICES.get(region, DEFAULT_PRICES)


def get_efs_storage_price(
    region: str = "ap-northeast-2",
    storage_class: str = "standard",
    session: "boto3.Session | None" = None,
) -> float:
    """EFS GB당 월 가격"""
    prices = get_efs_prices(region, session)
    return prices.get(storage_class.lower(), prices.get("standard", 0.30))


def get_efs_monthly_cost(
    region: str = "ap-northeast-2",
    storage_gb: float = 0,
    storage_class: str = "standard",
    session: "boto3.Session | None" = None,
) -> float:
    """EFS 월간 비용 계산"""
    price = get_efs_storage_price(region, storage_class, session)
    return round(storage_gb * price, 2)
