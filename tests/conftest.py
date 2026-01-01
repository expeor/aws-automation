"""
tests/conftest.py - pytest 공통 픽스처

AWS API 모킹과 테스트 헬퍼를 제공합니다.

Usage:
    def test_something(mock_aws, mock_context):
        # mock_aws: moto를 사용한 AWS 모킹
        # mock_context: 테스트용 ExecutionContext
        pass
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


# =============================================================================
# 환경 설정
# =============================================================================


@pytest.fixture(autouse=True)
def setup_test_environment():
    """테스트 환경 설정"""
    # 테스트용 환경 변수 설정
    os.environ.setdefault("AWS_DEFAULT_REGION", "ap-northeast-2")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")

    yield

    # 정리 (필요시)


# =============================================================================
# AWS 모킹 픽스처
# =============================================================================


@pytest.fixture
def mock_boto3_session():
    """boto3.Session 모킹"""
    with patch("boto3.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # 기본 클라이언트 설정
        mock_session.client.return_value = MagicMock()
        mock_session.resource.return_value = MagicMock()
        mock_session.region_name = "ap-northeast-2"

        yield mock_session


@pytest.fixture
def mock_ec2_client():
    """EC2 클라이언트 모킹"""
    mock_client = MagicMock()

    # describe_instances 기본 응답
    mock_client.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": "i-1234567890abcdef0",
                        "InstanceType": "t3.micro",
                        "State": {"Name": "running"},
                        "Tags": [{"Key": "Name", "Value": "test-instance"}],
                        "LaunchTime": "2024-01-01T00:00:00Z",
                        "PrivateIpAddress": "10.0.0.1",
                    }
                ]
            }
        ]
    }

    # describe_volumes 기본 응답
    mock_client.describe_volumes.return_value = {
        "Volumes": [
            {
                "VolumeId": "vol-1234567890abcdef0",
                "VolumeType": "gp3",
                "Size": 100,
                "State": "available",
                "AvailabilityZone": "ap-northeast-2a",
                "Encrypted": True,
                "Tags": [{"Key": "Name", "Value": "test-volume"}],
            }
        ]
    }

    # 페이지네이터 모킹
    mock_paginator = MagicMock()
    mock_paginator.paginate.return_value = [mock_client.describe_instances.return_value]
    mock_client.get_paginator.return_value = mock_paginator

    yield mock_client


@pytest.fixture
def mock_s3_client():
    """S3 클라이언트 모킹"""
    mock_client = MagicMock()

    mock_client.list_buckets.return_value = {
        "Buckets": [{"Name": "test-bucket", "CreationDate": "2024-01-01T00:00:00Z"}],
        "Owner": {"DisplayName": "test-owner", "ID": "12345"},
    }

    yield mock_client


@pytest.fixture
def mock_iam_client():
    """IAM 클라이언트 모킹"""
    mock_client = MagicMock()

    mock_client.list_users.return_value = {
        "Users": [
            {
                "UserName": "test-user",
                "UserId": "AIDATEST123",
                "Arn": "arn:aws:iam::123456789012:user/test-user",
                "CreateDate": "2024-01-01T00:00:00Z",
            }
        ]
    }

    mock_client.list_roles.return_value = {
        "Roles": [
            {
                "RoleName": "test-role",
                "RoleId": "AROATEST123",
                "Arn": "arn:aws:iam::123456789012:role/test-role",
                "CreateDate": "2024-01-01T00:00:00Z",
            }
        ]
    }

    yield mock_client


@pytest.fixture
def mock_sts_client():
    """STS 클라이언트 모킹"""
    mock_client = MagicMock()

    mock_client.get_caller_identity.return_value = {
        "UserId": "AIDATEST123",
        "Account": "123456789012",
        "Arn": "arn:aws:iam::123456789012:user/test-user",
    }

    mock_client.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "ASIATEST123",
            "SecretAccessKey": "test-secret",
            "SessionToken": "test-token",
            "Expiration": "2024-12-31T23:59:59Z",
        }
    }

    yield mock_client


# =============================================================================
# Context 픽스처
# =============================================================================


@dataclass
class MockAccountInfo:
    """테스트용 AccountInfo"""

    id: str = "123456789012"
    name: str = "test-account"
    email: str = "test@example.com"
    roles: List[str] = field(default_factory=lambda: ["AdminRole", "ReadOnlyRole"])


@dataclass
class MockProvider:
    """테스트용 Provider"""

    _authenticated: bool = True
    _accounts: Dict[str, MockAccountInfo] = field(default_factory=dict)

    def __post_init__(self):
        if not self._accounts:
            self._accounts = {"123456789012": MockAccountInfo()}

    def is_authenticated(self) -> bool:
        return self._authenticated

    def authenticate(self) -> None:
        self._authenticated = True

    def get_session(
        self,
        account_id: Optional[str] = None,
        role_name: Optional[str] = None,
        region: Optional[str] = None,
    ):
        mock_session = MagicMock()
        mock_session.region_name = region or "ap-northeast-2"
        return mock_session

    def list_accounts(self) -> Dict[str, MockAccountInfo]:
        return self._accounts

    def supports_multi_account(self) -> bool:
        return True

    def close(self) -> None:
        self._authenticated = False


@pytest.fixture
def mock_account_info():
    """테스트용 AccountInfo"""
    return MockAccountInfo()


@pytest.fixture
def mock_provider():
    """테스트용 Provider"""
    return MockProvider()


@pytest.fixture
def mock_context(mock_provider, mock_account_info):
    """테스트용 ExecutionContext"""
    from cli.flow.context import ExecutionContext, ProviderKind, ToolInfo

    ctx = ExecutionContext()
    ctx.category = "ec2"
    ctx.tool = ToolInfo(
        name="미사용 EC2",
        description="테스트 도구",
        category="ec2",
        permission="read",
    )
    ctx.profile_name = "test-profile"
    ctx.provider_kind = ProviderKind.SSO_SESSION
    ctx.provider = mock_provider
    ctx.accounts = [mock_account_info]
    ctx.regions = ["ap-northeast-2"]

    return ctx


@pytest.fixture
def mock_static_context():
    """Static credentials용 테스트 ExecutionContext"""
    from cli.flow.context import ExecutionContext, ProviderKind, ToolInfo

    ctx = ExecutionContext()
    ctx.category = "s3"
    ctx.tool = ToolInfo(
        name="S3 버킷 목록",
        description="테스트 도구",
        category="s3",
        permission="read",
    )
    ctx.profile_name = "test-static"
    ctx.profiles = ["test-static"]
    ctx.provider_kind = ProviderKind.STATIC_CREDENTIALS
    ctx.regions = ["ap-northeast-2"]

    return ctx


# =============================================================================
# 분석 도구 픽스처
# =============================================================================


@pytest.fixture
def mock_session_iterator(mock_boto3_session):
    """SessionIterator 모킹"""
    with patch("core.auth.SessionIterator") as mock_class:
        mock_iterator = MagicMock()
        mock_iterator.__enter__ = MagicMock(return_value=mock_iterator)
        mock_iterator.__exit__ = MagicMock(return_value=None)
        mock_iterator.__iter__ = MagicMock(
            return_value=iter([(mock_boto3_session, "123456789012", "ap-northeast-2")])
        )
        mock_iterator.has_any_success.return_value = True
        mock_iterator.has_failures_only.return_value = False
        mock_iterator.has_no_sessions.return_value = False

        mock_class.return_value = mock_iterator
        yield mock_iterator


# =============================================================================
# 유틸리티 함수
# =============================================================================


def create_mock_response(
    data: Dict[str, Any],
    next_token: Optional[str] = None,
) -> Dict[str, Any]:
    """페이지네이션 응답 생성 헬퍼"""
    response = data.copy()
    if next_token:
        response["NextToken"] = next_token
    return response


def create_mock_client_error(
    error_code: str,
    error_message: str = "Test error",
) -> Exception:
    """ClientError 생성 헬퍼"""
    from botocore.exceptions import ClientError

    return ClientError(
        {
            "Error": {
                "Code": error_code,
                "Message": error_message,
            }
        },
        "TestOperation",
    )


# =============================================================================
# moto 통합 (선택적)
# =============================================================================

try:
    import moto

    @pytest.fixture
    def aws_credentials():
        """moto 사용 시 AWS 자격 증명 설정"""
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-2"

    @pytest.fixture
    def moto_ec2(aws_credentials):
        """moto를 사용한 EC2 모킹"""
        with moto.mock_aws():
            import boto3

            ec2 = boto3.client("ec2", region_name="ap-northeast-2")

            # VPC 생성
            vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
            vpc_id = vpc["Vpc"]["VpcId"]

            # 서브넷 생성
            subnet = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
            subnet_id = subnet["Subnet"]["SubnetId"]

            yield ec2, vpc_id, subnet_id

    @pytest.fixture
    def moto_s3(aws_credentials):
        """moto를 사용한 S3 모킹"""
        with moto.mock_aws():
            import boto3

            s3 = boto3.client("s3", region_name="ap-northeast-2")
            yield s3

    @pytest.fixture
    def moto_iam(aws_credentials):
        """moto를 사용한 IAM 모킹"""
        with moto.mock_aws():
            import boto3

            iam = boto3.client("iam", region_name="ap-northeast-2")
            yield iam

except ImportError:
    # moto가 설치되지 않은 경우 더미 픽스처
    @pytest.fixture
    def moto_ec2():
        pytest.skip("moto not installed")

    @pytest.fixture
    def moto_s3():
        pytest.skip("moto not installed")

    @pytest.fixture
    def moto_iam():
        pytest.skip("moto not installed")
