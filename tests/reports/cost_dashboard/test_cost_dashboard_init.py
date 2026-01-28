"""
tests/reports/cost_dashboard/test_cost_dashboard_init.py - Cost Dashboard module structure tests
"""

import pytest

from reports.cost_dashboard import (
    CATEGORY,
    RESOURCE_FIELD_MAP,
    TOOLS,
    WASTE_FIELDS,
    SessionCollectionResult,
    UnusedAllResult,
    UnusedResourceSummary,
)


class TestCostDashboardCategory:
    """Cost Dashboard CATEGORY metadata tests"""

    def test_category_exists(self):
        """CATEGORY should be defined"""
        assert CATEGORY is not None

    def test_category_name(self):
        """CATEGORY should have correct name"""
        assert CATEGORY["name"] == "cost_dashboard"

    def test_category_display_name(self):
        """CATEGORY should have display name"""
        assert CATEGORY["display_name"] == "Cost Dashboard"

    def test_category_has_korean_description(self):
        """CATEGORY should have Korean description"""
        assert "description" in CATEGORY
        assert len(CATEGORY["description"]) > 0
        assert "미사용" in CATEGORY["description"]

    def test_category_has_english_description(self):
        """CATEGORY should have English description"""
        assert "description_en" in CATEGORY
        assert len(CATEGORY["description_en"]) > 0

    def test_category_has_aliases(self):
        """CATEGORY should have aliases"""
        assert "aliases" in CATEGORY
        assert isinstance(CATEGORY["aliases"], list)


class TestCostDashboardTools:
    """Cost Dashboard TOOLS metadata tests"""

    def test_tools_exists(self):
        """TOOLS should be defined"""
        assert TOOLS is not None

    def test_tools_is_list(self):
        """TOOLS should be a list"""
        assert isinstance(TOOLS, list)

    def test_tools_has_one_tool(self):
        """TOOLS should have exactly one comprehensive tool"""
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
        assert tool["name"] == "미사용 리소스 종합 탐지"
        assert tool["name_en"] == "Comprehensive Unused Resources Detection"

    def test_tool_permission(self):
        """Tool should have read permission"""
        tool = TOOLS[0]
        assert tool["permission"] == "read"

    def test_tool_area(self):
        """Tool should be in cost area"""
        tool = TOOLS[0]
        assert tool["area"] == "cost"

    def test_tool_module(self):
        """Tool should reference orchestrator module"""
        tool = TOOLS[0]
        assert tool["module"] == "orchestrator"


class TestResourceFieldMap:
    """RESOURCE_FIELD_MAP tests"""

    def test_field_map_exists(self):
        """RESOURCE_FIELD_MAP should be defined"""
        assert RESOURCE_FIELD_MAP is not None

    def test_field_map_is_dict(self):
        """RESOURCE_FIELD_MAP should be a dictionary"""
        assert isinstance(RESOURCE_FIELD_MAP, dict)

    def test_field_map_not_empty(self):
        """RESOURCE_FIELD_MAP should contain multiple resources"""
        assert len(RESOURCE_FIELD_MAP) > 10

    def test_all_resources_have_required_fields(self):
        """All resources should have required fields"""
        required_fields = ["display", "total", "unused", "data_unused", "session", "final", "data_key"]

        for resource_key, config in RESOURCE_FIELD_MAP.items():
            for field in required_fields:
                assert field in config, f"Resource {resource_key} missing field: {field}"

    def test_all_resources_have_valid_data_key(self):
        """All resources should have valid data_key"""
        valid_data_keys = ["result", "findings"]

        for resource_key, config in RESOURCE_FIELD_MAP.items():
            assert config["data_key"] in valid_data_keys, f"Invalid data_key for {resource_key}"

    def test_compute_resources_present(self):
        """Compute resources should be present"""
        compute_resources = ["ami", "ebs", "snapshot", "eip", "eni", "ec2_instance"]

        for resource in compute_resources:
            assert resource in RESOURCE_FIELD_MAP, f"Missing compute resource: {resource}"

    def test_networking_resources_present(self):
        """Networking resources should be present"""
        networking_resources = ["nat", "endpoint"]

        for resource in networking_resources:
            assert resource in RESOURCE_FIELD_MAP, f"Missing networking resource: {resource}"

    def test_database_resources_present(self):
        """Database resources should be present"""
        database_resources = ["dynamodb", "elasticache", "rds_instance", "rds_snapshot"]

        for resource in database_resources:
            assert resource in RESOURCE_FIELD_MAP, f"Missing database resource: {resource}"

    def test_storage_resources_present(self):
        """Storage resources should be present"""
        storage_resources = ["ecr", "efs", "s3"]

        for resource in storage_resources:
            assert resource in RESOURCE_FIELD_MAP, f"Missing storage resource: {resource}"

    def test_serverless_resources_present(self):
        """Serverless resources should be present"""
        serverless_resources = ["lambda", "apigateway", "eventbridge"]

        for resource in serverless_resources:
            assert resource in RESOURCE_FIELD_MAP, f"Missing serverless resource: {resource}"

    def test_global_resources_marked(self):
        """Global resources should be marked"""
        global_resources = ["s3", "route53"]

        for resource in global_resources:
            if resource in RESOURCE_FIELD_MAP:
                assert RESOURCE_FIELD_MAP[resource].get("is_global") is True


