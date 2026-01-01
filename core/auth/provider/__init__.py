# internal/auth/provider/__init__.py
"""
AWS 인증 Provider 구현 모듈

이 모듈은 다양한 인증 방식을 구현하는 Provider 클래스들을 제공합니다.

Provider 목록:
- SSOSessionProvider: AWS SSO 세션 기반 인증 (멀티 계정 지원)
- SSOProfileProvider: SSO 프로파일 기반 인증 (단일 계정)
- StaticCredentialsProvider: 정적 액세스 키 인증 (단일 계정)

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
"""

__all__ = [
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

_IMPORT_MAPPING = {
    "BaseProvider": (".base", "BaseProvider"),
    "SSOSessionProvider": (".sso_session", "SSOSessionProvider"),
    "SSOSessionConfig": (".sso_session", "SSOSessionConfig"),
    "SSOProfileProvider": (".sso_profile", "SSOProfileProvider"),
    "SSOProfileConfig": (".sso_profile", "SSOProfileConfig"),
    "StaticCredentialsProvider": (".static", "StaticCredentialsProvider"),
    "StaticCredentialsConfig": (".static", "StaticCredentialsConfig"),
}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in _IMPORT_MAPPING:
        module_name, attr_name = _IMPORT_MAPPING[name]
        import importlib

        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
