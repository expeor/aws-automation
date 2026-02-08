"""
core/shared/aws/pricing/utils.py - 가격 조회 통합 서비스 (PricingService)

``PricingService`` 싱글톤이 캐시(PriceCache) + API(PricingFetcher) + fallback(constants)을
통합 관리하여 thread-safe한 가격 조회를 제공한다.

주요 기능:
    - Double-checked locking: 동일 서비스/리전의 동시 API 호출 방지
    - Exponential backoff: Throttling 시 1/2/4초 간격으로 최대 3회 재시도
    - Metrics: 캐시 히트율, API 호출 수, 에러 수, 재시도 수 추적
    - Lazy init: PricingFetcher(boto3 클라이언트)를 첫 호출 시 생성

사용법:
    from core.shared.aws.pricing.utils import pricing_service

    # 가격 조회 (캐시 -> API -> fallback 순서)
    prices = pricing_service.get_prices("ec2", "ap-northeast-2")

    # 캐시 무효화 후 재조회
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
    """가격 조회 성능/상태 메트릭을 thread-safe하게 수집하는 데이터 클래스.

    Attributes:
        api_calls: Pricing API 호출 횟수
        cache_hits: 캐시 히트 횟수
        cache_misses: 캐시 미스 횟수
        errors: API 호출 에러 횟수
        retries: API 재시도 횟수
    """

    api_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: int = 0
    retries: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def hit_rate(self) -> float:
        """캐시 히트율을 반환한다 (0.0 ~ 1.0).

        Returns:
            ``cache_hits / (cache_hits + cache_misses)``. 조회가 없으면 ``0.0``
        """
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
        """메트릭 값을 딕셔너리로 변환하여 반환한다.

        Returns:
            ``{"api_calls": int, "cache_hits": int, "cache_misses": int,
            "hit_rate": float, "errors": int, "retries": int}``
        """
        return {
            "api_calls": self.api_calls,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": round(self.hit_rate, 2),
            "errors": self.errors,
            "retries": self.retries,
        }

    def reset(self) -> None:
        """모든 메트릭 카운터를 0으로 초기화한다."""
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
    """가격 조회 통합 서비스 (Singleton).

    Thread-safe한 가격 조회를 제공하며, 프로세스 내에서 단일 인스턴스로 동작한다.
    캐시(PriceCache) -> API(PricingFetcher) -> fallback(constants) 순서로
    가격을 조회하고, per-region 락으로 동일 서비스/리전의 동시 API 호출을 방지한다.

    Attributes:
        _cache: PriceCache 인스턴스 (파일 기반 캐시)
        _fetcher: PricingFetcher 인스턴스 (lazy init)
        _metrics: PricingMetrics 인스턴스 (성능 추적)
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
        """PricingFetcher를 지연 생성(lazy init)하여 반환한다.

        Returns:
            PricingFetcher 인스턴스
        """
        if self._fetcher is None:
            self._fetcher = PricingFetcher()
        return self._fetcher

    def _get_lock(self, key: str) -> threading.Lock:
        """서비스/리전 조합별 락을 반환한다 (double-checked locking).

        Args:
            key: 락 키 (``"{service}_{region}"`` 형식)

        Returns:
            해당 키에 대한 ``threading.Lock`` 인스턴스
        """
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
        """통합 가격 조회 (캐시 -> API -> fallback 순서).

        1차(fast path): 락 없이 캐시 확인
        2차(slow path): 락 획득 후 double-check -> API 호출 -> fallback 병합 -> 캐시 저장

        API 결과의 ``0.0`` 이 아닌 값만 기본값을 덮어쓰며, 결과를 캐시에 저장한다.

        Args:
            service: AWS 서비스 코드 (``"ec2"``, ``"ebs"``, ``"sagemaker"`` 등)
            region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)
            refresh: ``True`` 이면 캐시를 무시하고 API에서 새로 조회
            defaults: 커스텀 기본값 딕셔너리 (``None`` 이면 ``constants.DEFAULT_PRICES`` 사용)

        Returns:
            ``{key: price}`` 형식의 가격 딕셔너리 (예: ``{"t3.medium": 0.0416}``)
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
        """Exponential backoff으로 PricingFetcher의 서비스별 메서드를 호출한다.

        Throttling/RequestLimitExceeded/ServiceUnavailable 에러 시
        1, 2, 4초 간격으로 최대 ``max_retries`` 회 재시도한다.

        Args:
            service: AWS 서비스 코드 (``_FETCHER_METHODS`` 에 등록된 키)
            region: AWS 리전 코드
            max_retries: 최대 재시도 횟수 (기본: ``3``)

        Returns:
            가격 딕셔너리 (API 실패 시 빈 딕셔너리)
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
        """캐시를 무효화(삭제)한다.

        Args:
            service: AWS 서비스 코드 (``None`` 이면 전체 서비스)
            region: AWS 리전 코드 (``None`` 이면 전체 리전)

        Returns:
            삭제된 캐시 파일 수
        """
        from .cache import clear_cache

        count = clear_cache(service, region)
        logger.info(f"캐시 무효화: {service or '*'}/{region or '*'} ({count}개)")
        return count

    def refresh(self, service: str, region: str = "ap-northeast-2") -> dict[str, float]:
        """캐시를 무효화하고 API에서 강제로 새로 조회한다.

        Args:
            service: AWS 서비스 코드
            region: AWS 리전 코드 (기본: ``"ap-northeast-2"``)

        Returns:
            새로 조회된 가격 딕셔너리
        """
        self._cache.invalidate(service, region)
        return self.get_prices(service, region, refresh=True)

    def get_metrics(self) -> dict[str, float | int]:
        """현재 메트릭 값을 딕셔너리로 반환한다.

        Returns:
            ``PricingMetrics.to_dict()`` 와 동일한 형식
        """
        return self._metrics.to_dict()

    def reset_metrics(self) -> None:
        """모든 메트릭 카운터를 0으로 초기화한다."""
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
