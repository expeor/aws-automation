"""
core/parallel/errors.py - 에러 수집 및 관리

일관된 에러 핸들링을 위한 유틸리티:
- 에러 수집 및 컨텍스트 추적
- 로깅 통합
- 에러 카테고리 분류
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TypeVar

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorSeverity(Enum):
    """에러 심각도"""

    CRITICAL = "critical"  # 핵심 기능 실패 - 반드시 보고
    WARNING = "warning"  # 부분 실패 - 보고하되 계속 진행
    INFO = "info"  # 정보성 - 로그만 남김 (권한 없음 등)
    DEBUG = "debug"  # 디버그 - 개발 시에만 필요


class ErrorCategory(Enum):
    """에러 카테고리"""

    ACCESS_DENIED = "access_denied"  # 권한 없음
    NOT_FOUND = "not_found"  # 리소스 없음
    THROTTLING = "throttling"  # API 제한
    TIMEOUT = "timeout"  # 타임아웃
    INVALID_REQUEST = "invalid_request"  # 잘못된 요청
    SERVICE_ERROR = "service_error"  # AWS 서비스 오류
    UNKNOWN = "unknown"  # 알 수 없음


@dataclass
class CollectedError:
    """수집된 에러 정보"""

    timestamp: datetime
    account_id: str
    account_name: str
    region: str
    service: str
    operation: str
    error_code: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    resource_id: str | None = None

    def __str__(self) -> str:
        loc = f"{self.account_name}/{self.region}"
        return f"[{self.severity.value.upper()}] {loc} - {self.service}.{self.operation}: {self.error_code}"

    def to_dict(self) -> dict[str, str | None]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "account_id": self.account_id,
            "account_name": self.account_name,
            "region": self.region,
            "service": self.service,
            "operation": self.operation,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "severity": self.severity.value,
            "category": self.category.value,
            "resource_id": self.resource_id,
        }


def categorize_error(error_code: str) -> ErrorCategory:
    """에러 코드로 카테고리 분류"""
    code = error_code.lower()

    if any(x in code for x in ["accessdenied", "unauthorized", "forbidden"]):
        return ErrorCategory.ACCESS_DENIED
    if any(x in code for x in ["notfound", "nosuch", "doesnotexist"]):
        return ErrorCategory.NOT_FOUND
    if any(x in code for x in ["throttl", "ratelimit", "toomanyrequests"]):
        return ErrorCategory.THROTTLING
    if any(x in code for x in ["timeout", "timedout"]):
        return ErrorCategory.TIMEOUT
    if any(x in code for x in ["invalid", "validation", "malformed"]):
        return ErrorCategory.INVALID_REQUEST
    if any(x in code for x in ["internal", "serviceunavailable", "serviceerror"]):
        return ErrorCategory.SERVICE_ERROR

    return ErrorCategory.UNKNOWN


class ErrorCollector:
    """스레드 세이프 에러 수집기

    Usage:
        collector = ErrorCollector("lambda")

        # 에러 발생 시
        try:
            result = client.list_functions()
        except ClientError as e:
            collector.collect(e, account_id, account_name, region, "list_functions")

        # 작업 완료 후
        if collector.has_errors:
            print(collector.get_summary())
            for err in collector.critical_errors:
                print(err)
    """

    def __init__(self, service: str):
        self.service = service
        self._errors: list[CollectedError] = []
        self._lock = threading.Lock()

    def collect(
        self,
        error: ClientError,
        account_id: str,
        account_name: str,
        region: str,
        operation: str,
        severity: ErrorSeverity = ErrorSeverity.WARNING,
        resource_id: str | None = None,
    ) -> None:
        """ClientError 수집"""
        error_info = error.response.get("Error", {})
        error_code = error_info.get("Code", "Unknown")
        error_message = error_info.get("Message", str(error))
        category = categorize_error(error_code)

        # 권한 없음은 INFO로 다운그레이드
        if category == ErrorCategory.ACCESS_DENIED:
            severity = ErrorSeverity.INFO

        collected = CollectedError(
            timestamp=datetime.now(),
            account_id=account_id,
            account_name=account_name,
            region=region,
            service=self.service,
            operation=operation,
            error_code=error_code,
            error_message=error_message,
            severity=severity,
            category=category,
            resource_id=resource_id,
        )

        with self._lock:
            self._errors.append(collected)

        # 로깅
        log_msg = f"{collected}"
        if severity == ErrorSeverity.CRITICAL:
            logger.error(log_msg)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(log_msg)
        elif severity == ErrorSeverity.INFO:
            logger.info(log_msg)
        else:
            logger.debug(log_msg)

    def collect_generic(
        self,
        error_code: str,
        error_message: str,
        account_id: str,
        account_name: str,
        region: str,
        operation: str,
        severity: ErrorSeverity = ErrorSeverity.WARNING,
        resource_id: str | None = None,
    ) -> None:
        """일반 에러 수집"""
        category = categorize_error(error_code)

        collected = CollectedError(
            timestamp=datetime.now(),
            account_id=account_id,
            account_name=account_name,
            region=region,
            service=self.service,
            operation=operation,
            error_code=error_code,
            error_message=error_message,
            severity=severity,
            category=category,
            resource_id=resource_id,
        )

        with self._lock:
            self._errors.append(collected)

        log_msg = f"{collected}"
        if severity == ErrorSeverity.CRITICAL:
            logger.error(log_msg)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    @property
    def errors(self) -> list[CollectedError]:
        """모든 에러"""
        with self._lock:
            return list(self._errors)

    @property
    def has_errors(self) -> bool:
        """에러 존재 여부"""
        with self._lock:
            return len(self._errors) > 0

    @property
    def critical_errors(self) -> list[CollectedError]:
        """CRITICAL 에러만"""
        with self._lock:
            return [e for e in self._errors if e.severity == ErrorSeverity.CRITICAL]

    @property
    def warning_errors(self) -> list[CollectedError]:
        """WARNING 에러만"""
        with self._lock:
            return [e for e in self._errors if e.severity == ErrorSeverity.WARNING]

    def get_summary(self) -> str:
        """에러 요약"""
        with self._lock:
            if not self._errors:
                return "에러 없음"

            by_severity: dict[str, int] = {}
            for e in self._errors:
                by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1

            parts = [f"{k}: {v}건" for k, v in sorted(by_severity.items())]
            return f"에러 {len(self._errors)}건 ({', '.join(parts)})"

    def get_by_account(self) -> dict[str, list[CollectedError]]:
        """계정별 에러 그룹핑"""
        with self._lock:
            result: dict[str, list[CollectedError]] = {}
            for e in self._errors:
                key = f"{e.account_name} ({e.account_id})"
                if key not in result:
                    result[key] = []
                result[key].append(e)
            return result

    def clear(self) -> None:
        """에러 초기화"""
        with self._lock:
            self._errors.clear()


def safe_collect(
    collector: ErrorCollector | None,
    error: ClientError,
    account_id: str,
    account_name: str,
    region: str,
    operation: str,
    severity: ErrorSeverity = ErrorSeverity.WARNING,
    resource_id: str | None = None,
) -> None:
    """안전한 에러 수집 (collector가 None이어도 동작)"""
    if collector:
        collector.collect(error, account_id, account_name, region, operation, severity, resource_id)
    else:
        # collector 없으면 로깅만
        error_info = error.response.get("Error", {})
        error_code = error_info.get("Code", "Unknown")
        logger.warning(f"[{account_name}/{region}] {operation}: {error_code} - {error}")


def try_or_default(
    func: Callable[[], T],
    default: T,
    collector: ErrorCollector | None = None,
    account_id: str = "",
    account_name: str = "",
    region: str = "",
    operation: str = "",
    severity: ErrorSeverity = ErrorSeverity.DEBUG,
) -> T:
    """함수 실행, 실패 시 기본값 반환 + 에러 수집

    Usage:
        # 태그 조회 - 실패해도 기본값 반환
        tags = try_or_default(
            lambda: client.list_tags(Resource=arn)["Tags"],
            default={},
            collector=collector,
            account_name=account_name,
            region=region,
            operation="list_tags",
            severity=ErrorSeverity.DEBUG,  # 태그는 옵션이라 DEBUG
        )
    """
    try:
        return func()
    except ClientError as e:
        if collector:
            collector.collect(e, account_id, account_name, region, operation, severity)
        elif severity in (ErrorSeverity.CRITICAL, ErrorSeverity.WARNING):
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.warning(f"[{account_name}/{region}] {operation}: {error_code}")
        return default
    except Exception as e:
        if collector:
            collector.collect_generic(
                "UnexpectedError",
                str(e),
                account_id,
                account_name,
                region,
                operation,
                severity,
            )
        elif severity in (ErrorSeverity.CRITICAL, ErrorSeverity.WARNING):
            logger.warning(f"[{account_name}/{region}] {operation}: {e}")
        return default
