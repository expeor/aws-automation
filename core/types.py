"""
core/types.py - 공통 타입 정의

TypedDict와 Protocol을 사용하여 타입 안전성을 높입니다.
런타임 타입 체크와 IDE 자동완성을 지원합니다.

주요 컴포넌트:
    플러그인 메타데이터:
        - ToolMetadata: 도구 메타데이터 타입 (name, description, permission 등)
        - CategoryMetadata: 카테고리 메타데이터 타입 (name, description, aliases)
        - DiscoveredCategory: 발견된 카테고리 전체 정보

    AWS 리소스 타입:
        - AWSTag: AWS 태그 타입 (Key, Value)
        - AWSResource: 공통 리소스 필드 (Tags, Arn, 메타 필드)
        - EC2Instance, EBSVolume, S3Bucket, RDSInstance: 서비스별 리소스 타입

    프로토콜 정의:
        - PluginRunner: 플러그인 실행 함수 프로토콜
        - OptionsCollector: 옵션 수집 함수 프로토콜
        - AWSClient: boto3 클라이언트 프로토콜
        - SessionProvider: 세션 프로바이더 프로토콜

    분석 결과 타입:
        - AnalysisResult: 분석 결과 타입 (success, data, errors)
        - ErrorInfo: 에러 정보 타입

    API 응답 타입:
        - PaginatedResponse: 페이지네이션 응답 기본 타입
        - DescribeInstancesResponse, DescribeVolumesResponse 등

Usage:
    # 도구 메타데이터 처리
    from core.types import ToolMetadata, is_tool_metadata

    def process_tool(tool: ToolMetadata) -> None:
        print(f"도구: {tool['name']}")
        print(f"권한: {tool['permission']}")

    # 타입 가드 사용
    data = {"name": "test", "description": "테스트", "permission": "read"}
    if is_tool_metadata(data):
        process_tool(data)  # 타입 안전

    # 프로토콜 사용
    from core.types import SessionProvider

    def use_provider(provider: SessionProvider) -> None:
        if provider.is_authenticated():
            session = provider.get_session(region="ap-northeast-2")

    # AWS 리소스 타입
    from core.types import EC2Instance, EBSVolume

    def process_instance(instance: EC2Instance) -> str:
        return f"{instance['InstanceId']} ({instance['InstanceType']})"
"""

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    TypedDict,
    Union,
    runtime_checkable,
)

# =============================================================================
# 플러그인 메타데이터 타입
# =============================================================================


class ToolMetadata(TypedDict, total=False):
    """도구 메타데이터 타입

    total=False로 선택적 필드 허용
    """

    # 필수 필드
    name: str
    description: str
    permission: Literal["read", "write", "delete"]

    # 선택적 필드
    module: str
    function: str
    area: Literal[
        "security",
        "cost",
        "performance",
        "fault_tolerance",
        "service_limits",
        "operational",
        "inventory",
    ]
    tags: List[str]
    service: str
    ref: str  # 참조 도구용
    requires: List[str]  # 필요한 패키지


class CategoryMetadata(TypedDict, total=False):
    """카테고리 메타데이터 타입"""

    # 필수 필드
    name: str
    description: str

    # 선택적 필드
    aliases: List[str]
    icon: str


class DiscoveredCategory(TypedDict):
    """발견된 카테고리 전체 정보"""

    name: str
    description: str
    tools: List[ToolMetadata]
    module_path: str
    _source: str


# =============================================================================
# AWS 리소스 타입
# =============================================================================


class AWSTag(TypedDict):
    """AWS 태그 타입"""

    Key: str
    Value: str


class AWSResource(TypedDict, total=False):
    """AWS 리소스 공통 필드

    모든 AWS 리소스가 가질 수 있는 공통 필드를 정의합니다.
    """

    # 분석 도구가 추가하는 메타 필드
    _account: str
    _region: str
    _resource_id: str
    _name: str
    _status: str

    # AWS 공통 필드
    Tags: List[AWSTag]
    Arn: str


