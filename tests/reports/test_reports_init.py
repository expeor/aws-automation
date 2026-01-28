"""
tests/reports/test_reports_init.py - Reports module structure tests

Tests for the main reports module initialization and metadata.
"""

import pytest

from reports import CATEGORY, TOOLS


class TestReportsCategory:
    """Reports CATEGORY metadata tests"""

    def test_category_exists(self):
        """CATEGORY should be defined"""
        assert CATEGORY is not None

    def test_category_name(self):
        """CATEGORY should have correct name"""
        assert CATEGORY["name"] == "report"

    def test_category_display_name(self):
        """CATEGORY should have display name"""
        assert CATEGORY["display_name"] == "Reports"

    def test_category_has_korean_description(self):
        """CATEGORY should have Korean description"""
        assert "description" in CATEGORY
        assert len(CATEGORY["description"]) > 0

    def test_category_has_english_description(self):
        """CATEGORY should have English description"""
        assert "description_en" in CATEGORY
        assert len(CATEGORY["description_en"]) > 0

    def test_category_has_aliases(self):
        """CATEGORY should have aliases"""
        assert "aliases" in CATEGORY
        assert isinstance(CATEGORY["aliases"], list)
        assert "reports" in CATEGORY["aliases"]
        assert "rpt" in CATEGORY["aliases"]


class TestReportsTools:
    """Reports TOOLS metadata tests"""

    def test_tools_exists(self):
        """TOOLS should be defined"""
        assert TOOLS is not None

    def test_tools_is_list(self):
        """TOOLS should be a list"""
        assert isinstance(TOOLS, list)

    def test_tools_not_empty(self):
        """TOOLS should contain at least one tool"""
        assert len(TOOLS) > 0

    def test_all_tools_have_required_fields(self):
        """All tools should have required fields"""
        required_fields = ["name", "name_en", "description", "description_en", "permission", "area"]

        for tool in TOOLS:
            for field in required_fields:
                assert field in tool, f"Tool {tool.get('name', 'unknown')} missing field: {field}"

    def test_all_tools_have_valid_permission(self):
        """All tools should have valid permission"""
        valid_permissions = ["read", "write"]

        for tool in TOOLS:
            assert tool["permission"] in valid_permissions, f"Invalid permission: {tool['permission']}"

    def test_all_tools_have_valid_area(self):
        """All tools should have valid area"""
        valid_areas = ["cost", "inventory", "search", "log"]

        for tool in TOOLS:
            assert tool["area"] in valid_areas, f"Invalid area: {tool['area']}"

    def test_unused_resources_dashboard_tool(self):
        """Unused resources dashboard tool should be present"""
        tool = next((t for t in TOOLS if "미사용 리소스" in t["name"]), None)
        assert tool is not None
        assert tool["name"] == "미사용 리소스 종합"
        assert tool["name_en"] == "Unused Resources Dashboard"
        assert tool["permission"] == "read"
        assert tool["area"] == "cost"
        assert "ref" in tool
        assert tool["ref"] == "cost_dashboard/orchestrator"

    def test_inventory_tool(self):
        """Inventory tool should be present"""
        tool = next((t for t in TOOLS if "인벤토리" in t["name"]), None)
        assert tool is not None
        assert tool["name"] == "리소스 인벤토리"
        assert tool["name_en"] == "Resource Inventory"
        assert tool["permission"] == "read"
        assert tool["area"] == "inventory"
        assert "ref" in tool
        assert tool["ref"] == "inventory/inventory"

    def test_public_ip_search_tool(self):
        """Public IP search tool should be present"""
        tool = next((t for t in TOOLS if "Public IP" in t["name"]), None)
        assert tool is not None
        assert tool["name"] == "Public IP 검색"
        assert tool["name_en"] == "Public IP Search"
        assert tool["permission"] == "read"
        assert tool["area"] == "search"
        assert "ref" in tool
        assert tool["ref"] == "ip_search/public_ip.tool"

    def test_private_ip_search_tool(self):
        """Private IP search tool should be present"""
        tool = next((t for t in TOOLS if "Private IP" in t["name"]), None)
        assert tool is not None
        assert tool["name"] == "Private IP 검색"
        assert tool["name_en"] == "Private IP Search"
        assert tool["permission"] == "read"
        assert tool["area"] == "search"
        assert "ref" in tool
        assert tool["ref"] == "ip_search/private_ip.tool"

    def test_alb_log_analyzer_tool(self):
        """ALB log analyzer tool should be present"""
        tool = next((t for t in TOOLS if "ALB" in t.get("name_en", "")), None)
        assert tool is not None
        assert tool["name_en"] == "ALB Log Analysis"
        assert tool["permission"] == "read"
        assert tool["area"] == "log"
        assert "ref" in tool
        # Note: ref points to elb/alb_log, not log_analyzer/alb_log_analyzer
        assert tool["ref"] == "elb/alb_log"
        assert tool.get("single_region_only") is True

    def test_scheduled_operations_tool(self):
        """Scheduled operations tool should be present"""
        tool = next((t for t in TOOLS if "Scheduled Operations" in t["name_en"]), None)
        assert tool is not None
        assert tool["name_en"] == "Scheduled Operations"
        assert tool["permission"] == "read"
        # Note: area changed from "operational" to "inventory" in reports/__init__.py
        assert tool["area"] == "inventory"
        assert "module" in tool
        assert tool["module"] == "_scheduled_menu"
        assert tool.get("is_menu") is True


class TestReportsToolsCount:
    """Test that we have the expected number of tools"""

    def test_tool_count(self):
        """Should have at least 6 tools"""
        assert len(TOOLS) >= 6

    def test_no_duplicate_tool_names(self):
        """Tool names should be unique"""
        names = [tool["name"] for tool in TOOLS]
        assert len(names) == len(set(names))

    def test_no_duplicate_english_names(self):
        """English tool names should be unique"""
        names_en = [tool["name_en"] for tool in TOOLS]
        assert len(names_en) == len(set(names_en))
