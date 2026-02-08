"""
shared/aws/inventory - 리소스 인벤토리 공통 모듈

InventoryCollector와 데이터 타입을 제공합니다.

카테고리:
- Network (14): VPC, Subnet, RouteTable, InternetGateway, ElasticIP, ENI, NATGateway, VPCEndpoint,
                TransitGateway, TransitGatewayAttachment, VPNGateway, VPNConnection, NetworkACL, VPCPeeringConnection
- Compute (11): EC2Instance, EBSVolume, LambdaFunction, ECSCluster, ECSService,
                AutoScalingGroup, LaunchTemplate, EKSCluster, EKSNodeGroup, AMI, Snapshot
- Database/Storage (8): RDSInstance, RDSCluster, S3Bucket, DynamoDBTable, ElastiCacheCluster,
                        RedshiftCluster, EFSFileSystem, FSxFileSystem
- Security (8): SecurityGroup, KMSKey, Secret, IAMRole, IAMUser, IAMPolicy, ACMCertificate, WAFWebACL
- CDN/DNS (2): CloudFrontDistribution, Route53HostedZone
- Load Balancing (2): LoadBalancer, TargetGroup
- Integration/Messaging (5): SNSTopic, SQSQueue, EventBridgeRule, StepFunction, APIGatewayAPI
- Monitoring (2): CloudWatchAlarm, CloudWatchLogGroup
- Analytics (3): KinesisStream, KinesisFirehose, GlueDatabase
- DevOps (3): CloudFormationStack, CodePipeline, CodeBuildProject
- Backup (2): BackupVault, BackupPlan

Total: 60 resource types
"""

from .collector import InventoryCollector
from .types import (
    # Compute
    AMI,
    # Network
    ENI,
    VPC,
    # Security
    ACMCertificate,
    # Integration/Messaging
    APIGatewayAPI,
    AutoScalingGroup,
    # Backup
    BackupPlan,
    BackupVault,
    # DevOps
    CloudFormationStack,
    # CDN/DNS
    CloudFrontDistribution,
    # Monitoring
    CloudWatchAlarm,
    CloudWatchLogGroup,
    CodeBuildProject,
    CodePipeline,
    # Database/Storage
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
    # Analytics
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
    # Load Balancing
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

__all__ = [
    "InventoryCollector",
    # Network (Basic)
    "VPC",
    "Subnet",
    "RouteTable",
    "InternetGateway",
    "ElasticIP",
    "ENI",
    "NATGateway",
    "VPCEndpoint",
    # Network (Advanced)
    "TransitGateway",
    "TransitGatewayAttachment",
    "VPNGateway",
    "VPNConnection",
    "NetworkACL",
    "VPCPeeringConnection",
    # Compute
    "EC2Instance",
    "EBSVolume",
    "LambdaFunction",
    "ECSCluster",
    "ECSService",
    "AutoScalingGroup",
    "LaunchTemplate",
    "EKSCluster",
    "EKSNodeGroup",
    "AMI",
    "Snapshot",
    # Database/Storage
    "RDSInstance",
    "RDSCluster",
    "S3Bucket",
    "DynamoDBTable",
    "ElastiCacheCluster",
    "RedshiftCluster",
    "EFSFileSystem",
    "FSxFileSystem",
    # Security
    "SecurityGroup",
    "KMSKey",
    "Secret",
    "IAMRole",
    "IAMUser",
    "IAMPolicy",
    "ACMCertificate",
    "WAFWebACL",
    # CDN/DNS
    "CloudFrontDistribution",
    "Route53HostedZone",
    # Load Balancing
    "LoadBalancer",
    "TargetGroup",
    # Integration/Messaging
    "SNSTopic",
    "SQSQueue",
    "EventBridgeRule",
    "StepFunction",
    "APIGatewayAPI",
    # Monitoring
    "CloudWatchAlarm",
    "CloudWatchLogGroup",
    # Analytics
    "KinesisStream",
    "KinesisFirehose",
    "GlueDatabase",
    # DevOps
    "CloudFormationStack",
    "CodePipeline",
    "CodeBuildProject",
    # Backup
    "BackupVault",
    "BackupPlan",
]
