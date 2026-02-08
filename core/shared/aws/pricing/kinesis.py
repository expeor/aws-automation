"""
core/shared/aws/pricing/kinesis.py - Amazon Kinesis Data Streams 가격 조회

Kinesis Data Streams의 Provisioned/On-Demand 모드별 비용을 조회한다.
Pricing API 직접 호출 후, 실패 시 하드코딩 가격으로 fallback한다.

비용 구조 (ap-northeast-2 기준):
    - Provisioned: Shard-hour $0.015
    - On-Demand: Stream-hour $0.04 + 데이터 수집/조회 비용
    - Extended Retention: Shard-hour $0.020 (24시간 초과분)

사용법:
    from core.shared.aws.pricing.kinesis import get_kinesis_monthly_cost

    # Provisioned 4 Shard 월간 비용
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
    """AWS Pricing API를 통해 Kinesis Data Streams 가격을 조회한다.

    Args:
        session: boto3 세션
        region: 대상 AWS 리전 코드

    Returns:
        Shard-hour/Payload/Extended retention 가격 딕셔너리.
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
    """Kinesis Data Streams 가격을 조회한다.

    ``session`` 이 제공되면 Pricing API를 우선 호출하고,
    실패 시 하드코딩된 ``KINESIS_PRICES`` 에서 fallback한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        ``{"shard_hour": float, "put_payload_unit": float, ...}`` 형식의 가격 딕셔너리
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
    """Provisioned 모드 Shard-hour 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        Shard-hour당 USD (기본값: ``0.015``)
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
    """Kinesis Data Streams의 월간 비용을 계산한다.

    Provisioned 모드: ``shard_hour * 730h * shard_count + extended_retention``
    On-Demand 모드: ``stream_hour * 730h`` (데이터 비용은 사용량에 따라 별도)

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        shard_count: Shard 수 (Provisioned 모드, 기본: ``1``)
        mode: ``"PROVISIONED"`` 또는 ``"ON_DEMAND"`` (기본: ``"PROVISIONED"``)
        extended_retention_hours: 24시간 초과 보존 시간 (기본: ``0``)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
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
