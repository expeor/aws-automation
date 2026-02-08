"""캐시 경로 유틸리티.

모든 캐시는 프로젝트 루트의 ``temp/`` 디렉토리에 저장됩니다.
캐시 루트 경로 상수와 카테고리별 캐시 디렉토리/파일 경로 생성 함수를 제공합니다.

Attributes:
    CACHE_ROOT: 캐시 루트 디렉토리 절대 경로 (``{project_root}/temp``).
"""

import os
from pathlib import Path


def _get_project_root() -> str:
    """프로젝트 루트 경로를 반환합니다.

    파일 위치 기준으로 4단계 상위 디렉토리를 계산합니다:
    ``core/tools/cache/path.py`` -> ``core/tools/cache/`` -> ``core/tools/`` -> ``core/`` -> ``project_root/``

    Returns:
        프로젝트 루트 디렉토리 절대 경로 문자열.
    """
    current = Path(__file__).resolve()
    return str(current.parent.parent.parent.parent)


# 캐시 루트 디렉토리 (프로젝트 루트/temp)
CACHE_ROOT = os.path.join(_get_project_root(), "temp")


def get_cache_dir(category: str = "") -> str:
    """캐시 디렉토리 경로 반환

    Args:
        category: 캐시 카테고리 (예: "ip", "eni")
                  빈 문자열이면 루트 캐시 디렉토리 반환

    Returns:
        캐시 디렉토리 절대 경로 (자동 생성됨)

    Example:
        >>> get_cache_dir("ip")
        '/path/to/project/temp/ip'
    """
    cache_dir = os.path.join(CACHE_ROOT, category) if category else CACHE_ROOT

    # 디렉토리 자동 생성
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def get_cache_path(category: str, filename: str) -> str:
    """캐시 파일 경로 반환

    Args:
        category: 캐시 카테고리 (예: "ip", "eni")
        filename: 캐시 파일명 (예: "azure_servicetags_cache.json")

    Returns:
        캐시 파일 절대 경로 (디렉토리 자동 생성됨)

    Example:
        >>> get_cache_path("ip", "azure_servicetags_cache.json")
        '/path/to/project/temp/ip/azure_servicetags_cache.json'
    """
    cache_dir = get_cache_dir(category)
    return os.path.join(cache_dir, filename)
