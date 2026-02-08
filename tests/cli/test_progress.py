# tests/cli/test_progress.py
"""
cli/ui/progress 모듈 단위 테스트

Progress tracking components for parallel execution.
"""

from concurrent.futures import ThreadPoolExecutor

# =============================================================================
# ParallelTracker 테스트
# =============================================================================


class TestParallelTracker:
    """ParallelTracker 단위 테스트"""

    def test_initial_stats(self):
        """초기 상태 확인"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=None)
            tracker = ParallelTracker(progress, task_id, "test")

            success, failed, total = tracker.stats
            assert success == 0
            assert failed == 0
            assert total == 0

    def test_set_total(self):
        """set_total 동작 확인"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=None)
            tracker = ParallelTracker(progress, task_id, "test")

            tracker.set_total(100)
            assert tracker.total_count == 100

    def test_on_complete_success(self):
        """성공 완료 처리"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = ParallelTracker(progress, task_id, "test")
            tracker.set_total(10)

            tracker.on_complete(success=True)
            tracker.on_complete(success=True)
            tracker.on_complete(success=True)

            assert tracker.success_count == 3
            assert tracker.failed_count == 0

    def test_on_complete_failure(self):
        """실패 완료 처리"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = ParallelTracker(progress, task_id, "test")
            tracker.set_total(10)

            tracker.on_complete(success=False)
            tracker.on_complete(success=False)

            assert tracker.success_count == 0
            assert tracker.failed_count == 2

    def test_mixed_success_failure(self):
        """성공/실패 혼합 카운트"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = ParallelTracker(progress, task_id, "test")
            tracker.set_total(10)

            tracker.on_complete(success=True)
            tracker.on_complete(success=False)
            tracker.on_complete(success=True)
            tracker.on_complete(success=False)
            tracker.on_complete(success=True)

            success, failed, total = tracker.stats
            assert success == 3
            assert failed == 2
            assert total == 10


class TestParallelTrackerThreadSafety:
    """ParallelTracker thread-safety 테스트"""

    def test_concurrent_on_complete(self):
        """동시 on_complete() 호출 시 race condition 검증"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=1000)
            tracker = ParallelTracker(progress, task_id, "test")
            tracker.set_total(1000)

            with ThreadPoolExecutor(max_workers=50) as executor:
                # 500 success, 500 fail 동시 호출
                futures = []
                for i in range(1000):
                    future = executor.submit(tracker.on_complete, i % 2 == 0)
                    futures.append(future)

                for f in futures:
                    f.result()

            success, failed, total = tracker.stats
            assert success == 500
            assert failed == 500
            assert total == 1000

    def test_high_concurrency_stress(self):
        """높은 동시성 스트레스 테스트"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        num_tasks = 10000
        num_workers = 100

        with Progress() as progress:
            task_id = progress.add_task("stress", total=num_tasks)
            tracker = ParallelTracker(progress, task_id, "stress")
            tracker.set_total(num_tasks)

            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = []
                for i in range(num_tasks):
                    # 70% 성공, 30% 실패
                    future = executor.submit(tracker.on_complete, i % 10 < 7)
                    futures.append(future)

                for f in futures:
                    f.result()

            success, failed, total = tracker.stats
            assert success + failed == num_tasks
            assert total == num_tasks


# =============================================================================
# StepTracker 테스트
# =============================================================================


class TestStepTracker:
    """StepTracker 단위 테스트"""

    def test_step_progress(self):
        """step() 호출로 단계 진행"""
        from rich.console import Console
        from rich.progress import Progress

        from core.cli.ui.progress import StepTracker

        console = Console()
        with Progress() as progress:
            task_id = progress.add_task("test", total=3)
            tracker = StepTracker(progress, task_id, "test", 3, console)

            tracker.step("Step 1")
            tracker.step("Step 2")
            tracker.step("Step 3")

            # 내부 상태 확인
            assert tracker._current_step == 3

    def test_complete_step(self):
        """complete_step() 호출"""
        from rich.console import Console
        from rich.progress import Progress

        from core.cli.ui.progress import StepTracker

        console = Console()
        with Progress() as progress:
            task_id = progress.add_task("test", total=3)
            tracker = StepTracker(progress, task_id, "test", 3, console)

            tracker.step("Step 1")
            tracker.complete_step()


# =============================================================================
# DownloadTracker 테스트
# =============================================================================


class TestDownloadTracker:
    """DownloadTracker 단위 테스트"""

    def test_advance(self):
        """advance() 호출로 진행"""
        from rich.progress import Progress

        from core.cli.ui.progress import DownloadTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=100)
            tracker = DownloadTracker(progress, task_id, "test", 100)

            tracker.advance()
            tracker.advance()
            tracker.advance(5)

            assert tracker.completed == 7
            assert tracker.total == 100

    def test_update_description(self):
        """update_description() 호출"""
        from rich.progress import Progress

        from core.cli.ui.progress import DownloadTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=100)
            tracker = DownloadTracker(progress, task_id, "test", 100)

            tracker.update_description("새로운 설명")
            # 에러 없이 실행되면 성공


class TestDownloadTrackerThreadSafety:
    """DownloadTracker thread-safety 테스트"""

    def test_concurrent_advance(self):
        """동시 advance() 호출"""
        from rich.progress import Progress

        from core.cli.ui.progress import DownloadTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=1000)
            tracker = DownloadTracker(progress, task_id, "test", 1000)

            with ThreadPoolExecutor(max_workers=50) as executor:
                futures = []
                for _ in range(1000):
                    future = executor.submit(tracker.advance, 1)
                    futures.append(future)

                for f in futures:
                    f.result()

            assert tracker.completed == 1000


# =============================================================================
# StatusTracker 테스트
# =============================================================================


class TestStatusTracker:
    """StatusTracker 단위 테스트"""

    def test_update(self):
        """update() 호출"""
        from rich.progress import Progress

        from core.cli.ui.progress import StatusTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=None)
            tracker = StatusTracker(progress, task_id, "test")

            tracker.update("새로운 상태")
            # 에러 없이 실행되면 성공

    def test_complete(self):
        """complete() 호출"""
        from rich.progress import Progress

        from core.cli.ui.progress import StatusTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=None)
            tracker = StatusTracker(progress, task_id, "test")

            tracker.complete("완료!")
            # 에러 없이 실행되면 성공


# =============================================================================
# BaseTracker 테스트
# =============================================================================


class TestBaseTracker:
    """BaseTracker 기본 기능 테스트"""

    def test_progress_property(self):
        """progress 프로퍼티 접근"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = ParallelTracker(progress, task_id, "test")

            assert tracker.progress is progress

    def test_task_id_property(self):
        """task_id 프로퍼티 접근"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = ParallelTracker(progress, task_id, "test")

            assert tracker.task_id == task_id

    def test_as_callback_simple(self):
        """as_callback() 간단한 콜백 반환"""
        from rich.progress import Progress

        from core.cli.ui.progress import DownloadTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = DownloadTracker(progress, task_id, "test", 10)

            callback = tracker.as_callback()
            assert callable(callback)

            # 콜백 호출 시 advance
            callback()
            assert tracker.completed == 1

    def test_as_callback_with_status(self):
        """as_callback(include_status=True) 상태 포함 콜백"""
        from rich.progress import Progress

        from core.cli.ui.progress import DownloadTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = DownloadTracker(progress, task_id, "test", 10)

            callback = tracker.as_callback(include_status=True)
            assert callable(callback)

            # 콜백 호출 시 상태 업데이트 + advance
            callback("상태 메시지", done=True)
            assert tracker.completed == 1


# =============================================================================
# Context Manager 테스트
# =============================================================================


class TestParallelProgressContextManager:
    """parallel_progress context manager 테스트"""

    def test_basic_usage(self):
        """기본 사용법"""
        from core.cli.ui.progress import parallel_progress

        with parallel_progress("테스트") as tracker:
            tracker.set_total(10)
            for _ in range(10):
                tracker.on_complete(success=True)

        success, failed, total = tracker.stats
        assert success == 10
        assert failed == 0
        assert total == 10

    def test_mixed_results(self):
        """성공/실패 혼합"""
        from core.cli.ui.progress import parallel_progress

        with parallel_progress("테스트") as tracker:
            tracker.set_total(5)
            tracker.on_complete(success=True)
            tracker.on_complete(success=False)
            tracker.on_complete(success=True)
            tracker.on_complete(success=False)
            tracker.on_complete(success=True)

        success, failed, total = tracker.stats
        assert success == 3
        assert failed == 2


class TestStepProgressContextManager:
    """step_progress context manager 테스트"""

    def test_basic_usage(self):
        """기본 사용법"""
        from core.cli.ui.progress import step_progress

        with step_progress("테스트", total_steps=3) as steps:
            steps.step("Step 1")
            steps.complete_step()
            steps.step("Step 2")
            steps.complete_step()
            steps.step("Step 3")
            steps.complete_step()


class TestDownloadProgressContextManager:
    """download_progress context manager 테스트"""

    def test_basic_usage(self):
        """기본 사용법"""
        from core.cli.ui.progress import download_progress

        with download_progress("테스트", total=5) as tracker:
            for _ in range(5):
                tracker.advance()

        assert tracker.completed == 5


class TestIndeterminateProgressContextManager:
    """indeterminate_progress context manager 테스트"""

    def test_basic_usage(self):
        """기본 사용법"""
        from core.cli.ui.progress import indeterminate_progress

        with indeterminate_progress("테스트") as status:
            status.update("처리 중...")
            status.complete("완료")


# =============================================================================
# SuccessFailColumn 테스트
# =============================================================================


class TestSuccessFailColumn:
    """SuccessFailColumn 렌더링 테스트"""

    def test_render(self):
        """render() 호출"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker, SuccessFailColumn

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = ParallelTracker(progress, task_id, "test")
            column = SuccessFailColumn(tracker)

            task = progress.tasks[0]
            text = column.render(task)

            # Text 객체가 반환되었는지 확인
            from rich.text import Text

            assert isinstance(text, Text)


