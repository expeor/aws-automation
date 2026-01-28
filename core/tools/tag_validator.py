"""DEPRECATED: Use shared.aws.tags instead.

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드에서는 shared.aws.tags를 사용하세요.
"""

import warnings

from shared.aws.tags import (
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

warnings.warn(
    "core.tools.tag_validator is deprecated. Use shared.aws.tags instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "TagValidationErrorType",
    "TagValidationError",
    "TagRule",
    "TagPolicy",
    "TagValidationResult",
    "TagPolicyValidator",
    "create_basic_policy",
    "create_cost_allocation_policy",
    "create_security_policy",
    "create_map_migration_policy",
]
