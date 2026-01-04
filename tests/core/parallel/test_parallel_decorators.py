"""
tests/test_parallel_decorators.py - core/parallel/decorators.py 테스트
"""


import pytest
from botocore.exceptions import ClientError

from core.parallel.decorators import (
    DEFAULT_RETRY_CONFIG,
    RETRYABLE_ERROR_CODES,
    RetryConfig,
    categorize_error,
    get_error_code,
    is_retryable,
    safe_aws_call,
    with_retry,
)
from core.parallel.types import ErrorCategory, TaskError


class TestRetryConfig:
    """RetryConfig 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_values(self):
        """커스텀 값 설정"""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False,
        )

        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 60.0
        assert config.exponential_base == 3.0
        assert config.jitter is False

    def test_get_delay_exponential_no_jitter(self):
        """지수 백오프 (jitter 없음)"""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=100.0,
            jitter=False,
        )

        assert config.get_delay(0) == 1.0  # 1 * 2^0 = 1
        assert config.get_delay(1) == 2.0  # 1 * 2^1 = 2
        assert config.get_delay(2) == 4.0  # 1 * 2^2 = 4
        assert config.get_delay(3) == 8.0  # 1 * 2^3 = 8

    def test_get_delay_max_cap(self):
        """최대 지연 시간 제한"""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=5.0,
            jitter=False,
        )

        assert config.get_delay(10) == 5.0  # 2^10 = 1024 > 5, 따라서 5

    def test_get_delay_with_jitter(self):
        """Jitter가 있을 때 랜덤성"""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            jitter=True,
        )

        # jitter가 있으면 매번 다른 값
        delays = [config.get_delay(2) for _ in range(10)]

        # 모든 값이 0과 4.0 사이
        assert all(0 <= d <= 4.0 for d in delays)

        # 값들이 다양해야 함 (확률적으로 거의 항상 참)
        # 10개 중 적어도 2개는 달라야 함
        unique_delays = set(delays)
        assert len(unique_delays) >= 2


class TestDefaultRetryConfig:
    """DEFAULT_RETRY_CONFIG 테스트"""

    def test_default_config_exists(self):
        """기본 설정 존재 확인"""
        assert DEFAULT_RETRY_CONFIG is not None
        assert isinstance(DEFAULT_RETRY_CONFIG, RetryConfig)


class TestRetryableErrorCodes:
    """RETRYABLE_ERROR_CODES 테스트"""

    def test_throttling_codes(self):
        """쓰로틀링 에러 코드 포함"""
        assert "Throttling" in RETRYABLE_ERROR_CODES
        assert "ThrottlingException" in RETRYABLE_ERROR_CODES
        assert "RequestLimitExceeded" in RETRYABLE_ERROR_CODES
        assert "TooManyRequestsException" in RETRYABLE_ERROR_CODES

    def test_service_error_codes(self):
        """서비스 에러 코드 포함"""
        assert "ServiceUnavailable" in RETRYABLE_ERROR_CODES
        assert "InternalError" in RETRYABLE_ERROR_CODES

    def test_timeout_codes(self):
        """타임아웃 에러 코드 포함"""
        assert "RequestTimeout" in RETRYABLE_ERROR_CODES


class TestCategorizeError:
    """categorize_error 함수 테스트"""

    def test_throttling_error(self):
        """쓰로틀링 에러 분류"""
        error = ClientError(
            {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
            "describe_instances",
        )
        assert categorize_error(error) == ErrorCategory.THROTTLING

    def test_access_denied_error(self):
        """권한 없음 에러 분류"""
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
            "describe_instances",
        )
        assert categorize_error(error) == ErrorCategory.ACCESS_DENIED

    def test_not_found_error(self):
        """리소스 없음 에러 분류"""
        error = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}},
            "describe_instances",
        )
        assert categorize_error(error) == ErrorCategory.NOT_FOUND

    def test_timeout_error(self):
        """타임아웃 에러 분류"""
        error = ClientError(
            {"Error": {"Code": "RequestTimeout", "Message": "Timed out"}},
            "describe_instances",
        )
        assert categorize_error(error) == ErrorCategory.TIMEOUT

    def test_expired_token_error(self):
        """토큰 만료 에러 분류"""
        error = ClientError(
            {"Error": {"Code": "ExpiredToken", "Message": "Token expired"}},
            "describe_instances",
        )
        assert categorize_error(error) == ErrorCategory.EXPIRED_TOKEN

    def test_network_error_connection(self):
        """ConnectionError 분류"""
        error = ConnectionError("Connection refused")
        assert categorize_error(error) == ErrorCategory.NETWORK

    def test_network_error_timeout(self):
        """TimeoutError 분류"""
        error = TimeoutError("Connection timed out")
        assert categorize_error(error) == ErrorCategory.NETWORK

    def test_network_error_os(self):
        """OSError 분류"""
        error = OSError("Network unreachable")
        assert categorize_error(error) == ErrorCategory.NETWORK

    def test_unknown_error(self):
        """알 수 없는 에러 분류"""
        error = ValueError("Some value error")
        assert categorize_error(error) == ErrorCategory.UNKNOWN


class TestGetErrorCode:
    """get_error_code 함수 테스트"""

    def test_client_error_code(self):
        """ClientError에서 코드 추출"""
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "msg"}},
            "operation",
        )
        assert get_error_code(error) == "AccessDenied"

    def test_client_error_no_code(self):
        """Error 블록 없을 때"""
        error = ClientError({"Error": {}}, "operation")
        assert get_error_code(error) == "Unknown"

    def test_generic_exception(self):
        """일반 예외에서 클래스명 반환"""
        error = ValueError("test")
        assert get_error_code(error) == "ValueError"

    def test_custom_exception(self):
        """커스텀 예외에서 클래스명 반환"""

        class CustomError(Exception):
            pass

        error = CustomError("test")
        assert get_error_code(error) == "CustomError"


class TestIsRetryable:
    """is_retryable 함수 테스트"""

    def test_throttling_is_retryable(self):
        """쓰로틀링은 재시도 가능"""
        error = ClientError(
            {"Error": {"Code": "Throttling", "Message": "msg"}},
            "operation",
        )
        assert is_retryable(error) is True

    def test_service_unavailable_is_retryable(self):
        """ServiceUnavailable은 재시도 가능"""
        error = ClientError(
            {"Error": {"Code": "ServiceUnavailable", "Message": "msg"}},
            "operation",
        )
        assert is_retryable(error) is True

    def test_access_denied_not_retryable(self):
        """AccessDenied는 재시도 불가"""
        error = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "msg"}},
            "operation",
        )
        assert is_retryable(error) is False

    def test_not_found_not_retryable(self):
        """NotFound는 재시도 불가"""
        error = ClientError(
            {"Error": {"Code": "ResourceNotFound", "Message": "msg"}},
            "operation",
        )
        assert is_retryable(error) is False

    def test_connection_error_is_retryable(self):
        """ConnectionError는 재시도 가능"""
        error = ConnectionError("Connection refused")
        assert is_retryable(error) is True

    def test_timeout_error_is_retryable(self):
        """TimeoutError는 재시도 가능"""
        error = TimeoutError("Timed out")
        assert is_retryable(error) is True

    def test_os_error_is_retryable(self):
        """OSError는 재시도 가능"""
        error = OSError("Network error")
        assert is_retryable(error) is True

    def test_value_error_not_retryable(self):
        """ValueError는 재시도 불가"""
        error = ValueError("Invalid value")
        assert is_retryable(error) is False


class TestSafeAwsCall:
    """safe_aws_call 데코레이터 테스트"""

    def test_successful_call(self):
        """성공적인 호출"""

        @safe_aws_call(service="ec2", operation="test")
        def successful_func():
            return ["result1", "result2"]

        result = successful_func()
        assert result == ["result1", "result2"]

    def test_non_retryable_error_returns_task_error(self):
        """재시도 불가 에러는 TaskError 반환"""

        @safe_aws_call(
            service="ec2",
            operation="test",
            identifier="test-account",
            region="us-east-1",
        )
        def access_denied_func():
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Not authorized"}},
                "describe_instances",
            )

        result = access_denied_func()

        assert isinstance(result, TaskError)
        assert result.category == ErrorCategory.ACCESS_DENIED
        assert result.error_code == "AccessDenied"
        assert result.identifier == "test-account"
        assert result.region == "us-east-1"

    def test_retryable_error_retries(self):
        """재시도 가능 에러는 재시도 수행"""
        call_count = {"value": 0}

        @safe_aws_call(
            service="ec2",
            operation="test",
            retry_config=RetryConfig(max_retries=2, base_delay=0.01, jitter=False),
        )
        def throttling_func():
            call_count["value"] += 1
            if call_count["value"] < 3:
                raise ClientError(
                    {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
                    "describe_instances",
                )
            return "success"

        result = throttling_func()

        assert result == "success"
        assert call_count["value"] == 3  # 1 + 2 재시도

    def test_max_retries_exceeded(self):
        """최대 재시도 초과"""

        @safe_aws_call(
            service="ec2",
            operation="test",
            retry_config=RetryConfig(max_retries=2, base_delay=0.01, jitter=False),
            identifier="test",
            region="test-region",
        )
        def always_throttling():
            raise ClientError(
                {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
                "describe_instances",
            )

        result = always_throttling()

        assert isinstance(result, TaskError)
        assert "최대 재시도 횟수 초과" in result.message
        assert result.retries == 2

    def test_unexpected_error_handling(self):
        """예상치 못한 에러 처리"""

        @safe_aws_call(
            service="ec2",
            operation="test",
            identifier="test",
            region="test-region",
        )
        def unexpected_error():
            raise ValueError("Unexpected!")

        result = unexpected_error()

        assert isinstance(result, TaskError)
        assert result.error_code == "ValueError"


class TestWithRetry:
    """with_retry 데코레이터 테스트"""

    def test_successful_call(self):
        """성공적인 호출"""

        @with_retry(max_retries=3)
        def successful_func():
            return "success"

        result = successful_func()
        assert result == "success"

    def test_retry_on_client_error(self):
        """ClientError 발생 시 재시도"""
        call_count = {"value": 0}

        @with_retry(max_retries=3, base_delay=0.01)
        def retry_func():
            call_count["value"] += 1
            if call_count["value"] < 2:
                raise ClientError(
                    {"Error": {"Code": "Throttling", "Message": "msg"}},
                    "operation",
                )
            return "success"

        result = retry_func()

        assert result == "success"
        assert call_count["value"] == 2

    def test_non_retryable_error_raises(self):
        """재시도 불가 에러는 즉시 raise"""

        @with_retry(max_retries=3)
        def access_denied():
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "msg"}},
                "operation",
            )

        with pytest.raises(ClientError):
            access_denied()

    def test_max_retries_exceeded_raises(self):
        """최대 재시도 초과 시 raise"""

        @with_retry(max_retries=2, base_delay=0.01)
        def always_fails():
            raise ClientError(
                {"Error": {"Code": "Throttling", "Message": "msg"}},
                "operation",
            )

        with pytest.raises(ClientError):
            always_fails()

    def test_custom_retryable_exceptions_network_error(self):
        """커스텀 재시도 가능 예외 (네트워크 에러)"""
        call_count = {"value": 0}

        # ConnectionError는 is_retryable에서 True를 반환하므로 재시도됨
        @with_retry(
            max_retries=3, base_delay=0.01, retryable_exceptions=(ConnectionError,)
        )
        def retry_connection_error():
            call_count["value"] += 1
            if call_count["value"] < 2:
                raise ConnectionError("Connection failed")
            return "success"

        result = retry_connection_error()

        assert result == "success"
        assert call_count["value"] == 2
