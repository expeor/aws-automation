# internal/auth/cache/__init__.py
"""
AWS 인증 토큰 및 계정 캐시 관리 모듈

이 모듈은 SSO 토큰과 계정 정보를 캐시하여 불필요한 API 호출을 줄입니다.

캐시 전략:
- TokenCache: 파일 기반 (~/.aws/sso/cache/) - AWS CLI 호환 필수
- AccountCache: 메모리 기반 - 세션 중 재사용
- CredentialsCache: 메모리 기반 - 30분 TTL
"""

from .cache import (
    AccountCache,
    CacheEntry,
    CredentialsCache,
    TokenCache,
    TokenCacheManager,
)

__all__: list[str] = [
    "TokenCache",
    "TokenCacheManager",
    "AccountCache",
    "CredentialsCache",
    "CacheEntry",
]
