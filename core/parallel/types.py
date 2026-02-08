"""
core/parallel/types.py - 병렬 처리 결과 및 에러 타입 정의

TaskError, TaskResult, ParallelExecutionResult 등
병렬 실행 결과를 추적하고 분석하기 위한 타입들을 정의합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import cached_property
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class ErrorCategory(Enum):
    """에러 분류

    AWS API 에러를 카테고리로 분류하여 적절한 처리를 가능하게 합니다.
    """

    THROTTLING = "throttling"  # API 쓰로틀링 (재시도 가능)
    ACCESS_DENIED = "access_denied"  # 권한 없음 (재시도 불가)
    NOT_FOUND = "not_found"  # 리소스 없음 (재시도 불가)
    NETWORK = "network"  # 네트워크 오류 (재시도 가능)
    TIMEOUT = "timeout"  # 타임아웃 (재시도 가능)
    EXPIRED_TOKEN = "expired_token"  # 토큰 만료 (재인증 필요)
    INVALID_REQUEST = "invalid_request"  # 잘못된 요청 (재시도 불가)
    SERVICE_ERROR = "service_error"  # AWS 서비스 오류 (재시도 가능)
    UNKNOWN = "unknown"  # 기타


@dataclass
class TaskError:
    """개별 작업 에러 정보

    병렬 실행 중 발생한 에러의 상세 정보를 담습니다.

    Attributes:
        identifier: 계정 ID 또는 프로파일명
        region: AWS 리전
        category: 에러 카테고리
        error_code: AWS 에러 코드 (예: "AccessDenied")
        message: 에러 메시지
        timestamp: 발생 시각
        retries: 재시도 횟수
        original_exception: 원본 예외 객체
    """

    identifier: str
    region: str
    category: ErrorCategory
    error_code: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    retries: int = 0
    original_exception: Exception | None = None

    def is_retryable(self) -> bool:
        """재시도 가능한 에러인지 확인"""
        return self.category in (
            ErrorCategory.THROTTLING,
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
        )

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환 (로깅/직렬화용)"""
        return {
            "identifier": self.identifier,
            "region": self.region,
            "category": self.category.value,
            "error_code": self.error_code,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "retries": self.retries,
        }

    def __str__(self) -> str:
        return f"[{self.identifier}/{self.region}] {self.error_code}: {self.message}"


@dataclass
class TaskResult(Generic[T]):
    """개별 작업 결과

    병렬 실행된 단일 작업의 결과를 담습니다.

    Attributes:
        identifier: 계정 ID 또는 프로파일명
        region: AWS 리전
        success: 성공 여부
        data: 성공 시 결과 데이터
        error: 실패 시 에러 정보
        duration_ms: 실행 시간 (밀리초)
    """

    identifier: str
    region: str
    success: bool
    data: T | None = None
    error: TaskError | None = None
    duration_ms: float = 0.0

    def __str__(self) -> str:
        status = "OK" if self.success else "FAIL"
        return f"[{self.identifier}/{self.region}] {status} ({self.duration_ms:.0f}ms)"


@dataclass
class ParallelExecutionResult(Generic[T]):
    """병렬 실행 전체 결과

    모든 병렬 작업의 결과를 집계하고 분석하는 컨테이너입니다.

    Example:
        result = executor.execute(collect_func)

        # 성공한 데이터만 추출
        all_data = result.get_data()

        # 통계 확인
        print(f"성공: {result.success_count}, 실패: {result.error_count}")

        # 에러 요약
        if result.error_count > 0:
            print(result.get_error_summary())
    """

    results: tuple[TaskResult[T], ...] = ()

    @cached_property
    def successful(self) -> list[TaskResult[T]]:
        """성공한 결과만 반환 (캐싱됨)"""
        return [r for r in self.results if r.success]

    @cached_property
    def failed(self) -> list[TaskResult[T]]:
        """실패한 결과만 반환 (캐싱됨)"""
        return [r for r in self.results if not r.success]

    @property
    def success_count(self) -> int:
        """성공한 작업 수"""
        return len(self.successful)

    @property
    def error_count(self) -> int:
        """실패한 작업 수"""
        return len(self.failed)

    @property
    def total_count(self) -> int:
        """전체 작업 수"""
        return len(self.results)

    @cached_property
    def total_duration_ms(self) -> float:
        """전체 실행 시간 (밀리초, 캐싱됨)"""
        return sum(r.duration_ms for r in self.results)

    def has_any_success(self) -> bool:
        """하나 이상 성공했는지"""
        return self.success_count > 0

    def has_any_failure(self) -> bool:
        """하나 이상 실패했는지"""
        return self.error_count > 0

    def has_failures_only(self) -> bool:
        """모든 작업이 실패했는지"""
        return self.total_count > 0 and self.success_count == 0

    def get_data(self) -> list[T]:
        """성공한 결과의 데이터만 추출

        Returns:
            성공한 작업들의 data 리스트 (None 제외)
        """
        return [r.data for r in self.successful if r.data is not None]

    def get_flat_data(self) -> list[Any]:
        """성공한 결과의 데이터를 평탄화하여 추출

        각 결과가 리스트인 경우 하나의 리스트로 병합합니다.

        Returns:
            모든 성공 데이터를 평탄화한 리스트
        """
        flat: list[Any] = []
        for r in self.successful:
            if r.data is None:
                continue
            if isinstance(r.data, list):
                flat.extend(r.data)
            else:
                flat.append(r.data)
        return flat

    def get_errors(self) -> list[TaskError]:
        """모든 에러 정보 반환"""
        return [r.error for r in self.failed if r.error is not None]

    def get_errors_by_category(self) -> dict[ErrorCategory, list[TaskError]]:
        """카테고리별로 에러를 그룹화

        Returns:
            {ErrorCategory: [TaskError, ...]} 딕셔너리
        """
        grouped: dict[ErrorCategory, list[TaskError]] = {}
        for r in self.failed:
            if r.error:
                cat = r.error.category
                if cat not in grouped:
                    grouped[cat] = []
                grouped[cat].append(r.error)
        return grouped

    def get_error_summary(self, max_per_category: int = 3) -> str:
        """에러 요약 문자열 생성

        Args:
            max_per_category: 카테고리당 최대 표시 에러 수

        Returns:
            포맷팅된 에러 요약 문자열
        """
        if not self.failed:
            return ""

        lines = [f"총 {self.error_count}개 작업 실패:"]
        by_category = self.get_errors_by_category()

        for category, errors in by_category.items():
            lines.append(f"  [{category.value}] {len(errors)}건")
            for err in errors[:max_per_category]:
                lines.append(f"    - {err.identifier}/{err.region}: {err.error_code}")
            if len(errors) > max_per_category:
                lines.append(f"    ... 외 {len(errors) - max_per_category}건")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환 (로깅/직렬화용)"""
        return {
            "total": self.total_count,
            "success": self.success_count,
            "failed": self.error_count,
            "total_duration_ms": self.total_duration_ms,
            "errors": [e.to_dict() for e in self.get_errors()],
        }
