# core/__init__.py
"""
core - AWS Automation CLI 인프라

CLI 기반 인프라 전체를 포함하는 최상위 패키지입니다.
인증, 병렬 처리, 도구 관리, CLI, 공유 유틸리티를 통합합니다.

아키텍처:
    core/
    ├── auth/           # AWS 인증 서브시스템
    ├── parallel/       # 병렬 처리 (executor, rate limiter)
    ├── tools/          # 도구 관리 (discovery, history, cache)
    ├── region/         # 리전 데이터 및 가용성
    ├── cli/            # Click CLI, 대화형 메뉴, i18n
    ├── shared/         # 공유 유틸리티 (AWS, I/O)
    ├── scripts/        # 개발 도구 (index generator)
    ├── config.py       # 중앙 설정 관리
    └── exceptions.py   # 통합 예외 계층

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

    # 플러그인 발견
    from core.tools.discovery import discover_categories
    categories = discover_categories()

    # 인증
    from core.auth import create_provider, SessionIterator
    provider = create_provider("sso_session", "my-profile")
    provider.authenticate()
"""

from core import auth, cli, config, exceptions, parallel, region, shared, tools

__all__: list[str] = [
    # 서브패키지
    "auth",
    "cli",
    "shared",
    "tools",
    "region",
    "parallel",
    # 모듈
    "config",
    "exceptions",
]
