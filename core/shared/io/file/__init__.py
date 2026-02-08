# pkg/io/file - 파일 I/O
"""
파일 유틸리티

Note:
    탐색기 열기는 pkg.output.open_in_explorer 사용.
"""

from .io import ensure_dir, read_file, read_json, write_file, write_json

__all__: list[str] = [
    # io
    "read_file",
    "write_file",
    "ensure_dir",
    "read_json",
    "write_json",
]
