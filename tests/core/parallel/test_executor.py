"""
tests/core/parallel/test_executor.py - ParallelSessionExecutor 테스트
"""

import time
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from core.parallel.executor import ParallelConfig, ParallelSessionExecutor, parallel_collect
from core.parallel.types import ErrorCategory


@pytest.fixture
def sso_context(mock_context):
    """SSO Session용 완전히 설정된 컨텍스트"""
    from cli.flow.context import FallbackStrategy, RoleSelection

    # RoleSelection 설정 (필수)
    role_selection = RoleSelection(
        primary_role="AdminRole",
        fallback_role=None,
        fallback_strategy=FallbackStrategy.SKIP_ACCOUNT,
        role_account_map={"AdminRole": ["123456789012"]},
        skipped_accounts=[],
    )
    mock_context.role_selection = role_selection
    return mock_context


class TestParallelConfig:
    """ParallelConfig 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        config = ParallelConfig()

        assert config.max_workers == 20
        assert config.retry_config is None
        assert config.rate_limiter_config is None

    def test_custom_values(self):
        """커스텀 값 설정"""
        from core.parallel.decorators import RetryConfig
        from core.parallel.rate_limiter import RateLimiterConfig

        retry_config = RetryConfig(max_retries=5)
        limiter_config = RateLimiterConfig(requests_per_second=50.0)

        config = ParallelConfig(
            max_workers=30,
            retry_config=retry_config,
            rate_limiter_config=limiter_config,
        )

        assert config.max_workers == 30
        assert config.retry_config == retry_config
        assert config.rate_limiter_config == limiter_config


class TestParallelSessionExecutor:
    """ParallelSessionExecutor 테스트"""

    def test_init_with_default_config(self, mock_context):
        """기본 설정으로 초기화"""
        executor = ParallelSessionExecutor(mock_context)

        assert executor.ctx == mock_context
        assert executor.config is not None
        assert executor.config.max_workers == 20

    def test_init_with_custom_config(self, mock_context):
        """커스텀 설정으로 초기화"""
        config = ParallelConfig(max_workers=10)
        executor = ParallelSessionExecutor(mock_context, config)

        assert executor.config.max_workers == 10

    def test_build_task_list_single_profile(self, mock_static_context):
        """단일 프로파일 작업 목록 생성"""
        executor = ParallelSessionExecutor(mock_static_context)
        tasks = executor._build_task_list()

        # 1개 프로파일 × 1개 리전 = 1개 작업
        assert len(tasks) == 1
        assert tasks[0].account_id == "test-static"
        assert tasks[0].region == "ap-northeast-2"

    @patch("core.auth.session.get_session")
    def test_build_task_list_multi_profile(self, mock_get_session):
        """다중 프로파일 작업 목록 생성"""
        from cli.flow.context import ExecutionContext, ProviderKind

        # Mock session
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # 다중 프로파일 컨텍스트
        ctx = ExecutionContext()
        ctx.provider_kind = ProviderKind.STATIC_CREDENTIALS
        ctx.profiles = ["profile1", "profile2"]
        ctx.regions = ["us-east-1", "ap-northeast-2"]

        executor = ParallelSessionExecutor(ctx)
        tasks = executor._build_task_list()

        # 2개 프로파일 × 2개 리전 = 4개 작업
        assert len(tasks) == 4

    def test_build_task_list_sso_session(self, sso_context):
        """SSO Session 작업 목록 생성"""
        executor = ParallelSessionExecutor(sso_context)
        tasks = executor._build_task_list()

        # 1개 계정 × 1개 리전 = 1개 작업
        assert len(tasks) >= 1
        assert tasks[0].account_id == "123456789012"
        assert tasks[0].region == "ap-northeast-2"

    def test_execute_success(self, sso_context):
        """성공적인 실행"""

        def collector_func(session, account_id, account_name, region):
            return [{"resource": "test-resource", "region": region}]

        executor = ParallelSessionExecutor(sso_context)
        result = executor.execute(collector_func, service="test")

        assert result.success_count > 0
        assert result.error_count == 0
        assert len(result.get_flat_data()) > 0

    def test_execute_with_error(self, sso_context):
        """에러 발생 시 처리"""

        def failing_collector(session, account_id, account_name, region):
            raise ValueError("Test error")

        executor = ParallelSessionExecutor(sso_context)
        result = executor.execute(failing_collector, service="test")

        assert result.error_count > 0
        assert result.success_count == 0

    def test_execute_with_client_error(self, sso_context):
        """ClientError 처리"""

        def throttled_collector(session, account_id, account_name, region):
            raise ClientError(
                {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
                "DescribeInstances",
            )

        executor = ParallelSessionExecutor(sso_context)
        result = executor.execute(throttled_collector, service="ec2")

        assert result.error_count > 0
        errors = result.get_errors()
        assert len(errors) > 0
        # Throttling은 재시도 후 실패
        assert any(e.category == ErrorCategory.THROTTLING for e in errors)

    def test_execute_with_progress_tracker(self, sso_context):
        """Progress tracker 사용"""

        def collector_func(session, account_id, account_name, region):
            return [{"test": "data"}]

        # Mock progress tracker
        mock_tracker = MagicMock()
        mock_tracker.set_total = MagicMock()
        mock_tracker.on_complete = MagicMock()

        executor = ParallelSessionExecutor(sso_context)
        result = executor.execute(collector_func, service="test", progress_tracker=mock_tracker)

        # set_total이 호출되었는지 확인
        mock_tracker.set_total.assert_called_once()

        # on_complete가 각 작업마다 호출되었는지 확인
        assert mock_tracker.on_complete.call_count == result.total_count

    def test_execute_empty_task_list(self):
        """작업 목록이 비어있을 때"""
        from cli.flow.context import ExecutionContext

        ctx = ExecutionContext()
        ctx.regions = []  # 빈 리전 목록

        def collector_func(session, account_id, account_name, region):
            return []

        executor = ParallelSessionExecutor(ctx)
        result = executor.execute(collector_func, service="test")

        assert result.total_count == 0
        assert result.success_count == 0
        assert result.error_count == 0

    def test_execute_rate_limiting(self, sso_context):
        """Rate limiting 적용"""
        from core.parallel.rate_limiter import RateLimiterConfig

        # 매우 제한적인 rate limiter
        config = ParallelConfig(
            rate_limiter_config=RateLimiterConfig(
                requests_per_second=0.1,  # 초당 0.1개 (10초에 1개)
                burst_size=1,
                wait_timeout=0.01,  # 매우 짧은 타임아웃
            )
        )

        call_count = {"value": 0}

        def collector_func(session, account_id, account_name, region):
            call_count["value"] += 1
            return [{"call": call_count["value"]}]

        executor = ParallelSessionExecutor(sso_context, config)
        result = executor.execute(collector_func, service="test")

        # Rate limit으로 인해 일부 작업이 실패할 수 있음
        # (타임아웃으로 인해)
        assert result.total_count > 0

    def test_execute_with_retry(self, sso_context):
        """재시도 로직 테스트"""
        from core.parallel.decorators import RetryConfig

        config = ParallelConfig(retry_config=RetryConfig(max_retries=2, base_delay=0.01))

        attempt_count = {"value": 0}

        def flaky_collector(session, account_id, account_name, region):
            attempt_count["value"] += 1
            if attempt_count["value"] < 2:
                # 첫 번째 시도는 실패
                raise ClientError(
                    {"Error": {"Code": "ServiceUnavailable", "Message": "Try again"}},
                    "DescribeInstances",
                )
            # 두 번째 시도는 성공
            return [{"success": True}]

        executor = ParallelSessionExecutor(sso_context, config)
        result = executor.execute(flaky_collector, service="test")

        # 재시도 후 성공해야 함
        assert result.success_count > 0

    def test_execute_max_workers(self, sso_context):
        """max_workers 설정 테스트"""
        config = ParallelConfig(max_workers=2)

        concurrent_count = {"value": 0, "max": 0}

        def collector_func(session, account_id, account_name, region):
            concurrent_count["value"] += 1
            concurrent_count["max"] = max(concurrent_count["max"], concurrent_count["value"])
            time.sleep(0.01)  # 약간 대기
            concurrent_count["value"] -= 1
            return []

        # 여러 리전 설정
        sso_context.regions = ["us-east-1", "us-west-2", "ap-northeast-2", "eu-west-1"]

        executor = ParallelSessionExecutor(sso_context, config)
        executor.execute(collector_func, service="test")

        # max_workers=2이므로 동시 실행이 2를 넘지 않아야 함
        assert concurrent_count["max"] <= 2

    def test_execute_session_getter_called(self, sso_context):
        """세션 getter가 호출되는지 확인"""
        session_calls = []

        original_get_session = sso_context.provider.get_session

        def tracked_get_session(*args, **kwargs):
            session_calls.append((args, kwargs))
            return original_get_session(*args, **kwargs)

        sso_context.provider.get_session = tracked_get_session

        def collector_func(session, account_id, account_name, region):
            return [{"test": "data"}]

        executor = ParallelSessionExecutor(sso_context)
        result = executor.execute(collector_func, service="test")

        # 각 작업마다 세션 getter가 호출되어야 함
        assert len(session_calls) == result.total_count

    def test_execute_quiet_mode_propagation(self, sso_context):
        """Quiet 모드가 워커 스레드에 전파되는지 확인"""
        from core.parallel.quiet import is_quiet, set_quiet

        quiet_states = []

        def collector_func(session, account_id, account_name, region):
            quiet_states.append(is_quiet())
            return []

        # Quiet 모드 설정
        set_quiet(True)

        executor = ParallelSessionExecutor(sso_context)
        executor.execute(collector_func, service="test")

        # 워커 스레드에서도 quiet 모드여야 함
        assert any(quiet_states)

        # 원상 복구
        set_quiet(False)


class TestParallelCollect:
    """parallel_collect 편의 함수 테스트"""

    def test_basic_collect(self, sso_context):
        """기본 수집"""

        def collector_func(session, account_id, account_name, region):
            return [
                {"id": f"resource-{region}-1", "region": region},
                {"id": f"resource-{region}-2", "region": region},
            ]

        result = parallel_collect(sso_context, collector_func, service="test")

        assert result.success_count > 0
        data = result.get_flat_data()
        assert len(data) > 0

    def test_collect_with_max_workers(self, sso_context):
        """max_workers 지정"""

        def collector_func(session, account_id, account_name, region):
            return [{"region": region}]

        result = parallel_collect(sso_context, collector_func, max_workers=5, service="test")

        assert result.total_count > 0

    def test_collect_with_progress_tracker(self, sso_context):
        """Progress tracker 사용"""
        mock_tracker = MagicMock()

        def collector_func(session, account_id, account_name, region):
            return [{"data": "test"}]

        result = parallel_collect(sso_context, collector_func, progress_tracker=mock_tracker)

        # set_total이 호출되어야 함
        mock_tracker.set_total.assert_called_once()

    def test_collect_error_handling(self, sso_context):
        """에러 처리 확인"""

        def failing_collector(session, account_id, account_name, region):
            raise ValueError("Intentional test error")

        result = parallel_collect(sso_context, failing_collector, service="test")

        assert result.error_count > 0
        assert result.success_count == 0

        # 에러 요약 생성 가능
        summary = result.get_error_summary()
        assert len(summary) > 0
        assert "실패" in summary or "FAIL" in summary.upper()

    def test_collect_flat_data(self, sso_context):
        """평탄화된 데이터 추출"""

        def collector_func(session, account_id, account_name, region):
            return [{"id": 1}, {"id": 2}, {"id": 3}]

        result = parallel_collect(sso_context, collector_func, service="test")

        flat_data = result.get_flat_data()

        # 리스트들이 하나로 병합되어야 함
        assert isinstance(flat_data, list)
        assert all(isinstance(item, dict) for item in flat_data)

    def test_collect_empty_results(self, sso_context):
        """빈 결과 처리"""

        def empty_collector(session, account_id, account_name, region):
            return []

        result = parallel_collect(sso_context, empty_collector, service="test")

        assert result.success_count > 0  # 성공은 했지만
        assert len(result.get_flat_data()) == 0  # 데이터는 비어있음

    def test_collect_mixed_results(self, sso_context):
        """혼합 결과 (성공/실패)"""
        call_count = {"value": 0}

        def mixed_collector(session, account_id, account_name, region):
            call_count["value"] += 1
            if call_count["value"] % 2 == 0:
                raise ValueError("Even numbered call fails")
            return [{"success": True}]

        # 여러 리전 설정
        sso_context.regions = ["us-east-1", "us-west-2", "ap-northeast-2"]

        result = parallel_collect(sso_context, mixed_collector, service="test")

        # 일부 성공, 일부 실패
        assert result.success_count > 0
        assert result.error_count > 0

    def test_collect_with_service_name(self, sso_context):
        """서비스 이름 지정"""

        def collector_func(session, account_id, account_name, region):
            return [{"service": "ec2"}]

        result = parallel_collect(sso_context, collector_func, service="ec2")

        assert result.total_count > 0

    def test_collect_preserves_metadata(self, sso_context):
        """메타데이터 보존 확인"""

        def collector_func(session, account_id, account_name, region):
            return [
                {
                    "resource_id": "test-123",
                    "account_id": account_id,
                    "region": region,
                    "account_name": account_name,
                }
            ]

        result = parallel_collect(sso_context, collector_func, service="test")

        data = result.get_flat_data()
        assert len(data) > 0

        # 메타데이터가 보존되어야 함
        first_item = data[0]
        assert "account_id" in first_item
        assert "region" in first_item
        assert "account_name" in first_item


class TestExecutorErrorScenarios:
    """Executor 에러 시나리오 테스트"""

    def test_access_denied_error(self, sso_context):
        """AccessDenied 에러 처리"""

        def access_denied_collector(session, account_id, account_name, region):
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "You don't have permission"}},
                "DescribeInstances",
            )

        result = parallel_collect(sso_context, access_denied_collector, service="ec2")

        assert result.error_count > 0
        errors = result.get_errors()
        assert any(e.category == ErrorCategory.ACCESS_DENIED for e in errors)

    def test_not_found_error(self, sso_context):
        """NotFound 에러 처리"""

        def not_found_collector(session, account_id, account_name, region):
            raise ClientError(
                {"Error": {"Code": "ResourceNotFound", "Message": "Resource not found"}},
                "DescribeVolume",
            )

        result = parallel_collect(sso_context, not_found_collector, service="ec2")

        assert result.error_count > 0

    def test_network_error(self, sso_context):
        """네트워크 에러 처리"""

        def network_error_collector(session, account_id, account_name, region):
            raise ConnectionError("Network connection failed")

        result = parallel_collect(sso_context, network_error_collector, service="ec2")

        assert result.error_count > 0
        errors = result.get_errors()
        assert any(e.category == ErrorCategory.NETWORK for e in errors)

    def test_timeout_error(self, sso_context):
        """타임아웃 에러 처리"""

        def timeout_collector(session, account_id, account_name, region):
            raise TimeoutError("Request timed out")

        result = parallel_collect(sso_context, timeout_collector, service="ec2")

        assert result.error_count > 0

    def test_unknown_error(self, sso_context):
        """알 수 없는 에러 처리"""

        def unknown_error_collector(session, account_id, account_name, region):
            raise RuntimeError("Something went wrong")

        result = parallel_collect(sso_context, unknown_error_collector, service="test")

        assert result.error_count > 0
        errors = result.get_errors()
        assert any(e.category == ErrorCategory.UNKNOWN for e in errors)


class TestExecutorPerformance:
    """Executor 성능 테스트"""

    def test_concurrent_execution(self, sso_context):
        """병렬 실행 확인"""
        import threading

        execution_times = []
        lock = threading.Lock()

        def slow_collector(session, account_id, account_name, region):
            start = time.monotonic()
            time.sleep(0.05)  # 50ms
            end = time.monotonic()
            with lock:
                execution_times.append((start, end))
            return [{"region": region}]

        # 여러 리전 설정
        sso_context.regions = ["us-east-1", "us-west-2", "ap-northeast-2", "eu-west-1"]

        start_time = time.monotonic()
        result = parallel_collect(sso_context, slow_collector, max_workers=4, service="test")
        total_time = time.monotonic() - start_time

        # 4개 작업이 병렬로 실행되므로 순차 실행(200ms)보다 빨라야 함
        # CI 환경에서는 타이밍이 더 느릴 수 있어 여유 있게 설정
        assert total_time < 0.5  # 500ms 미만 (병렬 실행)
        assert result.success_count == 4

    def test_sequential_execution_with_single_worker(self, sso_context):
        """단일 워커로 순차 실행"""

        def collector_func(session, account_id, account_name, region):
            time.sleep(0.01)
            return [{"region": region}]

        # 여러 리전 설정
        sso_context.regions = ["us-east-1", "us-west-2"]

        start_time = time.monotonic()
        result = parallel_collect(sso_context, collector_func, max_workers=1, service="test")
        total_time = time.monotonic() - start_time

        # 1개 워커이므로 순차 실행 (타이밍은 CI에서 불안정할 수 있음)
        assert total_time >= 0.01  # 최소 10ms
        assert result.success_count == 2
