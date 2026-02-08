# core/auth/config/loader.py
"""
core/auth/config/loader.py - AWS 설정 파일 로더

~/.aws/config와 ~/.aws/credentials 파일을 파싱하여 SSO 세션, 프로파일 정보를
추출하고 각 프로파일의 Provider 타입을 자동 감지합니다.

주요 기능:
    - ~/.aws/config 파일 파싱 (sso-session, profile 섹션)
    - ~/.aws/credentials 파일 파싱 및 프로파일 병합
    - Provider 타입 자동 감지 (SSO_SESSION, SSO_PROFILE, STATIC_CREDENTIALS)
    - Legacy SSO 설정 사용 시 마이그레이션 경고 표시
"""

import configparser
import logging
from dataclasses import dataclass, field
from pathlib import Path

from ..types import ConfigurationError, ProviderType

logger = logging.getLogger(__name__)

# Legacy SSO 경고를 이미 표시한 프로파일 추적 (중복 경고 방지)
_warned_legacy_profiles: set[str] = set()


def _warn_legacy_sso(profile_name: str) -> None:
    """Legacy SSO 설정 사용 시 경고 메시지 표시

    Args:
        profile_name: 프로파일 이름
    """
    if profile_name in _warned_legacy_profiles:
        return

    _warned_legacy_profiles.add(profile_name)

    try:
        from rich.console import Console
        from rich.panel import Panel

        console = Console(stderr=True)

        migration_guide = f"""[yellow]프로파일 '{profile_name}'이 Legacy SSO 설정을 사용하고 있습니다.[/yellow]

[bold red]⚠️  Legacy SSO는 더 이상 권장되지 않습니다.[/bold red]

[cyan]AWS 권장 방식 (sso-session)으로 마이그레이션하세요:[/cyan]

[dim]# ~/.aws/config 수정 방법[/dim]

[green]# 1. SSO Session 블록 추가[/green]
[sso-session my-sso]
sso_start_url = https://your-sso-portal.awsapps.com/start
sso_region = ap-northeast-2
sso_registration_scopes = sso:account:access

[green]# 2. 프로파일에서 sso_session 참조[/green]
[profile {profile_name}]
sso_session = my-sso
sso_account_id = 123456789012
sso_role_name = YourRoleName
region = ap-northeast-2

[dim]자세한 내용: https://docs.aws.amazon.com/cli/latest/userguide/sso-configure-profile-token.html[/dim]"""

        console.print()
        console.print(
            Panel(
                migration_guide,
                title="[bold yellow]🔄 SSO 설정 마이그레이션 권장[/bold yellow]",
                border_style="yellow",
            )
        )
        console.print()

    except ImportError:
        # Rich가 없으면 기본 로깅 사용
        logger.warning(
            f"⚠️  프로파일 '{profile_name}'이 Legacy SSO 설정을 사용 중입니다. "
            f"sso-session 방식으로 마이그레이션을 권장합니다. "
            f"https://docs.aws.amazon.com/cli/latest/userguide/sso-configure-profile-token.html"
        )


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class AWSSession:
    """SSO 세션 설정

    ~/.aws/config의 [sso-session xxx] 섹션을 나타냅니다.

    Attributes:
        name: 세션 이름
        start_url: SSO 시작 URL
        region: SSO 리전
        registration_scopes: 등록 스코프 (옵션)
    """

    name: str
    start_url: str
    region: str
    registration_scopes: str | None = None

    def __post_init__(self):
        """필수 필드(start_url, region) 유효성을 검사합니다.

        Raises:
            ConfigurationError: start_url 또는 region이 비어있는 경우
        """
        if not self.start_url:
            raise ConfigurationError(
                f"SSO 세션 '{self.name}'에 sso_start_url이 필요합니다",
                config_key="sso_start_url",
            )
        if not self.region:
            raise ConfigurationError(
                f"SSO 세션 '{self.name}'에 sso_region이 필요합니다",
                config_key="sso_region",
            )


