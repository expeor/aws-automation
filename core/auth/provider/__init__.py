# internal/auth/provider/__init__.py
"""
AWS 인증 Provider 구현 모듈

이 모듈은 다양한 인증 방식을 구현하는 Provider 클래스들을 제공합니다.

Provider 목록:
- SSOSessionProvider: AWS SSO 세션 기반 인증 (멀티 계정 지원)
- SSOProfileProvider: SSO 프로파일 기반 인증 (단일 계정)
- StaticCredentialsProvider: 정적 액세스 키 인증 (단일 계정)
"""

from .base import BaseProvider
from .sso_profile import SSOProfileConfig, SSOProfileProvider
from .sso_session import SSOSessionConfig, SSOSessionProvider
from .static import StaticCredentialsConfig, StaticCredentialsProvider

__all__: list[str] = [
    # Base
    "BaseProvider",
    # SSO Session
    "SSOSessionProvider",
    "SSOSessionConfig",
    # SSO Profile
    "SSOProfileProvider",
    "SSOProfileConfig",
    # Static Credentials
    "StaticCredentialsProvider",
    "StaticCredentialsConfig",
]
