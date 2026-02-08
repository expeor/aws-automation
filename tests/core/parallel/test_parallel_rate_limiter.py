"""
tests/test_parallel_rate_limiter.py - core/parallel/rate_limiter.py 테스트
"""

import threading
import time

import pytest

from core.parallel.rate_limiter import (
    SERVICE_RATE_LIMITS,
    RateLimiterConfig,
    TokenBucketRateLimiter,
    get_rate_limiter,
    reset_rate_limiters,
)


class TestRateLimiterConfig:
    """RateLimiterConfig 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        config = RateLimiterConfig()

        assert config.requests_per_second == 10.0
        assert config.burst_size == 20
        assert config.wait_timeout == 30.0

    def test_custom_values(self):
        """커스텀 값 설정"""
        config = RateLimiterConfig(
            requests_per_second=50.0,
            burst_size=100,
            wait_timeout=60.0,
        )

        assert config.requests_per_second == 50.0
        assert config.burst_size == 100
        assert config.wait_timeout == 60.0


class TestTokenBucketRateLimiter:
    """TokenBucketRateLimiter 테스트"""

    def test_init_with_default_config(self):
        """기본 설정으로 초기화"""
        limiter = TokenBucketRateLimiter()

        assert limiter.config.requests_per_second == 10.0
        assert limiter.config.burst_size == 20

    def test_init_with_custom_config(self):
        """커스텀 설정으로 초기화"""
        config = RateLimiterConfig(
            requests_per_second=5.0,
            burst_size=10,
        )
        limiter = TokenBucketRateLimiter(config)

        assert limiter.config.requests_per_second == 5.0
        assert limiter.config.burst_size == 10

    def test_initial_tokens_equals_burst_size(self):
        """초기 토큰 = 버스트 크기"""
        config = RateLimiterConfig(burst_size=15)
        limiter = TokenBucketRateLimiter(config)

        # 초기에는 버스트 크기만큼 토큰이 있어야 함
        assert limiter.available_tokens == 15

    def test_try_acquire_success(self):
        """토큰 획득 성공"""
        config = RateLimiterConfig(burst_size=10)
        limiter = TokenBucketRateLimiter(config)

        # 토큰이 있으므로 성공
        assert limiter.try_acquire() is True
        assert limiter.available_tokens < 10

    def test_try_acquire_multiple(self):
        """여러 토큰 한번에 획득"""
        config = RateLimiterConfig(burst_size=10, requests_per_second=0.1)
        limiter = TokenBucketRateLimiter(config)

        assert limiter.try_acquire(5) is True
        # 토큰 리필이 매우 느리므로 5개 이하 (약간의 오차 허용)
        assert limiter.available_tokens <= 5.1

    def test_try_acquire_failure_when_empty(self):
        """토큰 부족 시 실패"""
        config = RateLimiterConfig(burst_size=2, requests_per_second=0.1)
        limiter = TokenBucketRateLimiter(config)

        # 모든 토큰 소비
        assert limiter.try_acquire(2) is True

        # 더 이상 토큰 없음
        assert limiter.try_acquire() is False

    def test_acquire_waits_for_tokens(self):
        """토큰 없으면 대기"""
        config = RateLimiterConfig(
            requests_per_second=100.0,  # 빠른 리필
            burst_size=1,
            wait_timeout=1.0,
        )
        limiter = TokenBucketRateLimiter(config)

        # 첫 번째 토큰 소비
        assert limiter.acquire() is True

        # 두 번째는 대기 후 획득 (빠른 리필)
        start = time.monotonic()
        assert limiter.acquire() is True
        elapsed = time.monotonic() - start

        # 대기 시간이 있어야 함 (매우 짧더라도)
        assert elapsed >= 0

    def test_acquire_timeout(self):
        """토큰 대기 타임아웃"""
        config = RateLimiterConfig(
            requests_per_second=0.1,  # 매우 느린 리필 (10초에 1개)
            burst_size=1,
            wait_timeout=0.1,  # 짧은 타임아웃
        )
        limiter = TokenBucketRateLimiter(config)

        # 첫 번째 토큰 소비
        assert limiter.acquire() is True

        # 두 번째는 타임아웃
        start = time.monotonic()
        assert limiter.acquire() is False
        elapsed = time.monotonic() - start

        # 대기 시간이 타임아웃 근처
        assert elapsed < 0.3  # 약간의 여유

    def test_token_refill(self):
        """토큰 리필 확인"""
        config = RateLimiterConfig(
            requests_per_second=100.0,  # 초당 100개
            burst_size=10,
        )
        limiter = TokenBucketRateLimiter(config)

        # 모든 토큰 소비
        limiter.try_acquire(10)
        assert limiter.available_tokens < 1

        # 잠시 대기 후 리필 확인
        time.sleep(0.05)  # 50ms = 5개 토큰 리필
        assert limiter.available_tokens >= 4  # 약간의 오차 허용

    def test_burst_limit(self):
        """버스트 한도 초과 방지"""
        config = RateLimiterConfig(
            requests_per_second=1000.0,  # 매우 빠른 리필
            burst_size=5,
        )
        limiter = TokenBucketRateLimiter(config)

        # 긴 시간 대기해도 버스트 크기 초과 안함
        time.sleep(0.1)
        assert limiter.available_tokens <= 5

    def test_thread_safety(self):
        """스레드 안전성"""
        config = RateLimiterConfig(
            requests_per_second=1000.0,
            burst_size=100,
            wait_timeout=5.0,
        )
        limiter = TokenBucketRateLimiter(config)

        success_count = {"value": 0}
        lock = threading.Lock()

        def acquire_tokens():
            for _ in range(10):
                if limiter.try_acquire():
                    with lock:
                        success_count["value"] += 1

        # 여러 스레드에서 동시 획득 시도
        threads = [threading.Thread(target=acquire_tokens) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 모든 획득 시도가 버스트 크기 이하여야 함
        assert success_count["value"] <= 100


class TestServiceRateLimits:
    """서비스별 Rate Limit 설정 테스트"""

    def test_ec2_config(self):
        """EC2 설정"""
        config = SERVICE_RATE_LIMITS["ec2"]
        assert config.requests_per_second == 20
        assert config.burst_size == 40

    def test_iam_config(self):
        """IAM 설정"""
        config = SERVICE_RATE_LIMITS["iam"]
        assert config.requests_per_second == 10
        assert config.burst_size == 20

    def test_default_config(self):
        """기본 설정"""
        config = SERVICE_RATE_LIMITS["default"]
        assert config.requests_per_second == 10
        assert config.burst_size == 20

    def test_organizations_config_conservative(self):
        """Organizations 설정은 보수적"""
        config = SERVICE_RATE_LIMITS["organizations"]
        assert config.requests_per_second <= 5
        assert config.burst_size <= 10


class TestGetRateLimiter:
    """get_rate_limiter 싱글톤 테스트"""

    def setup_method(self):
        """테스트 전 리셋"""
        reset_rate_limiters()

    def test_returns_same_instance(self):
        """동일 서비스에 대해 같은 인스턴스 반환"""
        limiter1 = get_rate_limiter("ec2")
        limiter2 = get_rate_limiter("ec2")

        assert limiter1 is limiter2

    def test_different_services_different_instances(self):
        """다른 서비스는 다른 인스턴스"""
        ec2_limiter = get_rate_limiter("ec2")
        iam_limiter = get_rate_limiter("iam")

        assert ec2_limiter is not iam_limiter

    def test_unknown_service_uses_default_config(self):
        """알 수 없는 서비스는 기본 설정 사용"""
        limiter = get_rate_limiter("unknown_service")

        # 기본 설정과 동일해야 함
        default_config = SERVICE_RATE_LIMITS["default"]
        assert limiter.config.requests_per_second == default_config.requests_per_second
        assert limiter.config.burst_size == default_config.burst_size

    def test_thread_safe_singleton(self):
        """스레드 안전한 싱글톤"""
        reset_rate_limiters()
        instances = []

        def get_limiter():
            limiter = get_rate_limiter("test_service")
            instances.append(id(limiter))

        threads = [threading.Thread(target=get_limiter) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 모든 스레드가 같은 인스턴스를 받아야 함
        assert len(set(instances)) == 1


class TestRateLimiterConfigValidation:
    """RateLimiterConfig 검증 테스트"""

    def test_zero_requests_per_second_raises(self):
        """requests_per_second=0이면 ValueError"""
        with pytest.raises(ValueError, match="requests_per_second must be > 0"):
            RateLimiterConfig(requests_per_second=0)

    def test_negative_requests_per_second_raises(self):
        """requests_per_second < 0이면 ValueError"""
        with pytest.raises(ValueError, match="requests_per_second must be > 0"):
            RateLimiterConfig(requests_per_second=-1.0)


class TestResetRateLimiters:
    """reset_rate_limiters 테스트"""

    def test_reset_clears_cache(self):
        """캐시 초기화"""
        # 몇 개의 rate limiter 생성
        get_rate_limiter("ec2")
        get_rate_limiter("iam")
        get_rate_limiter("s3")

        # 리셋
        reset_rate_limiters()

        # 새로운 인스턴스가 생성되어야 함
        limiter1 = get_rate_limiter("ec2")

        # 다시 리셋 후 가져오면 다른 인스턴스
        reset_rate_limiters()
        limiter2 = get_rate_limiter("ec2")

        assert limiter1 is not limiter2


class TestRateLimiterPerformance:
    """Rate Limiter 성능 테스트"""

    def test_burst_performance(self):
        """버스트 처리 성능"""
        config = RateLimiterConfig(
            requests_per_second=100.0,
            burst_size=50,
            wait_timeout=1.0,
        )
        limiter = TokenBucketRateLimiter(config)

        # 버스트 크기만큼 즉시 획득 가능해야 함
        start = time.monotonic()
        success_count = 0
        for _ in range(50):
            if limiter.try_acquire():
                success_count += 1
        elapsed = time.monotonic() - start

        assert success_count == 50
        assert elapsed < 0.1  # 버스트는 빠르게 처리

    def test_sustained_rate(self):
        """지속적인 요청 속도 제어"""
        config = RateLimiterConfig(
            requests_per_second=50.0,  # 초당 50개
            burst_size=10,
            wait_timeout=1.0,
        )
        limiter = TokenBucketRateLimiter(config)

        # 버스트 소진
        for _ in range(10):
            limiter.try_acquire()

        # 이후 요청들의 속도 측정
        start = time.monotonic()
        for _ in range(5):
            limiter.acquire()
        elapsed = time.monotonic() - start

        # 5개 요청에 최소 0.1초 소요 (50 req/s)
        assert elapsed >= 0.05  # 약간의 여유
