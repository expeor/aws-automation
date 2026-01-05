# tests/test_auth_config_loader.py
"""
core/auth/config/loader.py 테스트

테스트 대상:
- AWSSession: SSO 세션 설정
- AWSProfile: AWS 프로파일 설정
- ParsedConfig: 파싱된 설정 전체
- Loader: AWS 설정 파일 로더
- 모듈 레벨 편의 함수들
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.auth.config.loader import (
    AWSProfile,
    AWSSession,
    Loader,
    ParsedConfig,
    _warn_legacy_sso,
    _warned_legacy_profiles,
    detect_provider_type,
    list_profiles,
    list_sso_sessions,
    load_config,
)
from core.auth.types import ConfigurationError, ProviderType


class TestAWSSession:
    """AWSSession 클래스 테스트"""

    def test_create_valid_session(self):
        """정상적인 SSO 세션 생성"""
        session = AWSSession(
            name="my-sso",
            start_url="https://example.awsapps.com/start",
            region="ap-northeast-2",
            registration_scopes="sso:account:access",
        )
        assert session.name == "my-sso"
        assert session.start_url == "https://example.awsapps.com/start"
        assert session.region == "ap-northeast-2"
        assert session.registration_scopes == "sso:account:access"

    def test_create_session_without_scopes(self):
        """registration_scopes 없이 생성"""
        session = AWSSession(
            name="my-sso",
            start_url="https://example.awsapps.com/start",
            region="ap-northeast-2",
        )
        assert session.registration_scopes is None

    def test_create_session_missing_start_url(self):
        """sso_start_url 누락 시 오류"""
        with pytest.raises(ConfigurationError) as exc_info:
            AWSSession(
                name="my-sso",
                start_url="",
                region="ap-northeast-2",
            )
        assert "sso_start_url" in str(exc_info.value)

    def test_create_session_missing_region(self):
        """sso_region 누락 시 오류"""
        with pytest.raises(ConfigurationError) as exc_info:
            AWSSession(
                name="my-sso",
                start_url="https://example.awsapps.com/start",
                region="",
            )
        assert "sso_region" in str(exc_info.value)


class TestAWSProfile:
    """AWSProfile 클래스 테스트"""

    def test_create_minimal_profile(self):
        """최소 프로파일 생성"""
        profile = AWSProfile(name="test")
        assert profile.name == "test"
        assert profile.region is None
        assert profile.sso_session is None

    def test_create_sso_profile(self):
        """SSO 프로파일 생성"""
        profile = AWSProfile(
            name="dev",
            region="ap-northeast-2",
            sso_session="my-sso",
            sso_account_id="111111111111",
            sso_role_name="AdministratorAccess",
        )
        assert profile.sso_session == "my-sso"
        assert profile.sso_account_id == "111111111111"
        assert profile.sso_role_name == "AdministratorAccess"

    def test_create_assume_role_profile(self):
        """AssumeRole 프로파일 생성"""
        profile = AWSProfile(
            name="prod",
            role_arn="arn:aws:iam::222222222222:role/AdminRole",
            source_profile="dev",
            external_id="external-123",
            mfa_serial="arn:aws:iam::111111111111:mfa/user",
            duration_seconds=3600,
        )
        assert profile.role_arn == "arn:aws:iam::222222222222:role/AdminRole"
        assert profile.source_profile == "dev"
        assert profile.external_id == "external-123"
        assert profile.duration_seconds == 3600

    def test_create_static_credentials_profile(self):
        """Static Credentials 프로파일 생성"""
        profile = AWSProfile(
            name="static",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            aws_session_token="session-token",
        )
        assert profile.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert profile.aws_secret_access_key is not None
        assert profile.aws_session_token == "session-token"

    def test_create_legacy_sso_profile(self):
        """Legacy SSO 프로파일 생성"""
        profile = AWSProfile(
            name="legacy",
            sso_start_url="https://example.awsapps.com/start",
            sso_region="ap-northeast-2",
            sso_account_id="111111111111",
            sso_role_name="PowerUserAccess",
        )
        assert profile.sso_start_url == "https://example.awsapps.com/start"
        assert profile.sso_region == "ap-northeast-2"


class TestParsedConfig:
    """ParsedConfig 클래스 테스트"""

    def test_create_empty_config(self):
        """빈 설정 생성"""
        config = ParsedConfig()
        assert config.sessions == {}
        assert config.profiles == {}
        assert config.default_profile is None

    def test_create_config_with_data(self):
        """데이터가 있는 설정 생성"""
        session = AWSSession(
            name="my-sso",
            start_url="https://example.awsapps.com/start",
            region="ap-northeast-2",
        )
        profile = AWSProfile(name="default")

        config = ParsedConfig(
            sessions={"my-sso": session},
            profiles={"default": profile},
            default_profile="default",
            config_path="/home/user/.aws/config",
            credentials_path="/home/user/.aws/credentials",
        )
        assert "my-sso" in config.sessions
        assert "default" in config.profiles
        assert config.default_profile == "default"


class TestLoader:
    """Loader 클래스 테스트"""

    def test_init_default_paths(self):
        """기본 경로로 초기화"""
        loader = Loader()
        home = Path.home()
        assert loader.config_path == home / ".aws" / "config"
        assert loader.credentials_path == home / ".aws" / "credentials"

    def test_init_custom_paths(self):
        """커스텀 경로로 초기화"""
        loader = Loader(
            config_path="/custom/config",
            credentials_path="/custom/credentials",
        )
        assert loader.config_path == Path("/custom/config")
        assert loader.credentials_path == Path("/custom/credentials")

    def test_load_empty_directory(self):
        """설정 파일이 없는 경우"""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = Loader(
                config_path=f"{tmpdir}/config",
                credentials_path=f"{tmpdir}/credentials",
            )
            config = loader.load()
            assert config.profiles == {}
            assert config.sessions == {}

    def test_load_config_file_with_sso_session(self):
        """SSO 세션이 있는 config 파일 로드"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[sso-session my-sso]
