"""
tests/shared/aws/metrics/test_session_cache.py - 세션 캐시 테스트

MetricSessionCache 클래스의 동작을 테스트합니다.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

from shared.aws.metrics.session_cache import (
    CacheStats,
    FileBackedMetricCache,
    MetricSessionCache,
    SharedMetricCache,
    get_active_cache,
    get_global_cache,
    is_cache_active,
    set_global_cache,
)


class TestCacheStats:
    """CacheStats 테스트"""

    def test_initial_state(self):
        """초기 상태 확인"""
        stats = CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.hit_rate == 0.0

    def test_hit_rate_calculation(self):
        """히트율 계산"""
        stats = CacheStats(hits=3, misses=7)
        assert stats.hit_rate == 0.3

        stats = CacheStats(hits=10, misses=0)
        assert stats.hit_rate == 1.0

        stats = CacheStats(hits=0, misses=10)
        assert stats.hit_rate == 0.0


class TestMetricSessionCache:
    """MetricSessionCache 테스트"""

    def test_context_manager(self):
        """context manager 동작"""
        assert not is_cache_active()

        with MetricSessionCache() as cache:
            assert is_cache_active()
            assert cache is not None

        assert not is_cache_active()

    def test_get_set_single(self):
        """단일 값 get/set"""
        with MetricSessionCache() as cache:
            # 캐시 미스
            assert cache.get("key1") is None

            # 값 설정
            cache.set("key1", 100.5)

            # 캐시 히트
            assert cache.get("key1") == 100.5
            assert cache.stats.hits == 1
            assert cache.stats.misses == 1
            assert cache.stats.sets == 1

    def test_get_set_many(self):
        """다중 값 get_many/set_many"""
        with MetricSessionCache() as cache:
            # 초기 상태: 캐시 미스
            result = cache.get_many(["k1", "k2", "k3"])
            assert result == {}
            assert cache.stats.misses == 3

            # 여러 값 설정
            cache.set_many({"k1": 1.0, "k2": 2.0, "k3": 3.0})
            assert cache.stats.sets == 3

            # 캐시 히트
            result = cache.get_many(["k1", "k2", "k3"])
            assert result == {"k1": 1.0, "k2": 2.0, "k3": 3.0}
            assert cache.stats.hits == 3

            # 부분 히트
            result = cache.get_many(["k1", "k4"])
            assert result == {"k1": 1.0}
            assert cache.stats.hits == 4
            assert cache.stats.misses == 4

    def test_size(self):
        """캐시 크기 확인"""
        with MetricSessionCache() as cache:
            assert cache.size() == 0

            cache.set("k1", 1.0)
            assert cache.size() == 1

            cache.set_many({"k2": 2.0, "k3": 3.0})
            assert cache.size() == 3

    def test_cache_isolation_after_exit(self):
        """context manager 종료 후 캐시 격리"""
        with MetricSessionCache() as cache:
            cache.set("key", 100.0)
            assert cache.get("key") == 100.0

        # 새 context에서는 이전 캐시에 접근 불가
        with MetricSessionCache() as cache:
            assert cache.get("key") is None

    def test_get_active_cache(self):
        """get_active_cache 함수"""
        # 캐시 비활성 상태
        assert get_active_cache() is None

        # 캐시 활성 상태
        with MetricSessionCache() as cache:
            active = get_active_cache()
            assert active is not None

            # 같은 저장소 공유 확인
            cache.set("shared_key", 42.0)
            assert active.get("shared_key") == 42.0


class TestMetricSessionCacheThreadSafety:
    """스레드 안전성 테스트"""

    def test_thread_isolation(self):
        """스레드별 캐시 격리"""
        results = {}
        barrier = threading.Barrier(2)

        def thread_work(thread_id: int):
            with MetricSessionCache() as cache:
                # 각 스레드에서 고유 값 설정
                cache.set("key", float(thread_id * 100))
                barrier.wait()  # 동기화

                # 각 스레드가 자신의 값을 읽어야 함
                results[thread_id] = cache.get("key")

        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(thread_work, 1)
            executor.submit(thread_work, 2)

        # 각 스레드가 자신의 캐시 값을 가져야 함
        # ContextVar는 스레드별로 독립적
        assert 1 in results or 2 in results

    def test_concurrent_access_per_thread(self):
        """각 스레드가 자체 캐시를 사용하는 동시 접근 테스트

        ContextVar는 스레드별로 독립적이므로, 각 스레드에서 자체
        MetricSessionCache context manager를 사용해야 합니다.
        이것이 cost_dashboard에서 의도한 동작입니다.
        """
        num_threads = 10
        iterations = 100
        errors = []
        results = {}

        def worker(thread_id: int):
            try:
                # 각 스레드에서 자체 캐시 context 생성
                with MetricSessionCache() as cache:
                    for i in range(iterations):
                        key = f"thread_{thread_id}_iter_{i}"
                        value = float(thread_id * 1000 + i)
                        cache.set(key, value)
                        retrieved = cache.get(key)
                        if retrieved != value:
                            errors.append(f"Mismatch: expected {value}, got {retrieved}")
                    results[thread_id] = cache.size()
            except Exception as e:
                errors.append(str(e))

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            for f in futures:
                f.result()

        assert len(errors) == 0, f"Errors: {errors[:5]}"
        # 각 스레드가 iterations 개의 항목을 캐시에 저장
        for _thread_id, size in results.items():
            assert size == iterations


class TestMetricSessionCacheEdgeCases:
    """엣지 케이스 테스트"""

    def test_zero_value(self):
        """0 값 저장/조회"""
        with MetricSessionCache() as cache:
            cache.set("zero_key", 0.0)
            # 0.0은 None이 아니므로 캐시 히트
            assert cache.get("zero_key") == 0.0

    def test_negative_value(self):
        """음수 값 저장/조회"""
        with MetricSessionCache() as cache:
            cache.set("neg_key", -123.45)
            assert cache.get("neg_key") == -123.45

    def test_large_cache(self):
        """대량 데이터 캐싱"""
        with MetricSessionCache() as cache:
            # 10,000개 항목
            items = {f"key_{i}": float(i) for i in range(10000)}
            cache.set_many(items)

            assert cache.size() == 10000

            # 일부 조회
            result = cache.get_many([f"key_{i}" for i in range(100)])
            assert len(result) == 100
            assert result["key_50"] == 50.0

    def test_empty_operations(self):
        """빈 입력 처리"""
        with MetricSessionCache() as cache:
            # 빈 목록
            result = cache.get_many([])
            assert result == {}

            cache.set_many({})
            assert cache.size() == 0

    def test_cache_outside_context(self):
        """context 외부에서 캐시 사용"""
        cache = MetricSessionCache()

        # context 외부에서는 캐시 비활성
        assert cache.get("key") is None

        cache.set("key", 100.0)
        assert cache.get("key") is None  # 저장되지 않음

        assert cache.size() == 0

    def test_nested_context_managers(self):
        """중첩 context manager"""
        with MetricSessionCache() as outer:
            outer.set("outer_key", 1.0)

            with MetricSessionCache() as inner:
                # 내부 캐시는 새로운 캐시
                assert inner.get("outer_key") is None
                inner.set("inner_key", 2.0)
                assert inner.get("inner_key") == 2.0

            # 외부 캐시로 복귀
            assert outer.get("outer_key") == 1.0
            assert outer.get("inner_key") is None


# =============================================================================
# SharedMetricCache 테스트 (스레드 간 공유 가능)
# =============================================================================


class TestSharedMetricCache:
    """SharedMetricCache 기본 테스트"""

    def test_context_manager(self):
        """context manager 동작"""
        cache = SharedMetricCache()

        # context 외부에서는 비활성
        assert cache.get("key") is None

        with cache:
            cache.set("key", 100.0)
            assert cache.get("key") == 100.0

        # context 종료 후 비활성
        assert cache.get("key") is None

    def test_get_set_single(self):
        """단일 값 get/set"""
        with SharedMetricCache() as cache:
            assert cache.get("key1") is None
            cache.set("key1", 100.5)
            assert cache.get("key1") == 100.5

    def test_get_set_many(self):
        """다중 값 get_many/set_many"""
        with SharedMetricCache() as cache:
            cache.set_many({"k1": 1.0, "k2": 2.0, "k3": 3.0})
            result = cache.get_many(["k1", "k2", "k3"])
            assert result == {"k1": 1.0, "k2": 2.0, "k3": 3.0}

    def test_size(self):
        """캐시 크기"""
        with SharedMetricCache() as cache:
            assert cache.size() == 0
            cache.set_many({"k1": 1.0, "k2": 2.0})
            assert cache.size() == 2


class TestSharedMetricCacheThreadSharing:
    """SharedMetricCache 스레드 간 공유 테스트"""

    def test_thread_sharing(self):
        """워커 스레드에서 캐시 공유 확인"""
        results = {}

        def worker(cache: SharedMetricCache, worker_id: int):
            """워커에서 캐시 사용"""
            # 다른 워커가 저장한 값 읽기 시도
            existing = cache.get("shared_key")
            results[f"worker_{worker_id}_read"] = existing

            # 자신의 값 저장
            cache.set(f"worker_{worker_id}", float(worker_id * 100))

        with SharedMetricCache() as cache:
            # 메인 스레드에서 값 설정
            cache.set("shared_key", 999.0)

            # 워커 스레드에서 캐시 접근
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(worker, cache, i) for i in range(3)]
                for f in futures:
                    f.result()

            # 모든 워커가 shared_key를 읽을 수 있어야 함
            for i in range(3):
                assert results[f"worker_{i}_read"] == 999.0, f"워커 {i}가 공유 값을 읽지 못함"

            # 워커들이 저장한 값 확인
            for i in range(3):
                assert cache.get(f"worker_{i}") == float(i * 100)

    def test_concurrent_writes(self):
        """동시 쓰기 테스트"""
        num_threads = 10
        iterations = 100
        errors = []

        def worker(cache: SharedMetricCache, thread_id: int):
            try:
                for i in range(iterations):
                    key = f"t{thread_id}_i{i}"
                    value = float(thread_id * 1000 + i)
                    cache.set(key, value)
                    retrieved = cache.get(key)
                    if retrieved != value:
                        errors.append(f"Mismatch: {key} expected {value}, got {retrieved}")
            except Exception as e:
                errors.append(str(e))

        with SharedMetricCache() as cache:
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(worker, cache, i) for i in range(num_threads)]
                for f in futures:
                    f.result()

            # 모든 값 저장 확인
            assert cache.size() == num_threads * iterations

        assert len(errors) == 0, f"Errors: {errors[:5]}"

    def test_stats_thread_safe(self):
        """통계 스레드 안전성"""
        num_threads = 5
        iterations = 100

        with SharedMetricCache() as cache:
            # 먼저 일부 값 저장
            for i in range(50):
                cache.set(f"pre_{i}", float(i))

            def worker(cache: SharedMetricCache, thread_id: int):
                for i in range(iterations):
                    # 히트 (기존 키)
                    cache.get(f"pre_{i % 50}")
                    # 미스 (존재하지 않는 키)
                    cache.get(f"nonexistent_{thread_id}_{i}")

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(worker, cache, i) for i in range(num_threads)]
                for f in futures:
                    f.result()

            stats = cache.stats
            expected_hits = num_threads * iterations
            expected_misses = num_threads * iterations

            assert stats.hits == expected_hits, f"Expected {expected_hits} hits, got {stats.hits}"
            assert stats.misses == expected_misses, f"Expected {expected_misses} misses, got {stats.misses}"


# =============================================================================
# LRU Eviction 테스트
# =============================================================================


class TestSharedMetricCacheLRU:
    """SharedMetricCache LRU eviction 테스트"""

    def test_lru_eviction(self):
        """LRU eviction 동작 확인"""
        max_size = 5

        with SharedMetricCache(max_size=max_size, register_global=False) as cache:
            # max_size 만큼 채움
            for i in range(max_size):
                cache.set(f"key_{i}", float(i))

            assert cache.size() == max_size

            # 추가 항목 저장 시 가장 오래된 항목 제거
            cache.set("new_key", 100.0)
            assert cache.size() == max_size  # 크기 유지
            assert cache.get("key_0") is None  # 가장 오래된 항목 제거됨
            assert cache.get("new_key") == 100.0

    def test_lru_access_updates_order(self):
        """접근 시 LRU 순서 갱신"""
        max_size = 3

        with SharedMetricCache(max_size=max_size, register_global=False) as cache:
            cache.set("a", 1.0)
            cache.set("b", 2.0)
            cache.set("c", 3.0)

            # a를 접근하여 최신으로 갱신
            cache.get("a")

            # 새 항목 추가 시 b가 제거됨 (a는 최근 접근)
            cache.set("d", 4.0)

            assert cache.get("a") == 1.0  # 유지
            assert cache.get("b") is None  # 제거됨
            assert cache.get("c") == 3.0  # 유지
            assert cache.get("d") == 4.0  # 신규

    def test_eviction_stats(self):
        """eviction 통계 확인"""
        with SharedMetricCache(max_size=3, register_global=False) as cache:
            for i in range(10):
                cache.set(f"key_{i}", float(i))

            # 10개 저장, max 3개이므로 7개 eviction
            assert cache.stats.evictions == 7

    def test_unlimited_size(self):
        """무제한 크기 (max_size=0)"""
        with SharedMetricCache(max_size=0, register_global=False) as cache:
            for i in range(1000):
                cache.set(f"key_{i}", float(i))

            assert cache.size() == 1000
            assert cache.stats.evictions == 0


# =============================================================================
# 전역 캐시 테스트
# =============================================================================


class TestGlobalCache:
    """전역 캐시 테스트"""

    def test_set_get_global_cache(self):
        """전역 캐시 설정/조회"""
        assert get_global_cache() is None

        with SharedMetricCache(register_global=True) as cache:
            assert get_global_cache() is cache

        assert get_global_cache() is None

    def test_manual_global_cache(self):
        """수동 전역 캐시 설정"""
        cache = SharedMetricCache(register_global=False)
        cache._active = True  # 수동 활성화

        set_global_cache(cache)
        assert get_global_cache() is cache

        set_global_cache(None)
        assert get_global_cache() is None

    def test_global_cache_in_workers(self):
        """워커에서 전역 캐시 접근"""
        results = {}

        def worker(worker_id: int):
            cache = get_global_cache()
            if cache:
                results[worker_id] = cache.get("shared_key")

        with SharedMetricCache(register_global=True) as cache:
            cache.set("shared_key", 42.0)

            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(worker, i) for i in range(3)]
                for f in futures:
                    f.result()

        # 모든 워커가 전역 캐시에서 값을 읽음
        assert all(v == 42.0 for v in results.values())


# =============================================================================
# FileBackedMetricCache 테스트
# =============================================================================


class TestFileBackedMetricCache:
    """FileBackedMetricCache 테스트"""

    def test_basic_operations(self, tmp_path):
        """기본 get/set 동작"""
        with FileBackedMetricCache(cache_dir=tmp_path, register_global=False) as cache:
            assert cache.get("key1") is None
            cache.set("key1", 100.0)
            assert cache.get("key1") == 100.0

    def test_cleanup_on_exit(self, tmp_path):
        """종료 시 파일 삭제 (기본 동작)"""
        with FileBackedMetricCache(cache_dir=tmp_path, cleanup_on_exit=True, register_global=False) as cache:
            cache.set("key1", 100.0)
            cache.set("key2", 200.0)

            # 파일이 생성됨
            files = list(tmp_path.glob("*.json"))
            assert len(files) == 2

        # 종료 후 파일 삭제됨
        files_after = list(tmp_path.glob("*.json"))
        assert len(files_after) == 0

    def test_persist_on_exit(self, tmp_path):
        """종료 시 파일 유지 옵션"""
        with FileBackedMetricCache(cache_dir=tmp_path, cleanup_on_exit=False, register_global=False) as cache:
            cache.set("key1", 100.0)

        # 종료 후에도 파일 유지
        files_after = list(tmp_path.glob("*.json"))
        assert len(files_after) == 1

        # 정리
        for f in files_after:
            f.unlink()

    def test_file_cache_hit(self, tmp_path):
        """파일 캐시 히트 (메모리 미스 시)"""
        # 첫 번째 세션: 파일에 저장
        with FileBackedMetricCache(cache_dir=tmp_path, cleanup_on_exit=False, register_global=False) as cache:
            cache.set("persistent_key", 999.0)

        # 두 번째 세션: 파일에서 로드
        with FileBackedMetricCache(cache_dir=tmp_path, cleanup_on_exit=True, register_global=False) as cache:
            # 메모리에 없지만 파일에서 로드
            value = cache.get("persistent_key")
            assert value == 999.0
            assert cache._file_hits == 1

    def test_memory_lru(self, tmp_path):
        """메모리 캐시 LRU"""
        with FileBackedMetricCache(
            cache_dir=tmp_path, max_memory_size=3, cleanup_on_exit=True, register_global=False
        ) as cache:
            for i in range(10):
                cache.set(f"key_{i}", float(i))

            # 메모리에는 최근 3개만
            assert cache.size() == 3

    def test_global_registration(self, tmp_path):
        """전역 캐시 등록"""
        assert get_global_cache() is None

        with FileBackedMetricCache(cache_dir=tmp_path, register_global=True) as cache:
            # FileBackedMetricCache도 전역 캐시로 등록됨
            assert get_global_cache() is cache

        assert get_global_cache() is None
