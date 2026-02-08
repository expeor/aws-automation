# core/auth/config/__init__.py
"""
core/auth/config - AWS 설정 파일 파싱 모듈

~/.aws/config 및 ~/.aws/credentials 파일을 파싱하여 SSO 세션,
프로파일 정보를 추출하고, 각 프로파일의 Provider 타입을 자동 감지합니다.

주요 클래스:
    - Loader: AWS 설정 파일 로더 (config + credentials 파싱)
    - AWSProfile: 프로파일 설정 데이터 클래스
    - AWSSession: SSO 세션 설정 데이터 클래스
    - ParsedConfig: 파싱 결과 전체를 담는 데이터 클래스
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
