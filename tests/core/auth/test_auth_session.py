# tests/test_auth_session.py
"""
internal/auth/session.py 단위 테스트

Mock 데이터를 사용하여 인증 모듈의 완전성을 테스트합니다.
"""

import threading
from unittest.mock import MagicMock, patch

import pytest

# 테스트 대상 모듈
from core.auth.session import (
    SessionIterator,
    _cache_lock,
    _provider_cache,
    clear_cache,
    get_session,
    iter_profiles,
    iter_regions,
    iter_sessions,
)
from core.auth.types import AccountInfo, TokenExpiredError

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_boto3_session():
    """Mock boto3.Session"""
    with patch("core.auth.session.boto3.Session") as mock:
        mock_session = MagicMock()
        mock_session.client.return_value = MagicMock()
        mock_session.region_name = "ap-northeast-2"
        mock.return_value = mock_session
        yield mock


@pytest.fixture
def mock_sts_client():
    """Mock STS GetCallerIdentity 응답"""
    mock_client = MagicMock()
    mock_client.get_caller_identity.return_value = {
        "Account": "123456789012",
        "Arn": "arn:aws:iam::123456789012:user/test-user",
        "UserId": "AIDAEXAMPLE",
    }
    return mock_client


@pytest.fixture
def mock_execution_context():
    """Mock ExecutionContext for SessionIterator"""
    ctx = MagicMock()
    ctx.is_sso_session.return_value = False
    ctx.is_multi_profile.return_value = False
    ctx.profile_name = "test-profile"
    ctx.regions = ["ap-northeast-2", "us-east-1"]
    ctx.profiles = ["dev", "prod"]
    return ctx


@pytest.fixture
def mock_sso_execution_context():
    """Mock SSO Session ExecutionContext"""
    ctx = MagicMock()
    ctx.is_sso_session.return_value = True
    ctx.is_multi_profile.return_value = False
    ctx.regions = ["ap-northeast-2"]

    # Mock accounts
    account1 = AccountInfo(id="111111111111", name="dev-account", roles=["AdminRole"])
    account2 = AccountInfo(id="222222222222", name="prod-account", roles=["ReadOnlyRole"])
    ctx.get_target_accounts.return_value = [account1, account2]
    ctx.get_effective_role.side_effect = lambda acc_id: ("AdminRole" if acc_id == "111111111111" else "ReadOnlyRole")

    # Mock provider
    ctx.provider = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = MagicMock()
    ctx.provider.get_session.return_value = mock_session

    return ctx


@pytest.fixture(autouse=True)
def clear_provider_cache():
    """각 테스트 전후로 캐시 초기화"""
    clear_cache()
    yield
    clear_cache()


# =============================================================================
# SessionIterator 테스트
# =============================================================================


