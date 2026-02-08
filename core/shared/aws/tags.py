"""
shared/aws/tags.py - 태그 정책 검증

AWS 리소스 태그의 정책 준수 여부를 검증합니다.

Usage:
    from core.shared.aws.tags import TagPolicyValidator, TagPolicy, TagRule

    # 정책 정의
    policy = TagPolicy(
        name="Production Policy",
        rules=[
            TagRule(key="Environment", required=True, allowed_values=["prod", "stg", "dev"]),
            TagRule(key="Owner", required=True, pattern=r"^[a-z]+@company\\.com$"),
            TagRule(key="CostCenter", required=True, pattern=r"^CC-\\d{4}$"),
            TagRule(key="Project", required=False),
        ]
    )

    # 검증기 생성
    validator = TagPolicyValidator(policy)

    # 리소스 태그 검증
    tags = {"Environment": "prod", "Owner": "john@company.com"}
    result = validator.validate(tags)

    if not result.is_valid:
        for error in result.errors:
            print(f"오류: {error}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TagValidationErrorType(Enum):
    """태그 검증 오류 유형"""

    MISSING_REQUIRED = "missing_required"  # 필수 태그 누락
    INVALID_VALUE = "invalid_value"  # 허용되지 않는 값
    PATTERN_MISMATCH = "pattern_mismatch"  # 패턴 불일치
    KEY_FORMAT_ERROR = "key_format_error"  # 키 형식 오류
    VALUE_FORMAT_ERROR = "value_format_error"  # 값 형식 오류
    FORBIDDEN_KEY = "forbidden_key"  # 금지된 키


@dataclass
class TagValidationError:
    """태그 검증 오류

    Attributes:
        error_type: 오류 유형
        tag_key: 태그 키
        tag_value: 태그 값 (있는 경우)
        message: 오류 메시지
        expected: 기대값 (있는 경우)
    """

    error_type: TagValidationErrorType
    tag_key: str
    tag_value: str | None = None
    message: str = ""
    expected: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.error_type.value,
            "tag_key": self.tag_key,
            "tag_value": self.tag_value,
            "message": self.message,
            "expected": self.expected,
        }

    def __str__(self) -> str:
        return self.message or f"[{self.error_type.value}] {self.tag_key}: {self.tag_value}"


@dataclass
class TagRule:
    """태그 규칙

    Attributes:
        key: 태그 키 (정확히 일치) 또는 키 패턴
        required: 필수 여부
        allowed_values: 허용된 값 목록 (None이면 모든 값 허용)
        pattern: 값 정규식 패턴 (None이면 패턴 검사 안 함)
        case_sensitive: 값 비교 시 대소문자 구분
        description: 규칙 설명
        key_pattern: True이면 key를 정규식 패턴으로 사용
        forbidden: True이면 이 키가 있으면 오류
    """

    key: str
    required: bool = False
    allowed_values: list[str] | None = None
    pattern: str | None = None
    case_sensitive: bool = False
    description: str = ""
    key_pattern: bool = False
    forbidden: bool = False

    def matches_key(self, tag_key: str) -> bool:
        """태그 키가 이 규칙과 일치하는지 확인"""
        if self.key_pattern:
            try:
                return bool(re.match(self.key, tag_key, re.IGNORECASE if not self.case_sensitive else 0))
            except re.error:
                return False
        else:
            if self.case_sensitive:
                return tag_key == self.key
            return tag_key.lower() == self.key.lower()

    def validate_value(self, value: str) -> TagValidationError | None:
        """태그 값이 규칙을 만족하는지 검증"""
        # 금지된 키인 경우
        if self.forbidden:
            return TagValidationError(
                error_type=TagValidationErrorType.FORBIDDEN_KEY,
                tag_key=self.key,
                tag_value=value,
                message=f"금지된 태그 키: {self.key}",
            )

        # 허용 값 목록 확인
        if self.allowed_values is not None:
            compare_value = value if self.case_sensitive else value.lower()
            compare_allowed = self.allowed_values if self.case_sensitive else [v.lower() for v in self.allowed_values]

            if compare_value not in compare_allowed:
                return TagValidationError(
                    error_type=TagValidationErrorType.INVALID_VALUE,
                    tag_key=self.key,
                    tag_value=value,
                    message=f"'{self.key}' 값 '{value}'은(는) 허용되지 않음. 허용 값: {self.allowed_values}",
                    expected=", ".join(self.allowed_values),
                )

        # 패턴 확인
        if self.pattern is not None:
            try:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                if not re.match(self.pattern, value, flags):
                    return TagValidationError(
                        error_type=TagValidationErrorType.PATTERN_MISMATCH,
                        tag_key=self.key,
                        tag_value=value,
                        message=f"'{self.key}' 값 '{value}'이(가) 패턴과 불일치: {self.pattern}",
                        expected=self.pattern,
                    )
            except re.error as e:
                return TagValidationError(
                    error_type=TagValidationErrorType.PATTERN_MISMATCH,
                    tag_key=self.key,
                    tag_value=value,
                    message=f"잘못된 패턴: {self.pattern} - {e}",
                )

        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "required": self.required,
            "allowed_values": self.allowed_values,
            "pattern": self.pattern,
            "case_sensitive": self.case_sensitive,
            "description": self.description,
            "key_pattern": self.key_pattern,
            "forbidden": self.forbidden,
        }


@dataclass
class TagPolicy:
    """태그 정책

    여러 규칙을 조합한 태그 정책입니다.

    Attributes:
        name: 정책 이름
        rules: 태그 규칙 목록
        description: 정책 설명
        allow_extra_tags: 규칙에 정의되지 않은 추가 태그 허용 여부
    """

    name: str
    rules: list[TagRule] = field(default_factory=list)
    description: str = ""
    allow_extra_tags: bool = True

    def add_rule(self, rule: TagRule) -> None:
        """규칙 추가"""
        self.rules.append(rule)

    def get_required_keys(self) -> list[str]:
        """필수 태그 키 목록"""
        return [r.key for r in self.rules if r.required and not r.key_pattern]

    def get_rule_for_key(self, tag_key: str) -> TagRule | None:
        """특정 키에 해당하는 규칙 조회"""
        for rule in self.rules:
            if rule.matches_key(tag_key):
                return rule
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "rules": [r.to_dict() for r in self.rules],
            "allow_extra_tags": self.allow_extra_tags,
        }


@dataclass
class TagValidationResult:
    """태그 검증 결과

    Attributes:
        is_valid: 검증 통과 여부
        errors: 오류 목록
        warnings: 경고 목록
        checked_tags: 검사된 태그 수
        missing_required: 누락된 필수 태그 키 목록
    """

    is_valid: bool = True
    errors: list[TagValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_tags: int = 0
    missing_required: list[str] = field(default_factory=list)

    def add_error(self, error: TagValidationError) -> None:
        """오류 추가"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """경고 추가"""
        self.warnings.append(warning)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "checked_tags": self.checked_tags,
            "missing_required": self.missing_required,
        }

    def get_summary(self) -> str:
        """검증 결과 요약"""
        if self.is_valid:
            return f"✓ 검증 통과 (태그 {self.checked_tags}개 확인)"

        lines = [f"✗ 검증 실패 (오류 {self.error_count}개)"]

        if self.missing_required:
            lines.append(f"  - 누락된 필수 태그: {', '.join(self.missing_required)}")

        for error in self.errors[:5]:  # 최대 5개만 표시
            lines.append(f"  - {error.message}")

        if self.error_count > 5:
            lines.append(f"  ... 외 {self.error_count - 5}개 오류")

        return "\n".join(lines)


@dataclass
class TagPolicyValidator:
    """태그 정책 검증기

    Example:
        policy = TagPolicy(
            name="Standard Tags",
            rules=[
                TagRule(key="Environment", required=True, allowed_values=["prod", "stg", "dev"]),
                TagRule(key="Owner", required=True),
            ]
        )

        validator = TagPolicyValidator(policy)
        result = validator.validate({"Environment": "prod"})

        if not result.is_valid:
            print(result.get_summary())
    """

    policy: TagPolicy

    def validate(self, tags: dict[str, str] | list[dict[str, str]] | None) -> TagValidationResult:
        """태그 검증

        Args:
            tags: 검증할 태그 딕셔너리 또는 [{"Key": ..., "Value": ...}] 형식

        Returns:
            TagValidationResult
        """
        result = TagValidationResult()

        # None 처리
        if tags is None:
            tags = {}

        # AWS API 형식 변환 [{"Key": ..., "Value": ...}] -> {key: value}
        if isinstance(tags, list):
            tags = {t.get("Key", ""): t.get("Value", "") for t in tags if "Key" in t}

        result.checked_tags = len(tags)

        # 1. 필수 태그 확인
        for rule in self.policy.rules:
            if rule.required and not rule.key_pattern:
                found = False
                for tag_key in tags:
                    if rule.matches_key(tag_key):
                        found = True
                        break

                if not found:
                    result.missing_required.append(rule.key)
                    result.add_error(
                        TagValidationError(
                            error_type=TagValidationErrorType.MISSING_REQUIRED,
                            tag_key=rule.key,
                            message=f"필수 태그 누락: {rule.key}",
                        )
                    )

        # 2. 각 태그 값 검증
        for tag_key, tag_value in tags.items():
            matching_rule = self.policy.get_rule_for_key(tag_key)

            if matching_rule:
                error = matching_rule.validate_value(tag_value)
                if error:
                    result.add_error(error)
            elif not self.policy.allow_extra_tags:
                result.add_warning(f"정의되지 않은 태그: {tag_key}")

        return result

    def validate_resources(
        self, resources: list[dict[str, Any]], tag_field: str = "Tags"
    ) -> dict[str, TagValidationResult]:
        """여러 리소스의 태그 일괄 검증

        Args:
            resources: 리소스 목록 (각 리소스는 딕셔너리)
            tag_field: 태그가 저장된 필드명

        Returns:
            {리소스 식별자: TagValidationResult} 딕셔너리
        """
        results: dict[str, TagValidationResult] = {}

        for i, resource in enumerate(resources):
            # 리소스 식별자 찾기
            resource_id = (
                resource.get("ResourceArn")
                or resource.get("Arn")
                or resource.get("ResourceId")
                or resource.get("Id")
                or resource.get("InstanceId")
                or resource.get("VolumeId")
                or f"resource_{i}"
            )

            tags = resource.get(tag_field, {})
            results[resource_id] = self.validate(tags)

        return results

    def get_compliance_summary(self, results: dict[str, TagValidationResult]) -> tuple[int, int, list[str]]:
        """준수율 요약

        Args:
            results: validate_resources 결과

        Returns:
            (준수 리소스 수, 미준수 리소스 수, 미준수 리소스 ID 목록)
        """
        compliant = 0
        non_compliant = 0
        non_compliant_ids = []

        for resource_id, result in results.items():
            if result.is_valid:
                compliant += 1
            else:
                non_compliant += 1
                non_compliant_ids.append(resource_id)

        return compliant, non_compliant, non_compliant_ids


# =============================================================================
# 사전 정의된 정책
# =============================================================================


def create_basic_policy(
    required_tags: list[str] | None = None,
    environment_values: list[str] | None = None,
) -> TagPolicy:
    """기본 태그 정책 생성

    Args:
        required_tags: 필수 태그 키 목록
        environment_values: Environment 태그 허용 값

    Returns:
        TagPolicy
    """
    rules = []

    # 기본 필수 태그
    default_required = required_tags or ["Name", "Environment", "Owner"]

    for key in default_required:
        rule = TagRule(key=key, required=True)

        # Environment 태그 특수 처리
        if key.lower() == "environment" and environment_values:
            rule.allowed_values = environment_values

        rules.append(rule)

    return TagPolicy(
        name="Basic Tag Policy",
        description="기본 태그 정책",
        rules=rules,
    )


def create_cost_allocation_policy() -> TagPolicy:
    """비용 할당 태그 정책 생성"""
    return TagPolicy(
        name="Cost Allocation Policy",
        description="비용 할당 태그 정책",
        rules=[
            TagRule(
                key="CostCenter",
                required=True,
                pattern=r"^CC-\d{4,6}$",
                description="비용 센터 코드 (CC-XXXX 형식)",
            ),
            TagRule(
                key="Project",
                required=True,
                description="프로젝트명",
            ),
            TagRule(
                key="Owner",
                required=True,
                pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                description="소유자 이메일",
            ),
            TagRule(
                key="Environment",
                required=True,
                allowed_values=["prod", "stg", "dev", "test", "sandbox"],
                case_sensitive=False,
            ),
        ],
    )


def create_security_policy() -> TagPolicy:
    """보안 태그 정책 생성"""
    return TagPolicy(
        name="Security Tag Policy",
        description="보안 태그 정책",
        rules=[
            TagRule(
                key="DataClassification",
                required=True,
                allowed_values=["public", "internal", "confidential", "restricted"],
                case_sensitive=False,
                description="데이터 분류",
            ),
            TagRule(
                key="Compliance",
                required=False,
                allowed_values=["pci", "hipaa", "sox", "gdpr", "none"],
                case_sensitive=False,
                description="규정 준수 요구사항",
            ),
            # aws: 접두사 태그 금지
            TagRule(
                key=r"^aws:",
                key_pattern=True,
                forbidden=True,
                description="AWS 예약 태그 사용 금지",
            ),
        ],
    )


def create_map_migration_policy(server_id_pattern: str | None = None) -> TagPolicy:
    """MAP 2.0 마이그레이션 태그 정책 생성

    Args:
        server_id_pattern: 서버 ID 패턴 (예: "mig12345", "sap12345")
    """
    # 기본 패턴: mig, sap, oracle, comm 접두사 + 숫자 또는 XXXXX+숫자
    default_pattern = r"^(mig|sap|oracle|comm)([A-Z]{0,5})?[\d]+$"

    return TagPolicy(
        name="MAP 2.0 Migration Policy",
        description="AWS MAP 2.0 마이그레이션 태그 정책",
        rules=[
            TagRule(
                key="map-migrated",
                required=True,
                pattern=server_id_pattern or default_pattern,
                case_sensitive=True,
                description="MAP 마이그레이션 서버 ID",
            ),
        ],
    )