sso_start_url = https://example.awsapps.com/start
sso_region = ap-northeast-2
sso_registration_scopes = sso:account:access

[profile dev]
sso_session = my-sso
sso_account_id = 111111111111
sso_role_name = AdministratorAccess
region = ap-northeast-2
"""
            config_path.write_text(config_content)

            loader = Loader(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            parsed = loader.load()

            assert "my-sso" in parsed.sessions
            assert parsed.sessions["my-sso"].start_url == "https://example.awsapps.com/start"
            assert "dev" in parsed.profiles
            assert parsed.profiles["dev"].sso_session == "my-sso"

    def test_load_config_file_with_default_profile(self):
        """default 프로파일이 있는 config 파일"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[default]
region = us-east-1
output = json
"""
            config_path.write_text(config_content)

            loader = Loader(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            parsed = loader.load()

            assert "default" in parsed.profiles
            assert parsed.default_profile == "default"
            assert parsed.profiles["default"].region == "us-east-1"

    def test_load_credentials_file(self):
        """credentials 파일 로드 및 병합"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            credentials_path = Path(tmpdir) / "credentials"

            config_content = """
[profile dev]
region = ap-northeast-2
"""
            credentials_content = """
[dev]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
"""
            config_path.write_text(config_content)
            credentials_path.write_text(credentials_content)

            loader = Loader(
                config_path=str(config_path),
                credentials_path=str(credentials_path),
            )
            parsed = loader.load()

            profile = parsed.profiles["dev"]
            assert profile.region == "ap-northeast-2"
            assert profile.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
            assert profile.aws_secret_access_key is not None

    def test_load_credentials_only_profile(self):
        """config에 없고 credentials에만 있는 프로파일"""
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_path = Path(tmpdir) / "credentials"
            credentials_content = """
[new-profile]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
aws_session_token = session-token
"""
            credentials_path.write_text(credentials_content)

            loader = Loader(
                config_path=f"{tmpdir}/config",
                credentials_path=str(credentials_path),
            )
            parsed = loader.load()

            assert "new-profile" in parsed.profiles
            profile = parsed.profiles["new-profile"]
            assert profile.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
            assert profile.aws_session_token == "session-token"

    def test_load_assume_role_profile(self):
        """AssumeRole 프로파일 로드"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[profile source]
region = ap-northeast-2

[profile prod]
role_arn = arn:aws:iam::222222222222:role/AdminRole
source_profile = source
external_id = external-123
mfa_serial = arn:aws:iam::111111111111:mfa/user
duration_seconds = 3600
"""
            config_path.write_text(config_content)

            loader = Loader(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            parsed = loader.load()

            profile = parsed.profiles["prod"]
            assert profile.role_arn == "arn:aws:iam::222222222222:role/AdminRole"
            assert profile.source_profile == "source"
            assert profile.external_id == "external-123"
            assert profile.duration_seconds == 3600

    def test_list_profiles(self):
        """프로파일 목록 조회"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[profile dev]
region = ap-northeast-2

[profile prod]
region = us-east-1
"""
            config_path.write_text(config_content)

            loader = Loader(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            profiles = loader.list_profiles()
            assert "dev" in profiles
            assert "prod" in profiles

    def test_list_sso_sessions(self):
        """SSO 세션 목록 조회"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[sso-session sso-1]
sso_start_url = https://example1.awsapps.com/start
sso_region = ap-northeast-2

[sso-session sso-2]
sso_start_url = https://example2.awsapps.com/start
sso_region = us-east-1
"""
            config_path.write_text(config_content)

            loader = Loader(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            sessions = loader.list_sso_sessions()
            assert "sso-1" in sessions
            assert "sso-2" in sessions


class TestDetectProviderType:
    """detect_provider_type 함수 테스트"""

    def test_detect_sso_profile(self):
        """SSO Profile 감지 (sso_session + account/role)"""
        profile = AWSProfile(
            name="dev",
            sso_session="my-sso",
            sso_account_id="111111111111",
            sso_role_name="AdministratorAccess",
        )
        assert Loader.detect_provider_type(profile) == ProviderType.SSO_PROFILE

    def test_detect_sso_session(self):
        """SSO Session 감지 (sso_session만)"""
        profile = AWSProfile(
            name="session-only",
            sso_session="my-sso",
        )
        assert Loader.detect_provider_type(profile) == ProviderType.SSO_SESSION

    def test_detect_legacy_sso(self):
        """Legacy SSO 감지 (sso_start_url 직접 설정)"""
        # 경고 추적 초기화
        _warned_legacy_profiles.clear()

        profile = AWSProfile(
            name="legacy-sso-test",
            sso_start_url="https://example.awsapps.com/start",
            sso_region="ap-northeast-2",
            sso_account_id="111111111111",
            sso_role_name="PowerUserAccess",
        )

        # _warn_legacy_sso 함수 자체를 모킹 (내부에서 Console을 임포트하므로)
        with patch("core.auth.config.loader._warn_legacy_sso"):
            result = Loader.detect_provider_type(profile)

        assert result == ProviderType.SSO_PROFILE

    def test_detect_multi_account_not_supported(self):
        """Multi Account (AssumeRole)는 지원하지 않음 - None 반환"""
        profile = AWSProfile(
            name="prod",
            role_arn="arn:aws:iam::222222222222:role/AdminRole",
            source_profile="dev",
        )
        assert Loader.detect_provider_type(profile) is None

    def test_detect_static_credentials(self):
        """Static Credentials 감지"""
        profile = AWSProfile(
            name="static",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        assert Loader.detect_provider_type(profile) == ProviderType.STATIC_CREDENTIALS

    def test_detect_ambient_not_supported(self):
        """Ambient (아무 설정도 없는 경우)는 지원하지 않음 - None 반환"""
        profile = AWSProfile(
            name="ambient",
            region="ap-northeast-2",
        )
        assert Loader.detect_provider_type(profile) is None


class TestWarnLegacySso:
    """_warn_legacy_sso 함수 테스트"""

    def test_warn_once(self):
        """경고가 한 번만 표시되는지 확인"""
        _warned_legacy_profiles.clear()

        # rich.console.Console을 패치 (함수 내부에서 임포트됨)
        with patch("rich.console.Console") as mock_console:
            _warn_legacy_sso("test-profile-1")
            _warn_legacy_sso("test-profile-1")  # 두 번째 호출

            # 두 번째 호출에서는 경고가 표시되지 않음
            assert "test-profile-1" in _warned_legacy_profiles
            # Console이 한 번만 인스턴스화되어야 함
            assert mock_console.call_count == 1

    def test_warn_different_profiles(self):
        """다른 프로파일에 대해 각각 경고"""
        _warned_legacy_profiles.clear()

        with patch("rich.console.Console"):
            _warn_legacy_sso("profile-a")
            _warn_legacy_sso("profile-b")

            assert "profile-a" in _warned_legacy_profiles
            assert "profile-b" in _warned_legacy_profiles

    def test_warn_fallback_to_logger(self):
        """Rich 없을 때 logger 사용"""
        _warned_legacy_profiles.clear()

        # ImportError를 발생시켜 logger fallback 테스트
        with (
            patch("core.auth.config.loader.logger") as mock_logger,
            patch.dict("sys.modules", {"rich.console": None, "rich.panel": None}),
        ):
            # rich 모듈을 못 찾도록 설정
            import builtins

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name in ("rich.console", "rich.panel"):
                    raise ImportError(f"No module named '{name}'")
                return original_import(name, *args, **kwargs)

            with patch.object(builtins, "__import__", mock_import):
                _warn_legacy_sso("logger-test-profile")
                mock_logger.warning.assert_called_once()


class TestModuleFunctions:
    """모듈 레벨 편의 함수 테스트"""

    def test_load_config_function(self):
        """load_config 편의 함수"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[profile test]
region = ap-northeast-2
"""
            config_path.write_text(config_content)

            parsed = load_config(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            assert "test" in parsed.profiles

    def test_detect_provider_type_function(self):
        """detect_provider_type 편의 함수"""
        profile = AWSProfile(
            name="static",
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="secret",
        )
        result = detect_provider_type(profile)
        assert result == ProviderType.STATIC_CREDENTIALS

    def test_list_profiles_function(self):
        """list_profiles 편의 함수"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[profile alpha]
region = ap-northeast-2

[profile beta]
region = us-east-1
"""
            config_path.write_text(config_content)

            profiles = list_profiles(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            assert "alpha" in profiles
            assert "beta" in profiles

    def test_list_sso_sessions_function(self):
        """list_sso_sessions 편의 함수"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[sso-session main-sso]
sso_start_url = https://main.awsapps.com/start
sso_region = ap-northeast-2
"""
            config_path.write_text(config_content)

            sessions = list_sso_sessions(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            assert "main-sso" in sessions


class TestLoaderEdgeCases:
    """Loader 엣지 케이스 테스트"""

    def test_credentials_without_access_key(self):
        """access_key 없는 credentials 섹션 스킵"""
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_path = Path(tmpdir) / "credentials"
            credentials_content = """
[incomplete]
aws_secret_access_key = secret-only
"""
            credentials_path.write_text(credentials_content)

            loader = Loader(
                config_path=f"{tmpdir}/config",
                credentials_path=str(credentials_path),
            )
            parsed = loader.load()

            # access_key가 없으므로 프로파일이 생성되지 않아야 함
            assert "incomplete" not in parsed.profiles

    def test_credentials_without_secret_key(self):
        """secret_key 없는 credentials 섹션 스킵"""
        with tempfile.TemporaryDirectory() as tmpdir:
            credentials_path = Path(tmpdir) / "credentials"
            credentials_content = """
[incomplete]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
"""
            credentials_path.write_text(credentials_content)

            loader = Loader(
                config_path=f"{tmpdir}/config",
                credentials_path=str(credentials_path),
            )
            parsed = loader.load()

            # secret_key가 없으므로 프로파일이 생성되지 않아야 함
            assert "incomplete" not in parsed.profiles

    def test_default_profile_fallback(self):
        """default 프로파일이 없을 때 첫 번째 프로파일 선택"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[profile alpha]
region = ap-northeast-2

[profile beta]
region = us-east-1
"""
            config_path.write_text(config_content)

            loader = Loader(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            parsed = loader.load()

            # default가 없으면 첫 번째 프로파일이 default
            assert parsed.default_profile in parsed.profiles

    def test_parse_profile_with_credential_process(self):
        """credential_process가 있는 프로파일"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[profile external]
credential_process = /usr/local/bin/get-credentials
region = ap-northeast-2
"""
            config_path.write_text(config_content)

            loader = Loader(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            parsed = loader.load()

            profile = parsed.profiles["external"]
            assert profile.credential_process == "/usr/local/bin/get-credentials"

    def test_multiple_sso_sessions_and_profiles(self):
        """여러 SSO 세션과 프로파일"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[sso-session company-sso]
sso_start_url = https://company.awsapps.com/start
sso_region = ap-northeast-2
sso_registration_scopes = sso:account:access

[sso-session partner-sso]
sso_start_url = https://partner.awsapps.com/start
sso_region = us-west-2

[profile dev-company]
sso_session = company-sso
sso_account_id = 111111111111
sso_role_name = Developer
region = ap-northeast-2

[profile prod-company]
sso_session = company-sso
sso_account_id = 222222222222
sso_role_name = Administrator
region = ap-northeast-2

[profile partner-access]
sso_session = partner-sso
sso_account_id = 333333333333
sso_role_name = ReadOnly
region = us-west-2
"""
            config_path.write_text(config_content)

            loader = Loader(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            parsed = loader.load()

            # SSO 세션 확인
            assert len(parsed.sessions) == 2
            assert "company-sso" in parsed.sessions
            assert "partner-sso" in parsed.sessions
            assert parsed.sessions["company-sso"].registration_scopes == "sso:account:access"

            # 프로파일 확인
            assert len(parsed.profiles) == 3
            assert parsed.profiles["dev-company"].sso_session == "company-sso"
            assert parsed.profiles["partner-access"].sso_session == "partner-sso"

    def test_list_profiles_auto_load(self):
        """config 인자 없이 list_profiles 호출"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[profile test]
region = ap-northeast-2
"""
            config_path.write_text(config_content)

            loader = Loader(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            # config 인자 없이 호출
            profiles = loader.list_profiles()
            assert "test" in profiles

    def test_list_sso_sessions_auto_load(self):
        """config 인자 없이 list_sso_sessions 호출"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config"
            config_content = """
[sso-session test-sso]
sso_start_url = https://test.awsapps.com/start
sso_region = ap-northeast-2
"""
            config_path.write_text(config_content)

            loader = Loader(
                config_path=str(config_path),
                credentials_path=f"{tmpdir}/credentials",
            )
            # config 인자 없이 호출
            sessions = loader.list_sso_sessions()
            assert "test-sso" in sessions
