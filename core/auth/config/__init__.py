# internal/auth/config/__init__.py
"""
AWS 설정 파일 파싱 모듈

이 모듈은 ~/.aws/config 및 ~/.aws/credentials 파일을 파싱하고
Provider 타입을 자동 감지합니다.
"""

from .loader import (
    AWSProfile,
    AWSSession,
    Loader,
    ParsedConfig,
    detect_provider_type,
    list_profiles,
    list_sso_sessions,
    load_config,
)

__all__: list[str] = [
    # Data classes
    "AWSProfile",
    "AWSSession",
    "ParsedConfig",
    # Classes
    "Loader",
    # Functions
    "load_config",
    "detect_provider_type",
    "list_profiles",
    "list_sso_sessions",
]
