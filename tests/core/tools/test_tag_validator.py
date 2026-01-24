"""
tests/core/tools/test_tag_validator.py - 태그 정책 검증 테스트
"""

from core.tools.tag_validator import (
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


class TestTagValidationErrorType:
    """TagValidationErrorType 테스트"""

    def test_enum_values(self):
        """Enum 값 확인"""
        assert TagValidationErrorType.MISSING_REQUIRED.value == "missing_required"
        assert TagValidationErrorType.INVALID_VALUE.value == "invalid_value"
        assert TagValidationErrorType.PATTERN_MISMATCH.value == "pattern_mismatch"
        assert TagValidationErrorType.FORBIDDEN_KEY.value == "forbidden_key"


class TestTagValidationError:
    """TagValidationError 테스트"""

    def test_basic_creation(self):
        """기본 생성"""
        error = TagValidationError(
            error_type=TagValidationErrorType.MISSING_REQUIRED,
            tag_key="Environment",
            message="필수 태그 누락",
        )

        assert error.error_type == TagValidationErrorType.MISSING_REQUIRED
        assert error.tag_key == "Environment"
        assert "필수" in error.message

    def test_to_dict(self):
        """딕셔너리 변환"""
        error = TagValidationError(
            error_type=TagValidationErrorType.INVALID_VALUE,
            tag_key="Environment",
            tag_value="invalid",
            message="허용되지 않는 값",
            expected="prod, stg, dev",
        )

        d = error.to_dict()

        assert d["error_type"] == "invalid_value"
        assert d["tag_key"] == "Environment"
        assert d["tag_value"] == "invalid"

    def test_str(self):
        """문자열 변환"""
        error = TagValidationError(
            error_type=TagValidationErrorType.MISSING_REQUIRED,
            tag_key="Environment",
            message="필수 태그 누락",
        )

        assert "필수 태그 누락" in str(error)


class TestTagRule:
    """TagRule 테스트"""

    def test_basic_creation(self):
        """기본 생성"""
        rule = TagRule(key="Environment", required=True)

        assert rule.key == "Environment"
        assert rule.required is True
        assert rule.allowed_values is None

    def test_matches_key_exact(self):
        """정확한 키 매칭"""
        rule = TagRule(key="Environment")

        assert rule.matches_key("Environment") is True
        assert rule.matches_key("environment") is True  # 대소문자 무시
        assert rule.matches_key("Env") is False

    def test_matches_key_case_sensitive(self):
        """대소문자 구분 매칭"""
        rule = TagRule(key="Environment", case_sensitive=True)

        assert rule.matches_key("Environment") is True
        assert rule.matches_key("environment") is False

    def test_matches_key_pattern(self):
        """패턴 매칭"""
        rule = TagRule(key=r"^aws:", key_pattern=True)

        assert rule.matches_key("aws:autoscaling") is True
        assert rule.matches_key("aws:ec2") is True
        assert rule.matches_key("myapp:env") is False

    def test_validate_value_allowed(self):
        """허용 값 검증"""
        rule = TagRule(key="Environment", allowed_values=["prod", "stg", "dev"])

        assert rule.validate_value("prod") is None
        assert rule.validate_value("stg") is None

        error = rule.validate_value("invalid")
        assert error is not None
        assert error.error_type == TagValidationErrorType.INVALID_VALUE

    def test_validate_value_pattern(self):
        """패턴 검증"""
        rule = TagRule(key="CostCenter", pattern=r"^CC-\d{4}$")

        assert rule.validate_value("CC-1234") is None
        assert rule.validate_value("CC-5678") is None

        error = rule.validate_value("CC-12")
        assert error is not None
        assert error.error_type == TagValidationErrorType.PATTERN_MISMATCH

    def test_forbidden_key(self):
        """금지된 키 검증"""
        rule = TagRule(key="secret", forbidden=True)

        error = rule.validate_value("anything")
        assert error is not None
        assert error.error_type == TagValidationErrorType.FORBIDDEN_KEY


class TestTagPolicy:
    """TagPolicy 테스트"""

    def test_basic_creation(self):
        """기본 생성"""
        policy = TagPolicy(name="Test Policy")

        assert policy.name == "Test Policy"
        assert len(policy.rules) == 0

    def test_add_rule(self):
        """규칙 추가"""
        policy = TagPolicy(name="Test Policy")
        policy.add_rule(TagRule(key="Environment", required=True))
        policy.add_rule(TagRule(key="Owner"))

        assert len(policy.rules) == 2

    def test_get_required_keys(self):
        """필수 키 조회"""
        policy = TagPolicy(
            name="Test Policy",
            rules=[
                TagRule(key="Environment", required=True),
                TagRule(key="Owner", required=True),
                TagRule(key="Project", required=False),
            ],
        )

        required = policy.get_required_keys()

        assert "Environment" in required
        assert "Owner" in required
        assert "Project" not in required

    def test_get_rule_for_key(self):
        """키에 해당하는 규칙 조회"""
        policy = TagPolicy(
            name="Test Policy",
            rules=[
                TagRule(key="Environment"),
                TagRule(key="Owner"),
            ],
        )

        rule = policy.get_rule_for_key("Environment")
        assert rule is not None
        assert rule.key == "Environment"

        rule = policy.get_rule_for_key("Unknown")
        assert rule is None


class TestTagValidationResult:
    """TagValidationResult 테스트"""

    def test_default_valid(self):
        """기본 상태는 유효"""
        result = TagValidationResult()

        assert result.is_valid is True
        assert result.error_count == 0

    def test_add_error(self):
        """오류 추가"""
        result = TagValidationResult()
        result.add_error(
            TagValidationError(
                error_type=TagValidationErrorType.MISSING_REQUIRED,
                tag_key="Environment",
            )
        )

        assert result.is_valid is False
        assert result.error_count == 1

    def test_add_warning(self):
        """경고 추가"""
        result = TagValidationResult()
        result.add_warning("정의되지 않은 태그: CustomTag")

        assert result.is_valid is True  # 경고는 유효성에 영향 없음
        assert result.warning_count == 1

    def test_get_summary_valid(self):
        """유효한 결과 요약"""
        result = TagValidationResult(checked_tags=5)

        summary = result.get_summary()
        assert "검증 통과" in summary

    def test_get_summary_invalid(self):
        """유효하지 않은 결과 요약"""
        result = TagValidationResult()
        result.add_error(
            TagValidationError(
                error_type=TagValidationErrorType.MISSING_REQUIRED,
                tag_key="Environment",
                message="필수 태그 누락: Environment",
            )
        )

        summary = result.get_summary()
        assert "검증 실패" in summary


class TestTagPolicyValidator:
    """TagPolicyValidator 테스트"""

    def test_validate_empty_tags(self):
        """빈 태그 검증"""
        policy = TagPolicy(
            name="Test",
            rules=[TagRule(key="Environment", required=True)],
        )
        validator = TagPolicyValidator(policy)

        result = validator.validate({})

        assert result.is_valid is False
        assert "Environment" in result.missing_required

    def test_validate_valid_tags(self):
        """유효한 태그 검증"""
        policy = TagPolicy(
            name="Test",
            rules=[
                TagRule(key="Environment", required=True, allowed_values=["prod", "dev"]),
                TagRule(key="Owner", required=True),
            ],
        )
        validator = TagPolicyValidator(policy)

        result = validator.validate({"Environment": "prod", "Owner": "team-a"})

        assert result.is_valid is True
        assert result.error_count == 0

    def test_validate_invalid_value(self):
        """유효하지 않은 값 검증"""
        policy = TagPolicy(
            name="Test",
            rules=[
                TagRule(key="Environment", required=True, allowed_values=["prod", "dev"]),
            ],
        )
        validator = TagPolicyValidator(policy)

        result = validator.validate({"Environment": "invalid"})

        assert result.is_valid is False
        assert any(e.error_type == TagValidationErrorType.INVALID_VALUE for e in result.errors)

    def test_validate_aws_api_format(self):
        """AWS API 형식 태그 검증 [{"Key": ..., "Value": ...}]"""
        policy = TagPolicy(
            name="Test",
            rules=[TagRule(key="Environment", required=True)],
        )
        validator = TagPolicyValidator(policy)

        tags = [
            {"Key": "Environment", "Value": "prod"},
            {"Key": "Owner", "Value": "team-a"},
        ]

        result = validator.validate(tags)

        assert result.is_valid is True
        assert result.checked_tags == 2

    def test_validate_resources(self):
        """여러 리소스 일괄 검증"""
        policy = TagPolicy(
            name="Test",
            rules=[TagRule(key="Environment", required=True)],
        )
        validator = TagPolicyValidator(policy)

        resources = [
            {"Id": "res-1", "Tags": {"Environment": "prod"}},
            {"Id": "res-2", "Tags": {}},
            {"Id": "res-3", "Tags": {"Environment": "dev"}},
        ]

        results = validator.validate_resources(resources)

        assert len(results) == 3
        assert results["res-1"].is_valid is True
        assert results["res-2"].is_valid is False
        assert results["res-3"].is_valid is True

    def test_get_compliance_summary(self):
        """준수율 요약"""
        policy = TagPolicy(
            name="Test",
            rules=[TagRule(key="Environment", required=True)],
        )
        validator = TagPolicyValidator(policy)

        results = {
            "res-1": TagValidationResult(is_valid=True),
            "res-2": TagValidationResult(is_valid=False),
            "res-3": TagValidationResult(is_valid=True),
        }

        compliant, non_compliant, ids = validator.get_compliance_summary(results)

        assert compliant == 2
        assert non_compliant == 1
        assert "res-2" in ids


class TestPredefinedPolicies:
    """사전 정의된 정책 테스트"""

    def test_create_basic_policy(self):
        """기본 정책 생성"""
        policy = create_basic_policy()

        assert policy.name == "Basic Tag Policy"
        required = policy.get_required_keys()
        assert "Name" in required
        assert "Environment" in required
        assert "Owner" in required

    def test_create_basic_policy_custom(self):
        """커스텀 기본 정책"""
        policy = create_basic_policy(
            required_tags=["Project", "Team"],
            environment_values=["prod", "stg"],
        )

        required = policy.get_required_keys()
        assert "Project" in required
        assert "Team" in required

    def test_create_cost_allocation_policy(self):
        """비용 할당 정책 생성"""
        policy = create_cost_allocation_policy()

        assert policy.name == "Cost Allocation Policy"
        required = policy.get_required_keys()
        assert "CostCenter" in required
        assert "Project" in required
        assert "Owner" in required

    def test_create_security_policy(self):
        """보안 정책 생성"""
        policy = create_security_policy()

        assert policy.name == "Security Tag Policy"

        # aws: 접두사 금지 규칙 확인
        rule = policy.get_rule_for_key("aws:test")
        assert rule is not None
        assert rule.forbidden is True

    def test_create_map_migration_policy(self):
        """MAP 마이그레이션 정책 생성"""
        policy = create_map_migration_policy()

        assert policy.name == "MAP 2.0 Migration Policy"
        required = policy.get_required_keys()
        assert "map-migrated" in required

    def test_map_policy_validation(self):
        """MAP 정책 검증"""
        policy = create_map_migration_policy()
        validator = TagPolicyValidator(policy)

        # 유효한 값
        result = validator.validate({"map-migrated": "mig12345"})
        assert result.is_valid is True

        result = validator.validate({"map-migrated": "sapABCDE12345"})
        assert result.is_valid is True

        # 유효하지 않은 값
        result = validator.validate({"map-migrated": "invalid"})
        assert result.is_valid is False
