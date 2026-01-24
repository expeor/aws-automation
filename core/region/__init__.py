# internal/region - 리전 데이터
"""리전 데이터 및 가용성 확인 모듈"""

from .data import ALL_REGIONS, COMMON_REGIONS, REGION_NAMES
from .availability import (
    RegionAvailabilityChecker,
    RegionInfo,
    filter_available_regions,
    get_available_regions,
    get_region_checker,
    reset_region_checkers,
    validate_regions,
)

__all__: list[str] = [
    # 리전 데이터
    "ALL_REGIONS",
    "REGION_NAMES",
    "COMMON_REGIONS",
    # 가용성 확인
    "RegionAvailabilityChecker",
    "RegionInfo",
    "get_region_checker",
    "get_available_regions",
    "filter_available_regions",
    "validate_regions",
    "reset_region_checkers",
]
