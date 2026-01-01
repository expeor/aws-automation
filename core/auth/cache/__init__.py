# internal/auth/cache/__init__.py
"""
AWS 인증 토큰 및 계정 캐시 관리 모듈

이 모듈은 SSO 토큰과 계정 정보를 캐시하여 불필요한 API 호출을 줄입니다.

캐시 전략:
- TokenCache: 파일 기반 (~/.aws/sso/cache/) - AWS CLI 호환 필수
- AccountCache: 메모리 기반 - 세션 중 재사용
- CredentialsCache: 메모리 기반 - 30분 TTL

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
"""

__all__ = [
    "TokenCache",
    "TokenCacheManager",
    "AccountCache",
    "CredentialsCache",
    "CacheEntry",
]

_IMPORT_MAPPING = {
    "TokenCache": (".cache", "TokenCache"),
    "TokenCacheManager": (".cache", "TokenCacheManager"),
    "AccountCache": (".cache", "AccountCache"),
    "CredentialsCache": (".cache", "CredentialsCache"),
    "CacheEntry": (".cache", "CacheEntry"),
}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in _IMPORT_MAPPING:
        module_name, attr_name = _IMPORT_MAPPING[name]
        import importlib

        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
