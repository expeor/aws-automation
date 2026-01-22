"""
core/data/pricing - AWS Pricing API Services

Re-export from plugins/cost/pricing for the new core/data/ architecture.
This module provides the canonical import path for pricing services.

Usage (new):
    from core.data.pricing import get_ec2_monthly_cost, get_ebs_monthly_cost

Usage (legacy, still supported):
    from plugins.cost.pricing import get_ec2_monthly_cost, get_ebs_monthly_cost
"""

# Re-export everything from the original module
# This maintains backward compatibility while establishing the new import path
from plugins.cost.pricing import (
    # Core - Utils
    PricingService,
    pricing_service,
    get_prices,
    # Core - Fetcher & Cache
    PricingFetcher,
    PriceCache,
    clear_cache,
    get_cache_info,
    # Constants
    HOURS_PER_MONTH,
    DEFAULT_PRICES,
    LAMBDA_FREE_TIER_REQUESTS,
    LAMBDA_FREE_TIER_GB_SECONDS,
    get_default_prices,
    # EC2
    get_ec2_price,
    get_ec2_monthly_cost,
    get_ec2_prices,
    get_ec2_prices_bulk,
    # EBS
    get_ebs_price,
    get_ebs_monthly_cost,
    get_ebs_prices,
    get_ebs_prices_bulk,
    # NAT
    get_nat_prices,
    get_nat_hourly_price,
    get_nat_data_price,
    get_nat_monthly_cost,
    get_nat_monthly_fixed_cost,
    estimate_nat_savings,
    # VPC Endpoint
    get_endpoint_prices,
    get_endpoint_hourly_price,
    get_endpoint_data_price,
    get_endpoint_monthly_cost,
    get_endpoint_monthly_fixed_cost,
    # Secrets Manager
    get_secret_prices,
    get_secret_price,
    get_secret_api_price,
    get_secret_monthly_cost,
    # KMS
    get_kms_prices,
    get_kms_key_price,
    get_kms_request_price,
    get_kms_key_monthly_cost,
    # ECR
    get_ecr_prices,
    get_ecr_storage_price,
    get_ecr_monthly_cost,
    # Route53
    get_route53_prices,
    get_hosted_zone_price,
    get_query_price,
    get_hosted_zone_monthly_cost,
    get_query_monthly_cost,
    # EBS Snapshot
    get_snapshot_prices,
    get_snapshot_price,
    get_snapshot_monthly_cost,
    # EIP
    get_eip_prices,
    get_eip_hourly_price,
    get_eip_monthly_cost,
    # ELB
    get_elb_prices,
    get_elb_hourly_price,
    get_elb_monthly_cost,
    # RDS Snapshot
    get_rds_snapshot_prices,
    get_rds_snapshot_price,
    get_rds_snapshot_monthly_cost,
    # CloudWatch
    get_cloudwatch_prices,
    get_cloudwatch_storage_price,
    get_cloudwatch_ingestion_price,
    get_cloudwatch_monthly_cost,
    # Lambda
    get_lambda_prices,
    get_lambda_request_price,
    get_lambda_duration_price,
    get_lambda_provisioned_price,
    get_lambda_monthly_cost,
    get_lambda_provisioned_monthly_cost,
    estimate_lambda_cost,
    # DynamoDB
    get_dynamodb_prices,
    get_dynamodb_provisioned_price,
    get_dynamodb_ondemand_price,
    get_dynamodb_storage_price,
    get_dynamodb_monthly_cost,
    estimate_dynamodb_provisioned_cost,
    estimate_dynamodb_ondemand_cost,
    # SageMaker
    get_sagemaker_price,
    get_sagemaker_monthly_cost,
    get_sagemaker_prices,
    get_sagemaker_prices_bulk,
)

__all__ = [
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
]
