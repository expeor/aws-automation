# tests/test_auth_provider_static.py
"""
core/auth/provider/static.py 단위 테스트

StaticCredentialsProvider 테스트.
"""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from core.auth.provider.static import StaticCredentialsConfig, StaticCredentialsProvider
from core.auth.types import NotAuthenticatedError, ProviderError, ProviderType

# =============================================================================
# StaticCredentialsConfig 테스트
# =============================================================================


class TestStaticCredentialsConfig:
    """StaticCredentialsConfig 테스트"""

    def test_default_init(self):
        """기본 초기화"""
        config = StaticCredentialsConfig()

        assert config.profile_name is None
        assert config.access_key_id is None
        assert config.secret_access_key is None
        assert config.session_token is None
        assert config.region == "ap-northeast-2"

    def test_profile_based_config(self):
        """프로파일 기반 설정"""
        config = StaticCredentialsConfig(
            profile_name="my-profile",
            region="us-east-1",
        )

        assert config.profile_name == "my-profile"
        assert config.name == "my-profile"
        assert config.region == "us-east-1"

    def test_direct_credentials_config(self):
        """직접 자격증명 설정"""
        config = StaticCredentialsConfig(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            session_token="FwoGZXIvYXdzEBY...",
            region="eu-west-1",
        )

        assert config.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert config.session_token == "FwoGZXIvYXdzEBY..."
        assert config.name == "static-credentials"  # profile_name 없으면 기본값

    def test_name_property_with_profile(self):
        """name 속성 - 프로파일 있을 때"""
        config = StaticCredentialsConfig(profile_name="test-profile")
        assert config.name == "test-profile"

    def test_name_property_without_profile(self):
        """name 속성 - 프로파일 없을 때"""
        config = StaticCredentialsConfig(access_key_id="AKIA...")
        assert config.name == "static-credentials"


# =============================================================================
# StaticCredentialsProvider 초기화 테스트
# =============================================================================


class TestStaticCredentialsProviderInit:
    """StaticCredentialsProvider 초기화 테스트"""

    def test_init_with_profile(self):
        """프로파일 기반 초기화"""
        config = StaticCredentialsConfig(profile_name="test-profile")
        provider = StaticCredentialsProvider(config)

        assert provider._name == "test-profile"
        assert provider._default_region == "ap-northeast-2"
        assert provider._authenticated is False

    def test_init_with_direct_credentials(self):
        """직접 자격증명 초기화"""
        config = StaticCredentialsConfig(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            region="us-west-2",
        )
        provider = StaticCredentialsProvider(config)

        assert provider._name == "static-credentials"
        assert provider._default_region == "us-west-2"

    def test_provider_type(self):
        """Provider 타입"""
        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)

        assert provider.type() == ProviderType.STATIC_CREDENTIALS


# =============================================================================
# authenticate 테스트
# =============================================================================


