"""
plugins/cost/unused_all/types.py - 미사용 리소스 분석 데이터 타입

데이터클래스 및 리소스 필드 매핑 정의
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
from plugins.ecr.unused import ECRAnalysisResult
from plugins.efs.unused import EFSAnalysisResult
from plugins.elasticache.unused import ElastiCacheAnalysisResult
from plugins.elb.target_group_audit import TargetGroupAnalysisResult
from plugins.elb.unused import LBAnalysisResult
from plugins.eventbridge.unused import EventBridgeAnalysisResult
from plugins.fn.unused import LambdaAnalysisResult
from plugins.kms.unused import KMSKeyAnalysisResult
from plugins.rds.snapshot_audit import RDSSnapshotAnalysisResult
from plugins.rds.unused import RDSAnalysisResult as RDSInstanceAnalysisResult
from plugins.route53.empty_zone import Route53AnalysisResult
from plugins.s3.empty_bucket import S3AnalysisResult
from plugins.secretsmanager.unused import SecretAnalysisResult
from plugins.sns.unused import SNSAnalysisResult
from plugins.sqs.unused import SQSAnalysisResult
from plugins.vpc.endpoint_audit import EndpointAnalysisResult
from plugins.vpc.eni_audit import ENIAnalysisResult


# =============================================================================
# 리소스 설정 (카테고리별 그룹화)
# =============================================================================

# 리소스별 필드 매핑
# - display: 표시 이름
# - total/unused/waste: summary 필드명
# - data_unused: collector 반환 데이터의 unused 키 (unused, old, issue, orphan 등)
# - session/final: 세션/최종 결과의 필드명
# - data_key: collector 반환 데이터의 결과 키 (result, findings)
RESOURCE_FIELD_MAP: Dict[str, Dict[str, Any]] = {
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
        "unused": "tg_issue",
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
        "unused": "rds_snap_old",
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
        "unused": "ecr_issue",
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
        "unused": "s3_empty",
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
        "unused": "cw_alarm_orphan",
        "waste": None,
        "data_unused": "orphan",
        "session": "cw_alarm_result",
        "final": "cw_alarm_results",
        "data_key": "result",
    },
    "loggroup": {
        "display": "Log Group",
        "total": "loggroup_total",
        "unused": "loggroup_issue",
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
        "unused": "route53_empty",
        "waste": "route53_monthly_waste",
        "data_unused": "empty",
        "session": "route53_result",
        "final": "route53_results",
        "data_key": "result",
        "is_global": True,
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
    tg_issue: int = 0

    # Database
    dynamodb_total: int = 0
    dynamodb_unused: int = 0
    dynamodb_monthly_waste: float = 0.0

    elasticache_total: int = 0
    elasticache_unused: int = 0
    elasticache_monthly_waste: float = 0.0

    rds_instance_total: int = 0
    rds_instance_unused: int = 0
    rds_instance_monthly_waste: float = 0.0

    rds_snap_total: int = 0
    rds_snap_old: int = 0
    rds_snap_monthly_waste: float = 0.0

    # Storage
    ecr_total: int = 0
    ecr_issue: int = 0
    ecr_monthly_waste: float = 0.0

    efs_total: int = 0
    efs_unused: int = 0
    efs_monthly_waste: float = 0.0

    s3_total: int = 0
    s3_empty: int = 0

    # Serverless
    apigateway_total: int = 0
    apigateway_unused: int = 0

    eventbridge_total: int = 0
    eventbridge_unused: int = 0

    lambda_total: int = 0
    lambda_unused: int = 0
    lambda_monthly_waste: float = 0.0

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
    cw_alarm_orphan: int = 0

    loggroup_total: int = 0
    loggroup_issue: int = 0
    loggroup_monthly_waste: float = 0.0

    # DNS (Global)
    route53_total: int = 0
    route53_empty: int = 0
    route53_monthly_waste: float = 0.0


@dataclass
class SessionCollectionResult:
    """단일 세션(계정/리전)의 수집 결과"""

    summary: UnusedResourceSummary

    # Compute (EC2)
    ami_result: Optional[AMIAnalysisResult] = None
    ebs_result: Optional[EBSAnalysisResult] = None
    snap_result: Optional[SnapshotAnalysisResult] = None
    eip_result: Optional[EIPAnalysisResult] = None
    eni_result: Optional[ENIAnalysisResult] = None

    # Networking (VPC)
    nat_findings: List[Any] = field(default_factory=list)
    endpoint_result: Optional[EndpointAnalysisResult] = None

    # Load Balancing
    elb_result: Optional[LBAnalysisResult] = None
    tg_result: Optional[TargetGroupAnalysisResult] = None

    # Database
    dynamodb_result: Optional[DynamoDBAnalysisResult] = None
    elasticache_result: Optional[ElastiCacheAnalysisResult] = None
    rds_instance_result: Optional[RDSInstanceAnalysisResult] = None
    rds_snap_result: Optional[RDSSnapshotAnalysisResult] = None

    # Storage
    ecr_result: Optional[ECRAnalysisResult] = None
    efs_result: Optional[EFSAnalysisResult] = None
    s3_result: Optional[S3AnalysisResult] = None

    # Serverless
    apigateway_result: Optional[APIGatewayAnalysisResult] = None
    eventbridge_result: Optional[EventBridgeAnalysisResult] = None
    lambda_result: Optional[LambdaAnalysisResult] = None

    # Messaging
    sns_result: Optional[SNSAnalysisResult] = None
    sqs_result: Optional[SQSAnalysisResult] = None

    # Security
    acm_result: Optional[ACMAnalysisResult] = None
    kms_result: Optional[KMSKeyAnalysisResult] = None
    secret_result: Optional[SecretAnalysisResult] = None

    # Monitoring
    cw_alarm_result: Optional[AlarmAnalysisResult] = None
    loggroup_result: Optional[LogGroupAnalysisResult] = None

    # DNS (Global)
    route53_result: Optional[Route53AnalysisResult] = None

    # 에러 목록
    errors: List[str] = field(default_factory=list)


@dataclass
class UnusedAllResult:
    """종합 분석 결과"""

    summaries: List[UnusedResourceSummary] = field(default_factory=list)

    # Compute (EC2)
    ami_results: List[AMIAnalysisResult] = field(default_factory=list)
    ebs_results: List[EBSAnalysisResult] = field(default_factory=list)
    snap_results: List[SnapshotAnalysisResult] = field(default_factory=list)
    eip_results: List[EIPAnalysisResult] = field(default_factory=list)
    eni_results: List[ENIAnalysisResult] = field(default_factory=list)

    # Networking (VPC)
    nat_findings: List[Any] = field(default_factory=list)
    endpoint_results: List[EndpointAnalysisResult] = field(default_factory=list)

    # Load Balancing
    elb_results: List[LBAnalysisResult] = field(default_factory=list)
    tg_results: List[TargetGroupAnalysisResult] = field(default_factory=list)

    # Database
    dynamodb_results: List[DynamoDBAnalysisResult] = field(default_factory=list)
    elasticache_results: List[ElastiCacheAnalysisResult] = field(default_factory=list)
    rds_instance_results: List[RDSInstanceAnalysisResult] = field(default_factory=list)
    rds_snap_results: List[RDSSnapshotAnalysisResult] = field(default_factory=list)

    # Storage
    ecr_results: List[ECRAnalysisResult] = field(default_factory=list)
    efs_results: List[EFSAnalysisResult] = field(default_factory=list)
    s3_results: List[S3AnalysisResult] = field(default_factory=list)

    # Serverless
    apigateway_results: List[APIGatewayAnalysisResult] = field(default_factory=list)
    eventbridge_results: List[EventBridgeAnalysisResult] = field(default_factory=list)
    lambda_results: List[LambdaAnalysisResult] = field(default_factory=list)

    # Messaging
    sns_results: List[SNSAnalysisResult] = field(default_factory=list)
    sqs_results: List[SQSAnalysisResult] = field(default_factory=list)

    # Security
    acm_results: List[ACMAnalysisResult] = field(default_factory=list)
    kms_results: List[KMSKeyAnalysisResult] = field(default_factory=list)
    secret_results: List[SecretAnalysisResult] = field(default_factory=list)

    # Monitoring
    cw_alarm_results: List[AlarmAnalysisResult] = field(default_factory=list)
    loggroup_results: List[LogGroupAnalysisResult] = field(default_factory=list)

    # DNS (Global)
    route53_results: List[Route53AnalysisResult] = field(default_factory=list)
