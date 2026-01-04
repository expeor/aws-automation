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
        """필수 영역 존재 확인"""
        keys = [a["key"] for a in AREA_REGISTRY]
        assert "security" in keys
        assert "cost" in keys
        assert "fault_tolerance" in keys
        assert "performance" in keys
        assert "operational" in keys

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
        assert AREA_COMMANDS["/ft"] == "fault_tolerance"
        assert AREA_COMMANDS["/perf"] == "performance"
        assert AREA_COMMANDS["/ops"] == "operational"

    def test_alias_commands(self):
        """별칭 커맨드"""
        assert AREA_COMMANDS["/sec"] == "security"
        assert AREA_COMMANDS["/op"] == "operational"

    def test_all_registry_commands_mapped(self):
        """모든 레지스트리 커맨드가 매핑됨"""
        for area in AREA_REGISTRY:
            assert area["command"] in AREA_COMMANDS


class TestAreaKeywords:
    """AREA_KEYWORDS 테스트"""

    def test_security_keywords(self):
        """보안 키워드"""
        assert AREA_KEYWORDS["보안"] == "security"
        assert AREA_KEYWORDS["취약"] == "security"
        assert AREA_KEYWORDS["암호화"] == "security"
        assert AREA_KEYWORDS["퍼블릭"] == "security"

    def test_cost_keywords(self):
        """비용 키워드"""
        assert AREA_KEYWORDS["비용"] == "cost"
        assert AREA_KEYWORDS["미사용"] == "cost"
        assert AREA_KEYWORDS["절감"] == "cost"
        assert AREA_KEYWORDS["유휴"] == "cost"

    def test_fault_tolerance_keywords(self):
        """내결함성 키워드"""
        assert AREA_KEYWORDS["내결함성"] == "fault_tolerance"
        assert AREA_KEYWORDS["가용성"] == "fault_tolerance"
        assert AREA_KEYWORDS["백업"] == "fault_tolerance"
        assert AREA_KEYWORDS["복구"] == "fault_tolerance"

    def test_performance_keywords(self):
        """성능 키워드"""
        assert AREA_KEYWORDS["성능"] == "performance"

    def test_operational_keywords(self):
        """운영 키워드"""
        assert AREA_KEYWORDS["운영"] == "operational"
        assert AREA_KEYWORDS["보고서"] == "operational"
        assert AREA_KEYWORDS["리포트"] == "operational"
        assert AREA_KEYWORDS["현황"] == "operational"


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
