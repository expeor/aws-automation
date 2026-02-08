"""
core/parallel/quotas.py - AWS Service Quotas 확인

운영 전 서비스 한도를 확인하여 쿼터 초과를 방지합니다.

Usage:
    from core.parallel.quotas import ServiceQuotaChecker, get_quota_checker

    # 기본 사용
    checker = get_quota_checker(session, region="ap-northeast-2")
    quota = checker.get_quota("ec2", "Running On-Demand Standard instances")

    # 사용률 확인
    if quota and quota.usage_percent > 80:
        print(f"경고: {quota.quota_name} 사용률 {quota.usage_percent:.1f}%")

    # 모든 쿼터 확인
    quotas = checker.get_service_quotas("ec2")
    high_usage = [q for q in quotas if q.usage_percent > 80]
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import TypeAlias

    import boto3

    Boto3Session: TypeAlias = boto3.Session

logger = logging.getLogger(__name__)

# 캐시 TTL (초)
DEFAULT_CACHE_TTL = 300  # 5분


class QuotaStatus(Enum):
    """쿼터 상태"""

    OK = "ok"  # 정상 (80% 미만)
    WARNING = "warning"  # 경고 (80% 이상)
    CRITICAL = "critical"  # 위험 (90% 이상)
    EXCEEDED = "exceeded"  # 초과 (100% 이상)
    UNKNOWN = "unknown"  # 확인 불가


@dataclass
class ServiceQuotaInfo:
    """서비스 쿼터 정보

    Attributes:
        service_code: AWS 서비스 코드 (예: "ec2", "lambda")
        quota_code: 쿼터 코드 (예: "L-1216C47A")
        quota_name: 쿼터 이름
        value: 쿼터 한도 값
        unit: 단위 (예: "None", "Count", "Megabytes")
        adjustable: 조정 가능 여부
        global_quota: 글로벌 쿼터 여부
        usage_value: 현재 사용량 (확인 가능한 경우)
        usage_percent: 사용률 (%) (확인 가능한 경우)
        status: 쿼터 상태
    """

    service_code: str
    quota_code: str
    quota_name: str
    value: float
    unit: str = "None"
    adjustable: bool = False
    global_quota: bool = False
    usage_value: float | None = None
    usage_percent: float = 0.0
    status: QuotaStatus = QuotaStatus.UNKNOWN

    def __post_init__(self):
        """사용률 기반 상태 계산"""
        if self.usage_value is not None and self.value > 0:
            self.usage_percent = (self.usage_value / self.value) * 100
            if self.usage_percent >= 100:
                self.status = QuotaStatus.EXCEEDED
            elif self.usage_percent >= 90:
                self.status = QuotaStatus.CRITICAL
            elif self.usage_percent >= 80:
                self.status = QuotaStatus.WARNING
            else:
                self.status = QuotaStatus.OK

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "service_code": self.service_code,
            "quota_code": self.quota_code,
            "quota_name": self.quota_name,
            "value": self.value,
            "unit": self.unit,
            "adjustable": self.adjustable,
            "global_quota": self.global_quota,
            "usage_value": self.usage_value,
            "usage_percent": self.usage_percent,
            "status": self.status.value,
        }


@dataclass
class _CacheEntry:
    """캐시 엔트리"""

    data: Any
    timestamp: float
    ttl: float

    def is_expired(self) -> bool:
        return time.monotonic() - self.timestamp > self.ttl


@dataclass
class ServiceQuotaChecker:
    """서비스 쿼터 확인 클래스

    AWS Service Quotas API를 사용하여 서비스 한도를 확인합니다.

    Example:
        checker = ServiceQuotaChecker(session, region="ap-northeast-2")

        # EC2 쿼터 확인
        quotas = checker.get_service_quotas("ec2")
        for q in quotas:
            if q.status == QuotaStatus.WARNING:
                print(f"경고: {q.quota_name} - {q.usage_percent:.1f}%")

        # 특정 쿼터 확인
        quota = checker.get_quota("ec2", "Running On-Demand Standard instances")
    """

    session: Boto3Session
    region: str
    cache_ttl: float = DEFAULT_CACHE_TTL
    _cache: dict[str, _CacheEntry] = field(default_factory=dict)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def _get_client(self):
        """Service Quotas 클라이언트 생성"""
        from .client import get_client

        return get_client(self.session, "service-quotas", region_name=self.region)

    def _get_cloudwatch_client(self):
        """CloudWatch 클라이언트 생성 (사용량 확인용)"""
        from .client import get_client

        return get_client(self.session, "cloudwatch", region_name=self.region)

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
            self._cache[key] = _CacheEntry(data=data, timestamp=time.monotonic(), ttl=self.cache_ttl)

    def get_service_quotas(self, service_code: str) -> list[ServiceQuotaInfo]:
        """서비스의 모든 쿼터 조회

        Args:
            service_code: AWS 서비스 코드 (예: "ec2", "lambda", "rds")

        Returns:
            ServiceQuotaInfo 리스트
        """
        cache_key = f"quotas:{service_code}:{self.region}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        quotas: list[ServiceQuotaInfo] = []

        try:
            client = self._get_client()
            paginator = client.get_paginator("list_service_quotas")

            for page in paginator.paginate(ServiceCode=service_code):
                for quota in page.get("Quotas", []):
                    quota_info = ServiceQuotaInfo(
                        service_code=service_code,
                        quota_code=quota.get("QuotaCode", ""),
                        quota_name=quota.get("QuotaName", ""),
                        value=quota.get("Value", 0.0),
                        unit=quota.get("Unit", "None"),
                        adjustable=quota.get("Adjustable", False),
                        global_quota=quota.get("GlobalQuota", False),
                    )
                    quotas.append(quota_info)

        except Exception as e:
            logger.debug(f"쿼터 조회 실패 ({service_code}): {e}")
            # 기본 쿼터 시도
            with contextlib.suppress(Exception):
                quotas = self._get_default_quotas(service_code)

        self._set_cached(cache_key, quotas)
        return quotas

    def _get_default_quotas(self, service_code: str) -> list[ServiceQuotaInfo]:
        """AWS 기본 쿼터 조회 (계정 미조정 값)"""
        quotas: list[ServiceQuotaInfo] = []

        try:
            client = self._get_client()
            paginator = client.get_paginator("list_aws_default_service_quotas")

            for page in paginator.paginate(ServiceCode=service_code):
                for quota in page.get("Quotas", []):
                    quota_info = ServiceQuotaInfo(
                        service_code=service_code,
                        quota_code=quota.get("QuotaCode", ""),
                        quota_name=quota.get("QuotaName", ""),
                        value=quota.get("Value", 0.0),
                        unit=quota.get("Unit", "None"),
                        adjustable=quota.get("Adjustable", False),
                        global_quota=quota.get("GlobalQuota", False),
                    )
                    quotas.append(quota_info)
        except Exception as e:
            logger.debug(f"기본 쿼터 조회 실패 ({service_code}): {e}")

        return quotas

    def get_quota(self, service_code: str, quota_name: str) -> ServiceQuotaInfo | None:
        """특정 쿼터 조회

        Args:
            service_code: AWS 서비스 코드
            quota_name: 쿼터 이름 (부분 일치 지원)

        Returns:
            ServiceQuotaInfo 또는 None
        """
        quotas = self.get_service_quotas(service_code)
        quota_name_lower = quota_name.lower()

        # 정확한 일치 먼저
        for quota in quotas:
            if quota.quota_name.lower() == quota_name_lower:
                return quota

        # 부분 일치
        for quota in quotas:
            if quota_name_lower in quota.quota_name.lower():
                return quota

        return None

    def get_quota_with_usage(
        self,
        service_code: str,
        quota_code: str,
        metric_namespace: str | None = None,
        metric_name: str | None = None,
        dimensions: list[dict[str, str]] | None = None,
    ) -> ServiceQuotaInfo | None:
        """사용량 포함 쿼터 조회

        CloudWatch 메트릭을 사용하여 현재 사용량을 확인합니다.

        Args:
            service_code: AWS 서비스 코드
            quota_code: 쿼터 코드
            metric_namespace: CloudWatch 메트릭 네임스페이스
            metric_name: CloudWatch 메트릭 이름
            dimensions: CloudWatch 메트릭 디멘션

        Returns:
            사용량이 포함된 ServiceQuotaInfo
        """
        cache_key = f"quota_usage:{service_code}:{quota_code}:{self.region}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore[no-any-return]

        try:
            client = self._get_client()
            response = client.get_service_quota(ServiceCode=service_code, QuotaCode=quota_code)

            quota = response.get("Quota", {})
            quota_value = quota.get("Value", 0.0)

            # 사용량 조회 시도
            usage_value = None
            if metric_namespace and metric_name:
                usage_value = self._get_metric_value(metric_namespace, metric_name, dimensions)

            quota_info = ServiceQuotaInfo(
                service_code=service_code,
                quota_code=quota.get("QuotaCode", quota_code),
                quota_name=quota.get("QuotaName", ""),
                value=quota_value,
                unit=quota.get("Unit", "None"),
                adjustable=quota.get("Adjustable", False),
                global_quota=quota.get("GlobalQuota", False),
                usage_value=usage_value,
            )

            self._set_cached(cache_key, quota_info)
            return quota_info

        except Exception as e:
            logger.debug(f"쿼터 상세 조회 실패 ({service_code}/{quota_code}): {e}")
            return None

    def _get_metric_value(
        self,
        namespace: str,
        metric_name: str,
        dimensions: list[dict[str, str]] | None = None,
    ) -> float | None:
        """CloudWatch 메트릭 현재 값 조회"""
        from datetime import datetime, timedelta, timezone

        try:
            cw = self._get_cloudwatch_client()

            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)

            params: dict[str, Any] = {
                "Namespace": namespace,
                "MetricName": metric_name,
                "StartTime": start_time,
                "EndTime": end_time,
                "Period": 300,  # 5분
                "Statistics": ["Maximum"],
            }

            if dimensions:
                params["Dimensions"] = dimensions

            response = cw.get_metric_statistics(**params)
            datapoints = response.get("Datapoints", [])

            if datapoints:
                # 가장 최근 값
                latest = max(datapoints, key=lambda x: x["Timestamp"])
                return float(latest.get("Maximum", 0.0))

        except Exception as e:
            logger.debug(f"메트릭 조회 실패 ({namespace}/{metric_name}): {e}")

        return None

    def check_quotas_health(
        self, service_code: str, warning_threshold: float = 80.0
    ) -> tuple[list[ServiceQuotaInfo], list[ServiceQuotaInfo], list[ServiceQuotaInfo]]:
        """서비스 쿼터 건강 상태 확인

        get_service_quotas()는 usage 데이터를 포함하지 않으므로,
        usage_value가 None인 쿼터는 UNKNOWN으로 별도 분리합니다.
        사용량 확인이 필요하면 get_quota_with_usage()를 개별 호출하세요.

        Args:
            service_code: AWS 서비스 코드
            warning_threshold: 경고 임계치 (%)

        Returns:
            (정상 쿼터, 경고/위험 쿼터, 사용량 미확인 쿼터) 튜플
        """
        quotas = self.get_service_quotas(service_code)

        ok_quotas: list[ServiceQuotaInfo] = []
        warn_quotas: list[ServiceQuotaInfo] = []
        unknown_quotas: list[ServiceQuotaInfo] = []

        for quota in quotas:
            if quota.usage_value is None:
                unknown_quotas.append(quota)
            elif quota.usage_percent >= warning_threshold:
                warn_quotas.append(quota)
            else:
                ok_quotas.append(quota)

        return ok_quotas, warn_quotas, unknown_quotas

    def clear_cache(self) -> None:
        """캐시 초기화"""
        with self._lock:
            self._cache.clear()


# =============================================================================
# 서비스별 주요 쿼터 정의
# =============================================================================

# 자주 확인하는 쿼터 매핑 (서비스 코드 -> 쿼터 코드 -> 설명)
COMMON_QUOTAS: dict[str, dict[str, str]] = {
    "ec2": {
        "L-1216C47A": "Running On-Demand Standard instances",
        "L-34B43A08": "All Standard Spot Instance Requests",
        "L-0263D0A3": "EC2-VPC Elastic IPs",
        "L-E3A00192": "Volumes (io1, io2)",
    },
    "lambda": {
        "L-B99A9384": "Concurrent executions",
        "L-2ACBD22F": "Function and layer storage",
    },
    "rds": {
        "L-7B6409FD": "DB instances",
        "L-952B80B8": "DB clusters",
        "L-7ADDB58A": "DB cluster parameter groups",
    },
    "s3": {
        "L-DC2B2D3D": "Buckets",
    },
    "dynamodb": {
        "L-F98FE922": "Table-level read throughput",
        "L-F1E6EC6C": "Table-level write throughput",
    },
    "iam": {
        "L-F4A5425F": "Roles",
        "L-FE177D64": "Users",
        "L-BF35879D": "Groups",
    },
}


# =============================================================================
# 싱글톤 팩토리
# =============================================================================

_checkers: dict[str, ServiceQuotaChecker] = {}
_checker_lock = threading.Lock()
_MAX_CACHED_CHECKERS = 50


def get_quota_checker(
    session: Boto3Session,
    region: str,
    cache_ttl: float = DEFAULT_CACHE_TTL,
) -> ServiceQuotaChecker:
    """리전별 ServiceQuotaChecker 싱글톤 조회

    Args:
        session: boto3 Session
        region: AWS 리전
        cache_ttl: 캐시 TTL (초)

    Returns:
        ServiceQuotaChecker 인스턴스
    """
    key = f"{getattr(session, 'profile_name', 'default')}:{region}"

    with _checker_lock:
        if key not in _checkers:
            # 캐시 크기 제한: 최대 초과 시 전체 초기화
            if len(_checkers) >= _MAX_CACHED_CHECKERS:
                _checkers.clear()
            _checkers[key] = ServiceQuotaChecker(session=session, region=region, cache_ttl=cache_ttl)
        return _checkers[key]


def reset_quota_checkers() -> None:
    """모든 쿼터 체커 초기화"""
    global _checkers
    with _checker_lock:
        _checkers = {}
