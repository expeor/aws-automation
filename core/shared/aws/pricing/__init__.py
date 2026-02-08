"""
shared/aws/pricing - AWS 서비스 비용 조회 및 계산 유틸리티

AWS Pricing API를 사용하여 실시간 가격 정보를 조회하고 캐싱합니다.

모듈 구성:
    - utils: PricingService (통합 가격 조회 서비스)
    - constants: 기본값 및 상수
    - fetcher: AWS Pricing Bulk API 클라이언트
    - cache: 로컬 가격 캐시 (7일 TTL, filelock 지원)
    - ec2: EC2 인스턴스 가격 조회
    - ebs: EBS 볼륨 가격 조회
    - nat: NAT Gateway 가격 조회
    - vpc_endpoint: VPC Endpoint 가격 조회
    - secretsmanager: Secrets Manager 가격 조회
    - kms: KMS 가격 조회
    - ecr: ECR 가격 조회
    - route53: Route53 가격 조회

사용법:
    from core.shared.aws.pricing import get_ec2_monthly_cost, get_ebs_monthly_cost
    from core.shared.aws.pricing import get_nat_monthly_cost, get_endpoint_monthly_cost
    from core.shared.aws.pricing import get_secret_monthly_cost, get_kms_key_monthly_cost
    from core.shared.aws.pricing import get_ecr_monthly_cost, get_hosted_zone_monthly_cost

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

    # 통합 가격 서비스 사용
    from core.shared.aws.pricing import pricing_service
    prices = pricing_service.get_prices("ec2", "ap-northeast-2")
    metrics = pricing_service.get_metrics()
"""

# AMI 가격 (스냅샷 기반)
from .ami import get_ami_monthly_cost, get_ami_snapshot_price
from .cache import PriceCache, clear_cache, get_cache_info

# CloudWatch 가격
from .cloudwatch import (
    get_cloudwatch_ingestion_price,
    get_cloudwatch_monthly_cost,
    get_cloudwatch_prices,
    get_cloudwatch_storage_price,
)

# Constants - 중앙 관리되는 상수 및 기본값
from .constants import (
    DEFAULT_PRICES,
    HOURS_PER_MONTH,
    LAMBDA_FREE_TIER_GB_SECONDS,
    LAMBDA_FREE_TIER_REQUESTS,
    get_default_prices,
)

# DynamoDB 가격
from .dynamodb import (
    estimate_ondemand_cost as estimate_dynamodb_ondemand_cost,
)
from .dynamodb import (
    estimate_provisioned_cost as estimate_dynamodb_provisioned_cost,
)
from .dynamodb import (
    get_dynamodb_monthly_cost,
    get_dynamodb_ondemand_price,
    get_dynamodb_prices,
    get_dynamodb_provisioned_price,
    get_dynamodb_storage_price,
)

# EBS 가격
from .ebs import get_ebs_monthly_cost, get_ebs_price, get_ebs_prices, get_ebs_prices_bulk

# EC2 가격
from .ec2 import get_ec2_monthly_cost, get_ec2_price, get_ec2_prices, get_ec2_prices_bulk

# ECR 가격
from .ecr import get_ecr_monthly_cost, get_ecr_prices, get_ecr_storage_price

# EFS 가격
from .efs import (
    get_efs_monthly_cost,
    get_efs_prices,
    get_efs_storage_price,
)

# EIP 가격
from .eip import get_eip_hourly_price, get_eip_monthly_cost, get_eip_prices

# ElastiCache 가격
from .elasticache import (
    get_elasticache_hourly_price,
    get_elasticache_monthly_cost,
    get_elasticache_prices,
)
from .elasticache import (
    get_elasticache_hourly_price as get_elasticache_node_price,  # alias
)

# ELB 가격
from .elb import get_elb_hourly_price, get_elb_monthly_cost, get_elb_prices

# Fetcher & Cache
from .fetcher import PricingFetcher

# FSx 가격
from .fsx import (
    get_fsx_gb_price,
    get_fsx_monthly_cost,
    get_fsx_prices,
)

# Kinesis 가격
from .kinesis import (
    get_kinesis_monthly_cost,
    get_kinesis_prices,
    get_kinesis_shard_hour_price,
)
from .kinesis import (
    get_kinesis_shard_hour_price as get_kinesis_shard_price,  # alias
)

# KMS 가격
from .kms import (
    get_kms_key_monthly_cost,
    get_kms_key_price,
    get_kms_prices,
    get_kms_request_price,
)

# Lambda 가격
from .lambda_ import (
    estimate_lambda_cost,
    get_lambda_duration_price,
    get_lambda_monthly_cost,
    get_lambda_prices,
    get_lambda_provisioned_monthly_cost,
    get_lambda_provisioned_price,
    get_lambda_request_price,
)

