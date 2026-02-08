"""
core/parallel/errors.py - 에러 수집 및 관리

병렬 실행 중 발생하는 에러를 일관되게 수집하고 관리하는 유틸리티입니다.

주요 구성 요소:
- ErrorSeverity: 에러 심각도 분류
- CollectedError: 수집된 에러 상세 정보
- ErrorCollector: 스레드 세이프 에러 수집기
- safe_collect: 안전한 에러 수집 헬퍼
- try_or_default: 실패 시 기본값 반환 헬퍼

Example:
    collector = ErrorCollector("ec2")

    try:
        result = client.describe_instances()
    except ClientError as e:
        collector.collect(e, account_id, account_name, region, "describe_instances")

    if collector.has_errors:
        print(collector.get_summary())
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

from .types import ErrorCategory

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorSeverity(Enum):
    """에러 심각도 분류

    수집된 에러의 심각도를 나타내며, 로깅 레벨과 보고 여부를 결정합니다.
    """

    CRITICAL = "critical"  # 핵심 기능 실패 - 반드시 보고
    WARNING = "warning"  # 부분 실패 - 보고하되 계속 진행
    INFO = "info"  # 정보성 - 로그만 남김 (권한 없음 등)
    DEBUG = "debug"  # 디버그 - 개발 시에만 필요


@dataclass
class CollectedError:
    """수집된 에러 상세 정보

    ErrorCollector에 의해 수집된 개별 에러의 컨텍스트 정보를 담습니다.

    Attributes:
        timestamp: 에러 발생 시각
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름 또는 프로파일명
        region: AWS 리전
        service: AWS 서비스 이름 (예: "ec2", "lambda")
        operation: API 작업 이름 (예: "describe_instances")
        error_code: AWS 에러 코드 (예: "AccessDenied")
        error_message: 에러 메시지
        severity: 에러 심각도
        category: 에러 카테고리 (ErrorCategory)
        resource_id: 관련 리소스 ID (선택사항)
    """

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
        """딕셔너리로 변환 (로깅/직렬화용)"""
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


def categorize_error_code(error_code: str) -> ErrorCategory:
    """에러 코드 문자열을 기반으로 ErrorCategory 분류

    에러 코드에 포함된 키워드를 분석하여 적절한 카테고리를 반환합니다.

    Args:
        error_code: AWS 에러 코드 문자열 (예: "AccessDenied", "ThrottlingException")

    Returns:
        분류된 에러 카테고리. 매칭되는 키워드가 없으면 UNKNOWN 반환.
    """
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

    병렬 실행 중 여러 스레드에서 발생하는 에러를 안전하게 수집하고
    심각도별로 분류하여 요약 보고를 제공합니다.

    Example:
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
        """초기화

        Args:
            service: AWS 서비스 이름 (수집된 에러에 공통 적용)
        """
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
        """botocore ClientError를 수집하고 로깅

        에러 코드에서 카테고리를 자동 분류하며, ACCESS_DENIED는
        심각도를 INFO로 자동 다운그레이드합니다.

        Args:
            error: botocore ClientError 예외
            account_id: AWS 계정 ID
            account_name: 계정 이름 또는 프로파일명
            region: AWS 리전
            operation: API 작업 이름
            severity: 에러 심각도 (기본: WARNING)
            resource_id: 관련 리소스 ID (선택사항)
        """
        error_info = error.response.get("Error", {})
        error_code = error_info.get("Code", "Unknown")
        error_message = error_info.get("Message", str(error))
        category = categorize_error_code(error_code)

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
        """일반 에러 수집 (ClientError 이외의 에러용)

        Args:
            error_code: 에러 코드 문자열
            error_message: 에러 메시지
            account_id: AWS 계정 ID
            account_name: 계정 이름 또는 프로파일명
            region: AWS 리전
            operation: API 작업 이름
            severity: 에러 심각도 (기본: WARNING)
            resource_id: 관련 리소스 ID (선택사항)
        """
        category = categorize_error_code(error_code)

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
        """수집된 모든 에러의 복사본 반환"""
        with self._lock:
            return list(self._errors)

    @property
    def has_errors(self) -> bool:
        """에러 존재 여부"""
        with self._lock:
            return len(self._errors) > 0

    @property
    def critical_errors(self) -> list[CollectedError]:
        """CRITICAL 심각도 에러만 반환"""
        with self._lock:
            return [e for e in self._errors if e.severity == ErrorSeverity.CRITICAL]

    @property
    def warning_errors(self) -> list[CollectedError]:
        """WARNING 심각도 에러만 반환"""
        with self._lock:
            return [e for e in self._errors if e.severity == ErrorSeverity.WARNING]

    def get_summary(self) -> str:
        """심각도별 에러 건수를 포함한 요약 문자열 반환

        Returns:
            포맷팅된 요약 문자열 (예: "에러 3건 (critical: 1건, warning: 2건)")
        """
        with self._lock:
            if not self._errors:
                return "에러 없음"

            by_severity: dict[str, int] = {}
            for e in self._errors:
                by_severity[e.severity.value] = by_severity.get(e.severity.value, 0) + 1

            parts = [f"{k}: {v}건" for k, v in sorted(by_severity.items())]
            return f"에러 {len(self._errors)}건 ({', '.join(parts)})"

    def get_by_account(self) -> dict[str, list[CollectedError]]:
        """계정별로 에러를 그룹핑하여 반환

        Returns:
            {"계정이름 (계정ID)": [CollectedError, ...]} 딕셔너리
        """
        with self._lock:
            result: dict[str, list[CollectedError]] = {}
            for e in self._errors:
                key = f"{e.account_name} ({e.account_id})"
                if key not in result:
                    result[key] = []
                result[key].append(e)
            return result

    def clear(self) -> None:
        """수집된 에러 전체 초기화"""
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
    """안전한 에러 수집 (collector가 None이어도 동작)

    collector가 있으면 에러를 수집하고, 없으면 로깅만 수행합니다.
    collector 유무에 관계없이 안전하게 호출할 수 있습니다.

    Args:
        collector: ErrorCollector 인스턴스 (None 가능)
        error: botocore ClientError 예외
        account_id: AWS 계정 ID
        account_name: 계정 이름 또는 프로파일명
        region: AWS 리전
        operation: API 작업 이름
        severity: 에러 심각도 (기본: WARNING)
        resource_id: 관련 리소스 ID (선택사항)
    """
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

    부수적인 API 호출(태그 조회 등)에서 실패해도 전체 로직을 중단하지 않고
    기본값으로 대체하면서 에러를 수집합니다.

    Args:
        func: 실행할 함수 (인자 없음)
        default: 실패 시 반환할 기본값
        collector: ErrorCollector 인스턴스 (None이면 로깅만)
        account_id: AWS 계정 ID
        account_name: 계정 이름 또는 프로파일명
        region: AWS 리전
        operation: API 작업 이름
        severity: 에러 심각도 (기본: DEBUG)

    Returns:
        함수 실행 결과 또는 실패 시 default 값

    Example:
        tags = try_or_default(
            lambda: client.list_tags(Resource=arn)["Tags"],
            default={},
            collector=collector,
            account_name=account_name,
            region=region,
            operation="list_tags",
            severity=ErrorSeverity.DEBUG,
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
