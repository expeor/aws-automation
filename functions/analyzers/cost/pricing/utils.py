"""
plugins/cost/pricing/utils.py - 가격 조회 통합 서비스

PricingService: 캐시 + API + fallback을 통합 관리하는 싱글톤 서비스
- Thread Lock: 동일 프로세스 내 동시성 보호
- Lazy Loading: 필요할 때만 가격 조회
- Exponential Backoff: API 실패 시 재시도
- Metrics: 캐시 히트율, API 호출 수 추적

사용법:
    from functions.analyzers.cost.pricing.utils import pricing_service

    # 가격 조회
    prices = pricing_service.get_prices("ec2", "ap-northeast-2")

    # 캐시 무효화
    pricing_service.invalidate("ec2", "ap-northeast-2")

    # 메트릭 조회
    metrics = pricing_service.get_metrics()
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from botocore.exceptions import BotoCoreError, ClientError

from .cache import PriceCache
from .constants import DEFAULT_PRICES
from .fetcher import PricingFetcher

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class PricingMetrics:
    """가격 조회 메트릭"""

    api_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    retries: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def hit_rate(self) -> float:
        """캐시 히트율"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    def increment_api_calls(self) -> None:
        with self._lock:
            self.api_calls += 1

    def increment_cache_hits(self) -> None:
        with self._lock:
            self.cache_hits += 1

    def increment_cache_misses(self) -> None:
        with self._lock:
            self.cache_misses += 1

    def increment_errors(self) -> None:
        with self._lock:
            self.errors += 1

    def increment_retries(self) -> None:
        with self._lock:
            self.retries += 1

    def to_dict(self) -> dict[str, float | int]:
        """메트릭을 딕셔너리로 변환"""
        return {
            "api_calls": self.api_calls,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": round(self.hit_rate, 2),
            "errors": self.errors,
            "retries": self.retries,
        }

    def reset(self) -> None:
        """메트릭 초기화"""
        with self._lock:
            self.api_calls = 0
            self.cache_hits = 0
            self.cache_misses = 0
            self.errors = 0
            self.retries = 0


# Fetcher 메서드 매핑 (service -> fetcher method name)
_FETCHER_METHODS: dict[str, str] = {
    "ec2": "get_ec2_prices",
    "ebs": "get_ebs_prices",
    "sagemaker": "get_sagemaker_prices",
    "vpc_endpoint": "get_vpc_endpoint_prices",
    "secretsmanager": "get_secrets_manager_prices",  # 주의: fetcher에서 secrets_manager (언더스코어)
    "kms": "get_kms_prices",
    "ecr": "get_ecr_prices",
    "route53": "get_route53_prices",  # 글로벌 서비스 - 리전 파라미터 없음
    "snapshot": "get_snapshot_prices",
    "eip": "get_eip_prices",
    "elb": "get_elb_prices",
    "rds_snapshot": "get_rds_snapshot_prices",
    "cloudwatch": "get_cloudwatch_prices",
    "lambda": "get_lambda_prices",
    "dynamodb": "get_dynamodb_prices",
}


