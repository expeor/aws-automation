"""
tests/test_discovery_system.py - 플러그인 디스커버리 테스트

플러그인 발견 시스템의 단위 테스트
"""


class TestDiscoverCategories:
    """discover_categories 함수 테스트"""

    def test_discover_returns_list(self):
        """카테고리 리스트 반환 확인"""
        from core.tools.discovery import discover_categories

        categories = discover_categories(use_cache=False)
        assert isinstance(categories, list)

    def test_discover_analysis_categories_only(self):
        """분석 카테고리만 반환 (기본값)"""
        from core.tools.discovery import ANALYSIS_CATEGORIES, discover_categories

        categories = discover_categories(include_aws_services=False, use_cache=False)

        # 모든 반환된 카테고리가 분석 카테고리이거나 AWS 서비스가 아님
        from core.tools.discovery import AWS_SERVICE_NAMES

        for cat in categories:
            name = cat.get("name", "")
            assert name not in AWS_SERVICE_NAMES or name in ANALYSIS_CATEGORIES

    def test_discover_all_categories(self):
        """모든 카테고리 반환 (AWS 서비스 포함)"""
        from core.tools.discovery import discover_categories

        categories = discover_categories(include_aws_services=True, use_cache=False)

        # 최소한 일부 AWS 서비스가 있어야 함 (ec2, s3 등)
        assert len(categories) > 0

    def test_category_has_required_fields(self):
        """카테고리에 필수 필드 존재 확인"""
        from core.tools.discovery import discover_categories

        categories = discover_categories(include_aws_services=True, use_cache=False)

        for cat in categories:
            assert "name" in cat, f"Category missing 'name': {cat}"
            assert "tools" in cat, f"Category missing 'tools': {cat}"
            assert "module_path" in cat, f"Category missing 'module_path': {cat}"

    def test_tools_have_required_fields(self):
        """도구에 필수 필드 존재 확인"""
        from core.tools.discovery import discover_categories

        categories = discover_categories(
            include_aws_services=True,
            use_cache=False,
            validate=True,
        )

        for cat in categories:
            for tool in cat["tools"]:
                assert "name" in tool, f"Tool missing 'name' in {cat['name']}"
                assert "description" in tool, f"Tool missing 'description' in {cat['name']}"
                assert "permission" in tool, f"Tool missing 'permission' in {cat['name']}"

    def test_cache_works(self):
        """캐싱 동작 확인"""
        from core.tools.discovery import (
            _discovery_cache,
            clear_discovery_cache,
            discover_categories,
        )

        # 캐시 초기화
        clear_discovery_cache()
        assert len(_discovery_cache) == 0

        # 첫 호출 - 캐시 생성
        categories1 = discover_categories(use_cache=True)

        # 캐시에 저장됨
        assert len(_discovery_cache) > 0

        # 두 번째 호출 - 캐시 사용
        categories2 = discover_categories(use_cache=True)

        # 동일한 결과
        assert len(categories1) == len(categories2)

        # 캐시 초기화
        clear_discovery_cache()
        assert len(_discovery_cache) == 0


class TestLoadTool:
    """load_tool 함수 테스트"""

    def test_load_existing_tool(self):
        """존재하는 도구 로드"""
        from core.tools.discovery import discover_categories, load_tool

        # 첫 번째 카테고리의 첫 번째 도구 로드 시도
        categories = discover_categories(include_aws_services=True, use_cache=False)

        if categories and categories[0]["tools"]:
            cat_name = categories[0]["name"]
            tool_name = categories[0]["tools"][0]["name"]

            tool = load_tool(cat_name, tool_name)

            if tool:  # ref 도구가 아닌 경우에만
                assert "run" in tool
                assert "meta" in tool
                assert callable(tool["run"])

    def test_load_nonexistent_tool(self):
        """존재하지 않는 도구 로드"""
        from core.tools.discovery import load_tool

        tool = load_tool("nonexistent-category", "nonexistent-tool")
        assert tool is None

    def test_load_nonexistent_category(self):
        """존재하지 않는 카테고리 로드"""
        from core.tools.discovery import load_tool

        tool = load_tool("nonexistent-category", "some-tool")
        assert tool is None


class TestGetCategory:
    """get_category 함수 테스트"""

    def test_get_existing_category(self):
        """존재하는 카테고리 조회"""
        from core.tools.discovery import discover_categories, get_category

        categories = discover_categories(include_aws_services=True, use_cache=False)

        if categories:
            cat_name = categories[0]["name"]
            cat = get_category(cat_name)

            assert cat is not None
            assert cat["name"] == cat_name

    def test_get_category_by_alias(self):
        """별칭으로 카테고리 조회"""
        from core.tools.discovery import discover_categories, get_category

        # 별칭이 있는 카테고리 찾기
        categories = discover_categories(include_aws_services=True, use_cache=False)

        for cat in categories:
            aliases = cat.get("aliases", [])
            if aliases:
                # 별칭으로 조회
                found = get_category(aliases[0])
                assert found is not None
                assert found["name"] == cat["name"]
                break

    def test_get_nonexistent_category(self):
        """존재하지 않는 카테고리 조회"""
        from core.tools.discovery import get_category

        cat = get_category("nonexistent-category-12345")
        assert cat is None


class TestMetadataValidation:
    """메타데이터 검증 테스트"""

    def test_validate_tool_metadata_valid(self):
        """유효한 도구 메타데이터 검증"""
        from core.config import validate_tool_metadata

        valid_tool = {
            "name": "테스트 도구",
            "description": "테스트 설명",
            "permission": "read",
        }

        errors = validate_tool_metadata(valid_tool)
        assert len(errors) == 0

    def test_validate_tool_metadata_missing_name(self):
        """name 필드 누락 검증"""
        from core.config import validate_tool_metadata

        invalid_tool = {
            "description": "테스트 설명",
            "permission": "read",
        }

        errors = validate_tool_metadata(invalid_tool)
        assert len(errors) > 0
        assert any("name" in e for e in errors)

    def test_validate_tool_metadata_invalid_permission(self):
        """유효하지 않은 permission 검증"""
        from core.config import validate_tool_metadata

        invalid_tool = {
            "name": "테스트",
            "description": "테스트",
            "permission": "invalid",
        }

        errors = validate_tool_metadata(invalid_tool)
        assert len(errors) > 0
        assert any("permission" in e for e in errors)

    def test_validate_tool_metadata_invalid_area(self):
        """유효하지 않은 area 검증"""
        from core.config import validate_tool_metadata

        invalid_tool = {
            "name": "테스트",
            "description": "테스트",
            "permission": "read",
            "area": "invalid_area",
        }

        errors = validate_tool_metadata(invalid_tool)
        assert len(errors) > 0
        assert any("area" in e for e in errors)


class TestListFunctions:
    """리스트 함수 테스트"""

    def test_list_categories(self):
        """카테고리 이름 목록 반환"""
        from core.tools.discovery import list_categories

        names = list_categories()
        assert isinstance(names, list)
        assert all(isinstance(n, str) for n in names)

    def test_list_tools(self):
        """도구 이름 목록 반환"""
        from core.tools.discovery import list_categories, list_tools

        categories = list_categories()

        if categories:
            cat_name = categories[0]
            tools = list_tools(cat_name)
            assert isinstance(tools, list)

    def test_list_tools_nonexistent_category(self):
        """존재하지 않는 카테고리의 도구 목록"""
        from core.tools.discovery import list_tools

        tools = list_tools("nonexistent-category")
        assert tools == []
