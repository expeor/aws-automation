# internal/region - 리전 데이터
"""
리전 데이터 모듈

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
"""

__all__ = ["ALL_REGIONS", "REGION_NAMES", "COMMON_REGIONS"]


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in ("ALL_REGIONS", "REGION_NAMES", "COMMON_REGIONS"):
        from .data import ALL_REGIONS, COMMON_REGIONS, REGION_NAMES

        if name == "ALL_REGIONS":
            return ALL_REGIONS
        elif name == "REGION_NAMES":
            return REGION_NAMES
        elif name == "COMMON_REGIONS":
            return COMMON_REGIONS

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