class TestWasteFields:
    """WASTE_FIELDS tests"""

    def test_waste_fields_exists(self):
        """WASTE_FIELDS should be defined"""
        assert WASTE_FIELDS is not None

    def test_waste_fields_is_list(self):
        """WASTE_FIELDS should be a list"""
        assert isinstance(WASTE_FIELDS, list)

    def test_waste_fields_not_empty(self):
        """WASTE_FIELDS should contain waste field names"""
        assert len(WASTE_FIELDS) > 0

    def test_waste_fields_valid(self):
        """All waste fields should be valid field names"""
        for field in WASTE_FIELDS:
            assert isinstance(field, str)
            assert field.endswith("_monthly_waste")


class TestUnusedResourceSummary:
    """UnusedResourceSummary dataclass tests"""

    def test_summary_creation(self):
        """Should create summary with required fields"""
        summary = UnusedResourceSummary(
            account_id="123456789012", account_name="test-account", region="ap-northeast-2"
        )

        assert summary.account_id == "123456789012"
        assert summary.account_name == "test-account"
        assert summary.region == "ap-northeast-2"

    def test_summary_default_values(self):
        """Summary should have default values for all metrics"""
        summary = UnusedResourceSummary(
            account_id="123456789012", account_name="test-account", region="ap-northeast-2"
        )

        # Test a few default values
        assert summary.ebs_total == 0
        assert summary.ebs_unused == 0
        assert summary.ebs_monthly_waste == 0.0
        assert summary.lambda_total == 0
        assert summary.lambda_unused == 0

    def test_summary_with_values(self):
        """Summary should accept custom values"""
        summary = UnusedResourceSummary(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            ebs_total=10,
            ebs_unused=3,
            ebs_monthly_waste=15.50,
        )

        assert summary.ebs_total == 10
        assert summary.ebs_unused == 3
        assert summary.ebs_monthly_waste == 15.50


class TestSessionCollectionResult:
    """SessionCollectionResult dataclass tests"""

    def test_session_result_creation(self):
        """Should create session result with summary"""
        summary = UnusedResourceSummary(
            account_id="123456789012", account_name="test-account", region="ap-northeast-2"
        )
        result = SessionCollectionResult(summary=summary)

        assert result.summary == summary
        assert result.errors == []

    def test_session_result_default_values(self):
        """Session result should have None for all analysis results"""
        summary = UnusedResourceSummary(
            account_id="123456789012", account_name="test-account", region="ap-northeast-2"
        )
        result = SessionCollectionResult(summary=summary)

        assert result.ebs_result is None
        assert result.lambda_result is None
        assert result.dynamodb_result is None

    def test_session_result_with_errors(self):
        """Session result should store errors"""
        summary = UnusedResourceSummary(
            account_id="123456789012", account_name="test-account", region="ap-northeast-2"
        )
        result = SessionCollectionResult(summary=summary, errors=["Error 1", "Error 2"])

        assert len(result.errors) == 2
        assert "Error 1" in result.errors


class TestUnusedAllResult:
    """UnusedAllResult dataclass tests"""

    def test_unused_all_result_creation(self):
        """Should create empty unused all result"""
        result = UnusedAllResult()

        assert result.summaries == []
        assert result.ebs_results == []
        assert result.lambda_results == []

    def test_unused_all_result_with_summaries(self):
        """Should store multiple summaries"""
        summary1 = UnusedResourceSummary(
            account_id="123456789012", account_name="account1", region="ap-northeast-2"
        )
        summary2 = UnusedResourceSummary(
            account_id="123456789012", account_name="account1", region="us-east-1"
        )

        result = UnusedAllResult(summaries=[summary1, summary2])

        assert len(result.summaries) == 2
        assert result.summaries[0].region == "ap-northeast-2"
        assert result.summaries[1].region == "us-east-1"
