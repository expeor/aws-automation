"""
tests/reports/ip_search/test_ip_search_init.py - IP search module structure tests
"""

import pytest

from reports.ip_search import CATEGORY, TOOLS


class TestIPSearchCategory:
    """IP Search CATEGORY metadata tests"""

    def test_category_exists(self):
        """CATEGORY should be defined"""
        assert CATEGORY is not None

    def test_category_name(self):
        """CATEGORY should have correct name"""
        assert CATEGORY["name"] == "ip_search"

    def test_category_display_name(self):
        """CATEGORY should have display name"""
        assert CATEGORY["display_name"] == "IP Search"

    def test_category_has_korean_description(self):
        """CATEGORY should have Korean description"""
        assert "description" in CATEGORY
        assert len(CATEGORY["description"]) > 0
        assert "IP" in CATEGORY["description"]

    def test_category_has_english_description(self):
        """CATEGORY should have English description"""
        assert "description_en" in CATEGORY
        assert len(CATEGORY["description_en"]) > 0

    def test_category_has_aliases(self):
        """CATEGORY should have aliases"""
        assert "aliases" in CATEGORY
        assert isinstance(CATEGORY["aliases"], list)
        assert "ip" in CATEGORY["aliases"]
        assert "ipsearch" in CATEGORY["aliases"]


class TestIPSearchTools:
    """IP Search TOOLS metadata tests"""

    def test_tools_exists(self):
        """TOOLS should be defined"""
        assert TOOLS is not None

    def test_tools_is_list(self):
        """TOOLS should be a list"""
        assert isinstance(TOOLS, list)

    def test_tools_has_two_tools(self):
        """TOOLS should have exactly two tools"""
        assert len(TOOLS) == 2

    def test_all_tools_have_required_fields(self):
        """All tools should have all required fields"""
        required_fields = ["name", "name_en", "description", "description_en", "permission", "module", "area"]

        for tool in TOOLS:
            for field in required_fields:
                assert field in tool, f"Tool {tool.get('name', 'unknown')} missing field: {field}"

    def test_public_ip_search_tool(self):
        """Public IP search tool should be present"""
        tool = next((t for t in TOOLS if "Public IP" in t["name"]), None)
        assert tool is not None
        assert tool["name"] == "Public IP 검색"
        assert tool["name_en"] == "Public IP Search"
        assert "AWS" in tool["description"]
        assert "GCP" in tool["description"]
        assert tool["permission"] == "read"
        assert tool["area"] == "search"
        assert tool["module"] == "public_ip.tool"

    def test_private_ip_search_tool(self):
        """Private IP search tool should be present"""
        tool = next((t for t in TOOLS if "Private IP" in t["name"]), None)
        assert tool is not None
        assert tool["name"] == "Private IP 검색"
        assert tool["name_en"] == "Private IP Search"
        assert "ENI" in tool["description"]
        assert tool["permission"] == "read"
        assert tool["area"] == "search"
        assert tool["module"] == "private_ip.tool"
