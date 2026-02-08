"""
tests/test_core_config.py - core/config.py 테스트
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from core.config import (
    TOOL_REQUIRED_FIELDS,
    VALID_AREAS,
    VALID_PERMISSIONS,
    get_analyzers_path,
    get_default_region,
    get_project_root,
    get_version,
    settings,
    validate_tool_metadata,
)


class TestSettings:
    """Settings 데이터클래스 테스트"""

    def test_settings_is_frozen(self):
        """설정이 불변인지 확인"""
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            settings.DEFAULT_REGION = "us-east-1"

    def test_default_values(self):
        """기본값 확인"""
        assert settings.DEFAULT_REGION == "ap-northeast-2"

    def test_security_settings(self):
        """보안 설정 확인"""
        assert settings.SECURITY_MIN_TLS_VERSION == "TLSv1.2"
        assert "SSLv3" in settings.SECURITY_VULNERABLE_PROTOCOLS
        assert "TLSv1" in settings.SECURITY_VULNERABLE_PROTOCOLS
        assert "TLSv1.2" in settings.SECURITY_SECURE_PROTOCOLS
        assert "TLSv1.3" in settings.SECURITY_SECURE_PROTOCOLS

    def test_weak_cipher_patterns(self):
        """취약 암호화 패턴 확인"""
        weak_patterns = settings.SECURITY_WEAK_CIPHER_PATTERNS
        assert "RC4" in weak_patterns
        assert "DES" in weak_patterns
        assert "3DES" in weak_patterns
        assert "MD5" in weak_patterns
        assert "NULL" in weak_patterns

    def test_analysis_categories(self):
        """분석 카테고리 확인"""
        assert "cost" in settings.ANALYSIS_CATEGORIES
        assert "security" in settings.ANALYSIS_CATEGORIES


class TestProjectPaths:
    """프로젝트 경로 함수 테스트"""

    def test_get_project_root(self):
        """프로젝트 루트 경로"""
        root = get_project_root()
        assert isinstance(root, Path)
        assert root.exists()
        assert (root / "core").exists()
        assert (root / "functions" / "analyzers").exists()

    def test_get_analyzers_path(self):
        """분석기 경로"""
        analyzers = get_analyzers_path()
        assert isinstance(analyzers, Path)
        assert analyzers.exists()
        assert analyzers.name == "analyzers"
        assert analyzers.parent.name == "functions"


class TestEnvironmentHelpers:
    """환경변수 헬퍼 함수 테스트"""

    def test_get_default_region_from_aws_region(self):
        """AWS_REGION 환경변수에서 리전 가져오기"""
        with patch.dict(os.environ, {"AWS_REGION": "us-west-2"}, clear=False):
            assert get_default_region() == "us-west-2"

    def test_get_default_region_fallback(self):
        """리전 환경변수 없을 때 기본값"""
        with patch.dict(os.environ, {}, clear=True):
            assert get_default_region() == settings.DEFAULT_REGION


class TestValidateToolMetadata:
    """validate_tool_metadata 테스트"""

    def test_valid_metadata(self):
        """유효한 메타데이터"""
        tool = {
            "name": "test-tool",
            "description": "Test description",
            "permission": "read",
        }
        errors = validate_tool_metadata(tool)
        assert errors == []

    def test_missing_required_fields(self):
        """필수 필드 누락"""
        tool = {"name": "test-tool"}
        errors = validate_tool_metadata(tool)
        assert any("description" in e for e in errors)
        assert any("permission" in e for e in errors)

    def test_empty_required_fields(self):
        """필수 필드가 비어있음"""
        tool = {
            "name": "",
            "description": "Test",
            "permission": "read",
        }
        errors = validate_tool_metadata(tool)
        assert any("비어있음" in e and "name" in e for e in errors)

    def test_invalid_permission(self):
        """유효하지 않은 permission"""
        tool = {
            "name": "test",
            "description": "Test",
            "permission": "invalid",
        }
        errors = validate_tool_metadata(tool)
        assert any("permission" in e for e in errors)

    def test_valid_permissions(self):
        """유효한 permission 값들"""
        for perm in VALID_PERMISSIONS:
            tool = {
                "name": "test",
                "description": "Test",
                "permission": perm,
            }
            errors = validate_tool_metadata(tool)
            assert errors == []

    def test_invalid_area(self):
        """유효하지 않은 area"""
        tool = {
            "name": "test",
            "description": "Test",
            "permission": "read",
            "area": "invalid_area",
        }
        errors = validate_tool_metadata(tool)
        assert any("area" in e for e in errors)

    def test_valid_areas(self):
        """유효한 area 값들"""
        for area in VALID_AREAS:
            tool = {
                "name": "test",
                "description": "Test",
                "permission": "read",
                "area": area,
            }
            errors = validate_tool_metadata(tool)
            assert errors == []

    def test_invalid_bool_field(self):
        """bool 필드에 잘못된 타입"""
        tool = {
            "name": "test",
            "description": "Test",
            "permission": "read",
            "single_region_only": "yes",  # 문자열이 아닌 bool이어야 함
        }
        errors = validate_tool_metadata(tool)
        assert any("single_region_only" in e and "bool" in e for e in errors)

    def test_valid_bool_fields(self):
        """유효한 bool 필드"""
        tool = {
            "name": "test",
            "description": "Test",
            "permission": "read",
            "single_region_only": True,
            "single_account_only": False,
        }
        errors = validate_tool_metadata(tool)
        assert errors == []


class TestGetVersion:
    """get_version 테스트"""

    def test_get_version_returns_string(self):
        """버전이 문자열로 반환됨"""
        version = get_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_version_format(self):
        """버전 포맷 확인 (기본 형식)"""
        # 캐시 클리어
        get_version.cache_clear()
        version = get_version()
        # 최소한 숫자와 점이 있어야 함
        assert any(c.isdigit() for c in version)


class TestConstants:
    """상수 테스트"""

    def test_tool_required_fields(self):
        """필수 필드 상수"""
        assert "name" in TOOL_REQUIRED_FIELDS
        assert "description" in TOOL_REQUIRED_FIELDS
        assert "permission" in TOOL_REQUIRED_FIELDS

    def test_valid_permissions(self):
        """유효한 permission 상수"""
        assert "read" in VALID_PERMISSIONS
        assert "write" in VALID_PERMISSIONS
        assert "delete" in VALID_PERMISSIONS

    def test_valid_areas(self):
        """유효한 area 상수"""
        assert "security" in VALID_AREAS
        assert "cost" in VALID_AREAS
        assert "performance" in VALID_AREAS
