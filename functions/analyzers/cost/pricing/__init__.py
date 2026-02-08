"""
plugins/cost/pricing - Backwards Compatibility Shim

DEPRECATED: 이 모듈은 shared.aws.pricing으로 이동되었습니다.
새 코드에서는 shared.aws.pricing을 직접 import하세요.

Usage (NEW):
    from core.shared.aws.pricing import get_ec2_monthly_cost, get_ebs_monthly_cost
    from core.shared.aws.pricing import pricing_service
"""

import warnings

# Re-export everything from new location for backwards compatibility
from core.shared.aws.pricing import (
    DEFAULT_PRICES,
    # Constants
    HOURS_PER_MONTH,
    LAMBDA_FREE_TIER_GB_SECONDS,
    LAMBDA_FREE_TIER_REQUESTS,
    PriceCache,
    # Core - Fetcher & Cache
    PricingFetcher,
    # Core - Utils
    PricingService,
    clear_cache,
    estimate_dynamodb_ondemand_cost,
    estimate_dynamodb_provisioned_cost,
    estimate_lambda_cost,
    estimate_nat_savings,
    # AMI
    get_ami_monthly_cost,
    get_ami_snapshot_price,
    get_cache_info,
    get_cloudwatch_ingestion_price,
    get_cloudwatch_monthly_cost,
    # CloudWatch
    get_cloudwatch_prices,
    get_cloudwatch_storage_price,
    get_default_prices,
    get_dynamodb_monthly_cost,
    get_dynamodb_ondemand_price,
    # DynamoDB
    get_dynamodb_prices,
    get_dynamodb_provisioned_price,
    get_dynamodb_storage_price,
    get_ebs_monthly_cost,
    # EBS
    get_ebs_price,
    get_ebs_prices,
    get_ebs_prices_bulk,
    get_ec2_monthly_cost,
    # EC2
    get_ec2_price,
    get_ec2_prices,
    get_ec2_prices_bulk,
    get_ecr_monthly_cost,
    # ECR
    get_ecr_prices,
    get_ecr_storage_price,
    get_efs_monthly_cost,
    # EFS
    get_efs_prices,
    get_efs_storage_price,
    get_eip_hourly_price,
    get_eip_monthly_cost,
    # EIP
    get_eip_prices,
    get_elasticache_hourly_price,
    get_elasticache_monthly_cost,
    get_elasticache_node_price,
    # ElastiCache
    get_elasticache_prices,
    get_elb_hourly_price,
    get_elb_monthly_cost,
    # ELB
    get_elb_prices,
    get_endpoint_data_price,
    get_endpoint_hourly_price,
    get_endpoint_monthly_cost,
    get_endpoint_monthly_fixed_cost,
    # VPC Endpoint
    get_endpoint_prices,
    get_fsx_gb_price,
    get_fsx_monthly_cost,
    # FSx
    get_fsx_prices,
    get_hosted_zone_monthly_cost,
    get_hosted_zone_price,
    get_kinesis_monthly_cost,
    # Kinesis
    get_kinesis_prices,
    get_kinesis_shard_hour_price,
    get_kinesis_shard_price,
    get_kms_key_monthly_cost,
    get_kms_key_price,
    # KMS
    get_kms_prices,
    get_kms_request_price,
    get_lambda_duration_price,
    get_lambda_monthly_cost,
    # Lambda
    get_lambda_prices,
    get_lambda_provisioned_monthly_cost,
    get_lambda_provisioned_price,
    get_lambda_request_price,
    get_nat_data_price,
    get_nat_hourly_price,
    get_nat_monthly_cost,
    get_nat_monthly_fixed_cost,
    # NAT
    get_nat_prices,
    get_opensearch_instance_price,
    get_opensearch_monthly_cost,
    # OpenSearch
    get_opensearch_prices,
    get_opensearch_storage_price,
    get_prices,
    get_query_monthly_cost,
    get_query_price,
    get_rds_instance_price,
    get_rds_monthly_cost,
    # RDS
    get_rds_prices,
    get_rds_snapshot_monthly_cost,
    get_rds_snapshot_price,
    # RDS Snapshot
    get_rds_snapshot_prices,
    get_rds_storage_price,
    get_redshift_monthly_cost,
    get_redshift_node_price,
    # Redshift
    get_redshift_prices,
    get_redshift_storage_price,
    # Route53
    get_route53_prices,
    get_sagemaker_monthly_cost,
    # SageMaker
    get_sagemaker_price,
    get_sagemaker_prices,
    get_sagemaker_prices_bulk,
    get_secret_api_price,
    get_secret_monthly_cost,
    get_secret_price,
    # Secrets Manager
    get_secret_prices,
    get_snapshot_monthly_cost,
    get_snapshot_price,
    # EBS Snapshot
    get_snapshot_prices,
    get_transfer_hourly_price,
    get_transfer_monthly_cost,
    # Transfer Family
    get_transfer_prices,
    pricing_service,
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
    "get_ec2_prices_bulk",
    # EBS
    "get_ebs_price",
    "get_ebs_monthly_cost",
    "get_ebs_prices",
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
    "get_sagemaker_prices_bulk",
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
    "get_elasticache_node_price",
    "get_elasticache_monthly_cost",
    # FSx
    "get_fsx_prices",
    "get_fsx_gb_price",
    "get_fsx_monthly_cost",
    # Kinesis
    "get_kinesis_prices",
    "get_kinesis_shard_hour_price",
    "get_kinesis_shard_price",
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

# Issue deprecation warning when this module is imported
warnings.warn(
    "plugins.cost.pricing is deprecated. Use shared.aws.pricing instead.",
    DeprecationWarning,
    stacklevel=2,
)