class PricingService:
    """가격 조회 통합 서비스 (Singleton)

    Thread-safe한 가격 조회를 제공합니다.
    - Double-checked locking으로 동시성 보호
    - Exponential backoff으로 API 재시도
    - 메트릭 수집으로 모니터링 지원
    """

    _instance: PricingService | None = None
    _init_lock = threading.Lock()

    def __new__(cls) -> PricingService:
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        # 이미 초기화된 경우 스킵
        if getattr(self, "_initialized", False):
            return

        self._cache = PriceCache()
        self._fetcher: PricingFetcher | None = None
        self._metrics = PricingMetrics()

        # Per-region 락 레지스트리
        self._lock_registry: dict[str, threading.Lock] = {}
        self._registry_mutex = threading.Lock()

        self._initialized = True

    @property
    def fetcher(self) -> PricingFetcher:
        """Fetcher lazy initialization"""
        if self._fetcher is None:
            self._fetcher = PricingFetcher()
        return self._fetcher

    def _get_lock(self, key: str) -> threading.Lock:
        """Per-region 락 획득 (double-checked locking)"""
        if key not in self._lock_registry:
            with self._registry_mutex:
                if key not in self._lock_registry:
                    self._lock_registry[key] = threading.Lock()
        return self._lock_registry[key]

    def get_prices(
        self,
        service: str,
        region: str = "ap-northeast-2",
        refresh: bool = False,
        defaults: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """통합 가격 조회 (캐시 + API + fallback)

        Args:
            service: 서비스 코드 (ec2, ebs, sagemaker 등)
            region: AWS 리전
            refresh: 캐시 무시하고 새로 조회
            defaults: 커스텀 기본값 (None이면 constants.py 사용)

        Returns:
            가격 딕셔너리 {key: price}
        """
        lock_key = f"{service}_{region}"

        # 1차: 락 없이 캐시 확인 (fast path)
        if not refresh:
            cached = self._cache.get(service, region)
            if cached:
                self._metrics.increment_cache_hits()
                logger.debug(f"캐시 히트: {service}/{region}")
                return cached

        # 2차: 락 획득 후 API 호출 (slow path)
        with self._get_lock(lock_key):
            # Double-check: 다른 스레드가 이미 로드했을 수 있음
            if not refresh:
                cached = self._cache.get(service, region)
                if cached:
                    self._metrics.increment_cache_hits()
                    logger.debug(f"캐시 히트 (락 내부): {service}/{region}")
                    return cached

            self._metrics.increment_cache_misses()

            # 기본값 가져오기
            fallback = defaults if defaults is not None else DEFAULT_PRICES.get(service, {})

            # API 호출
            api_prices = self._fetch_with_retry(service, region)

            # 기본값 + API 결과 병합 (API의 0.0이 아닌 값만 덮어씀)
            merged = fallback.copy()
            for k, v in api_prices.items():
                if v != 0.0 or k not in merged:  # 0.0이 아니거나 기본값에 없는 키
                    merged[k] = v

            if merged:
                self._cache.set(service, region, merged)
                if api_prices:
                    logger.debug(f"API 가격 조회 성공: {service}/{region} ({len(api_prices)}개)")
                else:
                    logger.debug(f"기본값 사용: {service}/{region}")

            return merged

    def _fetch_with_retry(
        self,
        service: str,
        region: str,
        max_retries: int = 3,
    ) -> dict[str, float]:
        """Exponential backoff으로 API 호출

        Args:
            service: 서비스 코드
            region: AWS 리전
            max_retries: 최대 재시도 횟수

        Returns:
            가격 딕셔너리 (실패 시 빈 딕셔너리)
        """
        method_name = _FETCHER_METHODS.get(service)
        if not method_name:
            logger.warning(f"알 수 없는 서비스: {service}")
            return {}

        fetcher_method: Callable[..., dict[str, float]] | None = getattr(self.fetcher, method_name, None)
        if not fetcher_method:
            logger.warning(f"Fetcher 메서드 없음: {method_name}")
            return {}

        for attempt in range(max_retries + 1):
            try:
                self._metrics.increment_api_calls()
                logger.info(f"Pricing API 호출: {service}/{region} (시도 {attempt + 1}/{max_retries + 1})")

                # Route53은 리전 파라미터 없음
                if service == "route53":
                    return fetcher_method()
                return fetcher_method(region)

            except (ClientError, BotoCoreError) as e:
                error_code = getattr(e, "response", {}).get("Error", {}).get("Code", "")

                # Throttling 또는 일시적 오류인 경우 재시도
                if error_code in ("Throttling", "RequestLimitExceeded", "ServiceUnavailable"):
                    if attempt < max_retries:
                        wait = 2**attempt  # 1, 2, 4초
                        logger.warning(f"API 제한, {wait}초 후 재시도: {service}/{region}")
                        self._metrics.increment_retries()
                        time.sleep(wait)
                        continue

                self._metrics.increment_errors()
                logger.warning(f"Pricing API 실패 [{service}/{region}]: {e}")
                return {}

            except Exception as e:
                self._metrics.increment_errors()
                logger.warning(f"Pricing API 예외 [{service}/{region}]: {e}")
                return {}

        return {}

    def invalidate(self, service: str | None = None, region: str | None = None) -> int:
        """캐시 무효화

        Args:
            service: 서비스 코드 (None이면 전체)
            region: AWS 리전 (None이면 전체)

        Returns:
            삭제된 캐시 항목 수
        """
        from .cache import clear_cache

        count = clear_cache(service, region)
        logger.info(f"캐시 무효화: {service or '*'}/{region or '*'} ({count}개)")
        return count

    def refresh(self, service: str, region: str = "ap-northeast-2") -> dict[str, float]:
        """강제 새로고침

        Args:
            service: 서비스 코드
            region: AWS 리전

        Returns:
            가격 딕셔너리
        """
        self._cache.invalidate(service, region)
        return self.get_prices(service, region, refresh=True)

    def get_metrics(self) -> dict[str, float | int]:
        """메트릭 조회"""
        return self._metrics.to_dict()

    def reset_metrics(self) -> None:
        """메트릭 초기화"""
        self._metrics.reset()


# 모듈 레벨 싱글톤 인스턴스
pricing_service = PricingService()


def get_prices(
    service: str,
    region: str = "ap-northeast-2",
    refresh: bool = False,
    defaults: dict[str, float] | None = None,
) -> dict[str, float]:
    """통합 가격 조회 함수 (편의 함수)

    Args:
        service: 서비스 코드
        region: AWS 리전
        refresh: 캐시 무시
        defaults: 커스텀 기본값

    Returns:
        가격 딕셔너리
    """
    return pricing_service.get_prices(service, region, refresh, defaults)