@dataclass
class AWSProfile:
    """AWS 프로파일 설정

    ~/.aws/config의 [profile xxx] 섹션을 나타냅니다.

    Attributes:
        name: 프로파일 이름
        region: 기본 리전
        output: 출력 형식
        sso_session: 연결된 SSO 세션 이름
        sso_account_id: SSO 계정 ID
        sso_role_name: SSO 역할 이름
        role_arn: AssumeRole에 사용할 역할 ARN
        source_profile: 소스 프로파일 (AssumeRole용)
        external_id: 외부 ID (AssumeRole용)
        mfa_serial: MFA 디바이스 시리얼
        duration_seconds: 세션 유효 시간
        credential_process: 외부 자격증명 프로세스
    """

    name: str
    region: str | None = None
    output: str | None = None
    # SSO 관련 (권장: sso_session 사용)
    sso_session: str | None = None
    sso_account_id: str | None = None
    sso_role_name: str | None = None
    # ⚠️ 구버전 SSO (Deprecated: sso_session 없이 직접 설정)
    sso_start_url: str | None = None
    sso_region: str | None = None
    # AssumeRole 관련
    role_arn: str | None = None
    source_profile: str | None = None
    external_id: str | None = None
    mfa_serial: str | None = None
    duration_seconds: int | None = None
    # 기타
    credential_process: str | None = None
    # Credentials (from ~/.aws/credentials)
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None


@dataclass
class ParsedConfig:
    """파싱된 AWS 설정 전체

    Attributes:
        sessions: SSO 세션 목록 {name: AWSSession}
        profiles: 프로파일 목록 {name: AWSProfile}
        default_profile: 기본 프로파일 이름
        config_path: config 파일 경로
        credentials_path: credentials 파일 경로
    """

    sessions: dict[str, AWSSession] = field(default_factory=dict)
    profiles: dict[str, AWSProfile] = field(default_factory=dict)
    default_profile: str | None = None
    config_path: str | None = None
    credentials_path: str | None = None


# =============================================================================
# Loader Class
# =============================================================================


