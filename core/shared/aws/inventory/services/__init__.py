"""
core/shared/aws/inventory/services - 서비스별 리소스 수집기 패키지

각 AWS 서비스별 리소스 수집 로직을 제공합니다.

각 서비스 모듈은 ``collect_*`` 함수를 제공하며, 단일 계정/리전에서 해당 리소스를
수집합니다. 이 함수들은 ``InventoryCollector``에서 ``parallel_collect``를 통해
멀티 계정/리전으로 확장됩니다. ``helpers`` 모듈은 태그 파싱, 보안 규칙 분석 등
유틸리티 함수를 제공합니다.

카테고리 (11개, 총 60종):
    - Network (14): VPC, Subnet, RouteTable, InternetGateway, ElasticIP, ENI,
      NATGateway, VPCEndpoint, TransitGateway, TransitGatewayAttachment,
      VPNGateway, VPNConnection, NetworkACL, VPCPeeringConnection
    - Compute (11): EC2Instance, EBSVolume, LambdaFunction, ECSCluster, ECSService,
      AutoScalingGroup, LaunchTemplate, EKSCluster, EKSNodeGroup, AMI, Snapshot
    - Database/Storage (8): RDSInstance, RDSCluster, S3Bucket, DynamoDBTable,
      ElastiCacheCluster, RedshiftCluster, EFSFileSystem, FSxFileSystem
    - Security (8): SecurityGroup, KMSKey, Secret, IAMRole, IAMUser, IAMPolicy,
      ACMCertificate, WAFWebACL
    - CDN/DNS (2): CloudFrontDistribution, Route53HostedZone
    - Load Balancing (2): LoadBalancer, TargetGroup
    - Integration/Messaging (5): SNSTopic, SQSQueue, EventBridgeRule, StepFunction,
      APIGatewayAPI
    - Monitoring (2): CloudWatchAlarm, CloudWatchLogGroup
    - Analytics (3): KinesisStream, KinesisFirehose, GlueDatabase
    - DevOps (3): CloudFormationStack, CodePipeline, CodeBuildProject
    - Backup (2): BackupVault, BackupPlan
"""

# Network (Basic)
# Analytics
from .analytics import collect_glue_databases, collect_kinesis_firehoses, collect_kinesis_streams

# Backup
from .backup import collect_backup_plans, collect_backup_vaults

# CDN/DNS
from .cdn import collect_cloudfront_distributions, collect_route53_hosted_zones

# Compute
from .compute import (
    collect_amis,
    collect_auto_scaling_groups,
    collect_ebs_volumes,
    collect_ecs_clusters,
    collect_ecs_services,
    collect_eks_clusters,
    collect_eks_node_groups,
    collect_lambda_functions,
    collect_launch_templates,
    collect_snapshots,
)

# Database/Storage
from .database import (
    collect_dynamodb_tables,
    collect_elasticache_clusters,
    collect_rds_clusters,
    collect_rds_instances,
    collect_redshift_clusters,
    collect_s3_buckets,
)

# DevOps
from .devops import collect_cloudformation_stacks, collect_codebuild_projects, collect_codepipelines
from .ec2 import collect_ec2_instances, collect_security_groups

# Load Balancing
from .elb import collect_load_balancers, collect_target_groups

# Helpers
from .helpers import (
    count_rules,
    get_name_from_tags,
    get_tag_value,
    has_public_access_rule,
    parse_tags,
)
from .iam import (
    collect_acm_certificates,
    collect_iam_policies,
    collect_iam_roles,
    collect_iam_users,
    collect_waf_web_acls,
)

# Integration/Messaging
from .messaging import (
    collect_api_gateway_apis,
    collect_eventbridge_rules,
    collect_sns_topics,
    collect_sqs_queues,
    collect_step_functions,
)

# Monitoring
from .monitoring import collect_cloudwatch_alarms, collect_cloudwatch_log_groups

# Network (Advanced)
from .network_advanced import (
    collect_network_acls,
    collect_transit_gateway_attachments,
    collect_transit_gateways,
    collect_vpc_peering_connections,
    collect_vpn_connections,
    collect_vpn_gateways,
)

# Security
from .security import collect_kms_keys, collect_secrets
from .storage import collect_efs_file_systems, collect_fsx_file_systems
from .vpc import (
    collect_elastic_ips,
    collect_enis,
    collect_internet_gateways,
    collect_nat_gateways,
    collect_route_tables,
    collect_subnets,
    collect_vpc_endpoints,
    collect_vpcs,
)

__all__ = [
    # Network (Basic)
    "collect_vpcs",
    "collect_subnets",
    "collect_route_tables",
    "collect_internet_gateways",
    "collect_elastic_ips",
    "collect_enis",
    "collect_nat_gateways",
    "collect_vpc_endpoints",
    # Network (Advanced)
    "collect_transit_gateways",
    "collect_transit_gateway_attachments",
    "collect_vpn_gateways",
    "collect_vpn_connections",
    "collect_network_acls",
    "collect_vpc_peering_connections",
    # Compute
    "collect_ec2_instances",
    "collect_ebs_volumes",
    "collect_lambda_functions",
    "collect_ecs_clusters",
    "collect_ecs_services",
    "collect_auto_scaling_groups",
    "collect_launch_templates",
    "collect_eks_clusters",
    "collect_eks_node_groups",
    "collect_amis",
    "collect_snapshots",
    # Database/Storage
    "collect_rds_instances",
    "collect_rds_clusters",
    "collect_s3_buckets",
    "collect_dynamodb_tables",
    "collect_elasticache_clusters",
    "collect_redshift_clusters",
    "collect_efs_file_systems",
    "collect_fsx_file_systems",
    # Security
    "collect_security_groups",
    "collect_kms_keys",
    "collect_secrets",
    "collect_iam_roles",
    "collect_iam_users",
    "collect_iam_policies",
    "collect_acm_certificates",
    "collect_waf_web_acls",
    # CDN/DNS
    "collect_cloudfront_distributions",
    "collect_route53_hosted_zones",
    # Load Balancing
    "collect_load_balancers",
    "collect_target_groups",
    # Integration/Messaging
    "collect_sns_topics",
    "collect_sqs_queues",
    "collect_eventbridge_rules",
    "collect_step_functions",
    "collect_api_gateway_apis",
    # Monitoring
    "collect_cloudwatch_alarms",
    "collect_cloudwatch_log_groups",
    # Analytics
    "collect_kinesis_streams",
    "collect_kinesis_firehoses",
    "collect_glue_databases",
    # DevOps
    "collect_cloudformation_stacks",
    "collect_codepipelines",
    "collect_codebuild_projects",
    # Backup
    "collect_backup_vaults",
    "collect_backup_plans",
    # Helpers
    "parse_tags",
    "get_name_from_tags",
    "get_tag_value",
    "has_public_access_rule",
    "count_rules",
]
