"""DEPRECATED: Use shared.io.compat instead.

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드에서는 shared.io.compat를 사용하세요.
"""

import warnings

from shared.io.compat import generate_dual_report, generate_reports

warnings.warn(
    "core.tools.io.compat is deprecated. Use shared.io.compat instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["generate_reports", "generate_dual_report"]
