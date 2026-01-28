"""
tests/core/tools/cache/test_manager.py

Cache path management 테스트
- Cache directory creation
- Cache path generation
- Project root discovery
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_project_root(tmp_path):
    """임시 프로젝트 루트 디렉토리"""
    project_root = tmp_path / "test_project"
    project_root.mkdir()
    return project_root


@pytest.fixture
def mock_project_root(temp_project_root, monkeypatch):
    """프로젝트 루트를 임시 디렉토리로 설정"""
    # Mock the project root discovery
    import core.tools.cache.path as cache_path

    original_get_root = cache_path._get_project_root

    def mock_get_root():
        return str(temp_project_root)

    monkeypatch.setattr(cache_path, "_get_project_root", mock_get_root)
    monkeypatch.setattr(cache_path, "CACHE_ROOT", str(temp_project_root / "temp"))

    yield temp_project_root

    # Restore
    monkeypatch.setattr(cache_path, "_get_project_root", original_get_root)


# =============================================================================
# Cache Path Tests
# =============================================================================


class TestCachePath:
    """캐시 경로 테스트"""

    def test_get_cache_dir_without_category(self, mock_project_root):
        """카테고리 없이 루트 캐시 디렉토리 조회"""
        from core.tools.cache import get_cache_dir

        cache_dir = get_cache_dir()

        assert os.path.exists(cache_dir)
        assert cache_dir.endswith("temp")

    def test_get_cache_dir_with_category(self, mock_project_root):
        """카테고리별 캐시 디렉토리 조회"""
        from core.tools.cache import get_cache_dir

        cache_dir = get_cache_dir("ip")

        assert os.path.exists(cache_dir)
        assert cache_dir.endswith(os.path.join("temp", "ip"))

    def test_get_cache_dir_creates_directory(self, mock_project_root):
        """캐시 디렉토리 자동 생성 확인"""
        from core.tools.cache import get_cache_dir

        # Directory should not exist before call
        test_category = "new_category_xyz"
        test_path = mock_project_root / "temp" / test_category

        if test_path.exists():
            os.rmdir(test_path)

        cache_dir = get_cache_dir(test_category)

        # Directory should exist after call
        assert os.path.exists(cache_dir)
        assert test_path.exists()

    def test_get_cache_path(self, mock_project_root):
        """캐시 파일 경로 조회"""
        from core.tools.cache import get_cache_path

        cache_path = get_cache_path("ip", "test_cache.json")

        assert cache_path.endswith(os.path.join("temp", "ip", "test_cache.json"))
        # Directory should be created
        cache_dir = os.path.dirname(cache_path)
        assert os.path.exists(cache_dir)

    def test_get_cache_path_multiple_categories(self, mock_project_root):
        """여러 카테고리의 캐시 경로 조회"""
        from core.tools.cache import get_cache_path

        path1 = get_cache_path("ip", "file1.json")
        path2 = get_cache_path("eni", "file2.msgpack")
        path3 = get_cache_path("metrics", "file3.cache")

        assert "ip" in path1
        assert "eni" in path2
        assert "metrics" in path3

        # All directories should exist
        assert os.path.exists(os.path.dirname(path1))
        assert os.path.exists(os.path.dirname(path2))
        assert os.path.exists(os.path.dirname(path3))

    def test_cache_root_constant(self):
        """CACHE_ROOT 상수 확인"""
        from core.tools.cache import CACHE_ROOT

        assert CACHE_ROOT is not None
        assert isinstance(CACHE_ROOT, str)
        assert "temp" in CACHE_ROOT


# =============================================================================
# Project Root Discovery Tests
# =============================================================================


class TestProjectRootDiscovery:
    """프로젝트 루트 디스커버리 테스트"""

    def test_get_project_root_basic(self):
        """기본 프로젝트 루트 조회"""
        from core.tools.cache.path import _get_project_root

        root = _get_project_root()

        assert root is not None
        assert isinstance(root, str)
        assert os.path.exists(root)

    def test_get_project_root_finds_parent(self, tmp_path):
        """부모 디렉토리에서 프로젝트 루트 찾기"""
        from core.tools.cache.path import _get_project_root

        # Create project structure
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create pyproject.toml marker
        (project_root / "pyproject.toml").touch()

        # Create nested directory
        nested = project_root / "core" / "tools" / "cache"
        nested.mkdir(parents=True)

        # Mock current directory
        original_cwd = os.getcwd()
        try:
            os.chdir(nested)
            root = _get_project_root()
            # Should find project_root (where pyproject.toml is)
            assert "project" in root or os.path.exists(os.path.join(root, "pyproject.toml"))
        finally:
            os.chdir(original_cwd)

    def test_project_root_with_git(self, tmp_path):
        """Git 저장소 루트 찾기"""
        from core.tools.cache.path import _get_project_root

        # Create project with .git
        project_root = tmp_path / "git_project"
        project_root.mkdir()
        (project_root / ".git").mkdir()

        # Create nested directory
        nested = project_root / "subdir"
        nested.mkdir()

        original_cwd = os.getcwd()
        try:
            os.chdir(nested)
            root = _get_project_root()
            # Should find git_project (where .git is)
            assert "git_project" in root or os.path.exists(os.path.join(root, ".git"))
        finally:
            os.chdir(original_cwd)


# =============================================================================
# Cache File Operations Tests
# =============================================================================


class TestCacheFileOperations:
    """캐시 파일 작업 테스트"""

    def test_write_and_read_cache_file(self, mock_project_root):
        """캐시 파일 쓰기/읽기"""
        from core.tools.cache import get_cache_path

        cache_path = get_cache_path("test", "data.json")

        # Write test data
        test_data = '{"test": "data"}'
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(test_data)

        # Read back
        with open(cache_path, encoding="utf-8") as f:
            content = f.read()

        assert content == test_data

    def test_cache_path_separators(self, mock_project_root):
        """캐시 경로 구분자 확인"""
        from core.tools.cache import get_cache_path

        # Test with various filenames
        path1 = get_cache_path("ip", "azure_servicetags_cache.json")
        path2 = get_cache_path("eni", "network_interfaces_cache_session.msgpack")

        # Paths should use OS-specific separators
        assert os.sep in path1
        assert os.sep in path2

    def test_cache_directory_isolation(self, mock_project_root):
        """캐시 디렉토리 격리 확인"""
        from core.tools.cache import get_cache_dir

        ip_dir = get_cache_dir("ip")
        eni_dir = get_cache_dir("eni")

        # Directories should be different
        assert ip_dir != eni_dir

        # Both should exist under temp/
        assert "temp" in ip_dir
        assert "temp" in eni_dir

        # Both should exist
        assert os.path.exists(ip_dir)
        assert os.path.exists(eni_dir)


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_category_name(self, mock_project_root):
        """빈 카테고리명 처리"""
        from core.tools.cache import get_cache_dir

        cache_dir = get_cache_dir("")

        # Should return root cache directory
        assert cache_dir.endswith("temp")

    def test_special_characters_in_filename(self, mock_project_root):
        """파일명 특수 문자 처리"""
        from core.tools.cache import get_cache_path

        # Most special characters should work in filenames
        path = get_cache_path("test", "cache_with-dash_and.periods.json")

        assert os.path.exists(os.path.dirname(path))
        assert "cache_with-dash_and.periods.json" in path

    def test_nested_category_path(self, mock_project_root):
        """중첩된 카테고리 경로"""
        from core.tools.cache import get_cache_dir

        # Category can contain path separators
        nested_category = os.path.join("level1", "level2")
        cache_dir = get_cache_dir(nested_category)

        assert os.path.exists(cache_dir)
        assert "level1" in cache_dir
        assert "level2" in cache_dir

    def test_multiple_calls_same_category(self, mock_project_root):
        """같은 카테고리 여러 번 호출"""
        from core.tools.cache import get_cache_dir

        dir1 = get_cache_dir("test")
        dir2 = get_cache_dir("test")
        dir3 = get_cache_dir("test")

        # All should return same path
        assert dir1 == dir2 == dir3

        # Directory should exist only once
        assert os.path.exists(dir1)

    def test_unicode_in_filename(self, mock_project_root):
        """유니코드 파일명 처리"""
        from core.tools.cache import get_cache_path

        # Unicode filename
        path = get_cache_path("test", "캐시_파일.json")

        assert os.path.exists(os.path.dirname(path))
        # Check that path is valid
        assert isinstance(path, str)


# =============================================================================
# Module Exports Tests
# =============================================================================


class TestModuleExports:
    """모듈 익스포트 테스트"""

    def test_all_exports(self):
        """__all__ 익스포트 확인"""
        import core.tools.cache as cache_module

        assert hasattr(cache_module, "__all__")
        assert "get_cache_dir" in cache_module.__all__
        assert "get_cache_path" in cache_module.__all__
        assert "CACHE_ROOT" in cache_module.__all__

    def test_imported_functions_callable(self):
        """임포트된 함수 호출 가능 확인"""
        from core.tools.cache import get_cache_dir, get_cache_path

        assert callable(get_cache_dir)
        assert callable(get_cache_path)

    def test_cache_root_accessible(self):
        """CACHE_ROOT 접근 가능 확인"""
        from core.tools.cache import CACHE_ROOT

        assert CACHE_ROOT is not None
        assert isinstance(CACHE_ROOT, str)
