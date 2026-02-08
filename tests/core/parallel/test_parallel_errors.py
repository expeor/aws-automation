"""
tests/test_parallel_errors.py - core/parallel/errors.py 테스트
"""

import threading
from datetime import datetime

from botocore.exceptions import ClientError

from core.parallel.errors import (
    CollectedError,
    ErrorCategory,
    ErrorCollector,
    ErrorSeverity,
    categorize_error_code,
    safe_collect,
    try_or_default,
)


class TestErrorSeverity:
    """ErrorSeverity 열거형 테스트"""

    def test_all_severities_exist(self):
        """모든 심각도 레벨 존재 확인"""
        assert ErrorSeverity.CRITICAL.value == "critical"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.INFO.value == "info"
        assert ErrorSeverity.DEBUG.value == "debug"


class TestErrorCategory:
    """ErrorCategory 열거형 테스트"""

    def test_all_categories_exist(self):
        """모든 카테고리 존재 확인"""
        assert ErrorCategory.ACCESS_DENIED.value == "access_denied"
        assert ErrorCategory.NOT_FOUND.value == "not_found"
        assert ErrorCategory.THROTTLING.value == "throttling"
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.INVALID_REQUEST.value == "invalid_request"
        assert ErrorCategory.SERVICE_ERROR.value == "service_error"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestCollectedError:
    """CollectedError 데이터 클래스 테스트"""

    def test_create_collected_error(self):
        """CollectedError 생성"""
        now = datetime.now()
        error = CollectedError(
            timestamp=now,
            account_id="123456789012",
            account_name="my-account",
            region="us-east-1",
            service="lambda",
            operation="list_functions",
            error_code="AccessDenied",
            error_message="Not authorized",
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.ACCESS_DENIED,
            resource_id="arn:aws:lambda:...",
        )

        assert error.timestamp == now
        assert error.account_id == "123456789012"
        assert error.account_name == "my-account"
        assert error.region == "us-east-1"
        assert error.service == "lambda"
        assert error.operation == "list_functions"
        assert error.error_code == "AccessDenied"
        assert error.error_message == "Not authorized"
        assert error.severity == ErrorSeverity.WARNING
        assert error.category == ErrorCategory.ACCESS_DENIED
        assert error.resource_id == "arn:aws:lambda:..."

    def test_str_representation(self):
        """문자열 표현"""
        error = CollectedError(
            timestamp=datetime.now(),
            account_id="123",
            account_name="test-account",
            region="us-west-2",
            service="ec2",
            operation="describe_instances",
            error_code="Throttling",
            error_message="Rate exceeded",
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.THROTTLING,
        )

        result = str(error)
        assert "[WARNING]" in result
        assert "test-account/us-west-2" in result
        assert "ec2.describe_instances" in result
        assert "Throttling" in result

    def test_to_dict(self):
        """딕셔너리 변환"""
        now = datetime.now()
        error = CollectedError(
            timestamp=now,
            account_id="123",
            account_name="test",
            region="us-east-1",
            service="s3",
            operation="list_buckets",
            error_code="AccessDenied",
            error_message="msg",
            severity=ErrorSeverity.INFO,
            category=ErrorCategory.ACCESS_DENIED,
            resource_id="bucket-name",
        )

        result = error.to_dict()

        assert result["timestamp"] == now.isoformat()
        assert result["account_id"] == "123"
        assert result["account_name"] == "test"
        assert result["region"] == "us-east-1"
        assert result["service"] == "s3"
        assert result["operation"] == "list_buckets"
        assert result["error_code"] == "AccessDenied"
        assert result["error_message"] == "msg"
        assert result["severity"] == "info"
        assert result["category"] == "access_denied"
        assert result["resource_id"] == "bucket-name"


