# tests/test_auth_provider_sso_session.py
"""
core/auth/provider/sso_session.py 테스트

테스트 대상:
- SSOSessionConfig: SSO 세션 설정
- SSOSessionProvider: SSO 세션 기반 인증 Provider
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from core.auth.cache import TokenCache
from core.auth.provider.sso_session import SSOSessionConfig, SSOSessionProvider
from core.auth.types import ProviderType, TokenExpiredError


class TestSSOSessionConfig:
    """SSOSessionConfig 클래스 테스트"""

    def test_create_config_minimal(self):
        """최소 설정으로 생성"""
        config = SSOSessionConfig(
            session_name="my-sso",
            start_url="https://example.awsapps.com/start",
            region="ap-northeast-2",
        )
        assert config.session_name == "my-sso"
        assert config.start_url == "https://example.awsapps.com/start"
        assert config.region == "ap-northeast-2"
        assert config.client_name == "python-auth"
        assert config.client_type == "public"

    def test_create_config_with_custom_client(self):
        """커스텀 클라이언트 설정"""
        config = SSOSessionConfig(
            session_name="custom-sso",
            start_url="https://custom.awsapps.com/start",
            region="us-east-1",
            client_name="custom-client",
            client_type="confidential",
        )
        assert config.client_name == "custom-client"
        assert config.client_type == "confidential"


class TestSSOSessionProvider:
    """SSOSessionProvider 클래스 테스트"""

    @pytest.fixture
    def config(self):
        """테스트용 설정"""
        return SSOSessionConfig(
            session_name="test-sso",
            start_url="https://test.awsapps.com/start",
            region="ap-northeast-2",
        )

    @pytest.fixture
    def mock_boto3_session(self):
        """boto3.Session 모킹"""
        with patch("core.auth.provider.sso_session.boto3.Session") as mock:
            mock_session = MagicMock()
            mock_sso_client = MagicMock()
            mock_sso_oidc_client = MagicMock()
            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": mock_sso_client,
                "sso-oidc": mock_sso_oidc_client,
            }[service]
            mock.return_value = mock_session
            yield {
                "session": mock_session,
                "sso": mock_sso_client,
                "sso_oidc": mock_sso_oidc_client,
            }

    def test_init(self, config, mock_boto3_session):
        """초기화 테스트"""
        provider = SSOSessionProvider(config)
        assert provider._name == "test-sso"
        assert provider._default_region == "ap-northeast-2"
        assert provider._config == config
        assert provider._authenticated is False

    def test_provider_type(self, config, mock_boto3_session):
        """Provider 타입 확인"""
        provider = SSOSessionProvider(config)
        assert provider._provider_type == ProviderType.SSO_SESSION

    def test_supports_multi_account(self, config, mock_boto3_session):
        """멀티 계정 지원 확인"""
        provider = SSOSessionProvider(config)
        assert provider.supports_multi_account() is True

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_authenticate_with_cached_token(self, mock_cache_manager_class, config):
        """캐시된 토큰으로 인증"""
        # 유효한 토큰 캐시 설정
        mock_cache_manager = MagicMock()
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_token_cache = TokenCache(
            access_token="cached-access-token",
            expires_at=future_time,
            client_id="client-id",
            client_secret="client-secret",
            region="ap-northeast-2",
            start_url="https://test.awsapps.com/start",
        )
        mock_cache_manager.load.return_value = mock_token_cache
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch("core.auth.provider.sso_session.boto3.Session"):
            provider = SSOSessionProvider(config)
            provider.authenticate()

        assert provider._authenticated is True
        assert provider._access_token == "cached-access-token"
        # 디바이스 인증 시작되지 않아야 함
        mock_cache_manager.save.assert_not_called()

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_authenticate_with_expired_token_and_refresh(
        self, mock_cache_manager_class, config
    ):
        """만료된 토큰 + 갱신 토큰으로 인증"""
        # 만료된 토큰 캐시 설정 (갱신 토큰 있음)
        mock_cache_manager = MagicMock()
        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_token_cache = TokenCache(
            access_token="expired-access-token",
            expires_at=past_time,
            client_id="client-id",
            client_secret="client-secret",
            refresh_token="refresh-token",
            region="ap-northeast-2",
            start_url="https://test.awsapps.com/start",
        )
        mock_cache_manager.load.return_value = mock_token_cache
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso_oidc = MagicMock()
            # 토큰 갱신 응답
            mock_sso_oidc.create_token.return_value = {
                "accessToken": "refreshed-access-token",
                "expiresIn": 28800,
                "refreshToken": "new-refresh-token",
            }
            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": MagicMock(),
                "sso-oidc": mock_sso_oidc,
            }.get(service, MagicMock())
            mock_session_class.return_value = mock_session

            provider = SSOSessionProvider(config)
            provider.authenticate()

        assert provider._authenticated is True
        assert provider._access_token == "refreshed-access-token"

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_authenticate_force(self, mock_cache_manager_class, config):
        """강제 재인증"""
        mock_cache_manager = MagicMock()
        mock_cache_manager.load.return_value = None
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso_oidc = MagicMock()

            # 클라이언트 등록 응답
            mock_sso_oidc.register_client.return_value = {
                "clientId": "new-client-id",
                "clientSecret": "new-client-secret",
            }

            # 디바이스 인증 시작 응답
            mock_sso_oidc.start_device_authorization.return_value = {
                "deviceCode": "device-code",
                "verificationUriComplete": "https://verify.example.com",
                "interval": 1,
                "expiresIn": 600,
            }

            # 토큰 생성 응답
            mock_sso_oidc.create_token.return_value = {
                "accessToken": "new-access-token",
                "expiresIn": 28800,
            }

            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": MagicMock(),
                "sso-oidc": mock_sso_oidc,
            }.get(service, MagicMock())
            mock_session_class.return_value = mock_session

            with (
                patch("core.auth.provider.sso_session.webbrowser"),
                patch("core.auth.provider.sso_session.sleep"),
            ):
                provider = SSOSessionProvider(config)
                provider.authenticate(force=True)

        mock_cache_manager.delete.assert_called_once()
        assert provider._authenticated is True

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_get_session_success(self, mock_cache_manager_class, config):
        """세션 획득 성공"""
        mock_cache_manager = MagicMock()
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_token_cache = TokenCache(
            access_token="access-token",
            expires_at=future_time,
            client_id="client-id",
            client_secret="client-secret",
            region="ap-northeast-2",
            start_url="https://test.awsapps.com/start",
        )
        mock_cache_manager.load.return_value = mock_token_cache
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso = MagicMock()
            mock_sso.get_role_credentials.return_value = {
                "roleCredentials": {
                    "accessKeyId": "AKIAIOSFODNN7EXAMPLE",
                    "secretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                    "sessionToken": "session-token",
                }
            }
            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": mock_sso,
                "sso-oidc": MagicMock(),
            }.get(service, MagicMock())
            mock_session_class.return_value = mock_session

            provider = SSOSessionProvider(config)
            provider.authenticate()
            session = provider.get_session(
                account_id="111111111111", role_name="AdminRole"
            )

        assert session is not None
        mock_sso.get_role_credentials.assert_called_once_with(
            roleName="AdminRole",
            accountId="111111111111",
            accessToken="access-token",
        )

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_get_session_missing_params(self, mock_cache_manager_class, config):
        """필수 파라미터 누락 시 오류"""
        mock_cache_manager = MagicMock()
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_token_cache = TokenCache(
            access_token="access-token",
            expires_at=future_time,
            client_id="client-id",
            client_secret="client-secret",
            region="ap-northeast-2",
            start_url="https://test.awsapps.com/start",
        )
        mock_cache_manager.load.return_value = mock_token_cache
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch("core.auth.provider.sso_session.boto3.Session"):
            provider = SSOSessionProvider(config)
            provider.authenticate()

            with pytest.raises(ValueError) as exc_info:
                provider.get_session(account_id="111111111111")

            assert "account_id와 role_name은 필수" in str(exc_info.value)

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_list_accounts_success(self, mock_cache_manager_class, config):
        """계정 목록 조회 성공"""
        mock_cache_manager = MagicMock()
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_token_cache = TokenCache(
            access_token="access-token",
            expires_at=future_time,
            client_id="client-id",
            client_secret="client-secret",
            region="ap-northeast-2",
            start_url="https://test.awsapps.com/start",
        )
        mock_cache_manager.load.return_value = mock_token_cache
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso = MagicMock()

            # Paginator 설정
            mock_paginator = MagicMock()
            mock_paginator.paginate.return_value = [
                {
                    "accountList": [
                        {
                            "accountId": "111111111111",
                            "accountName": "Production",
                            "emailAddress": "prod@example.com",
                        },
                        {
                            "accountId": "222222222222",
                            "accountName": "Development",
                            "emailAddress": "dev@example.com",
                        },
                    ]
                }
            ]
            mock_sso.get_paginator.return_value = mock_paginator

            # 역할 목록 조회 응답
            mock_sso.list_account_roles.side_effect = [
                {"roleList": [{"roleName": "AdminRole"}, {"roleName": "ReadOnlyRole"}]},
                {"roleList": [{"roleName": "DeveloperRole"}]},
            ]

            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": mock_sso,
                "sso-oidc": MagicMock(),
            }.get(service, MagicMock())
            mock_session_class.return_value = mock_session

            provider = SSOSessionProvider(config)
            provider.authenticate()
            accounts = provider.list_accounts()

        assert len(accounts) == 2
        assert "111111111111" in accounts
        assert accounts["111111111111"].name == "Production"
        assert "AdminRole" in accounts["111111111111"].roles
        assert "222222222222" in accounts
        assert accounts["222222222222"].name == "Development"

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_refresh_with_refresh_token(self, mock_cache_manager_class, config):
        """갱신 토큰으로 갱신"""
        mock_cache_manager = MagicMock()
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_token_cache = TokenCache(
            access_token="old-access-token",
            expires_at=future_time,
            client_id="client-id",
            client_secret="client-secret",
            refresh_token="refresh-token",
            region="ap-northeast-2",
            start_url="https://test.awsapps.com/start",
        )
        mock_cache_manager.load.return_value = mock_token_cache
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso_oidc = MagicMock()
            mock_sso_oidc.create_token.return_value = {
                "accessToken": "new-access-token",
                "expiresIn": 28800,
                "refreshToken": "new-refresh-token",
            }
            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": MagicMock(),
                "sso-oidc": mock_sso_oidc,
            }.get(service, MagicMock())
            mock_session_class.return_value = mock_session

            provider = SSOSessionProvider(config)
            provider.authenticate()
            provider.refresh()

        assert provider._access_token == "new-access-token"
        mock_sso_oidc.create_token.assert_called()

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_refresh_without_refresh_token(self, mock_cache_manager_class, config):
        """갱신 토큰 없이 갱신 시 디바이스 인증"""
        mock_cache_manager = MagicMock()
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_token_cache = TokenCache(
            access_token="access-token",
            expires_at=future_time,
            client_id="client-id",
            client_secret="client-secret",
            # refresh_token 없음
            region="ap-northeast-2",
            start_url="https://test.awsapps.com/start",
        )
        mock_cache_manager.load.return_value = mock_token_cache
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso_oidc = MagicMock()

            # 클라이언트 등록 응답
            mock_sso_oidc.register_client.return_value = {
                "clientId": "new-client-id",
                "clientSecret": "new-client-secret",
            }

            # 디바이스 인증 시작 응답
            mock_sso_oidc.start_device_authorization.return_value = {
                "deviceCode": "device-code",
                "verificationUriComplete": "https://verify.example.com",
                "interval": 1,
                "expiresIn": 600,
            }

            # 토큰 생성 응답
            mock_sso_oidc.create_token.return_value = {
                "accessToken": "new-access-token",
                "expiresIn": 28800,
            }

            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": MagicMock(),
                "sso-oidc": mock_sso_oidc,
            }.get(service, MagicMock())
            mock_session_class.return_value = mock_session

            with (
                patch("core.auth.provider.sso_session.webbrowser"),
                patch("core.auth.provider.sso_session.sleep"),
            ):
                provider = SSOSessionProvider(config)
                provider.authenticate()
                provider.refresh()

        mock_sso_oidc.register_client.assert_called()


class TestSSOSessionProviderEdgeCases:
    """SSOSessionProvider 엣지 케이스 테스트"""

    @pytest.fixture
    def config(self):
        return SSOSessionConfig(
            session_name="test-sso",
            start_url="https://test.awsapps.com/start",
            region="ap-northeast-2",
        )

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_poll_for_token_timeout(self, mock_cache_manager_class, config):
        """토큰 폴링 타임아웃"""
        mock_cache_manager = MagicMock()
        mock_cache_manager.load.return_value = None
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso_oidc = MagicMock()

            # 클라이언트 등록 응답
            mock_sso_oidc.register_client.return_value = {
                "clientId": "client-id",
                "clientSecret": "client-secret",
            }

            # 디바이스 인증 시작 응답 (짧은 만료 시간)
            mock_sso_oidc.start_device_authorization.return_value = {
                "deviceCode": "device-code",
                "verificationUriComplete": "https://verify.example.com",
                "interval": 1,
                "expiresIn": 2,  # 2초 후 만료
            }

            # 계속 AuthorizationPendingException 발생
            mock_sso_oidc.exceptions.AuthorizationPendingException = type(
                "AuthorizationPendingException", (Exception,), {}
            )
            mock_sso_oidc.create_token.side_effect = (
                mock_sso_oidc.exceptions.AuthorizationPendingException()
            )

            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": MagicMock(),
                "sso-oidc": mock_sso_oidc,
            }.get(service, MagicMock())
            mock_session_class.return_value = mock_session

            with (
                patch("core.auth.provider.sso_session.webbrowser"),
                patch("core.auth.provider.sso_session.sleep"),
            ):
                provider = SSOSessionProvider(config)

                with pytest.raises(TokenExpiredError) as exc_info:
                    provider.authenticate()

                    assert "시간 초과" in str(exc_info.value)

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_poll_for_token_slow_down(self, mock_cache_manager_class, config):
        """토큰 폴링 슬로우다운 처리"""
        mock_cache_manager = MagicMock()
        mock_cache_manager.load.return_value = None
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso_oidc = MagicMock()

            # 클라이언트 등록 응답
            mock_sso_oidc.register_client.return_value = {
                "clientId": "client-id",
                "clientSecret": "client-secret",
            }

            # 디바이스 인증 시작 응답
            mock_sso_oidc.start_device_authorization.return_value = {
                "deviceCode": "device-code",
                "verificationUriComplete": "https://verify.example.com",
                "interval": 1,
                "expiresIn": 10,
            }

            # SlowDown 후 성공
            mock_sso_oidc.exceptions.SlowDownException = type(
                "SlowDownException", (Exception,), {}
            )
            mock_sso_oidc.exceptions.AuthorizationPendingException = type(
                "AuthorizationPendingException", (Exception,), {}
            )
            mock_sso_oidc.create_token.side_effect = [
                mock_sso_oidc.exceptions.SlowDownException(),
                {
                    "accessToken": "access-token",
                    "expiresIn": 28800,
                },
            ]

            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": MagicMock(),
                "sso-oidc": mock_sso_oidc,
            }.get(service, MagicMock())
            mock_session_class.return_value = mock_session

            with (
                patch("core.auth.provider.sso_session.webbrowser"),
                patch("core.auth.provider.sso_session.sleep"),
            ):
                provider = SSOSessionProvider(config)
                provider.authenticate()

        assert provider._authenticated is True

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_get_session_with_cached_credentials(
        self, mock_cache_manager_class, config
    ):
        """캐시된 자격증명으로 세션 획득"""
        mock_cache_manager = MagicMock()
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_token_cache = TokenCache(
            access_token="access-token",
            expires_at=future_time,
            client_id="client-id",
            client_secret="client-secret",
            region="ap-northeast-2",
            start_url="https://test.awsapps.com/start",
        )
        mock_cache_manager.load.return_value = mock_token_cache
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso = MagicMock()
            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": mock_sso,
                "sso-oidc": MagicMock(),
            }.get(service, MagicMock())
            mock_session_class.return_value = mock_session

            provider = SSOSessionProvider(config)
            provider.authenticate()

            # 자격증명 캐시에 미리 저장
            provider._cache_credentials(
                "111111111111",
                "AdminRole",
                {
                    "access_key_id": "CACHED_ACCESS_KEY",
                    "secret_access_key": "CACHED_SECRET_KEY",
                    "session_token": "CACHED_SESSION_TOKEN",
                },
            )

            provider.get_session(account_id="111111111111", role_name="AdminRole")

        # SSO API 호출되지 않아야 함 (캐시 사용)
        mock_sso.get_role_credentials.assert_not_called()

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_list_accounts_with_cached_accounts(self, mock_cache_manager_class, config):
        """캐시된 계정 목록 사용"""
        from core.auth.types import AccountInfo

        mock_cache_manager = MagicMock()
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_token_cache = TokenCache(
            access_token="access-token",
            expires_at=future_time,
            client_id="client-id",
            client_secret="client-secret",
            region="ap-northeast-2",
            start_url="https://test.awsapps.com/start",
        )
        mock_cache_manager.load.return_value = mock_token_cache
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso = MagicMock()
            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": mock_sso,
                "sso-oidc": MagicMock(),
            }.get(service, MagicMock())
            mock_session_class.return_value = mock_session

            provider = SSOSessionProvider(config)
            provider.authenticate()

            # 계정 캐시에 미리 저장
            cached_accounts = {
                "111111111111": AccountInfo(
                    id="111111111111", name="Cached Account", roles=["CachedRole"]
                )
            }
            provider._account_cache.set_all(cached_accounts)

            accounts = provider.list_accounts()

        # SSO API 호출되지 않아야 함 (캐시 사용)
        mock_sso.get_paginator.assert_not_called()
        assert accounts == cached_accounts

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_list_account_roles_error_handling(self, mock_cache_manager_class, config):
        """계정 역할 목록 조회 오류 처리"""
        mock_cache_manager = MagicMock()
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_token_cache = TokenCache(
            access_token="access-token",
            expires_at=future_time,
            client_id="client-id",
            client_secret="client-secret",
            region="ap-northeast-2",
            start_url="https://test.awsapps.com/start",
        )
        mock_cache_manager.load.return_value = mock_token_cache
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso = MagicMock()

            # Paginator 설정
            mock_paginator = MagicMock()
            mock_paginator.paginate.return_value = [
                {
                    "accountList": [
                        {
                            "accountId": "111111111111",
                            "accountName": "Test Account",
                        },
                    ]
                }
            ]
            mock_sso.get_paginator.return_value = mock_paginator

            # 역할 목록 조회 실패
            mock_sso.list_account_roles.side_effect = Exception("Role list error")

            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": mock_sso,
                "sso-oidc": MagicMock(),
            }.get(service, MagicMock())
            mock_session_class.return_value = mock_session

            provider = SSOSessionProvider(config)
            provider.authenticate()
            accounts = provider.list_accounts()

        # 오류가 발생해도 빈 역할 목록으로 계정 반환
        assert "111111111111" in accounts
        assert accounts["111111111111"].roles == []

    @patch("core.auth.provider.sso_session.TokenCacheManager")
    def test_get_aws_config(self, mock_cache_manager_class, config):
        """AWS 설정 정보 반환"""
        mock_cache_manager = MagicMock()
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        mock_token_cache = TokenCache(
            access_token="access-token",
            expires_at=future_time,
            client_id="client-id",
            client_secret="client-secret",
            region="ap-northeast-2",
            start_url="https://test.awsapps.com/start",
        )
        mock_cache_manager.load.return_value = mock_token_cache
        mock_cache_manager_class.return_value = mock_cache_manager

        with patch(
            "core.auth.provider.sso_session.boto3.Session"
        ) as mock_session_class:
            mock_session = MagicMock()
            mock_sso = MagicMock()
            mock_sso.get_role_credentials.return_value = {
                "roleCredentials": {
                    "accessKeyId": "ACCESS_KEY",
                    "secretAccessKey": "SECRET_KEY",
                    "sessionToken": "SESSION_TOKEN",
                }
            }

            mock_new_session = MagicMock()
            mock_new_session.region_name = "ap-northeast-2"
            mock_new_session.get_credentials.return_value = MagicMock(
                access_key="ACCESS_KEY",
                secret_key="SECRET_KEY",
                token="SESSION_TOKEN",
            )

            call_count = [0]

            def session_factory(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return mock_session
                return mock_new_session

            mock_session.client.side_effect = lambda service, **kwargs: {
                "sso": mock_sso,
                "sso-oidc": MagicMock(),
            }.get(service, MagicMock())
            mock_session_class.side_effect = session_factory

            provider = SSOSessionProvider(config)
            provider.authenticate()
            aws_config = provider.get_aws_config(
                account_id="111111111111", role_name="AdminRole"
            )

        assert "region_name" in aws_config
        assert "credentials" in aws_config
