"""
core/region/availability.py - 리전 가용성 확인

EC2.describe_regions()를 사용하여 계정에서 접근 가능한 리전을 확인합니다.

Usage:
    from core.region.availability import get_available_regions, RegionAvailabilityChecker

    # 간편 사용
    regions = get_available_regions(session)

    # 상세 사용
    checker = RegionAvailabilityChecker(session)
    regions = checker.get_available_regions()

    # 특정 리전 확인
    if checker.is_region_available("ap-northeast-2"):
        print("서울 리전 사용 가능")

    # 리전 패턴 필터링과 함께 사용
    from core.filter import expand_region_pattern
    requested = expand_region_pattern("ap-*")
    available = checker.filter_available_regions(requested)
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import boto3

logger = logging.getLogger(__name__)

# 캐시 TTL (초) - 리전 목록은 자주 변경되지 않음
DEFAULT_CACHE_TTL = 3600  # 1시간


@dataclass
class RegionInfo:
    """리전 정보

    Attributes:
        region_name: 리전 코드 (예: "ap-northeast-2")
        endpoint: 리전 엔드포인트
        opt_in_status: 옵트인 상태 ("opt-in-not-required", "opted-in", "not-opted-in")
    """

    region_name: str
    endpoint: str = ""
    opt_in_status: str = "opt-in-not-required"

    @property
    def is_opted_in(self) -> bool:
        """옵트인 리전 여부 (활성화됨)"""
        return self.opt_in_status in ("opt-in-not-required", "opted-in")

    @property
    def requires_opt_in(self) -> bool:
        """옵트인이 필요한 리전인지"""
        return self.opt_in_status != "opt-in-not-required"

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_name": self.region_name,
            "endpoint": self.endpoint,
            "opt_in_status": self.opt_in_status,
            "is_opted_in": self.is_opted_in,
        }


@dataclass
class _CacheEntry:
    """캐시 엔트리"""

    data: Any
    timestamp: float
    ttl: float

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


@dataclass
class RegionAvailabilityChecker:
    """리전 가용성 확인 클래스

    계정에서 접근 가능한 AWS 리전을 확인합니다.
    옵트인이 필요한 리전도 지원합니다.

    Example:
        checker = RegionAvailabilityChecker(session)

        # 사용 가능한 모든 리전
        regions = checker.get_available_regions()

        # 특정 리전 확인
        if checker.is_region_available("me-south-1"):
            print("바레인 리전 활성화됨")
        else:
            print("바레인 리전 비활성화 (옵트인 필요)")
    """

    session: Any  # boto3.Session
    cache_ttl: float = DEFAULT_CACHE_TTL
    _cache: dict[str, _CacheEntry] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def _get_cached(self, key: str) -> Any | None:
        """캐시에서 값 조회"""
        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                return entry.data
            return None

    def _set_cached(self, key: str, data: Any) -> None:
        """캐시에 값 저장"""
        with self._lock:
            self._cache[key] = _CacheEntry(data=data, timestamp=time.time(), ttl=self.cache_ttl)

    def get_all_regions_info(self) -> list[RegionInfo]:
        """모든 리전 정보 조회 (옵트인 상태 포함)

        Returns:
            RegionInfo 리스트 (활성화 여부 관계없이 모든 리전)
        """
        cache_key = "all_regions_info"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        regions: list[RegionInfo] = []

        try:
            # 기본 리전에서 EC2 클라이언트 생성
            ec2 = self.session.client("ec2", region_name="us-east-1")

            # AllRegions=True로 모든 리전 조회 (옵트인 상태 포함)
            response = ec2.describe_regions(AllRegions=True)

            for region in response.get("Regions", []):
                region_info = RegionInfo(
                    region_name=region.get("RegionName", ""),
                    endpoint=region.get("Endpoint", ""),
                    opt_in_status=region.get("OptInStatus", "opt-in-not-required"),
                )
                regions.append(region_info)

        except Exception as e:
            logger.warning(f"리전 목록 조회 실패: {e}")
            # 폴백: 기본 리전 목록 사용
            from .data import ALL_REGIONS

            regions = [RegionInfo(region_name=r) for r in ALL_REGIONS]

        self._set_cached(cache_key, regions)
        return regions

    def get_available_regions(self, include_opt_in_pending: bool = False) -> list[str]:
        """접근 가능한 리전 목록 조회

        Args:
            include_opt_in_pending: 옵트인 대기 중인 리전도 포함할지

        Returns:
            사용 가능한 리전 코드 리스트
        """
        cache_key = f"available_regions:{include_opt_in_pending}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        all_regions = self.get_all_regions_info()

        available = []
        for region in all_regions:
            if region.is_opted_in:
                available.append(region.region_name)
            elif include_opt_in_pending and region.opt_in_status == "not-opted-in":
                # 옵트인 대기 중인 리전도 포함 (테스트용)
                pass

        self._set_cached(cache_key, available)
        return available

    def is_region_available(self, region_name: str) -> bool:
        """특정 리전 사용 가능 여부 확인

        Args:
            region_name: 확인할 리전 코드

        Returns:
            사용 가능하면 True
        """
        available = self.get_available_regions()
        return region_name in available

    def get_region_info(self, region_name: str) -> RegionInfo | None:
        """특정 리전 상세 정보 조회

        Args:
            region_name: 조회할 리전 코드

        Returns:
            RegionInfo 또는 None
        """
        all_regions = self.get_all_regions_info()
        for region in all_regions:
            if region.region_name == region_name:
                return region
        return None

    def filter_available_regions(self, regions: list[str]) -> list[str]:
        """요청된 리전 중 사용 가능한 리전만 필터링

        Args:
            regions: 확인할 리전 목록

        Returns:
            사용 가능한 리전만 포함된 리스트
        """
        available = set(self.get_available_regions())
        return [r for r in regions if r in available]

    def get_unavailable_regions(self, regions: list[str]) -> list[tuple[str, str]]:
        """요청된 리전 중 사용 불가능한 리전과 이유

        Args:
            regions: 확인할 리전 목록

        Returns:
            (리전 코드, 이유) 튜플 리스트
        """
        unavailable = []
        all_info = {r.region_name: r for r in self.get_all_regions_info()}

        for region in regions:
            if region not in all_info:
                unavailable.append((region, "존재하지 않는 리전"))
            elif not all_info[region].is_opted_in:
                unavailable.append((region, f"옵트인 필요 (상태: {all_info[region].opt_in_status})"))

        return unavailable

    def get_opt_in_regions(self) -> list[RegionInfo]:
        """옵트인이 필요한 리전 목록

        Returns:
            옵트인이 필요한 RegionInfo 리스트
        """
        all_regions = self.get_all_regions_info()
        return [r for r in all_regions if r.requires_opt_in]

    def get_enabled_opt_in_regions(self) -> list[RegionInfo]:
        """활성화된 옵트인 리전 목록

        Returns:
            옵트인 후 활성화된 RegionInfo 리스트
        """
        all_regions = self.get_all_regions_info()
        return [r for r in all_regions if r.opt_in_status == "opted-in"]

    def clear_cache(self) -> None:
        """캐시 초기화"""
        with self._lock:
            self._cache.clear()


# =============================================================================
# 싱글톤 팩토리
# =============================================================================

_checkers: dict[int, RegionAvailabilityChecker] = {}
_checker_lock = threading.Lock()


def get_region_checker(
    session: boto3.Session,
    cache_ttl: float = DEFAULT_CACHE_TTL,
) -> RegionAvailabilityChecker:
    """세션별 RegionAvailabilityChecker 싱글톤 조회

    Args:
        session: boto3 Session
        cache_ttl: 캐시 TTL (초)

    Returns:
        RegionAvailabilityChecker 인스턴스
    """
    key = id(session)

    with _checker_lock:
        if key not in _checkers:
            _checkers[key] = RegionAvailabilityChecker(session=session, cache_ttl=cache_ttl)
        return _checkers[key]


def reset_region_checkers() -> None:
    """모든 리전 체커 초기화"""
    global _checkers
    with _checker_lock:
        _checkers = {}


# =============================================================================
# 편의 함수
# =============================================================================


def get_available_regions(session: boto3.Session) -> list[str]:
    """간편하게 사용 가능한 리전 목록 조회

    Args:
        session: boto3 Session

    Returns:
        사용 가능한 리전 코드 리스트
    """
    checker = get_region_checker(session)
    return checker.get_available_regions()


def filter_available_regions(session: boto3.Session, regions: list[str]) -> list[str]:
    """요청된 리전 중 사용 가능한 리전만 필터링

    Args:
        session: boto3 Session
        regions: 확인할 리전 목록

    Returns:
        사용 가능한 리전만 포함된 리스트
    """
    checker = get_region_checker(session)
    return checker.filter_available_regions(regions)


def validate_regions(session: boto3.Session, regions: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    """리전 목록 검증

    Args:
        session: boto3 Session
        regions: 검증할 리전 목록

    Returns:
        (사용 가능한 리전 리스트, (사용 불가 리전, 이유) 튜플 리스트)
    """
    checker = get_region_checker(session)
    available = checker.filter_available_regions(regions)
    unavailable = checker.get_unavailable_regions(regions)
    return available, unavailable
