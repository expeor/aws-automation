"""
tests/shared/aws/metrics/test_cache_benchmark.py - 캐시 성능 벤치마크

캐시 적용 전후 성능을 비교합니다.
pytest-benchmark 없이 간단한 시간 측정으로 구현.

실행:
    pytest tests/shared/aws/metrics/test_cache_benchmark.py -v -s
"""

from __future__ import annotations

import time
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from core.shared.aws.metrics import MetricQuery, MetricSessionCache, batch_get_metrics


class TestCacheBenchmark:
    """캐시 성능 벤치마크"""

    def setup_method(self):
        """테스트 설정"""
        self.start_time = datetime(2024, 1, 1)
        self.end_time = datetime(2024, 1, 2)

    def _create_queries(self, count: int) -> list[MetricQuery]:
        """테스트용 쿼리 생성"""
        return [
            MetricQuery(
                id=f"q_{i}",
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                dimensions={"InstanceId": f"i-{i:012d}"},
                stat="Average",
            )
            for i in range(count)
        ]

    def _create_mock_client(self, queries: list[MetricQuery], delay_ms: float = 10):
        """지연이 있는 CloudWatch 클라이언트 모킹

        Args:
            queries: 쿼리 목록
            delay_ms: API 호출당 지연 시간 (밀리초)
        """
        mock_client = MagicMock()

        def mock_get_metric_data(**kwargs):
            # API 호출 지연 시뮬레이션
            time.sleep(delay_ms / 1000)

            # 요청된 쿼리에 대한 결과 생성
            results = []
            for mdq in kwargs.get("MetricDataQueries", []):
                results.append({"Id": mdq["Id"], "Values": [50.0]})

            return {"MetricDataResults": results}

        mock_client.get_metric_data.side_effect = mock_get_metric_data
        return mock_client

    def test_benchmark_without_cache(self):
        """캐시 없이 반복 호출 성능 측정"""
        num_queries = 50
        num_iterations = 3
        api_delay_ms = 5

        queries = self._create_queries(num_queries)
        mock_client = self._create_mock_client(queries, delay_ms=api_delay_ms)

        # 캐시 없이 반복 호출
        start = time.perf_counter()

        for _ in range(num_iterations):
            result = batch_get_metrics(
                mock_client,
                queries,
                self.start_time,
                self.end_time,
                cache=None,
            )
            assert len(result) == num_queries

        elapsed_no_cache = time.perf_counter() - start
        api_calls_no_cache = mock_client.get_metric_data.call_count

        print("\n[캐시 없음]")
        print(f"  총 소요 시간: {elapsed_no_cache * 1000:.1f}ms")
        print(f"  API 호출 횟수: {api_calls_no_cache}")
        print(f"  호출당 평균: {elapsed_no_cache / api_calls_no_cache * 1000:.1f}ms")

        # 캐시 없이는 매번 API 호출
        assert api_calls_no_cache == num_iterations

    def test_benchmark_with_cache(self):
        """캐시 사용 시 반복 호출 성능 측정"""
        num_queries = 50
        num_iterations = 3
        api_delay_ms = 5

        queries = self._create_queries(num_queries)
        mock_client = self._create_mock_client(queries, delay_ms=api_delay_ms)

        # 캐시 사용하여 반복 호출
        start = time.perf_counter()

        with MetricSessionCache() as cache:
            for _ in range(num_iterations):
                result = batch_get_metrics(
                    mock_client,
                    queries,
                    self.start_time,
                    self.end_time,
                    cache=cache,
                )
                assert len(result) == num_queries

            cache_stats = cache.stats

        elapsed_with_cache = time.perf_counter() - start
        api_calls_with_cache = mock_client.get_metric_data.call_count

        print("\n[캐시 사용]")
        print(f"  총 소요 시간: {elapsed_with_cache * 1000:.1f}ms")
        print(f"  API 호출 횟수: {api_calls_with_cache}")
        print(f"  캐시 히트: {cache_stats.hits}")
        print(f"  캐시 미스: {cache_stats.misses}")
        print(f"  캐시 히트율: {cache_stats.hit_rate:.1%}")

        # 캐시 사용 시 첫 호출만 API 호출
        assert api_calls_with_cache == 1
        assert cache_stats.hits == num_queries * (num_iterations - 1)
        assert cache_stats.misses == num_queries

    def test_benchmark_comparison(self):
        """캐시 유무 성능 비교"""
        num_queries = 100
        num_iterations = 5
        api_delay_ms = 10  # 실제 API 호출에 가까운 지연

        queries = self._create_queries(num_queries)

        # === 캐시 없이 ===
        mock_client_no_cache = self._create_mock_client(queries, delay_ms=api_delay_ms)
        start = time.perf_counter()

        for _ in range(num_iterations):
            batch_get_metrics(
                mock_client_no_cache,
                queries,
                self.start_time,
                self.end_time,
                cache=None,
            )

        elapsed_no_cache = time.perf_counter() - start
        api_calls_no_cache = mock_client_no_cache.get_metric_data.call_count

        # === 캐시 사용 ===
        mock_client_with_cache = self._create_mock_client(queries, delay_ms=api_delay_ms)
        start = time.perf_counter()

        with MetricSessionCache() as cache:
            for _ in range(num_iterations):
                batch_get_metrics(
                    mock_client_with_cache,
                    queries,
                    self.start_time,
                    self.end_time,
                    cache=cache,
                )

        elapsed_with_cache = time.perf_counter() - start
        api_calls_with_cache = mock_client_with_cache.get_metric_data.call_count

        # === 결과 출력 ===
        speedup = elapsed_no_cache / elapsed_with_cache if elapsed_with_cache > 0 else float("inf")
        api_reduction = (1 - api_calls_with_cache / api_calls_no_cache) * 100

        print(f"\n{'=' * 60}")
        print(f"성능 비교 결과 (쿼리 {num_queries}개 × {num_iterations}회 반복)")
        print(f"{'=' * 60}")
        print(f"{'항목':<20} {'캐시 없음':>15} {'캐시 사용':>15} {'개선':>10}")
        print(f"{'-' * 60}")
        print(
            f"{'총 소요 시간':<20} {elapsed_no_cache * 1000:>12.1f}ms {elapsed_with_cache * 1000:>12.1f}ms {speedup:>8.1f}x"
        )
        print(f"{'API 호출 횟수':<20} {api_calls_no_cache:>15} {api_calls_with_cache:>15} {api_reduction:>7.0f}%↓")
        print(f"{'=' * 60}")

        # 검증
        assert api_calls_with_cache < api_calls_no_cache, "캐시 사용 시 API 호출이 줄어야 함"
        assert elapsed_with_cache < elapsed_no_cache, "캐시 사용 시 더 빨라야 함"

    def test_benchmark_partial_cache_scenario(self):
        """부분 캐시 히트 시나리오 (실제 사용 패턴 시뮬레이션)

        cost_dashboard에서 여러 collector가 일부 겹치는 메트릭을 조회하는 상황
        """
        api_delay_ms = 5

        # Collector A: EC2 인스턴스 1-50 메트릭
        queries_a = self._create_queries(50)

        # Collector B: EC2 인스턴스 25-75 메트릭 (50% 중복)
        queries_b = [
            MetricQuery(
                id=f"q_{i}",
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                dimensions={"InstanceId": f"i-{i:012d}"},
                stat="Average",
            )
            for i in range(25, 75)
        ]

        # Collector C: EC2 인스턴스 50-100 메트릭 (Collector A와 겹침 없음)
        queries_c = [
            MetricQuery(
                id=f"q_{i}",
                namespace="AWS/EC2",
                metric_name="CPUUtilization",
                dimensions={"InstanceId": f"i-{i:012d}"},
                stat="Average",
            )
            for i in range(50, 100)
        ]

        # === 캐시 없이 ===
        all_queries = queries_a + queries_b + queries_c
        mock_client_no_cache = self._create_mock_client(all_queries, delay_ms=api_delay_ms)

        start = time.perf_counter()
        batch_get_metrics(mock_client_no_cache, queries_a, self.start_time, self.end_time, cache=None)
        batch_get_metrics(mock_client_no_cache, queries_b, self.start_time, self.end_time, cache=None)
        batch_get_metrics(mock_client_no_cache, queries_c, self.start_time, self.end_time, cache=None)
        elapsed_no_cache = time.perf_counter() - start
        api_calls_no_cache = mock_client_no_cache.get_metric_data.call_count

        # === 캐시 사용 ===
        mock_client_with_cache = self._create_mock_client(all_queries, delay_ms=api_delay_ms)

        start = time.perf_counter()
        with MetricSessionCache() as cache:
            batch_get_metrics(mock_client_with_cache, queries_a, self.start_time, self.end_time, cache=cache)
            batch_get_metrics(mock_client_with_cache, queries_b, self.start_time, self.end_time, cache=cache)
            batch_get_metrics(mock_client_with_cache, queries_c, self.start_time, self.end_time, cache=cache)
            stats = cache.stats
        elapsed_with_cache = time.perf_counter() - start
        api_calls_with_cache = mock_client_with_cache.get_metric_data.call_count

        # === 결과 ===
        print(f"\n{'=' * 60}")
        print("부분 캐시 히트 시나리오")
        print("  Collector A: 쿼리 50개 (인스턴스 0-49)")
        print("  Collector B: 쿼리 50개 (인스턴스 25-74, 50% 중복)")
        print("  Collector C: 쿼리 50개 (인스턴스 50-99)")
        print(f"{'=' * 60}")
        print(f"캐시 없음: API 호출 {api_calls_no_cache}회, {elapsed_no_cache * 1000:.1f}ms")
        print(f"캐시 사용: API 호출 {api_calls_with_cache}회, {elapsed_with_cache * 1000:.1f}ms")
        print(f"  - 캐시 히트: {stats.hits}개")
        print(f"  - 캐시 미스: {stats.misses}개")
        print(f"  - 히트율: {stats.hit_rate:.1%}")
        print(f"{'=' * 60}")

        # 검증: B에서 25개 캐시 히트 (인스턴스 25-49), C에서 25개 캐시 히트 (인스턴스 50-74)
        assert stats.hits == 50, f"50개 캐시 히트 예상, 실제: {stats.hits}"
        assert stats.misses == 100, f"100개 캐시 미스 예상, 실제: {stats.misses}"


class TestCacheMemoryUsage:
    """캐시 메모리 사용량 테스트"""

    def test_large_cache_size(self):
        """대량 캐시 항목 테스트"""
        num_items = 10000

        with MetricSessionCache() as cache:
            # 대량 항목 추가
            items = {f"key_{i}": float(i) for i in range(num_items)}
            cache.set_many(items)

            assert cache.size() == num_items

            # 조회 테스트
            result = cache.get_many([f"key_{i}" for i in range(100)])
            assert len(result) == 100

        # context 종료 후 캐시 비활성화
        assert not MetricSessionCache().get("key_0")

    def test_cache_cleanup_on_exit(self):
        """context 종료 시 캐시 정리 확인"""
        with MetricSessionCache() as cache:
            cache.set("test_key", 100.0)
            assert cache.size() == 1

        # 새 context에서는 빈 캐시
        with MetricSessionCache() as cache:
            assert cache.size() == 0
            assert cache.get("test_key") is None


if __name__ == "__main__":
    # 직접 실행 시 벤치마크만 실행
    pytest.main([__file__, "-v", "-s", "-k", "benchmark"])
