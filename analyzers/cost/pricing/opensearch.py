"""
plugins/cost/pricing/opensearch.py - Amazon OpenSearch Service 가격 조회

OpenSearch 비용 계산:
- 인스턴스 시간당 비용 (타입별)
- EBS 스토리지 비용 (GB당)
- UltraWarm/Cold 스토리지

사용법:
    from analyzers.cost.pricing.opensearch import get_opensearch_monthly_cost

    # 월간 비용
    monthly = get_opensearch_monthly_cost(
        "ap-northeast-2",
        instance_type="r6g.large.search",
        instance_count=2,
        storage_gb=100
    )
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
HOURS_PER_MONTH = 730

# OpenSearch 인스턴스 타입별 시간당 가격 (USD) - 2025년 기준
# https://aws.amazon.com/opensearch-service/pricing/
OPENSEARCH_INSTANCE_PRICES: dict[str, dict[str, float]] = {
    "ap-northeast-2": {
        "t3.small.search": 0.036,
        "t3.medium.search": 0.073,
        "m6g.large.search": 0.128,
        "m6g.xlarge.search": 0.256,
        "m6g.2xlarge.search": 0.512,
        "r6g.large.search": 0.167,
        "r6g.xlarge.search": 0.334,
        "r6g.2xlarge.search": 0.668,
        "c6g.large.search": 0.111,
        "c6g.xlarge.search": 0.223,
    },
    "us-east-1": {
        "t3.small.search": 0.036,
        "t3.medium.search": 0.073,
        "m6g.large.search": 0.128,
        "m6g.xlarge.search": 0.256,
        "m6g.2xlarge.search": 0.512,
        "r6g.large.search": 0.167,
        "r6g.xlarge.search": 0.334,
        "r6g.2xlarge.search": 0.668,
        "c6g.large.search": 0.111,
        "c6g.xlarge.search": 0.223,
    },
}

# OpenSearch EBS 스토리지 가격 (GB당 월)
OPENSEARCH_STORAGE_PRICES: dict[str, float] = {
    "ap-northeast-2": 0.115,
    "us-east-1": 0.115,
    "ap-northeast-1": 0.122,
    "eu-west-1": 0.115,
}

DEFAULT_INSTANCE_PRICE = 0.20
DEFAULT_STORAGE_PRICE = 0.115


def get_opensearch_prices_from_api(session: boto3.Session, region: str) -> dict[str, float]:
    """Pricing API를 통해 OpenSearch 가격 조회"""
    try:
        pricing = get_client(session, "pricing", region_name=PRICING_API_REGION)
        response = pricing.get_products(
            ServiceCode="AmazonES",  # OpenSearch는 여전히 ES 서비스 코드 사용
            Filters=[
                {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
            ],
            MaxResults=100,
        )

        prices: dict[str, float] = {}

        for price_item in response.get("PriceList", []):
            data = json.loads(price_item) if isinstance(price_item, str) else price_item
            attrs = data.get("product", {}).get("attributes", {})
            terms = data.get("terms", {}).get("OnDemand", {})

            instance_type = attrs.get("instanceType", "")
            usage_type = attrs.get("usagetype", "").lower()

            for term in terms.values():
                for dim in term.get("priceDimensions", {}).values():
                    price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    if price > 0:
                        if instance_type:
                            # .search 접미사 추가
                            if not instance_type.endswith(".search"):
                                instance_type = f"{instance_type}.search"
                            prices[instance_type] = price
                        elif "storage" in usage_type or "ebs" in usage_type:
                            prices["storage_gb"] = price

        if prices:
            logger.info(f"OpenSearch 가격 조회 완료 (API): {region}")
            return prices

    except (ClientError, BotoCoreError) as e:
        logger.debug(f"OpenSearch 가격 API 조회 실패 [{region}]: {e}")

    return {}


def get_opensearch_prices(
    region: str = "ap-northeast-2",
    session: boto3.Session | None = None,
) -> dict[str, float]:
    """OpenSearch 가격 조회"""
    if session:
        api_prices = get_opensearch_prices_from_api(session, region)
        if api_prices:
            return api_prices

    return OPENSEARCH_INSTANCE_PRICES.get(region, OPENSEARCH_INSTANCE_PRICES.get("us-east-1", {}))


def get_opensearch_instance_price(
    region: str = "ap-northeast-2",
    instance_type: str = "m6g.large.search",
    session: boto3.Session | None = None,
) -> float:
    """OpenSearch 인스턴스 시간당 가격"""
    prices = get_opensearch_prices(region, session)
    return prices.get(instance_type, DEFAULT_INSTANCE_PRICE)


def get_opensearch_storage_price(
    region: str = "ap-northeast-2",
    session: boto3.Session | None = None,
) -> float:
    """OpenSearch 스토리지 GB당 월 가격"""
    if session:
        api_prices = get_opensearch_prices_from_api(session, region)
        if api_prices and "storage_gb" in api_prices:
            return api_prices["storage_gb"]

    return OPENSEARCH_STORAGE_PRICES.get(region, DEFAULT_STORAGE_PRICE)


def get_opensearch_monthly_cost(
    region: str = "ap-northeast-2",
    instance_type: str = "m6g.large.search",
    instance_count: int = 1,
    storage_gb: int = 0,
    session: boto3.Session | None = None,
) -> float:
    """OpenSearch 월간 비용 계산"""
    instance_hourly = get_opensearch_instance_price(region, instance_type, session)
    storage_monthly = get_opensearch_storage_price(region, session)

    instance_cost = instance_hourly * HOURS_PER_MONTH * instance_count
    storage_cost = storage_gb * storage_monthly * instance_count  # 각 노드별 스토리지

    return round(instance_cost + storage_cost, 2)
