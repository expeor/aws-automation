"""
plugins/tag_editor/types.py - MAP 태그 관리 데이터 타입

MAP 2.0 마이그레이션 태그 분석/적용을 위한 데이터 구조 정의

Reference:
- MAP 2.0 공식 문서 (태깅 가이드):
  https://docs.aws.amazon.com/migrationhub-strategy/latest/userguide/tagging-key-combinations.html
- MAP 2.0 포함 서비스 목록:
  https://s3-us-west-2.amazonaws.com/map-2.0-customer-documentation/included-services/MAP_Included_Services_List.pdf
- ResourceGroupsTaggingAPI 지원 서비스:
  https://docs.aws.amazon.com/resourcegroupstagging/latest/APIReference/supported-services.html
- 대규모 리소스 태깅 베스트 프랙티스:
  https://aws.amazon.com/blogs/mt/maximizing-resource-tagging-at-scale-and-across-teams-for-your-migration-to-aws/

MAP Tag Value 형식:
- 일반 마이그레이션: mig{MPE_ID} (예: mig12345 또는 migABCDE12345)
- SAP 워크로드: sap{MPE_ID} (예: sap12345 또는 sapABCDE12345)
- Oracle 워크로드: oracle{MPE_ID} (예: oracle12345 또는 oracleABCDE12345)
- Commercial DB&A (On-prem → AWS): comm{MPE_ID}
- Non-commercial DB&A (EC2 → AWS): mig_ec2_{MPE_ID}
- Commercial DB&A (EC2 → AWS): comm_ec2_{MPE_ID}

MPE ID 형식:
- Short: 5자리 숫자 (예: 12345)
- Long: 10자리 영숫자 (예: ABCDE12345, 대문자)

※ prefix는 소문자, Long MPE ID는 대문자 사용
※ 태그 키 "map-migrated"는 반드시 소문자 그대로 사용 (대소문자 변경/공백 불가)
※ Cost Allocation Tag는 자동 활성화됨 (MAP 2.0 terms signed after Nov 18, 2024)

참고 - 자동 생성 태그:
- "aws-migration-project-id": MGN(Application Migration Service)에서 자동 생성
  → MAP 크레딧 계산에 직접 사용되지 않음, 별도 관리 불필요
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# =============================================================================
# 상수 정의
# =============================================================================

# MAP 태그 키
MAP_TAG_KEY = "map-migrated"

# MAP 2.0 지원 리소스 타입 (ResourceGroupsTaggingAPI 기준)
# Reference: https://docs.aws.amazon.com/resourcegroupstagging/latest/APIReference/supported-services.html
SUPPORTED_RESOURCE_TYPES = [
    # Compute (EC2)
    "ec2:instance",
    "ec2:volume",
    "ec2:snapshot",
    "ec2:image",
    "ec2:network-interface",
    "ec2:elastic-ip",
    "ec2:security-group",
    "ec2:key-pair",
    "ec2:launch-template",
    "ec2:spot-instances-request",
    "ec2:dedicated-host",
    "ec2:capacity-reservation",
    # Database (RDS/Aurora)
    "rds:db",
    "rds:cluster",
    "rds:snapshot",
    "rds:cluster-snapshot",
    "rds:subgrp",
    "rds:og",
    "rds:pg",
    # DynamoDB
    "dynamodb:table",
    # ElastiCache
    "elasticache:cluster",
    "elasticache:replication-group",
    "elasticache:snapshot",
    # Neptune
    "neptune:db",
    "neptune:cluster",
    # Redshift
    "redshift:cluster",
    "redshift:snapshot",
    "redshift:parametergroup",
    # Storage (S3/EFS/FSx)
    "s3:bucket",
    "efs:file-system",
    "fsx:file-system",
    "fsx:backup",
    "glacier:vault",
    # Serverless (Lambda/API Gateway/Step Functions)
    "lambda:function",
    "apigateway:restapis",
    "apigateway:stage",
    "states:stateMachine",
    # Networking (VPC/ELB)
    "ec2:vpc",
    "ec2:subnet",
    "ec2:internet-gateway",
    "ec2:nat-gateway",
    "ec2:route-table",
    "ec2:network-acl",
    "ec2:vpc-endpoint",
    "ec2:vpn-gateway",
    "ec2:customer-gateway",
    "ec2:transit-gateway",
    "elasticloadbalancing:loadbalancer",
    "elasticloadbalancing:targetgroup",
    # Containers (ECS/EKS/ECR)
    "ecs:cluster",
    "ecs:service",
    "ecs:task-definition",
    "eks:cluster",
    "eks:nodegroup",
    "ecr:repository",
    # Security (KMS/Secrets Manager/ACM)
    "secretsmanager:secret",
    "kms:key",
    "acm:certificate",
    "waf:webacl",
    "wafv2:webacl",
    # Messaging (SQS/SNS/Kinesis)
    "sqs:queue",
    "sns:topic",
    "kinesis:stream",
    "firehose:deliverystream",
    # Monitoring (CloudWatch)
    "logs:log-group",
    "cloudwatch:alarm",
    # Analytics (Athena/EMR/Glue)
    "athena:workgroup",
    "emr:cluster",
    "glue:database",
    "glue:table",
    "glue:crawler",
    "glue:job",
    # Machine Learning
    "sagemaker:endpoint",
    "sagemaker:notebook-instance",
    "sagemaker:training-job",
    # Others
    "backup:backup-plan",
    "backup:backup-vault",
    "cloudformation:stack",
    "ssm:parameter",
    "ssm:document",
    "config:config-rule",
    "codebuild:project",
    "codepipeline:pipeline",
]

# 리소스 타입 그룹화 (UI 표시용)
RESOURCE_TYPE_GROUPS = {
    "Compute": [
        "ec2:instance",
        "ec2:volume",
        "ec2:snapshot",
        "ec2:image",
        "ec2:network-interface",
        "ec2:elastic-ip",
        "ec2:security-group",
        "ec2:launch-template",
        "ec2:dedicated-host",
    ],
    "Database": [
        "rds:db",
        "rds:cluster",
        "rds:snapshot",
        "rds:cluster-snapshot",
        "dynamodb:table",
        "elasticache:cluster",
        "elasticache:replication-group",
        "neptune:db",
        "neptune:cluster",
        "redshift:cluster",
    ],
    "Storage": [
        "s3:bucket",
        "efs:file-system",
        "fsx:file-system",
        "glacier:vault",
    ],
    "Serverless": [
        "lambda:function",
        "apigateway:restapis",
        "states:stateMachine",
    ],
    "Networking": [
        "ec2:vpc",
        "ec2:subnet",
        "ec2:internet-gateway",
        "ec2:nat-gateway",
        "ec2:route-table",
        "ec2:vpc-endpoint",
        "ec2:transit-gateway",
        "elasticloadbalancing:loadbalancer",
        "elasticloadbalancing:targetgroup",
    ],
    "Containers": [
        "ecs:cluster",
        "ecs:service",
        "ecs:task-definition",
        "ecr:repository",
        "eks:cluster",
        "eks:nodegroup",
    ],
    "Security": [
        "secretsmanager:secret",
        "kms:key",
        "acm:certificate",
        "waf:webacl",
        "wafv2:webacl",
    ],
    "Messaging": [
        "sqs:queue",
        "sns:topic",
        "kinesis:stream",
        "firehose:deliverystream",
    ],
    "Monitoring": [
        "logs:log-group",
        "cloudwatch:alarm",
    ],
    "Analytics": [
        "athena:workgroup",
        "emr:cluster",
        "glue:database",
        "glue:job",
        "glue:crawler",
    ],
    "DevOps": [
        "cloudformation:stack",
        "codebuild:project",
        "codepipeline:pipeline",
        "ssm:parameter",
        "config:config-rule",
    ],
}


# =============================================================================
# Enum 정의
# =============================================================================


class MapTagStatus(Enum):
    """MAP 태그 상태"""

    TAGGED = "tagged"  # map-migrated 태그 있음
    UNTAGGED = "untagged"  # map-migrated 태그 없음
    PARTIAL = "partial"  # 일부 태그됨 (그룹 레벨)


class TagOperationResult(Enum):
    """태그 적용 결과"""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# 데이터 클래스
# =============================================================================


@dataclass
class ResourceTagInfo:
    """개별 리소스 태그 정보"""

    resource_arn: str
    resource_type: str  # e.g., "ec2:instance"
    resource_id: str  # e.g., "i-1234567890abcdef0"
    name: str  # Name 태그 값
    account_id: str
    account_name: str
    region: str
    tags: dict[str, str]  # 현재 태그들
    has_map_tag: bool
    map_tag_value: str | None = None


@dataclass
class ResourceTypeStats:
    """리소스 타입별 통계"""

    resource_type: str
    display_name: str
    total: int = 0
    tagged: int = 0
    untagged: int = 0

    @property
    def tag_rate(self) -> float:
        """태그 적용률 (%)"""
        if self.total == 0:
            return 0.0
        return (self.tagged / self.total) * 100


@dataclass
class MapTagAnalysisResult:
    """MAP 태그 분석 결과 (계정/리전 단위)"""

    account_id: str
    account_name: str
    region: str

    # 전체 통계
    total_resources: int = 0
    tagged_resources: int = 0
    untagged_resources: int = 0

    # 리소스 타입별 통계
    type_stats: list[ResourceTypeStats] = field(default_factory=list)

    # 상세 리소스 목록
    resources: list[ResourceTagInfo] = field(default_factory=list)

    @property
    def tag_rate(self) -> float:
        """전체 태그 적용률 (%)"""
        if self.total_resources == 0:
            return 0.0
        return (self.tagged_resources / self.total_resources) * 100


@dataclass
class TagOperationLog:
    """태그 적용 작업 로그"""

    resource_arn: str
    resource_type: str
    resource_id: str
    name: str
    operation: str  # "add", "update", "remove"
    result: TagOperationResult
    error_message: str | None = None
    previous_value: str | None = None
    new_value: str | None = None


@dataclass
class MapTagApplyResult:
    """MAP 태그 적용 결과"""

    account_id: str
    account_name: str
    region: str
    tag_value: str  # 적용한 map-migrated 값

    # 통계
    total_targeted: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0

    # 상세 로그
    operation_logs: list[TagOperationLog] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """성공률 (%)"""
        if self.total_targeted == 0:
            return 0.0
        return (self.success_count / self.total_targeted) * 100