class Loader:
    """AWS 설정 파일 로더

    Example:
        loader = Loader()
        config = loader.load()

        # 프로파일 목록
        profiles = loader.list_profiles(config)

        # Provider 타입 감지
        provider_type = Loader.detect_provider_type(config.profiles["my-profile"])
    """

    def __init__(
        self,
        config_path: str | None = None,
        credentials_path: str | None = None,
    ):
        """Loader 초기화

        Args:
            config_path: config 파일 경로 (기본: ~/.aws/config)
            credentials_path: credentials 파일 경로 (기본: ~/.aws/credentials)
        """
        home = Path.home()
        aws_dir = home / ".aws"

        self.config_path = Path(config_path) if config_path else aws_dir / "config"
        self.credentials_path = Path(credentials_path) if credentials_path else aws_dir / "credentials"

    def load(self) -> ParsedConfig:
        """AWS 설정 파일들을 파싱

        Returns:
            ParsedConfig 객체

        Raises:
            ConfigurationError: 설정 파일 파싱 실패 시
        """
        result = ParsedConfig(
            config_path=str(self.config_path),
            credentials_path=str(self.credentials_path),
        )

        # ~/.aws/config 파싱
        if self.config_path.exists():
            self._parse_config_file(result)

        # ~/.aws/credentials 파싱 및 병합
        if self.credentials_path.exists():
            self._parse_credentials_file(result)

        # default 프로파일 설정
        if "default" in result.profiles:
            result.default_profile = "default"
        elif result.profiles:
            result.default_profile = next(iter(result.profiles.keys()))

        return result

    def _parse_config_file(self, result: ParsedConfig) -> None:
        """~/.aws/config 파일을 파싱하여 세션과 프로파일 정보를 추출합니다.

        Args:
            result: 파싱 결과를 저장할 ParsedConfig 객체 (in-place 수정)

        Raises:
            ConfigurationError: 설정 파일 파싱 실패 시
        """
        config = configparser.ConfigParser()
        config.optionxform = str  # type: ignore[assignment,method-assign]  # 대소문자 유지

        try:
            config.read(str(self.config_path), encoding="utf-8")
        except Exception as e:
            raise ConfigurationError(f"config 파일 파싱 실패: {self.config_path}", cause=e) from e

        for section in config.sections():
            try:
                if section.startswith("sso-session "):
                    # SSO 세션 파싱
                    session_name = section.split("sso-session ", 1)[1].strip()
                    session = AWSSession(
                        name=session_name,
                        start_url=config.get(section, "sso_start_url", fallback=""),
                        region=config.get(section, "sso_region", fallback=""),
                        registration_scopes=config.get(section, "sso_registration_scopes", fallback=None),
                    )
                    result.sessions[session_name] = session

                elif section.startswith("profile ") or section == "default":
                    # 프로파일 파싱
                    profile_name = (
                        section.split("profile ", 1)[1].strip() if section.startswith("profile ") else "default"
                    )
                    profile = self._parse_profile_section(config, section, profile_name)
                    result.profiles[profile_name] = profile

            except ConfigurationError:
                raise
            except Exception as e:
                # 개별 섹션 파싱 오류는 경고만 하고 계속 진행
                logger.debug("Failed to parse section %s: %s", section, e)

    def _parse_profile_section(
        self,
        config: configparser.ConfigParser,
        section: str,
        profile_name: str,
    ) -> AWSProfile:
        """단일 프로파일 섹션을 파싱하여 AWSProfile 객체를 생성합니다.

        Args:
            config: configparser 인스턴스
            section: 섹션 이름 (예: "profile my-profile")
            profile_name: 프로파일 이름 (예: "my-profile")

        Returns:
            AWSProfile 객체
        """
        duration = config.get(section, "duration_seconds", fallback=None)

        return AWSProfile(
            name=profile_name,
            region=config.get(section, "region", fallback=None),
            output=config.get(section, "output", fallback=None),
            sso_session=config.get(section, "sso_session", fallback=None),
            sso_account_id=config.get(section, "sso_account_id", fallback=None),
            sso_role_name=config.get(section, "sso_role_name", fallback=None),
            sso_start_url=config.get(section, "sso_start_url", fallback=None),
            sso_region=config.get(section, "sso_region", fallback=None),
            role_arn=config.get(section, "role_arn", fallback=None),
            source_profile=config.get(section, "source_profile", fallback=None),
            external_id=config.get(section, "external_id", fallback=None),
            mfa_serial=config.get(section, "mfa_serial", fallback=None),
            duration_seconds=int(duration) if duration else None,
            credential_process=config.get(section, "credential_process", fallback=None),
        )

    def _parse_credentials_file(self, result: ParsedConfig) -> None:
        """~/.aws/credentials 파일을 파싱하여 기존 프로파일에 자격증명을 병합합니다.

        config 파일에 이미 존재하는 프로파일에는 credentials를 병합하고,
        존재하지 않는 프로파일은 새로 생성합니다.

        Args:
            result: 파싱 결과를 저장할 ParsedConfig 객체 (in-place 수정)

        Raises:
            ConfigurationError: credentials 파일 파싱 실패 시
        """
        config = configparser.ConfigParser()
        config.optionxform = str  # type: ignore[assignment,method-assign]  # 대소문자 유지

        try:
            config.read(str(self.credentials_path), encoding="utf-8")
        except Exception as e:
            raise ConfigurationError(f"credentials 파일 파싱 실패: {self.credentials_path}", cause=e) from e

        for section in config.sections():
            profile_name = section

            access_key = config.get(section, "aws_access_key_id", fallback=None)
            secret_key = config.get(section, "aws_secret_access_key", fallback=None)
            session_token = config.get(section, "aws_session_token", fallback=None)

            if not (access_key and secret_key):
                continue

            if profile_name in result.profiles:
                # 기존 프로파일에 credentials 병합
                profile = result.profiles[profile_name]
                profile.aws_access_key_id = access_key
                profile.aws_secret_access_key = secret_key
                profile.aws_session_token = session_token
            else:
                # 새 프로파일 생성
                result.profiles[profile_name] = AWSProfile(
                    name=profile_name,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    aws_session_token=session_token,
                )

    @staticmethod
    def detect_provider_type(profile: AWSProfile) -> ProviderType | None:
        """프로파일에서 Provider 타입을 감지

        Args:
            profile: AWSProfile 객체

        Returns:
            ProviderType enum 값 또는 None (지원하지 않는 타입)
        """
        # SSO Session 기반 (최신 권장 방식)
        if profile.sso_session:
            if profile.sso_account_id and profile.sso_role_name:
                return ProviderType.SSO_PROFILE
            return ProviderType.SSO_SESSION

        # Legacy SSO (sso_session 없이 직접 설정) - 경고 표시
        if profile.sso_start_url and profile.sso_region:
            _warn_legacy_sso(profile.name)
            return ProviderType.SSO_PROFILE

        # Static Credentials
        if profile.aws_access_key_id and profile.aws_secret_access_key:
            return ProviderType.STATIC_CREDENTIALS

        # AssumeRole 및 Ambient는 지원하지 않음
        return None

    def list_profiles(self, config: ParsedConfig | None = None) -> list[str]:
        """프로파일 이름 목록 반환

        Args:
            config: ParsedConfig (없으면 새로 로드)

        Returns:
            프로파일 이름 리스트
        """
        if config is None:
            config = self.load()
        return list(config.profiles.keys())

    def list_sso_sessions(self, config: ParsedConfig | None = None) -> list[str]:
        """SSO 세션 이름 목록 반환

        Args:
            config: ParsedConfig (없으면 새로 로드)

        Returns:
            SSO 세션 이름 리스트
        """
        if config is None:
            config = self.load()
        return list(config.sessions.keys())