class EC2Instance(AWSResource):
    """EC2 인스턴스 타입"""

    InstanceId: str
    InstanceType: str
    State: Dict[str, str]
    LaunchTime: str
    PrivateIpAddress: str
    PublicIpAddress: str
    VpcId: str
    SubnetId: str


class EBSVolume(AWSResource):
    """EBS 볼륨 타입"""

    VolumeId: str
    VolumeType: str
    Size: int
    State: str
    AvailabilityZone: str
    Encrypted: bool
    Iops: int
    Throughput: int


class S3Bucket(AWSResource):
    """S3 버킷 타입"""

    Name: str
    CreationDate: str


class RDSInstance(AWSResource):
    """RDS 인스턴스 타입"""

    DBInstanceIdentifier: str
    DBInstanceClass: str
    Engine: str
    EngineVersion: str
    DBInstanceStatus: str
    MasterUsername: str
    AllocatedStorage: int
    AvailabilityZone: str
    MultiAZ: bool


# =============================================================================
# 프로토콜 정의
# =============================================================================


@runtime_checkable
class PluginRunner(Protocol):
    """플러그인 실행 함수 프로토콜"""

    def __call__(self, ctx: Any) -> None:
        """플러그인 실행

        Args:
            ctx: ExecutionContext
        """
        ...


@runtime_checkable
class OptionsCollector(Protocol):
    """옵션 수집 함수 프로토콜"""

    def __call__(self, ctx: Any) -> Dict[str, Any]:
        """옵션 수집

        Args:
            ctx: ExecutionContext

        Returns:
            수집된 옵션 딕셔너리
        """
        ...


@runtime_checkable
class AWSClient(Protocol):
    """boto3 클라이언트 프로토콜"""

    def __getattr__(self, name: str) -> Callable[..., Dict[str, Any]]:
        ...


@runtime_checkable
class SessionProvider(Protocol):
    """세션 프로바이더 프로토콜"""

    def authenticate(self) -> None:
        """인증 수행"""
        ...

    def is_authenticated(self) -> bool:
        """인증 상태 확인"""
        ...

    def get_session(
        self,
        account_id: Optional[str] = None,
        role_name: Optional[str] = None,
        region: Optional[str] = None,
    ) -> Any:  # boto3.Session
        """세션 반환"""
        ...

    def list_accounts(self) -> Dict[str, Any]:
        """계정 목록 반환"""
        ...

    def supports_multi_account(self) -> bool:
        """멀티 계정 지원 여부"""
        ...

    def close(self) -> None:
        """리소스 정리"""
        ...


# =============================================================================
# 분석 결과 타입
# =============================================================================


class AnalysisResult(TypedDict, total=False):
    """분석 결과 타입"""

    success: bool
    data: List[Dict[str, Any]]
    errors: List[str]
    output_path: str
    summary: Dict[str, Any]


class ErrorInfo(TypedDict):
    """에러 정보 타입"""

    identifier: str
    region: str
    error_code: str
    error_message: str


# =============================================================================
# API 응답 타입
# =============================================================================


class PaginatedResponse(TypedDict, total=False):
    """페이지네이션 응답 타입"""

    NextToken: str
    NextMarker: str


class DescribeInstancesResponse(PaginatedResponse):
    """EC2 describe_instances 응답"""

    Reservations: List[Dict[str, Any]]


class DescribeVolumesResponse(PaginatedResponse):
    """EC2 describe_volumes 응답"""

    Volumes: List[EBSVolume]


class ListBucketsResponse(TypedDict):
    """S3 list_buckets 응답"""

    Buckets: List[S3Bucket]
    Owner: Dict[str, str]


# =============================================================================
# 설정 타입
# =============================================================================


class AWSConfig(TypedDict, total=False):
    """AWS 설정 타입"""

    region_name: str
    profile_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_session_token: str


class SSOConfig(TypedDict):
    """SSO 설정 타입"""

    start_url: str
    region: str
    account_id: str
    role_name: str


# =============================================================================
# 타입 가드 함수
# =============================================================================


def is_tool_metadata(obj: Any) -> bool:
    """ToolMetadata 타입인지 확인"""
    if not isinstance(obj, dict):
        return False
    return all(key in obj for key in ("name", "description", "permission"))
