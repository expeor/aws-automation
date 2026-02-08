"""캐시 TTL(Time To Live) 관리.

카테고리별 캐시 유효기간을 관리하고, 파일 mtime 기반으로 만료 여부를 확인합니다.
``get_or_fetch``를 통해 캐시 우선 데이터 조회를 간편하게 수행할 수 있습니다.

Attributes:
    CACHE_TTL: 카테고리별 캐시 TTL 설정 딕셔너리.
    DEFAULT_TTL: 설정되지 않은 카테고리의 기본 TTL (12시간).

Example:
    ::

        from core.tools.cache.ttl import is_cache_valid, get_or_fetch

        # 캐시 유효성 확인
        if is_cache_valid("pricing", filepath):
            data = load_from_cache(filepath)
        else:
            data = fetch_from_api()
            save_to_cache(filepath, data)

        # 또는 한 줄로:
        data = get_or_fetch("pricing", "ec2_prices.json", fetch_fn=fetch_ec2_prices)
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from .path import get_cache_path

logger = logging.getLogger(__name__)

# 카테고리별 캐시 TTL 설정
CACHE_TTL: dict[str, timedelta] = {
    "pricing": timedelta(days=1),
    "ip": timedelta(hours=1),
    "ip_ranges": timedelta(hours=24),
    "region": timedelta(weeks=1),
    "eni": timedelta(hours=4),
}

# 기본 TTL (설정되지 않은 카테고리)
DEFAULT_TTL = timedelta(hours=12)


def get_ttl(category: str) -> timedelta:
    """카테고리의 TTL 반환

    Args:
        category: 캐시 카테고리

    Returns:
        해당 카테고리의 TTL (설정 없으면 DEFAULT_TTL)
    """
    return CACHE_TTL.get(category, DEFAULT_TTL)


def is_cache_valid(category: str, filepath: str) -> bool:
    """파일 mtime 기반 캐시 유효성 확인

    Args:
        category: 캐시 카테고리 (TTL 조회용)
        filepath: 캐시 파일 경로

    Returns:
        캐시가 유효하면 True, 만료되었거나 없으면 False
    """
    if not os.path.exists(filepath):
        return False

    try:
        mtime = os.path.getmtime(filepath)
        import time

        age_seconds = time.time() - mtime
        ttl = get_ttl(category)
        return age_seconds < ttl.total_seconds()
    except OSError:
        return False


def get_or_fetch(
    category: str,
    filename: str,
    fetch_fn: Callable[[], Any],
) -> Any:
    """캐시 유효하면 로드, 아니면 fetch_fn 실행 후 저장

    JSON 직렬화 가능한 데이터에 대해 동작합니다.

    Args:
        category: 캐시 카테고리
        filename: 캐시 파일명
        fetch_fn: 캐시 미스 시 호출할 데이터 fetch 함수

    Returns:
        캐시된 데이터 또는 새로 fetch한 데이터
    """
    filepath = get_cache_path(category, filename)

    if is_cache_valid(category, filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.debug("캐시 로드 실패 (%s/%s): %s", category, filename, e)

    # Cache miss - fetch new data
    data = fetch_fn()

    # Save to cache
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
    except OSError as e:
        logger.debug("캐시 저장 실패 (%s/%s): %s", category, filename, e)

    return data
