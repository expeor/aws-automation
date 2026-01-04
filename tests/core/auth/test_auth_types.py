# tests/test_auth_types.py
"""
internal/auth/types/types.py 단위 테스트

타입 정의 및 예외 클래스 테스트.
"""

from datetime import datetime

from core.auth.types import (
    AccountInfo,
    AccountNotFoundError,
    AuthError,
    ConfigurationError,
    NotAuthenticatedError,
    ProviderError,
    ProviderType,
    TokenExpiredError,
)

# =============================================================================
# ProviderType Enum 테스트
# =============================================================================


class TestProviderType:
    """ProviderType Enum 테스트"""

    def test_all_types_defined(self):
        """모든 타입 정의 확인"""
        assert ProviderType.SSO_SESSION.value == "sso-session"
        assert ProviderType.SSO_PROFILE.value == "sso-profile"
        assert ProviderType.STATIC_CREDENTIALS.value == "static-credentials"

    def test_type_count(self):
        """타입 개수 확인"""
        assert len(ProviderType) == 3

    def test_str_conversion(self):
        """문자열 변환"""
        assert str(ProviderType.SSO_SESSION) == "sso-session"
        assert str(ProviderType.STATIC_CREDENTIALS) == "static-credentials"

    def test_from_value(self):
        """값으로부터 생성"""
        assert ProviderType("sso-session") == ProviderType.SSO_SESSION
        assert ProviderType("static-credentials") == ProviderType.STATIC_CREDENTIALS


# =============================================================================
# AccountInfo 테스트
# =============================================================================


class TestAccountInfo:
    """AccountInfo 데이터클래스 테스트"""

    def test_basic_creation(self):
        """기본 생성"""
        account = AccountInfo(id="111122223333", name="dev-account")

        assert account.id == "111122223333"
        assert account.name == "dev-account"
        assert account.email is None
        assert account.roles == []
        assert account.default_role is None
        assert account.is_management is False
        assert account.tags == {}

    def test_full_creation(self):
        """전체 속성으로 생성"""
        account = AccountInfo(
            id="111122223333",
            name="prod-account",
            email="prod@example.com",
            roles=["AdminRole", "ReadOnlyRole"],
            default_role="ReadOnlyRole",
            is_management=True,
            tags={"env": "prod", "team": "devops"},
        )

        assert account.email == "prod@example.com"
        assert len(account.roles) == 2
        assert account.default_role == "ReadOnlyRole"
        assert account.is_management is True
        assert account.tags["env"] == "prod"

    def test_auto_name_generation(self):
        """이름 없으면 자동 생성"""
        account = AccountInfo(id="111122223333", name="")

        assert account.name == "account-111122223333"

    def test_get_role_preferred(self):
        """get_role - 선호 역할 찾기"""
        account = AccountInfo(
            id="111122223333",
            name="test",
            roles=["AdminRole", "ReadOnlyAccess", "ViewRole"],
        )

        assert account.get_role("readonly") == "ReadOnlyAccess"
        assert account.get_role("admin") == "AdminRole"

    def test_get_role_first_fallback(self):
        """get_role - 못찾으면 첫번째 역할"""
        account = AccountInfo(
            id="111122223333",
            name="test",
            roles=["CustomRole1", "CustomRole2"],
        )

        assert account.get_role("nonexistent") == "CustomRole1"

    def test_get_role_default_fallback(self):
        """get_role - 역할 없으면 default_role"""
        account = AccountInfo(
            id="111122223333",
            name="test",
            roles=[],
            default_role="FallbackRole",
        )

        assert account.get_role("any") == "FallbackRole"

    def test_hash(self):
        """해시 기능"""
        account1 = AccountInfo(id="111122223333", name="test1")
        account2 = AccountInfo(id="111122223333", name="test2")
        account3 = AccountInfo(id="444455556666", name="test1")

        # 같은 ID면 같은 해시
        assert hash(account1) == hash(account2)
        # 다른 ID면 다른 해시
        assert hash(account1) != hash(account3)

    def test_equality(self):
        """동등성 비교"""
        account1 = AccountInfo(id="111122223333", name="test1")
        account2 = AccountInfo(id="111122223333", name="test2")
        account3 = AccountInfo(id="444455556666", name="test1")

        # 같은 ID면 같음
        assert account1 == account2
        # 다른 ID면 다름
        assert account1 != account3
        # 타입 다르면 다름
        assert account1 != "111122223333"

    def test_in_set(self):
        """집합에서 사용"""
        account1 = AccountInfo(id="111122223333", name="test1")
        account2 = AccountInfo(id="111122223333", name="test2")

        accounts = {account1}
        assert account2 in accounts  # ID 같으면 같은 객체로 취급


