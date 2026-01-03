"""
core/config.py - 중앙 집중식 설정 관리

애플리케이션 전체에서 사용되는 설정 값을 한 곳에서 관리합니다.
하드코딩을 제거하고 일관성을 유지하며, 환경 변수 오버라이드를 지원합니다.

주요 컴포넌트:
    - Settings: 불변 설정 클래스 (싱글톤 패턴)
    - 경로 헬퍼: get_project_root(), get_plugins_path()
    - 환경변수 헬퍼: get_default_profile(), get_default_region()
    - 버전 관리: get_version()
    - 메타데이터 검증: validate_tool_metadata()

Usage:
    # 설정 값 접근
    from core.config import settings

    region = settings.DEFAULT_REGION        # "ap-northeast-2"
    timeout = settings.API_TIMEOUT          # 30
    retry = settings.API_RETRY_COUNT        # 3

    # 환경 변수 기반 값
    from core.config import get_default_profile, get_default_region

    profile = get_default_profile()         # AWS_PROFILE 또는 None
    region = get_default_region()           # AWS_REGION 또는 기본값

    # 프로젝트 경로
    from core.config import get_project_root, get_plugins_path

    root = get_project_root()               # Path(".../aws-automation-toolkit")
    plugins = get_plugins_path()            # Path(".../aws-automation-toolkit/plugins")

    # 메타데이터 검증
    from core.config import validate_tool_metadata

    errors = validate_tool_metadata({"name": "test", "permission": "read"})
    # errors = ["필수 필드 누락: description"]

환경 변수:
    AWS_PROFILE: 기본 AWS 프로파일
    AWS_DEFAULT_PROFILE: 기본 AWS 프로파일 (AWS_PROFILE 우선)
    AWS_REGION: 기본 AWS 리전
    AWS_DEFAULT_REGION: 기본 AWS 리전 (AWS_REGION 우선)
    LOG_LEVEL: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
    LOG_FORMAT: 로그 포맷 문자열
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional

# =============================================================================
# 프로젝트 경로 설정
# =============================================================================


def get_project_root() -> Path:
    """프로젝트 루트 경로 반환

    여러 곳에서 Path(__file__).parent.parent... 하던 것을 중앙화
    """
    return Path(__file__).resolve().parent.parent


def get_plugins_path() -> Path:
    """플러그인 폴더 경로 반환"""
    return get_project_root() / "plugins"


def get_version_file() -> Path:
    """version.txt 파일 경로 반환"""
    return get_project_root() / "version.txt"


# =============================================================================
# 애플리케이션 설정
# =============================================================================


@dataclass(frozen=True)
class Settings:
    """불변 설정 클래스

    모든 설정 값은 frozen=True로 불변성을 보장합니다.
    """

    # AWS 기본 설정
    DEFAULT_REGION: str = "ap-northeast-2"
    DEFAULT_REGIONS: tuple = ("ap-northeast-2", "us-east-1", "eu-west-1")

    # API 호출 설정
    API_TIMEOUT: int = 30  # 초
    API_RETRY_COUNT: int = 3
    API_RETRY_DELAY: float = 1.0  # 초

    # 세션 설정
    SESSION_DURATION_SECONDS: int = 3600  # 1시간
    TOKEN_REFRESH_MARGIN: int = 300  # 만료 5분 전 갱신

    # 캐시 설정
    CACHE_TTL_SECONDS: int = 300  # 5분
    DISCOVERY_CACHE_TTL: int = 600  # 10분

    # 출력 설정
    MAX_DISPLAY_ERRORS: int = 5
    MAX_LOG_LINE_LENGTH: int = 2000

    # 플러그인 설정
    PLUGIN_EXCLUDE_DIRS: FrozenSet[str] = frozenset(
        {"__pycache__", "_templates", "_legacy", ".git"}
    )

    # 분석 카테고리 우선순위
    ANALYSIS_CATEGORIES: tuple = (
        "cost",  # 비용 최적화
        "security",  # 보안 취약점
        "inventory",  # 리소스 인벤토리
        "network",  # 네트워크 분석
        "compliance",  # 규정준수
        "log",  # 로그 분석
        "report",  # 정기 보고서
    )

    # =========================================================================
    # 보안 감사 설정
    # =========================================================================

    # TLS 최소 버전 (TLSv1.2, TLSv1.3)
    # - 기업 정책에 따라 조정 가능
    # - PCI-DSS: TLSv1.2 이상 필수
    # - 최신 보안 권장: TLSv1.3
    SECURITY_MIN_TLS_VERSION: str = "TLSv1.2"

    # 취약 프로토콜 목록
    # - SSLv3: POODLE 취약점
    # - TLSv1/1.1: 2020년 deprecated (RFC 8996)
    SECURITY_VULNERABLE_PROTOCOLS: FrozenSet[str] = frozenset(
        {"SSLv3", "TLSv1", "TLSv1.1"}
    )

    # 안전한 프로토콜 목록
    SECURITY_SECURE_PROTOCOLS: FrozenSet[str] = frozenset({"TLSv1.2", "TLSv1.3"})

    # 취약한 암호화 스위트 패턴
    # - RC4: 스트림 암호 취약 (2015 금지)
    # - DES/3DES: 블록 크기 취약 (Sweet32)
    # - MD5: 충돌 공격 취약
    # - NULL: 암호화 없음
    # - EXPORT: 약한 키 길이
    # - anon: 인증 없음 (MITM 취약)
    SECURITY_WEAK_CIPHER_PATTERNS: FrozenSet[str] = frozenset(
        {"RC4", "DES", "3DES", "MD5", "NULL", "EXPORT", "anon"}
    )

    # 인증서 만료 경고 임계값 (일)
    SECURITY_CERT_EXPIRY_CRITICAL: int = 7  # 7일 이내 = CRITICAL
    SECURITY_CERT_EXPIRY_HIGH: int = 30  # 30일 이내 = HIGH
    SECURITY_CERT_EXPIRY_MEDIUM: int = 90  # 90일 이내 = MEDIUM

    # WAF 필수 여부 (internet-facing ALB)
    SECURITY_WAF_REQUIRED_FOR_PUBLIC: bool = True

    # 액세스 로그 필수 여부
    SECURITY_ACCESS_LOG_REQUIRED: bool = True

    # 삭제 보호 필수 패턴 (정규식)
    # - 이 패턴에 매칭되는 이름의 리소스는 삭제 보호 필수
    SECURITY_DELETION_PROTECTION_PATTERNS: tuple = (
        "prod",
        "prd",
        "production",
        "live",
        "main",
        "master",
    )


# 싱글톤 설정 인스턴스
settings = Settings()


# =============================================================================
# 환경 변수 헬퍼 함수
# =============================================================================


def get_default_profile() -> Optional[str]:
    """기본 AWS 프로파일 반환

    우선순위:
    1. AWS_PROFILE 환경변수
    2. AWS_DEFAULT_PROFILE 환경변수
    3. None (boto3가 default 프로파일 사용)

    Returns:
        프로파일 이름 또는 None
    """
    return os.environ.get("AWS_PROFILE") or os.environ.get("AWS_DEFAULT_PROFILE")


def get_default_region() -> str:
    """기본 AWS 리전 반환

    우선순위:
    1. AWS_REGION 환경변수
    2. AWS_DEFAULT_REGION 환경변수
    3. settings.DEFAULT_REGION

    Returns:
        리전 이름
    """
    return (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or settings.DEFAULT_REGION
    )


def get_env_bool(key: str, default: bool = False) -> bool:
    """환경변수를 bool로 변환

    Args:
        key: 환경변수 키
        default: 기본값

    Returns:
        True/False
    """
    value = os.environ.get(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    return default


def get_env_int(key: str, default: int) -> int:
    """환경변수를 int로 변환

    Args:
        key: 환경변수 키
        default: 기본값

    Returns:
        정수값
    """
    value = os.environ.get(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


# =============================================================================
# 버전 관리
# =============================================================================


@lru_cache(maxsize=1)
def get_version() -> str:
    """애플리케이션 버전 반환 (캐싱됨)

    version.txt 파일에서 버전을 읽어옵니다.
    파일이 없으면 importlib.metadata를 사용합니다.

    Returns:
        버전 문자열 (예: "1.0.0")
    """
    version_file = get_version_file()

    if version_file.exists():
        try:
            return version_file.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # Fallback: importlib.metadata
    try:
        from importlib.metadata import version as pkg_version

        return pkg_version("aa")
    except Exception:
        return "0.0.1"


# =============================================================================
# 로깅 설정
# =============================================================================


@dataclass
class LogConfig:
    """로깅 설정"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def from_env(cls) -> "LogConfig":
        """환경변수에서 로깅 설정 로드"""
        return cls(
            level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            format=os.environ.get("LOG_FORMAT", cls.format),
            date_format=os.environ.get("LOG_DATE_FORMAT", cls.date_format),
        )