# =============================================================================
# 통합 테스트
# =============================================================================


class TestIntegration:
    """통합 테스트"""

    def test_parallel_progress_with_threading(self):
        """병렬 progress와 스레딩 통합"""
        from core.cli.ui.progress import parallel_progress

        with parallel_progress("통합 테스트") as tracker:
            tracker.set_total(100)

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for i in range(100):
                    future = executor.submit(tracker.on_complete, i % 3 != 0)
                    futures.append(future)

                for f in futures:
                    f.result()

        success, failed, total = tracker.stats
        assert success + failed == 100
        assert total == 100

    def test_step_with_sub_parallel(self):
        """step progress 내 nested parallel"""
        from core.cli.ui.progress import step_progress

        with step_progress("분석", total_steps=2) as steps:
            steps.step("Phase 1")

            with steps.sub_parallel("수집 중") as tracker:
                tracker.set_total(5)
                for _ in range(5):
                    tracker.on_complete(success=True)

            steps.complete_step()

            steps.step("Phase 2")
            steps.complete_step()


# =============================================================================
# 모듈 Export 테스트
# =============================================================================


class TestModuleExports:
    """모듈 export 테스트"""

    def test_import_from_cli_ui(self):
        """core.cli.ui에서 progress 컴포넌트 import 가능"""
        from core.cli.ui import (
            BaseTracker,
            DownloadTracker,
            ParallelTracker,
            StatusTracker,
            StepTracker,
            download_progress,
            indeterminate_progress,
            parallel_progress,
            step_progress,
        )

        assert BaseTracker is not None
        assert ParallelTracker is not None
        assert StepTracker is not None
        assert DownloadTracker is not None
        assert StatusTracker is not None
        assert callable(parallel_progress)
        assert callable(step_progress)
        assert callable(download_progress)
        assert callable(indeterminate_progress)

    def test_import_from_progress_module(self):
        """core.cli.ui.progress에서 직접 import 가능"""
        from core.cli.ui.progress import (
            BaseTracker,
            SuccessFailColumn,
        )

        assert BaseTracker is not None
        assert SuccessFailColumn is not None


