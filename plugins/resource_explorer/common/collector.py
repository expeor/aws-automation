"""
plugins/resource_explorer/common/collector.py - 인벤토리 수집기

병렬로 AWS 리소스를 수집하는 통합 클래스.

카테고리:
- Network: VPC, Subnet, RouteTable, InternetGateway, ElasticIP, ENI, NATGateway, VPCEndpoint
          TransitGateway, TransitGatewayAttachment, VPNGateway, VPNConnection, NetworkACL, VPCPeering
- Compute: EC2, EBSVolume, LambdaFunction, ECSCluster, ECSService
           AutoScalingGroup, LaunchTemplate, EKSCluster, EKSNodeGroup, AMI, Snapshot
- Database/Storage: RDSInstance, RDSCluster, S3Bucket, DynamoDBTable, ElastiCacheCluster
                    RedshiftCluster, EFSFileSystem, FSxFileSystem
- Security: SecurityGroup, KMSKey, Secret, IAMRole, IAMUser, IAMPolicy, ACMCertificate, WAFWebACL
- CDN/DNS: CloudFrontDistribution, Route53HostedZone
- Load Balancing: LoadBalancer, TargetGroup
- Integration/Messaging: SNSTopic, SQSQueue, EventBridgeRule, StepFunction, APIGatewayAPI
- Monitoring: CloudWatchAlarm, CloudWatchLogGroup
- Analytics: KinesisStream, KinesisFirehose, GlueDatabase
- DevOps: CloudFormationStack, CodePipeline, CodeBuildProject
- Backup: BackupVault, BackupPlan
"""

from core.parallel import parallel_collect

from .services import (
    # Security - Extended
    collect_acm_certificates,
    # Compute - Extended
    collect_amis,
    # Integration/Messaging
    collect_api_gateway_apis,
    collect_auto_scaling_groups,
    # Backup
    collect_backup_plans,
    collect_backup_vaults,
    # DevOps
    collect_cloudformation_stacks,
    # CDN/DNS
    collect_cloudfront_distributions,
    # Monitoring
    collect_cloudwatch_alarms,
    collect_cloudwatch_log_groups,
    collect_codebuild_projects,
    collect_codepipelines,
    # Database/Storage
    collect_dynamodb_tables,
    # Compute
    collect_ebs_volumes,
    # Security (EC2)
    collect_ec2_instances,
    collect_ecs_clusters,
    collect_ecs_services,
    # Storage - Extended
    collect_efs_file_systems,
    collect_eks_clusters,
    collect_eks_node_groups,
    # Network
    collect_elastic_ips,
    collect_elasticache_clusters,
    collect_enis,
    collect_eventbridge_rules,
    collect_fsx_file_systems,
    # Analytics
    collect_glue_databases,
    collect_iam_policies,
    collect_iam_roles,
    collect_iam_users,
    collect_internet_gateways,
    collect_kinesis_firehoses,
    collect_kinesis_streams,
    # Security
    collect_kms_keys,
    collect_lambda_functions,
    collect_launch_templates,
    # Load Balancing
    collect_load_balancers,
    collect_nat_gateways,
    # Network - Advanced
    collect_network_acls,
    collect_rds_clusters,
    collect_rds_instances,
    # Database - Extended
    collect_redshift_clusters,
    collect_route53_hosted_zones,
    collect_route_tables,
    collect_s3_buckets,
    collect_secrets,
    collect_security_groups,
    collect_snapshots,
    collect_sns_topics,
    collect_sqs_queues,
    collect_step_functions,
    collect_subnets,
    collect_target_groups,
    collect_transit_gateway_attachments,
    collect_transit_gateways,
    collect_vpc_endpoints,
    collect_vpc_peering_connections,
    collect_vpcs,
    collect_vpn_connections,
    collect_vpn_gateways,
    collect_waf_web_acls,
)
from .types import (
    AMI,
    ENI,
    VPC,
    ACMCertificate,
    APIGatewayAPI,
    AutoScalingGroup,
    BackupPlan,
    BackupVault,
    CloudFormationStack,
    CloudFrontDistribution,
    CloudWatchAlarm,
    CloudWatchLogGroup,
    CodeBuildProject,
    CodePipeline,
    DynamoDBTable,
    EBSVolume,
    EC2Instance,
    ECSCluster,
    ECSService,
    EFSFileSystem,
    EKSCluster,
    EKSNodeGroup,
    ElastiCacheCluster,
    ElasticIP,
    EventBridgeRule,
    FSxFileSystem,
    GlueDatabase,
    IAMPolicy,
    IAMRole,
    IAMUser,
    InternetGateway,
    KinesisFirehose,
    KinesisStream,
    KMSKey,
    LambdaFunction,
    LaunchTemplate,
    LoadBalancer,
    NATGateway,
    NetworkACL,
    RDSCluster,
    RDSInstance,
    RedshiftCluster,
    Route53HostedZone,
    RouteTable,
    S3Bucket,
    Secret,
    SecurityGroup,
    Snapshot,
    SNSTopic,
    SQSQueue,
    StepFunction,
    Subnet,
    TargetGroup,
    TransitGateway,
    TransitGatewayAttachment,
    VPCEndpoint,
    VPCPeeringConnection,
    VPNConnection,
    VPNGateway,
    WAFWebACL,
)


