"""
functions/analyzers/cost/pricing/kinesis.py - Amazon Kinesis Data Streams 가격 조회

Kinesis 비용 계산:
- Provisioned: Shard-hour당 $0.015
- On-Demand: 스트림당 시간 + 데이터 비용
- Extended Retention: 추가 비용

사용법:
    from functions.analyzers.cost.pricing.kinesis import get_kinesis_monthly_cost

    # Provisioned 모드 월간 비용
    monthly = get_kinesis_monthly_cost("ap-northeast-2", shard_count=4)

    # On-Demand 모드 월간 비용
    monthly = get_kinesis_monthly_cost("ap-northeast-2", mode="ON_DEMAND")
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

# Kinesis Data Streams 리전별 가격 (USD) - 2025년 기준
# https://aws.amazon.com/kinesis/data-streams/pricing/
KINESIS_PRICES: dict[str, dict[str, float]] = {
    "ap-northeast-2": {
        "shard_hour": 0.015,  # Provisioned shard-hour
        "put_payload_unit": 0.014,  # PUT Payload Units (25KB units) per million
        "extended_retention_hour": 0.020,  # Extended retention per shard-hour
        "on_demand_stream_hour": 0.04,  # On-Demand stream-hour
        "on_demand_data_in_gb": 0.08,  # On-Demand data ingested per GB
        "on_demand_data_out_gb": 0.04,  # On-Demand data retrieved per GB
    },
    "us-east-1": {
        "shard_hour": 0.015,
        "put_payload_unit": 0.014,
        "extended_retention_hour": 0.020,
        "on_demand_stream_hour": 0.04,
        "on_demand_data_in_gb": 0.08,
        "on_demand_data_out_gb": 0.04,
    },
    "ap-northeast-1": {
        "shard_hour": 0.0195,
        "put_payload_unit": 0.0182,
        "extended_retention_hour": 0.026,
        "on_demand_stream_hour": 0.052,
        "on_demand_data_in_gb": 0.104,
        "on_demand_data_out_gb": 0.052,
    },
}

DEFAULT_PRICES = {
    "shard_hour": 0.015,
    "put_payload_unit": 0.014,
    "extended_retention_hour": 0.020,
    "on_demand_stream_hour": 0.04,
    "on_demand_data_in_gb": 0.08,
    "on_demand_data_out_gb": 0.04,
}


def get_kinesis_prices_from_api(session: boto3.Session, region: str) -> dict[str, float]:
    """AWS Pricing API를 통해 Kinesis Data Streams 가격 조회

    Shard-hour, PUT payload, extended retention 가격을 조회합니다.
    API에서 조회된 값은 DEFAULT_PRICES에 병합됩니다.

    Args:
        session: boto3 Session 객체
        region: 가격을 조회할 AWS 리전 코드

    Returns:
        가격 항목별 딕셔너리 (USD).
        조회 실패 시 빈 딕셔너리.
    """
    try:
        pricing = get_client(session, "pricing", region_name=PRICING_API_REGION)
        response = pricing.get_products(
            ServiceCode="AmazonKinesis",
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

            usage_type = attrs.get("usagetype", "").lower()

            for term in terms.values():
                for dim in term.get("priceDimensions", {}).values():
                    price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    if price > 0:
                        if "shard" in usage_type and "hour" in usage_type:
                            prices["shard_hour"] = price
                        elif "payload" in usage_type:
                            prices["put_payload_unit"] = price
                        elif "extended" in usage_type:
                            prices["extended_retention_hour"] = price

        if prices:
            logger.info(f"Kinesis 가격 조회 완료 (API): {region}")
            return {**DEFAULT_PRICES, **prices}

    except (ClientError, BotoCoreError) as e:
        logger.debug(f"Kinesis 가격 API 조회 실패 [{region}]: {e}")

    return {}


def get_kinesis_prices(region: str = "ap-northeast-2", session: boto3.Session | None = None) -> dict[str, float]:
    """Kinesis Data Streams 가격 항목별 조회

    API 조회 실패 시 하드코딩된 기본값을 반환합니다.

    Args:
        region: AWS 리전 코드
        session: boto3 Session (None이면 API 조회 생략)

    Returns:
        가격 항목별 딕셔너리 (USD).
        키: shard_hour, put_payload_unit, extended_retention_hour,
        on_demand_stream_hour, on_demand_data_in_gb, on_demand_data_out_gb
    """
    if session:
        api_prices = get_kinesis_prices_from_api(session, region)
        if api_prices:
            return api_prices

    return KINESIS_PRICES.get(region, DEFAULT_PRICES)


def get_kinesis_shard_hour_price(
    region: str = "ap-northeast-2",
    session: boto3.Session | None = None,
) -> float:
    """Kinesis Provisioned 모드 Shard-hour 가격 조회

    Args:
        region: AWS 리전 코드
        session: boto3 Session (None이면 API 조회 생략)

    Returns:
        Shard-hour당 가격 (USD)
    """
    prices = get_kinesis_prices(region, session)
    return prices.get("shard_hour", 0.015)


def get_kinesis_monthly_cost(
    region: str = "ap-northeast-2",
    shard_count: int = 1,
    mode: str = "PROVISIONED",
    extended_retention_hours: int = 0,
    session: boto3.Session | None = None,
) -> float:
    """Kinesis 월간 비용 계산

    Args:
        region: AWS 리전
        shard_count: Shard 수 (Provisioned 모드)
        mode: PROVISIONED 또는 ON_DEMAND
        extended_retention_hours: 기본 24시간 초과 보존 시간
        session: boto3 세션

    Returns:
        월간 USD 비용
    """
    prices = get_kinesis_prices(region, session)

    if mode.upper() == "ON_DEMAND":
        # On-Demand: 스트림당 시간 비용만 (데이터 비용은 사용량에 따라)
        stream_cost = prices.get("on_demand_stream_hour", 0.04) * HOURS_PER_MONTH
        return round(stream_cost, 2)
    else:
        # Provisioned: Shard-hour 비용
        shard_cost = prices.get("shard_hour", 0.015) * HOURS_PER_MONTH * shard_count

        # Extended retention 비용 (24시간 초과분)
        extended_cost = 0.0
        if extended_retention_hours > 0:
            extended_cost = prices.get("extended_retention_hour", 0.020) * extended_retention_hours * shard_count

        return round(shard_cost + extended_cost, 2)
