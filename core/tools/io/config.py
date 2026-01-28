"""DEPRECATED: Use shared.io.config instead.

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드에서는 shared.io.config를 사용하세요.
"""

import warnings

from shared.io.config import OutputConfig, OutputFormat

warnings.warn(
    "core.tools.io.config is deprecated. Use shared.io.config instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["OutputConfig", "OutputFormat"]