# =============================================================================
# AuthError 테스트
# =============================================================================


class TestAuthError:
    """AuthError 기본 예외 테스트"""

    def test_basic_error(self):
        """기본 에러"""
        error = AuthError("인증 실패")

        assert error.message == "인증 실패"
        assert error.cause is None
        assert str(error) == "인증 실패"

    def test_error_with_cause(self):
        """원인 포함 에러"""
        cause = ValueError("invalid token")
        error = AuthError("인증 실패", cause=cause)

        assert error.cause == cause
        assert "인증 실패" in str(error)
        assert "invalid token" in str(error)

    def test_is_exception(self):
        """Exception 상속 확인"""
        error = AuthError("test")
        assert isinstance(error, Exception)


# =============================================================================
# NotAuthenticatedError 테스트
# =============================================================================


class TestNotAuthenticatedError:
    """NotAuthenticatedError 테스트"""

    def test_default_message(self):
        """기본 메시지"""
        error = NotAuthenticatedError()
        assert "인증이 필요합니다" in str(error)

    def test_custom_message(self):
        """커스텀 메시지"""
        error = NotAuthenticatedError("SSO 토큰이 만료됨")
        assert "SSO 토큰이 만료됨" in str(error)

    def test_is_auth_error(self):
        """AuthError 상속 확인"""
        error = NotAuthenticatedError()
        assert isinstance(error, AuthError)


# =============================================================================
# AccountNotFoundError 테스트
# =============================================================================


class TestAccountNotFoundError:
    """AccountNotFoundError 테스트"""

    def test_includes_account_id(self):
        """계정 ID 포함"""
        error = AccountNotFoundError("111122223333")

        assert error.account_id == "111122223333"
        assert "111122223333" in str(error)

    def test_message_format(self):
        """메시지 형식"""
        error = AccountNotFoundError("111122223333")
        assert "계정을 찾을 수 없습니다" in str(error)

    def test_is_auth_error(self):
        """AuthError 상속 확인"""
        error = AccountNotFoundError("123")
        assert isinstance(error, AuthError)


# =============================================================================
# TokenExpiredError 테스트
# =============================================================================


class TestTokenExpiredError:
    """TokenExpiredError 테스트"""

    def test_default_message(self):
        """기본 메시지"""
        error = TokenExpiredError()
        assert "토큰이 만료되었습니다" in str(error)

    def test_with_expired_at(self):
        """만료 시간 포함"""
        expired = datetime(2025, 12, 10, 15, 30)
        error = TokenExpiredError(expired_at=expired)

        assert error.expired_at == expired

    def test_custom_message(self):
        """커스텀 메시지"""
        error = TokenExpiredError("SSO 토큰 만료")
        assert "SSO 토큰 만료" in str(error)


# =============================================================================
# ConfigurationError 테스트
# =============================================================================


class TestConfigurationError:
    """ConfigurationError 테스트"""

    def test_basic_error(self):
        """기본 에러"""
        error = ConfigurationError("잘못된 설정")
        assert "잘못된 설정" in str(error)

    def test_with_config_key(self):
        """설정 키 포함"""
        error = ConfigurationError("값이 필요합니다", config_key="sso_start_url")

        assert error.config_key == "sso_start_url"


# =============================================================================
# ProviderError 테스트
# =============================================================================


class TestProviderError:
    """ProviderError 테스트"""

    def test_full_message(self):
        """전체 메시지 형식"""
        error = ProviderError(
            provider="sso-session",
            operation="authenticate",
            message="토큰 갱신 실패",
        )

        msg = str(error)
        assert "[sso-session]" in msg
        assert "authenticate" in msg
        assert "토큰 갱신 실패" in msg

    def test_properties(self):
        """속성 접근"""
        error = ProviderError(
            provider="static",
            operation="get_session",
            message="자격 증명 오류",
        )

        assert error.provider == "static"
        assert error.operation == "get_session"

    def test_with_cause(self):
        """원인 포함"""
        cause = RuntimeError("connection failed")
        error = ProviderError(
            provider="sso",
            operation="list_accounts",
            message="API 호출 실패",
            cause=cause,
        )

        assert error.cause == cause
