# core/auth/__init__.py
"""
AWS 통합 인증 모듈 (core/auth)

문제점 해결:
- 각 도구마다 인증 코드를 별도로 작성 → Provider 인터페이스로 통합
- 인증 방식 변경 시 여러 파일 수정 → Manager로 중앙 집중 관리
- 코드 중복 및 유지보수 어려움 → 서브패키지로 기능 분리

지원하는 인증 방식:
- SSOSessionProvider: AWS SSO 세션 기반 인증 (멀티 계정 지원)
- SSOProfileProvider: SSO 프로파일 기반 인증 (단일/다중 프로파일)
- StaticCredentialsProvider: 정적 액세스 키 (단일/다중 프로파일)

사용 예시:
    from core.auth import (
        Manager, create_manager,
        SSOSessionProvider, SSOSessionConfig,
        ProviderType, AccountInfo,
    )
    
    # Provider 생성 및 인증
    config = SSOSessionConfig(
        session_name="my-sso",
        start_url="https://my-sso.awsapps.com/start",
        region="ap-northeast-2",
    )
    provider = SSOSessionProvider(config)
    
    # Manager 사용
    manager = create_manager()
    manager.register_provider(provider)
    manager.set_active_provider(provider)
    manager.authenticate()
    
    # 계정 목록 조회
    accounts = manager.list_accounts()
    
    # 세션 획득
    session = manager.get_session(
        account_id="123456789012",
        role_name="AdminRole",
        region="ap-northeast-2"
    )

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
    실제 사용 시점에만 하위 모듈이 로드되어 CLI 시작 시간을 최적화합니다.
"""

__all__ = [
    # Types
    "ProviderType",
    "Provider",
    "AccountInfo",
    "AuthError",
    "NotAuthenticatedError",
    "AccountNotFoundError",
    "ProviderError",
    "TokenExpiredError",
    "ConfigurationError",
    # Cache
    "TokenCache",
    "TokenCacheManager",
    "AccountCache",
    "CredentialsCache",
    "CacheEntry",
    # Config
    "Loader",
    "AWSProfile",
    "AWSSession",
    "ParsedConfig",
    "load_config",
    "detect_provider_type",
    "list_profiles",
    "list_sso_sessions",
    # Providers
    "BaseProvider",
    "SSOSessionProvider",
    "SSOSessionConfig",
    "SSOProfileProvider",
    "SSOProfileConfig",
    "StaticCredentialsProvider",
    "StaticCredentialsConfig",
    # Manager
    "Manager",
    "create_manager",
    # Session 헬퍼
    "get_session",
    "iter_regions",
    "iter_profiles",
    "iter_sessions",
    "clear_cache",
    # Context 기반 세션 헬퍼
    "SessionIterator",
    "iter_context_sessions",
    "get_context_session",
    # Context 정보 조회
    "get_current_context_info",
    # Account 유틸리티
    "get_account_display_name",
    "get_account_display_name_from_ctx",
    "get_account_id",
    "get_account_alias",
    "get_account_info",
    "format_account_identifier",
]

# Lazy import 매핑 테이블
_IMPORT_MAPPING = {
    # Types
    "ProviderType": (".types", "ProviderType"),
    "Provider": (".types", "Provider"),
    "AccountInfo": (".types", "AccountInfo"),
    "AuthError": (".types", "AuthError"),
    "NotAuthenticatedError": (".types", "NotAuthenticatedError"),
    "AccountNotFoundError": (".types", "AccountNotFoundError"),
    "ProviderError": (".types", "ProviderError"),
    "TokenExpiredError": (".types", "TokenExpiredError"),
    "ConfigurationError": (".types", "ConfigurationError"),
    # Cache
    "TokenCache": (".cache", "TokenCache"),
    "TokenCacheManager": (".cache", "TokenCacheManager"),
    "AccountCache": (".cache", "AccountCache"),
    "CredentialsCache": (".cache", "CredentialsCache"),
    "CacheEntry": (".cache", "CacheEntry"),
    # Config
    "Loader": (".config", "Loader"),
    "AWSProfile": (".config", "AWSProfile"),
    "AWSSession": (".config", "AWSSession"),
    "ParsedConfig": (".config", "ParsedConfig"),
    "load_config": (".config", "load_config"),
    "detect_provider_type": (".config", "detect_provider_type"),
    "list_profiles": (".config", "list_profiles"),
    "list_sso_sessions": (".config", "list_sso_sessions"),
    # Providers
    "BaseProvider": (".provider", "BaseProvider"),
    "SSOSessionProvider": (".provider", "SSOSessionProvider"),
    "SSOSessionConfig": (".provider", "SSOSessionConfig"),
    "SSOProfileProvider": (".provider", "SSOProfileProvider"),
    "SSOProfileConfig": (".provider", "SSOProfileConfig"),
    "StaticCredentialsProvider": (".provider", "StaticCredentialsProvider"),
    "StaticCredentialsConfig": (".provider", "StaticCredentialsConfig"),
    # Manager
    "Manager": (".auth", "Manager"),
    "create_manager": (".auth", "create_manager"),
    # Session 헬퍼
    "get_session": (".session", "get_session"),
    "iter_regions": (".session", "iter_regions"),
    "iter_profiles": (".session", "iter_profiles"),
    "iter_sessions": (".session", "iter_sessions"),
    "clear_cache": (".session", "clear_cache"),
    # Context 기반 세션 헬퍼
    "SessionIterator": (".session", "SessionIterator"),
    "iter_context_sessions": (".session", "iter_context_sessions"),
    "get_context_session": (".session", "get_context_session"),
    # Context 정보 조회
    "get_current_context_info": (".session", "get_current_context_info"),
    # Account 유틸리티
    "get_account_display_name": (".account", "get_account_display_name"),
    "get_account_display_name_from_ctx": (
        ".account",
        "get_account_display_name_from_ctx",
    ),
    "get_account_id": (".account", "get_account_id"),
    "get_account_alias": (".account", "get_account_alias"),
    "get_account_info": (".account", "get_account_info"),
    "format_account_identifier": (".account", "format_account_identifier"),
}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드

    CLI 시작 시간 최적화를 위해 무거운 의존성(boto3 등)을
    실제 필요한 시점에만 로드합니다.
    """
    if name in _IMPORT_MAPPING:
        module_name, attr_name = _IMPORT_MAPPING[name]
        import importlib

        module = importlib.import_module(module_name, __name__)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
