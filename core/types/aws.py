"""
core/types/aws.py - AWS 클라이언트 Protocol 정의

boto3 클라이언트의 타입을 정의합니다.
boto3-stubs가 설치되어 있으면 해당 타입을 사용하고,
그렇지 않으면 Protocol을 사용하여 기본적인 타입 체킹을 지원합니다.

Usage:
    from core.types.aws import EC2Client, S3Client, get_ec2_client

    def list_instances(client: EC2Client) -> list[dict]:
        return client.describe_instances()["Reservations"]

Note:
    boto3-stubs를 설치하면 자동완성과 더 정확한 타입 체킹이 가능합니다:
    pip install "boto3-stubs[ec2,s3,iam]"
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeAlias, TypedDict

# =============================================================================
# boto3-stubs 타입 (설치된 경우)
# =============================================================================

if TYPE_CHECKING:
    # boto3-stubs 타입 사용 (개발 의존성으로 설치됨)
    from mypy_boto3_acm import ACMClient as ACMClient
    from mypy_boto3_apigateway import APIGatewayClient as APIGatewayClient
    from mypy_boto3_apigatewayv2 import ApiGatewayV2Client as ApiGatewayV2Client
    from mypy_boto3_backup import BackupClient as BackupClient
    from mypy_boto3_ce import CostExplorerClient as CostExplorerClient
    from mypy_boto3_cloudformation import CloudFormationClient as CloudFormationClient
    from mypy_boto3_cloudtrail import CloudTrailClient as CloudTrailClient
    from mypy_boto3_cloudwatch import CloudWatchClient as CloudWatchClient
    from mypy_boto3_codecommit import CodeCommitClient as CodeCommitClient
    from mypy_boto3_dynamodb import DynamoDBClient as DynamoDBClient
    from mypy_boto3_ec2 import EC2Client as EC2Client
    from mypy_boto3_ecr import ECRClient as ECRClient
    from mypy_boto3_efs import EFSClient as EFSClient
    from mypy_boto3_elasticache import ElastiCacheClient as ElastiCacheClient
    from mypy_boto3_elb import ElasticLoadBalancingClient as ElasticLoadBalancingClient
    from mypy_boto3_elbv2 import ElasticLoadBalancingv2Client as ElasticLoadBalancingv2Client
    from mypy_boto3_events import EventBridgeClient as EventBridgeClient
    from mypy_boto3_fsx import FSxClient as FSxClient
    from mypy_boto3_glue import GlueClient as GlueClient
    from mypy_boto3_health import HealthClient as HealthClient
    from mypy_boto3_iam import IAMClient as IAMClient
    from mypy_boto3_kinesis import KinesisClient as KinesisClient
    from mypy_boto3_kms import KMSClient as KMSClient
    from mypy_boto3_lambda import LambdaClient as LambdaClient
    from mypy_boto3_logs import CloudWatchLogsClient as CloudWatchLogsClient
    from mypy_boto3_opensearch import OpenSearchServiceClient as OpenSearchServiceClient
    from mypy_boto3_organizations import OrganizationsClient as OrganizationsClient
    from mypy_boto3_pricing import PricingClient as PricingClient
    from mypy_boto3_rds import RDSClient as RDSClient
    from mypy_boto3_redshift import RedshiftClient as RedshiftClient
    from mypy_boto3_resource_explorer_2 import ResourceExplorer2Client as ResourceExplorer2Client
    from mypy_boto3_route53 import Route53Client as Route53Client
    from mypy_boto3_s3 import S3Client as S3Client
    from mypy_boto3_sagemaker import SageMakerClient as SageMakerClient
    from mypy_boto3_secretsmanager import SecretsManagerClient as SecretsManagerClient
    from mypy_boto3_service_quotas import ServiceQuotasClient as ServiceQuotasClient
    from mypy_boto3_sns import SNSClient as SNSClient
    from mypy_boto3_sqs import SQSClient as SQSClient
    from mypy_boto3_sso import SSOClient as SSOClient
    from mypy_boto3_sso_admin import SSOAdminClient as SSOAdminClient
    from mypy_boto3_sso_oidc import SSOOIDCClient as SSOOIDCClient
    from mypy_boto3_sts import STSClient as STSClient
    from mypy_boto3_transfer import TransferClient as TransferClient


# =============================================================================
# 공통 응답 타입
# =============================================================================


class PaginatedResponse(TypedDict, total=False):
    """페이지네이션 응답 기본 타입"""

    NextToken: str
    NextMarker: str
    Marker: str
    IsTruncated: bool


class ResponseMetadata(TypedDict):
    """AWS API 응답 메타데이터"""

    RequestId: str
    HTTPStatusCode: int
    HTTPHeaders: dict[str, str]
    RetryAttempts: int


class AWSResponse(TypedDict, total=False):
    """AWS API 응답 기본 타입"""

    ResponseMetadata: ResponseMetadata


# =============================================================================
# 세션 타입
# =============================================================================


class SessionProtocol(Protocol):
    """boto3.Session Protocol"""

    def client(self, service_name: str, **kwargs: Any) -> Any:
        """서비스 클라이언트 생성"""
        ...

    def resource(self, service_name: str, **kwargs: Any) -> Any:
        """서비스 리소스 생성"""
        ...

    @property
    def region_name(self) -> str | None:
        """현재 리전"""
        ...

    @property
    def profile_name(self) -> str | None:
        """프로파일 이름"""
        ...

    def get_credentials(self) -> Any:
        """자격 증명 반환"""
        ...


# =============================================================================
# 클라이언트 프로토콜 (boto3-stubs 없을 때 사용)
# =============================================================================


class BaseClientProtocol(Protocol):
    """boto3 클라이언트 기본 Protocol"""

    def get_paginator(self, operation_name: str) -> Any:
        """Paginator 반환"""
        ...

    def can_paginate(self, operation_name: str) -> bool:
        """페이지네이션 지원 여부"""
        ...

    @property
    def meta(self) -> Any:
        """클라이언트 메타데이터"""
        ...


class PaginatorProtocol(Protocol):
    """boto3 Paginator Protocol"""

    def paginate(self, **kwargs: Any) -> Any:
        """페이지네이션 실행"""
        ...


# =============================================================================
# 서비스별 클라이언트 타입 별칭 (런타임용)
# =============================================================================

# boto3-stubs가 설치되지 않은 런타임에서 사용할 타입
AnyClient: TypeAlias = Any
AnySession: TypeAlias = Any
AnyPaginator: TypeAlias = Any


# =============================================================================
# 클라이언트 팩토리 타입
# =============================================================================


class ClientFactory(Protocol):
    """클라이언트 팩토리 Protocol"""

    def __call__(
        self,
        session: SessionProtocol,
        service_name: str,
        region_name: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """클라이언트 생성"""
        ...


# =============================================================================
# boto3 Session 타입 (실제 boto3.Session과 호환)
# =============================================================================

if TYPE_CHECKING:
    import boto3

    Boto3Session: TypeAlias = boto3.Session
else:
    Boto3Session: TypeAlias = Any


# =============================================================================
# 서비스 이름 리터럴 타입
# =============================================================================

# 주요 서비스 이름 (자동완성 지원)
AWSServiceName = Literal[
    "acm",
    "apigateway",
    "apigatewayv2",
    "backup",
    "ce",
    "cloudformation",
    "cloudtrail",
    "cloudwatch",
    "codecommit",
    "dynamodb",
    "ec2",
    "ecr",
    "efs",
    "elasticache",
    "elb",
    "elbv2",
    "events",
    "fsx",
    "glue",
    "health",
    "iam",
    "kinesis",
    "kms",
    "lambda",
    "logs",
    "opensearch",
    "organizations",
    "pricing",
    "rds",
    "redshift",
    "resource-explorer-2",
    "route53",
    "s3",
    "sagemaker",
    "secretsmanager",
    "service-quotas",
    "sns",
    "sqs",
    "sso",
    "sso-admin",
    "sso-oidc",
    "sts",
    "transfer",
]
