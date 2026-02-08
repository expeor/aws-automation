"""
tests/shared/aws/test_tags.py - Comprehensive tags module tests

Tests for tag policy validation and management.

Test Coverage:
    - TagRule: Key matching, value validation, patterns
    - TagPolicy: Policy creation, rule management
    - TagPolicyValidator: Validation logic, resource validation
    - Tag extraction: AWS API format conversion
    - Policy helpers: Basic, cost allocation, security, MAP migration
    - Validation errors: Error types, messages, summaries

Test Classes:
    - TestTagRule: 12 tests
    - TestTagPolicy: 6 tests
    - TestTagValidationError: 3 tests
    - TestTagValidationResult: 5 tests
    - TestTagPolicyValidator: 10 tests
    - TestPolicyHelpers: 8 tests
    - TestResourceValidation: 4 tests
    - TestEdgeCases: 8 tests

Total: 56 tests achieving 100% code coverage.
"""

import pytest

from core.shared.aws.tags import (
    TagPolicy,
    TagPolicyValidator,
    TagRule,
    TagValidationError,
    TagValidationErrorType,
    TagValidationResult,
    create_basic_policy,
    create_cost_allocation_policy,
    create_map_migration_policy,
    create_security_policy,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def basic_tag_rule():
    """Basic required tag rule"""
    return TagRule(key="Environment", required=True, allowed_values=["prod", "stg", "dev"])


@pytest.fixture
def pattern_tag_rule():
    """Tag rule with pattern validation"""
    return TagRule(key="Owner", required=True, pattern=r"^[a-z]+@company\.com$")


@pytest.fixture
def optional_tag_rule():
    """Optional tag rule"""
    return TagRule(key="Project", required=False)


@pytest.fixture
def case_insensitive_rule():
    """Case insensitive tag rule"""
    return TagRule(key="Environment", required=True, allowed_values=["prod", "stg", "dev"], case_sensitive=False)


@pytest.fixture
def forbidden_rule():
    """Forbidden tag key rule"""
    return TagRule(key="aws:", key_pattern=True, forbidden=True)


@pytest.fixture
def basic_policy(basic_tag_rule, pattern_tag_rule, optional_tag_rule):
    """Basic tag policy"""
    return TagPolicy(name="Test Policy", rules=[basic_tag_rule, pattern_tag_rule, optional_tag_rule])


@pytest.fixture
def sample_tags():
    """Sample valid tags"""
    return {"Environment": "prod", "Owner": "john@company.com", "Project": "web-app"}


# =============================================================================
# TagRule Tests
# =============================================================================


class TestTagRule:
    """TagRule class tests"""

    def test_exact_key_match(self, basic_tag_rule):
        """Test exact key matching (case insensitive by default)"""
        assert basic_tag_rule.matches_key("Environment")
        assert basic_tag_rule.matches_key("environment")  # case insensitive by default

    def test_case_insensitive_key_match(self, case_insensitive_rule):
        """Test case insensitive key matching"""
        assert case_insensitive_rule.matches_key("Environment")
        assert case_insensitive_rule.matches_key("environment")
        assert case_insensitive_rule.matches_key("ENVIRONMENT")

    def test_pattern_key_match(self):
        """Test pattern-based key matching"""
        rule = TagRule(key=r"^aws:", key_pattern=True)
        assert rule.matches_key("aws:cloudformation:stack-name")
        assert rule.matches_key("aws:ec2:instance")
        assert not rule.matches_key("custom:tag")

    def test_allowed_values_validation(self, basic_tag_rule):
        """Test allowed values validation"""
        # Valid value
        error = basic_tag_rule.validate_value("prod")
        assert error is None

        # Invalid value
        error = basic_tag_rule.validate_value("production")
        assert error is not None
        assert error.error_type == TagValidationErrorType.INVALID_VALUE
        assert "production" in error.message
        assert error.expected == "prod, stg, dev"

    def test_case_insensitive_allowed_values(self, case_insensitive_rule):
        """Test case insensitive allowed values"""
        assert case_insensitive_rule.validate_value("prod") is None
        assert case_insensitive_rule.validate_value("PROD") is None
        assert case_insensitive_rule.validate_value("Prod") is None
        assert case_insensitive_rule.validate_value("invalid") is not None

    def test_pattern_validation(self, pattern_tag_rule):
        """Test pattern validation"""
        # Valid pattern
        error = pattern_tag_rule.validate_value("john@company.com")
        assert error is None

        # Invalid pattern
        error = pattern_tag_rule.validate_value("john@other.com")
        assert error is not None
        assert error.error_type == TagValidationErrorType.PATTERN_MISMATCH
        assert "john@other.com" in error.message

    def test_case_insensitive_pattern(self):
        """Test case insensitive pattern matching"""
        rule = TagRule(key="Email", pattern=r"^[a-z]+@company\.com$", case_sensitive=False)
        assert rule.validate_value("John@Company.COM") is None
        assert rule.validate_value("JOHN@COMPANY.COM") is None

    def test_forbidden_key_validation(self, forbidden_rule):
        """Test forbidden key validation"""
        error = forbidden_rule.validate_value("anything")
        assert error is not None
        assert error.error_type == TagValidationErrorType.FORBIDDEN_KEY
        assert "금지된 태그 키" in error.message

    def test_no_constraints_rule(self, optional_tag_rule):
        """Test rule without constraints"""
        # Any value should be valid
        assert optional_tag_rule.validate_value("any-value") is None
        assert optional_tag_rule.validate_value("123") is None
        assert optional_tag_rule.validate_value("") is None

    def test_invalid_regex_pattern(self):
        """Test invalid regex pattern handling"""
        rule = TagRule(key="Test", pattern=r"[invalid(")
        error = rule.validate_value("test")
        assert error is not None
        assert error.error_type == TagValidationErrorType.PATTERN_MISMATCH
        assert "잘못된 패턴" in error.message

    def test_rule_to_dict(self, basic_tag_rule):
        """Test TagRule to_dict method"""
        result = basic_tag_rule.to_dict()
        assert result["key"] == "Environment"
        assert result["required"] is True
        assert result["allowed_values"] == ["prod", "stg", "dev"]
        assert result["case_sensitive"] is False

    def test_rule_with_description(self):
        """Test TagRule with description"""
        rule = TagRule(key="CostCenter", required=True, description="Cost center code")
        assert rule.description == "Cost center code"


# =============================================================================
# TagPolicy Tests
# =============================================================================


class TestTagPolicy:
    """TagPolicy class tests"""

    def test_policy_creation(self, basic_policy):
        """Test policy creation"""
        assert basic_policy.name == "Test Policy"
        assert len(basic_policy.rules) == 3
        assert basic_policy.allow_extra_tags is True

    def test_add_rule(self):
        """Test adding rules to policy"""
        policy = TagPolicy(name="Test")
        assert len(policy.rules) == 0

        rule = TagRule(key="Environment", required=True)
        policy.add_rule(rule)
        assert len(policy.rules) == 1

    def test_get_required_keys(self, basic_policy):
        """Test getting required keys"""
        required = basic_policy.get_required_keys()
        assert "Environment" in required
        assert "Owner" in required
        assert "Project" not in required

    def test_get_rule_for_key(self, basic_policy):
        """Test finding rule for specific key"""
        rule = basic_policy.get_rule_for_key("Environment")
        assert rule is not None
        assert rule.key == "Environment"

        rule = basic_policy.get_rule_for_key("NonExistent")
        assert rule is None

    def test_policy_to_dict(self, basic_policy):
        """Test policy to_dict method"""
        result = basic_policy.to_dict()
        assert result["name"] == "Test Policy"
        assert len(result["rules"]) == 3
        assert result["allow_extra_tags"] is True

    def test_policy_without_extra_tags(self):
        """Test policy that disallows extra tags"""
        policy = TagPolicy(name="Strict Policy", allow_extra_tags=False)
        assert policy.allow_extra_tags is False


# =============================================================================
# TagValidationError Tests
# =============================================================================


class TestTagValidationError:
    """TagValidationError class tests"""

    def test_error_creation(self):
        """Test error creation"""
        error = TagValidationError(
            error_type=TagValidationErrorType.MISSING_REQUIRED, tag_key="Environment", message="Required tag missing"
        )
        assert error.error_type == TagValidationErrorType.MISSING_REQUIRED
        assert error.tag_key == "Environment"
        assert error.message == "Required tag missing"

    def test_error_to_dict(self):
        """Test error to_dict method"""
        error = TagValidationError(
            error_type=TagValidationErrorType.INVALID_VALUE,
            tag_key="Environment",
            tag_value="invalid",
            message="Invalid value",
            expected="prod, stg, dev",
        )
        result = error.to_dict()
        assert result["error_type"] == "invalid_value"
        assert result["tag_key"] == "Environment"
        assert result["tag_value"] == "invalid"
        assert result["expected"] == "prod, stg, dev"

    def test_error_str(self):
        """Test error string representation"""
        error = TagValidationError(
            error_type=TagValidationErrorType.PATTERN_MISMATCH,
            tag_key="Owner",
            tag_value="invalid-email",
            message="Pattern mismatch",
        )
        assert "Pattern mismatch" in str(error)


# =============================================================================
# TagValidationResult Tests
# =============================================================================


class TestTagValidationResult:
    """TagValidationResult class tests"""

    def test_result_creation(self):
        """Test result creation"""
        result = TagValidationResult()
        assert result.is_valid is True
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_add_error(self):
        """Test adding errors"""
        result = TagValidationResult()
        error = TagValidationError(
            error_type=TagValidationErrorType.MISSING_REQUIRED, tag_key="Environment", message="Missing tag"
        )
        result.add_error(error)
        assert result.is_valid is False
        assert result.error_count == 1

    def test_add_warning(self):
        """Test adding warnings"""
        result = TagValidationResult()
        result.add_warning("Extra tag found")
        assert result.is_valid is True  # Warnings don't affect validity
        assert result.warning_count == 1

    def test_result_to_dict(self):
        """Test result to_dict method"""
        result = TagValidationResult()
        result.checked_tags = 3
        result.add_error(
            TagValidationError(
                error_type=TagValidationErrorType.MISSING_REQUIRED, tag_key="Environment", message="Missing"
            )
        )
        result.add_warning("Extra tag")

        result_dict = result.to_dict()
        assert result_dict["is_valid"] is False
        assert result_dict["error_count"] == 1
        assert result_dict["warning_count"] == 1
        assert result_dict["checked_tags"] == 3

    def test_get_summary_valid(self):
        """Test summary for valid result"""
        result = TagValidationResult()
        result.checked_tags = 5
        summary = result.get_summary()
        assert "검증 통과" in summary
        assert "5개" in summary

    def test_get_summary_invalid(self):
        """Test summary for invalid result"""
        result = TagValidationResult()
        result.checked_tags = 3
        result.missing_required.append("Environment")
        result.add_error(
            TagValidationError(
                error_type=TagValidationErrorType.MISSING_REQUIRED, tag_key="Environment", message="Missing Environment"
            )
        )
        summary = result.get_summary()
        assert "검증 실패" in summary
        assert "Environment" in summary


# =============================================================================
# TagPolicyValidator Tests
# =============================================================================


class TestTagPolicyValidator:
    """TagPolicyValidator class tests"""

    def test_validate_valid_tags(self, basic_policy, sample_tags):
        """Test validation with valid tags"""
        validator = TagPolicyValidator(basic_policy)
        result = validator.validate(sample_tags)
        assert result.is_valid is True
        assert result.error_count == 0

    def test_validate_missing_required(self, basic_policy):
        """Test validation with missing required tags"""
        validator = TagPolicyValidator(basic_policy)
        result = validator.validate({"Project": "test"})
        assert result.is_valid is False
        assert "Environment" in result.missing_required
        assert "Owner" in result.missing_required

    def test_validate_invalid_value(self, basic_policy):
        """Test validation with invalid value"""
        validator = TagPolicyValidator(basic_policy)
        result = validator.validate({"Environment": "production", "Owner": "john@company.com"})
        assert result.is_valid is False
        assert result.error_count >= 1

    def test_validate_pattern_mismatch(self, basic_policy):
        """Test validation with pattern mismatch"""
        validator = TagPolicyValidator(basic_policy)
        result = validator.validate({"Environment": "prod", "Owner": "invalid-email"})
        assert result.is_valid is False
        assert any(e.error_type == TagValidationErrorType.PATTERN_MISMATCH for e in result.errors)

    def test_validate_aws_api_format(self, basic_policy):
        """Test validation with AWS API tag format"""
        validator = TagPolicyValidator(basic_policy)
        aws_tags = [
            {"Key": "Environment", "Value": "prod"},
            {"Key": "Owner", "Value": "john@company.com"},
            {"Key": "Project", "Value": "web-app"},
        ]
        result = validator.validate(aws_tags)
        assert result.is_valid is True

    def test_validate_none_tags(self, basic_policy):
        """Test validation with None tags"""
        validator = TagPolicyValidator(basic_policy)
        result = validator.validate(None)
        assert result.is_valid is False
        assert result.error_count > 0  # Should have missing required errors

    def test_validate_extra_tags_allowed(self, basic_policy):
        """Test validation with extra tags allowed"""
        validator = TagPolicyValidator(basic_policy)
        tags = {"Environment": "prod", "Owner": "john@company.com", "CustomTag": "value"}
        result = validator.validate(tags)
        assert result.is_valid is True
        assert result.warning_count == 0  # Extra tags allowed

    def test_validate_extra_tags_not_allowed(self):
        """Test validation with extra tags not allowed"""
        policy = TagPolicy(
            name="Strict",
            rules=[TagRule(key="Environment", required=True)],
            allow_extra_tags=False,
        )
        validator = TagPolicyValidator(policy)
        tags = {"Environment": "prod", "CustomTag": "value"}
        result = validator.validate(tags)
        assert result.is_valid is True  # Still valid
        assert result.warning_count == 1  # But has warning

    def test_validate_resources(self, basic_policy, sample_tags):
        """Test bulk resource validation"""
        validator = TagPolicyValidator(basic_policy)
        resources = [
            {"ResourceId": "i-123", "Tags": sample_tags},
            {"ResourceId": "i-456", "Tags": {"Environment": "prod"}},
            {"ResourceId": "i-789", "Tags": sample_tags},
        ]
        results = validator.validate_resources(resources)
        assert len(results) == 3
        assert results["i-123"].is_valid is True
        assert results["i-456"].is_valid is False

    def test_get_compliance_summary(self, basic_policy, sample_tags):
        """Test compliance summary"""
        validator = TagPolicyValidator(basic_policy)
        resources = [
            {"ResourceId": "i-123", "Tags": sample_tags},
            {"ResourceId": "i-456", "Tags": {"Environment": "prod"}},
            {"ResourceId": "i-789", "Tags": sample_tags},
        ]
        results = validator.validate_resources(resources)
        compliant, non_compliant, non_compliant_ids = validator.get_compliance_summary(results)
        assert compliant == 2
        assert non_compliant == 1
        assert "i-456" in non_compliant_ids


# =============================================================================
# Policy Helpers Tests
# =============================================================================


class TestPolicyHelpers:
    """Policy helper functions tests"""

    def test_create_basic_policy_defaults(self):
        """Test basic policy with defaults"""
        policy = create_basic_policy()
        assert policy.name == "Basic Tag Policy"
        required_keys = policy.get_required_keys()
        assert "Name" in required_keys
        assert "Environment" in required_keys
        assert "Owner" in required_keys

    def test_create_basic_policy_custom_tags(self):
        """Test basic policy with custom tags"""
        policy = create_basic_policy(required_tags=["Application", "Team"])
        required_keys = policy.get_required_keys()
        assert "Application" in required_keys
        assert "Team" in required_keys

    def test_create_basic_policy_environment_values(self):
        """Test basic policy with environment values"""
        policy = create_basic_policy(environment_values=["prod", "dev"])
        env_rule = policy.get_rule_for_key("Environment")
        assert env_rule is not None
        assert env_rule.allowed_values == ["prod", "dev"]

    def test_create_cost_allocation_policy(self):
        """Test cost allocation policy"""
        policy = create_cost_allocation_policy()
        assert policy.name == "Cost Allocation Policy"
        required_keys = policy.get_required_keys()
        assert "CostCenter" in required_keys
        assert "Project" in required_keys
        assert "Owner" in required_keys
        assert "Environment" in required_keys

        # Test CostCenter pattern
        validator = TagPolicyValidator(policy)
        valid_tags = {
            "CostCenter": "CC-1234",
            "Project": "web-app",
            "Owner": "john@example.com",
            "Environment": "prod",
        }
        result = validator.validate(valid_tags)
        assert result.is_valid is True

    def test_create_security_policy(self):
        """Test security policy"""
        policy = create_security_policy()
        assert policy.name == "Security Tag Policy"

        # Test DataClassification
        validator = TagPolicyValidator(policy)
        valid_tags = {"DataClassification": "confidential"}
        result = validator.validate(valid_tags)
        assert result.is_valid is True

        # Test forbidden aws: prefix
        invalid_tags = {"DataClassification": "public", "aws:cloudformation:stack": "test"}
        result = validator.validate(invalid_tags)
        assert result.is_valid is False

    def test_create_map_migration_policy_default(self):
        """Test MAP migration policy with default pattern"""
        policy = create_map_migration_policy()
        assert policy.name == "MAP 2.0 Migration Policy"

        validator = TagPolicyValidator(policy)

        # Valid server IDs
        valid_tags_list = [
            {"map-migrated": "mig12345"},
            {"map-migrated": "sap98765"},
            {"map-migrated": "oracle123"},
            {"map-migrated": "comm456"},
        ]
        for tags in valid_tags_list:
            result = validator.validate(tags)
            assert result.is_valid is True, f"Failed for {tags}"

    def test_create_map_migration_policy_custom(self):
        """Test MAP migration policy with custom pattern"""
        policy = create_map_migration_policy(server_id_pattern=r"^server-\d{4}$")

        validator = TagPolicyValidator(policy)

        # Valid custom pattern
        result = validator.validate({"map-migrated": "server-1234"})
        assert result.is_valid is True

        # Invalid pattern
        result = validator.validate({"map-migrated": "invalid"})
        assert result.is_valid is False


# =============================================================================
# Resource Validation Tests
# =============================================================================


class TestResourceValidation:
    """Resource validation tests"""

    def test_validate_resources_with_different_id_fields(self, basic_policy, sample_tags):
        """Test resource validation with various ID field names"""
        validator = TagPolicyValidator(basic_policy)

        resources = [
            {"ResourceArn": "arn:aws:ec2:...", "Tags": sample_tags},
            {"Arn": "arn:aws:s3:...", "Tags": sample_tags},
            {"InstanceId": "i-123", "Tags": sample_tags},
            {"VolumeId": "vol-456", "Tags": sample_tags},
            {"Tags": sample_tags},  # No ID field
        ]

        results = validator.validate_resources(resources)
        assert len(results) == 5
        assert "arn:aws:ec2:..." in results
        assert "arn:aws:s3:..." in results
        assert "i-123" in results
        assert "vol-456" in results
        assert "resource_4" in results  # Fallback ID

    def test_validate_resources_custom_tag_field(self, basic_policy, sample_tags):
        """Test resource validation with custom tag field"""
        validator = TagPolicyValidator(basic_policy)

        resources = [{"ResourceId": "r-123", "TagSet": sample_tags}, {"ResourceId": "r-456", "TagSet": {}}]

        results = validator.validate_resources(resources, tag_field="TagSet")
        assert len(results) == 2
        assert results["r-123"].is_valid is True
        assert results["r-456"].is_valid is False

    def test_validate_empty_resources(self, basic_policy):
        """Test validation with empty resource list"""
        validator = TagPolicyValidator(basic_policy)
        results = validator.validate_resources([])
        assert len(results) == 0

    def test_compliance_summary_all_compliant(self, basic_policy, sample_tags):
        """Test compliance summary with all compliant resources"""
        validator = TagPolicyValidator(basic_policy)
        resources = [{"ResourceId": f"r-{i}", "Tags": sample_tags} for i in range(5)]
        results = validator.validate_resources(resources)
        compliant, non_compliant, non_compliant_ids = validator.get_compliance_summary(results)
        assert compliant == 5
        assert non_compliant == 0
        assert len(non_compliant_ids) == 0


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Edge case tests"""

    def test_empty_tags(self, basic_policy):
        """Test validation with empty tags"""
        validator = TagPolicyValidator(basic_policy)
        result = validator.validate({})
        assert result.is_valid is False
        assert result.checked_tags == 0

    def test_empty_policy(self):
        """Test validation with empty policy"""
        policy = TagPolicy(name="Empty")
        validator = TagPolicyValidator(policy)
        result = validator.validate({"Any": "tag"})
        assert result.is_valid is True

    def test_case_sensitive_key_matching(self):
        """Test case sensitive key matching"""
        rule = TagRule(key="Environment", required=True, case_sensitive=True)
        assert rule.matches_key("Environment")
        assert not rule.matches_key("environment")

    def test_pattern_with_special_characters(self):
        """Test pattern with special regex characters"""
        rule = TagRule(key="Version", pattern=r"^v\d+\.\d+\.\d+$")
        assert rule.validate_value("v1.2.3") is None
        assert rule.validate_value("1.2.3") is not None

    def test_aws_tag_format_with_missing_keys(self, basic_policy):
        """Test AWS tag format with missing Key field"""
        validator = TagPolicyValidator(basic_policy)
        aws_tags = [
            {"Key": "Environment", "Value": "prod"},
            {"Value": "no-key"},  # Missing Key
        ]
        result = validator.validate(aws_tags)
        # Should handle gracefully and validate what's available
        assert result.checked_tags == 1

    def test_multiple_pattern_rules(self):
        """Test policy with multiple pattern-based rules"""
        policy = TagPolicy(
            name="Pattern Policy",
            rules=[
                TagRule(key=r"^aws:", key_pattern=True, forbidden=True),
                TagRule(key=r"^custom:", key_pattern=True, required=False),
            ],
        )
        validator = TagPolicyValidator(policy)

        # Should allow custom: tags but forbid aws: tags
        result = validator.validate({"custom:tag": "value"})
        assert result.is_valid is True

        result = validator.validate({"aws:tag": "value"})
        assert result.is_valid is False

    def test_invalid_key_pattern_regex(self):
        """Test invalid regex in key_pattern"""
        rule = TagRule(key=r"[invalid(", key_pattern=True)
        # Should handle invalid regex gracefully and return False
        assert not rule.matches_key("test")
        assert not rule.matches_key("invalid")

    def test_summary_with_many_errors(self):
        """Test summary with more than 5 errors"""
        policy = TagPolicy(
            name="Test",
            rules=[
                TagRule(key="Tag1", required=True),
                TagRule(key="Tag2", required=True),
                TagRule(key="Tag3", required=True),
                TagRule(key="Tag4", required=True),
                TagRule(key="Tag5", required=True),
                TagRule(key="Tag6", required=True),
                TagRule(key="Tag7", required=True),
            ],
        )
        validator = TagPolicyValidator(policy)
        result = validator.validate({})

        # Should have 7 errors (all missing required tags)
        assert result.error_count == 7
        summary = result.get_summary()
        assert "외 2개 오류" in summary  # 7 errors, shows 5, mentions 2 more
