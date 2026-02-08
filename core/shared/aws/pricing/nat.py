"""
core/pricing/nat.py - NAT Gateway 가격 조회

NAT Gateway 비용 계산:
- 시간당 고정 비용: ~$0.045/hour (리전별 상이)
- 데이터 처리 비용: ~$0.045/GB (리전별 상이)

사용법:
    from core.pricing import get_nat_hourly_price, get_nat_monthly_cost

    # 시간당 가격
    hourly = get_nat_hourly_price("ap-northeast-2")

    # 월간 고정 비용 (가동 시간 기준)
    monthly = get_nat_monthly_cost("ap-northeast-2")

    # 데이터 처리 비용 포함
    total = get_nat_monthly_cost("ap-northeast-2", data_processed_gb=100)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# NAT Gateway 리전별 가격 (USD) - 2025년 기준
# 가격 변동이 드물어 하드코딩 (AWS Price List API 응답 파싱이 복잡함)
# https://aws.amazon.com/vpc/pricing/

NAT_GATEWAY_PRICES: dict[str, dict[str, float]] = {
    # Asia Pacific
    "ap-northeast-2": {"hourly": 0.045, "per_gb": 0.045},  # 서울
    "ap-northeast-1": {"hourly": 0.045, "per_gb": 0.045},  # 도쿄
    "ap-northeast-3": {"hourly": 0.045, "per_gb": 0.045},  # 오사카
    "ap-southeast-1": {"hourly": 0.045, "per_gb": 0.045},  # 싱가포르
    "ap-southeast-2": {"hourly": 0.045, "per_gb": 0.045},  # 시드니
    "ap-south-1": {"hourly": 0.045, "per_gb": 0.045},  # 뭄바이
    "ap-east-1": {"hourly": 0.045, "per_gb": 0.045},  # 홍콩
    # US
    "us-east-1": {"hourly": 0.045, "per_gb": 0.045},  # 버지니아
    "us-east-2": {"hourly": 0.045, "per_gb": 0.045},  # 오하이오
    "us-west-1": {"hourly": 0.045, "per_gb": 0.045},  # 캘리포니아
    "us-west-2": {"hourly": 0.045, "per_gb": 0.045},  # 오레곤
    # Europe
    "eu-west-1": {"hourly": 0.045, "per_gb": 0.045},  # 아일랜드
    "eu-west-2": {"hourly": 0.045, "per_gb": 0.045},  # 런던
    "eu-west-3": {"hourly": 0.045, "per_gb": 0.045},  # 파리
    "eu-central-1": {"hourly": 0.045, "per_gb": 0.045},  # 프랑크푸르트
    "eu-north-1": {"hourly": 0.045, "per_gb": 0.045},  # 스톡홀름
    # Others
    "sa-east-1": {"hourly": 0.045, "per_gb": 0.045},  # 상파울루
    "ca-central-1": {"hourly": 0.045, "per_gb": 0.045},  # 캐나다
    "me-south-1": {"hourly": 0.045, "per_gb": 0.045},  # 바레인
    "af-south-1": {"hourly": 0.045, "per_gb": 0.045},  # 케이프타운
}

# 기본 가격 (알 수 없는 리전용)
DEFAULT_PRICES = {"hourly": 0.045, "per_gb": 0.045}

# 월 평균 시간 (24 * 30)
HOURS_PER_MONTH = 730


def get_nat_prices(region: str = "ap-northeast-2") -> dict[str, float]:
    """NAT Gateway 가격 조회

    Args:
        region: AWS 리전

    Returns:
        {"hourly": float, "per_gb": float}
    """
    return NAT_GATEWAY_PRICES.get(region, DEFAULT_PRICES)


def get_nat_hourly_price(region: str = "ap-northeast-2") -> float:
    """NAT Gateway 시간당 가격

    Args:
        region: AWS 리전

    Returns:
        시간당 USD
    """
    prices = get_nat_prices(region)
    return prices["hourly"]


def get_nat_data_price(region: str = "ap-northeast-2") -> float:
    """NAT Gateway 데이터 처리 GB당 가격

    Args:
        region: AWS 리전

    Returns:
        GB당 USD
    """
    prices = get_nat_prices(region)
    return prices["per_gb"]


def get_nat_monthly_cost(
    region: str = "ap-northeast-2",
    hours: int = HOURS_PER_MONTH,
    data_processed_gb: float = 0.0,
) -> float:
    """NAT Gateway 월간 비용 계산

    Args:
        region: AWS 리전
        hours: 가동 시간 (기본: 730시간 = 한 달)
        data_processed_gb: 처리된 데이터량 (GB)

    Returns:
        월간 USD 비용
    """
    prices = get_nat_prices(region)

    # 고정 비용 (시간당)
    fixed_cost = prices["hourly"] * hours

    # 데이터 처리 비용
    data_cost = prices["per_gb"] * data_processed_gb

    return round(fixed_cost + data_cost, 2)


def get_nat_monthly_fixed_cost(region: str = "ap-northeast-2") -> float:
    """NAT Gateway 월간 고정 비용 (데이터 처리 비용 제외)

    Args:
        region: AWS 리전

    Returns:
        월간 고정 USD 비용
    """
    return get_nat_monthly_cost(region, hours=HOURS_PER_MONTH, data_processed_gb=0)


def estimate_savings(
    nat_count: int,
    region: str = "ap-northeast-2",
    months: int = 12,
) -> dict[str, float | int | str]:
    """NAT Gateway 제거 시 예상 절감액 계산

    Args:
        nat_count: NAT Gateway 개수
        region: AWS 리전
        months: 계산 기간 (개월)

    Returns:
        절감액 정보 딕셔너리
    """
    monthly_fixed = get_nat_monthly_fixed_cost(region)
    monthly_savings = monthly_fixed * nat_count
    annual_savings = monthly_savings * months

    return {
        "monthly_per_nat": monthly_fixed,
        "monthly_total": round(monthly_savings, 2),
        "annual_total": round(annual_savings, 2),
        "nat_count": nat_count,
        "region": region,
    }
