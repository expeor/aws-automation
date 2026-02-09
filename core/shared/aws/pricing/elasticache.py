"""
core/shared/aws/pricing/elasticache.py - Amazon ElastiCache 가격 조회

ElastiCache 노드 타입별 시간당/월간 비용을 조회한다.
Pricing API 직접 호출 후, 실패 시 하드코딩 가격으로 fallback한다.
Redis와 Memcached는 동일 노드 타입이면 동일 가격이다.

사용법:
    from core.shared.aws.pricing.elasticache import get_elasticache_monthly_cost

    # cache.r6g.large 2노드 월간 비용
    monthly = get_elasticache_monthly_cost(
        "ap-northeast-2", "cache.r6g.large", num_nodes=2
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

from .constants import HOURS_PER_MONTH

PRICING_API_REGION = "us-east-1"

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
    """AWS Pricing API를 통해 ElastiCache 노드 타입별 가격을 조회한다.

    ``cache.`` 접두사가 없는 인스턴스 타입에는 자동으로 추가한다.

    Args:
        session: boto3 세션
        region: 대상 AWS 리전 코드

    Returns:
        ``{node_type: hourly_price}`` 딕셔너리. 조회 실패 시 빈 딕셔너리.
    """
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
    """ElastiCache 노드 타입별 가격을 조회한다.

    ``session`` 이 제공되면 Pricing API를 우선 호출하고,
    실패 시 하드코딩된 ``ELASTICACHE_PRICES`` 에서 fallback한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        ``{node_type: hourly_price}`` 딕셔너리 (예: ``{"cache.r6g.large": 0.207}``)
    """
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
    """ElastiCache 노드의 시간당 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        node_type: 노드 타입 (예: ``"cache.t3.medium"``, ``"cache.r6g.large"``)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        시간당 USD (알 수 없는 노드 타입이면 기본값 ``0.20``)
    """
    prices = get_elasticache_prices(region, session)
    return prices.get(node_type, DEFAULT_NODE_PRICE)


def get_elasticache_monthly_cost(
    region: str = "ap-northeast-2",
    node_type: str = "cache.t3.medium",
    num_nodes: int = 1,
    session: boto3.Session | None = None,
) -> float:
    """ElastiCache 클러스터의 월간 비용을 계산한다.

    ``hourly_price * 730시간 * num_nodes`` 로 산출한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        node_type: 노드 타입 (예: ``"cache.r6g.large"``)
        num_nodes: 노드 수 (기본: ``1``)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    hourly_price = get_elasticache_hourly_price(region, node_type, session)
    return round(hourly_price * HOURS_PER_MONTH * num_nodes, 2)
