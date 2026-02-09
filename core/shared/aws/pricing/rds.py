"""
core/shared/aws/pricing/rds.py - Amazon RDS 인스턴스 가격 조회

RDS 인스턴스 클래스별/엔진별 시간당 비용과 스토리지 비용을 조회한다.
Pricing API 직접 호출 후, 실패 시 하드코딩 가격(MySQL 기준)으로 fallback한다.

비용 구조:
    - 인스턴스: 클래스/엔진별 시간당 비용
    - 스토리지: 타입별 GB당 월간 비용 (gp2, gp3, io1, magnetic)
    - Multi-AZ: 인스턴스 + 스토리지 비용 2배

사용법:
    from core.shared.aws.pricing.rds import get_rds_monthly_cost

    # MySQL db.r6g.large Multi-AZ + 100GB gp3 월간 비용
    monthly = get_rds_monthly_cost(
        "ap-northeast-2",
        instance_class="db.r6g.large",
        engine="mysql",
        storage_gb=100,
        multi_az=True,
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

# RDS 인스턴스 클래스별 시간당 가격 (USD, MySQL 기준) - 2025년 기준
# https://aws.amazon.com/rds/pricing/
RDS_INSTANCE_PRICES: dict[str, dict[str, float]] = {
    "ap-northeast-2": {
        "db.t3.micro": 0.018,
        "db.t3.small": 0.036,
        "db.t3.medium": 0.073,
        "db.t3.large": 0.146,
        "db.m6g.large": 0.178,
        "db.m6g.xlarge": 0.356,
        "db.m6g.2xlarge": 0.712,
        "db.r6g.large": 0.240,
        "db.r6g.xlarge": 0.480,
        "db.r6g.2xlarge": 0.960,
        "db.r7g.large": 0.252,
        "db.r7g.xlarge": 0.504,
    },
    "us-east-1": {
        "db.t3.micro": 0.017,
        "db.t3.small": 0.034,
        "db.t3.medium": 0.068,
        "db.t3.large": 0.136,
        "db.m6g.large": 0.166,
        "db.m6g.xlarge": 0.332,
        "db.m6g.2xlarge": 0.664,
        "db.r6g.large": 0.228,
        "db.r6g.xlarge": 0.456,
        "db.r6g.2xlarge": 0.912,
        "db.r7g.large": 0.240,
        "db.r7g.xlarge": 0.480,
    },
}

# RDS 스토리지 가격 (GB당 월)
RDS_STORAGE_PRICES: dict[str, dict[str, float]] = {
    "ap-northeast-2": {"gp2": 0.115, "gp3": 0.095, "io1": 0.125, "magnetic": 0.10},
    "us-east-1": {"gp2": 0.115, "gp3": 0.095, "io1": 0.125, "magnetic": 0.10},
}

DEFAULT_INSTANCE_PRICE = 0.20
DEFAULT_STORAGE_PRICES = {"gp2": 0.115, "gp3": 0.095, "io1": 0.125, "magnetic": 0.10}


def get_rds_prices_from_api(session: boto3.Session, region: str, engine: str = "mysql") -> dict[str, float]:
    """AWS Pricing API를 통해 RDS 인스턴스 클래스별 가격을 조회한다.

    엔진 이름을 Pricing API 필터값으로 변환한다 (postgres -> PostgreSQL 등).
    ``db.`` 접두사가 없는 인스턴스 타입에는 자동으로 추가한다.

    Args:
        session: boto3 세션
        region: 대상 AWS 리전 코드
        engine: DB 엔진 (``"mysql"``, ``"postgres"``, ``"oracle"``, ``"sqlserver"``)

    Returns:
        ``{instance_class: hourly_price}`` 딕셔너리. 조회 실패 시 빈 딕셔너리.
    """
    try:
        pricing = get_client(session, "pricing", region_name=PRICING_API_REGION)

        # 엔진별 필터
        engine_filter = engine.lower()
        if "postgres" in engine_filter:
            engine_filter = "PostgreSQL"
        elif "mysql" in engine_filter or "maria" in engine_filter:
            engine_filter = "MySQL"
        elif "oracle" in engine_filter:
            engine_filter = "Oracle"
        elif "sqlserver" in engine_filter:
            engine_filter = "SQL Server"
        else:
            engine_filter = "MySQL"  # 기본값

        response = pricing.get_products(
            ServiceCode="AmazonRDS",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": engine_filter},
                {"Type": "TERM_MATCH", "Field": "deploymentOption", "Value": "Single-AZ"},
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

            # db. 접두사 추가
            if not instance_type.startswith("db."):
                instance_type = f"db.{instance_type}"

            for term in terms.values():
                for dim in term.get("priceDimensions", {}).values():
                    price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    if price > 0:
                        prices[instance_type] = price
                        break

        if prices:
            logger.info(f"RDS 가격 조회 완료 (API): {region} ({len(prices)} types)")
            return prices

    except (ClientError, BotoCoreError) as e:
        logger.debug(f"RDS 가격 API 조회 실패 [{region}]: {e}")

    return {}


def get_rds_prices(
    region: str = "ap-northeast-2",
    engine: str = "mysql",
    session: boto3.Session | None = None,
) -> dict[str, float]:
    """RDS 인스턴스 클래스별 가격을 조회한다.

    ``session`` 이 제공되면 Pricing API를 우선 호출하고,
    실패 시 하드코딩된 ``RDS_INSTANCE_PRICES`` 에서 fallback한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        engine: DB 엔진 (기본: ``"mysql"``)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        ``{instance_class: hourly_price}`` 딕셔너리
    """
    if session:
        api_prices = get_rds_prices_from_api(session, region, engine)
        if api_prices:
            return api_prices

    return RDS_INSTANCE_PRICES.get(region, RDS_INSTANCE_PRICES.get("us-east-1", {}))


def get_rds_instance_price(
    region: str = "ap-northeast-2",
    instance_class: str = "db.t3.medium",
    engine: str = "mysql",
    session: boto3.Session | None = None,
) -> float:
    """RDS 인스턴스의 시간당 On-Demand 가격을 반환한다 (Single-AZ 기준).

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        instance_class: 인스턴스 클래스 (예: ``"db.t3.medium"``, ``"db.r6g.large"``)
        engine: DB 엔진 (기본: ``"mysql"``)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        시간당 USD (알 수 없는 클래스이면 기본값 ``0.20``)
    """
    prices = get_rds_prices(region, engine, session)
    return prices.get(instance_class, DEFAULT_INSTANCE_PRICE)


def get_rds_storage_price(
    region: str = "ap-northeast-2",
    storage_type: str = "gp3",
) -> float:
    """RDS 스토리지 타입의 GB당 월간 가격을 반환한다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        storage_type: 스토리지 타입 (``"gp2"``, ``"gp3"``, ``"io1"``, ``"magnetic"``)

    Returns:
        GB당 월간 USD (gp3 기본: ``0.095``)
    """
    storage_prices = RDS_STORAGE_PRICES.get(region, DEFAULT_STORAGE_PRICES)
    return storage_prices.get(storage_type, 0.095)


def get_rds_monthly_cost(
    region: str = "ap-northeast-2",
    instance_class: str = "db.t3.medium",
    engine: str = "mysql",
    storage_gb: int = 20,
    storage_type: str = "gp3",
    multi_az: bool = False,
    session: boto3.Session | None = None,
) -> float:
    """RDS 인스턴스 + 스토리지의 월간 총 비용을 계산한다.

    Multi-AZ 배포 시 인스턴스와 스토리지 비용이 모두 2배가 된다.

    Args:
        region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
        instance_class: 인스턴스 클래스 (기본: ``"db.t3.medium"``)
        engine: DB 엔진 (기본: ``"mysql"``)
        storage_gb: 스토리지 크기 (GB, 기본: ``20``)
        storage_type: 스토리지 타입 (기본: ``"gp3"``)
        multi_az: Multi-AZ 배포 여부 (기본: ``False``, ``True`` 이면 2배)
        session: boto3 세션 (API 조회용, 선택 사항)

    Returns:
        월간 USD 비용 (소수점 2자리 반올림)
    """
    instance_hourly = get_rds_instance_price(region, instance_class, engine, session)
    storage_monthly = get_rds_storage_price(region, storage_type)

    # Multi-AZ는 2배 비용
    multiplier = 2 if multi_az else 1

    instance_cost = instance_hourly * HOURS_PER_MONTH * multiplier
    storage_cost = storage_gb * storage_monthly * multiplier

    return round(instance_cost + storage_cost, 2)
