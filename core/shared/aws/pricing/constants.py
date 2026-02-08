"""
core/shared/aws/pricing/constants.py - 가격 모듈 중앙 상수 및 기본값

모든 서비스의 기본 가격과 공통 상수를 중앙에서 관리한다.
AWS Pricing API 호출 실패 시 fallback 가격으로 사용되며,
ap-northeast-2(서울) 리전 기준 2025년 가격이다.

상수:
    - ``HOURS_PER_MONTH``: 월간 시간 (730h = 365일 * 24h / 12개월)
    - ``LAMBDA_FREE_TIER_REQUESTS``: Lambda 무료 티어 월간 요청 수 (100만)
    - ``LAMBDA_FREE_TIER_GB_SECONDS``: Lambda 무료 티어 월간 GB-초 (40만)
    - ``DEFAULT_PRICES``: 서비스별 기본 가격 딕셔너리 (14개 서비스)
"""

from __future__ import annotations

# 월간 시간 상수
HOURS_PER_MONTH = 730

# Lambda 프리 티어
LAMBDA_FREE_TIER_REQUESTS = 1_000_000  # 월 100만 요청 무료
LAMBDA_FREE_TIER_GB_SECONDS = 400_000  # 월 40만 GB-초 무료

# ============================================================================
# 서비스별 기본 가격 (API 실패 시 fallback, ap-northeast-2 기준)
# ============================================================================

