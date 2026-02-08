"""
core/parallel/decorators.py - AWS API 호출 안전 래퍼 데코레이터

AWS API 호출을 안전하게 래핑하는 데코레이터들을 제공합니다.

주요 구성 요소:
- RetryConfig: 재시도 설정 (지수 백오프 + 지터)
- @safe_aws_call: Rate limiting + 재시도 + 구조화된 에러 처리 (TaskError 반환)
- @with_retry: 간단한 재시도 데코레이터 (예외 그대로 raise, 하위 호환용)
- categorize_error: 예외를 ErrorCategory로 분류
- get_error_code: 예외에서 에러 코드 추출
- is_retryable: 재시도 가능 여부 판단

Example:
    @safe_aws_call(service="ec2", operation="describe_instances")
    def get_instances(session, region):
        ec2 = session.client("ec2", region_name=region)
        return ec2.describe_instances()["Reservations"]
"""

import functools
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from botocore.exceptions import ClientError

from core.exceptions import is_access_denied, is_not_found, is_throttling

from .rate_limiter import TokenBucketRateLimiter, get_rate_limiter
from .types import ErrorCategory, TaskError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """재시도 설정

    Attributes:
        max_retries: 최대 재시도 횟수 (0이면 재시도 안함)
        base_delay: 기본 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)
        exponential_base: 지수 백오프 밑수
        jitter: 지터 사용 여부 (대기 시간에 랜덤성 추가)
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """재시도 대기 시간 계산

        Exponential backoff with optional jitter.

        Args:
            attempt: 현재 시도 횟수 (0부터 시작)

        Returns:
            대기 시간 (초)
        """
        delay = self.base_delay * (self.exponential_base**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Full jitter: [0, delay]
            delay = random.uniform(0, delay)

        return delay


# 기본 재시도 설정
DEFAULT_RETRY_CONFIG = RetryConfig()

# 재시도 가능한 AWS 에러 코드
RETRYABLE_ERROR_CODES: set[str] = {
    "Throttling",
    "ThrottlingException",
    "RequestLimitExceeded",
    "TooManyRequestsException",
    "RateExceeded",
    "ServiceUnavailable",
    "ServiceUnavailableException",
    "InternalError",
    "InternalServiceError",
    "RequestTimeout",
    "RequestTimeoutException",
    "ProvisionedThroughputExceededException",
    "SlowDown",
}


def categorize_error(error: Exception) -> ErrorCategory:
    """예외 객체를 분석하여 ErrorCategory로 분류

    ClientError의 경우 response에서 에러 코드를 추출하고,
    네트워크/타임아웃 에러는 타입으로 분류합니다.

    Args:
        error: 분류할 예외

    Returns:
        에러 카테고리
    """
    # 기존 유틸리티 함수 활용
    if is_throttling(error):
        return ErrorCategory.THROTTLING
    if is_access_denied(error):
        return ErrorCategory.ACCESS_DENIED
    if is_not_found(error):
        return ErrorCategory.NOT_FOUND

    # ClientError 상세 분류
    response = getattr(error, "response", None)
    if response is not None:
        error_code = response.get("Error", {}).get("Code", "")

        if "Timeout" in error_code:
            return ErrorCategory.TIMEOUT

        if error_code in ("ExpiredToken", "ExpiredTokenException"):
            return ErrorCategory.EXPIRED_TOKEN

    # 네트워크 에러
    if isinstance(error, (ConnectionError, TimeoutError, OSError)):
        return ErrorCategory.NETWORK

    return ErrorCategory.UNKNOWN


def get_error_code(error: Exception) -> str:
    """예외 객체에서 에러 코드 문자열 추출

    ClientError의 경우 response에서 Code를 추출하고,
    그 외에는 예외 클래스명을 반환합니다.

    Args:
        error: 예외 객체

    Returns:
        에러 코드 문자열
    """
    response = getattr(error, "response", None)
    if response is not None:
        code: str = response.get("Error", {}).get("Code", "Unknown")
        return code
    return error.__class__.__name__


def is_retryable(error: Exception) -> bool:
    """재시도 가능한 에러인지 확인

    RETRYABLE_ERROR_CODES에 포함된 에러 코드이거나
    네트워크/타임아웃 에러인 경우 True를 반환합니다.

    Args:
        error: 확인할 예외

    Returns:
        재시도 가능하면 True
    """
    response = getattr(error, "response", None)
    if response is not None:
        error_code = response.get("Error", {}).get("Code", "")
        return error_code in RETRYABLE_ERROR_CODES

    return isinstance(error, (ConnectionError, TimeoutError, OSError))


def safe_aws_call(
    service: str = "default",
    operation: str = "",
    retry_config: RetryConfig | None = None,
    rate_limiter: TokenBucketRateLimiter | None = None,
    identifier: str = "",
    region: str = "",
) -> Callable[[Callable[..., T]], Callable[..., T | TaskError]]:
    """AWS API 호출을 안전하게 래핑하는 데코레이터

    기능:
    - Rate limiting (토큰 버킷)
    - 재시도 (지수 백오프 + 지터)
    - 구조화된 에러 분류 및 로깅

    Args:
        service: AWS 서비스 이름 (rate limit 결정용)
        operation: API 작업 이름 (로깅용)
        retry_config: 재시도 설정 (None이면 기본값)
        rate_limiter: Rate limiter (None이면 서비스별 기본값)
        identifier: 계정/프로파일 식별자 (에러 추적용)
        region: 리전 (에러 추적용)

    Returns:
        데코레이터 함수

    Example:
        @safe_aws_call(service="ec2", operation="describe_volumes")
        def get_volumes(session, region):
            ec2 = session.client("ec2", region_name=region)
            return ec2.describe_volumes()["Volumes"]

        result = get_volumes(session, "ap-northeast-2")
        if isinstance(result, TaskError):
            print(f"Error: {result.message}")
        else:
            print(f"Found {len(result)} volumes")
    """
    config = retry_config or DEFAULT_RETRY_CONFIG
    limiter = rate_limiter or get_rate_limiter(service)

    def decorator(func: Callable[..., T]) -> Callable[..., T | TaskError]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T | TaskError:
            last_error: Exception | None = None
            op_name = operation or func.__name__

            for attempt in range(config.max_retries + 1):
                # Rate limiting
                if not limiter.acquire():
                    logger.warning(f"Rate limit timeout: {service}.{op_name}")
                    return TaskError(
                        identifier=identifier,
                        region=region,
                        category=ErrorCategory.THROTTLING,
                        error_code="RateLimitTimeout",
                        message="Rate limiter timeout - 요청이 너무 많습니다",
                        retries=attempt,
                    )

                try:
                    return func(*args, **kwargs)

                except ClientError as e:
                    last_error = e
                    error_code = get_error_code(e)
                    category = categorize_error(e)

                    logger.debug(
                        f"[{service}.{op_name}] 시도 {attempt + 1}/{config.max_retries + 1} 실패: {error_code}"
                    )

                    # 재시도 불가능한 에러는 즉시 반환
                    if not is_retryable(e):
                        return TaskError(
                            identifier=identifier,
                            region=region,
                            category=category,
                            error_code=error_code,
                            message=str(e),
                            retries=attempt,
                            original_exception=e,
                        )

                    # 마지막 시도면 에러 반환
                    if attempt >= config.max_retries:
                        break

                    # 재시도 대기
                    delay = config.get_delay(attempt)
                    logger.debug(f"[{service}.{op_name}] {delay:.2f}초 후 재시도...")
                    time.sleep(delay)

                except Exception as e:
                    # 예상치 못한 에러
                    last_error = e
                    category = categorize_error(e)

                    logger.warning(f"[{service}.{op_name}] 예상치 못한 에러: {e.__class__.__name__}: {e}")

                    # 네트워크 에러 등은 재시도 가능
                    if is_retryable(e) and attempt < config.max_retries:
                        delay = config.get_delay(attempt)
                        time.sleep(delay)
                        continue

                    return TaskError(
                        identifier=identifier,
                        region=region,
                        category=category,
                        error_code=e.__class__.__name__,
                        message=str(e),
                        retries=attempt,
                        original_exception=e,
                    )

            # 재시도 소진
            return TaskError(
                identifier=identifier,
                region=region,
                category=(categorize_error(last_error) if last_error else ErrorCategory.UNKNOWN),
                error_code=get_error_code(last_error) if last_error else "Unknown",
                message=f"최대 재시도 횟수 초과 ({config.max_retries}회)",
                retries=config.max_retries,
                original_exception=last_error,
            )

        return wrapper

    return decorator


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (ClientError,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """간단한 재시도 데코레이터 (하위 호환용)

    기존 코드와의 호환성을 위한 단순화된 버전.
    에러 시 TaskError를 반환하지 않고 예외를 그대로 raise합니다.

    Args:
        max_retries: 최대 재시도 횟수
        base_delay: 기본 대기 시간 (초)
        max_delay: 최대 대기 시간 (초)
        retryable_exceptions: 재시도할 예외 타입들

    Returns:
        데코레이터 함수

    Example:
        @with_retry(max_retries=3)
        def risky_operation():
            ...
    """
    config = RetryConfig(max_retries=max_retries, base_delay=base_delay, max_delay=max_delay)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error: Exception | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_error = e

                    # 재시도 불가능하거나 마지막 시도면 raise
                    if not is_retryable(e) or attempt >= config.max_retries:
                        raise

                    delay = config.get_delay(attempt)
                    logger.debug(f"[{func.__name__}] 시도 {attempt + 1} 실패, {delay:.2f}초 후 재시도...")
                    time.sleep(delay)

            # 여기 도달하면 안 됨
            if last_error:
                raise last_error
            raise RuntimeError("Unexpected state in retry loop")

        return wrapper

    return decorator