# =============================================================================
# Module-level Functions (편의용)
# =============================================================================


def load_config(
    config_path: str | None = None,
    credentials_path: str | None = None,
) -> ParsedConfig:
    """AWS 설정 파일 로드 (편의 함수)

    Args:
        config_path: config 파일 경로 (기본: ~/.aws/config)
        credentials_path: credentials 파일 경로 (기본: ~/.aws/credentials)

    Returns:
        ParsedConfig 객체
    """
    loader = Loader(config_path, credentials_path)
    return loader.load()


def detect_provider_type(profile: AWSProfile) -> ProviderType | None:
    """프로파일에서 Provider 타입을 감지합니다 (편의 함수).

    Args:
        profile: AWSProfile 객체

    Returns:
        ProviderType enum 값 또는 None (지원하지 않는 타입)
    """
    return Loader.detect_provider_type(profile)


def list_profiles(
    config_path: str | None = None,
    credentials_path: str | None = None,
) -> list[str]:
    """프로파일 이름 목록을 반환합니다 (편의 함수).

    Args:
        config_path: config 파일 경로 (기본: ~/.aws/config)
        credentials_path: credentials 파일 경로 (기본: ~/.aws/credentials)

    Returns:
        프로파일 이름 리스트
    """
    loader = Loader(config_path, credentials_path)
    return loader.list_profiles()


def list_sso_sessions(
    config_path: str | None = None,
    credentials_path: str | None = None,
) -> list[str]:
    """SSO 세션 이름 목록을 반환합니다 (편의 함수).

    Args:
        config_path: config 파일 경로 (기본: ~/.aws/config)
        credentials_path: credentials 파일 경로 (기본: ~/.aws/credentials)

    Returns:
        SSO 세션 이름 리스트
    """
    loader = Loader(config_path, credentials_path)
    return loader.list_sso_sessions()
