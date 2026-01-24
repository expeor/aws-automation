"""
plugins/cost/pricing/fsx.py - Amazon FSx 가격 조회

FSx 비용 계산:
- Windows File Server: GB당 월 $0.013 (SSD)
- Lustre: GB당 월 $0.14 (Persistent SSD)
- ONTAP: GB당 월 $0.024 (Primary storage)
- OpenZFS: GB당 월 $0.09 (SSD)

사용법:
    from plugins.cost.pricing.fsx import get_fsx_gb_price, get_fsx_monthly_cost

    # GB당 월 가격
    price = get_fsx_gb_price("ap-northeast-2", "WINDOWS")

    # 월간 비용
    monthly = get_fsx_monthly_cost("ap-northeast-2", "WINDOWS", storage_gb=1000)
"""

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

# FSx 타입별 리전별 가격 (USD per GB-month) - 2025년 기준 폴백
# https://aws.amazon.com/fsx/pricing/
FSX_PRICES: dict[str, dict[str, dict[str, float]]] = {
    # Windows File Server
    "WINDOWS": {
        "ap-northeast-2": {"ssd": 0.013, "hdd": 0.006},
        "ap-northeast-1": {"ssd": 0.013, "hdd": 0.006},
        "us-east-1": {"ssd": 0.013, "hdd": 0.006},
        "us-west-2": {"ssd": 0.013, "hdd": 0.006},
        "eu-west-1": {"ssd": 0.013, "hdd": 0.006},
        "eu-central-1": {"ssd": 0.013, "hdd": 0.006},
    },
    # Lustre
    "LUSTRE": {
        "ap-northeast-2": {"ssd": 0.14, "hdd": 0.012},
        "ap-northeast-1": {"ssd": 0.14, "hdd": 0.012},
        "us-east-1": {"ssd": 0.14, "hdd": 0.012},
        "us-west-2": {"ssd": 0.14, "hdd": 0.012},
        "eu-west-1": {"ssd": 0.14, "hdd": 0.012},
        "eu-central-1": {"ssd": 0.14, "hdd": 0.012},
    },
    # NetApp ONTAP
    "ONTAP": {
        "ap-northeast-2": {"ssd": 0.024, "capacity": 0.0125},
        "ap-northeast-1": {"ssd": 0.024, "capacity": 0.0125},
        "us-east-1": {"ssd": 0.024, "capacity": 0.0125},
        "us-west-2": {"ssd": 0.024, "capacity": 0.0125},
        "eu-west-1": {"ssd": 0.024, "capacity": 0.0125},
        "eu-central-1": {"ssd": 0.024, "capacity": 0.0125},
    },
    # OpenZFS
    "OPENZFS": {
        "ap-northeast-2": {"ssd": 0.09},
        "ap-northeast-1": {"ssd": 0.09},
        "us-east-1": {"ssd": 0.09},
        "us-west-2": {"ssd": 0.09},
        "eu-west-1": {"ssd": 0.09},
        "eu-central-1": {"ssd": 0.09},
    },
}

# 기본 가격 (알 수 없는 리전용)
DEFAULT_PRICES = {
    "WINDOWS": {"ssd": 0.013, "hdd": 0.006},
    "LUSTRE": {"ssd": 0.14, "hdd": 0.012},
    "ONTAP": {"ssd": 0.024, "capacity": 0.0125},
    "OPENZFS": {"ssd": 0.09},
}


