# core/__init__.py
"""
core - AWS Automation 핵심 비즈니스 로직

순수 비즈니스 로직만 포함하며, CLI/Web UI에 대한 의존성이 없습니다.
모든 AWS 관련 기능의 기반이 되는 모듈입니다.

아키텍처:
    core/                       # 핵심 비즈니스 로직
    ├── auth/                   # AWS 인증 서브시스템
    │   ├── provider/           # 인증 프로바이더 구현체
    │   │   ├── sso_session.py  # SSO Session 인증
    │   │   ├── sso_profile.py  # SSO Profile 인증
    │   │   ├── static.py       # Static Credentials
    │   │   └── multi_account.py # Multi-Account 지원
    │   ├── session.py          # SessionIterator, DefaultProvider
    │   └── types.py            # 인증 관련 타입/예외
    │
    ├── tools/                  # 도구 플러그인 서브시스템
    │   ├── discovery.py        # 플러그인 자동 발견
    │   ├── aws_categories.py   # AWS 서비스 카테고리
    │   └── analysis/           # 분석 도구 베이스
    │       └── base.py         # BaseAnalysis 클래스
    │
    ├── region/                 # 리전 데이터
    │   └── data.py             # 리전 정보, 국가 매핑
    │
    ├── parallel/               # 병렬 처리 서브시스템
    │   ├── executor.py         # ParallelSessionExecutor
    │   ├── decorators.py       # @safe_aws_call, @with_retry
    │   ├── rate_limiter.py     # TokenBucketRateLimiter
    │   └── types.py            # TaskError, TaskResult
    │
    ├── config.py               # 중앙 집중식 설정 관리
    ├── exceptions.py           # 통합 예외 계층 구조
    └── types.py                # TypedDict/Protocol 정의

Usage:
    # 설정 사용
    from core.config import settings, get_default_region
    region = get_default_region()  # "ap-northeast-2"

    # 예외 처리
    from core.exceptions import APICallError, is_access_denied
    try:
        result = ec2.describe_instances()
    except Exception as e:
        if is_access_denied(e):
            print("권한이 없습니다")

    # 타입 사용
    from core.types import ToolMetadata, SessionProvider
    def process_tool(tool: ToolMetadata) -> None:
        print(tool["name"])

    # 플러그인 발견
    from core.tools.discovery import discover_categories
    categories = discover_categories()

    # 인증
    from core.auth import create_provider, SessionIterator
    provider = create_provider("sso_session", "my-profile")
    provider.authenticate()
"""

__all__: list[str] = [
    # 서브패키지
    "auth",
    "tools",
    "region",
    "parallel",
    # 모듈
    "config",
    "exceptions",
    "types",
]
