# internal/auth/config/__init__.py
"""
AWS 설정 파일 파싱 모듈

이 모듈은 ~/.aws/config 및 ~/.aws/credentials 파일을 파싱하고
Provider 타입을 자동 감지합니다.

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
"""

__all__ = [
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

_IMPORT_MAPPING = {
    "AWSProfile": (".loader", "AWSProfile"),
    "AWSSession": (".loader", "AWSSession"),
    "ParsedConfig": (".loader", "ParsedConfig"),
    "Loader": (".loader", "Loader"),
    "load_config": (".loader", "load_config"),
    "detect_provider_type": (".loader", "detect_provider_type"),
    "list_profiles": (".loader", "list_profiles"),
    "list_sso_sessions": (".loader", "list_sso_sessions"),
}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in _IMPORT_MAPPING:
        module_name, attr_name = _IMPORT_MAPPING[name]
        import importlib

        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
