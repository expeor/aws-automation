"""
core/parallel/rate_limiter.py - Token Bucket 기반 Rate Limiter

AWS API 쓰로틀링 방지를 위한 요청 속도 제한 구현.
Thread-safe하며, 버스트 트래픽을 허용하면서 장기적으로
일정한 요청 속도를 유지합니다.
"""

import threading
import time
from dataclasses import dataclass


@dataclass
class RateLimiterConfig:
    """Rate Limiter 설정

    Attributes:
        requests_per_second: 초당 허용 요청 수 (토큰 생성 속도)
        burst_size: 버스트 허용량 (최대 토큰 수)
        wait_timeout: 토큰 대기 최대 시간 (초)
    """

    requests_per_second: float = 10.0
    burst_size: int = 20
    wait_timeout: float = 30.0


class TokenBucketRateLimiter:
    """Token Bucket 알고리즘 기반 Rate Limiter

    Thread-safe하며, 버스트 트래픽을 허용하면서
    장기적으로 일정한 요청 속도를 유지합니다.

    Algorithm:
        - 버킷에는 최대 burst_size개의 토큰이 담길 수 있음
        - 매 초마다 requests_per_second개의 토큰이 추가됨
        - 요청 시 토큰을 소비, 토큰이 없으면 대기

    Example:
        limiter = TokenBucketRateLimiter(
            RateLimiterConfig(requests_per_second=10, burst_size=20)
        )

        # 요청 전 호출 (토큰 없으면 대기)
        if limiter.acquire():
            make_api_call()

        # 또는 즉시 시도 (대기 없이)
        if limiter.try_acquire():
            make_api_call()
        else:
            print("Rate limit 초과")
    """

    def __init__(self, config: RateLimiterConfig | None = None):
        """초기화

        Args:
            config: Rate limiter 설정. None이면 기본값 사용.
        """
        self.config = config or RateLimiterConfig()
        self._tokens = float(self.config.burst_size)  # 초기에는 버스트 허용
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """토큰 획득 (없으면 대기)

        토큰이 부족하면 생성될 때까지 대기합니다.
        wait_timeout 시간 내에 획득하지 못하면 False를 반환합니다.

        Args:
            tokens: 필요한 토큰 수

        Returns:
            True if 획득 성공, False if 타임아웃
        """
        deadline = time.monotonic() + self.config.wait_timeout

        while True:
            with self._lock:
                self._refill()

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

                # 다음 토큰까지 필요한 대기 시간 계산
                tokens_needed = tokens - self._tokens
                wait_time = tokens_needed / self.config.requests_per_second

            # 타임아웃 체크
            if time.monotonic() >= deadline:
                return False

            # 대기 (락 해제 상태에서)
            actual_wait = min(wait_time, 0.1, deadline - time.monotonic())
            if actual_wait > 0:
                time.sleep(actual_wait)

    def try_acquire(self, tokens: int = 1) -> bool:
        """토큰 획득 시도 (대기 없이)

        즉시 토큰 획득을 시도하고 결과를 반환합니다.
        토큰이 부족하면 대기 없이 바로 False를 반환합니다.

        Args:
            tokens: 필요한 토큰 수

        Returns:
            True if 획득 성공
        """
        with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def _refill(self) -> None:
        """토큰 보충 (락 내에서 호출)

        마지막 보충 이후 경과 시간에 비례하여 토큰을 추가합니다.
        """
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now

        new_tokens = elapsed * self.config.requests_per_second
        self._tokens = min(self.config.burst_size, self._tokens + new_tokens)

    @property
    def available_tokens(self) -> float:
        """현재 사용 가능한 토큰 수 (근사치)"""
        with self._lock:
            self._refill()
            return self._tokens


# =============================================================================
# 서비스별 기본 Rate Limiter 설정
# =============================================================================