class TestAuthenticate:
    """authenticate 메서드 테스트"""

    @patch("core.auth.provider.static.boto3.Session")
    def test_authenticate_profile_success(self, mock_session_class):
        """프로파일 기반 인증 성공"""
        # Mock 설정
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "111111111111",
            "Arn": "arn:aws:iam::111111111111:user/test-user",
            "UserId": "AIDAIOSFODNN7EXAMPLE",
        }
        mock_session.client.return_value = mock_sts
        mock_session_class.return_value = mock_session

        config = StaticCredentialsConfig(profile_name="test-profile")
        provider = StaticCredentialsProvider(config)

        provider.authenticate()

        assert provider.is_authenticated() is True
        assert provider._account_info is not None
        assert provider._account_info.id == "111111111111"
        assert provider._account_info.name == "user-test-user"

        # 프로파일 기반 세션 생성 확인
        mock_session_class.assert_called_once_with(
            profile_name="test-profile",
            region_name="ap-northeast-2",
        )

    @patch("core.auth.provider.static.boto3.Session")
    def test_authenticate_direct_credentials_success(self, mock_session_class):
        """직접 자격증명 인증 성공"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "222222222222",
            "Arn": "arn:aws:iam::222222222222:role/AdminRole",
            "UserId": "AIDAIOSFODNN7EXAMPLE",
        }
        mock_session.client.return_value = mock_sts
        mock_session_class.return_value = mock_session

        config = StaticCredentialsConfig(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI",
            session_token="FwoGZXIvYXdzEBY...",
            region="us-east-1",
        )
        provider = StaticCredentialsProvider(config)

        provider.authenticate()

        assert provider.is_authenticated() is True
        assert provider._account_info.name == "role-AdminRole"

        # 직접 자격증명 세션 생성 확인
        mock_session_class.assert_called_once_with(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI",
            aws_session_token="FwoGZXIvYXdzEBY...",
            region_name="us-east-1",
        )

    @patch("core.auth.provider.static.boto3.Session")
    def test_authenticate_assumed_role_arn(self, mock_session_class):
        """assumed-role ARN 처리"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "333333333333",
            "Arn": "arn:aws:sts::333333333333:assumed-role/AdminRole/session-name",
            "UserId": "AROAIOSFODNN7EXAMPLE:session-name",
        }
        mock_session.client.return_value = mock_sts
        mock_session_class.return_value = mock_session

        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)

        provider.authenticate()

        assert provider._account_info.name == "assumed-AdminRole"

    @patch("core.auth.provider.static.boto3.Session")
    def test_authenticate_invalid_credentials(self, mock_session_class):
        """유효하지 않은 자격증명"""
        from botocore.exceptions import ClientError

        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "InvalidClientTokenId", "Message": "Invalid token"}},
            "GetCallerIdentity",
        )
        mock_session.client.return_value = mock_sts
        mock_session_class.return_value = mock_session

        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)

        with pytest.raises(ProviderError) as exc_info:
            provider.authenticate()

        assert "유효하지 않은 AWS 자격증명" in str(exc_info.value)

    @patch("core.auth.provider.static.boto3.Session")
    def test_authenticate_expired_token(self, mock_session_class):
        """만료된 토큰"""
        from botocore.exceptions import ClientError

        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "ExpiredToken", "Message": "Token expired"}},
            "GetCallerIdentity",
        )
        mock_session.client.return_value = mock_sts
        mock_session_class.return_value = mock_session

        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)

        with pytest.raises(ProviderError) as exc_info:
            provider.authenticate()

        assert "임시 자격증명이 만료" in str(exc_info.value)

    @patch("core.auth.provider.static.boto3.Session")
    def test_authenticate_other_client_error(self, mock_session_class):
        """기타 ClientError"""
        from botocore.exceptions import ClientError

        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "GetCallerIdentity",
        )
        mock_session.client.return_value = mock_sts
        mock_session_class.return_value = mock_session

        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)

        with pytest.raises(ProviderError) as exc_info:
            provider.authenticate()

        assert "AccessDenied" in str(exc_info.value)


# =============================================================================
# _extract_name_from_arn 테스트
# =============================================================================


class TestExtractNameFromArn:
    """_extract_name_from_arn 메서드 테스트"""

    def test_user_arn(self):
        """사용자 ARN"""
        config = StaticCredentialsConfig()
        provider = StaticCredentialsProvider(config)

        result = provider._extract_name_from_arn(
            "arn:aws:iam::111111111111:user/my-user"
        )
        assert result == "user-my-user"

    def test_role_arn(self):
        """역할 ARN"""
        config = StaticCredentialsConfig()
        provider = StaticCredentialsProvider(config)

        result = provider._extract_name_from_arn(
            "arn:aws:iam::111111111111:role/AdminRole"
        )
        assert result == "role-AdminRole"

    def test_assumed_role_arn(self):
        """assumed-role ARN"""
        config = StaticCredentialsConfig()
        provider = StaticCredentialsProvider(config)

        result = provider._extract_name_from_arn(
            "arn:aws:sts::111111111111:assumed-role/AdminRole/session-name"
        )
        assert result == "assumed-AdminRole"

    def test_unknown_arn(self):
        """알 수 없는 ARN"""
        config = StaticCredentialsConfig()
        provider = StaticCredentialsProvider(config)

        result = provider._extract_name_from_arn(
            "arn:aws:sts::111111111111:federated-user/username"
        )
        assert result == "unknown"


# =============================================================================
# get_session 테스트
# =============================================================================


