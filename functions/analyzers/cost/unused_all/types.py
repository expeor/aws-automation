"""
functions/analyzers/cost/unused_all/types.py - 미사용 리소스 분석 데이터 타입

미사용 리소스 종합 분석에 사용되는 데이터클래스와 리소스 필드 매핑을 정의합니다.

주요 구성:
    - RESOURCE_FIELD_MAP: 리소스 타입별 필드 매핑 (display, total, unused 등)
    - UnusedResourceSummary: 단일 계정/리전의 미사용 리소스 카운트 요약
    - SessionCollectionResult: 단일 세션의 수집 결과 (요약 + 상세)
    - UnusedAllResult: 전체 분석 결과 (모든 세션 병합)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 각 도구의 결과 타입 import
from functions.analyzers.acm.unused import ACMAnalysisResult
from functions.analyzers.apigateway.unused import APIGatewayAnalysisResult
from functions.analyzers.cloudwatch.alarm_orphan import AlarmAnalysisResult
from functions.analyzers.cloudwatch.loggroup_audit import LogGroupAnalysisResult
from functions.analyzers.dynamodb.unused import DynamoDBAnalysisResult
from functions.analyzers.ec2.ami_audit import AMIAnalysisResult
from functions.analyzers.ec2.ebs_audit import EBSAnalysisResult
from functions.analyzers.ec2.eip_audit import EIPAnalysisResult
from functions.analyzers.ec2.snapshot_audit import SnapshotAnalysisResult
from functions.analyzers.ec2.unused import EC2AnalysisResult
from functions.analyzers.ecr.unused import ECRAnalysisResult
from functions.analyzers.efs.unused import EFSAnalysisResult
from functions.analyzers.elasticache.unused import ElastiCacheAnalysisResult
from functions.analyzers.elb.target_group_audit import TargetGroupAnalysisResult
from functions.analyzers.elb.unused import LBAnalysisResult
from functions.analyzers.eventbridge.unused import EventBridgeAnalysisResult
from functions.analyzers.fn.unused import LambdaAnalysisResult
from functions.analyzers.fsx.unused import FSxAnalysisResult
from functions.analyzers.glue.unused import GlueAnalysisResult
from functions.analyzers.kinesis.unused import KinesisAnalysisResult
from functions.analyzers.kms.unused import KMSKeyAnalysisResult
from functions.analyzers.opensearch.unused import OpenSearchAnalysisResult
from functions.analyzers.rds.snapshot_audit import RDSSnapshotAnalysisResult
from functions.analyzers.rds.unused import RDSAnalysisResult as RDSInstanceAnalysisResult
from functions.analyzers.redshift.unused import RedshiftAnalysisResult
from functions.analyzers.route53.empty_zone import Route53AnalysisResult
from functions.analyzers.s3.empty_bucket import S3AnalysisResult
from functions.analyzers.sagemaker.unused import SageMakerAnalysisResult
from functions.analyzers.secretsmanager.unused import SecretAnalysisResult
from functions.analyzers.sns.unused import SNSAnalysisResult
from functions.analyzers.sqs.unused import SQSAnalysisResult
from functions.analyzers.transfer.unused import TransferAnalysisResult
from functions.analyzers.vpc.endpoint_audit import EndpointAnalysisResult
from functions.analyzers.vpc.eni_audit import ENIAnalysisResult
from functions.analyzers.vpc.sg_audit_analysis import SGAnalysisResult

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
    """미사용 리소스 종합 요약

    단일 계정/리전의 모든 리소스 타입에 대한 전체 수, 미사용 수,
    월간 낭비 비용을 집계합니다.

    Attributes:
        account_id: AWS 계정 ID
        account_name: 계정 이름
        region: AWS 리전 코드
        ami_total: AMI 전체 수
        ami_unused: 미사용 AMI 수
        ami_monthly_waste: AMI 월간 낭비 비용 (USD)
        ebs_total: EBS 볼륨 전체 수
        ebs_unused: 미사용 EBS 볼륨 수
        ebs_monthly_waste: EBS 월간 낭비 비용 (USD)
        snap_total: EBS 스냅샷 전체 수
        snap_unused: 미사용 스냅샷 수
        snap_monthly_waste: 스냅샷 월간 낭비 비용 (USD)
        eip_total: EIP 전체 수
        eip_unused: 미사용 EIP 수
        eip_monthly_waste: EIP 월간 낭비 비용 (USD)
        eni_total: ENI 전체 수
        eni_unused: 미사용 ENI 수
        ec2_instance_total: EC2 인스턴스 전체 수
        ec2_instance_unused: 미사용/유휴 EC2 인스턴스 수
        ec2_instance_monthly_waste: EC2 월간 낭비 비용 (USD)
        nat_total: NAT Gateway 전체 수
        nat_unused: 미사용 NAT Gateway 수
        nat_monthly_waste: NAT Gateway 월간 낭비 비용 (USD)
        endpoint_total: VPC Endpoint 전체 수
        endpoint_unused: 미사용 VPC Endpoint 수
        endpoint_monthly_waste: VPC Endpoint 월간 낭비 비용 (USD)
        elb_total: ELB 전체 수
        elb_unused: 미사용 ELB 수
        elb_monthly_waste: ELB 월간 낭비 비용 (USD)
        tg_total: Target Group 전체 수
        tg_unused: 문제 Target Group 수
        dynamodb_total: DynamoDB 테이블 전체 수
        dynamodb_unused: 미사용 DynamoDB 테이블 수
        dynamodb_monthly_waste: DynamoDB 월간 낭비 비용 (USD)
        elasticache_total: ElastiCache 클러스터 전체 수
        elasticache_unused: 미사용 ElastiCache 수
        elasticache_monthly_waste: ElastiCache 월간 낭비 비용 (USD)
        redshift_total: Redshift 클러스터 전체 수
        redshift_unused: 미사용 Redshift 수
        redshift_monthly_waste: Redshift 월간 낭비 비용 (USD)
        opensearch_total: OpenSearch 도메인 전체 수
        opensearch_unused: 미사용 OpenSearch 수
        opensearch_monthly_waste: OpenSearch 월간 낭비 비용 (USD)
        rds_instance_total: RDS 인스턴스 전체 수
        rds_instance_unused: 미사용 RDS 인스턴스 수
        rds_instance_monthly_waste: RDS 월간 낭비 비용 (USD)
        rds_snap_total: RDS 스냅샷 전체 수
        rds_snap_unused: 오래된 RDS 스냅샷 수
        rds_snap_monthly_waste: RDS 스냅샷 월간 낭비 비용 (USD)
        ecr_total: ECR 리포지토리 전체 수
        ecr_unused: 문제 ECR 리포지토리 수
        ecr_monthly_waste: ECR 월간 낭비 비용 (USD)
        efs_total: EFS 파일시스템 전체 수
        efs_unused: 미사용 EFS 수
        efs_monthly_waste: EFS 월간 낭비 비용 (USD)
        s3_total: S3 버킷 전체 수
        s3_unused: 빈 S3 버킷 수
        apigateway_total: API Gateway 전체 수
        apigateway_unused: 미사용 API Gateway 수
        eventbridge_total: EventBridge 규칙 전체 수
        eventbridge_unused: 미사용 EventBridge 규칙 수
        lambda_total: Lambda 함수 전체 수
        lambda_unused: 미사용 Lambda 함수 수
        lambda_monthly_waste: Lambda 월간 낭비 비용 (USD)
        sagemaker_endpoint_total: SageMaker Endpoint 전체 수
        sagemaker_endpoint_unused: 미사용 SageMaker Endpoint 수
        sagemaker_endpoint_monthly_waste: SageMaker 월간 낭비 비용 (USD)
        sns_total: SNS 토픽 전체 수
        sns_unused: 미사용 SNS 토픽 수
        sqs_total: SQS 큐 전체 수
        sqs_unused: 미사용 SQS 큐 수
        acm_total: ACM 인증서 전체 수
        acm_unused: 미사용 ACM 인증서 수
        kms_total: KMS 키 전체 수
        kms_unused: 미사용 KMS 키 수
        kms_monthly_waste: KMS 월간 낭비 비용 (USD)
        secret_total: Secrets Manager 시크릿 전체 수
        secret_unused: 미사용 시크릿 수
        secret_monthly_waste: Secrets Manager 월간 낭비 비용 (USD)
        cw_alarm_total: CloudWatch Alarm 전체 수
        cw_alarm_unused: 고아/무동작 알람 수
        loggroup_total: Log Group 전체 수
        loggroup_unused: 문제 Log Group 수
        loggroup_monthly_waste: Log Group 월간 낭비 비용 (USD)
        route53_total: Route53 Hosted Zone 전체 수
        route53_unused: 빈 Hosted Zone 수
        route53_monthly_waste: Route53 월간 낭비 비용 (USD)
        kinesis_total: Kinesis 스트림 전체 수
        kinesis_unused: 미사용 Kinesis 스트림 수
        kinesis_monthly_waste: Kinesis 월간 낭비 비용 (USD)
        glue_total: Glue 작업 전체 수
        glue_unused: 미사용 Glue 작업 수
        sg_total: Security Group 전체 수
        sg_unused: 미사용 Security Group 수
        transfer_total: Transfer Family 서버 전체 수
        transfer_unused: 미사용 Transfer 서버 수
        transfer_monthly_waste: Transfer Family 월간 낭비 비용 (USD)
        fsx_total: FSx 파일시스템 전체 수
        fsx_unused: 미사용 FSx 수
        fsx_monthly_waste: FSx 월간 낭비 비용 (USD)
    """

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
    """단일 세션(계정/리전)의 수집 결과

    collect_session_resources()의 반환 타입으로, 요약 통계와
    각 리소스 타입별 상세 분석 결과를 포함합니다.

    Attributes:
        summary: 미사용 리소스 카운트 요약
        ami_result: AMI 분석 결과
        ebs_result: EBS 분석 결과
        snap_result: EBS Snapshot 분석 결과
        eip_result: EIP 분석 결과
        eni_result: ENI 분석 결과
        ec2_instance_result: EC2 인스턴스 분석 결과
        nat_findings: NAT Gateway 분석 결과 리스트
        endpoint_result: VPC Endpoint 분석 결과
        elb_result: ELB 분석 결과
        tg_result: Target Group 분석 결과
        dynamodb_result: DynamoDB 분석 결과
        elasticache_result: ElastiCache 분석 결과
        redshift_result: Redshift 분석 결과
        opensearch_result: OpenSearch 분석 결과
        rds_instance_result: RDS 인스턴스 분석 결과
        rds_snap_result: RDS Snapshot 분석 결과
        ecr_result: ECR 분석 결과
        efs_result: EFS 분석 결과
        s3_result: S3 분석 결과
        apigateway_result: API Gateway 분석 결과
        eventbridge_result: EventBridge 분석 결과
        lambda_result: Lambda 분석 결과
        sagemaker_endpoint_result: SageMaker Endpoint 분석 결과
        sns_result: SNS 분석 결과
        sqs_result: SQS 분석 결과
        acm_result: ACM 분석 결과
        kms_result: KMS 분석 결과
        secret_result: Secrets Manager 분석 결과
        cw_alarm_result: CloudWatch Alarm 분석 결과
        loggroup_result: Log Group 분석 결과
        route53_result: Route53 분석 결과
        kinesis_result: Kinesis 분석 결과
        glue_result: Glue 분석 결과
        sg_result: Security Group 분석 결과 리스트
        transfer_result: Transfer Family 분석 결과
        fsx_result: FSx 분석 결과
        errors: 수집 중 발생한 오류 메시지 목록
    """

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
    """종합 분석 결과

    모든 세션(계정/리전)의 결과를 병합한 최종 결과입니다.
    각 리소스 타입별 분석 결과가 리스트로 집계됩니다.

    Attributes:
        summaries: 세션별 요약 통계 목록
        ami_results: 전체 AMI 분석 결과 리스트
        ebs_results: 전체 EBS 분석 결과 리스트
        snap_results: 전체 EBS Snapshot 분석 결과 리스트
        eip_results: 전체 EIP 분석 결과 리스트
        eni_results: 전체 ENI 분석 결과 리스트
        ec2_instance_results: 전체 EC2 인스턴스 분석 결과 리스트
        nat_findings: 전체 NAT Gateway 분석 결과 리스트
        endpoint_results: 전체 VPC Endpoint 분석 결과 리스트
        elb_results: 전체 ELB 분석 결과 리스트
        tg_results: 전체 Target Group 분석 결과 리스트
        dynamodb_results: 전체 DynamoDB 분석 결과 리스트
        elasticache_results: 전체 ElastiCache 분석 결과 리스트
        redshift_results: 전체 Redshift 분석 결과 리스트
        opensearch_results: 전체 OpenSearch 분석 결과 리스트
        rds_instance_results: 전체 RDS 인스턴스 분석 결과 리스트
        rds_snap_results: 전체 RDS Snapshot 분석 결과 리스트
        ecr_results: 전체 ECR 분석 결과 리스트
        efs_results: 전체 EFS 분석 결과 리스트
        s3_results: 전체 S3 분석 결과 리스트
        apigateway_results: 전체 API Gateway 분석 결과 리스트
        eventbridge_results: 전체 EventBridge 분석 결과 리스트
        lambda_results: 전체 Lambda 분석 결과 리스트
        sagemaker_endpoint_results: 전체 SageMaker 분석 결과 리스트
        sns_results: 전체 SNS 분석 결과 리스트
        sqs_results: 전체 SQS 분석 결과 리스트
        acm_results: 전체 ACM 분석 결과 리스트
        kms_results: 전체 KMS 분석 결과 리스트
        secret_results: 전체 Secrets Manager 분석 결과 리스트
        cw_alarm_results: 전체 CloudWatch Alarm 분석 결과 리스트
        loggroup_results: 전체 Log Group 분석 결과 리스트
        route53_results: 전체 Route53 분석 결과 리스트
        kinesis_results: 전체 Kinesis 분석 결과 리스트
        glue_results: 전체 Glue 분석 결과 리스트
        sg_results: 전체 Security Group 분석 결과 리스트
        transfer_results: 전체 Transfer Family 분석 결과 리스트
        fsx_results: 전체 FSx 분석 결과 리스트
    """

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
