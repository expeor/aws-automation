"""
tests/test_parallel_types.py - core/parallel/types.py 테스트
"""

from datetime import datetime

import pytest

from core.parallel.types import (
    ErrorCategory,
    ParallelExecutionResult,
    TaskError,
    TaskResult,
)


class TestErrorCategory:
    """ErrorCategory 열거형 테스트"""

    def test_all_categories_exist(self):
        """모든 에러 카테고리가 정의되어 있는지 확인"""
        assert ErrorCategory.THROTTLING.value == "throttling"
        assert ErrorCategory.ACCESS_DENIED.value == "access_denied"
        assert ErrorCategory.NOT_FOUND.value == "not_found"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.EXPIRED_TOKEN.value == "expired_token"
        assert ErrorCategory.UNKNOWN.value == "unknown"

    def test_category_count(self):
        """카테고리 개수 확인"""
        assert len(ErrorCategory) == 9


class TestTaskError:
    """TaskError 데이터 클래스 테스트"""

    def test_create_task_error(self):
        """TaskError 생성 테스트"""
        error = TaskError(
            identifier="123456789012",
            region="ap-northeast-2",
            category=ErrorCategory.ACCESS_DENIED,
            error_code="AccessDenied",
            message="User is not authorized",
        )

        assert error.identifier == "123456789012"
        assert error.region == "ap-northeast-2"
        assert error.category == ErrorCategory.ACCESS_DENIED
        assert error.error_code == "AccessDenied"
        assert error.message == "User is not authorized"
        assert error.retries == 0
        assert error.original_exception is None
        assert isinstance(error.timestamp, datetime)

    def test_is_retryable_throttling(self):
        """쓰로틀링 에러는 재시도 가능"""
        error = TaskError(
            identifier="test",
            region="us-east-1",
            category=ErrorCategory.THROTTLING,
            error_code="Throttling",
            message="Rate exceeded",
        )
        assert error.is_retryable() is True

    def test_is_retryable_network(self):
        """네트워크 에러는 재시도 가능"""
        error = TaskError(
            identifier="test",
            region="us-east-1",
            category=ErrorCategory.NETWORK,
            error_code="ConnectionError",
            message="Connection refused",
        )
        assert error.is_retryable() is True

    def test_is_retryable_timeout(self):
        """타임아웃 에러는 재시도 가능"""
        error = TaskError(
            identifier="test",
            region="us-east-1",
            category=ErrorCategory.TIMEOUT,
            error_code="RequestTimeout",
            message="Request timed out",
        )
        assert error.is_retryable() is True

    def test_is_not_retryable_access_denied(self):
        """권한 없음 에러는 재시도 불가"""
        error = TaskError(
            identifier="test",
            region="us-east-1",
            category=ErrorCategory.ACCESS_DENIED,
            error_code="AccessDenied",
            message="Not authorized",
        )
        assert error.is_retryable() is False

    def test_is_not_retryable_not_found(self):
        """리소스 없음 에러는 재시도 불가"""
        error = TaskError(
            identifier="test",
            region="us-east-1",
            category=ErrorCategory.NOT_FOUND,
            error_code="ResourceNotFound",
            message="Resource not found",
        )
        assert error.is_retryable() is False

    def test_to_dict(self):
        """딕셔너리 변환 테스트"""
        error = TaskError(
            identifier="test-account",
            region="eu-west-1",
            category=ErrorCategory.THROTTLING,
            error_code="ThrottlingException",
            message="Too many requests",
            retries=2,
        )

        result = error.to_dict()

        assert result["identifier"] == "test-account"
        assert result["region"] == "eu-west-1"
        assert result["category"] == "throttling"
        assert result["error_code"] == "ThrottlingException"
        assert result["message"] == "Too many requests"
        assert result["retries"] == 2
        assert "timestamp" in result

    def test_str_representation(self):
        """문자열 표현 테스트"""
        error = TaskError(
            identifier="my-account",
            region="us-west-2",
            category=ErrorCategory.ACCESS_DENIED,
            error_code="AccessDenied",
            message="Not allowed",
        )

        assert str(error) == "[my-account/us-west-2] AccessDenied: Not allowed"