class TestCategorizeErrorCode:
    """categorize_error_code 함수 테스트"""

    def test_access_denied(self):
        """AccessDenied 분류"""
        assert categorize_error_code("AccessDenied") == ErrorCategory.ACCESS_DENIED
        assert categorize_error_code("UnauthorizedAccess") == ErrorCategory.ACCESS_DENIED
        assert categorize_error_code("Forbidden") == ErrorCategory.ACCESS_DENIED

    def test_not_found(self):
        """NotFound 분류"""
        assert categorize_error_code("ResourceNotFound") == ErrorCategory.NOT_FOUND
        assert categorize_error_code("NoSuchBucket") == ErrorCategory.NOT_FOUND
        assert categorize_error_code("FunctionDoesNotExist") == ErrorCategory.NOT_FOUND

    def test_throttling(self):
        """Throttling 분류"""
        assert categorize_error_code("Throttling") == ErrorCategory.THROTTLING
        assert categorize_error_code("RateLimitExceeded") == ErrorCategory.THROTTLING
        assert categorize_error_code("TooManyRequests") == ErrorCategory.THROTTLING

    def test_timeout(self):
        """Timeout 분류"""
        assert categorize_error_code("RequestTimeout") == ErrorCategory.TIMEOUT
        assert categorize_error_code("TimedOut") == ErrorCategory.TIMEOUT

    def test_invalid_request(self):
        """Invalid request 분류"""
        assert categorize_error_code("InvalidParameterValue") == ErrorCategory.INVALID_REQUEST
        assert categorize_error_code("ValidationError") == ErrorCategory.INVALID_REQUEST
        assert categorize_error_code("MalformedRequest") == ErrorCategory.INVALID_REQUEST

    def test_service_error(self):
        """Service error 분류"""
        assert categorize_error_code("InternalError") == ErrorCategory.SERVICE_ERROR
        assert categorize_error_code("ServiceUnavailable") == ErrorCategory.SERVICE_ERROR

    def test_unknown(self):
        """Unknown 분류"""
        assert categorize_error_code("SomeRandomError") == ErrorCategory.UNKNOWN
        assert categorize_error_code("") == ErrorCategory.UNKNOWN


