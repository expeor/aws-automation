# core/auth/provider/__init__.py
"""
core/auth/provider - AWS 인증 Provider 구현 모듈

다양한 인증 방식을 구현하는 Provider 클래스들을 제공합니다.
모든 Provider는 BaseProvider를 상속하며, Provider ABC 인터페이스를 준수합니다.

Provider 목록:
    - SSOSessionProvider: AWS SSO 세션 기반 인증 (멀티 계정 지원, 권장)
    - SSOProfileProvider: SSO 프로파일 기반 인증 (특정 계정/역할 바인딩)
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
