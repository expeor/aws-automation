"""
plugins/cost/pricing/elasticache.py - Amazon ElastiCache 가격 조회

ElastiCache 비용 계산:
- 노드 시간당 비용 (인스턴스 타입별)
- Redis/Memcached 동일 가격

사용법:
    from plugins.cost.pricing.elasticache import get_elasticache_monthly_cost

    # 월간 비용
    monthly = get_elasticache_monthly_cost("ap-northeast-2", "cache.r6g.large", num_nodes=2)
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

# ElastiCache 노드 타입별 시간당 가격 (USD) - 2025년 기준
# https://aws.amazon.com/elasticache/pricing/
ELASTICACHE_PRICES: dict[str, dict[str, float]] = {
    "ap-northeast-2": {
        "cache.t3.micro": 0.018,
        "cache.t3.small": 0.036,
        "cache.t3.medium": 0.073,
        "cache.m6g.large": 0.154,
        "cache.m6g.xlarge": 0.308,
        "cache.m6g.2xlarge": 0.617,
        "cache.r6g.large": 0.207,
        "cache.r6g.xlarge": 0.413,
        "cache.r6g.2xlarge": 0.826,
        "cache.r7g.large": 0.218,
        "cache.r7g.xlarge": 0.435,
    },
    "us-east-1": {
        "cache.t3.micro": 0.017,
        "cache.t3.small": 0.034,
        "cache.t3.medium": 0.068,
        "cache.m6g.large": 0.145,
        "cache.m6g.xlarge": 0.290,
        "cache.m6g.2xlarge": 0.581,
        "cache.r6g.large": 0.195,
        "cache.r6g.xlarge": 0.389,
        "cache.r6g.2xlarge": 0.778,
        "cache.r7g.large": 0.205,
        "cache.r7g.xlarge": 0.410,
    },
}

DEFAULT_NODE_PRICE = 0.20  # 알 수 없는 노드 타입용 기본값


def get_elasticache_prices_from_api(session: boto3.Session, region: str) -> dict[str, float]:
    """Pricing API를 통해 ElastiCache 가격 조회"""
    try:
        pricing = get_client(session, "pricing", region_name=PRICING_API_REGION)
        response = pricing.get_products(
            ServiceCode="AmazonElastiCache",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Cache Instance"},
            ],
            MaxResults=100,
        )

        prices: dict[str, float] = {}

        for price_item in response.get("PriceList", []):
            data = json.loads(price_item) if isinstance(price_item, str) else price_item
            attrs = data.get("product", {}).get("attributes", {})
            terms = data.get("terms", {}).get("OnDemand", {})

            instance_type = attrs.get("instanceType", "")
            if not instance_type:
                continue

            # cache. 접두사 추가
            if not instance_type.startswith("cache."):
                instance_type = f"cache.{instance_type}"

            for term in terms.values():
                for dim in term.get("priceDimensions", {}).values():
                    price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    if price > 0:
                        prices[instance_type] = price
                        break

        if prices:
            logger.info(f"ElastiCache 가격 조회 완료 (API): {region} ({len(prices)} types)")
            return prices

    except (ClientError, BotoCoreError) as e:
        logger.debug(f"ElastiCache 가격 API 조회 실패 [{region}]: {e}")

    return {}


def get_elasticache_prices(region: str = "ap-northeast-2", session: boto3.Session | None = None) -> dict[str, float]:
    """ElastiCache 가격 조회"""
    if session:
        api_prices = get_elasticache_prices_from_api(session, region)
        if api_prices:
            return api_prices

    return ELASTICACHE_PRICES.get(region, ELASTICACHE_PRICES.get("us-east-1", {}))


def get_elasticache_hourly_price(
    region: str = "ap-northeast-2",
    node_type: str = "cache.t3.medium",
    session: boto3.Session | None = None,
) -> float:
    """ElastiCache 노드 시간당 가격"""
    prices = get_elasticache_prices(region, session)
    return prices.get(node_type, DEFAULT_NODE_PRICE)


def get_elasticache_monthly_cost(
    region: str = "ap-northeast-2",
    node_type: str = "cache.t3.medium",
    num_nodes: int = 1,
    session: boto3.Session | None = None,
) -> float:
    """ElastiCache 월간 비용 계산"""
    hourly_price = get_elasticache_hourly_price(region, node_type, session)
    return round(hourly_price * HOURS_PER_MONTH * num_nodes, 2)