class TestTaskResult:
    """TaskResult 데이터 클래스 테스트"""

    def test_create_successful_result(self):
        """성공 결과 생성 테스트"""
        result = TaskResult(
            identifier="account-1",
            region="ap-northeast-2",
            success=True,
            data={"volumes": ["vol-1", "vol-2"]},
            duration_ms=150.5,
        )

        assert result.identifier == "account-1"
        assert result.region == "ap-northeast-2"
        assert result.success is True
        assert result.data == {"volumes": ["vol-1", "vol-2"]}
        assert result.error is None
        assert result.duration_ms == 150.5

    def test_create_failed_result(self):
        """실패 결과 생성 테스트"""
        error = TaskError(
            identifier="account-1",
            region="ap-northeast-2",
            category=ErrorCategory.ACCESS_DENIED,
            error_code="AccessDenied",
            message="Not authorized",
        )

        result = TaskResult(
            identifier="account-1",
            region="ap-northeast-2",
            success=False,
            error=error,
            duration_ms=50.0,
        )

        assert result.success is False
        assert result.data is None
        assert result.error is error

    def test_str_representation_success(self):
        """성공 결과 문자열 표현"""
        result = TaskResult(
            identifier="test",
            region="us-east-1",
            success=True,
            duration_ms=100.0,
        )
        assert str(result) == "[test/us-east-1] OK (100ms)"

    def test_str_representation_failure(self):
        """실패 결과 문자열 표현"""
        result = TaskResult(
            identifier="test",
            region="us-east-1",
            success=False,
            duration_ms=50.0,
        )
        assert str(result) == "[test/us-east-1] FAIL (50ms)"


