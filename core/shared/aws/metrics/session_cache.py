"""
shared/aws/metrics/session_cache.py - CloudWatch 메트릭 캐시

cost_dashboard 실행 중 동일 메트릭 중복 조회 방지를 위한 캐시 시스템.

캐시 타입:
1. MetricSessionCache: ContextVar 기반, 단일 스레드 내에서만 유효
2. SharedMetricCache: threading.Lock 기반, 멀티스레드 환경에서 공유 가능 (LRU 지원)
3. FileBackedMetricCache: 파일 기반 캐시, 반복 실행 시에도 API 호출 절감

전역 캐시:
- set_global_cache() / get_global_cache(): 전역 캐시 설정/조회
- batch_get_metrics에서 cache=None 시 자동으로 전역 캐시 사용

Usage:
    # 방법 1: 명시적 캐시 전달
    with SharedMetricCache() as cache:
        result = batch_get_metrics(..., cache=cache)

    # 방법 2: 전역 캐시 (collectors 수정 없이 사용)
    with SharedMetricCache() as cache:
        set_global_cache(cache)
        # 이후 batch_get_metrics 호출 시 자동으로 cache 사용
        worker_function()  # 내부에서 batch_get_metrics(..., cache=None) 호출
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# 세션별 캐시 저장소 (ContextVar로 스레드/코루틴별 독립)
_session_cache: ContextVar[dict[str, float] | None] = ContextVar("metric_cache", default=None)

# 전역 캐시 (스레드 간 공유)
_global_cache: SharedMetricCache | None = None
_global_cache_lock = threading.Lock()


# =============================================================================
# 캐시 통계
# =============================================================================


@dataclass
class CacheStats:
    """캐시 통계 (스레드 안전)

    CloudWatch 메트릭 캐시의 히트/미스/저장/eviction 통계를 추적합니다.
    모든 카운터 조작은 threading.Lock으로 보호됩니다.

    Attributes:
        hits: 캐시 히트 횟수
        misses: 캐시 미스 횟수
        sets: 캐시 저장 횟수
        evictions: LRU eviction 횟수
    """

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0  # LRU eviction 횟수

    @property
    def hit_rate(self) -> float:
        """캐시 히트율 (0.0 ~ 1.0)

        Returns:
            히트 횟수 / (히트 + 미스) 비율. 조회 없으면 0.0
        """
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def add_hit(self, count: int = 1) -> None:
        """히트 카운트 증가 (스레드 안전)

        Args:
            count: 증가할 횟수 (기본 1)
        """
        with self._lock:
            self.hits += count

    def add_miss(self, count: int = 1) -> None:
        """미스 카운트 증가 (스레드 안전)

        Args:
            count: 증가할 횟수 (기본 1)
        """
        with self._lock:
            self.misses += count

    def add_set(self, count: int = 1) -> None:
        """저장 카운트 증가 (스레드 안전)

        Args:
            count: 증가할 횟수 (기본 1)
        """
        with self._lock:
            self.sets += count

    def add_eviction(self, count: int = 1) -> None:
        """eviction 카운트 증가 (스레드 안전)

        Args:
            count: 증가할 횟수 (기본 1)
        """
        with self._lock:
            self.evictions += count

    def summary(self) -> str:
        """통계 요약 문자열

        Returns:
            "hits=N, misses=N, hit_rate=N%, evictions=N" 형식의 문자열
        """
        return f"hits={self.hits}, misses={self.misses}, hit_rate={self.hit_rate:.1%}, evictions={self.evictions}"


# =============================================================================
# 전역 캐시 접근 함수
# =============================================================================


def set_global_cache(cache: SharedMetricCache | None) -> None:
    """전역 캐시 설정

    Args:
        cache: 설정할 캐시 인스턴스 (None으로 해제)

    Example:
        with SharedMetricCache() as cache:
            set_global_cache(cache)
            # 이후 batch_get_metrics에서 자동으로 cache 사용
    """
    global _global_cache
    with _global_cache_lock:
        _global_cache = cache
        if cache:
            logger.debug("전역 캐시 설정됨")
        else:
            logger.debug("전역 캐시 해제됨")


def get_global_cache() -> SharedMetricCache | None:
    """현재 전역 캐시 반환

    Returns:
        활성화된 전역 캐시 또는 None
    """
    with _global_cache_lock:
        return _global_cache


# =============================================================================
# MetricSessionCache (ContextVar 기반, 단일 스레드)
# =============================================================================


class MetricSessionCache:
    """세션 내 메트릭 캐시 (단일 스레드용)

    CloudWatch 메트릭 조회 결과를 세션 내에서 캐싱.
    동일 세션에서 같은 메트릭을 다시 조회할 때 API 호출 절감.

    Thread-safety:
        - ContextVar 사용으로 스레드별 독립적 캐시 제공
        - 동일 스레드 내에서는 안전하게 공유

    Note:
        ThreadPoolExecutor 워커에서는 사용 불가.
        멀티스레드 환경에서는 SharedMetricCache 사용.
    """

    def __init__(self) -> None:
        self._stats = CacheStats()
        self._token: Token[dict[str, float] | None] | None = None

    def __enter__(self) -> MetricSessionCache:
        """캐시 활성화"""
        self._token = _session_cache.set({})
        logger.debug("MetricSessionCache: 캐시 활성화")
        return self

    def __exit__(self, *args) -> None:
        """캐시 비활성화 및 정리"""
        if self._token is not None:
            _session_cache.reset(self._token)
            self._token = None
        logger.debug(f"MetricSessionCache: 캐시 종료 ({self._stats.summary()})")

    @property
    def stats(self) -> CacheStats:
        """캐시 통계 반환"""
        return self._stats

    def get(self, key: str) -> float | None:
        """캐시에서 값 조회

        Args:
            key: 캐시 키 (메트릭 쿼리 해시)

        Returns:
            캐시된 메트릭 값 또는 None (미스 시)
        """
        cache = _session_cache.get()
        if cache is None:
            return None

        value = cache.get(key)
        if value is not None:
            self._stats.hits += 1
        else:
            self._stats.misses += 1

        return value

    def set(self, key: str, value: float) -> None:
        """캐시에 값 저장

        Args:
            key: 캐시 키 (메트릭 쿼리 해시)
            value: 저장할 메트릭 값
        """
        cache = _session_cache.get()
        if cache is not None:
            cache[key] = value
            self._stats.sets += 1

    def get_many(self, keys: list[str]) -> dict[str, float]:
        """여러 키를 한번에 조회

        Args:
            keys: 조회할 캐시 키 목록

        Returns:
            {키: 값} 딕셔너리 (캐시 히트된 항목만 포함)
        """
        cache = _session_cache.get()
        if not cache:
            self._stats.misses += len(keys)
            return {}

        result = {}
        for key in keys:
            if key in cache:
                result[key] = cache[key]
                self._stats.hits += 1
            else:
                self._stats.misses += 1

        return result

    def set_many(self, items: dict[str, float]) -> None:
        """여러 값을 한번에 저장

        Args:
            items: {캐시 키: 메트릭 값} 딕셔너리
        """
        cache = _session_cache.get()
        if cache is not None:
            cache.update(items)
            self._stats.sets += len(items)

    def size(self) -> int:
        """현재 캐시 크기 반환

        Returns:
            캐시에 저장된 항목 수 (비활성 시 0)
        """
        cache = _session_cache.get()
        return len(cache) if cache else 0


def get_active_cache() -> MetricSessionCache | None:
    """현재 활성화된 ContextVar 캐시 반환

    Returns:
        활성 MetricSessionCache 인스턴스 또는 None (비활성 시)
    """
    if _session_cache.get() is not None:
        return MetricSessionCache()
    return None


def is_cache_active() -> bool:
    """ContextVar 캐시가 활성화되어 있는지 확인

    Returns:
        ContextVar 기반 캐시가 현재 스레드에서 활성 상태이면 True
    """
    return _session_cache.get() is not None


# =============================================================================
# SharedMetricCache (스레드 간 공유, LRU 지원)
# =============================================================================


class SharedMetricCache:
    """스레드 간 공유 가능한 메트릭 캐시 (LRU 지원)

    ThreadPoolExecutor 등 멀티스레드 환경에서 캐시를 공유할 때 사용.
    threading.Lock으로 스레드 안전성 보장.

    Features:
        - 스레드 안전 (Lock 기반)
        - LRU eviction (최대 크기 제한)
        - 전역 캐시로 설정 가능

    Args:
        max_size: 최대 캐시 항목 수 (기본 10000, 0이면 무제한)
        register_global: True면 전역 캐시로 자동 등록

    Usage:
        with SharedMetricCache(max_size=5000, register_global=True) as cache:
            # 모든 워커에서 자동으로 캐시 사용
            with ThreadPoolExecutor() as executor:
                executor.submit(worker_function)
    """

    def __init__(self, max_size: int = 10000, register_global: bool = True) -> None:
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()
        self._stats = CacheStats()
        self._active = False
        self._max_size = max_size
        self._register_global = register_global

    def __enter__(self) -> SharedMetricCache:
        """캐시 활성화"""
        self._active = True
        if self._register_global:
            set_global_cache(self)
        logger.debug(f"SharedMetricCache: 캐시 활성화 (max_size={self._max_size})")
        return self

    def __exit__(self, *args) -> None:
        """캐시 비활성화 및 정리"""
        self._active = False
        if self._register_global:
            set_global_cache(None)
        size = len(self._cache)
        self._cache.clear()
        logger.debug(f"SharedMetricCache: 캐시 종료 (size={size}, {self._stats.summary()})")

    @property
    def stats(self) -> CacheStats:
        """캐시 통계 반환"""
        return self._stats

    def _evict_if_needed(self) -> None:
        """LRU eviction (Lock 내부에서 호출)"""
        if self._max_size <= 0:
            return

        evicted = 0
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)  # 가장 오래된 항목 제거
            evicted += 1

        if evicted:
            self._stats.add_eviction(evicted)

    def get(self, key: str) -> float | None:
        """캐시에서 값 조회 (LRU 갱신)"""
        if not self._active:
            return None

        with self._lock:
            if key in self._cache:
                # LRU: 최근 사용으로 이동
                self._cache.move_to_end(key)
                value = self._cache[key]
                self._stats.add_hit()
                return value

        self._stats.add_miss()
        return None

    def set(self, key: str, value: float) -> None:
        """캐시에 값 저장 (LRU eviction 적용)"""
        if not self._active:
            return

        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                self._evict_if_needed()
            self._cache[key] = value

        self._stats.add_set()

    def get_many(self, keys: list[str]) -> dict[str, float]:
        """여러 키를 한번에 조회"""
        if not self._active:
            self._stats.add_miss(len(keys))
            return {}

        result = {}
        hits = 0
        misses = 0

        with self._lock:
            for key in keys:
                if key in self._cache:
                    self._cache.move_to_end(key)
                    result[key] = self._cache[key]
                    hits += 1
                else:
                    misses += 1

        if hits:
            self._stats.add_hit(hits)
        if misses:
            self._stats.add_miss(misses)

        return result

    def set_many(self, items: dict[str, float]) -> None:
        """여러 값을 한번에 저장"""
        if not self._active or not items:
            return

        with self._lock:
            for key, value in items.items():
                if key in self._cache:
                    self._cache.move_to_end(key)
                else:
                    self._evict_if_needed()
                self._cache[key] = value

        self._stats.add_set(len(items))

    def size(self) -> int:
        """현재 캐시 크기 반환"""
        with self._lock:
            return len(self._cache)


# =============================================================================
# FileBackedMetricCache (파일 기반, 반복 실행 효과)
# =============================================================================


class FileBackedMetricCache:
    """파일 기반 메트릭 캐시 (반복 실행 시 API 호출 절감)

    메모리 캐시와 파일 캐시를 결합하여:
    - 세션 내: 메모리 캐시로 빠른 접근
    - 반복 실행: 파일 캐시로 API 호출 절감

    Features:
        - TTL 기반 만료 (기본 7일)
        - 자동 정리 (만료된 항목 제거)
        - 스레드 안전
        - 종료 시 파일 삭제 옵션

    Args:
        cache_dir: 캐시 파일 디렉토리 (기본: ~/.aws-automation/cache/metrics)
        ttl_days: 캐시 TTL (일 단위, 기본 7일)
        max_memory_size: 메모리 캐시 최대 크기
        register_global: 전역 캐시로 등록 여부
        cleanup_on_exit: 종료 시 파일 캐시 삭제 여부 (기본 True)

    Usage:
        # 일회성 캐시 (실행 후 삭제, 기본값)
        with FileBackedMetricCache() as cache:
            result = batch_get_metrics(..., cache=cache)

        # 영구 캐시 (다음 실행에도 유지)
        with FileBackedMetricCache(cleanup_on_exit=False) as cache:
            result = batch_get_metrics(..., cache=cache)
    """

    DEFAULT_CACHE_DIR = Path.home() / ".aws-automation" / "cache" / "metrics"

    def __init__(
        self,
        cache_dir: Path | str | None = None,
        ttl_days: int = 7,
        max_memory_size: int = 10000,
        register_global: bool = True,
        cleanup_on_exit: bool = True,
    ) -> None:
        self._cache_dir = Path(cache_dir) if cache_dir else self.DEFAULT_CACHE_DIR
        self._ttl_seconds = ttl_days * 86400
        self._memory_cache = SharedMetricCache(max_size=max_memory_size, register_global=False)
        self._lock = threading.Lock()
        self._stats = CacheStats()
        self._active = False
        self._register_global = register_global
        self._cleanup_on_exit = cleanup_on_exit
        self._file_hits = 0
        self._files_created: set[Path] = set()  # 이 세션에서 생성된 파일 추적

    def __enter__(self) -> FileBackedMetricCache:
        """캐시 활성화"""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache.__enter__()
        self._active = True
        self._files_created.clear()
        if self._register_global:
            set_global_cache(self)  # type: ignore[arg-type]
        self._cleanup_expired()
        logger.debug(
            f"FileBackedMetricCache: 캐시 활성화 (dir={self._cache_dir}, cleanup_on_exit={self._cleanup_on_exit})"
        )
        return self

    def __exit__(self, *args) -> None:
        """캐시 비활성화 및 정리"""
        self._active = False
        if self._register_global:
            set_global_cache(None)
        self._memory_cache.__exit__()

        # 종료 시 파일 캐시 삭제
        files_removed = 0
        if self._cleanup_on_exit:
            files_removed = self.clear_file_cache()

        logger.debug(
            f"FileBackedMetricCache: 캐시 종료 "
            f"({self._stats.summary()}, file_hits={self._file_hits}, files_removed={files_removed})"
        )

    @property
    def stats(self) -> CacheStats:
        """캐시 통계 반환"""
        return self._stats

    def _key_to_filename(self, key: str) -> Path:
        """캐시 키를 파일명으로 변환

        Args:
            key: 캐시 키 문자열

        Returns:
            SHA256 해시 기반의 안전한 파일 경로 (.json)
        """
        # SHA256 해시로 안전한 파일명 생성
        hash_val = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self._cache_dir / f"{hash_val}.json"

    def _is_expired(self, filepath: Path) -> bool:
        """파일 캐시 만료 확인

        Args:
            filepath: 확인할 캐시 파일 경로

        Returns:
            파일이 없거나 TTL 초과 시 True
        """
        if not filepath.exists():
            return True
        mtime = filepath.stat().st_mtime
        return (time.time() - mtime) > self._ttl_seconds

    def _cleanup_expired(self) -> None:
        """만료된 캐시 파일 정리"""
        if not self._cache_dir.exists():
            return

        removed = 0
        for filepath in self._cache_dir.glob("*.json"):
            if self._is_expired(filepath):
                try:
                    filepath.unlink()
                    removed += 1
                except OSError:
                    pass

        if removed:
            logger.debug(f"FileBackedMetricCache: 만료 캐시 {removed}개 정리")

    def get(self, key: str) -> float | None:
        """캐시에서 값 조회 (메모리 → 파일)"""
        if not self._active:
            return None

        # 1. 메모리 캐시 확인
        value = self._memory_cache.get(key)
        if value is not None:
            self._stats.add_hit()
            return value

        # 2. 파일 캐시 확인
        filepath = self._key_to_filename(key)
        if not self._is_expired(filepath):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                    value = data.get("value")
                    if value is not None:
                        # 메모리 캐시에 로드
                        self._memory_cache.set(key, value)
                        self._stats.add_hit()
                        self._file_hits += 1
                        return float(value)
            except (OSError, json.JSONDecodeError):
                pass

        self._stats.add_miss()
        return None

    def set(self, key: str, value: float) -> None:
        """캐시에 값 저장 (메모리 + 파일)"""
        if not self._active:
            return

        # 메모리 캐시 저장
        self._memory_cache.set(key, value)

        # 파일 캐시 저장
        filepath = self._key_to_filename(key)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"key": key, "value": value, "ts": time.time()}, f)
        except OSError as e:
            logger.debug(f"파일 캐시 저장 실패: {e}")

        self._stats.add_set()

    def get_many(self, keys: list[str]) -> dict[str, float]:
        """여러 키를 한번에 조회"""
        if not self._active:
            self._stats.add_miss(len(keys))
            return {}

        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value

        return result

    def set_many(self, items: dict[str, float]) -> None:
        """여러 값을 한번에 저장"""
        if not self._active or not items:
            return

        for key, value in items.items():
            self.set(key, value)

    def size(self) -> int:
        """메모리 캐시 크기 반환"""
        return self._memory_cache.size()

    def clear_file_cache(self) -> int:
        """파일 캐시 전체 삭제

        Returns:
            삭제된 캐시 파일 수
        """
        removed = 0
        if self._cache_dir.exists():
            for filepath in self._cache_dir.glob("*.json"):
                try:
                    filepath.unlink()
                    removed += 1
                except OSError:
                    pass
        logger.info(f"FileBackedMetricCache: 파일 캐시 {removed}개 삭제")
        return removed
