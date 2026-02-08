"""
core/parallel/decorators.py - AWS API 에러 분류 및 재시도 유틸리티

AWS API 호출의 에러 분류, 재시도 가능 여부 판단,
지수 백오프 재시도 설정을 제공합니다.

주요 구성 요소:
- RetryConfig: 재시도 설정 (지수 백오프 + 지터)
- categorize_error: 예외를 ErrorCategory로 분류
- get_error_code: 예외에서 에러 코드 추출
- is_retryable: 재시도 가능 여부 판단
"""

import logging
import random
from dataclasses import dataclass

from core.exceptions import is_access_denied, is_not_found, is_throttling

from .types import ErrorCategory

logger = logging.getLogger(__name__)


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
