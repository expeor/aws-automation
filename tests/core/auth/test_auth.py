# tests/core/auth/test_auth.py
"""
core/auth 모듈 통합 테스트

이 파일은 core/auth 모듈의 전체 흐름을 테스트합니다:
1. Provider 초기화 및 설정
2. 인증 수행 (with mocked boto3/botocore)
3. Session 생성
4. 멀티 계정 세션 순회
5. 에러 처리 (인증 실패, 토큰 만료 등)

이 테스트는 실제 AWS API를 호출하지 않고 모든 것을 mocking합니다.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from core.auth import (
    SessionIterator,
    SSOSessionConfig,
    SSOSessionProvider,
    StaticCredentialsConfig,
    StaticCredentialsProvider,
    create_manager,
)
from core.auth.cache import TokenCache
from core.auth.types import (
    AccountInfo,
    NotAuthenticatedError,
    ProviderError,
    ProviderType,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_execution_context():
    """Mock ExecutionContext for integration tests"""
    ctx = MagicMock()
    ctx.is_sso_session.return_value = False
    ctx.is_multi_profile.return_value = False
    ctx.profile_name = "test-profile"
    ctx.regions = ["ap-northeast-2"]

    # Mock provider
    ctx.provider = MagicMock()
    mock_session = MagicMock()
    mock_session.region_name = "ap-northeast-2"
    ctx.provider.get_session.return_value = mock_session

    return ctx


@pytest.fixture
def mock_sso_sts_response():
    """Mock STS AssumeRole response for SSO"""
    return {
        "Credentials": {
            "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",
            "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "SessionToken": "FwoGZXIvYXdzEBY...",
            "Expiration": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "AssumedRoleUser": {
            "AssumedRoleId": "AROA3XFRBF535PLBIFPI4:test-session",
            "Arn": "arn:aws:sts::123456789012:assumed-role/AdminRole/test-session",
        },
    }


@pytest.fixture
def mock_sso_accounts():
    """Mock SSO ListAccounts response"""
    return {
        "accountList": [
            {
                "accountId": "111111111111",
                "accountName": "dev-account",
                "emailAddress": "dev@example.com",
            },
            {
                "accountId": "222222222222",
                "accountName": "prod-account",
                "emailAddress": "prod@example.com",
            },
        ]
    }


@pytest.fixture
def mock_sso_roles():
    """Mock SSO ListAccountRoles response"""
    return {
        "roleList": [
            {"roleName": "AdminRole", "accountId": "111111111111"},
            {"roleName": "ReadOnlyRole", "accountId": "111111111111"},
        ]
    }


# =============================================================================
# 통합 테스트: Static Credentials Provider
# =============================================================================


class TestStaticCredentialsIntegration:
    """Static Credentials Provider 통합 테스트"""

    @patch("core.auth.provider.static.boto3.Session")
    def test_static_provider_full_flow(self, mock_boto3_session_class):
        """Static Provider 전체 흐름 테스트"""
        # Mock STS response
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:user/test-user",
            "UserId": "AIDAEXAMPLE",
        }
        mock_session.client.return_value = mock_sts
        mock_session.region_name = "ap-northeast-2"
        mock_boto3_session_class.return_value = mock_session

        # 1. Provider 생성 및 인증
        config = StaticCredentialsConfig(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="ap-northeast-2",
        )
        provider = StaticCredentialsProvider(config)
        provider.authenticate()

        # 2. 인증 상태 확인
        assert provider.is_authenticated() is True
        assert provider.type() == ProviderType.STATIC_CREDENTIALS

        # 3. 계정 목록 조회
        accounts = provider.list_accounts()
        assert len(accounts) == 1
        assert "123456789012" in accounts

        # 4. Session 획득
        session = provider.get_session(region="us-east-1")
        assert session is not None

        # 5. Manager와 통합
        manager = create_manager()
        manager.register_provider(provider)
        manager.set_active_provider(provider)

        assert manager.is_authenticated() is True
        session = manager.get_session()
        assert session is not None

    @patch("core.auth.provider.static.boto3.Session")
    def test_static_provider_authentication_failure(self, mock_boto3_session_class):
        """Static Provider 인증 실패 테스트"""
        # Mock invalid credentials
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "InvalidClientTokenId", "Message": "Invalid access key"}},
            "GetCallerIdentity",
        )
        mock_session.client.return_value = mock_sts
        mock_boto3_session_class.return_value = mock_session

        config = StaticCredentialsConfig(
            access_key_id="INVALID_KEY",
            secret_access_key="invalid_secret",
        )
        provider = StaticCredentialsProvider(config)

        # 인증 실패 예외 발생
        with pytest.raises(ProviderError) as exc_info:
            provider.authenticate()

        assert "유효하지 않은 AWS 자격증명" in str(exc_info.value)

    @patch("core.auth.provider.static.boto3.Session")
    def test_static_provider_expired_token(self, mock_boto3_session_class):
        """Static Provider 만료된 토큰 테스트"""
        # Mock expired token
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "ExpiredToken", "Message": "Token expired"}},
            "GetCallerIdentity",
        )
        mock_session.client.return_value = mock_sts
        mock_boto3_session_class.return_value = mock_session

        config = StaticCredentialsConfig(
            access_key_id="ASIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
            session_token="expired_token",
        )
        provider = StaticCredentialsProvider(config)

        with pytest.raises(ProviderError) as exc_info:
            provider.authenticate()

        assert "임시 자격증명이 만료되었습니다" in str(exc_info.value)


# =============================================================================
# 통합 테스트: SSO Session Provider
# =============================================================================


class TestSSOSessionIntegration:
    """SSO Session Provider 통합 테스트"""

    @patch("core.auth.provider.sso_session.webbrowser.open")
    @patch("core.auth.provider.sso_session.sleep")
    @patch("core.auth.provider.sso_session.boto3.Session")
    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_sso_session_device_authorization_flow(
        self,
        mock_cache_manager_class,
        mock_boto3_session_class,
        mock_sleep,
        mock_webbrowser,
        mock_sso_accounts,
        mock_sso_roles,
        mock_sso_sts_response,
    ):
        """SSO Session 디바이스 인증 흐름 테스트"""
        # Mock cache (no cached token)
        mock_cache_manager = MagicMock()
        mock_cache_manager.load.return_value = None
        mock_cache_manager_class.return_value = mock_cache_manager

        # Mock boto3 clients
        mock_session = MagicMock()
        mock_sso_client = MagicMock()
        mock_sso_oidc_client = MagicMock()
        mock_sts_client = MagicMock()

        def client_factory(service, **kwargs):
            if service == "sso":
                return mock_sso_client
            elif service == "sso-oidc":
                return mock_sso_oidc_client
            elif service == "sts":
                return mock_sts_client
            return MagicMock()

        mock_session.client = client_factory
        mock_boto3_session_class.return_value = mock_session

        # Mock OIDC responses
        mock_sso_oidc_client.register_client.return_value = {
            "clientId": "test-client-id",
            "clientSecret": "test-client-secret",
        }
        mock_sso_oidc_client.start_device_authorization.return_value = {
            "deviceCode": "test-device-code",
            "userCode": "ABCD-1234",
            "verificationUri": "https://device.sso.test/",
            "verificationUriComplete": "https://device.sso.test/?user_code=ABCD-1234",
            "expiresIn": 600,
            "interval": 1,
        }
        mock_sso_oidc_client.create_token.return_value = {
            "accessToken": "test-access-token",
            "tokenType": "Bearer",
            "expiresIn": 28800,
            "refreshToken": "test-refresh-token",
        }

        # Mock SSO responses with paginator
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_sso_accounts]
        mock_sso_client.get_paginator.return_value = mock_paginator
        mock_sso_client.list_account_roles.return_value = mock_sso_roles
        mock_sso_client.get_role_credentials.return_value = {
            "roleCredentials": {
                "accessKeyId": "ASIAIOSFODNN7EXAMPLE",
                "secretAccessKey": "secret",
                "sessionToken": "token",
                "expiration": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp() * 1000),
            }
        }

        # Mock STS response
        mock_sts_client.assume_role.return_value = mock_sso_sts_response

        # 1. Provider 생성 및 인증
        config = SSOSessionConfig(
            session_name="test-sso",
            start_url="https://test.awsapps.com/start",
            region="ap-northeast-2",
        )
        provider = SSOSessionProvider(config)
        provider.authenticate()

        # 2. 인증 상태 확인
        assert provider.is_authenticated() is True
        assert provider.type() == ProviderType.SSO_SESSION

        # 3. 계정 목록 조회
        accounts = provider.list_accounts()
        assert len(accounts) == 2
        assert "111111111111" in accounts
        assert "222222222222" in accounts

        # 4. 특정 계정의 Session 획득
        session = provider.get_session(account_id="111111111111", role_name="AdminRole")
        assert session is not None

    @patch("core.auth.provider.sso_session.boto3.Session")
    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_sso_session_cached_token(self, mock_cache_manager_class, mock_boto3_session_class):
        """SSO Session 캐시된 토큰 사용 테스트"""
        # Mock cached token (needs proper format with datetime string)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        cached_token = TokenCache(
            start_url="https://test.awsapps.com/start",
            region="ap-northeast-2",
            access_token="cached-access-token",
            expires_at=expires_at,
            client_id="test-client-id",
            client_secret="test-client-secret",
        )
        mock_cache_manager = MagicMock()
        mock_cache_manager.load.return_value = cached_token
        mock_cache_manager_class.return_value = mock_cache_manager

        # Mock boto3 clients (minimal mocking needed)
        mock_session = MagicMock()
        mock_sso_client = MagicMock()
        mock_sso_oidc_client = MagicMock()

        def client_factory(service, **kwargs):
            if service == "sso":
                return mock_sso_client
            elif service == "sso-oidc":
                return mock_sso_oidc_client
            return MagicMock()

        mock_session.client = client_factory
        mock_boto3_session_class.return_value = mock_session

        # Provider 생성 및 인증 (캐시 사용)
        config = SSOSessionConfig(
            session_name="test-sso",
            start_url="https://test.awsapps.com/start",
            region="ap-northeast-2",
        )
        provider = SSOSessionProvider(config)
        provider.authenticate()

        # 캐시된 토큰으로 인증 완료
        assert provider.is_authenticated() is True

        # 디바이스 인증 흐름이 실행되지 않음 (cached token 사용)
        mock_sso_oidc_client.register_client.assert_not_called()


# =============================================================================
# 통합 테스트: Manager 멀티 계정 작업
# =============================================================================


class TestManagerMultiAccountIntegration:
    """Manager 멀티 계정 작업 통합 테스트"""

    @patch("core.auth.provider.static.boto3.Session")
    def test_manager_multi_account_sequential(self, mock_boto3_session_class):
        """Manager 순차 멀티 계정 작업"""
        # Mock session for single account (Static credentials only supports single account)
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:user/test-user",
            "UserId": "AIDAEXAMPLE",
        }
        mock_session.client.return_value = mock_sts
        mock_session.region_name = "ap-northeast-2"
        mock_boto3_session_class.return_value = mock_session

        # Setup provider
        config = StaticCredentialsConfig(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
        )
        provider = StaticCredentialsProvider(config)
        provider.authenticate()

        # Manager 설정
        manager = create_manager()
        manager.register_provider(provider)
        manager.set_active_provider(provider)

        # 멀티 계정 작업 수행 (커스텀 계정 목록 전달)
        custom_accounts = {
            "123456789012": AccountInfo(
                id="123456789012",
                name="test-account",
                roles=["AdminRole"],  # 역할 추가
            )
        }

        results = []

        def work_func(account_info, session):
            results.append(account_info.id)
            return f"processed-{account_info.id}"

        # 순차 실행
        output = manager.for_each_account(work_func, accounts=custom_accounts, role_name="AdminRole")

        assert len(output) == 1
        assert "123456789012" in output
        assert len(results) == 1

    @patch("core.auth.provider.static.boto3.Session")
    def test_manager_multi_account_parallel(self, mock_boto3_session_class):
        """Manager 병렬 멀티 계정 작업"""
        # Similar setup as sequential test
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {
            "Account": "123456789012",
            "Arn": "arn:aws:iam::123456789012:user/test-user",
            "UserId": "AIDAEXAMPLE",
        }
        mock_session.client.return_value = mock_sts
        mock_session.region_name = "ap-northeast-2"
        mock_boto3_session_class.return_value = mock_session

        # Provider 생성
        config = StaticCredentialsConfig(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
        )
        provider = StaticCredentialsProvider(config)
        provider.authenticate()

        # Manager 설정
        manager = create_manager()
        manager.register_provider(provider)
        manager.set_active_provider(provider)

        # 커스텀 계정 목록 (역할 포함)
        custom_accounts = {
            "123456789012": AccountInfo(
                id="123456789012",
                name="test-account",
                roles=["AdminRole"],
            )
        }

        # 병렬 작업 수행
        results = []

        def work_func(account_info, session):
            results.append(account_info.id)
            return f"processed-{account_info.id}"

        output = manager.for_each_account_parallel(
            work_func, accounts=custom_accounts, role_name="AdminRole", max_workers=2
        )

        assert len(output) == 1
        assert len(results) == 1


# =============================================================================
# 통합 테스트: SessionIterator
# =============================================================================


class TestSessionIteratorIntegration:
    """SessionIterator 통합 테스트"""

    @patch("core.auth.session.get_session")
    def test_session_iterator_single_profile(self, mock_get_session, mock_execution_context):
        """SessionIterator 단일 프로파일 테스트"""
        # Mock get_session
        mock_session = MagicMock()
        mock_session.region_name = "ap-northeast-2"
        mock_get_session.return_value = mock_session

        # SessionIterator 사용
        with SessionIterator(mock_execution_context) as sessions:
            session_list = list(sessions)

            # 1개 리전이므로 1개 세션
            assert len(session_list) == 1
            session, identifier, region = session_list[0]
            assert identifier == "test-profile"
            assert region == "ap-northeast-2"

        # 결과 확인
        assert sessions.success_count == 1
        assert sessions.error_count == 0
        assert sessions.has_any_success() is True

    @patch("core.auth.session.get_session")
    def test_session_iterator_with_errors(self, mock_get_session, mock_execution_context):
        """SessionIterator 에러 처리 테스트"""
        # Mock get_session to fail
        mock_get_session.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}},
            "GetSession",
        )

        # SessionIterator 사용
        with SessionIterator(mock_execution_context) as sessions:
            session_list = list(sessions)

            # 에러 발생으로 세션 없음
            assert len(session_list) == 0

        # 에러 상태 확인
        assert sessions.success_count == 0
        assert sessions.error_count == 1
        assert sessions.has_failures_only() is True

        # 에러 요약
        error_summary = sessions.get_error_summary()
        assert "총 1개 세션 생성 실패" in error_summary


# =============================================================================
# 통합 테스트: 에러 핸들링
# =============================================================================


class TestErrorHandlingIntegration:
    """에러 핸들링 통합 테스트"""

    def test_not_authenticated_error(self):
        """인증되지 않은 상태에서 작업 시도"""
        manager = create_manager()

        # 활성 Provider 없음
        with pytest.raises(NotAuthenticatedError):
            manager.get_session()

        with pytest.raises(NotAuthenticatedError):
            manager.list_accounts()

    @patch("core.auth.provider.static.boto3.Session")
    def test_provider_error_propagation(self, mock_boto3_session_class):
        """Provider 에러 전파 테스트"""
        # Mock AWS error
        mock_session = MagicMock()
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "Service unavailable"}},
            "GetCallerIdentity",
        )
        mock_session.client.return_value = mock_sts
        mock_boto3_session_class.return_value = mock_session

        config = StaticCredentialsConfig(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="secret",
        )
        provider = StaticCredentialsProvider(config)

        # 에러 발생
        with pytest.raises(ProviderError) as exc_info:
            provider.authenticate()

        error = exc_info.value
        assert error.provider == "static-credentials"
        assert error.operation == "authenticate"
        assert error.cause is not None