class TestErrorCollector:
    """ErrorCollector 테스트"""

    def test_init(self):
        """초기화"""
        collector = ErrorCollector("lambda")

        assert collector.service == "lambda"
        assert collector.errors == []
        assert collector.has_errors is False

    def test_collect_client_error(self):
        """ClientError 수집"""
        collector = ErrorCollector("ec2")

        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
            "describe_instances",
        )

        collector.collect(
            error=error,
            account_id="123",
            account_name="test-account",
            region="us-east-1",
            operation="describe_instances",
        )

        assert collector.has_errors is True
        assert len(collector.errors) == 1

        collected = collector.errors[0]
        assert collected.error_code == "AccessDenied"
        assert collected.error_message == "Not authorized"
        assert collected.category == ErrorCategory.ACCESS_DENIED
        # AccessDenied는 INFO로 다운그레이드됨
        assert collected.severity == ErrorSeverity.INFO

    def test_collect_with_resource_id(self):
        """리소스 ID 포함 수집"""
        collector = ErrorCollector("s3")

        error = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "Bucket not found"}},
            "get_bucket_location",
        )

        collector.collect(
            error=error,
            account_id="123",
            account_name="test",
            region="us-east-1",
            operation="get_bucket_location",
            resource_id="my-bucket",
        )

        assert collector.errors[0].resource_id == "my-bucket"

    def test_collect_generic_error(self):
        """일반 에러 수집"""
        collector = ErrorCollector("custom")

        collector.collect_generic(
            error_code="CustomError",
            error_message="Something went wrong",
            account_id="123",
            account_name="test",
            region="us-east-1",
            operation="custom_operation",
            severity=ErrorSeverity.CRITICAL,
        )

        assert collector.has_errors is True
        collected = collector.errors[0]
        assert collected.error_code == "CustomError"
        assert collected.severity == ErrorSeverity.CRITICAL

    def test_critical_errors(self):
        """CRITICAL 에러만 필터링"""
        collector = ErrorCollector("test")

        # CRITICAL 에러
        collector.collect_generic(
            error_code="Critical1",
            error_message="msg",
            account_id="1",
            account_name="a",
            region="r",
            operation="op",
            severity=ErrorSeverity.CRITICAL,
        )

        # WARNING 에러
        collector.collect_generic(
            error_code="Warning1",
            error_message="msg",
            account_id="2",
            account_name="b",
            region="r",
            operation="op",
            severity=ErrorSeverity.WARNING,
        )

        assert len(collector.critical_errors) == 1
        assert collector.critical_errors[0].error_code == "Critical1"

    def test_warning_errors(self):
        """WARNING 에러만 필터링"""
        collector = ErrorCollector("test")

        collector.collect_generic(
            error_code="Critical1",
            error_message="msg",
            account_id="1",
            account_name="a",
            region="r",
            operation="op",
            severity=ErrorSeverity.CRITICAL,
        )

        collector.collect_generic(
            error_code="Warning1",
            error_message="msg",
            account_id="2",
            account_name="b",
            region="r",
            operation="op",
            severity=ErrorSeverity.WARNING,
        )

        assert len(collector.warning_errors) == 1
        assert collector.warning_errors[0].error_code == "Warning1"

    def test_get_summary_empty(self):
        """빈 상태 요약"""
        collector = ErrorCollector("test")
        assert collector.get_summary() == "에러 없음"

    def test_get_summary_with_errors(self):
        """에러 있을 때 요약"""
        collector = ErrorCollector("test")

        collector.collect_generic(
            error_code="E1",
            error_message="m",
            account_id="1",
            account_name="a",
            region="r",
            operation="op",
            severity=ErrorSeverity.CRITICAL,
        )
        collector.collect_generic(
            error_code="E2",
            error_message="m",
            account_id="2",
            account_name="b",
            region="r",
            operation="op",
            severity=ErrorSeverity.WARNING,
        )

        summary = collector.get_summary()

        assert "에러 2건" in summary
        assert "critical: 1건" in summary
        assert "warning: 1건" in summary

    def test_get_by_account(self):
        """계정별 그룹핑"""
        collector = ErrorCollector("test")

        collector.collect_generic(
            error_code="E1",
            error_message="m",
            account_id="111",
            account_name="account-a",
            region="r",
            operation="op",
            severity=ErrorSeverity.WARNING,
        )
        collector.collect_generic(
            error_code="E2",
            error_message="m",
            account_id="111",
            account_name="account-a",
            region="r",
            operation="op",
            severity=ErrorSeverity.WARNING,
        )
        collector.collect_generic(
            error_code="E3",
            error_message="m",
            account_id="222",
            account_name="account-b",
            region="r",
            operation="op",
            severity=ErrorSeverity.WARNING,
        )

        by_account = collector.get_by_account()

        assert len(by_account) == 2
        assert len(by_account["account-a (111)"]) == 2
        assert len(by_account["account-b (222)"]) == 1

    def test_clear(self):
        """에러 초기화"""
        collector = ErrorCollector("test")

        collector.collect_generic(
            error_code="E1",
            error_message="m",
            account_id="1",
            account_name="a",
            region="r",
            operation="op",
            severity=ErrorSeverity.WARNING,
        )

        assert collector.has_errors is True

        collector.clear()

        assert collector.has_errors is False
        assert len(collector.errors) == 0

    def test_thread_safety(self):
        """스레드 안전성"""
        collector = ErrorCollector("test")
        error_count = 100

        def add_error(i):
            collector.collect_generic(
                error_code=f"E{i}",
                error_message="m",
                account_id=str(i),
                account_name=f"account-{i}",
                region="r",
                operation="op",
                severity=ErrorSeverity.WARNING,
            )

        threads = [threading.Thread(target=add_error, args=(i,)) for i in range(error_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(collector.errors) == error_count


class TestSafeCollect:
    """safe_collect 함수 테스트"""

    def test_with_collector(self):
        """collector가 있을 때"""
        collector = ErrorCollector("test")

        error = ClientError(
            {"Error": {"Code": "Throttling", "Message": "msg"}},
            "operation",
        )

        safe_collect(
            collector=collector,
            error=error,
            account_id="123",
            account_name="test",
            region="us-east-1",
            operation="test_op",
        )

        assert collector.has_errors is True

    def test_without_collector(self):
        """collector가 None일 때 (로깅만)"""
        error = ClientError(
            {"Error": {"Code": "Throttling", "Message": "msg"}},
            "operation",
        )

        # 예외 없이 동작해야 함
        safe_collect(
            collector=None,
            error=error,
            account_id="123",
            account_name="test",
            region="us-east-1",
            operation="test_op",
        )


class TestTryOrDefault:
    """try_or_default 함수 테스트"""

    def test_success_returns_result(self):
        """성공 시 결과 반환"""
        result = try_or_default(lambda: "success", default="default")
        assert result == "success"

    def test_failure_returns_default(self):
        """실패 시 기본값 반환"""

        def failing_func():
            raise ValueError("error")

        result = try_or_default(failing_func, default="default")
        assert result == "default"

    def test_client_error_returns_default(self):
        """ClientError 발생 시 기본값 반환"""

        def aws_call():
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "msg"}},
                "operation",
            )

        result = try_or_default(aws_call, default=[])
        assert result == []

    def test_with_collector(self):
        """collector와 함께 사용"""
        collector = ErrorCollector("test")

        def aws_call():
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "msg"}},
                "operation",
            )

        result = try_or_default(
            aws_call,
            default={},
            collector=collector,
            account_id="123",
            account_name="test",
            region="us-east-1",
            operation="test_op",
            severity=ErrorSeverity.WARNING,
        )

        assert result == {}
        assert collector.has_errors is True

    def test_generic_exception_collected(self):
        """일반 예외도 수집"""
        collector = ErrorCollector("test")

        def generic_error():
            raise RuntimeError("Something failed")

        result = try_or_default(
            generic_error,
            default=None,
            collector=collector,
            account_id="123",
            account_name="test",
            region="us-east-1",
            operation="test_op",
        )

        assert result is None
        assert collector.has_errors is True
        assert collector.errors[0].error_code == "UnexpectedError"
