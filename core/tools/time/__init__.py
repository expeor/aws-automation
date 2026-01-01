# pkg/time - 날짜/시간 유틸리티
"""
날짜/시간 유틸리티

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
"""

__all__ = [
    "get_local_timezone_offset",
    "utc_to_local",
    "format_local_datetime",
    "get_timezone_aware_now",
    "format_sso_token_expiry",
]

_UTILS_ATTRS = {
    "get_local_timezone_offset",
    "utc_to_local",
    "format_local_datetime",
    "get_timezone_aware_now",
    "format_sso_token_expiry",
}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in _UTILS_ATTRS:
        from . import utils

        return getattr(utils, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
