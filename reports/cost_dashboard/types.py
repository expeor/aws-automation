"""
plugins/cost/unused_all/types.py - 미사용 리소스 분석 데이터 타입

데이터클래스 및 리소스 필드 매핑 정의
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 각 도구의 결과 타입 import
from plugins.acm.unused import ACMAnalysisResult
from plugins.apigateway.unused import APIGatewayAnalysisResult
from plugins.cloudwatch.alarm_orphan import AlarmAnalysisResult
from plugins.cloudwatch.loggroup_audit import LogGroupAnalysisResult
from plugins.dynamodb.unused import DynamoDBAnalysisResult
from plugins.ec2.ami_audit import AMIAnalysisResult
from plugins.ec2.ebs_audit import EBSAnalysisResult
from plugins.ec2.eip_audit import EIPAnalysisResult
from plugins.ec2.snapshot_audit import SnapshotAnalysisResult
from plugins.ec2.unused import EC2AnalysisResult
from plugins.ecr.unused import ECRAnalysisResult
from plugins.efs.unused import EFSAnalysisResult
from plugins.elasticache.unused import ElastiCacheAnalysisResult
from plugins.elb.target_group_audit import TargetGroupAnalysisResult
from plugins.elb.unused import LBAnalysisResult
from plugins.eventbridge.unused import EventBridgeAnalysisResult
from plugins.fn.unused import LambdaAnalysisResult
from plugins.fsx.unused import FSxAnalysisResult
from plugins.glue.unused import GlueAnalysisResult
from plugins.kinesis.unused import KinesisAnalysisResult
from plugins.kms.unused import KMSKeyAnalysisResult
from plugins.opensearch.unused import OpenSearchAnalysisResult
from plugins.rds.snapshot_audit import RDSSnapshotAnalysisResult
from plugins.rds.unused import RDSAnalysisResult as RDSInstanceAnalysisResult
from plugins.redshift.unused import RedshiftAnalysisResult
from plugins.route53.empty_zone import Route53AnalysisResult
from plugins.s3.empty_bucket import S3AnalysisResult
from plugins.sagemaker.unused import SageMakerAnalysisResult
from plugins.secretsmanager.unused import SecretAnalysisResult
from plugins.sns.unused import SNSAnalysisResult
from plugins.sqs.unused import SQSAnalysisResult
from plugins.transfer.unused import TransferAnalysisResult
from plugins.vpc.endpoint_audit import EndpointAnalysisResult
from plugins.vpc.eni_audit import ENIAnalysisResult
from plugins.vpc.sg_audit_analysis import SGAnalysisResult

# =============================================================================
# 리소스 설정 (카테고리별 그룹화)
# =============================================================================

# 리소스별 필드 매핑
# - display: 표시 이름
# - total/unused/waste: summary 필드명
# - data_unused: collector 반환 데이터의 unused 키 (unused, old, issue, orphan 등)
# - session/final: 세션/최종 결과의 필드명
# - data_key: collector 반환 데이터의 결과 키 (result, findings)
RESOURCE_FIELD_MAP: dict[str, dict[str, Any]] = {
    # =========================================================================
    # Compute (EC2)
    # =========================================================================
    "ami": {
        "display": "AMI",
        "total": "ami_total",
        "unused": "ami_unused",
        "waste": "ami_monthly_waste",
        "data_unused": "unused",
        "session": "ami_result",
        "final": "ami_results",
        "data_key": "result",
    },
    "ebs": {
        "display": "EBS",
        "total": "ebs_total",
        "unused": "ebs_unused",
        "waste": "ebs_monthly_waste",
        "data_unused": "unused",
        "session": "ebs_result",
        "final": "ebs_results",
        "data_key": "result",
    },
    "snapshot": {
        "display": "EBS Snapshot",
        "total": "snap_total",
        "unused": "snap_unused",
        "waste": "snap_monthly_waste",
        "data_unused": "unused",
        "session": "snap_result",
        "final": "snap_results",
        "data_key": "result",
    },
    "eip": {
        "display": "EIP",
        "total": "eip_total",
        "unused": "eip_unused",
        "waste": "eip_monthly_waste",
        "data_unused": "unused",
        "session": "eip_result",
        "final": "eip_results",
        "data_key": "result",
    },
    "eni": {
        "display": "ENI",
        "total": "eni_total",
        "unused": "eni_unused",
        "waste": None,
        "data_unused": "unused",
        "session": "eni_result",
        "final": "eni_results",
        "data_key": "result",
    },
    "ec2_instance": {
        "display": "EC2 Instance",
        "total": "ec2_instance_total",
        "unused": "ec2_instance_unused",
        "waste": "ec2_instance_monthly_waste",
        "data_unused": "unused",
        "session": "ec2_instance_result",
        "final": "ec2_instance_results",
        "data_key": "result",
    },
    # =========================================================================
    # Networking (VPC)
    # =========================================================================
    "nat": {
        "display": "NAT Gateway",
        "total": "nat_total",
        "unused": "nat_unused",
        "waste": "nat_monthly_waste",
        "data_unused": "unused",
        "session": "nat_findings",
        "final": "nat_findings",
        "data_key": "findings",
    },
    "endpoint": {
        "display": "VPC Endpoint",
        "total": "endpoint_total",
        "unused": "endpoint_unused",
        "waste": "endpoint_monthly_waste",
        "data_unused": "unused",
        "session": "endpoint_result",
        "final": "endpoint_results",
        "data_key": "result",
    },
    # =========================================================================
    # Load Balancing
    # =========================================================================
    "elb": {
        "display": "ELB",
        "total": "elb_total",
        "unused": "elb_unused",
        "waste": "elb_monthly_waste",
        "data_unused": "unused",
        "session": "elb_result",
        "final": "elb_results",
        "data_key": "result",
    },
    "target_group": {
        "display": "Target Group",
        "total": "tg_total",
        "unused": "tg_unused",
        "waste": None,
        "data_unused": "issue",
        "session": "tg_result",
        "final": "tg_results",
        "data_key": "result",
    },
    # =========================================================================
    # Database
    # =========================================================================
    "dynamodb": {
        "display": "DynamoDB",
        "total": "dynamodb_total",
        "unused": "dynamodb_unused",
        "waste": "dynamodb_monthly_waste",
        "data_unused": "unused",
        "session": "dynamodb_result",
        "final": "dynamodb_results",
        "data_key": "result",
    },
    "elasticache": {
        "display": "ElastiCache",
        "total": "elasticache_total",
        "unused": "elasticache_unused",
        "waste": "elasticache_monthly_waste",
        "data_unused": "unused",
        "session": "elasticache_result",
        "final": "elasticache_results",
        "data_key": "result",
    },
    "redshift": {
        "display": "Redshift",
        "total": "redshift_total",
        "unused": "redshift_unused",
        "waste": "redshift_monthly_waste",
        "data_unused": "unused",
        "session": "redshift_result",
        "final": "redshift_results",
        "data_key": "result",
    },
    "opensearch": {
        "display": "OpenSearch",
        "total": "opensearch_total",
        "unused": "opensearch_unused",
        "waste": "opensearch_monthly_waste",
        "data_unused": "unused",
        "session": "opensearch_result",
        "final": "opensearch_results",
        "data_key": "result",
    },
    "rds_instance": {
        "display": "RDS Instance",
        "total": "rds_instance_total",
        "unused": "rds_instance_unused",
        "waste": "rds_instance_monthly_waste",
        "data_unused": "unused",
        "session": "rds_instance_result",
        "final": "rds_instance_results",
        "data_key": "result",
    },
    "rds_snapshot": {
        "display": "RDS Snapshot",
        "total": "rds_snap_total",
        "unused": "rds_snap_unused",
        "waste": "rds_snap_monthly_waste",
        "data_unused": "old",
        "session": "rds_snap_result",
        "final": "rds_snap_results",
        "data_key": "result",
    },
    # =========================================================================
    # Storage
    # =========================================================================
    "ecr": {
        "display": "ECR",
        "total": "ecr_total",
        "unused": "ecr_unused",
        "waste": "ecr_monthly_waste",
        "data_unused": "issue",
        "session": "ecr_result",
        "final": "ecr_results",
        "data_key": "result",
    },
    "efs": {
        "display": "EFS",
        "total": "efs_total",
        "unused": "efs_unused",
        "waste": "efs_monthly_waste",
        "data_unused": "unused",
        "session": "efs_result",
        "final": "efs_results",
        "data_key": "result",
    },
    "s3": {
        "display": "S3",
        "total": "s3_total",
        "unused": "s3_unused",
        "waste": None,
        "data_unused": "empty",
        "session": "s3_result",
        "final": "s3_results",
        "data_key": "result",
        "is_global": True,
    },
    # =========================================================================
    # Serverless
    # =========================================================================
    "apigateway": {
        "display": "API Gateway",
        "total": "apigateway_total",
        "unused": "apigateway_unused",
        "waste": None,
        "data_unused": "unused",
        "session": "apigateway_result",
        "final": "apigateway_results",
        "data_key": "result",
    },
    "eventbridge": {
        "display": "EventBridge",
        "total": "eventbridge_total",
        "unused": "eventbridge_unused",
        "waste": None,
        "data_unused": "unused",
        "session": "eventbridge_result",
        "final": "eventbridge_results",
        "data_key": "result",
    },
    "lambda": {
        "display": "Lambda",
        "total": "lambda_total",
        "unused": "lambda_unused",
        "waste": "lambda_monthly_waste",
        "data_unused": "unused",
        "session": "lambda_result",
        "final": "lambda_results",
        "data_key": "result",
    },
    # =========================================================================
    # ML
    # =========================================================================
    "sagemaker_endpoint": {
        "display": "SageMaker Endpoint",
        "total": "sagemaker_endpoint_total",
        "unused": "sagemaker_endpoint_unused",
        "waste": "sagemaker_endpoint_monthly_waste",
        "data_unused": "unused",
        "session": "sagemaker_endpoint_result",
        "final": "sagemaker_endpoint_results",
        "data_key": "result",
    },
    # =========================================================================
    # Messaging
    # =========================================================================
    "sns": {
        "display": "SNS",
        "total": "sns_total",
        "unused": "sns_unused",
        "waste": None,
        "data_unused": "unused",
        "session": "sns_result",
        "final": "sns_results",
        "data_key": "result",
    },
    "sqs": {
        "display": "SQS",
        "total": "sqs_total",
        "unused": "sqs_unused",
        "waste": None,
        "data_unused": "unused",
        "session": "sqs_result",
        "final": "sqs_results",
        "data_key": "result",
    },
    # =========================================================================
    # Security
    # =========================================================================
    "acm": {
        "display": "ACM",
        "total": "acm_total",
        "unused": "acm_unused",
        "waste": None,
        "data_unused": "unused",
        "session": "acm_result",
        "final": "acm_results",
        "data_key": "result",
    },
    "kms": {
        "display": "KMS",
        "total": "kms_total",
        "unused": "kms_unused",
        "waste": "kms_monthly_waste",
        "data_unused": "unused",
        "session": "kms_result",
        "final": "kms_results",
        "data_key": "result",
    },
    "secret": {
        "display": "Secrets Manager",
        "total": "secret_total",
        "unused": "secret_unused",
        "waste": "secret_monthly_waste",
        "data_unused": "unused",
        "session": "secret_result",
        "final": "secret_results",
        "data_key": "result",
    },
    # =========================================================================
    # Monitoring
    # =========================================================================
    "cw_alarm": {
        "display": "CloudWatch Alarm",
        "total": "cw_alarm_total",
        "unused": "cw_alarm_unused",
        "waste": None,
        "data_unused": "orphan",
        "session": "cw_alarm_result",
        "final": "cw_alarm_results",
        "data_key": "result",
    },
    "loggroup": {
        "display": "Log Group",
        "total": "loggroup_total",
        "unused": "loggroup_unused",
        "waste": "loggroup_monthly_waste",
        "data_unused": "issue",
        "session": "loggroup_result",
        "final": "loggroup_results",
        "data_key": "result",
    },
    # =========================================================================
    # DNS (Global)
    # =========================================================================
    "route53": {
        "display": "Route53",
        "total": "route53_total",
        "unused": "route53_unused",
        "waste": "route53_monthly_waste",
        "data_unused": "empty",
        "session": "route53_result",
        "final": "route53_results",
        "data_key": "result",
        "is_global": True,
    },
    # =========================================================================
    # Analytics
    # =========================================================================
    "kinesis": {
        "display": "Kinesis Stream",
        "total": "kinesis_total",
        "unused": "kinesis_unused",
        "waste": "kinesis_monthly_waste",
        "data_unused": "unused",
        "session": "kinesis_result",
        "final": "kinesis_results",
        "data_key": "result",
    },
    "glue": {
        "display": "Glue Job",
        "total": "glue_total",
        "unused": "glue_unused",
        "waste": None,  # 미사용 작업은 비용 없음 (실행 시에만 과금)
        "data_unused": "unused",
        "session": "glue_result",
        "final": "glue_results",
        "data_key": "result",
    },
    # =========================================================================
    # Security (VPC)
    # =========================================================================
    "security_group": {
        "display": "Security Group",
        "total": "sg_total",
        "unused": "sg_unused",
        "waste": None,  # 직접 비용 없음 (보안 위험 감소 목적)
        "data_unused": "unused",
        "session": "sg_result",
        "final": "sg_results",
        "data_key": "result",
    },
    # =========================================================================
    # File Transfer
    # =========================================================================
    "transfer": {
        "display": "Transfer Family",
        "total": "transfer_total",
        "unused": "transfer_unused",
        "waste": "transfer_monthly_waste",
        "data_unused": "unused",
        "session": "transfer_result",
        "final": "transfer_results",
        "data_key": "result",
    },
    "fsx": {
        "display": "FSx",
        "total": "fsx_total",
        "unused": "fsx_unused",
        "waste": "fsx_monthly_waste",
        "data_unused": "unused",
        "session": "fsx_result",
        "final": "fsx_results",
        "data_key": "result",
    },
}

# 비용 추정 가능한 리소스 필드 목록 (total_waste 계산용)
WASTE_FIELDS = [cfg["waste"] for cfg in RESOURCE_FIELD_MAP.values() if cfg.get("waste")]


# =============================================================================
# 종합 결과 데이터 구조
# =============================================================================


@dataclass
class UnusedResourceSummary:
    """미사용 리소스 종합 요약"""

    account_id: str
    account_name: str
    region: str

    # Compute (EC2)
    ami_total: int = 0
    ami_unused: int = 0
    ami_monthly_waste: float = 0.0

    ebs_total: int = 0
    ebs_unused: int = 0
    ebs_monthly_waste: float = 0.0

    snap_total: int = 0
    snap_unused: int = 0
    snap_monthly_waste: float = 0.0

    eip_total: int = 0
    eip_unused: int = 0
    eip_monthly_waste: float = 0.0

    eni_total: int = 0
    eni_unused: int = 0

    ec2_instance_total: int = 0
    ec2_instance_unused: int = 0
    ec2_instance_monthly_waste: float = 0.0

    # Networking (VPC)
    nat_total: int = 0
    nat_unused: int = 0
    nat_monthly_waste: float = 0.0

    endpoint_total: int = 0
    endpoint_unused: int = 0
    endpoint_monthly_waste: float = 0.0

    # Load Balancing
    elb_total: int = 0
    elb_unused: int = 0
    elb_monthly_waste: float = 0.0

    tg_total: int = 0
    tg_unused: int = 0

    # Database
    dynamodb_total: int = 0
    dynamodb_unused: int = 0
    dynamodb_monthly_waste: float = 0.0

    elasticache_total: int = 0
    elasticache_unused: int = 0
    elasticache_monthly_waste: float = 0.0

    redshift_total: int = 0
    redshift_unused: int = 0
    redshift_monthly_waste: float = 0.0

    opensearch_total: int = 0
    opensearch_unused: int = 0
    opensearch_monthly_waste: float = 0.0

    rds_instance_total: int = 0
    rds_instance_unused: int = 0
    rds_instance_monthly_waste: float = 0.0

    rds_snap_total: int = 0
    rds_snap_unused: int = 0
    rds_snap_monthly_waste: float = 0.0

    # Storage
    ecr_total: int = 0
    ecr_unused: int = 0
    ecr_monthly_waste: float = 0.0

    efs_total: int = 0
    efs_unused: int = 0
    efs_monthly_waste: float = 0.0

    s3_total: int = 0
    s3_unused: int = 0

    # Serverless
    apigateway_total: int = 0
    apigateway_unused: int = 0

    eventbridge_total: int = 0
    eventbridge_unused: int = 0

    lambda_total: int = 0
    lambda_unused: int = 0
    lambda_monthly_waste: float = 0.0

    # ML
    sagemaker_endpoint_total: int = 0
    sagemaker_endpoint_unused: int = 0
    sagemaker_endpoint_monthly_waste: float = 0.0

    # Messaging
    sns_total: int = 0
    sns_unused: int = 0

    sqs_total: int = 0
    sqs_unused: int = 0

    # Security
    acm_total: int = 0
    acm_unused: int = 0

    kms_total: int = 0
    kms_unused: int = 0
    kms_monthly_waste: float = 0.0

    secret_total: int = 0
    secret_unused: int = 0
    secret_monthly_waste: float = 0.0

    # Monitoring
    cw_alarm_total: int = 0
    cw_alarm_unused: int = 0

    loggroup_total: int = 0
    loggroup_unused: int = 0
    loggroup_monthly_waste: float = 0.0

    # DNS (Global)
    route53_total: int = 0
    route53_unused: int = 0
    route53_monthly_waste: float = 0.0

    # Analytics
    kinesis_total: int = 0
    kinesis_unused: int = 0
    kinesis_monthly_waste: float = 0.0

    glue_total: int = 0
    glue_unused: int = 0

    # Security (VPC)
    sg_total: int = 0
    sg_unused: int = 0

    # File Transfer
    transfer_total: int = 0
    transfer_unused: int = 0
    transfer_monthly_waste: float = 0.0

    fsx_total: int = 0
    fsx_unused: int = 0
    fsx_monthly_waste: float = 0.0


@dataclass
class SessionCollectionResult:
    """단일 세션(계정/리전)의 수집 결과"""

    summary: UnusedResourceSummary

    # Compute (EC2)
    ami_result: AMIAnalysisResult | None = None
    ebs_result: EBSAnalysisResult | None = None
    snap_result: SnapshotAnalysisResult | None = None
    eip_result: EIPAnalysisResult | None = None
    eni_result: ENIAnalysisResult | None = None
    ec2_instance_result: EC2AnalysisResult | None = None

    # Networking (VPC)
    nat_findings: list[Any] = field(default_factory=list)
    endpoint_result: EndpointAnalysisResult | None = None

    # Load Balancing
    elb_result: LBAnalysisResult | None = None
    tg_result: TargetGroupAnalysisResult | None = None

    # Database
    dynamodb_result: DynamoDBAnalysisResult | None = None
    elasticache_result: ElastiCacheAnalysisResult | None = None
    redshift_result: RedshiftAnalysisResult | None = None
    opensearch_result: OpenSearchAnalysisResult | None = None
    rds_instance_result: RDSInstanceAnalysisResult | None = None
    rds_snap_result: RDSSnapshotAnalysisResult | None = None

    # Storage
    ecr_result: ECRAnalysisResult | None = None
    efs_result: EFSAnalysisResult | None = None
    s3_result: S3AnalysisResult | None = None

    # Serverless
    apigateway_result: APIGatewayAnalysisResult | None = None
    eventbridge_result: EventBridgeAnalysisResult | None = None
    lambda_result: LambdaAnalysisResult | None = None

    # ML
    sagemaker_endpoint_result: SageMakerAnalysisResult | None = None

    # Messaging
    sns_result: SNSAnalysisResult | None = None
    sqs_result: SQSAnalysisResult | None = None

    # Security
    acm_result: ACMAnalysisResult | None = None
    kms_result: KMSKeyAnalysisResult | None = None
    secret_result: SecretAnalysisResult | None = None

    # Monitoring
    cw_alarm_result: AlarmAnalysisResult | None = None
    loggroup_result: LogGroupAnalysisResult | None = None

    # DNS (Global)
    route53_result: Route53AnalysisResult | None = None

    # Analytics
    kinesis_result: KinesisAnalysisResult | None = None
    glue_result: GlueAnalysisResult | None = None

    # Security (VPC)
    sg_result: list[SGAnalysisResult] | None = None

    # File Transfer
    transfer_result: TransferAnalysisResult | None = None
    fsx_result: FSxAnalysisResult | None = None

    # 에러 목록
    errors: list[str] = field(default_factory=list)


@dataclass
class UnusedAllResult:
    """종합 분석 결과"""

    summaries: list[UnusedResourceSummary] = field(default_factory=list)

    # Compute (EC2)
    ami_results: list[AMIAnalysisResult] = field(default_factory=list)
    ebs_results: list[EBSAnalysisResult] = field(default_factory=list)
    snap_results: list[SnapshotAnalysisResult] = field(default_factory=list)
    eip_results: list[EIPAnalysisResult] = field(default_factory=list)
    eni_results: list[ENIAnalysisResult] = field(default_factory=list)
    ec2_instance_results: list[EC2AnalysisResult] = field(default_factory=list)

    # Networking (VPC)
    nat_findings: list[Any] = field(default_factory=list)
    endpoint_results: list[EndpointAnalysisResult] = field(default_factory=list)

    # Load Balancing
    elb_results: list[LBAnalysisResult] = field(default_factory=list)
    tg_results: list[TargetGroupAnalysisResult] = field(default_factory=list)

    # Database
    dynamodb_results: list[DynamoDBAnalysisResult] = field(default_factory=list)
    elasticache_results: list[ElastiCacheAnalysisResult] = field(default_factory=list)
    redshift_results: list[RedshiftAnalysisResult] = field(default_factory=list)
    opensearch_results: list[OpenSearchAnalysisResult] = field(default_factory=list)
    rds_instance_results: list[RDSInstanceAnalysisResult] = field(default_factory=list)
    rds_snap_results: list[RDSSnapshotAnalysisResult] = field(default_factory=list)

    # Storage
    ecr_results: list[ECRAnalysisResult] = field(default_factory=list)
    efs_results: list[EFSAnalysisResult] = field(default_factory=list)
    s3_results: list[S3AnalysisResult] = field(default_factory=list)

    # Serverless
    apigateway_results: list[APIGatewayAnalysisResult] = field(default_factory=list)
    eventbridge_results: list[EventBridgeAnalysisResult] = field(default_factory=list)
    lambda_results: list[LambdaAnalysisResult] = field(default_factory=list)

    # ML
    sagemaker_endpoint_results: list[SageMakerAnalysisResult] = field(default_factory=list)

    # Messaging
    sns_results: list[SNSAnalysisResult] = field(default_factory=list)
    sqs_results: list[SQSAnalysisResult] = field(default_factory=list)

    # Security
    acm_results: list[ACMAnalysisResult] = field(default_factory=list)
    kms_results: list[KMSKeyAnalysisResult] = field(default_factory=list)
    secret_results: list[SecretAnalysisResult] = field(default_factory=list)

    # Monitoring
    cw_alarm_results: list[AlarmAnalysisResult] = field(default_factory=list)
    loggroup_results: list[LogGroupAnalysisResult] = field(default_factory=list)

    # DNS (Global)
    route53_results: list[Route53AnalysisResult] = field(default_factory=list)

    # Analytics
    kinesis_results: list[KinesisAnalysisResult] = field(default_factory=list)
    glue_results: list[GlueAnalysisResult] = field(default_factory=list)

    # Security (VPC)
    sg_results: list[SGAnalysisResult] = field(default_factory=list)

    # File Transfer
    transfer_results: list[TransferAnalysisResult] = field(default_factory=list)
    fsx_results: list[FSxAnalysisResult] = field(default_factory=list)