class TestParallelExecutionResult:
    """ParallelExecutionResult 테스트"""

    @pytest.fixture
    def mixed_results(self):
        """성공/실패가 섞인 결과"""
        success1 = TaskResult(
            identifier="account-1",
            region="us-east-1",
            success=True,
            data=["item1", "item2"],
            duration_ms=100.0,
        )
        success2 = TaskResult(
            identifier="account-2",
            region="us-east-1",
            success=True,
            data=["item3"],
            duration_ms=150.0,
        )
        failure1 = TaskResult(
            identifier="account-3",
            region="us-east-1",
            success=False,
            error=TaskError(
                identifier="account-3",
                region="us-east-1",
                category=ErrorCategory.ACCESS_DENIED,
                error_code="AccessDenied",
                message="Not authorized",
            ),
            duration_ms=50.0,
        )
        failure2 = TaskResult(
            identifier="account-4",
            region="us-east-1",
            success=False,
            error=TaskError(
                identifier="account-4",
                region="us-east-1",
                category=ErrorCategory.THROTTLING,
                error_code="Throttling",
                message="Rate exceeded",
            ),
            duration_ms=30.0,
        )

        return ParallelExecutionResult(results=[success1, success2, failure1, failure2])

    def test_empty_result(self):
        """빈 결과 테스트"""
        result = ParallelExecutionResult()

        assert result.total_count == 0
        assert result.success_count == 0
        assert result.error_count == 0
        assert result.has_any_success() is False
        assert result.has_any_failure() is False
        assert result.has_failures_only() is False

    def test_successful_property(self, mixed_results):
        """성공한 결과 필터링"""
        successful = mixed_results.successful
        assert len(successful) == 2
        assert all(r.success for r in successful)

    def test_failed_property(self, mixed_results):
        """실패한 결과 필터링"""
        failed = mixed_results.failed
        assert len(failed) == 2
        assert all(not r.success for r in failed)

    def test_counts(self, mixed_results):
        """카운트 속성 테스트"""
        assert mixed_results.total_count == 4
        assert mixed_results.success_count == 2
        assert mixed_results.error_count == 2

    def test_total_duration(self, mixed_results):
        """총 실행 시간 계산"""
        assert mixed_results.total_duration_ms == 330.0  # 100 + 150 + 50 + 30

    def test_has_any_success(self, mixed_results):
        """하나 이상 성공 확인"""
        assert mixed_results.has_any_success() is True

    def test_has_any_failure(self, mixed_results):
        """하나 이상 실패 확인"""
        assert mixed_results.has_any_failure() is True

    def test_has_failures_only(self, mixed_results):
        """모두 실패인지 확인"""
        assert mixed_results.has_failures_only() is False

        # 모두 실패인 경우
        all_failed = ParallelExecutionResult(
            results=[
                TaskResult(
                    identifier="a",
                    region="r",
                    success=False,
                    error=TaskError(
                        identifier="a",
                        region="r",
                        category=ErrorCategory.UNKNOWN,
                        error_code="Error",
                        message="msg",
                    ),
                )
            ]
        )
        assert all_failed.has_failures_only() is True

    def test_get_data(self, mixed_results):
        """성공 데이터 추출"""
        data = mixed_results.get_data()
        assert len(data) == 2
        assert ["item1", "item2"] in data
        assert ["item3"] in data

    def test_get_data_excludes_none(self):
        """None 데이터 제외"""
        result = ParallelExecutionResult(
            results=[
                TaskResult(
                    identifier="a",
                    region="r",
                    success=True,
                    data=None,  # None 데이터
                ),
                TaskResult(
                    identifier="b",
                    region="r",
                    success=True,
                    data="valid",
                ),
            ]
        )
        data = result.get_data()
        assert data == ["valid"]

    def test_get_flat_data(self, mixed_results):
        """평탄화된 데이터 추출"""
        flat = mixed_results.get_flat_data()
        assert flat == ["item1", "item2", "item3"]

    def test_get_flat_data_non_list(self):
        """리스트가 아닌 데이터 평탄화"""
        result = ParallelExecutionResult(
            results=[
                TaskResult(
                    identifier="a",
                    region="r",
                    success=True,
                    data="single",
                ),
                TaskResult(
                    identifier="b",
                    region="r",
                    success=True,
                    data=["list1", "list2"],
                ),
            ]
        )
        flat = result.get_flat_data()
        assert flat == ["single", "list1", "list2"]

    def test_get_errors(self, mixed_results):
        """에러 목록 추출"""
        errors = mixed_results.get_errors()
        assert len(errors) == 2
        assert all(isinstance(e, TaskError) for e in errors)

    def test_get_errors_by_category(self, mixed_results):
        """카테고리별 에러 그룹화"""
        by_category = mixed_results.get_errors_by_category()

        assert ErrorCategory.ACCESS_DENIED in by_category
        assert ErrorCategory.THROTTLING in by_category
        assert len(by_category[ErrorCategory.ACCESS_DENIED]) == 1
        assert len(by_category[ErrorCategory.THROTTLING]) == 1

    def test_get_error_summary(self, mixed_results):
        """에러 요약 문자열"""
        summary = mixed_results.get_error_summary()

        assert "총 2개 작업 실패" in summary
        assert "[access_denied]" in summary
        assert "[throttling]" in summary
        assert "account-3/us-east-1" in summary
        assert "account-4/us-east-1" in summary

    def test_get_error_summary_empty(self):
        """에러 없을 때 요약"""
        result = ParallelExecutionResult()
        assert result.get_error_summary() == ""

    def test_get_error_summary_truncation(self):
        """에러 요약 truncation 테스트"""
        # 같은 카테고리 에러 5개 생성
        errors = [
            TaskResult(
                identifier=f"account-{i}",
                region="us-east-1",
                success=False,
                error=TaskError(
                    identifier=f"account-{i}",
                    region="us-east-1",
                    category=ErrorCategory.THROTTLING,
                    error_code="Throttling",
                    message="Rate exceeded",
                ),
            )
            for i in range(5)
        ]

        result = ParallelExecutionResult(results=errors)
        summary = result.get_error_summary(max_per_category=2)

        assert "총 5개 작업 실패" in summary
        assert "외 3건" in summary

    def test_to_dict(self, mixed_results):
        """딕셔너리 변환"""
        d = mixed_results.to_dict()

        assert d["total"] == 4
        assert d["success"] == 2
        assert d["failed"] == 2
        assert d["total_duration_ms"] == 330.0
        assert len(d["errors"]) == 2
