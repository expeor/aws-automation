# internal/region - 리전 데이터
"""리전 데이터 및 가용성 확인 모듈"""

from .availability import (
    RegionAvailabilityChecker,
    RegionInfo,
    filter_available_regions,
    get_available_regions,
    get_region_checker,
    reset_region_checkers,
    validate_regions,
)
from .data import ALL_REGIONS, COMMON_REGIONS, REGION_NAMES
from .filter import (
    AccountFilter,
    expand_region_pattern,
    filter_accounts_by_pattern,
    filter_strings_by_pattern,
    match_any_pattern,
    match_pattern,
    parse_patterns,
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
    # 필터링
    "AccountFilter",
    "expand_region_pattern",
    "filter_accounts_by_pattern",
    "filter_strings_by_pattern",
    "match_any_pattern",
    "match_pattern",
    "parse_patterns",
]
