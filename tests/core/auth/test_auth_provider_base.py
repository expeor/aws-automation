# tests/test_auth_provider_base.py
"""
internal/auth/provider/base.py 단위 테스트

BaseProvider 기본 클래스 테스트.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.auth.provider.base import BaseProvider
from core.auth.types import NotAuthenticatedError, ProviderType

# =============================================================================
# ConcreteProvider - 테스트용 구현
# =============================================================================


class ConcreteProvider(BaseProvider):
    """테스트용 구체적 Provider 구현"""

    @property
    def _provider_type(self) -> ProviderType:
        return ProviderType.STATIC_CREDENTIALS

    def authenticate(self) -> None:
        self._authenticated = True

    def get_session(self, account_id=None, role_name=None, region=None):
        self._ensure_authenticated()
        return MagicMock()

    def get_aws_config(self, account_id=None, role_name=None, region=None):
        return {}

    def list_accounts(self):
        return {}

    def supports_multi_account(self) -> bool:
        return False


# =============================================================================
# BaseProvider 초기화 테스트
# =============================================================================


class TestBaseProviderInit:
    """BaseProvider 초기화 테스트"""

    def test_default_init(self):
        """기본 초기화"""
        provider = ConcreteProvider("test-provider")

        assert provider._name == "test-provider"
        assert provider._default_region == "ap-northeast-2"
        assert provider._authenticated is False

    def test_custom_region(self):
        """커스텀 리전 설정"""
        provider = ConcreteProvider("test", region="us-east-1")

        assert provider._default_region == "us-east-1"


# =============================================================================
# 기본 속성 테스트
# =============================================================================


class TestBaseProviderProperties:
    """기본 속성 메서드 테스트"""

    def test_type(self):
        """type() 메서드"""
        provider = ConcreteProvider("test")
        assert provider.type() == ProviderType.STATIC_CREDENTIALS

    def test_name(self):
        """name() 메서드"""
        provider = ConcreteProvider("my-provider")
        assert provider.name() == "my-provider"

    def test_is_authenticated_false(self):
        """인증 전 is_authenticated()"""
        provider = ConcreteProvider("test")
        assert provider.is_authenticated() is False

    def test_is_authenticated_true(self):
        """인증 후 is_authenticated()"""
        provider = ConcreteProvider("test")
        provider.authenticate()
        assert provider.is_authenticated() is True

    def test_get_default_region(self):
        """get_default_region() 메서드"""
        provider = ConcreteProvider("test", region="eu-west-1")
        assert provider.get_default_region() == "eu-west-1"


# =============================================================================
# _ensure_authenticated 테스트
# =============================================================================


class TestEnsureAuthenticated:
    """_ensure_authenticated 메서드 테스트"""

    def test_raises_when_not_authenticated(self):
        """인증 안됐으면 예외 발생"""
        provider = ConcreteProvider("test")

        with pytest.raises(NotAuthenticatedError) as exc_info:
            provider._ensure_authenticated()

        assert "test" in str(exc_info.value)

    def test_passes_when_authenticated(self):
        """인증됐으면 통과"""
        provider = ConcreteProvider("test")
        provider.authenticate()

        # 예외 발생하지 않음
        provider._ensure_authenticated()


# =============================================================================
# _create_session 테스트
# =============================================================================


class TestCreateSession:
    """_create_session 메서드 테스트"""

    @patch("core.auth.provider.base.boto3.Session")
    def test_creates_session_with_credentials(self, mock_session_class):
        """자격 증명으로 세션 생성"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        provider = ConcreteProvider("test")
        result = provider._create_session(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        mock_session_class.assert_called_once_with(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            aws_session_token=None,
            region_name="ap-northeast-2",
        )
        assert result == mock_session

    @patch("core.auth.provider.base.boto3.Session")
    def test_creates_session_with_token(self, mock_session_class):
        """세션 토큰 포함하여 세션 생성"""
        provider = ConcreteProvider("test")
        provider._create_session(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            session_token="FwoGZXIvYXdzEBY...",
        )

        call_kwargs = mock_session_class.call_args[1]
        assert call_kwargs["aws_session_token"] == "FwoGZXIvYXdzEBY..."

    @patch("core.auth.provider.base.boto3.Session")
    def test_creates_session_with_custom_region(self, mock_session_class):
        """커스텀 리전으로 세션 생성"""
        provider = ConcreteProvider("test")
        provider._create_session(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            region="us-west-2",
        )

        call_kwargs = mock_session_class.call_args[1]
        assert call_kwargs["region_name"] == "us-west-2"


# =============================================================================
# 캐시 관련 테스트
# =============================================================================


class TestCredentialsCache:
    """자격증명 캐시 테스트"""

    def test_get_cached_credentials_empty(self):
        """캐시 비어있으면 None"""
        provider = ConcreteProvider("test")
        result = provider._get_cached_credentials("111111111111", "AdminRole")
        assert result is None

    def test_cache_and_get_credentials(self):
        """캐시 저장 및 조회"""
        provider = ConcreteProvider("test")

        credentials = {
            "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
        }

        provider._cache_credentials("111111111111", "AdminRole", credentials)
        result = provider._get_cached_credentials("111111111111", "AdminRole")

        assert result == credentials

    def test_different_accounts_different_cache(self):
        """다른 계정은 다른 캐시"""
        provider = ConcreteProvider("test")

        creds1 = {"AccessKeyId": "KEY1"}
        creds2 = {"AccessKeyId": "KEY2"}

        provider._cache_credentials("111111111111", "Role", creds1)
        provider._cache_credentials("222222222222", "Role", creds2)

        assert provider._get_cached_credentials("111111111111", "Role") == creds1
        assert provider._get_cached_credentials("222222222222", "Role") == creds2


# =============================================================================
# close 테스트
# =============================================================================


class TestClose:
    """close 메서드 테스트"""

    def test_clears_authenticated(self):
        """인증 상태 초기화"""
        provider = ConcreteProvider("test")
        provider.authenticate()
        assert provider.is_authenticated() is True

        provider.close()
        assert provider.is_authenticated() is False

    def test_clears_caches(self):
        """캐시 초기화"""
        provider = ConcreteProvider("test")
        provider._cache_credentials("111111111111", "Role", {"key": "value"})

        provider.close()

        # 캐시 비어있어야 함
        result = provider._get_cached_credentials("111111111111", "Role")
        assert result is None
