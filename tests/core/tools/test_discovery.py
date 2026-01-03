# tests/test_discovery.py
"""
internal/tools/discovery.py 단위 테스트

플러그인 자동 발견 시스템 테스트.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.tools.discovery import (
    discover_categories,
    get_category,
    list_categories,
    list_tools,
    load_tool,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_tools_path(tmp_path):
    """임시 tools 디렉토리 생성"""
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    return tools_dir


@pytest.fixture
def mock_category_module():
    """Mock 카테고리 모듈"""
    mock = MagicMock()
    mock.CATEGORY = {
        "name": "test_service",
        "description": "테스트 서비스",
        "group": "aws",
    }
    mock.TOOLS = [
        {
            "name": "테스트 도구",
            "description": "테스트 도구 설명",
            "permission": "read",
            "module": "test_tool",
        },
    ]
    return mock


# =============================================================================
# discover_categories 테스트
# =============================================================================


class TestDiscoverCategories:
    """discover_categories 함수 테스트"""

    def test_returns_list(self):
        """리스트 반환 확인"""
        result = discover_categories()
        assert isinstance(result, list)

    def test_categories_have_required_fields(self):
        """필수 필드 존재 확인"""
        categories = discover_categories()

        for cat in categories:
            assert "name" in cat
            assert "description" in cat
            assert "tools" in cat
            assert "module_path" in cat

    def test_ec2_category_exists(self):
        """EC2 카테고리 존재 확인"""
        categories = discover_categories(include_aws_services=True)
        ec2_cats = [c for c in categories if c["name"] == "ec2"]

        assert len(ec2_cats) == 1
        assert "EC2" in ec2_cats[0]["description"]

    def test_ec2_has_ebs_tools(self):
        """EC2 카테고리에 EBS 도구 존재 확인"""
        categories = discover_categories(include_aws_services=True)
        ec2_cat = next((c for c in categories if c["name"] == "ec2"), None)

        assert ec2_cat is not None
        assert len(ec2_cat["tools"]) > 0

        # EBS 관련 도구 확인
        ebs_tool = next((t for t in ec2_cat["tools"] if "EBS" in t["name"]), None)
        assert ebs_tool is not None
        assert ebs_tool["permission"] == "read"

    def test_aws_service_categories_exist(self):
        """AWS 서비스 카테고리들이 존재하는지 확인"""
        categories = discover_categories(include_aws_services=True)
        category_names = [c["name"] for c in categories]

        # 주요 AWS 서비스 카테고리 확인 (ebs는 ec2에 통합됨)
        expected = ["ec2", "s3", "rds", "iam", "vpc"]
        for name in expected:
            assert name in category_names, f"{name} 카테고리가 없습니다"

    def test_categories_are_discovered(self):
        """카테고리가 발견되는지 확인"""
        categories = discover_categories(include_aws_services=True)
        category_names = [c["name"] for c in categories]

        # 최소 몇 개의 카테고리가 발견되어야 함
        assert len(category_names) > 5, "카테고리가 충분히 발견되지 않았습니다"

        # 중복이 없어야 함
        assert len(category_names) == len(set(category_names)), "중복 카테고리가 있습니다"

    def test_excludes_pycache(self):
        """__pycache__ 제외 확인"""
        categories = discover_categories()
        names = [c["name"] for c in categories]

        assert "__pycache__" not in names

    def test_excludes_private_folders(self):
        """_ 시작 폴더 제외 확인"""
        categories = discover_categories()
        names = [c["name"] for c in categories]

        for name in names:
            assert not name.startswith("_")


# =============================================================================
# get_category 테스트
# =============================================================================


class TestGetCategory:
    """get_category 함수 테스트"""

    def test_find_by_name(self):
        """이름으로 카테고리 찾기"""
        cat = get_category("ec2", include_aws_services=True)

        assert cat is not None
        assert cat["name"] == "ec2"

    def test_find_by_alias(self):
        """별칭으로 카테고리 찾기"""
        # ec2 카테고리는 compute, ebs, eip 별칭을 가짐
        found = get_category("compute", include_aws_services=True)
        assert found is not None
        assert found["name"] == "ec2"

    def test_not_found_returns_none(self):
        """존재하지 않는 카테고리는 None 반환"""
        cat = get_category("nonexistent_category_xyz", include_aws_services=True)

        assert cat is None

    def test_returns_tools_list(self):
        """tools 목록 포함 확인"""
        cat = get_category("ebs", include_aws_services=True)

        assert cat is not None
        assert "tools" in cat
        assert isinstance(cat["tools"], list)


# =============================================================================
# load_tool 테스트
# =============================================================================


class TestLoadTool:
    """load_tool 함수 테스트"""

    def test_load_existing_tool(self):
        """존재하는 도구 로드"""
        tool = load_tool("ec2", "EBS 미사용 분석")

        assert tool is not None
        assert "run" in tool
        assert callable(tool["run"])
        assert "meta" in tool

    def test_load_tool_returns_meta(self):
        """도구 메타데이터 반환 확인"""
        tool = load_tool("ec2", "EBS 미사용 분석")

        assert tool is not None
        assert tool["meta"]["name"] == "EBS 미사용 분석"
        assert tool["meta"]["permission"] == "read"

    def test_nonexistent_category_returns_none(self):
        """존재하지 않는 카테고리는 None 반환"""
        tool = load_tool("nonexistent", "도구")

        assert tool is None

    def test_nonexistent_tool_returns_none(self):
        """존재하지 않는 도구는 None 반환"""
        tool = load_tool("ec2", "존재하지않는도구")

        assert tool is None

    def test_collect_options_is_optional(self):
        """collect_options는 선택적"""
        tool = load_tool("ec2", "EBS 미사용 분석")

        assert tool is not None
        # collect_options가 없으면 None
        assert tool["collect_options"] is None or callable(tool["collect_options"])

    def test_load_tool_with_import_error(self):
        """모듈 import 실패 시 None 반환"""
        # 존재하지 않는 모듈을 가진 가상의 도구
        with patch("core.tools.discovery.get_category") as mock_get_cat:
            mock_get_cat.return_value = {
                "name": "fake",
                "module_path": "core.tools.fake",
                "tools": [
                    {
                        "name": "broken_tool",
                        "module": "nonexistent_module",
                    }
                ],
            }

            tool = load_tool("fake", "broken_tool")
            assert tool is None


# =============================================================================
# list_categories 테스트
# =============================================================================


class TestListCategories:
    """list_categories 함수 테스트"""

    def test_returns_list_of_strings(self):
        """문자열 리스트 반환"""
        names = list_categories()

        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)

    def test_contains_known_categories(self):
        """알려진 AWS 서비스 카테고리 포함 확인"""
        names = list_categories()

        # 기본 카테고리가 포함되어야 함 (cost, fn, sso 등)
        assert "cost" in names or "fn" in names or "sso" in names
        assert len(names) > 0


# =============================================================================
# list_tools 테스트
# =============================================================================


class TestListTools:
    """list_tools 함수 테스트"""

    def test_returns_list_of_strings(self):
        """문자열 리스트 반환"""
        tools = list_tools("ebs")

        assert isinstance(tools, list)
        assert all(isinstance(t, str) for t in tools)

    def test_ec2_tools(self):
        """EC2 도구 목록 확인 (ebs 별칭으로 조회)"""
        tools = list_tools("ebs")  # ebs는 ec2의 별칭

        assert "EBS 미사용 분석" in tools
        assert "EIP 미사용 분석" in tools

    def test_nonexistent_category_returns_empty(self):
        """존재하지 않는 카테고리는 빈 리스트 반환"""
        tools = list_tools("nonexistent")

        assert tools == []


# =============================================================================
# Integration Tests (레거시 도구 포함 - 별도 실행)
# =============================================================================


@pytest.mark.integration
class TestDiscoveryIntegration:
    """Discovery 통합 테스트

    Note: 레거시 도구들이 아직 마이그레이션되지 않아 일부 실패할 수 있음.
    pytest -m integration 으로 별도 실행.
    """

    def test_all_tools_loadable(self):
        """모든 도구가 로드 가능한지 확인

        실패한 도구 목록을 출력하여 마이그레이션 필요 도구 파악 가능.
        """
        categories = discover_categories()
        failed = []

        for cat in categories:
            for tool_meta in cat["tools"]:
                tool = load_tool(cat["name"], tool_meta["name"])
                if tool is None:
                    failed.append(f"{cat['name']}/{tool_meta['name']}")

        if failed:
            pytest.fail(f"로드 실패한 도구: {failed}")

    def test_all_tools_have_run_function(self):
        """모든 도구가 run 함수를 가지는지 확인"""
        categories = discover_categories()
        missing = []

        for cat in categories:
            for tool_meta in cat["tools"]:
                tool = load_tool(cat["name"], tool_meta["name"])
                if tool and not callable(tool.get("run")):
                    missing.append(f"{cat['name']}/{tool_meta['name']}")

        if missing:
            pytest.fail(f"run 함수 없는 도구: {missing}")

    def test_tool_permissions_valid(self):
        """도구 권한이 유효한지 확인"""
        valid_permissions = {"read", "write", "delete"}
        categories = discover_categories()
        invalid = []

        for cat in categories:
            for tool_meta in cat["tools"]:
                perm = tool_meta.get("permission", "read")
                if perm not in valid_permissions:
                    invalid.append(f"{cat['name']}/{tool_meta['name']}: {perm}")

        if invalid:
            pytest.fail(f"유효하지 않은 권한: {invalid}")


# =============================================================================
# 정상 동작 도구 테스트 (Cost 카테고리)
# =============================================================================


class TestServiceToolsLoadable:
    """서비스별 도구 로드 테스트"""

    def test_ebs_unused_tool_loadable(self):
        """EBS 미사용 분석 도구 로드 가능"""
        tool = load_tool("ec2", "EBS 미사용 분석")
        assert tool is not None
        assert callable(tool["run"])

    def test_eip_unused_tool_loadable(self):
        """EIP 미사용 분석 도구 로드 가능"""
        tool = load_tool("ec2", "EIP 미사용 분석")
        assert tool is not None
        assert callable(tool["run"])

    def test_snapshot_unused_tool_loadable(self):
        """EBS Snapshot 미사용 분석 도구 로드 가능"""
        tool = load_tool("ec2", "EBS Snapshot 미사용 분석")
        assert tool is not None
        assert callable(tool["run"])

    def test_ami_unused_tool_loadable(self):
        """AMI 미사용 분석 도구 로드 가능"""
        tool = load_tool("ec2", "AMI 미사용 분석")
        assert tool is not None
        assert callable(tool["run"])