# =============================================================================
# 플러그인 메타데이터 스키마
# =============================================================================

# 도구 메타데이터 필수 필드
TOOL_REQUIRED_FIELDS: FrozenSet[str] = frozenset(
    {
        "name",
        "description",
        "permission",
    }
)

# 유효한 permission 값
VALID_PERMISSIONS: FrozenSet[str] = frozenset(
    {
        "read",
        "write",
        "delete",
    }
)

# 유효한 area 값
VALID_AREAS: FrozenSet[str] = frozenset(
    {
        "security",
        "cost",
        "performance",
        "fault_tolerance",
        "service_limits",
        "operational",
        "inventory",
        "network",
        "log",
    }
)


def validate_tool_metadata(tool: Dict) -> List[str]:
    """도구 메타데이터 유효성 검사

    Args:
        tool: 도구 메타데이터 딕셔너리

    Returns:
        오류 메시지 리스트 (비어있으면 유효)
    """
    errors = []

    # 필수 필드 검사
    for fld in TOOL_REQUIRED_FIELDS:
        if fld not in tool:
            errors.append(f"필수 필드 누락: {fld}")
        elif not tool[fld]:
            errors.append(f"필드가 비어있음: {fld}")

    # permission 값 검사
    permission = tool.get("permission")
    if permission and permission not in VALID_PERMISSIONS:
        errors.append(f"유효하지 않은 permission: {permission}")

    # area 값 검사 (선택적 필드)
    area = tool.get("area")
    if area and area not in VALID_AREAS:
        errors.append(f"유효하지 않은 area: {area}")

    # 실행 제약 조건 필드 검사 (bool 타입)
    for bool_field in ("single_region_only", "single_account_only"):
        value = tool.get(bool_field)
        if value is not None and not isinstance(value, bool):
            errors.append(f"{bool_field}는 bool 타입이어야 함: {type(value).__name__}")

    return errors
