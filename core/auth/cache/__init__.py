# core/auth/cache/__init__.py
"""
core/auth/cache - AWS 인증 토큰 및 계정 캐시 관리 모듈

SSO 토큰과 계정 정보를 캐시하여 불필요한 API 호출을 줄입니다.

캐시 전략:
    - TokenCache / TokenCacheManager: 파일 기반 (~/.aws/sso/cache/) - AWS CLI 호환 필수
    - AccountCache: 메모리 기반 - 세션 중 계정 정보 재사용 (기본 TTL 1시간)
    - CredentialsCache: 메모리 기반 - STS 임시 자격증명 캐시 (기본 TTL 30분)
    - CacheEntry: 제네릭 캐시 항목 (만료 시간 관리 포함)
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
