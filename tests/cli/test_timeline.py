# tests/cli/test_timeline.py
"""
cli/ui/timeline 모듈 단위 테스트

Timeline progress component tests.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from unittest.mock import patch

from rich.console import Console

from core.cli.ui.timeline import (
    PhaseContext,
    PhaseInfo,
    PhaseState,
    StepContext,
    StepInfo,
    StepState,
    TimelineParallelTracker,
    TimelineRenderable,
    TimelineTracker,
    _format_elapsed,
    timeline_progress,
)

# =============================================================================
# PhaseInfo / StepInfo 데이터 모델 테스트
# =============================================================================


class TestPhaseInfo:
    """PhaseInfo 데이터 모델 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        phase = PhaseInfo(name="테스트")
        assert phase.name == "테스트"
        assert phase.state == PhaseState.PENDING
        assert phase.steps == []
        assert phase.elapsed == 0.0
        assert phase.progress_total == 0

    def test_progress_fields(self):
        """프로그레스 필드 설정"""
        phase = PhaseInfo(name="수집")
        phase.progress_total = 50
        phase.progress_success = 40
        phase.progress_failed = 10
        assert phase.progress_total == 50
        assert phase.progress_success == 40
        assert phase.progress_failed == 10


class TestStepInfo:
    """StepInfo 데이터 모델 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        step = StepInfo(name="옵션 수집")
        assert step.name == "옵션 수집"
        assert step.state == StepState.PENDING
        assert step.detail == ""
        assert step.elapsed == 0.0


# =============================================================================
# TimelineTracker 테스트
# =============================================================================


class TestTimelineTracker:
    """TimelineTracker 핵심 기능 테스트"""

    def test_init_phases(self):
        """초기 phase 생성"""
        tracker = TimelineTracker(["설정", "수집", "보고서"])
        assert len(tracker._phases) == 3
        assert tracker._phases[0].name == "설정"
        assert tracker._phases[1].name == "수집"
        assert tracker._phases[2].name == "보고서"
        for phase in tracker._phases:
            assert phase.state == PhaseState.PENDING

    def test_add_phase(self):
        """동적 phase 추가"""
        tracker = TimelineTracker(["수집"])
        idx = tracker.add_phase("보고서")
        assert idx == 1
        assert len(tracker._phases) == 2
        assert tracker._phases[1].name == "보고서"

    def test_activate_phase(self):
        """phase 활성화"""
        tracker = TimelineTracker(["수집", "보고서"])
        tracker.activate_phase(0)
        assert tracker._phases[0].state == PhaseState.ACTIVE
        assert tracker._phases[0].start_time > 0

    def test_complete_phase(self):
        """phase 완료"""
        tracker = TimelineTracker(["수집", "보고서"])
        # Mock time.monotonic to avoid flaky results on Windows (GetTickCount64 ~15ms resolution)
        with patch("core.cli.ui.timeline.time.monotonic", side_effect=[100.0, 102.5]):
            tracker.activate_phase(0)
            tracker.complete_phase(0)
        assert tracker._phases[0].state == PhaseState.COMPLETED
        assert tracker._phases[0].elapsed == 2.5

    def test_complete_phase_failed(self):
        """phase 실패"""
        tracker = TimelineTracker(["수집", "보고서"])
        tracker.activate_phase(0)
        tracker.complete_phase(0, failed=True)
        assert tracker._phases[0].state == PhaseState.FAILED

    def test_set_phase_progress(self):
        """phase 프로그레스 업데이트"""
        tracker = TimelineTracker(["수집"])
        tracker.activate_phase(0)
        tracker.set_phase_progress(0, current=5, total=10, success=4, failed=1)
        phase = tracker._phases[0]
        assert phase.progress_current == 5
        assert phase.progress_total == 10
        assert phase.progress_success == 4
        assert phase.progress_failed == 1

    def test_phase_context_manager(self):
        """phase context manager"""
        tracker = TimelineTracker(["수집", "보고서"])
        with tracker.phase(0):
            assert tracker._phases[0].state == PhaseState.ACTIVE
        assert tracker._phases[0].state == PhaseState.COMPLETED

    def test_phase_context_manager_on_error(self):
        """phase context manager 에러 시 FAILED"""
        tracker = TimelineTracker(["수집"])
        try:
            with tracker.phase(0):
                raise ValueError("test error")
        except ValueError:
            pass
        assert tracker._phases[0].state == PhaseState.FAILED

    def test_out_of_bounds_phase(self):
        """범위 밖 phase index는 무시"""
        tracker = TimelineTracker(["수집"])
        tracker.activate_phase(5)  # should not raise
        tracker.complete_phase(5)  # should not raise
        tracker.set_phase_progress(5, 0, 0, 0, 0)  # should not raise


# =============================================================================
# PhaseContext 테스트
# =============================================================================


class TestPhaseContext:
    """PhaseContext 테스트"""

    def test_step_creation(self):
        """step 생성"""
        tracker = TimelineTracker(["수집"])
        ctx = PhaseContext(tracker, 0)
        step = ctx.step("옵션 수집")
        assert isinstance(step, StepContext)
        assert len(tracker._phases[0].steps) == 1
        assert tracker._phases[0].steps[0].name == "옵션 수집"

    def test_parallel_tracker(self):
        """parallel tracker 생성"""
        tracker = TimelineTracker(["수집"])
        ctx = PhaseContext(tracker, 0)
        pt = ctx.parallel_tracker()
        assert isinstance(pt, TimelineParallelTracker)


# =============================================================================
# StepContext 테스트
# =============================================================================


class TestStepContext:
    """StepContext 테스트"""

    def test_step_auto_complete(self):
        """step context manager 자동 완료"""
        tracker = TimelineTracker(["수집"])
        tracker.activate_phase(0)
        with tracker.phase(0) as phase, phase.step("옵션 수집"):
            pass  # auto-complete
        step = tracker._phases[0].steps[0]
        assert step.state == StepState.COMPLETED
        assert step.elapsed >= 0

    def test_step_manual_complete(self):
        """step 수동 완료"""
        tracker = TimelineTracker(["수집"])
        with tracker.phase(0) as phase, phase.step("옵션 수집") as s:
            s.complete("5개 옵션")
        step = tracker._phases[0].steps[0]
        assert step.state == StepState.COMPLETED
        assert step.detail == "5개 옵션"

    def test_step_fail(self):
        """step 실패"""
        tracker = TimelineTracker(["수집"])
        with tracker.phase(0) as phase, phase.step("옵션 수집") as s:
            s.fail("연결 실패")
        step = tracker._phases[0].steps[0]
        assert step.state == StepState.FAILED
        assert step.error == "연결 실패"

    def test_step_auto_fail_on_exception(self):
        """step context manager 예외 시 자동 실패"""
        tracker = TimelineTracker(["수집"])
        try:
            with tracker.phase(0) as phase, phase.step("옵션 수집"):
                raise RuntimeError("test")
        except RuntimeError:
            pass
        step = tracker._phases[0].steps[0]
        assert step.state == StepState.FAILED


# =============================================================================
# TimelineParallelTracker 테스트
# =============================================================================


class TestTimelineParallelTracker:
    """TimelineParallelTracker 테스트"""

    def test_set_total(self):
        """set_total 설정"""
        tracker = TimelineTracker(["수집"])
        pt = tracker.create_parallel_tracker(0)
        pt.set_total(50)
        assert pt.total_count == 50
        assert tracker._phases[0].progress_total == 50

    def test_on_complete_success(self):
        """성공 완료"""
        tracker = TimelineTracker(["수집"])
        pt = tracker.create_parallel_tracker(0)
        pt.set_total(10)
        pt.on_complete(True)
        pt.on_complete(True)
        assert pt.success_count == 2
        assert pt.failed_count == 0

    def test_on_complete_failure(self):
        """실패 완료"""
        tracker = TimelineTracker(["수집"])
        pt = tracker.create_parallel_tracker(0)
        pt.set_total(10)
        pt.on_complete(False)
        pt.on_complete(False)
        assert pt.success_count == 0
        assert pt.failed_count == 2

    def test_mixed_results(self):
        """성공/실패 혼합"""
        tracker = TimelineTracker(["수집"])
        pt = tracker.create_parallel_tracker(0)
        pt.set_total(5)
        pt.on_complete(True)
        pt.on_complete(False)
        pt.on_complete(True)
        success, failed, total = pt.stats
        assert success == 2
        assert failed == 1
        assert total == 5

    def test_thread_safety(self):
        """스레드 안전성"""
        tracker = TimelineTracker(["수집"])
        pt = tracker.create_parallel_tracker(0)
        pt.set_total(1000)

        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = []
            for i in range(1000):
                future = executor.submit(pt.on_complete, i % 2 == 0)
                futures.append(future)
            for f in futures:
                f.result()

        success, failed, total = pt.stats
        assert success == 500
        assert failed == 500
        assert total == 1000


# =============================================================================
# TimelineRenderable 테스트
# =============================================================================


class TestTimelineRenderable:
    """TimelineRenderable 렌더링 테스트"""

    def test_render_pending_phases(self):
        """PENDING 상태 렌더링"""
        phases = [PhaseInfo(name="수집"), PhaseInfo(name="보고서")]
        renderable = TimelineRenderable(phases)
        console = Console(width=80, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "수집" in output
        assert "보고서" in output

    def test_render_active_phase(self):
        """ACTIVE 상태 렌더링"""
        phases = [PhaseInfo(name="수집", state=PhaseState.ACTIVE, start_time=time.monotonic())]
        renderable = TimelineRenderable(phases)
        console = Console(width=80, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "수집" in output

    def test_render_completed_phase(self):
        """COMPLETED 상태 렌더링"""
        phases = [PhaseInfo(name="수집", state=PhaseState.COMPLETED, elapsed=1.5)]
        renderable = TimelineRenderable(phases)
        console = Console(width=80, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "수집" in output
        assert "1.5s" in output

    def test_render_with_progress(self):
        """프로그레스 바 렌더링"""
        phases = [
            PhaseInfo(
                name="수집",
                state=PhaseState.ACTIVE,
                start_time=time.monotonic(),
                progress_total=50,
                progress_success=40,
                progress_failed=10,
            )
        ]
        renderable = TimelineRenderable(phases)
        console = Console(width=120, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "50" in output

    def test_render_with_steps(self):
        """step 포함 렌더링"""
        phases = [
            PhaseInfo(
                name="설정",
                state=PhaseState.COMPLETED,
                elapsed=0.5,
                steps=[
                    StepInfo(name="옵션 수집", state=StepState.COMPLETED, elapsed=0.5),
                ],
            )
        ]
        renderable = TimelineRenderable(phases)
        console = Console(width=80, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "설정" in output
        assert "옵션 수집" in output


# =============================================================================
# _format_elapsed 테스트
# =============================================================================


class TestFormatElapsed:
    """시간 포맷팅 테스트"""

    def test_seconds_short(self):
        """짧은 시간 (초 단위)"""
        assert _format_elapsed(1.5) == "1.5s"
        assert _format_elapsed(0.3) == "0.3s"
        assert _format_elapsed(59.9) == "59.9s"

    def test_minutes(self):
        """분 단위"""
        assert _format_elapsed(60) == "1m 00s"
        assert _format_elapsed(90) == "1m 30s"
        assert _format_elapsed(150.9) == "2m 30s"
        assert _format_elapsed(3661) == "61m 01s"


class TestTimelineRenderableVisuals:
    """TimelineRenderable 시각적 요소 테스트"""

    def test_render_uses_box_drawing_connector(self):
        """box drawing 커넥터(│) 사용 확인"""
        phases = [PhaseInfo(name="수집"), PhaseInfo(name="보고서")]
        renderable = TimelineRenderable(phases)
        console = Console(width=80, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "│" in output

    def test_render_uses_circle_for_pending(self):
        """pending 상태에 ○ 마커 사용"""
        phases = [PhaseInfo(name="보고서")]
        renderable = TimelineRenderable(phases)
        console = Console(width=80, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "○" in output

    def test_render_uses_check_for_completed(self):
        """completed 상태에 ✓ 마커 사용"""
        phases = [PhaseInfo(name="수집", state=PhaseState.COMPLETED, elapsed=1.0)]
        renderable = TimelineRenderable(phases)
        console = Console(width=80, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "✓" in output

    def test_render_uses_styled_progress_bar(self):
        """━ 스타일 프로그레스 바 사용"""
        phases = [
            PhaseInfo(
                name="수집",
                state=PhaseState.ACTIVE,
                start_time=time.monotonic(),
                progress_total=10,
                progress_success=5,
                progress_failed=0,
            )
        ]
        renderable = TimelineRenderable(phases)
        console = Console(width=120, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "━" in output

    def test_render_hides_zero_failures(self):
        """실패가 0이면 실패 카운트 숨김"""
        phases = [
            PhaseInfo(
                name="수집",
                state=PhaseState.COMPLETED,
                elapsed=1.0,
                progress_total=10,
                progress_success=10,
                progress_failed=0,
            )
        ]
        renderable = TimelineRenderable(phases)
        console = Console(width=120, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "✓" in output
        # ✗ should NOT appear when failed=0
        assert "✗" not in output

    def test_render_shows_failures_when_nonzero(self):
        """실패가 있으면 실패 카운트 표시"""
        phases = [
            PhaseInfo(
                name="수집",
                state=PhaseState.COMPLETED,
                elapsed=1.0,
                progress_total=10,
                progress_success=8,
                progress_failed=2,
            )
        ]
        renderable = TimelineRenderable(phases)
        console = Console(width=120, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "✓" in output
        assert "✗" in output

    def test_render_minutes_format(self):
        """2분 이상 소요 시 'm s' 형식"""
        phases = [PhaseInfo(name="수집", state=PhaseState.COMPLETED, elapsed=150.9)]
        renderable = TimelineRenderable(phases)
        console = Console(width=80, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        assert "2m" in output

    def test_render_braille_spinner(self):
        """active 상태에 braille 스피너 사용"""
        phases = [PhaseInfo(name="수집", state=PhaseState.ACTIVE, start_time=time.monotonic())]
        renderable = TimelineRenderable(phases, spinner_frame=0)
        console = Console(width=80, force_terminal=True)
        with console.capture() as capture:
            console.print(renderable)
        output = capture.get()
        # First braille spinner frame
        assert "⠋" in output


# =============================================================================
# timeline_progress context manager 테스트
# =============================================================================


class TestTimelineProgress:
    """timeline_progress context manager 테스트"""

    def test_basic_usage(self):
        """기본 사용"""
        console = Console(width=80, force_terminal=True, file=StringIO())
        with timeline_progress(["수집", "보고서"], console=console) as tl:
            with tl.phase(0):
                pass
            with tl.phase(1):
                pass
        assert tl._phases[0].state == PhaseState.COMPLETED
        assert tl._phases[1].state == PhaseState.COMPLETED

    def test_with_parallel(self):
        """parallel tracker 통합"""
        console = Console(width=80, force_terminal=True, file=StringIO())
        with timeline_progress(["수집"], console=console) as tl:
            tl.activate_phase(0)
            pt = tl.create_parallel_tracker(0)
            pt.set_total(5)
            for _ in range(5):
                pt.on_complete(True)
            tl.complete_phase(0)

        success, failed, total = pt.stats
        assert success == 5
        assert total == 5


# =============================================================================
# 모듈 Export 테스트
# =============================================================================


class TestModuleExports:
    """모듈 export 테스트"""

    def test_import_from_cli_ui(self):
        """core.cli.ui에서 timeline 컴포넌트 import 가능"""
        from core.cli.ui import TimelineParallelTracker, TimelineTracker, timeline_progress

        assert TimelineTracker is not None
        assert TimelineParallelTracker is not None
        assert callable(timeline_progress)

    def test_import_all_classes(self):
        """모든 클래스/함수 import 가능"""
        from core.cli.ui.timeline import (
            PhaseContext,
            PhaseInfo,
            PhaseState,
            StepContext,
            StepInfo,
            StepState,
            TimelineParallelTracker,
            TimelineRenderable,
            TimelineTracker,
            timeline_progress,
        )

        assert PhaseState.PENDING is not None
        assert StepState.COMPLETED is not None
        assert PhaseInfo is not None
        assert StepInfo is not None
        assert TimelineTracker is not None
        assert PhaseContext is not None
        assert StepContext is not None
        assert TimelineParallelTracker is not None
        assert TimelineRenderable is not None
        assert callable(timeline_progress)
