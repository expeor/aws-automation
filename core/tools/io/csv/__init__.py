"""DEPRECATED: Use shared.io.csv instead.

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드에서는 shared.io.csv를 사용하세요.
"""

import warnings

from shared.io.csv import (
    ENCODING_PRIORITIES,
    detect_csv_encoding,
    get_platform_recommended_encoding,
    read_csv_robust,
    validate_csv_headers,
)

warnings.warn(
    "core.tools.io.csv is deprecated. Use shared.io.csv instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__: list[str] = [
    "ENCODING_PRIORITIES",
    "detect_csv_encoding",
    "read_csv_robust",
    "validate_csv_headers",
    "get_platform_recommended_encoding",
]