# AWS 서비스별 API Rate Limit 참고 설정
# 실제 AWS 제한보다 보수적으로 설정하여 안전 마진 확보
SERVICE_RATE_LIMITS: dict[str, RateLimiterConfig] = {
    # EC2: 대부분의 Describe API는 초당 100회까지 가능
    "ec2": RateLimiterConfig(requests_per_second=20, burst_size=40),
    # IAM: 초당 20회 정도
    "iam": RateLimiterConfig(requests_per_second=10, burst_size=20),
    # STS: 초당 100회 이상 가능
    "sts": RateLimiterConfig(requests_per_second=20, burst_size=40),
    # CloudWatch: 초당 50회 정도
    "cloudwatch": RateLimiterConfig(requests_per_second=20, burst_size=40),
    # S3: 버킷당 3,500 PUT/초, 5,500 GET/초
    "s3": RateLimiterConfig(requests_per_second=50, burst_size=100),
    # RDS: 초당 10~20회
    "rds": RateLimiterConfig(requests_per_second=10, burst_size=20),
    # ELB/ELBV2: 초당 20회 정도
    "elb": RateLimiterConfig(requests_per_second=15, burst_size=30),
    "elbv2": RateLimiterConfig(requests_per_second=15, burst_size=30),
    # Lambda: 초당 15회 정도
    "lambda": RateLimiterConfig(requests_per_second=10, burst_size=20),
    # Organizations: 초당 5회 정도 (매우 제한적)
    "organizations": RateLimiterConfig(requests_per_second=5, burst_size=10),
    # SSO Admin: 초당 10회 정도
    "sso-admin": RateLimiterConfig(requests_per_second=8, burst_size=15),
    # Secrets Manager: 초당 20회 정도
    "secretsmanager": RateLimiterConfig(requests_per_second=15, burst_size=30),
    # KMS: 초당 100회 이상
    "kms": RateLimiterConfig(requests_per_second=30, burst_size=60),
    # Route53: 초당 5회 정도
    "route53": RateLimiterConfig(requests_per_second=5, burst_size=10),
    # ECR: 초당 10회 정도
    "ecr": RateLimiterConfig(requests_per_second=10, burst_size=20),
    # CloudWatch Logs: 초당 25회 정도
    "logs": RateLimiterConfig(requests_per_second=20, burst_size=40),
    # 기본값: 보수적 설정
    "default": RateLimiterConfig(requests_per_second=10, burst_size=20),
}

# 서비스별 Rate Limiter 인스턴스 캐시 (싱글톤)
_rate_limiters: dict[str, TokenBucketRateLimiter] = {}
_limiter_lock = threading.Lock()


def get_rate_limiter(service: str = "default") -> TokenBucketRateLimiter:
    """서비스별 Rate Limiter 반환 (싱글톤)

    동일 서비스에 대해 항상 같은 Rate Limiter 인스턴스를 반환합니다.
    이를 통해 여러 스레드에서 동일 서비스 호출 시 전체 Rate를 공유합니다.

    Args:
        service: AWS 서비스 이름 (예: "ec2", "iam")

    Returns:
        해당 서비스의 Rate Limiter

    Example:
        limiter = get_rate_limiter("ec2")
        if limiter.acquire():
            ec2.describe_instances()
    """
    # 서비스명이 없으면 기본값 사용
    config_key = service if service in SERVICE_RATE_LIMITS else "default"

    with _limiter_lock:
        if service not in _rate_limiters:
            config = SERVICE_RATE_LIMITS[config_key]
            _rate_limiters[service] = TokenBucketRateLimiter(config)
        return _rate_limiters[service]


def create_rate_limiter(
    requests_per_second: float = 10.0,
    burst_size: int = 20,
    wait_timeout: float = 30.0,
) -> TokenBucketRateLimiter:
    """커스텀 Rate Limiter 생성

    싱글톤이 아닌 새로운 Rate Limiter를 생성합니다.
    특별한 Rate 제어가 필요한 경우 사용합니다.

    Args:
        requests_per_second: 초당 허용 요청 수
        burst_size: 버스트 허용량
        wait_timeout: 최대 대기 시간 (초)

    Returns:
        새 Rate Limiter 인스턴스
    """
    config = RateLimiterConfig(
        requests_per_second=requests_per_second,
        burst_size=burst_size,
        wait_timeout=wait_timeout,
    )
    return TokenBucketRateLimiter(config)


def reset_rate_limiters() -> None:
    """모든 Rate Limiter 초기화

    테스트 또는 장시간 실행 후 리셋이 필요할 때 사용합니다.
    """
    global _rate_limiters
    with _limiter_lock:
        _rate_limiters.clear()