class InventoryCollector:
    """AWS 리소스 인벤토리 수집기

    병렬 처리를 통해 multi-account/region에서 리소스를 수집합니다.

    Usage:
        collector = InventoryCollector(ctx)

        # Network
        vpcs = collector.collect_vpcs()
        subnets = collector.collect_subnets()

        # Compute
        instances = collector.collect_ec2()
        volumes = collector.collect_ebs_volumes()

        # Database
        rds_instances = collector.collect_rds_instances()
    """

    def __init__(self, ctx):
        """
        Args:
            ctx: ExecutionContext (provider, regions, accounts 포함)
        """
        self._ctx = ctx

    # =========================================================================
    # Network 카테고리 (Basic)
    # =========================================================================

    def collect_vpcs(self) -> list[VPC]:
        """VPC 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_vpcs(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_subnets(self) -> list[Subnet]:
        """Subnet 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_subnets(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_route_tables(self) -> list[RouteTable]:
        """Route Table 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_route_tables(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_internet_gateways(self) -> list[InternetGateway]:
        """Internet Gateway 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_internet_gateways(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_elastic_ips(self) -> list[ElasticIP]:
        """Elastic IP 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_elastic_ips(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_enis(self) -> list[ENI]:
        """ENI 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_enis(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_nat_gateways(self) -> list[NATGateway]:
        """NAT Gateway 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_nat_gateways(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_vpc_endpoints(self) -> list[VPCEndpoint]:
        """VPC Endpoint 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_vpc_endpoints(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    # =========================================================================
    # Network 카테고리 (Advanced)
    # =========================================================================

    def collect_transit_gateways(self) -> list[TransitGateway]:
        """Transit Gateway 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_transit_gateways(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_transit_gateway_attachments(self) -> list[TransitGatewayAttachment]:
        """Transit Gateway Attachment 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_transit_gateway_attachments(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_vpn_gateways(self) -> list[VPNGateway]:
        """VPN Gateway 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_vpn_gateways(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_vpn_connections(self) -> list[VPNConnection]:
        """VPN Connection 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_vpn_connections(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_network_acls(self) -> list[NetworkACL]:
        """Network ACL 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_network_acls(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_vpc_peering_connections(self) -> list[VPCPeeringConnection]:
        """VPC Peering Connection 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_vpc_peering_connections(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    # =========================================================================
    # Compute 카테고리
    # =========================================================================

    def collect_ec2(self) -> list[EC2Instance]:
        """EC2 인스턴스 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_ec2_instances(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_ebs_volumes(self) -> list[EBSVolume]:
        """EBS Volume 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_ebs_volumes(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_lambda_functions(self) -> list[LambdaFunction]:
        """Lambda Function 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_lambda_functions(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="lambda")
        return result.get_flat_data()

    def collect_ecs_clusters(self) -> list[ECSCluster]:
        """ECS Cluster 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_ecs_clusters(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ecs")
        return result.get_flat_data()

    def collect_ecs_services(self) -> list[ECSService]:
        """ECS Service 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_ecs_services(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ecs")
        return result.get_flat_data()

    def collect_auto_scaling_groups(self) -> list[AutoScalingGroup]:
        """Auto Scaling Group 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_auto_scaling_groups(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="autoscaling")
        return result.get_flat_data()

    def collect_launch_templates(self) -> list[LaunchTemplate]:
        """Launch Template 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_launch_templates(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_eks_clusters(self) -> list[EKSCluster]:
        """EKS Cluster 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_eks_clusters(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="eks")
        return result.get_flat_data()

    def collect_eks_node_groups(self) -> list[EKSNodeGroup]:
        """EKS Node Group 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_eks_node_groups(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="eks")
        return result.get_flat_data()

    def collect_amis(self) -> list[AMI]:
        """EC2 AMI (자체 소유) 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_amis(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_snapshots(self) -> list[Snapshot]:
        """EC2 Snapshot (자체 소유) 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_snapshots(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    # =========================================================================
    # Database/Storage 카테고리
    # =========================================================================

    def collect_rds_instances(self) -> list[RDSInstance]:
        """RDS Instance 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_rds_instances(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="rds")
        return result.get_flat_data()

    def collect_rds_clusters(self) -> list[RDSCluster]:
        """RDS Cluster (Aurora) 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_rds_clusters(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="rds")
        return result.get_flat_data()

    def collect_s3_buckets(self) -> list[S3Bucket]:
        """S3 Bucket 수집 (글로벌 - us-east-1에서만)"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_s3_buckets(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="s3")
        return result.get_flat_data()

    def collect_dynamodb_tables(self) -> list[DynamoDBTable]:
        """DynamoDB Table 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_dynamodb_tables(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="dynamodb")
        return result.get_flat_data()

    def collect_elasticache_clusters(self) -> list[ElastiCacheCluster]:
        """ElastiCache Cluster 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_elasticache_clusters(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="elasticache")
        return result.get_flat_data()

    def collect_redshift_clusters(self) -> list[RedshiftCluster]:
        """Redshift Cluster 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_redshift_clusters(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="redshift")
        return result.get_flat_data()

    def collect_efs_file_systems(self) -> list[EFSFileSystem]:
        """EFS File System 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_efs_file_systems(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="efs")
        return result.get_flat_data()

    def collect_fsx_file_systems(self) -> list[FSxFileSystem]:
        """FSx File System 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_fsx_file_systems(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="fsx")
        return result.get_flat_data()

    # =========================================================================
    # Security 카테고리
    # =========================================================================

    def collect_security_groups(self) -> list[SecurityGroup]:
        """Security Group 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_security_groups(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_kms_keys(self) -> list[KMSKey]:
        """KMS Key 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_kms_keys(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="kms")
        return result.get_flat_data()

    def collect_secrets(self) -> list[Secret]:
        """Secrets Manager Secret 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_secrets(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="secretsmanager")
        return result.get_flat_data()

    def collect_iam_roles(self) -> list[IAMRole]:
        """IAM Role 수집 (글로벌)"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_iam_roles(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="iam")
        return result.get_flat_data()

    def collect_iam_users(self) -> list[IAMUser]:
        """IAM User 수집 (글로벌)"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_iam_users(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="iam")
        return result.get_flat_data()

    def collect_iam_policies(self) -> list[IAMPolicy]:
        """IAM Policy (Customer Managed) 수집 (글로벌)"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_iam_policies(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="iam")
        return result.get_flat_data()

    def collect_acm_certificates(self) -> list[ACMCertificate]:
        """ACM Certificate 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_acm_certificates(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="acm")
        return result.get_flat_data()

    def collect_waf_web_acls(self) -> list[WAFWebACL]:
        """WAF WebACL 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_waf_web_acls(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="wafv2")
        return result.get_flat_data()

    # =========================================================================
    # CDN/DNS 카테고리
    # =========================================================================

    def collect_cloudfront_distributions(self) -> list[CloudFrontDistribution]:
        """CloudFront Distribution 수집 (글로벌 - us-east-1에서만)"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_cloudfront_distributions(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="cloudfront")
        return result.get_flat_data()

    def collect_route53_hosted_zones(self) -> list[Route53HostedZone]:
        """Route 53 Hosted Zone 수집 (글로벌 - us-east-1에서만)"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_route53_hosted_zones(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="route53")
        return result.get_flat_data()

    # =========================================================================
    # Load Balancing 카테고리
    # =========================================================================

    def collect_load_balancers(self, include_classic: bool = False) -> list[LoadBalancer]:
        """Load Balancer 수집

        Args:
            include_classic: True면 Classic LB도 포함
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_load_balancers(session, account_id, account_name, region, include_classic=include_classic)

        result = parallel_collect(self._ctx, _collect, service="elasticloadbalancing")
        return result.get_flat_data()

    def collect_target_groups(self) -> list[TargetGroup]:
        """Target Group 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_target_groups(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="elasticloadbalancing")
        return result.get_flat_data()

    # =========================================================================
    # Integration/Messaging 카테고리
    # =========================================================================

    def collect_sns_topics(self) -> list[SNSTopic]:
        """SNS Topic 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_sns_topics(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="sns")
        return result.get_flat_data()

    def collect_sqs_queues(self) -> list[SQSQueue]:
        """SQS Queue 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_sqs_queues(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="sqs")
        return result.get_flat_data()

    def collect_eventbridge_rules(self) -> list[EventBridgeRule]:
        """EventBridge Rule 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_eventbridge_rules(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="events")
        return result.get_flat_data()

    def collect_step_functions(self) -> list[StepFunction]:
        """Step Functions State Machine 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_step_functions(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="stepfunctions")
        return result.get_flat_data()

    def collect_api_gateway_apis(self) -> list[APIGatewayAPI]:
        """API Gateway REST/HTTP API 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_api_gateway_apis(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="apigateway")
        return result.get_flat_data()

    # =========================================================================
    # Monitoring 카테고리
    # =========================================================================

    def collect_cloudwatch_alarms(self) -> list[CloudWatchAlarm]:
        """CloudWatch Alarm 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_cloudwatch_alarms(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="cloudwatch")
        return result.get_flat_data()

    def collect_cloudwatch_log_groups(self) -> list[CloudWatchLogGroup]:
        """CloudWatch Log Group 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_cloudwatch_log_groups(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="logs")
        return result.get_flat_data()

    # =========================================================================
    # Analytics 카테고리
    # =========================================================================

    def collect_kinesis_streams(self) -> list[KinesisStream]:
        """Kinesis Data Stream 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_kinesis_streams(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="kinesis")
        return result.get_flat_data()

    def collect_kinesis_firehoses(self) -> list[KinesisFirehose]:
        """Kinesis Firehose Delivery Stream 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_kinesis_firehoses(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="firehose")
        return result.get_flat_data()

    def collect_glue_databases(self) -> list[GlueDatabase]:
        """Glue Database 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_glue_databases(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="glue")
        return result.get_flat_data()

    # =========================================================================
    # DevOps 카테고리
    # =========================================================================

    def collect_cloudformation_stacks(self) -> list[CloudFormationStack]:
        """CloudFormation Stack 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_cloudformation_stacks(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="cloudformation")
        return result.get_flat_data()

    def collect_codepipelines(self) -> list[CodePipeline]:
        """CodePipeline 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_codepipelines(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="codepipeline")
        return result.get_flat_data()

    def collect_codebuild_projects(self) -> list[CodeBuildProject]:
        """CodeBuild Project 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_codebuild_projects(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="codebuild")
        return result.get_flat_data()

    # =========================================================================
    # Backup 카테고리
    # =========================================================================

    def collect_backup_vaults(self) -> list[BackupVault]:
        """Backup Vault 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_backup_vaults(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="backup")
        return result.get_flat_data()

    def collect_backup_plans(self) -> list[BackupPlan]:
        """Backup Plan 수집"""

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_backup_plans(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="backup")
        return result.get_flat_data()
