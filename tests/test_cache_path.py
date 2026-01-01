# tests/test_cache_path.py
"""
pkg/cache/path.py 단위 테스트

캐시 경로 유틸리티 함수 테스트.
"""

import os
from pathlib import Path
from unittest.mock import patch

from core.tools.cache.path import (
    CACHE_ROOT,
    _get_project_root,
    get_cache_dir,
    get_cache_path,
)

# =============================================================================
# _get_project_root 테스트
# =============================================================================


class TestGetProjectRoot:
    """_get_project_root 함수 테스트"""

    def test_returns_string(self):
        """문자열 반환"""
        result = _get_project_root()
        assert isinstance(result, str)

    def test_returns_absolute_path(self):
        """절대 경로 반환"""
        result = _get_project_root()
        assert os.path.isabs(result)

    def test_contains_project_files(self):
        """프로젝트 파일 존재 확인"""
        root = _get_project_root()
        # 프로젝트 루트에 있어야 할 파일들
        assert os.path.exists(os.path.join(root, "pyproject.toml")) or os.path.exists(
            os.path.join(root, "requirements.txt")
        )


# =============================================================================
# CACHE_ROOT 테스트
# =============================================================================


class TestCacheRoot:
    """CACHE_ROOT 상수 테스트"""

    def test_is_string(self):
        """문자열 타입"""
        assert isinstance(CACHE_ROOT, str)

    def test_ends_with_temp(self):
        """temp 디렉토리로 끝남"""
        assert CACHE_ROOT.endswith("temp")

    def test_is_absolute_path(self):
        """절대 경로"""
        assert os.path.isabs(CACHE_ROOT)


# =============================================================================
# get_cache_dir 테스트
# =============================================================================


class TestGetCacheDir:
    """get_cache_dir 함수 테스트"""

    def test_returns_string(self):
        """문자열 반환"""
        result = get_cache_dir("test")
        assert isinstance(result, str)

    def test_creates_directory(self):
        """디렉토리 자동 생성"""
        result = get_cache_dir("test_category")
        assert os.path.isdir(result)

    def test_with_category(self):
        """카테고리가 있는 경우"""
        result = get_cache_dir("ip")
        assert "ip" in result
        assert "temp" in result

    def test_without_category(self):
        """카테고리가 없는 경우 (빈 문자열)"""
        result = get_cache_dir("")
        assert result == CACHE_ROOT

    def test_default_category(self):
        """기본값 (빈 문자열)"""
        result = get_cache_dir()
        assert result == CACHE_ROOT

    def test_nested_category_not_supported(self):
        """중첩 카테고리는 단순 문자열로 처리"""
        result = get_cache_dir("ip/azure")
        # 그냥 문자열로 처리됨 (os.path.join이 처리)
        assert "ip" in result or "azure" in result


# =============================================================================
# get_cache_path 테스트
# =============================================================================


class TestGetCachePath:
    """get_cache_path 함수 테스트"""

    def test_returns_string(self):
        """문자열 반환"""
        result = get_cache_path("ip", "cache.json")
        assert isinstance(result, str)

    def test_includes_category(self):
        """카테고리 경로 포함"""
        result = get_cache_path("ip", "azure_cache.json")
        assert "ip" in result

    def test_includes_filename(self):
        """파일명 포함"""
        result = get_cache_path("ip", "azure_cache.json")
        assert "azure_cache.json" in result

    def test_creates_directory(self):
        """디렉토리 자동 생성"""
        result = get_cache_path("new_category", "test.json")
        parent_dir = os.path.dirname(result)
        assert os.path.isdir(parent_dir)

    def test_is_absolute_path(self):
        """절대 경로"""
        result = get_cache_path("ip", "cache.json")
        assert os.path.isabs(result)

    def test_file_extension_preserved(self):
        """파일 확장자 보존"""
        result = get_cache_path("eni", "data.pickle")
        assert result.endswith(".pickle")

    def test_different_categories(self):
        """다른 카테고리에 대해 다른 경로"""
        result1 = get_cache_path("ip", "cache.json")
        result2 = get_cache_path("eni", "cache.json")
        assert result1 != result2
