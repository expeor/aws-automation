"""
tests/reports/inventory/test_inventory_init.py - Inventory module structure tests
"""

import pytest

from reports.inventory import CATEGORY, TOOLS


class TestInventoryCategory:
    """Inventory CATEGORY metadata tests"""

    def test_category_exists(self):
        """CATEGORY should be defined"""
        assert CATEGORY is not None

    def test_category_name(self):
        """CATEGORY should have correct name"""
        assert CATEGORY["name"] == "inventory"

    def test_category_display_name(self):
        """CATEGORY should have display name"""
        assert CATEGORY["display_name"] == "Resource Inventory"

    def test_category_has_korean_description(self):
        """CATEGORY should have Korean description"""
        assert "description" in CATEGORY
        assert len(CATEGORY["description"]) > 0
        assert "인벤토리" in CATEGORY["description"]

    def test_category_has_english_description(self):
        """CATEGORY should have English description"""
        assert "description_en" in CATEGORY
        assert len(CATEGORY["description_en"]) > 0

    def test_category_has_aliases(self):
        """CATEGORY should have aliases"""
        assert "aliases" in CATEGORY
        assert isinstance(CATEGORY["aliases"], list)
        assert "resource_explorer" in CATEGORY["aliases"]
        assert "cmdb" in CATEGORY["aliases"]


class TestInventoryTools:
    """Inventory TOOLS metadata tests"""

    def test_tools_exists(self):
        """TOOLS should be defined"""
        assert TOOLS is not None

    def test_tools_is_list(self):
        """TOOLS should be a list"""
        assert isinstance(TOOLS, list)

    def test_tools_has_one_tool(self):
        """TOOLS should have exactly one tool"""
        assert len(TOOLS) == 1

    def test_tool_has_required_fields(self):
        """Tool should have all required fields"""
        tool = TOOLS[0]
        required_fields = ["name", "name_en", "description", "description_en", "permission", "module", "area"]

        for field in required_fields:
            assert field in tool, f"Missing field: {field}"

    def test_tool_name(self):
        """Tool should have correct name"""
        tool = TOOLS[0]
        assert tool["name"] == "종합 인벤토리"
        assert tool["name_en"] == "Comprehensive Inventory"

    def test_tool_description(self):
        """Tool should have description"""
        tool = TOOLS[0]
        assert "EC2" in tool["description"]
        assert "VPC" in tool["description"]
        assert "ELB" in tool["description"]

    def test_tool_permission(self):
        """Tool should have read permission"""
        tool = TOOLS[0]
        assert tool["permission"] == "read"

    def test_tool_area(self):
        """Tool should be in inventory area"""
        tool = TOOLS[0]
        assert tool["area"] == "inventory"

    def test_tool_module(self):
        """Tool should reference inventory module"""
        tool = TOOLS[0]
        assert tool["module"] == "inventory"
