# pkg/io/file - 파일 I/O
"""
파일 유틸리티

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
    탐색기 열기는 pkg.output.open_in_explorer 사용.
"""

__all__ = [
    # io
    "read_file",
    "write_file",
    "ensure_dir",
    "read_json",
    "write_json",
]

_IO_ATTRS = {"read_file", "write_file", "ensure_dir", "read_json", "write_json"}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in _IO_ATTRS:
        from . import io

        return getattr(io, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
