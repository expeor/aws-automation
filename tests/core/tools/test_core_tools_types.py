"""
tests/test_core_tools_types.py - core/tools/types.py 테스트
"""

from core.tools.types import (
    AREA_COMMANDS,
    AREA_DISPLAY_BY_KEY,
    AREA_KEYWORDS,
    AREA_REGISTRY,
    AreaInfo,
    CategoryMeta,
    ToolMeta,
)


class TestAreaRegistry:
    """AREA_REGISTRY 테스트"""

    def test_has_required_areas(self):
        """필수 영역 존재 확인 (ReportType + ToolType)"""
        keys = [a["key"] for a in AREA_REGISTRY]
        # ReportType - Core (5)
        assert "unused" in keys
        assert "security" in keys
        assert "cost" in keys
        assert "audit" in keys
        assert "inventory" in keys
        # ReportType - Extended (5)
        assert "backup" in keys
        assert "compliance" in keys
        assert "performance" in keys
        assert "network" in keys
        assert "quota" in keys
        # ToolType (5)
        assert "log" in keys
        assert "search" in keys
        assert "cleanup" in keys
        assert "tag" in keys
        assert "sync" in keys

    def test_area_count(self):
        """영역 수 확인 (최소 15개 이상)"""
        assert len(AREA_REGISTRY) >= 15

    def test_area_has_required_fields(self):
        """각 영역에 필수 필드 존재"""
        for area in AREA_REGISTRY:
            assert "key" in area
            assert "command" in area
            assert "label" in area
            assert "desc" in area
            assert "color" in area
            assert "icon" in area

    def test_area_commands_format(self):
        """영역 커맨드 형식 확인"""
        for area in AREA_REGISTRY:
            assert area["command"].startswith("/")

    def test_security_area(self):
        """보안 영역 상세"""
        security = next(a for a in AREA_REGISTRY if a["key"] == "security")
        assert security["command"] == "/security"
        assert security["label"] == "보안"
        assert security["color"] == "magenta"

    def test_unused_area(self):
        """미사용 영역 상세"""
        unused = next(a for a in AREA_REGISTRY if a["key"] == "unused")
        assert unused["command"] == "/unused"
        assert unused["label"] == "미사용"
        assert unused["color"] == "red"

    def test_cost_area(self):
        """비용 영역 상세"""
        cost = next(a for a in AREA_REGISTRY if a["key"] == "cost")
        assert cost["command"] == "/cost"
        assert cost["label"] == "비용"
        assert cost["color"] == "cyan"


class TestAreaCommands:
    """AREA_COMMANDS 테스트"""

    def test_basic_commands(self):
        """기본 커맨드 매핑"""
        assert AREA_COMMANDS["/security"] == "security"
        assert AREA_COMMANDS["/cost"] == "cost"
        assert AREA_COMMANDS["/unused"] == "unused"
        assert AREA_COMMANDS["/audit"] == "audit"
        assert AREA_COMMANDS["/inventory"] == "inventory"
        assert AREA_COMMANDS["/backup"] == "backup"
        assert AREA_COMMANDS["/perf"] == "performance"
        assert AREA_COMMANDS["/log"] == "log"
        assert AREA_COMMANDS["/search"] == "search"
        assert AREA_COMMANDS["/cleanup"] == "cleanup"
        assert AREA_COMMANDS["/tag"] == "tag"
        assert AREA_COMMANDS["/sync"] == "sync"

    def test_alias_commands(self):
        """별칭 커맨드"""
        assert AREA_COMMANDS["/sec"] == "security"

    def test_all_registry_commands_mapped(self):
        """모든 레지스트리 커맨드가 매핑됨"""
        for area in AREA_REGISTRY:
            assert area["command"] in AREA_COMMANDS


