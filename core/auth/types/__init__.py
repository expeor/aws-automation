# core/auth/types/__init__.py
"""
core/auth/types - AWS 인증 모듈의 공통 타입 및 인터페이스 정의

모든 Provider가 구현해야 하는 인터페이스(Provider ABC)와
공통 데이터 타입(ProviderType, AccountInfo), 에러 클래스들을 제공합니다.
"""

from .types import (
    AccountInfo,
    AccountNotFoundError,
    AuthError,
    ConfigurationError,
    NotAuthenticatedError,
    Provider,
    ProviderError,
    ProviderType,
    TokenExpiredError,
)

__all__: list[str] = [
    # Enums
    "ProviderType",
    # Interfaces
    "Provider",
    # Data classes
    "AccountInfo",
    # Errors
    "AuthError",
    "NotAuthenticatedError",
    "AccountNotFoundError",
    "ProviderError",
    "TokenExpiredError",
    "ConfigurationError",
]
