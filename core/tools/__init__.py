"""AWS 분석/작업 도구 플러그인 시스템.

도구 발견(discovery), 도구 실행(base runner), 캐시, 이력 관리 등
플러그인 시스템의 핵심 모듈들을 제공합니다.

Modules:
    base: 도구 Runner 베이스 클래스 (BaseToolRunner).
    discovery: 카테고리/도구 자동 발견 시스템.
    aws_categories: AWS 서비스 카테고리 매핑.
    types: 도구/카테고리 메타데이터 타입 정의.
    cache: 캐시 경로 및 TTL 관리.
    history: 사용 이력, 즐겨찾기, 프로파일 그룹 관리.
"""

from .base import BaseToolRunner
from .discovery import (
    discover_categories,
    get_area_summary,
    get_category,
    list_tools_by_area,
    load_tool,
)

__all__: list[str] = [
    "BaseToolRunner",
    # Discovery
    "discover_categories",
    "get_category",
    "load_tool",
    "list_tools_by_area",
    "get_area_summary",
]
