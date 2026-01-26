"""
plugins/cost/pricing/transfer.py - AWS Transfer Family 가격 조회

Transfer Family 비용 계산:
- 프로토콜 엔드포인트 시간당 비용: $0.30/hour (SFTP, FTPS, FTP, AS2)

사용법:
    from plugins.cost.pricing.transfer import get_transfer_hourly_price, get_transfer_monthly_cost

    # 시간당 가격
    hourly = get_transfer_hourly_price("ap-northeast-2")

    # 월간 비용
    monthly = get_transfer_monthly_cost("ap-northeast-2", protocols=["SFTP", "FTPS"])
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

# Pricing API 리전
PRICING_API_REGION = "us-east-1"

# Transfer Family 리전별 가격 (USD) - 2025년 기준 폴백
# https://aws.amazon.com/aws-transfer-family/pricing/
TRANSFER_PRICES: dict[str, dict[str, float]] = {
    # Asia Pacific
    "ap-northeast-2": {"hourly": 0.30},  # 서울
    "ap-northeast-1": {"hourly": 0.30},  # 도쿄
    "ap-northeast-3": {"hourly": 0.30},  # 오사카
    "ap-southeast-1": {"hourly": 0.30},  # 싱가포르
    "ap-southeast-2": {"hourly": 0.30},  # 시드니
    "ap-south-1": {"hourly": 0.30},  # 뭄바이
    "ap-east-1": {"hourly": 0.30},  # 홍콩
    # US
    "us-east-1": {"hourly": 0.30},  # 버지니아
    "us-east-2": {"hourly": 0.30},  # 오하이오
    "us-west-1": {"hourly": 0.30},  # 캘리포니아
    "us-west-2": {"hourly": 0.30},  # 오레곤
    # Europe
    "eu-west-1": {"hourly": 0.30},  # 아일랜드
    "eu-west-2": {"hourly": 0.30},  # 런던
    "eu-west-3": {"hourly": 0.30},  # 파리
    "eu-central-1": {"hourly": 0.30},  # 프랑크푸르트
    "eu-north-1": {"hourly": 0.30},  # 스톡홀름
    # Others
    "sa-east-1": {"hourly": 0.30},  # 상파울루
    "ca-central-1": {"hourly": 0.30},  # 캐나다
    "me-south-1": {"hourly": 0.30},  # 바레인
    "af-south-1": {"hourly": 0.30},  # 케이프타운
}

# 기본 가격 (알 수 없는 리전용)
DEFAULT_PRICES = {"hourly": 0.30}

# 월 평균 시간 (24 * 30)
HOURS_PER_MONTH = 730


def get_transfer_prices_from_api(session: boto3.Session, region: str) -> dict[str, float]:
    """Pricing API를 통해 Transfer Family 가격 조회

    Args:
        session: boto3 세션
        region: 대상 리전

    Returns:
        {"hourly": float}
    """
    try:
        pricing = get_client(session, "pricing", region_name=PRICING_API_REGION)
        response = pricing.get_products(
            ServiceCode="AWSTransfer",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
            ],
            MaxResults=20,
        )

        prices = {"hourly": 0.0}

        for price_item in response.get("PriceList", []):
            data = json.loads(price_item) if isinstance(price_item, str) else price_item
            attrs = data.get("product", {}).get("attributes", {})
            terms = data.get("terms", {}).get("OnDemand", {})

            usage_type = attrs.get("usagetype", "").lower()

            for term in terms.values():
                for dim in term.get("priceDimensions", {}).values():
                    unit = dim.get("unit", "").lower()
                    price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    if price > 0 and ("hr" in unit or "hour" in unit):
                        # 프로토콜 엔드포인트 시간당 가격
                        if "endpoint" in usage_type or "server" in usage_type:
                            prices["hourly"] = price
                            break

        if prices["hourly"] > 0:
            logger.info(f"Transfer Family 가격 조회 완료 (API): {region}")
            return prices

    except (ClientError, BotoCoreError) as e:
        logger.debug(f"Transfer Family 가격 API 조회 실패 [{region}]: {e}")

    return {}


def get_transfer_prices(region: str = "ap-northeast-2", session: boto3.Session | None = None) -> dict[str, float]:
    """Transfer Family 가격 조회

    Args:
        region: AWS 리전
        session: boto3 세션 (API 조회용)

    Returns:
        {"hourly": float}
    """
    # API로 조회 시도
    if session:
        api_prices = get_transfer_prices_from_api(session, region)
        if api_prices and api_prices.get("hourly", 0) > 0:
            return api_prices

    # 폴백: 하드코딩된 가격
    return TRANSFER_PRICES.get(region, DEFAULT_PRICES)


def get_transfer_hourly_price(region: str = "ap-northeast-2", session: boto3.Session | None = None) -> float:
    """Transfer Family 프로토콜 엔드포인트 시간당 가격

    Args:
        region: AWS 리전
        session: boto3 세션

    Returns:
        시간당 USD
    """
    prices = get_transfer_prices(region, session)
    return prices["hourly"]


def get_transfer_monthly_cost(
    region: str = "ap-northeast-2",
    protocols: list[str] | None = None,
    hours: int = HOURS_PER_MONTH,
    session: boto3.Session | None = None,
) -> float:
    """Transfer Family 월간 비용 계산

    Args:
        region: AWS 리전
        protocols: 프로토콜 목록 (SFTP, FTPS, FTP, AS2)
        hours: 가동 시간 (기본: 730시간 = 한 달)
        session: boto3 세션

    Returns:
        월간 USD 비용
    """
    hourly_price = get_transfer_hourly_price(region, session)
    protocol_count = len(protocols) if protocols else 1

    # 각 프로토콜 엔드포인트별로 과금
    return round(hourly_price * hours * protocol_count, 2)


def estimate_savings(
    server_count: int,
    region: str = "ap-northeast-2",
    protocols_per_server: int = 1,
    months: int = 12,
    session: boto3.Session | None = None,
) -> dict[str, float | int | str]:
    """Transfer Family 서버 제거 시 예상 절감액 계산

    Args:
        server_count: 서버 개수
        region: AWS 리전
        protocols_per_server: 서버당 프로토콜 수
        months: 계산 기간 (개월)
        session: boto3 세션

    Returns:
        절감액 정보 딕셔너리
    """
    hourly_price = get_transfer_hourly_price(region, session)
    monthly_per_server = hourly_price * HOURS_PER_MONTH * protocols_per_server
    monthly_total = monthly_per_server * server_count
    annual_total = monthly_total * months

    return {
        "monthly_per_server": round(monthly_per_server, 2),
        "monthly_total": round(monthly_total, 2),
        "annual_total": round(annual_total, 2),
        "server_count": server_count,
        "region": region,
    }
