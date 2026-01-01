"""
plugins/cost/pricing - AWS 서비스 비용 조회 및 계산 유틸리티

AWS Pricing API를 사용하여 실시간 가격 정보를 조회하고 캐싱합니다.

모듈 구성:
    - fetcher: AWS Pricing Bulk API 클라이언트
    - cache: 로컬 가격 캐시 (7일 TTL)
    - ec2: EC2 인스턴스 가격 조회
    - ebs: EBS 볼륨 가격 조회
    - nat: NAT Gateway 가격 조회
    - vpc_endpoint: VPC Endpoint 가격 조회
    - secretsmanager: Secrets Manager 가격 조회
    - kms: KMS 가격 조회
    - ecr: ECR 가격 조회
    - route53: Route53 가격 조회

사용법:
    from plugins.cost.pricing import get_ec2_monthly_cost, get_ebs_monthly_cost
    from plugins.cost.pricing import get_nat_monthly_cost, get_endpoint_monthly_cost
    from plugins.cost.pricing import get_secret_monthly_cost, get_kms_key_monthly_cost
    from plugins.cost.pricing import get_ecr_monthly_cost, get_hosted_zone_monthly_cost

    # EC2 월간 비용
    cost = get_ec2_monthly_cost("t3.medium", "ap-northeast-2")

    # EBS 월간 비용 (100GB gp3)
    cost = get_ebs_monthly_cost("gp3", 100, "ap-northeast-2")

    # NAT Gateway 월간 비용
    cost = get_nat_monthly_cost("ap-northeast-2")

    # VPC Endpoint 월간 비용
    cost = get_endpoint_monthly_cost("ap-northeast-2")

    # Secrets Manager 월간 비용
    cost = get_secret_monthly_cost("ap-northeast-2", secret_count=5)

    # KMS 월간 비용
    cost = get_kms_key_monthly_cost("ap-northeast-2", key_count=3)

    # ECR 월간 비용
    cost = get_ecr_monthly_cost("ap-northeast-2", storage_gb=50)

    # Route53 Hosted Zone 월간 비용
    cost = get_hosted_zone_monthly_cost(zone_count=10)
"""

# Fetcher & Cache
from .fetcher import PricingFetcher
from .cache import PriceCache, clear_cache, get_cache_info

# EC2 가격
from .ec2 import (
    get_ec2_price,
    get_ec2_monthly_cost,
    get_ec2_prices_bulk,
)

# EBS 가격
from .ebs import (
    get_ebs_price,
    get_ebs_monthly_cost,
    get_ebs_prices_bulk,
)

# NAT Gateway 가격
from .nat import (
    get_nat_prices,
    get_nat_hourly_price,
    get_nat_data_price,
    get_nat_monthly_cost,
    get_nat_monthly_fixed_cost,
    estimate_savings as estimate_nat_savings,
)

# VPC Endpoint 가격
from .vpc_endpoint import (
    get_endpoint_prices,
    get_endpoint_hourly_price,
    get_endpoint_data_price,
    get_endpoint_monthly_cost,
    get_endpoint_monthly_fixed_cost,
)

# Secrets Manager 가격
from .secretsmanager import (
    get_secret_prices,
    get_secret_price,
    get_secret_api_price,
    get_secret_monthly_cost,
)

# KMS 가격
from .kms import (
    get_kms_prices,
    get_kms_key_price,
    get_kms_request_price,
    get_kms_key_monthly_cost,
)

# ECR 가격
from .ecr import (
    get_ecr_prices,
    get_ecr_storage_price,
    get_ecr_monthly_cost,
)

# Route53 가격
from .route53 import (
    get_route53_prices,
    get_hosted_zone_price,
    get_query_price,
    get_hosted_zone_monthly_cost,
    get_query_monthly_cost,
)

# EBS Snapshot 가격
from .snapshot import (
    get_snapshot_prices,
    get_snapshot_price,
    get_snapshot_monthly_cost,
)

# EIP 가격
from .eip import (
    get_eip_prices,
    get_eip_hourly_price,
    get_eip_monthly_cost,
)

# ELB 가격
from .elb import (
    get_elb_prices,
    get_elb_hourly_price,
    get_elb_monthly_cost,
)

# RDS Snapshot 가격
from .rds_snapshot import (
    get_rds_snapshot_prices,
    get_rds_snapshot_price,
    get_rds_snapshot_monthly_cost,
)

# CloudWatch 가격
from .cloudwatch import (
    get_cloudwatch_prices,
    get_cloudwatch_storage_price,
    get_cloudwatch_ingestion_price,
    get_cloudwatch_monthly_cost,
)

# Lambda 가격
from .lambda_ import (
    get_lambda_prices,
    get_lambda_request_price,
    get_lambda_duration_price,
    get_lambda_provisioned_price,
    get_lambda_monthly_cost,
    get_lambda_provisioned_monthly_cost,
    estimate_lambda_cost,
)

# 월간 시간 상수
HOURS_PER_MONTH = 730

__all__ = [
    # Core
    "PricingFetcher",
    "PriceCache",
    "clear_cache",
    "get_cache_info",
    # EC2
    "get_ec2_price",
    "get_ec2_monthly_cost",
    "get_ec2_prices_bulk",
    # EBS
    "get_ebs_price",
    "get_ebs_monthly_cost",
    "get_ebs_prices_bulk",
    # NAT
    "get_nat_prices",
    "get_nat_hourly_price",
    "get_nat_data_price",
    "get_nat_monthly_cost",
    "get_nat_monthly_fixed_cost",
    "estimate_nat_savings",
    # VPC Endpoint
    "get_endpoint_prices",
    "get_endpoint_hourly_price",
    "get_endpoint_data_price",
    "get_endpoint_monthly_cost",
    "get_endpoint_monthly_fixed_cost",
    # Secrets Manager
    "get_secret_prices",
    "get_secret_price",
    "get_secret_api_price",
    "get_secret_monthly_cost",
    # KMS
    "get_kms_prices",
    "get_kms_key_price",
    "get_kms_request_price",
    "get_kms_key_monthly_cost",
    # ECR
    "get_ecr_prices",
    "get_ecr_storage_price",
    "get_ecr_monthly_cost",
    # Route53
    "get_route53_prices",
    "get_hosted_zone_price",
    "get_query_price",
    "get_hosted_zone_monthly_cost",
    "get_query_monthly_cost",
    # EBS Snapshot
    "get_snapshot_prices",
    "get_snapshot_price",
    "get_snapshot_monthly_cost",
    # EIP
    "get_eip_prices",
    "get_eip_hourly_price",
    "get_eip_monthly_cost",
    # ELB
    "get_elb_prices",
    "get_elb_hourly_price",
    "get_elb_monthly_cost",
    # RDS Snapshot
    "get_rds_snapshot_prices",
    "get_rds_snapshot_price",
    "get_rds_snapshot_monthly_cost",
    # CloudWatch
    "get_cloudwatch_prices",
    "get_cloudwatch_storage_price",
    "get_cloudwatch_ingestion_price",
    "get_cloudwatch_monthly_cost",
    # Lambda
    "get_lambda_prices",
    "get_lambda_request_price",
    "get_lambda_duration_price",
    "get_lambda_provisioned_price",
    "get_lambda_monthly_cost",
    "get_lambda_provisioned_monthly_cost",
    "estimate_lambda_cost",
    # Constants
    "HOURS_PER_MONTH",
]