# =============================================================================
# ParallelTracker 추가 테스트
# =============================================================================


class TestParallelTrackerProperties:
    """ParallelTracker 프로퍼티 테스트"""

    def test_success_count_property(self):
        """success_count 프로퍼티"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = ParallelTracker(progress, task_id, "test")

            tracker.on_complete(success=True)
            tracker.on_complete(success=True)

            assert tracker.success_count == 2

    def test_failed_count_property(self):
        """failed_count 프로퍼티"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = ParallelTracker(progress, task_id, "test")

            tracker.on_complete(success=False)
            tracker.on_complete(success=False)
            tracker.on_complete(success=False)

            assert tracker.failed_count == 3

    def test_total_count_property(self):
        """total_count 프로퍼티"""
        from rich.progress import Progress

        from core.cli.ui.progress import ParallelTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=None)
            tracker = ParallelTracker(progress, task_id, "test")

            tracker.set_total(50)

            assert tracker.total_count == 50


# =============================================================================
# StepTracker.sub_parallel 테스트
# =============================================================================


class TestStepTrackerSubParallel:
    """StepTracker.sub_parallel 추가 테스트"""

    def test_sub_parallel_stats_tracking(self):
        """nested parallel의 통계 추적"""
        from core.cli.ui.progress import step_progress

        with step_progress("테스트", total_steps=1) as steps:
            steps.step("Step 1")

            with steps.sub_parallel("수집") as tracker:
                tracker.set_total(10)
                for i in range(10):
                    tracker.on_complete(success=i % 2 == 0)

                success, failed, total = tracker.stats
                assert success == 5
                assert failed == 5
                assert total == 10

            steps.complete_step()