def get_fsx_prices_from_api(session: "boto3.Session", region: str, fsx_type: str) -> dict[str, float]:
    """Pricing API를 통해 FSx 가격 조회

    Args:
        session: boto3 세션
        region: 대상 리전
        fsx_type: FSx 타입 (WINDOWS, LUSTRE, ONTAP, OPENZFS)

    Returns:
        {"ssd": float, "hdd": float, ...}
    """
    try:
        pricing = get_client(session, "pricing", region_name=PRICING_API_REGION)

        # 서비스 코드 매핑
        service_codes = {
            "WINDOWS": "AmazonFSx",
            "LUSTRE": "AmazonFSx",
            "ONTAP": "AmazonFSx",
            "OPENZFS": "AmazonFSx",
        }

        service_code = service_codes.get(fsx_type.upper(), "AmazonFSx")

        response = pricing.get_products(
            ServiceCode=service_code,
            Filters=[
                {"Type": "TERM_MATCH", "Field": "regionCode", "Value": region},
                {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"},
            ],
            MaxResults=50,
        )

        prices: dict[str, float] = {}

        for price_item in response.get("PriceList", []):
            data = json.loads(price_item) if isinstance(price_item, str) else price_item
            attrs = data.get("product", {}).get("attributes", {})
            terms = data.get("terms", {}).get("OnDemand", {})

            usage_type = attrs.get("usagetype", "").lower()
            file_system_type = attrs.get("fileSystemType", "").upper()
            storage_type = attrs.get("storageType", "").lower()

            # FSx 타입 필터링
            if fsx_type.upper() not in file_system_type and fsx_type.upper() != "WINDOWS":
                continue

            for term in terms.values():
                for dim in term.get("priceDimensions", {}).values():
                    price = float(dim.get("pricePerUnit", {}).get("USD", "0"))
                    if price > 0:
                        if "ssd" in storage_type or "ssd" in usage_type:
                            prices["ssd"] = price
                        elif "hdd" in storage_type or "hdd" in usage_type:
                            prices["hdd"] = price
                        elif "capacity" in storage_type:
                            prices["capacity"] = price

        if prices:
            logger.info(f"FSx 가격 조회 완료 (API): {region} - {fsx_type}")
            return prices

    except (ClientError, BotoCoreError) as e:
        logger.debug(f"FSx 가격 API 조회 실패 [{region}]: {e}")

    return {}


def get_fsx_prices(
    region: str = "ap-northeast-2",
    fsx_type: str = "WINDOWS",
    session: "boto3.Session | None" = None,
) -> dict[str, float]:
    """FSx 가격 조회

    Args:
        region: AWS 리전
        fsx_type: FSx 타입 (WINDOWS, LUSTRE, ONTAP, OPENZFS)
        session: boto3 세션 (API 조회용)

    Returns:
        {"ssd": float, "hdd": float, ...}
    """
    fsx_type = fsx_type.upper()

    # API로 조회 시도
    if session:
        api_prices = get_fsx_prices_from_api(session, region, fsx_type)
        if api_prices:
            return api_prices

    # 폴백: 하드코딩된 가격
    type_prices = FSX_PRICES.get(fsx_type)
    if type_prices:
        return type_prices.get(region, DEFAULT_PRICES.get(fsx_type, {"ssd": 0.10}))
    return DEFAULT_PRICES.get(fsx_type, {"ssd": 0.10})


def get_fsx_gb_price(
    region: str = "ap-northeast-2",
    fsx_type: str = "WINDOWS",
    storage_type: str = "SSD",
    session: "boto3.Session | None" = None,
) -> float:
    """FSx GB당 월 가격

    Args:
        region: AWS 리전
        fsx_type: FSx 타입 (WINDOWS, LUSTRE, ONTAP, OPENZFS)
        storage_type: 스토리지 타입 (SSD, HDD)
        session: boto3 세션

    Returns:
        GB당 월간 USD
    """
    prices = get_fsx_prices(region, fsx_type, session)
    storage_key = storage_type.lower()

    # SSD가 기본, 없으면 첫 번째 가격
    if storage_key in prices:
        return prices[storage_key]
    return next(iter(prices.values()), 0.10)


def get_fsx_monthly_cost(
    region: str = "ap-northeast-2",
    fsx_type: str = "WINDOWS",
    storage_gb: int = 0,
    storage_type: str = "SSD",
    session: "boto3.Session | None" = None,
) -> float:
    """FSx 월간 비용 계산

    Args:
        region: AWS 리전
        fsx_type: FSx 타입 (WINDOWS, LUSTRE, ONTAP, OPENZFS)
        storage_gb: 스토리지 용량 (GB)
        storage_type: 스토리지 타입 (SSD, HDD)
        session: boto3 세션

    Returns:
        월간 USD 비용
    """
    gb_price = get_fsx_gb_price(region, fsx_type, storage_type, session)
    return round(storage_gb * gb_price, 2)


def estimate_savings(
    filesystems: list[dict],
    region: str = "ap-northeast-2",
    months: int = 12,
    session: "boto3.Session | None" = None,
) -> dict[str, float | int | str]:
    """FSx 파일시스템 제거 시 예상 절감액 계산

    Args:
        filesystems: 파일시스템 목록 [{"type": "WINDOWS", "storage_gb": 1000, "storage_type": "SSD"}, ...]
        region: AWS 리전
        months: 계산 기간 (개월)
        session: boto3 세션

    Returns:
        절감액 정보 딕셔너리
    """
    monthly_total = 0.0
    total_storage_gb = 0

    for fs in filesystems:
        fsx_type = fs.get("type", "WINDOWS")
        storage_gb = fs.get("storage_gb", 0)
        storage_type = fs.get("storage_type", "SSD")

        monthly_total += get_fsx_monthly_cost(region, fsx_type, storage_gb, storage_type, session)
        total_storage_gb += storage_gb

    annual_total = monthly_total * months

    return {
        "monthly_total": round(monthly_total, 2),
        "annual_total": round(annual_total, 2),
        "filesystem_count": len(filesystems),
        "total_storage_gb": total_storage_gb,
        "region": region,
    }
