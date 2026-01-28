"""DEPRECATED: Use shared.io.file instead.

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드에서는 shared.io.file를 사용하세요.
"""

import warnings

from shared.io.file import ensure_dir, read_file, read_json, write_file, write_json

warnings.warn(
    "core.tools.io.file is deprecated. Use shared.io.file instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__: list[str] = [
    "read_file",
    "write_file",
    "ensure_dir",
    "read_json",
    "write_json",
]