# NAT Gateway 가격
from .nat import estimate_savings as estimate_nat_savings
from .nat import (
    get_nat_data_price,
    get_nat_hourly_price,
    get_nat_monthly_cost,
    get_nat_monthly_fixed_cost,
    get_nat_prices,
)

# OpenSearch 가격
from .opensearch import (
    get_opensearch_instance_price,
    get_opensearch_monthly_cost,
    get_opensearch_prices,
    get_opensearch_storage_price,
)

# RDS 가격
from .rds import (
    get_rds_instance_price,
    get_rds_monthly_cost,
    get_rds_prices,
    get_rds_storage_price,
)

# RDS Snapshot 가격
from .rds_snapshot import (
    get_rds_snapshot_monthly_cost,
    get_rds_snapshot_price,
    get_rds_snapshot_prices,
)

# Redshift 가격
from .redshift import (
    get_redshift_monthly_cost,
    get_redshift_node_price,
    get_redshift_prices,
    get_redshift_storage_price,
)

# Route53 가격
from .route53 import (
    get_hosted_zone_monthly_cost,
    get_hosted_zone_price,
    get_query_monthly_cost,
    get_query_price,
    get_route53_prices,
)

# SageMaker 가격
from .sagemaker import (
    get_sagemaker_monthly_cost,
    get_sagemaker_price,
    get_sagemaker_prices,
    get_sagemaker_prices_bulk,
)

# Secrets Manager 가격
from .secretsmanager import (
    get_secret_api_price,
    get_secret_monthly_cost,
    get_secret_price,
    get_secret_prices,
)

# EBS Snapshot 가격
from .snapshot import get_snapshot_monthly_cost, get_snapshot_price, get_snapshot_prices

# Transfer Family 가격
from .transfer import (
    get_transfer_hourly_price,
    get_transfer_monthly_cost,
    get_transfer_prices,
)

# Utils - PricingService 통합 가격 조회 서비스
from .utils import PricingService, get_prices, pricing_service

# VPC Endpoint 가격
from .vpc_endpoint import (
    get_endpoint_data_price,
    get_endpoint_hourly_price,
    get_endpoint_monthly_cost,
    get_endpoint_monthly_fixed_cost,
    get_endpoint_prices,
)

__all__: list[str] = [
    # Core - Utils
    "PricingService",
    "pricing_service",
    "get_prices",
    # Core - Fetcher & Cache
    "PricingFetcher",
    "PriceCache",
    "clear_cache",
    "get_cache_info",
    # Constants
    "HOURS_PER_MONTH",
    "DEFAULT_PRICES",
    "LAMBDA_FREE_TIER_REQUESTS",
    "LAMBDA_FREE_TIER_GB_SECONDS",
    "get_default_prices",
    # EC2
    "get_ec2_price",
    "get_ec2_monthly_cost",
    "get_ec2_prices",
    "get_ec2_prices_bulk",  # 하위 호환성 alias
    # EBS
    "get_ebs_price",
    "get_ebs_monthly_cost",
    "get_ebs_prices",
    "get_ebs_prices_bulk",  # 하위 호환성 alias
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
    # DynamoDB
    "get_dynamodb_prices",
    "get_dynamodb_provisioned_price",
    "get_dynamodb_ondemand_price",
    "get_dynamodb_storage_price",
    "get_dynamodb_monthly_cost",
    "estimate_dynamodb_provisioned_cost",
    "estimate_dynamodb_ondemand_cost",
    # SageMaker
    "get_sagemaker_price",
    "get_sagemaker_monthly_cost",
    "get_sagemaker_prices",
    "get_sagemaker_prices_bulk",  # 하위 호환성 alias
    # AMI
    "get_ami_monthly_cost",
    "get_ami_snapshot_price",
    # EFS
    "get_efs_prices",
    "get_efs_storage_price",
    "get_efs_monthly_cost",
    # ElastiCache
    "get_elasticache_prices",
    "get_elasticache_hourly_price",
    "get_elasticache_node_price",  # alias for get_elasticache_hourly_price
    "get_elasticache_monthly_cost",
    # FSx
    "get_fsx_prices",
    "get_fsx_gb_price",
    "get_fsx_monthly_cost",
    # Kinesis
    "get_kinesis_prices",
    "get_kinesis_shard_hour_price",
    "get_kinesis_shard_price",  # alias for get_kinesis_shard_hour_price
    "get_kinesis_monthly_cost",
    # OpenSearch
    "get_opensearch_prices",
    "get_opensearch_instance_price",
    "get_opensearch_storage_price",
    "get_opensearch_monthly_cost",
    # RDS
    "get_rds_prices",
    "get_rds_instance_price",
    "get_rds_storage_price",
    "get_rds_monthly_cost",
    # Redshift
    "get_redshift_prices",
    "get_redshift_node_price",
    "get_redshift_storage_price",
    "get_redshift_monthly_cost",
    # Transfer Family
    "get_transfer_prices",
    "get_transfer_hourly_price",
    "get_transfer_monthly_cost",
]