class TestGetSession:
    """get_session 메서드 테스트"""

    @patch("core.auth.provider.static.boto3.Session")
    def test_get_session_default_region(self, mock_session_class):
        """기본 리전 세션"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "111111111111",
            "Arn": "arn:aws:iam::111111111111:user/test",
            "UserId": "AIDAIOSFODNN7EXAMPLE",
        }
        mock_session.client.return_value = mock_sts
        mock_session_class.return_value = mock_session

        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)
        provider.authenticate()

        session = provider.get_session()
        assert session == mock_session

    @patch("core.auth.provider.static.boto3.Session")
    def test_get_session_different_region(self, mock_session_class):
        """다른 리전 세션"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "111111111111",
            "Arn": "arn:aws:iam::111111111111:user/test",
            "UserId": "AIDAIOSFODNN7EXAMPLE",
        }
        mock_session.client.return_value = mock_sts
        mock_session_class.return_value = mock_session

        config = StaticCredentialsConfig(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            region="ap-northeast-2",
        )
        provider = StaticCredentialsProvider(config)
        provider.authenticate()

        # 다른 리전으로 세션 요청
        mock_session_class.reset_mock()
        mock_session_class.return_value = MagicMock()

        session = provider.get_session(region="us-west-2")

        # 새 세션 생성 확인
        mock_session_class.assert_called_with(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="secret",
            aws_session_token=None,
            region_name="us-west-2",
        )

    def test_get_session_not_authenticated(self):
        """인증 안됐을 때"""
        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)

        with pytest.raises(NotAuthenticatedError):
            provider.get_session()


# =============================================================================
# get_aws_config 테스트
# =============================================================================


class TestGetAwsConfig:
    """get_aws_config 메서드 테스트"""

    @patch("core.auth.provider.static.boto3.Session")
    def test_get_aws_config(self, mock_session_class):
        """AWS 설정 정보 반환"""
        mock_session = MagicMock()
        mock_session.region_name = "ap-northeast-2"
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "111111111111",
            "Arn": "arn:aws:iam::111111111111:user/test",
            "UserId": "AIDAIOSFODNN7EXAMPLE",
        }
        mock_session.client.return_value = mock_sts
        mock_session_class.return_value = mock_session

        config = StaticCredentialsConfig(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            session_token="token",
        )
        provider = StaticCredentialsProvider(config)
        provider.authenticate()

        aws_config = provider.get_aws_config()

        assert aws_config["region_name"] == "ap-northeast-2"
        assert aws_config["credentials"]["access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
        assert aws_config["credentials"]["secret_access_key"] == "secret"
        assert aws_config["credentials"]["session_token"] == "token"


# =============================================================================
# list_accounts 테스트
# =============================================================================


class TestListAccounts:
    """list_accounts 메서드 테스트"""

    @patch("core.auth.provider.static.boto3.Session")
    def test_list_accounts(self, mock_session_class):
        """계정 목록 반환"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "111111111111",
            "Arn": "arn:aws:iam::111111111111:user/test",
            "UserId": "AIDAIOSFODNN7EXAMPLE",
        }
        mock_session.client.return_value = mock_sts
        mock_session_class.return_value = mock_session

        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)
        provider.authenticate()

        accounts = provider.list_accounts()

        assert len(accounts) == 1
        assert "111111111111" in accounts
        assert accounts["111111111111"].id == "111111111111"

    def test_list_accounts_not_authenticated(self):
        """인증 안됐을 때"""
        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)

        with pytest.raises(NotAuthenticatedError):
            provider.list_accounts()


# =============================================================================
# supports_multi_account 테스트
# =============================================================================


class TestSupportsMultiAccount:
    """supports_multi_account 메서드 테스트"""

    def test_supports_multi_account(self):
        """멀티 계정 지원 안함"""
        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)

        assert provider.supports_multi_account() is False


# =============================================================================
# get_account_info 테스트
# =============================================================================


class TestGetAccountInfo:
    """get_account_info 메서드 테스트"""

    @patch("core.auth.provider.static.boto3.Session")
    def test_get_account_info(self, mock_session_class):
        """계정 정보 반환"""
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "111111111111",
            "Arn": "arn:aws:iam::111111111111:user/test",
            "UserId": "AIDAIOSFODNN7EXAMPLE",
        }
        mock_session.client.return_value = mock_sts
        mock_session_class.return_value = mock_session

        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)
        provider.authenticate()

        account_info = provider.get_account_info()

        assert account_info is not None
        assert account_info.id == "111111111111"

    def test_get_account_info_not_authenticated(self):
        """인증 안됐을 때"""
        config = StaticCredentialsConfig(profile_name="test")
        provider = StaticCredentialsProvider(config)

        assert provider.get_account_info() is None