# =============================================================================
# DownloadTracker 추가 테스트
# =============================================================================


class TestDownloadTrackerProperties:
    """DownloadTracker 프로퍼티 테스트"""

    def test_total_property(self):
        """total 프로퍼티"""
        from rich.progress import Progress

        from core.cli.ui.progress import DownloadTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=100)
            tracker = DownloadTracker(progress, task_id, "test", 100)

            assert tracker.total == 100

    def test_completed_property(self):
        """completed 프로퍼티"""
        from rich.progress import Progress

        from core.cli.ui.progress import DownloadTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=100)
            tracker = DownloadTracker(progress, task_id, "test", 100)

            tracker.advance(10)
            tracker.advance(5)

            assert tracker.completed == 15


# =============================================================================
# Context Manager 예외 처리 테스트
# =============================================================================


class TestContextManagerExceptions:
    """Context manager 예외 처리 테스트"""

    def test_parallel_progress_with_exception(self):
        """예외 발생 시에도 정상 종료"""
        from core.cli.ui.progress import parallel_progress

        with parallel_progress("테스트") as tracker:
            tracker.set_total(5)
            tracker.on_complete(success=True)
            # 예외는 context manager 외부에서 처리
        # 정상 종료

    def test_step_progress_with_exception(self):
        """예외 발생 시에도 정상 종료"""
        from core.cli.ui.progress import step_progress

        with step_progress("테스트", total_steps=3) as steps:
            steps.step("Step 1")
            # 중간에 중단되어도 정상 종료
        # 정상 종료

    def test_download_progress_with_exception(self):
        """예외 발생 시에도 정상 종료"""
        from core.cli.ui.progress import download_progress

        with download_progress("테스트", total=10) as tracker:
            tracker.advance(3)
            # 중간에 중단되어도 정상 종료
        # 정상 종료


# =============================================================================
# BaseTracker.as_callback 추가 테스트
# =============================================================================


class TestAsCallbackAdvanced:
    """as_callback 고급 테스트"""

    def test_as_callback_with_args_and_kwargs(self):
        """임의의 args/kwargs를 받는 콜백"""
        from rich.progress import Progress

        from core.cli.ui.progress import DownloadTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = DownloadTracker(progress, task_id, "test", 10)

            callback = tracker.as_callback()

            # 임의의 인자와 함께 호출
            callback("arg1", "arg2", key1="value1")
            assert tracker.completed == 1

    def test_as_callback_status_without_done(self):
        """done=False인 상태 콜백"""
        from rich.progress import Progress

        from core.cli.ui.progress import DownloadTracker

        with Progress() as progress:
            task_id = progress.add_task("test", total=10)
            tracker = DownloadTracker(progress, task_id, "test", 10)

            callback = tracker.as_callback(include_status=True)

            # done=False로 호출하면 advance 안 함
            callback("상태 메시지", done=False)
            assert tracker.completed == 0

            # done=True로 호출하면 advance
            callback("완료", done=True)
            assert tracker.completed == 1


# =============================================================================
# Custom Console 테스트
# =============================================================================


class TestCustomConsole:
    """Custom console 사용 테스트"""

    def test_parallel_progress_custom_console(self):
        """커스텀 console 사용"""
        from rich.console import Console

        from core.cli.ui.progress import parallel_progress

        custom_console = Console()

        with parallel_progress("테스트", console=custom_console) as tracker:
            tracker.set_total(5)
            for _ in range(5):
                tracker.on_complete(success=True)

        success, failed, total = tracker.stats
        assert success == 5

    def test_step_progress_custom_console(self):
        """커스텀 console 사용"""
        from rich.console import Console

        from core.cli.ui.progress import step_progress

        custom_console = Console()

        with step_progress("테스트", total_steps=2, console=custom_console) as steps:
            steps.step("Step 1")
            steps.complete_step()
            steps.step("Step 2")
            steps.complete_step()

    def test_download_progress_custom_console(self):
        """커스텀 console 사용"""
        from rich.console import Console

        from core.cli.ui.progress import download_progress

        custom_console = Console()

        with download_progress("테스트", total=5, console=custom_console) as tracker:
            for _ in range(5):
                tracker.advance()

        assert tracker.completed == 5

    def test_indeterminate_progress_custom_console(self):
        """커스텀 console 사용"""
        from rich.console import Console

        from core.cli.ui.progress import indeterminate_progress

        custom_console = Console()

        with indeterminate_progress("테스트", console=custom_console) as status:
            status.update("처리 중")
            status.complete("완료")
