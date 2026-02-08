"""
tests/shared/aws/metrics/test_cache_thread_issue.py - 스레드 격리 문제 확인

ContextVar가 ThreadPoolExecutor 워커에서 접근 불가능함을 확인합니다.
"""

from concurrent.futures import ThreadPoolExecutor

from core.shared.aws.metrics.session_cache import MetricSessionCache, is_cache_active


def test_contextvar_thread_isolation_issue():
    """ContextVar가 워커 스레드에서 접근 불가능함 확인

    이 테스트는 현재 구현의 한계를 보여줍니다.
    메인 스레드에서 활성화한 캐시가 워커 스레드에서는 보이지 않습니다.
    """
    results = {}

    def check_cache_in_worker(worker_id: int) -> bool:
        """워커 스레드에서 캐시 활성화 여부 확인"""
        active = is_cache_active()
        results[worker_id] = active
        return active

    with MetricSessionCache() as cache:
        # 메인 스레드에서는 캐시 활성화됨
        assert is_cache_active() is True
        cache.set("main_thread_key", 100.0)

        # 워커 스레드에서 확인
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(check_cache_in_worker, i) for i in range(3)]
            worker_results = [f.result() for f in futures]

    # 워커 스레드에서는 캐시가 비활성화 상태 (ContextVar 격리)
    print("\n메인 스레드: 캐시 활성화 = True")
    print(f"워커 스레드들: 캐시 활성화 = {results}")

    # 모든 워커에서 캐시가 비활성화 상태여야 함
    assert all(r is False for r in worker_results), "워커 스레드에서 캐시가 보이면 안됨"


def test_current_orchestrator_pattern_limitation():
    """현재 orchestrator 패턴의 한계 확인

    orchestrator에서 MetricSessionCache를 활성화해도
    ThreadPoolExecutor 내 collector들은 캐시에 접근할 수 없습니다.
    """
    cache_hits_in_workers = []

    def simulate_collector(collector_id: int):
        """collector 시뮬레이션"""
        # 워커에서 캐시 활성화 여부 확인
        active = is_cache_active()
        cache_hits_in_workers.append((collector_id, active))

        # 워커에서 캐시 사용 시도
        cache = MetricSessionCache()  # context 외부이므로 효과 없음
        cache.set(f"key_{collector_id}", float(collector_id))
        value = cache.get(f"key_{collector_id}")

        return value is not None

    # orchestrator 패턴 시뮬레이션
    with MetricSessionCache() as main_cache:
        main_cache.set("shared_key", 999.0)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(simulate_collector, i) for i in range(5)]
            results = [f.result() for f in futures]

    print(f"\n워커 캐시 활성화 상태: {cache_hits_in_workers}")
    print(f"워커 캐시 사용 성공: {results}")

    # 모든 워커에서 캐시 사용 실패
    assert all(r is False for r in results), "워커에서 캐시 사용이 안되어야 함"


if __name__ == "__main__":
    test_contextvar_thread_isolation_issue()
    test_current_orchestrator_pattern_limitation()
    print("\n테스트 통과: ContextVar 스레드 격리 문제 확인됨")
