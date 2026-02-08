# core/auth/__init__.py
"""
core/auth - AWS 통합 인증 모듈

각 도구마다 인증 코드를 별도로 작성하는 문제를 Provider 인터페이스로 통합하고,
인증 방식 변경 시 Manager로 중앙 집중 관리합니다.

지원하는 인증 방식:
    - SSOSessionProvider: AWS SSO 세션 기반 인증 (멀티 계정 지원)
    - SSOProfileProvider: SSO 프로파일 기반 인증 (단일/다중 프로파일)
    - StaticCredentialsProvider: 정적 액세스 키 (단일/다중 프로파일)

서브패키지:
    - types: Provider 인터페이스, ProviderType enum, AccountInfo, 에러 클래스
    - config: ~/.aws/config, ~/.aws/credentials 파싱 및 Provider 타입 감지
    - cache: SSO 토큰 파일 캐시, 메모리 기반 계정/자격증명 캐시
    - provider: BaseProvider, SSOSession/SSOProfile/Static Provider 구현

Example:
    from core.auth import get_session, iter_context_sessions, Manager

    # 단일 프로파일 세션
    session = get_session("my-profile", "ap-northeast-2")

    # Manager를 통한 Provider 관리
    manager = Manager()
"""

from .account import (
    format_account_identifier,
    get_account_alias,
    get_account_display_name,
    get_account_display_name_from_ctx,
    get_account_id,
    get_account_info,
)
from .auth import Manager, create_manager
from .cache import (
    AccountCache,
    CacheEntry,
    CredentialsCache,
    TokenCache,
    TokenCacheManager,
)
from .config import (
    AWSProfile,
    AWSSession,
    Loader,
    ParsedConfig,
    detect_provider_type,
    list_profiles,
    list_sso_sessions,
    load_config,
)
from .datadog_client import (
    DatadogClientManager,
    get_datadog_clients,
)
from .provider import (
    BaseProvider,
    SSOProfileConfig,
    SSOProfileProvider,
    SSOSessionConfig,
    SSOSessionProvider,
    StaticCredentialsConfig,
    StaticCredentialsProvider,
)
from .session import (
    ParallelSessionIterator,
    SessionIterator,
    clear_cache,
    get_context_session,
    get_current_context_info,
    get_session,
    iter_context_sessions,
    iter_profiles,
    iter_regions,
    iter_sessions,
)
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
    # Session helpers
    "get_session",
    "iter_regions",
    "iter_profiles",
    "iter_sessions",
    "clear_cache",
    # Context-based session helpers
    "SessionIterator",
    "ParallelSessionIterator",
    "iter_context_sessions",
    "get_context_session",
    # Context info
    "get_current_context_info",
    # Account utilities
    "get_account_display_name",
    "get_account_display_name_from_ctx",
    "get_account_id",
    "get_account_alias",
    "get_account_info",
    "format_account_identifier",
    # Datadog Client
    "DatadogClientManager",
    "get_datadog_clients",
]
