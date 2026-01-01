# pkg/io/csv - CSV 파일 처리 유틸리티
"""
CSV 파일 처리 유틸리티

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
"""

__all__ = [
    "ENCODING_PRIORITIES",
    "detect_csv_encoding",
    "read_csv_robust",
    "validate_csv_headers",
    "get_platform_recommended_encoding",
]

_HANDLER_ATTRS = {
    "ENCODING_PRIORITIES",
    "detect_csv_encoding",
    "read_csv_robust",
    "validate_csv_headers",
    "get_platform_recommended_encoding",
}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in _HANDLER_ATTRS:
        from . import handler

        return getattr(handler, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