class TestAreaKeywords:
    """AREA_KEYWORDS 테스트"""

    def test_unused_keywords(self):
        """미사용 키워드"""
        assert AREA_KEYWORDS["미사용"] == "unused"
        assert AREA_KEYWORDS["유휴"] == "unused"
        assert AREA_KEYWORDS["고아"] == "unused"

    def test_security_keywords(self):
        """보안 키워드"""
        assert AREA_KEYWORDS["보안"] == "security"
        assert AREA_KEYWORDS["취약"] == "security"
        assert AREA_KEYWORDS["암호화"] == "security"
        assert AREA_KEYWORDS["퍼블릭"] == "security"

    def test_cost_keywords(self):
        """비용 키워드"""
        assert AREA_KEYWORDS["비용"] == "cost"
        assert AREA_KEYWORDS["절감"] == "cost"
        assert AREA_KEYWORDS["최적화"] == "cost"

    def test_audit_keywords(self):
        """감사 키워드"""
        assert AREA_KEYWORDS["감사"] == "audit"
        assert AREA_KEYWORDS["점검"] == "audit"

    def test_inventory_keywords(self):
        """인벤토리 키워드"""
        assert AREA_KEYWORDS["현황"] == "inventory"
        assert AREA_KEYWORDS["인벤토리"] == "inventory"
        assert AREA_KEYWORDS["목록"] == "inventory"

    def test_backup_keywords(self):
        """백업 키워드"""
        assert AREA_KEYWORDS["백업"] == "backup"
        assert AREA_KEYWORDS["복구"] == "backup"

    def test_performance_keywords(self):
        """성능 키워드"""
        assert AREA_KEYWORDS["성능"] == "performance"

    def test_search_keywords(self):
        """검색 키워드"""
        assert AREA_KEYWORDS["검색"] == "search"
        assert AREA_KEYWORDS["추적"] == "search"

    def test_cleanup_keywords(self):
        """정리 키워드"""
        assert AREA_KEYWORDS["정리"] == "cleanup"
        assert AREA_KEYWORDS["삭제"] == "cleanup"

    def test_tag_keywords(self):
        """태그 키워드"""
        assert AREA_KEYWORDS["태그"] == "tag"

    def test_sync_keywords(self):
        """동기화 키워드"""
        assert AREA_KEYWORDS["동기화"] == "sync"


class TestAreaDisplayByKey:
    """AREA_DISPLAY_BY_KEY 테스트"""

    def test_all_areas_have_display(self):
        """모든 영역에 디스플레이 정보 존재"""
        for area in AREA_REGISTRY:
            assert area["key"] in AREA_DISPLAY_BY_KEY

    def test_display_has_required_fields(self):
        """디스플레이에 필수 필드 존재"""
        for _key, display in AREA_DISPLAY_BY_KEY.items():
            assert "label" in display
            assert "color" in display
            assert "icon" in display

    def test_security_display(self):
        """보안 디스플레이"""
        assert AREA_DISPLAY_BY_KEY["security"]["label"] == "보안"
        assert AREA_DISPLAY_BY_KEY["security"]["color"] == "magenta"

    def test_unused_display(self):
        """미사용 디스플레이"""
        assert AREA_DISPLAY_BY_KEY["unused"]["label"] == "미사용"
        assert AREA_DISPLAY_BY_KEY["unused"]["color"] == "red"

    def test_cost_display(self):
        """비용 디스플레이"""
        assert AREA_DISPLAY_BY_KEY["cost"]["label"] == "비용"
        assert AREA_DISPLAY_BY_KEY["cost"]["color"] == "cyan"


class TestToolMeta:
    """ToolMeta TypedDict 테스트"""

    def test_can_create_minimal_tool_meta(self):
        """최소 필드로 ToolMeta 생성"""
        tool: ToolMeta = {
            "name": "test-tool",
            "description": "Test description",
            "permission": "read",
            "module": "test.module",
        }
        assert tool["name"] == "test-tool"
        assert tool["permission"] == "read"

    def test_can_create_full_tool_meta(self):
        """모든 필드로 ToolMeta 생성"""
        tool: ToolMeta = {
            "name": "test-tool",
            "description": "Test description",
            "permission": "write",
            "module": "test.module",
            "area": "security",
            "ref": "other/tool",
            "single_region_only": True,
            "single_account_only": False,
            "meta": {"cycle": "daily"},
            "function": "execute",
        }
        assert tool["area"] == "security"
        assert tool["single_region_only"] is True
        assert tool["meta"]["cycle"] == "daily"


class TestCategoryMeta:
    """CategoryMeta TypedDict 테스트"""

    def test_can_create_minimal_category_meta(self):
        """최소 필드로 CategoryMeta 생성"""
        category: CategoryMeta = {
            "name": "ec2",
            "description": "EC2 tools",
        }
        assert category["name"] == "ec2"

    def test_can_create_full_category_meta(self):
        """모든 필드로 CategoryMeta 생성"""
        category: CategoryMeta = {
            "name": "ec2",
            "description": "EC2 tools",
            "display_name": "Amazon EC2",
            "aliases": ["compute"],
            "group": "aws",
            "icon": "server",
            "collection": False,
        }
        assert category["display_name"] == "Amazon EC2"
        assert "compute" in category["aliases"]
        assert category["group"] == "aws"


class TestAreaInfoType:
    """AreaInfo TypedDict 테스트"""

    def test_area_info_fields(self):
        """AreaInfo 필드 확인"""
        area: AreaInfo = {
            "key": "test",
            "command": "/test",
            "label": "테스트",
            "desc": "테스트 영역",
            "color": "blue",
            "icon": "gear",
        }
        assert area["key"] == "test"
        assert area["command"] == "/test"
        assert area["label"] == "테스트"
        assert area["color"] == "blue"
