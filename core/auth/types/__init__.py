# internal/auth/types/__init__.py
"""
AWS 인증 모듈의 공통 타입 및 인터페이스 정의

이 모듈은 모든 Provider가 구현해야 하는 인터페이스와 공통 데이터 타입을 정의합니다.

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
"""

__all__ = [
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

_IMPORT_MAPPING = {
    "ProviderType": (".types", "ProviderType"),
    "Provider": (".types", "Provider"),
    "AccountInfo": (".types", "AccountInfo"),
    "AuthError": (".types", "AuthError"),
    "NotAuthenticatedError": (".types", "NotAuthenticatedError"),
    "AccountNotFoundError": (".types", "AccountNotFoundError"),
    "ProviderError": (".types", "ProviderError"),
    "TokenExpiredError": (".types", "TokenExpiredError"),
    "ConfigurationError": (".types", "ConfigurationError"),
}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in _IMPORT_MAPPING:
        module_name, attr_name = _IMPORT_MAPPING[name]
        import importlib

        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
