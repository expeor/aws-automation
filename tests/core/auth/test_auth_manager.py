# tests/core/auth/test_auth_manager.py
"""
core/auth/auth.py Manager 클래스 단위 테스트

테스트 대상:
- Manager: AWS 인증 Manager
  - Provider 등록 및 관리
  - 활성 Provider 설정
  - 멀티 계정 병렬 작업 지원
  - 통합된 인터페이스 제공
"""

from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError

from core.auth.auth import Manager, create_manager
from core.auth.config import AWSProfile, AWSSession, ParsedConfig
from core.auth.types import (
    AccountInfo,
    AuthError,
    NotAuthenticatedError,
    Provider,
    ProviderError,
    ProviderType,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_provider():
    """Mock Provider 생성"""
    provider = MagicMock(spec=Provider)
    provider.type.return_value = ProviderType.SSO_SESSION
    provider.name.return_value = "test-provider"
    provider.is_authenticated.return_value = True
    provider.get_default_region.return_value = "ap-northeast-2"
    provider.list_accounts.return_value = {
        "123456789012": AccountInfo(
            id="123456789012",
            name="test-account",
            roles=["AdminRole"],
        )
    }

    # Mock session
    mock_session = MagicMock(spec=boto3.Session)
    mock_session.region_name = "ap-northeast-2"
    provider.get_session.return_value = mock_session

    # Mock AWS config
    provider.get_aws_config.return_value = {
        "region_name": "ap-northeast-2",
        "credentials": {
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "secret_access_key": "secret",
            "session_token": "token",
        },
    }

    return provider


@pytest.fixture
def mock_static_provider():
    """Mock Static Credentials Provider"""
    provider = MagicMock(spec=Provider)
    provider.type.return_value = ProviderType.STATIC_CREDENTIALS
    provider.name.return_value = "static-provider"
    provider.is_authenticated.return_value = True
    provider.get_default_region.return_value = "us-east-1"
    provider.list_accounts.return_value = {
        "987654321098": AccountInfo(
            id="987654321098",
            name="static-account",
            roles=[],
        )
    }

    mock_session = MagicMock(spec=boto3.Session)
    mock_session.region_name = "us-east-1"
    provider.get_session.return_value = mock_session

    return provider


@pytest.fixture
def manager():
    """Manager 인스턴스 생성"""
    return Manager()


@pytest.fixture
def mock_parsed_config():
    """Mock ParsedConfig"""
    config = ParsedConfig(
        profiles={
            "test-profile": AWSProfile(
                name="test-profile",
                region="ap-northeast-2",
                sso_session="test-session",
            ),
        },
        sessions={
            "test-session": AWSSession(
                name="test-session",
                start_url="https://test.awsapps.com/start",
                region="ap-northeast-2",
            ),
        },
        default_profile="test-profile",
    )
    return config


# =============================================================================
# Manager 초기화 테스트
# =============================================================================


class TestManagerInit:
    """Manager 초기화 테스트"""

    def test_init(self):
        """Manager 초기화"""
        manager = Manager()

        assert manager._providers == {}
        assert manager._active_provider is None
        assert manager._config_loader is not None

    def test_create_manager_function(self):
        """create_manager 편의 함수 테스트"""
        manager = create_manager()

        assert isinstance(manager, Manager)
        assert manager._providers == {}
        assert manager._active_provider is None


# =============================================================================
# Provider 관리 테스트
# =============================================================================


class TestManagerProviderManagement:
    """Provider 관리 기능 테스트"""

    def test_register_provider(self, manager, mock_provider):
        """Provider 등록"""
        manager.register_provider(mock_provider)

        key = "sso-session:test-provider"
        assert key in manager._providers
        assert manager._providers[key] is mock_provider

    def test_register_multiple_providers(self, manager, mock_provider, mock_static_provider):
        """여러 Provider 등록"""
        manager.register_provider(mock_provider)
        manager.register_provider(mock_static_provider)

        assert len(manager._providers) == 2
        assert "sso-session:test-provider" in manager._providers
        assert "static-credentials:static-provider" in manager._providers

    def test_unregister_provider(self, manager, mock_provider):
        """Provider 등록 해제"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        result = manager.unregister_provider(mock_provider)

        assert result is True
        assert len(manager._providers) == 0
        assert manager._active_provider is None

    def test_unregister_non_registered_provider(self, manager, mock_provider):
        """등록되지 않은 Provider 해제 시도"""
        result = manager.unregister_provider(mock_provider)

        assert result is False

    def test_set_active_provider(self, manager, mock_provider):
        """활성 Provider 설정"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        assert manager._active_provider is mock_provider

    def test_get_active_provider(self, manager, mock_provider):
        """활성 Provider 조회"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        active = manager.get_active_provider()

        assert active is mock_provider

    def test_get_active_provider_none(self, manager):
        """활성 Provider 없을 때"""
        active = manager.get_active_provider()

        assert active is None

    def test_find_provider_by_type(self, manager, mock_provider, mock_static_provider):
        """Provider 타입으로 검색"""
        manager.register_provider(mock_provider)
        manager.register_provider(mock_static_provider)

        found = manager.find_provider(provider_type=ProviderType.SSO_SESSION)

        assert found is mock_provider

    def test_find_provider_by_name(self, manager, mock_provider, mock_static_provider):
        """Provider 이름으로 검색"""
        manager.register_provider(mock_provider)
        manager.register_provider(mock_static_provider)

        found = manager.find_provider(name="static-provider")

        assert found is mock_static_provider

    def test_find_provider_by_type_and_name(self, manager, mock_provider):
        """Provider 타입과 이름으로 검색"""
        manager.register_provider(mock_provider)

        found = manager.find_provider(provider_type=ProviderType.SSO_SESSION, name="test-provider")

        assert found is mock_provider

    def test_find_provider_not_found(self, manager):
        """Provider 찾지 못함"""
        found = manager.find_provider(name="non-existent")

        assert found is None

    def test_list_providers(self, manager, mock_provider, mock_static_provider):
        """등록된 Provider 목록"""
        manager.register_provider(mock_provider)
        manager.register_provider(mock_static_provider)

        providers = manager.list_providers()

        assert len(providers) == 2
        assert mock_provider in providers
        assert mock_static_provider in providers

    def test_list_providers_empty(self, manager):
        """Provider 없을 때 목록"""
        providers = manager.list_providers()

        assert providers == []


# =============================================================================
# 인증 API 테스트
# =============================================================================


class TestManagerAuthAPI:
    """Manager 인증 API 테스트"""

    def test_authenticate(self, manager, mock_provider):
        """인증 수행"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        manager.authenticate()

        mock_provider.authenticate.assert_called_once()

    def test_authenticate_no_active_provider(self, manager):
        """활성 Provider 없이 인증 시도"""
        with pytest.raises(NotAuthenticatedError) as exc_info:
            manager.authenticate()

        assert "활성 Provider가 설정되지 않았습니다" in str(exc_info.value)

    def test_is_authenticated_true(self, manager, mock_provider):
        """인증 상태 확인 - 인증됨"""
        mock_provider.is_authenticated.return_value = True
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        assert manager.is_authenticated() is True

    def test_is_authenticated_false(self, manager, mock_provider):
        """인증 상태 확인 - 인증 안됨"""
        mock_provider.is_authenticated.return_value = False
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        assert manager.is_authenticated() is False

    def test_is_authenticated_no_provider(self, manager):
        """활성 Provider 없을 때 인증 상태"""
        assert manager.is_authenticated() is False

    def test_get_session(self, manager, mock_provider):
        """boto3 Session 획득"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        session = manager.get_session(account_id="123456789012", role_name="AdminRole", region="ap-northeast-2")

        assert session is not None
        mock_provider.get_session.assert_called_once_with("123456789012", "AdminRole", "ap-northeast-2")

    def test_get_session_no_active_provider(self, manager):
        """활성 Provider 없이 세션 획득 시도"""
        with pytest.raises(NotAuthenticatedError):
            manager.get_session()

    def test_get_aws_config(self, manager, mock_provider):
        """AWS Config 획득"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        config = manager.get_aws_config(account_id="123456789012", role_name="AdminRole")

        assert config is not None
        assert "region_name" in config
        assert "credentials" in config
        mock_provider.get_aws_config.assert_called_once_with("123456789012", "AdminRole", None)

    def test_get_default_region(self, manager, mock_provider):
        """기본 리전 조회"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        region = manager.get_default_region()

        assert region == "ap-northeast-2"
        mock_provider.get_default_region.assert_called_once()


# =============================================================================
# 계정 관리 테스트
# =============================================================================


class TestManagerAccountManagement:
    """Manager 계정 관리 테스트"""

    def test_list_accounts(self, manager, mock_provider):
        """계정 목록 조회"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        accounts = manager.list_accounts()

        assert len(accounts) == 1
        assert "123456789012" in accounts
        assert accounts["123456789012"].name == "test-account"

    def test_list_all_accounts_single_provider(self, manager, mock_provider):
        """전체 계정 목록 - 단일 Provider"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        accounts = manager.list_all_accounts()

        assert len(accounts) == 1
        assert "123456789012" in accounts

    def test_list_all_accounts_multiple_providers(self, manager, mock_provider, mock_static_provider):
        """전체 계정 목록 - 다중 Provider"""
        manager.register_provider(mock_provider)
        manager.register_provider(mock_static_provider)
        manager.set_active_provider(mock_provider)

        accounts = manager.list_all_accounts()

        assert len(accounts) == 2
        assert "123456789012" in accounts
        assert "987654321098" in accounts

    def test_list_all_accounts_with_error(self, manager, mock_provider, mock_static_provider):
        """전체 계정 목록 - 일부 Provider 에러"""
        # mock_static_provider가 에러 발생하도록 설정
        mock_static_provider.list_accounts.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "ListAccounts",
        )

        manager.register_provider(mock_provider)
        manager.register_provider(mock_static_provider)

        accounts = manager.list_all_accounts()

        # 에러가 발생해도 다른 Provider의 계정은 포함
        assert len(accounts) == 1
        assert "123456789012" in accounts

    def test_list_all_accounts_not_authenticated(self, manager, mock_provider):
        """전체 계정 목록 - 인증되지 않은 Provider 스킵"""
        mock_provider.is_authenticated.return_value = False
        manager.register_provider(mock_provider)

        accounts = manager.list_all_accounts()

        assert len(accounts) == 0

    def test_get_account(self, manager, mock_provider):
        """특정 계정 정보 조회"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        account = manager.get_account("123456789012")

        assert account is not None
        assert account.id == "123456789012"
        assert account.name == "test-account"

    def test_get_account_not_found(self, manager, mock_provider):
        """존재하지 않는 계정 조회"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        account = manager.get_account("999999999999")

        assert account is None


# =============================================================================
# 멀티 계정 작업 테스트
# =============================================================================


class TestManagerMultiAccountOperations:
    """Manager 멀티 계정 작업 테스트"""

    def test_for_each_account_sequential(self, manager, mock_provider):
        """순차 멀티 계정 작업"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        # 작업 함수
        results = []

        def work_func(account_info, session):
            results.append(account_info.id)
            return f"result-{account_info.id}"

        output = manager.for_each_account(work_func)

        assert len(output) == 1
        assert "123456789012" in output
        assert output["123456789012"] == "result-123456789012"
        assert len(results) == 1

    def test_for_each_account_with_custom_accounts(self, manager, mock_provider):
        """커스텀 계정 목록으로 작업"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        # 커스텀 계정
        custom_accounts = {
            "111111111111": AccountInfo(id="111111111111", name="custom1", roles=["Role1"]),
            "222222222222": AccountInfo(id="222222222222", name="custom2", roles=["Role2"]),
        }

        results = []

        def work_func(account_info, session):
            results.append(account_info.id)
            return account_info.name

        output = manager.for_each_account(work_func, accounts=custom_accounts, role_name="CustomRole")

        assert len(output) == 2
        assert "111111111111" in output
        assert "222222222222" in output

    def test_for_each_account_with_error(self, manager, mock_provider):
        """작업 중 에러 발생"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        def work_func(account_info, session):
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
                "SomeOperation",
            )

        output = manager.for_each_account(work_func)

        # 에러가 발생하면 None 반환
        assert len(output) == 1
        assert output["123456789012"] is None

    def test_for_each_account_no_role(self, manager, mock_provider):
        """역할이 없는 계정 스킵"""
        mock_provider.list_accounts.return_value = {
            "123456789012": AccountInfo(id="123456789012", name="test-account", roles=[]),
        }
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        def work_func(account_info, session):
            return "result"

        output = manager.for_each_account(work_func)

        # 역할이 없으면 스킵
        assert len(output) == 0

    def test_for_each_account_parallel(self, manager, mock_provider):
        """병렬 멀티 계정 작업"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        results = []

        def work_func(account_info, session):
            results.append(account_info.id)
            return f"result-{account_info.id}"

        output = manager.for_each_account_parallel(work_func, max_workers=5)

        assert len(output) == 1
        assert "123456789012" in output
        assert output["123456789012"] == "result-123456789012"

    def test_for_each_account_parallel_multiple_accounts(self, manager, mock_provider):
        """병렬 멀티 계정 작업 - 여러 계정"""
        # 여러 계정 설정
        mock_provider.list_accounts.return_value = {
            "111111111111": AccountInfo(id="111111111111", name="account1", roles=["Role1"]),
            "222222222222": AccountInfo(id="222222222222", name="account2", roles=["Role2"]),
            "333333333333": AccountInfo(id="333333333333", name="account3", roles=["Role3"]),
        }
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        def work_func(account_info, session):
            return f"result-{account_info.id}"

        output = manager.for_each_account_parallel(work_func, max_workers=2)

        assert len(output) == 3
        assert all(key in output for key in ["111111111111", "222222222222", "333333333333"])

    def test_for_each_account_parallel_with_error(self, manager, mock_provider):
        """병렬 작업 중 에러 처리"""
        manager.register_provider(mock_provider)
        manager.set_active_provider(mock_provider)

        def work_func(account_info, session):
            raise ProviderError(
                provider="test",
                operation="test_op",
                message="Test error",
            )

        output = manager.for_each_account_parallel(work_func, max_workers=2)

        assert len(output) == 1
        assert output["123456789012"] is None


# =============================================================================
# 설정 로드 테스트
# =============================================================================


class TestManagerConfigLoading:
    """Manager 설정 로드 테스트"""

    @patch("core.auth.auth.Loader")
    def test_load_config(self, mock_loader_class, manager, mock_parsed_config):
        """설정 파일 로드"""
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_parsed_config
        mock_loader_class.return_value = mock_loader
        manager._config_loader = mock_loader

        config = manager.load_config()

        assert config is mock_parsed_config
        mock_loader.load.assert_called_once()

    @patch("core.auth.auth.Loader")
    def test_list_profiles(self, mock_loader_class, manager, mock_parsed_config):
        """프로파일 목록 조회"""
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_parsed_config
        manager._config_loader = mock_loader

        profiles = manager.list_profiles()

        assert profiles == ["test-profile"]

    @patch("core.auth.auth.Loader")
    def test_list_sso_sessions(self, mock_loader_class, manager, mock_parsed_config):
        """SSO 세션 목록 조회"""
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_parsed_config
        manager._config_loader = mock_loader

        sessions = manager.list_sso_sessions()

        assert sessions == ["test-session"]

    @patch("core.auth.auth.Loader")
    def test_get_profile(self, mock_loader_class, manager, mock_parsed_config):
        """프로파일 정보 조회"""
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_parsed_config
        manager._config_loader = mock_loader

        profile = manager.get_profile("test-profile")

        assert profile is not None
        assert profile.region == "ap-northeast-2"

    @patch("core.auth.auth.Loader")
    def test_get_profile_not_found(self, mock_loader_class, manager, mock_parsed_config):
        """존재하지 않는 프로파일 조회"""
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_parsed_config
        manager._config_loader = mock_loader

        profile = manager.get_profile("non-existent")

        assert profile is None

    @patch("core.auth.auth.Loader")
    def test_get_sso_session(self, mock_loader_class, manager, mock_parsed_config):
        """SSO 세션 정보 조회"""
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_parsed_config
        manager._config_loader = mock_loader

        session = manager.get_sso_session("test-session")

        assert session is not None
        assert session.start_url == "https://test.awsapps.com/start"

    @patch("core.auth.auth.Loader")
    def test_get_sso_session_not_found(self, mock_loader_class, manager, mock_parsed_config):
        """존재하지 않는 SSO 세션 조회"""
        mock_loader = MagicMock()
        mock_loader.load.return_value = mock_parsed_config
        manager._config_loader = mock_loader

        session = manager.get_sso_session("non-existent")

        assert session is None


# =============================================================================
# 리소스 정리 테스트
# =============================================================================


class TestManagerCleanup:
    """Manager 리소스 정리 테스트"""

    def test_close(self, manager, mock_provider, mock_static_provider):
        """리소스 정리"""
        manager.register_provider(mock_provider)
        manager.register_provider(mock_static_provider)
        manager.set_active_provider(mock_provider)

        manager.close()

        # 모든 Provider의 close 호출
        mock_provider.close.assert_called_once()
        mock_static_provider.close.assert_called_once()

        # 상태 초기화
        assert len(manager._providers) == 0
        assert manager._active_provider is None

    def test_close_with_error(self, manager, mock_provider):
        """정리 중 에러 발생 (무시됨)"""
        mock_provider.close.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "Internal error"}},
            "CloseOperation",
        )
        manager.register_provider(mock_provider)

        # 에러 발생해도 정상 종료
        manager.close()

        assert len(manager._providers) == 0

    def test_close_empty_manager(self, manager):
        """Provider 없는 Manager 정리"""
        manager.close()

        assert len(manager._providers) == 0
        assert manager._active_provider is None
