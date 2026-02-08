"""
core/shared/aws/inventory/collector.py - 인벤토리 수집기

병렬로 AWS 리소스를 수집하는 통합 클래스.

``InventoryCollector``는 ``parallel_collect``를 사용하여 멀티 계정/리전에서
60종의 AWS 리소스를 병렬로 수집합니다. 각 수집 메서드는 해당 리소스 타입의
데이터 클래스 목록을 반환합니다.

카테고리:
    - Network (14): VPC, Subnet, RouteTable, InternetGateway, ElasticIP, ENI, NATGateway,
      VPCEndpoint, TransitGateway, TransitGatewayAttachment, VPNGateway, VPNConnection,
      NetworkACL, VPCPeeringConnection
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

Example:
    >>> from core.shared.aws.inventory import InventoryCollector
    >>> collector = InventoryCollector(ctx)
    >>> vpcs = collector.collect_vpcs()
    >>> instances = collector.collect_ec2()
"""

from __future__ import annotations

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
    """AWS 리소스 인벤토리 수집기.

    ``parallel_collect``를 사용하여 멀티 계정/리전에서 AWS 리소스를 병렬로 수집합니다.
    11개 카테고리, 60종의 리소스 타입을 지원하며 각 수집 메서드는 해당 타입의
    데이터 클래스 목록을 반환합니다.

    글로벌 리소스(IAM, S3, CloudFront, Route53)는 us-east-1에서만 수집되며,
    리전 리소스는 ExecutionContext에 지정된 모든 리전에서 병렬 수집됩니다.

    Example:
        >>> collector = InventoryCollector(ctx)
        >>> vpcs = collector.collect_vpcs()
        >>> instances = collector.collect_ec2()
        >>> rds_instances = collector.collect_rds_instances()
    """

    def __init__(self, ctx):
        """InventoryCollector를 초기화합니다.

        Args:
            ctx: ExecutionContext 객체. provider, regions, accounts 정보를 포함합니다.
        """
        self._ctx = ctx

    # =========================================================================
    # Network 카테고리 (Basic)
    # =========================================================================

    def collect_vpcs(self) -> list[VPC]:
        """모든 계정/리전에서 VPC 리소스를 병렬 수집합니다.

        Returns:
            VPC 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_vpcs(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_subnets(self) -> list[Subnet]:
        """모든 계정/리전에서 Subnet 리소스를 병렬 수집합니다.

        Returns:
            Subnet 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_subnets(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_route_tables(self) -> list[RouteTable]:
        """모든 계정/리전에서 Route Table 리소스를 병렬 수집합니다.

        Returns:
            RouteTable 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_route_tables(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_internet_gateways(self) -> list[InternetGateway]:
        """모든 계정/리전에서 Internet Gateway 리소스를 병렬 수집합니다.

        Returns:
            InternetGateway 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_internet_gateways(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_elastic_ips(self) -> list[ElasticIP]:
        """모든 계정/리전에서 Elastic IP 리소스를 병렬 수집합니다.

        Returns:
            ElasticIP 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_elastic_ips(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_enis(self) -> list[ENI]:
        """모든 계정/리전에서 Elastic Network Interface를 병렬 수집합니다.

        Returns:
            ENI 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_enis(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_nat_gateways(self) -> list[NATGateway]:
        """모든 계정/리전에서 NAT Gateway 리소스를 병렬 수집합니다.

        Returns:
            NATGateway 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_nat_gateways(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_vpc_endpoints(self) -> list[VPCEndpoint]:
        """모든 계정/리전에서 VPC Endpoint 리소스를 병렬 수집합니다.

        Returns:
            VPCEndpoint 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_vpc_endpoints(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    # =========================================================================
    # Network 카테고리 (Advanced)
    # =========================================================================

    def collect_transit_gateways(self) -> list[TransitGateway]:
        """모든 계정/리전에서 Transit Gateway 리소스를 병렬 수집합니다.

        Returns:
            TransitGateway 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_transit_gateways(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_transit_gateway_attachments(self) -> list[TransitGatewayAttachment]:
        """모든 계정/리전에서 Transit Gateway Attachment를 병렬 수집합니다.

        Returns:
            TransitGatewayAttachment 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_transit_gateway_attachments(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_vpn_gateways(self) -> list[VPNGateway]:
        """모든 계정/리전에서 VPN Gateway 리소스를 병렬 수집합니다.

        Returns:
            VPNGateway 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_vpn_gateways(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_vpn_connections(self) -> list[VPNConnection]:
        """모든 계정/리전에서 VPN Connection 리소스를 병렬 수집합니다.

        Returns:
            VPNConnection 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_vpn_connections(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_network_acls(self) -> list[NetworkACL]:
        """모든 계정/리전에서 Network ACL 리소스를 병렬 수집합니다.

        Returns:
            NetworkACL 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_network_acls(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_vpc_peering_connections(self) -> list[VPCPeeringConnection]:
        """모든 계정/리전에서 VPC Peering Connection을 병렬 수집합니다.

        Returns:
            VPCPeeringConnection 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_vpc_peering_connections(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    # =========================================================================
    # Compute 카테고리
    # =========================================================================

    def collect_ec2(self) -> list[EC2Instance]:
        """모든 계정/리전에서 EC2 인스턴스를 병렬 수집합니다.

        Returns:
            EC2Instance 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_ec2_instances(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_ebs_volumes(self) -> list[EBSVolume]:
        """모든 계정/리전에서 EBS Volume 리소스를 병렬 수집합니다.

        Returns:
            EBSVolume 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_ebs_volumes(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_lambda_functions(self) -> list[LambdaFunction]:
        """모든 계정/리전에서 Lambda Function을 병렬 수집합니다.

        Returns:
            LambdaFunction 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_lambda_functions(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="lambda")
        return result.get_flat_data()

    def collect_ecs_clusters(self) -> list[ECSCluster]:
        """모든 계정/리전에서 ECS Cluster 리소스를 병렬 수집합니다.

        Returns:
            ECSCluster 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_ecs_clusters(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ecs")
        return result.get_flat_data()

    def collect_ecs_services(self) -> list[ECSService]:
        """모든 계정/리전에서 ECS Service를 병렬 수집합니다.

        Returns:
            ECSService 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_ecs_services(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ecs")
        return result.get_flat_data()

    def collect_auto_scaling_groups(self) -> list[AutoScalingGroup]:
        """모든 계정/리전에서 Auto Scaling Group을 병렬 수집합니다.

        Returns:
            AutoScalingGroup 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_auto_scaling_groups(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="autoscaling")
        return result.get_flat_data()

    def collect_launch_templates(self) -> list[LaunchTemplate]:
        """모든 계정/리전에서 Launch Template 리소스를 병렬 수집합니다.

        Returns:
            LaunchTemplate 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_launch_templates(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_eks_clusters(self) -> list[EKSCluster]:
        """모든 계정/리전에서 EKS Cluster 리소스를 병렬 수집합니다.

        Returns:
            EKSCluster 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_eks_clusters(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="eks")
        return result.get_flat_data()

    def collect_eks_node_groups(self) -> list[EKSNodeGroup]:
        """모든 계정/리전에서 EKS Node Group을 병렬 수집합니다.

        Returns:
            EKSNodeGroup 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_eks_node_groups(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="eks")
        return result.get_flat_data()

    def collect_amis(self) -> list[AMI]:
        """모든 계정/리전에서 자체 소유 EC2 AMI를 병렬 수집합니다.

        Returns:
            AMI 데이터 클래스 목록 (자체 소유 이미지만 포함)
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_amis(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_snapshots(self) -> list[Snapshot]:
        """모든 계정/리전에서 자체 소유 EC2 Snapshot을 병렬 수집합니다.

        Returns:
            Snapshot 데이터 클래스 목록 (자체 소유 스냅샷만 포함)
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_snapshots(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    # =========================================================================
    # Database/Storage 카테고리
    # =========================================================================

    def collect_rds_instances(self) -> list[RDSInstance]:
        """모든 계정/리전에서 RDS Instance를 병렬 수집합니다.

        Returns:
            RDSInstance 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_rds_instances(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="rds")
        return result.get_flat_data()

    def collect_rds_clusters(self) -> list[RDSCluster]:
        """모든 계정/리전에서 RDS Cluster (Aurora)를 병렬 수집합니다.

        Returns:
            RDSCluster 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_rds_clusters(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="rds")
        return result.get_flat_data()

    def collect_s3_buckets(self) -> list[S3Bucket]:
        """모든 계정에서 S3 Bucket을 병렬 수집합니다.

        S3는 글로벌 서비스이므로 us-east-1에서만 수집됩니다.

        Returns:
            S3Bucket 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_s3_buckets(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="s3")
        return result.get_flat_data()

    def collect_dynamodb_tables(self) -> list[DynamoDBTable]:
        """모든 계정/리전에서 DynamoDB Table을 병렬 수집합니다.

        Returns:
            DynamoDBTable 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_dynamodb_tables(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="dynamodb")
        return result.get_flat_data()

    def collect_elasticache_clusters(self) -> list[ElastiCacheCluster]:
        """모든 계정/리전에서 ElastiCache Cluster를 병렬 수집합니다.

        Returns:
            ElastiCacheCluster 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_elasticache_clusters(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="elasticache")
        return result.get_flat_data()

    def collect_redshift_clusters(self) -> list[RedshiftCluster]:
        """모든 계정/리전에서 Redshift Cluster를 병렬 수집합니다.

        Returns:
            RedshiftCluster 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_redshift_clusters(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="redshift")
        return result.get_flat_data()

    def collect_efs_file_systems(self) -> list[EFSFileSystem]:
        """모든 계정/리전에서 EFS File System을 병렬 수집합니다.

        Returns:
            EFSFileSystem 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_efs_file_systems(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="efs")
        return result.get_flat_data()

    def collect_fsx_file_systems(self) -> list[FSxFileSystem]:
        """모든 계정/리전에서 FSx File System을 병렬 수집합니다.

        Returns:
            FSxFileSystem 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_fsx_file_systems(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="fsx")
        return result.get_flat_data()

    # =========================================================================
    # Security 카테고리
    # =========================================================================

    def collect_security_groups(self) -> list[SecurityGroup]:
        """모든 계정/리전에서 Security Group을 병렬 수집합니다.

        Returns:
            SecurityGroup 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_security_groups(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="ec2")
        return result.get_flat_data()

    def collect_kms_keys(self) -> list[KMSKey]:
        """모든 계정/리전에서 KMS Key를 병렬 수집합니다.

        Returns:
            KMSKey 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_kms_keys(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="kms")
        return result.get_flat_data()

    def collect_secrets(self) -> list[Secret]:
        """모든 계정/리전에서 Secrets Manager Secret을 병렬 수집합니다.

        Returns:
            Secret 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_secrets(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="secretsmanager")
        return result.get_flat_data()

    def collect_iam_roles(self) -> list[IAMRole]:
        """모든 계정에서 IAM Role을 병렬 수집합니다.

        IAM은 글로벌 서비스이므로 us-east-1에서만 수집됩니다.

        Returns:
            IAMRole 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_iam_roles(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="iam")
        return result.get_flat_data()

    def collect_iam_users(self) -> list[IAMUser]:
        """모든 계정에서 IAM User를 병렬 수집합니다.

        IAM은 글로벌 서비스이므로 us-east-1에서만 수집됩니다.

        Returns:
            IAMUser 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_iam_users(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="iam")
        return result.get_flat_data()

    def collect_iam_policies(self) -> list[IAMPolicy]:
        """모든 계정에서 Customer Managed IAM Policy를 병렬 수집합니다.

        IAM은 글로벌 서비스이므로 us-east-1에서만 수집됩니다.
        AWS Managed Policy는 제외되고 Customer Managed Policy만 포함됩니다.

        Returns:
            IAMPolicy 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_iam_policies(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="iam")
        return result.get_flat_data()

    def collect_acm_certificates(self) -> list[ACMCertificate]:
        """모든 계정/리전에서 ACM Certificate를 병렬 수집합니다.

        Returns:
            ACMCertificate 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_acm_certificates(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="acm")
        return result.get_flat_data()

    def collect_waf_web_acls(self) -> list[WAFWebACL]:
        """모든 계정/리전에서 WAF WebACL을 병렬 수집합니다.

        Regional WebACL과 CloudFront WebACL(us-east-1에서만)을 모두 수집합니다.

        Returns:
            WAFWebACL 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_waf_web_acls(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="wafv2")
        return result.get_flat_data()

    # =========================================================================
    # CDN/DNS 카테고리
    # =========================================================================

    def collect_cloudfront_distributions(self) -> list[CloudFrontDistribution]:
        """모든 계정에서 CloudFront Distribution을 병렬 수집합니다.

        CloudFront는 글로벌 서비스이므로 us-east-1에서만 수집됩니다.

        Returns:
            CloudFrontDistribution 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_cloudfront_distributions(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="cloudfront")
        return result.get_flat_data()

    def collect_route53_hosted_zones(self) -> list[Route53HostedZone]:
        """모든 계정에서 Route 53 Hosted Zone을 병렬 수집합니다.

        Route 53는 글로벌 서비스이므로 us-east-1에서만 수집됩니다.

        Returns:
            Route53HostedZone 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_route53_hosted_zones(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="route53")
        return result.get_flat_data()

    # =========================================================================
    # Load Balancing 카테고리
    # =========================================================================

    def collect_load_balancers(self, include_classic: bool = False) -> list[LoadBalancer]:
        """모든 계정/리전에서 Load Balancer를 병렬 수집합니다.

        기본적으로 ALB/NLB/GWLB만 수집하며, include_classic=True 시 Classic LB도 포함합니다.

        Args:
            include_classic: True면 Classic LB도 포함합니다.

        Returns:
            LoadBalancer 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_load_balancers(session, account_id, account_name, region, include_classic=include_classic)

        result = parallel_collect(self._ctx, _collect, service="elasticloadbalancing")
        return result.get_flat_data()

    def collect_target_groups(self) -> list[TargetGroup]:
        """모든 계정/리전에서 Target Group을 병렬 수집합니다.

        Returns:
            TargetGroup 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_target_groups(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="elasticloadbalancing")
        return result.get_flat_data()

    # =========================================================================
    # Integration/Messaging 카테고리
    # =========================================================================

    def collect_sns_topics(self) -> list[SNSTopic]:
        """모든 계정/리전에서 SNS Topic을 병렬 수집합니다.

        Returns:
            SNSTopic 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_sns_topics(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="sns")
        return result.get_flat_data()

    def collect_sqs_queues(self) -> list[SQSQueue]:
        """모든 계정/리전에서 SQS Queue를 병렬 수집합니다.

        Returns:
            SQSQueue 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_sqs_queues(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="sqs")
        return result.get_flat_data()

    def collect_eventbridge_rules(self) -> list[EventBridgeRule]:
        """모든 계정/리전에서 EventBridge Rule을 병렬 수집합니다.

        Returns:
            EventBridgeRule 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_eventbridge_rules(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="events")
        return result.get_flat_data()

    def collect_step_functions(self) -> list[StepFunction]:
        """모든 계정/리전에서 Step Functions State Machine을 병렬 수집합니다.

        Returns:
            StepFunction 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_step_functions(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="stepfunctions")
        return result.get_flat_data()

    def collect_api_gateway_apis(self) -> list[APIGatewayAPI]:
        """모든 계정/리전에서 API Gateway REST/HTTP API를 병렬 수집합니다.

        REST API (v1)와 HTTP/WebSocket API (v2)를 모두 수집합니다.

        Returns:
            APIGatewayAPI 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_api_gateway_apis(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="apigateway")
        return result.get_flat_data()

    # =========================================================================
    # Monitoring 카테고리
    # =========================================================================

    def collect_cloudwatch_alarms(self) -> list[CloudWatchAlarm]:
        """모든 계정/리전에서 CloudWatch Alarm을 병렬 수집합니다.

        Returns:
            CloudWatchAlarm 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_cloudwatch_alarms(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="cloudwatch")
        return result.get_flat_data()

    def collect_cloudwatch_log_groups(self) -> list[CloudWatchLogGroup]:
        """모든 계정/리전에서 CloudWatch Log Group을 병렬 수집합니다.

        Returns:
            CloudWatchLogGroup 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_cloudwatch_log_groups(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="logs")
        return result.get_flat_data()

    # =========================================================================
    # Analytics 카테고리
    # =========================================================================

    def collect_kinesis_streams(self) -> list[KinesisStream]:
        """모든 계정/리전에서 Kinesis Data Stream을 병렬 수집합니다.

        Returns:
            KinesisStream 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_kinesis_streams(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="kinesis")
        return result.get_flat_data()

    def collect_kinesis_firehoses(self) -> list[KinesisFirehose]:
        """모든 계정/리전에서 Kinesis Firehose Delivery Stream을 병렬 수집합니다.

        Returns:
            KinesisFirehose 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_kinesis_firehoses(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="firehose")
        return result.get_flat_data()

    def collect_glue_databases(self) -> list[GlueDatabase]:
        """모든 계정/리전에서 Glue Database를 병렬 수집합니다.

        Returns:
            GlueDatabase 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_glue_databases(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="glue")
        return result.get_flat_data()

    # =========================================================================
    # DevOps 카테고리
    # =========================================================================

    def collect_cloudformation_stacks(self) -> list[CloudFormationStack]:
        """모든 계정/리전에서 CloudFormation Stack을 병렬 수집합니다.

        Returns:
            CloudFormationStack 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_cloudformation_stacks(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="cloudformation")
        return result.get_flat_data()

    def collect_codepipelines(self) -> list[CodePipeline]:
        """모든 계정/리전에서 CodePipeline을 병렬 수집합니다.

        Returns:
            CodePipeline 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_codepipelines(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="codepipeline")
        return result.get_flat_data()

    def collect_codebuild_projects(self) -> list[CodeBuildProject]:
        """모든 계정/리전에서 CodeBuild Project를 병렬 수집합니다.

        Returns:
            CodeBuildProject 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_codebuild_projects(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="codebuild")
        return result.get_flat_data()

    # =========================================================================
    # Backup 카테고리
    # =========================================================================

    def collect_backup_vaults(self) -> list[BackupVault]:
        """모든 계정/리전에서 Backup Vault를 병렬 수집합니다.

        Returns:
            BackupVault 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_backup_vaults(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="backup")
        return result.get_flat_data()

    def collect_backup_plans(self) -> list[BackupPlan]:
        """모든 계정/리전에서 Backup Plan을 병렬 수집합니다.

        Returns:
            BackupPlan 데이터 클래스 목록
        """

        def _collect(session, account_id: str, account_name: str, region: str):
            return collect_backup_plans(session, account_id, account_name, region)

        result = parallel_collect(self._ctx, _collect, service="backup")
        return result.get_flat_data()