DEFAULT_PRICES: dict[str, dict[str, float]] = {
    # EC2 인스턴스 시간당 가격
    "ec2": {
        "t3.nano": 0.0052,
        "t3.micro": 0.0104,
        "t3.small": 0.0208,
        "t3.medium": 0.0416,
        "t3.large": 0.0832,
        "t3.xlarge": 0.1664,
        "t3.2xlarge": 0.3328,
        "t2.micro": 0.0116,
        "t2.small": 0.023,
        "t2.medium": 0.0464,
        "m5.large": 0.096,
        "m5.xlarge": 0.192,
        "m5.2xlarge": 0.384,
        "m6i.large": 0.096,
        "m6i.xlarge": 0.192,
        "c5.large": 0.085,
        "c5.xlarge": 0.17,
        "r5.large": 0.126,
        "r5.xlarge": 0.252,
    },
    # EBS 볼륨 GB당 월 가격
    "ebs": {
        "gp3": 0.08,
        "gp2": 0.10,
        "io1": 0.125,
        "io2": 0.125,
        "st1": 0.045,
        "sc1": 0.025,
        "standard": 0.05,
    },
    # SageMaker 인스턴스 시간당 가격
    "sagemaker": {
        "ml.t2.medium": 0.0464,
        "ml.t2.large": 0.0928,
        "ml.t2.xlarge": 0.1856,
        "ml.t3.medium": 0.0416,
        "ml.t3.large": 0.0832,
        "ml.t3.xlarge": 0.1664,
        "ml.m5.large": 0.115,
        "ml.m5.xlarge": 0.23,
        "ml.m5.2xlarge": 0.461,
        "ml.m5.4xlarge": 0.922,
        "ml.m5.12xlarge": 2.765,
        "ml.m5.24xlarge": 5.53,
        "ml.m6i.large": 0.113,
        "ml.m6i.xlarge": 0.226,
        "ml.m6i.2xlarge": 0.452,
        "ml.c5.large": 0.102,
        "ml.c5.xlarge": 0.204,
        "ml.c5.2xlarge": 0.408,
        "ml.c5.4xlarge": 0.816,
        "ml.c5.9xlarge": 1.836,
        "ml.c6i.large": 0.102,
        "ml.c6i.xlarge": 0.204,
        "ml.p3.2xlarge": 3.825,
        "ml.p3.8xlarge": 14.688,
        "ml.p3.16xlarge": 28.152,
        "ml.g4dn.xlarge": 0.736,
        "ml.g4dn.2xlarge": 1.052,
        "ml.g4dn.4xlarge": 1.685,
        "ml.g4dn.8xlarge": 3.046,
        "ml.g4dn.12xlarge": 5.480,
        "ml.g5.xlarge": 1.408,
        "ml.g5.2xlarge": 1.686,
        "ml.g5.4xlarge": 2.242,
        "ml.g5.8xlarge": 3.354,
        "ml.g5.12xlarge": 7.098,
        "ml.g5.24xlarge": 11.340,
        "ml.g5.48xlarge": 22.680,
        "ml.inf1.xlarge": 0.228,
        "ml.inf1.2xlarge": 0.362,
        "ml.inf1.6xlarge": 1.180,
        "ml.inf1.24xlarge": 4.721,
        "ml.inf2.xlarge": 0.758,
        "ml.inf2.8xlarge": 1.968,
        "ml.inf2.24xlarge": 6.492,
        "ml.inf2.48xlarge": 12.984,
    },
    # NAT Gateway 가격
    "nat": {
        "hourly": 0.045,
        "data_per_gb": 0.045,
    },
    # VPC Endpoint 가격
    "vpc_endpoint": {
        "interface_hourly": 0.01,
        "gateway_hourly": 0.0,
        "data_per_gb": 0.01,
    },
    # Secrets Manager 가격
    "secretsmanager": {
        "per_secret_monthly": 0.40,
        "per_10k_api_calls": 0.05,
    },
    # KMS 가격
    "kms": {
        "customer_key_monthly": 1.0,
        "per_10k_requests": 0.03,
    },
    # ECR 가격
    "ecr": {
        "storage_per_gb_monthly": 0.10,
    },
    # Route53 가격 (글로벌)
    "route53": {
        "hosted_zone_monthly": 0.50,
        "additional_zone_monthly": 0.10,
        "query_per_million": 0.40,
    },
    # EBS Snapshot 가격
    "snapshot": {
        "storage_per_gb_monthly": 0.05,
    },
    # EIP 가격
    "eip": {
        "unused_hourly": 0.005,
        "additional_hourly": 0.005,
    },
    # ELB 가격
    "elb": {
        "alb_hourly": 0.0225,
        "nlb_hourly": 0.0225,
        "glb_hourly": 0.0125,
        "clb_hourly": 0.025,
    },
    # RDS Snapshot 가격
    "rds_snapshot": {
        "rds_per_gb_monthly": 0.02,
        "aurora_per_gb_monthly": 0.021,
    },
    # CloudWatch 가격
    "cloudwatch": {
        "storage_per_gb_monthly": 0.03,
        "ingestion_per_gb": 0.50,
    },
    # Lambda 가격
    "lambda": {
        "request_per_million": 0.20,
        "duration_per_gb_second": 0.0000166667,
        "provisioned_concurrency_per_gb_hour": 0.000004646,
    },
    # DynamoDB 가격
    "dynamodb": {
        "rcu_per_hour": 0.00013,
        "wcu_per_hour": 0.00065,
        "read_per_million": 0.25,
        "write_per_million": 1.25,
        "storage_per_gb": 0.25,
    },
}


def get_default_prices(service: str) -> dict[str, float]:
    """서비스별 기본 가격(fallback) 딕셔너리의 복사본을 반환한다.

    ``DEFAULT_PRICES`` 에서 해당 서비스의 가격 맵을 복사하여 반환한다.
    호출자가 반환값을 수정해도 원본 상수에 영향을 주지 않는다.

    Args:
        service: AWS 서비스 코드 (예: ``"ec2"``, ``"ebs"``, ``"sagemaker"``,
            ``"nat"``, ``"lambda"`` 등 ``DEFAULT_PRICES`` 의 키)

    Returns:
        기본 가격 딕셔너리의 shallow copy. 등록되지 않은 서비스이면 빈 딕셔너리.

    Example:
        >>> get_default_prices("ec2")
        {"t3.nano": 0.0052, "t3.micro": 0.0104, ...}
    """
    return DEFAULT_PRICES.get(service, {}).copy()