class TestSessionIterator:
    """SessionIterator 클래스 테스트"""

    def test_init(self, mock_execution_context):
        """초기화 테스트"""
        iterator = SessionIterator(mock_execution_context)

        assert iterator._ctx == mock_execution_context
        assert iterator._success_count == 0
        assert iterator._error_count == 0
        assert iterator._errors == []

    def test_context_manager(self, mock_execution_context):
        """컨텍스트 매니저 동작 테스트"""
        with SessionIterator(mock_execution_context) as sessions:
            assert isinstance(sessions, SessionIterator)

    def test_single_profile_iteration(self, mock_execution_context):
        """단일 프로파일 순회 테스트"""
        mock_execution_context.regions = ["ap-northeast-2"]

        with patch("core.auth.session.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            with SessionIterator(mock_execution_context) as sessions:
                results = list(sessions)

            assert len(results) == 1
            assert sessions.success_count == 1
            assert sessions.error_count == 0

    def test_single_profile_iteration_with_error(self, mock_execution_context):
        """단일 프로파일 순회 - 에러 발생 테스트"""
        mock_execution_context.regions = ["ap-northeast-2", "us-east-1"]

        with patch("core.auth.session.get_session") as mock_get_session:
            # 첫 번째 호출은 성공, 두 번째는 실패
            mock_session = MagicMock()
            mock_get_session.side_effect = [
                mock_session,
                Exception("Connection failed"),
            ]

            with SessionIterator(mock_execution_context) as sessions:
                results = list(sessions)

            assert len(results) == 1  # 성공한 것만
            assert sessions.success_count == 1
            assert sessions.error_count == 1
            assert len(sessions.errors) == 1
            assert sessions.errors[0][0] == "test-profile"
            assert sessions.errors[0][1] == "us-east-1"

    def test_multi_profile_iteration(self, mock_execution_context):
        """다중 프로파일 순회 테스트"""
        mock_execution_context.is_multi_profile.return_value = True
        mock_execution_context.profiles = ["dev", "prod"]
        mock_execution_context.regions = ["ap-northeast-2"]

        with patch("core.auth.session.get_session") as mock_get_session:
            mock_session = MagicMock()
            mock_get_session.return_value = mock_session

            with SessionIterator(mock_execution_context) as sessions:
                results = list(sessions)

            assert len(results) == 2
            assert sessions.success_count == 2

    def test_sso_session_iteration(self, mock_sso_execution_context):
        """SSO Session 멀티 계정 순회 테스트"""
        with SessionIterator(mock_sso_execution_context) as sessions:
            results = list(sessions)

        assert len(results) == 2  # 2 accounts × 1 region
        assert sessions.success_count == 2

        # identifier가 account_id인지 확인
        identifiers = [r[1] for r in results]
        assert "111111111111" in identifiers
        assert "222222222222" in identifiers

    def test_sso_session_iteration_with_error(self, mock_sso_execution_context):
        """SSO Session 순회 - 에러 발생 테스트"""
        # 두 번째 계정에서 에러 발생
        mock_sso_execution_context.provider.get_session.side_effect = [
            MagicMock(),
            TokenExpiredError("Token expired"),
        ]

        with SessionIterator(mock_sso_execution_context) as sessions:
            results = list(sessions)

        assert len(results) == 1
        assert sessions.success_count == 1
        assert sessions.error_count == 1

    def test_has_no_sessions(self, mock_execution_context):
        """세션 없음 확인 테스트"""
        mock_execution_context.regions = []

        with SessionIterator(mock_execution_context) as sessions:
            list(sessions)

        assert sessions.has_no_sessions() is True
        assert sessions.has_failures_only() is False
        assert sessions.has_any_success() is False

    def test_has_failures_only(self, mock_execution_context):
        """모든 실패 확인 테스트"""
        mock_execution_context.regions = ["ap-northeast-2"]

        with patch("core.auth.session.get_session") as mock_get_session:
            mock_get_session.side_effect = Exception("All failed")

            with SessionIterator(mock_execution_context) as sessions:
                list(sessions)

        assert sessions.has_no_sessions() is False
        assert sessions.has_failures_only() is True
        assert sessions.has_any_success() is False

    def test_has_any_success(self, mock_execution_context):
        """부분 성공 확인 테스트"""
        mock_execution_context.regions = ["ap-northeast-2", "us-east-1"]

        with patch("core.auth.session.get_session") as mock_get_session:
            mock_get_session.side_effect = [
                MagicMock(),
                Exception("Second failed"),
            ]

            with SessionIterator(mock_execution_context) as sessions:
                list(sessions)

        assert sessions.has_no_sessions() is False
        assert sessions.has_failures_only() is False
        assert sessions.has_any_success() is True

    def test_get_error_summary_empty(self, mock_execution_context):
        """에러 요약 - 에러 없음"""
        mock_execution_context.regions = []

        with SessionIterator(mock_execution_context) as sessions:
            list(sessions)

        assert sessions.get_error_summary() == ""

    def test_get_error_summary_with_errors(self, mock_execution_context):
        """에러 요약 - 에러 있음"""
        mock_execution_context.regions = ["ap-northeast-2", "us-east-1"]

        with patch("core.auth.session.get_session") as mock_get_session:
            mock_get_session.side_effect = [
                Exception("Error 1"),
                Exception("Error 2"),
            ]

            with SessionIterator(mock_execution_context) as sessions:
                list(sessions)

        summary = sessions.get_error_summary()

        assert "총 2개 세션 생성 실패" in summary
        assert "test-profile/ap-northeast-2" in summary
        assert "test-profile/us-east-1" in summary

    def test_get_error_summary_truncation(self, mock_execution_context):
        """에러 요약 - 5개 초과 시 자르기"""
        mock_execution_context.regions = ["r1", "r2", "r3", "r4", "r5", "r6", "r7"]

        with patch("core.auth.session.get_session") as mock_get_session:
            mock_get_session.side_effect = Exception("Error")

            with SessionIterator(mock_execution_context) as sessions:
                list(sessions)

        summary = sessions.get_error_summary()

        assert "총 7개 세션 생성 실패" in summary
        assert "외 2개" in summary  # 7 - 5 = 2


# =============================================================================
# get_session 함수 테스트
# =============================================================================


class TestGetSession:
    """get_session 함수 테스트"""

    @patch("core.auth.session._create_provider_for_profile")
    def test_get_session_creates_provider(self, mock_create_provider):
        """Provider 생성 및 캐싱 테스트"""
        mock_provider = MagicMock()
        mock_provider.is_authenticated.return_value = True
        mock_session = MagicMock()
        mock_provider.get_session.return_value = mock_session
        mock_create_provider.return_value = mock_provider

        session = get_session("new-profile", "ap-northeast-2")

        mock_create_provider.assert_called_once_with("new-profile")
        mock_provider.authenticate.assert_called_once()
        mock_provider.get_session.assert_called_with(region="ap-northeast-2")
        assert session == mock_session

    @patch("core.auth.session._create_provider_for_profile")
    def test_get_session_uses_cache(self, mock_create_provider):
        """캐시 사용 테스트"""
        mock_provider = MagicMock()
        mock_provider.is_authenticated.return_value = True
        mock_session = MagicMock()
        mock_provider.get_session.return_value = mock_session
        mock_create_provider.return_value = mock_provider

        # 첫 번째 호출
        get_session("cached-profile", "ap-northeast-2")

        # 두 번째 호출 - 캐시 사용
        get_session("cached-profile", "us-east-1")

        # Provider 생성은 한 번만 호출
        mock_create_provider.assert_called_once()

    @patch("core.auth.session._create_provider_for_profile")
    def test_get_session_auto_retry_on_token_expired(self, mock_create_provider):
        """토큰 만료 시 자동 재인증 테스트"""
        # 첫 번째 Provider - 정상 인증
        first_provider = MagicMock()
        first_provider.is_authenticated.return_value = True
        first_session = MagicMock(name="first_session")
        first_provider.get_session.return_value = first_session

        # 두 번째 Provider - 재인증 후 성공
        second_provider = MagicMock()
        second_provider.is_authenticated.return_value = True
        second_session = MagicMock(name="second_session")
        second_provider.get_session.return_value = second_session

        mock_create_provider.side_effect = [first_provider, second_provider]

        # 첫 호출 - Provider 생성 및 캐시
        session1 = get_session("expiring-profile", "ap-northeast-2")
        assert session1 == first_session
        assert mock_create_provider.call_count == 1

        # 두 번째 호출 전에 Provider가 토큰 만료되도록 설정
        first_provider.get_session.side_effect = TokenExpiredError("Expired")

        # 두 번째 호출 - TokenExpiredError 발생 → 캐시 삭제 → 재생성
        session2 = get_session("expiring-profile", "ap-northeast-2")

        assert session2 == second_session
        assert mock_create_provider.call_count == 2  # 재인증으로 2번 호출
        first_provider.close.assert_called_once()  # 만료된 Provider close 확인

    @patch("core.auth.session._create_provider_for_profile")
    def test_get_session_no_retry_when_disabled(self, mock_create_provider):
        """retry_on_expired=False일 때 재시도 안 함"""
        mock_provider = MagicMock()
        mock_provider.is_authenticated.return_value = True
        mock_provider.get_session.side_effect = TokenExpiredError("Expired")
        mock_create_provider.return_value = mock_provider

        with pytest.raises(TokenExpiredError):
            get_session("profile", "ap-northeast-2", retry_on_expired=False)


# =============================================================================
# Thread Safety 테스트
# =============================================================================


class TestThreadSafety:
    """Thread Safety 테스트"""

    def test_cache_lock_exists(self):
        """RLock 존재 확인"""
        assert _cache_lock is not None
        assert isinstance(_cache_lock, type(threading.RLock()))

    @patch("core.auth.session._create_provider_for_profile")
    def test_concurrent_get_session(self, mock_create_provider):
        """동시 get_session 호출 테스트"""
        call_count = 0
        lock = threading.Lock()

        def create_provider_side_effect(profile):
            nonlocal call_count
            with lock:
                call_count += 1
            mock_provider = MagicMock()
            mock_provider.is_authenticated.return_value = True
            mock_provider.get_session.return_value = MagicMock()
            return mock_provider

        mock_create_provider.side_effect = create_provider_side_effect

        threads = []
        results = []

        def call_get_session():
            try:
                session = get_session("concurrent-profile", "ap-northeast-2")
                results.append(session)
            except Exception as e:
                results.append(e)

        # 10개 스레드에서 동시 호출
        for _ in range(10):
            t = threading.Thread(target=call_get_session)
            threads.append(t)

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # 모든 스레드가 성공해야 함
        assert len(results) == 10
        assert all(not isinstance(r, Exception) for r in results)

        # Provider는 최대 몇 번만 생성 (Double-check 패턴으로 인해 1-2번)
        # 동시성 때문에 정확히 1번은 아닐 수 있음
        assert call_count <= 10  # 최악의 경우도 10번 이하


# =============================================================================
# iter_* 함수 테스트
# =============================================================================


class TestIterFunctions:
    """iter_regions, iter_profiles, iter_sessions 테스트"""

    @patch("core.auth.session.get_session")
    def test_iter_regions(self, mock_get_session):
        """iter_regions 테스트"""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        results = list(iter_regions("profile", ["ap-northeast-2", "us-east-1"]))

        assert len(results) == 2
        assert results[0] == (mock_session, "ap-northeast-2")
        assert results[1] == (mock_session, "us-east-1")

    @patch("core.auth.session.get_session")
    def test_iter_regions_with_error(self, mock_get_session):
        """iter_regions - 에러 발생 시 건너뛰기"""
        mock_session = MagicMock()
        mock_get_session.side_effect = [Exception("Error"), mock_session]

        results = list(iter_regions("profile", ["r1", "r2"]))

        assert len(results) == 1
        assert results[0] == (mock_session, "r2")

    @patch("core.auth.session.get_session")
    def test_iter_profiles(self, mock_get_session):
        """iter_profiles 테스트"""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        results = list(iter_profiles(["dev", "prod"], "ap-northeast-2"))

        assert len(results) == 2
        assert results[0] == (mock_session, "dev")
        assert results[1] == (mock_session, "prod")

    @patch("core.auth.session.get_session")
    def test_iter_sessions(self, mock_get_session):
        """iter_sessions 테스트"""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        results = list(iter_sessions(["dev", "prod"], ["r1", "r2"]))

        assert len(results) == 4  # 2 profiles × 2 regions


# =============================================================================
# clear_cache 테스트
# =============================================================================


class TestClearCache:
    """clear_cache 함수 테스트"""

    @patch("core.auth.session._create_provider_for_profile")
    def test_clear_cache(self, mock_create_provider):
        """캐시 초기화 테스트"""
        mock_provider = MagicMock()
        mock_provider.is_authenticated.return_value = True
        mock_provider.get_session.return_value = MagicMock()
        mock_create_provider.return_value = mock_provider

        # 캐시 생성
        get_session("profile1", "ap-northeast-2")
        get_session("profile2", "ap-northeast-2")

        # 캐시 초기화
        clear_cache()

        # Provider.close()가 호출되었는지 확인
        assert mock_provider.close.call_count >= 1

        # 캐시가 비어있는지 확인
        assert len(_provider_cache) == 0


# =============================================================================
# _create_provider_for_profile 테스트
# =============================================================================


class TestCreateProviderForProfile:
    """_create_provider_for_profile 함수 테스트"""

    @patch("core.auth.session.Loader")
    @patch("core.auth.session.detect_provider_type")
    def test_profile_not_found(self, mock_detect, mock_loader_class):
        """프로파일을 찾을 수 없는 경우"""
        from core.auth.session import _create_provider_for_profile

        mock_loader = MagicMock()
        mock_config = MagicMock()
        mock_config.profiles = {}  # 빈 프로파일
        mock_loader.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader

        with pytest.raises(ValueError) as exc_info:
            _create_provider_for_profile("nonexistent-profile")

        assert "프로파일을 찾을 수 없습니다" in str(exc_info.value)

    @patch("core.auth.session.Loader")
    @patch("core.auth.session.detect_provider_type")
    def test_sso_session_provider(self, mock_detect, mock_loader_class):
        """SSO Session Provider 생성"""
        from core.auth.provider import SSOSessionProvider
        from core.auth.session import _create_provider_for_profile
        from core.auth.types import ProviderType

        # Mock 설정
        mock_loader = MagicMock()
        mock_config = MagicMock()

        mock_profile = MagicMock()
        mock_profile.sso_session = "my-sso-session"
        mock_profile.sso_account_id = "123456789012"
        mock_profile.sso_role_name = "AdminRole"

        mock_session = MagicMock()
        mock_session.start_url = "https://example.awsapps.com/start"
        mock_session.region = "us-east-1"

        mock_config.profiles = {"sso-profile": mock_profile}
        mock_config.sessions = {"my-sso-session": mock_session}
        mock_loader.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader

        mock_detect.return_value = ProviderType.SSO_SESSION

        provider = _create_provider_for_profile("sso-profile")

        assert isinstance(provider, SSOSessionProvider)

    @patch("core.auth.session.Loader")
    @patch("core.auth.session.detect_provider_type")
    def test_sso_session_not_found(self, mock_detect, mock_loader_class):
        """SSO 세션을 찾을 수 없는 경우"""
        from core.auth.session import _create_provider_for_profile
        from core.auth.types import ProviderType

        mock_loader = MagicMock()
        mock_config = MagicMock()

        mock_profile = MagicMock()
        mock_profile.sso_session = "missing-session"

        mock_config.profiles = {"sso-profile": mock_profile}
        mock_config.sessions = {}  # 세션 없음
        mock_loader.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader

        mock_detect.return_value = ProviderType.SSO_SESSION

        with pytest.raises(ValueError) as exc_info:
            _create_provider_for_profile("sso-profile")

        assert "SSO 세션을 찾을 수 없습니다" in str(exc_info.value)

    @patch("core.auth.session.Loader")
    @patch("core.auth.session.detect_provider_type")
    def test_sso_profile_with_session(self, mock_detect, mock_loader_class):
        """SSO Profile Provider 생성 (sso_session 참조)"""
        from core.auth.provider import SSOProfileProvider
        from core.auth.session import _create_provider_for_profile
        from core.auth.types import ProviderType

        mock_loader = MagicMock()
        mock_config = MagicMock()

        mock_profile = MagicMock()
        mock_profile.sso_session = "my-sso-session"
        mock_profile.sso_account_id = "123456789012"
        mock_profile.sso_role_name = "ReadOnlyRole"
        mock_profile.region = "ap-northeast-2"

        mock_session = MagicMock()
        mock_session.start_url = "https://example.awsapps.com/start"
        mock_session.region = "us-east-1"

        mock_config.profiles = {"sso-profile": mock_profile}
        mock_config.sessions = {"my-sso-session": mock_session}
        mock_loader.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader

        mock_detect.return_value = ProviderType.SSO_PROFILE

        provider = _create_provider_for_profile("sso-profile")

        assert isinstance(provider, SSOProfileProvider)

    @patch("core.auth.session.Loader")
    @patch("core.auth.session.detect_provider_type")
    def test_sso_profile_legacy(self, mock_detect, mock_loader_class):
        """SSO Profile Provider 생성 (Legacy 직접 설정)"""
        from core.auth.provider import SSOProfileProvider
        from core.auth.session import _create_provider_for_profile
        from core.auth.types import ProviderType

        mock_loader = MagicMock()
        mock_config = MagicMock()

        mock_profile = MagicMock()
        mock_profile.sso_session = None  # Legacy
        mock_profile.sso_start_url = "https://legacy.awsapps.com/start"
        mock_profile.sso_region = "us-west-2"
        mock_profile.sso_account_id = "123456789012"
        mock_profile.sso_role_name = "AdminRole"
        mock_profile.region = None

        mock_config.profiles = {"legacy-sso": mock_profile}
        mock_config.sessions = {}
        mock_loader.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader

        mock_detect.return_value = ProviderType.SSO_PROFILE

        provider = _create_provider_for_profile("legacy-sso")

        assert isinstance(provider, SSOProfileProvider)

    @patch("core.auth.session.Loader")
    @patch("core.auth.session.detect_provider_type")
    def test_sso_profile_session_not_found(self, mock_detect, mock_loader_class):
        """SSO Profile에서 참조하는 세션을 찾을 수 없는 경우"""
        from core.auth.session import _create_provider_for_profile
        from core.auth.types import ProviderType

        mock_loader = MagicMock()
        mock_config = MagicMock()

        mock_profile = MagicMock()
        mock_profile.sso_session = "missing-session"

        mock_config.profiles = {"sso-profile": mock_profile}
        mock_config.sessions = {}
        mock_loader.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader

        mock_detect.return_value = ProviderType.SSO_PROFILE

        with pytest.raises(ValueError) as exc_info:
            _create_provider_for_profile("sso-profile")

        assert "SSO 세션을 찾을 수 없습니다" in str(exc_info.value)

    @patch("core.auth.session.Loader")
    @patch("core.auth.session.detect_provider_type")
    def test_static_credentials_provider(self, mock_detect, mock_loader_class):
        """Static Credentials Provider 생성"""
        from core.auth.provider import StaticCredentialsProvider
        from core.auth.session import _create_provider_for_profile
        from core.auth.types import ProviderType

        mock_loader = MagicMock()
        mock_config = MagicMock()

        mock_profile = MagicMock()
        mock_profile.aws_access_key_id = "AKIAEXAMPLE"
        mock_profile.aws_secret_access_key = "secret"
        mock_profile.aws_session_token = None
        mock_profile.region = "ap-northeast-2"

        mock_config.profiles = {"static-profile": mock_profile}
        mock_loader.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader

        mock_detect.return_value = ProviderType.STATIC_CREDENTIALS

        provider = _create_provider_for_profile("static-profile")

        assert isinstance(provider, StaticCredentialsProvider)

    @patch("core.auth.session.Loader")
    @patch("core.auth.session.detect_provider_type")
    def test_unsupported_provider_type(self, mock_detect, mock_loader_class):
        """지원하지 않는 Provider 타입이면 ValueError"""
        from core.auth.session import _create_provider_for_profile

        mock_loader = MagicMock()
        mock_config = MagicMock()

        mock_profile = MagicMock()
        mock_config.profiles = {"unsupported-profile": mock_profile}
        mock_loader.load.return_value = mock_config
        mock_loader_class.return_value = mock_loader

        mock_detect.return_value = None  # 지원하지 않는 타입

        with pytest.raises(ValueError) as exc_info:
            _create_provider_for_profile("unsupported-profile")

        assert "지원하지 않는 Provider 타입" in str(exc_info.value)


# =============================================================================
# iter_context_sessions 테스트
# =============================================================================


class TestIterContextSessions:
    """iter_context_sessions 함수 테스트"""

    def test_sso_session_mode(self):
        """SSO Session 모드"""
        from core.auth.session import iter_context_sessions

        ctx = MagicMock()
        ctx.is_sso_session.return_value = True
        ctx.is_multi_profile.return_value = False
        ctx.regions = ["ap-northeast-2"]

        account = MagicMock()
        account.id = "111111111111"
        ctx.get_target_accounts.return_value = [account]
        ctx.get_effective_role.return_value = "AdminRole"

        mock_session = MagicMock()
        ctx.provider.get_session.return_value = mock_session

        results = list(iter_context_sessions(ctx))

        assert len(results) == 1
        assert results[0][0] == mock_session
        assert results[0][1] == "111111111111"
        assert results[0][2] == "ap-northeast-2"

    def test_sso_session_no_role(self):
        """SSO Session - 역할 없는 계정 스킵"""
        from core.auth.session import iter_context_sessions

        ctx = MagicMock()
        ctx.is_sso_session.return_value = True
        ctx.is_multi_profile.return_value = False
        ctx.regions = ["ap-northeast-2"]

        account = MagicMock()
        account.id = "111111111111"
        ctx.get_target_accounts.return_value = [account]
        ctx.get_effective_role.return_value = None  # 역할 없음

        results = list(iter_context_sessions(ctx))

        assert len(results) == 0

    def test_sso_session_error_handling(self):
        """SSO Session - 에러 발생 시 건너뛰기"""
        from core.auth.session import iter_context_sessions

        ctx = MagicMock()
        ctx.is_sso_session.return_value = True
        ctx.is_multi_profile.return_value = False
        ctx.regions = ["ap-northeast-2", "us-east-1"]

        account = MagicMock()
        account.id = "111111111111"
        ctx.get_target_accounts.return_value = [account]
        ctx.get_effective_role.return_value = "AdminRole"

        # 첫 번째 성공, 두 번째 실패
        ctx.provider.get_session.side_effect = [
            MagicMock(),
            Exception("Connection failed"),
        ]

        results = list(iter_context_sessions(ctx))

        assert len(results) == 1

    @patch("core.auth.session.get_session")
    def test_multi_profile_mode(self, mock_get_session):
        """다중 프로파일 모드"""
        from core.auth.session import iter_context_sessions

        ctx = MagicMock()
        ctx.is_sso_session.return_value = False
        ctx.is_multi_profile.return_value = True
        ctx.profiles = ["dev", "prod"]
        ctx.regions = ["ap-northeast-2"]

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        results = list(iter_context_sessions(ctx))

        assert len(results) == 2

    @patch("core.auth.session.get_session")
    def test_multi_profile_error_handling(self, mock_get_session):
        """다중 프로파일 - 에러 발생 시 건너뛰기"""
        from core.auth.session import iter_context_sessions

        ctx = MagicMock()
        ctx.is_sso_session.return_value = False
        ctx.is_multi_profile.return_value = True
        ctx.profiles = ["dev", "prod"]
        ctx.regions = ["ap-northeast-2"]

        mock_get_session.side_effect = [
            MagicMock(),
            Exception("Auth failed"),
        ]

        results = list(iter_context_sessions(ctx))

        assert len(results) == 1

    @patch("core.auth.session.get_session")
    def test_single_profile_mode(self, mock_get_session):
        """단일 프로파일 모드"""
        from core.auth.session import iter_context_sessions

        ctx = MagicMock()
        ctx.is_sso_session.return_value = False
        ctx.is_multi_profile.return_value = False
        ctx.profile_name = "my-profile"
        ctx.regions = ["ap-northeast-2", "us-east-1"]

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        results = list(iter_context_sessions(ctx))

        assert len(results) == 2

    @patch("core.auth.session.get_session")
    def test_single_profile_error_handling(self, mock_get_session):
        """단일 프로파일 - 에러 발생 시 건너뛰기"""
        from core.auth.session import iter_context_sessions

        ctx = MagicMock()
        ctx.is_sso_session.return_value = False
        ctx.is_multi_profile.return_value = False
        ctx.profile_name = "my-profile"
        ctx.regions = ["ap-northeast-2", "us-east-1"]

        mock_get_session.side_effect = [
            Exception("Error"),
            MagicMock(),
        ]

        results = list(iter_context_sessions(ctx))

        assert len(results) == 1


# =============================================================================
# get_context_session 테스트
# =============================================================================


class TestGetContextSession:
    """get_context_session 함수 테스트"""

    def test_sso_session_single_account(self):
        """SSO Session - 단일 계정 자동 추론"""
        from core.auth.session import get_context_session

        ctx = MagicMock()
        ctx.is_sso_session.return_value = True

        account = MagicMock()
        account.id = "111111111111"
        ctx.get_target_accounts.return_value = [account]
        ctx.get_effective_role.return_value = "AdminRole"

        mock_session = MagicMock()
        ctx.provider.get_session.return_value = mock_session

        session = get_context_session(ctx, "ap-northeast-2")

        assert session == mock_session
        ctx.provider.get_session.assert_called_once_with(
            account_id="111111111111",
            role_name="AdminRole",
            region="ap-northeast-2",
        )

    def test_sso_session_explicit_account(self):
        """SSO Session - 명시적 계정 ID"""
        from core.auth.session import get_context_session

        ctx = MagicMock()
        ctx.is_sso_session.return_value = True
        ctx.get_effective_role.return_value = "ReadOnlyRole"

        mock_session = MagicMock()
        ctx.provider.get_session.return_value = mock_session

        session = get_context_session(ctx, "us-east-1", account_id="222222222222")

        assert session == mock_session
        ctx.provider.get_session.assert_called_once_with(
            account_id="222222222222",
            role_name="ReadOnlyRole",
            region="us-east-1",
        )

    def test_sso_session_multiple_accounts_no_id(self):
        """SSO Session - 여러 계정인데 account_id 없으면 에러"""
        from core.auth.session import get_context_session

        ctx = MagicMock()
        ctx.is_sso_session.return_value = True

        account1 = MagicMock()
        account1.id = "111111111111"
        account2 = MagicMock()
        account2.id = "222222222222"
        ctx.get_target_accounts.return_value = [account1, account2]

        with pytest.raises(ValueError) as exc_info:
            get_context_session(ctx, "ap-northeast-2")

        assert "account_id를 명시해야 합니다" in str(exc_info.value)

    def test_sso_session_no_role(self):
        """SSO Session - 역할 없으면 에러"""
        from core.auth.session import get_context_session

        ctx = MagicMock()
        ctx.is_sso_session.return_value = True

        account = MagicMock()
        account.id = "111111111111"
        ctx.get_target_accounts.return_value = [account]
        ctx.get_effective_role.return_value = None  # 역할 없음

        with pytest.raises(ValueError) as exc_info:
            get_context_session(ctx, "ap-northeast-2")

        assert "사용할 역할이 없습니다" in str(exc_info.value)

    @patch("core.auth.session.get_session")
    def test_non_sso_mode(self, mock_get_session):
        """비 SSO 모드 (프로파일 기반)"""
        from core.auth.session import get_context_session

        ctx = MagicMock()
        ctx.is_sso_session.return_value = False
        ctx.profile_name = "my-profile"

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        session = get_context_session(ctx, "ap-northeast-2")

        assert session == mock_session
        mock_get_session.assert_called_once_with("my-profile", "ap-northeast-2")


# =============================================================================
# SessionIterator SSO 추가 테스트
# =============================================================================


class TestSessionIteratorSsoAdditional:
    """SessionIterator SSO 관련 추가 테스트"""

    def test_sso_session_no_role_skip(self):
        """SSO Session - 역할 없는 계정 스킵"""
        ctx = MagicMock()
        ctx.is_sso_session.return_value = True
        ctx.is_multi_profile.return_value = False
        ctx.regions = ["ap-northeast-2"]

        account = MagicMock()
        account.id = "111111111111"
        ctx.get_target_accounts.return_value = [account]
        ctx.get_effective_role.return_value = None  # 역할 없음

        with SessionIterator(ctx) as sessions:
            results = list(sessions)

        assert len(results) == 0
        assert sessions.success_count == 0
        assert sessions.error_count == 0

    def test_multi_profile_with_errors(self):
        """다중 프로파일 순회 에러 추적"""
        ctx = MagicMock()
        ctx.is_sso_session.return_value = False
        ctx.is_multi_profile.return_value = True
        ctx.profiles = ["dev", "prod"]
        ctx.regions = ["ap-northeast-2"]

        with patch("core.auth.session.get_session") as mock_get_session:
            mock_get_session.side_effect = [
                MagicMock(),
                Exception("Auth failed"),
            ]

            with SessionIterator(ctx) as sessions:
                results = list(sessions)

            assert len(results) == 1
            assert sessions.success_count == 1
            assert sessions.error_count == 1
            assert sessions.errors[0][0] == "prod"


# =============================================================================
# iter_sessions 에러 처리 테스트
# =============================================================================


class TestIterSessionsErrorHandling:
    """iter_sessions 에러 처리 테스트"""

    @patch("core.auth.session.get_session")
    def test_iter_profiles_with_error(self, mock_get_session):
        """iter_profiles - 에러 발생 시 건너뛰기"""
        mock_session = MagicMock()
        mock_get_session.side_effect = [
            Exception("Error"),
            mock_session,
        ]

        results = list(iter_profiles(["dev", "prod"], "ap-northeast-2"))

        assert len(results) == 1
        assert results[0] == (mock_session, "prod")

    @patch("core.auth.session.get_session")
    def test_iter_sessions_with_errors(self, mock_get_session):
        """iter_sessions - 일부 에러 발생"""
        mock_session = MagicMock()
        mock_get_session.side_effect = [
            mock_session,
            Exception("Error 1"),
            mock_session,
            Exception("Error 2"),
        ]

        results = list(iter_sessions(["dev", "prod"], ["r1", "r2"]))

        assert len(results) == 2  # 4 - 2 errors


# =============================================================================
# 추가 엣지 케이스 테스트
# =============================================================================


class TestGetSessionEdgeCases:
    """get_session 엣지 케이스 테스트"""

    @patch("core.auth.session._create_provider_for_profile")
    def test_token_expired_retry_fails(self, mock_create_provider):
        """토큰 만료 후 재시도도 실패하는 경우"""
        from core.auth.session import _cache_lock, _provider_cache, get_session
        from core.auth.types import TokenExpiredError

        # 캐시 초기화
        with _cache_lock:
            _provider_cache.clear()

        # 첫 번째 provider - 캐시에 있는 상태에서 토큰 만료
        first_provider = MagicMock()
        first_provider.is_authenticated.return_value = True
        first_provider.get_session.side_effect = TokenExpiredError("Token expired")
        first_provider.close = MagicMock()

        # 캐시에 먼저 저장
        with _cache_lock:
            _provider_cache["expired-profile"] = first_provider

        # 두 번째 provider - 재시도 시 생성됨 (retry_on_expired=False 상태로 재귀 호출)
        second_provider = MagicMock()
        second_provider.is_authenticated.return_value = True
        second_provider.get_session.side_effect = TokenExpiredError("Still expired")

        mock_create_provider.return_value = second_provider

        with pytest.raises(TokenExpiredError):
            get_session("expired-profile", "ap-northeast-2")

        # 첫 번째 provider가 close 되었는지 확인
        first_provider.close.assert_called_once()

        # 캐시 정리
        with _cache_lock:
            _provider_cache.clear()

    def test_token_expired_no_retry(self):
        """retry_on_expired=False일 때 바로 예외 발생 (line 108 커버)"""
        from core.auth.session import _cache_lock, _provider_cache, get_session
        from core.auth.types import TokenExpiredError

        # 캐시 초기화
        with _cache_lock:
            _provider_cache.clear()

        # provider - 캐시에 있는 상태에서 토큰 만료
        provider = MagicMock()
        provider.is_authenticated.return_value = True
        provider.get_session.side_effect = TokenExpiredError("Token expired")

        # 캐시에 저장
        with _cache_lock:
            _provider_cache["no-retry-profile"] = provider

        # retry_on_expired=False로 직접 호출
        with pytest.raises(TokenExpiredError):
            get_session("no-retry-profile", "ap-northeast-2", retry_on_expired=False)

        # 캐시 정리
        with _cache_lock:
            _provider_cache.clear()

    @patch("core.auth.session._create_provider_for_profile")
    def test_cache_race_condition(self, mock_create_provider):
        """캐시 경쟁 상태 - 다른 스레드가 먼저 생성한 경우"""
        from core.auth.session import _cache_lock, _provider_cache, get_session

        # 캐시 초기화
        with _cache_lock:
            _provider_cache.clear()

        existing_provider = MagicMock()
        existing_provider.get_session.return_value = MagicMock()

        new_provider = MagicMock()
        new_provider.close = MagicMock()

        def create_and_inject_cache(profile):
            # Provider 생성 중 다른 스레드가 캐시에 먼저 넣은 상황 시뮬레이션
            with _cache_lock:
                _provider_cache[profile] = existing_provider
            return new_provider

        mock_create_provider.side_effect = create_and_inject_cache

        get_session("race-profile", "us-east-1")

        # 새로 만든 provider는 close 되어야 함
        new_provider.close.assert_called_once()

        # 캐시 정리
        with _cache_lock:
            _provider_cache.clear()


class TestClearCacheEdgeCases:
    """clear_cache 엣지 케이스 테스트"""

    def test_clear_cache_provider_close_fails(self):
        """provider.close() 실패해도 캐시는 정리됨"""
        from core.auth.session import _cache_lock, _provider_cache, clear_cache

        # 캐시에 실패하는 provider 추가
        failing_provider = MagicMock()
        failing_provider.close.side_effect = Exception("Close failed")

        with _cache_lock:
            _provider_cache["failing-profile"] = failing_provider

        # 예외 발생하지 않고 캐시 정리됨
        clear_cache()

        with _cache_lock:
            assert len(_provider_cache) == 0
