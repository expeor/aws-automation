"""
plugins/cost/pricing/redshift.py - Amazon Redshift 가격 조회

Redshift 비용 계산:
- 노드 시간당 비용 (타입별)
- Managed Storage (RA3 노드용)

사용법:
    from analyzers.cost.pricing.redshift import get_redshift_monthly_cost

    # 월간 비용
    monthly = get_redshift_monthly_cost("ap-northeast-2", "ra3.xlplus", num_nodes=2)
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

# Redshift 노드 타입별 시간당 가격 (USD) - 2025년 기준
# https://aws.amazon.com/redshift/pricing/
REDSHIFT_PRICES: dict[str, dict[str, float]] = {
    "ap-northeast-2": {
        "dc2.large": 0.25,
        "dc2.8xlarge": 4.80,
        "ra3.xlplus": 1.086,
        "ra3.4xlarge": 3.26,
        "ra3.16xlarge": 13.04,
        "ds2.xlarge": 0.85,
        "ds2.8xlarge": 6.80,
    },
    "us-east-1": {
        "dc2.large": 0.25,
        "dc2.8xlarge": 4.80,
        "ra3.xlplus": 1.086,
        "ra3.4xlarge": 3.26,
        "ra3.16xlarge": 13.04,
        "ds2.xlarge": 0.85,
        "ds2.8xlarge": 6.80,
    },
    "ap-northeast-1": {
        "dc2.large": 0.314,
        "dc2.8xlarge": 6.029,
        "ra3.xlplus": 1.358,
        "ra3.4xlarge": 4.074,
        "ra3.16xlarge": 16.296,
        "ds2.xlarge": 1.063,
        "ds2.8xlarge": 8.50,
    },
}

# RA3 Managed Storage 가격 (GB당 월)
REDSHIFT_MANAGED_STORAGE_PRICES: dict[str, float] = {
    "ap-northeast-2": 0.024,
    "us-east-1": 0.024,
    "ap-northeast-1": 0.030,
}

DEFAULT_NODE_PRICE = 1.00
DEFAULT_STORAGE_PRICE = 0.024


def get_redshift_prices_from_api(session: boto3.Session, region: str) -> dict[str, float]:
    """Pricing API를 통해 Redshift 가격 조회"""
    try:
        pricing = get_client(session, "pricing", region_name=PRICING_API_REGION)
        response = pricing.get_products(
            ServiceCode="AmazonRedshift",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
            ],
            MaxResults=50,
        )

        prices: dict[str, float] = {}

        for price_item in response.get("PriceList", []):
            data = json.loads(price_item) if isinstance(price_item, str) else price_item
            attrs = data.get("product", {}).get("attributes", {})
            terms = data.get("terms", {}).get("OnDemand", {})

            node_type = attrs.get("instanceType", "")
            usage_type = attrs.get("usagetype", "").lower()

            for term in terms.values():
                for dim in term.get("priceDimensions", {}).values():
                    price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    if price > 0:
                        if node_type:
                            prices[node_type] = price
                        elif "rms" in usage_type or "storage" in usage_type:
                            prices["managed_storage"] = price

        if prices:
            logger.info(f"Redshift 가격 조회 완료 (API): {region}")
            return prices

    except (ClientError, BotoCoreError) as e:
        logger.debug(f"Redshift 가격 API 조회 실패 [{region}]: {e}")

    return {}


def get_redshift_prices(
    region: str = "ap-northeast-2",
    session: boto3.Session | None = None,
) -> dict[str, float]:
    """Redshift 가격 조회"""
    if session:
        api_prices = get_redshift_prices_from_api(session, region)
        if api_prices:
            return api_prices

    return REDSHIFT_PRICES.get(region, REDSHIFT_PRICES.get("us-east-1", {}))


def get_redshift_node_price(
    region: str = "ap-northeast-2",
    node_type: str = "dc2.large",
    session: boto3.Session | None = None,
) -> float:
    """Redshift 노드 시간당 가격"""
    prices = get_redshift_prices(region, session)
    return prices.get(node_type, DEFAULT_NODE_PRICE)


def get_redshift_storage_price(
    region: str = "ap-northeast-2",
    session: boto3.Session | None = None,
) -> float:
    """Redshift Managed Storage GB당 월 가격 (RA3 노드용)"""
    if session:
        api_prices = get_redshift_prices_from_api(session, region)
        if api_prices and "managed_storage" in api_prices:
            return api_prices["managed_storage"]

    return REDSHIFT_MANAGED_STORAGE_PRICES.get(region, DEFAULT_STORAGE_PRICE)


def get_redshift_monthly_cost(
    region: str = "ap-northeast-2",
    node_type: str = "dc2.large",
    num_nodes: int = 1,
    managed_storage_gb: int = 0,
    session: boto3.Session | None = None,
) -> float:
    """Redshift 월간 비용 계산

    Args:
        region: AWS 리전
        node_type: 노드 타입 (dc2.large, ra3.xlplus 등)
        num_nodes: 노드 수
        managed_storage_gb: Managed Storage 용량 (RA3 노드용)
        session: boto3 세션

    Returns:
        월간 USD 비용
    """
    node_hourly = get_redshift_node_price(region, node_type, session)
    storage_monthly = get_redshift_storage_price(region, session)

    node_cost = node_hourly * HOURS_PER_MONTH * num_nodes

    # RA3 노드의 경우 Managed Storage 비용 추가
    storage_cost = 0.0
    if node_type.startswith("ra3") and managed_storage_gb > 0:
        storage_cost = managed_storage_gb * storage_monthly

    return round(node_cost + storage_cost, 2)
