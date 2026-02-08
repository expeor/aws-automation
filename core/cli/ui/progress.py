"""
cli/ui/progress.py - Progress tracking components for parallel execution

Thread-safe progress trackers with success/failure separation for multi-account,
multi-region parallel AWS operations.

Components:
- ParallelTracker: Thread-safe parallel execution tracker with success/failure display
- StepTracker: Step-based workflow tracker with nested parallel support
- DownloadTracker: Download/batch processing tracker
- StatusTracker: Indeterminate progress (spinner only)

Context managers:
- parallel_progress: For parallel collection operations
- step_progress: For multi-step workflows
- download_progress: For download/batch processing
- indeterminate_progress: For unknown duration tasks

Example (parallel collection):
    from core.cli.ui.progress import parallel_progress

    with parallel_progress("리소스 수집") as tracker:
        with quiet_mode():
            result = parallel_collect(ctx, collector, progress_tracker=tracker)

    success, failed, total = tracker.stats
    console.print(f"완료: {success}개 성공, {failed}개 실패")

Example (nested progress):
    with step_progress("분석", total_steps=3) as steps:
        steps.step("EC2 분석")
        with steps.sub_parallel("인스턴스 수집") as tracker:
            parallel_collect(ctx, ec2_collector, progress_tracker=tracker)

        steps.step("RDS 분석")
        with steps.sub_parallel("DB 수집") as tracker:
            parallel_collect(ctx, rds_collector, progress_tracker=tracker)
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.text import Text

if TYPE_CHECKING:
    from rich.console import Console

from .console import console as default_console

# =============================================================================
# Custom Progress Columns
# =============================================================================


class SuccessFailColumn(ProgressColumn):
    """Custom column showing success/fail counts: '40 10'"""

    def __init__(self, tracker: ParallelTracker) -> None:
        super().__init__()
        self._tracker = tracker

    def render(self, task: Task) -> Text:
        """Render the column with success (green) and fail (red) counts."""
        success, failed, _ = self._tracker.stats
        text = Text()
        text.append(f"{success}", style="green")
        text.append("\u2713 ", style="green")  # checkmark
        text.append(f"{failed}", style="red")
        text.append("\u2717", style="red")  # x mark
        return text


# =============================================================================
# Base Tracker Class
# =============================================================================


class BaseTracker:
    """Base class for all progress trackers.

    Provides low-level access to Rich Progress components for backward
    compatibility with existing patterns.
    """

    def __init__(self, progress: Progress, task_id: TaskID, description: str) -> None:
        self._progress = progress
        self._task_id = task_id
        self._description = description

    @property
    def progress(self) -> Progress:
        """Access the underlying Rich Progress object.

        Use this for custom progress updates when the high-level API
        doesn't meet your needs.

        Example (alb_log_analyzer pattern):
            with step_progress("분석", 10) as tracker:
                tracker.progress.update(tracker.task_id, description="Custom")
        """
        return self._progress

    @property
    def task_id(self) -> TaskID:
        """Access the underlying task ID.

        Use with progress property for direct Rich Progress manipulation.
        """
        return self._task_id

    def as_callback(self, include_status: bool = False) -> Callable[..., None]:
        """Convert to a callback function for legacy compatibility.

        Args:
            include_status: If True, returns (message, done) callback.
                           If False, returns simple () -> advance() callback.

        Example (alb_excel_reporter pattern):
            with step_progress("생성", 10) as tracker:
                build_sheets(data, progress=tracker.as_callback(include_status=True))

        Example (ip_search pattern):
            with download_progress("수집", total=len(regions)) as tracker:
                collect_enis(progress_callback=tracker.as_callback())
        """
        # Check if the tracker has its own advance method (e.g., DownloadTracker)
        has_own_advance = hasattr(self, "advance") and callable(getattr(self, "advance", None))

        if include_status:
            # (message: str, done: bool) -> None
            def status_callback(message: str = "", done: bool = False) -> None:
                if done:
                    if has_own_advance:
                        self.advance()  # type: ignore[attr-defined]
                    else:
                        self._progress.advance(self._task_id)
                if message:
                    self._progress.update(self._task_id, description=f"[cyan]{message}")

            return status_callback
        else:
            # () -> None (simple advance)
            def simple_callback(*args: Any, **kwargs: Any) -> None:
                if has_own_advance:
                    self.advance()  # type: ignore[attr-defined]
                else:
                    self._progress.advance(self._task_id)

            return simple_callback


# =============================================================================
# ParallelTracker - Thread-safe parallel execution tracker
# =============================================================================


class ParallelTracker(BaseTracker):
    """Thread-safe parallel execution progress tracker.

    Tracks success and failure counts separately with real-time display.
    Designed for use with parallel_collect() and ParallelSessionExecutor.

    Display format:
        [spinner] 리소스 수집 40 10 / 50 [progress bar] 00:15

    Thread-safety:
        All public methods are thread-safe via internal locking.
        Safe to call on_complete() from multiple worker threads.
    """

    def __init__(
        self,
        progress: Progress,
        task_id: TaskID,
        description: str,
    ) -> None:
        super().__init__(progress, task_id, description)
        self._lock = threading.Lock()
        self._success = 0
        self._failed = 0
        self._total = 0

    def set_total(self, total: int) -> None:
        """Set the total number of tasks.

        Called internally by parallel_collect() after task list is built.
        Can also be called manually for custom parallel implementations.

        Args:
            total: Total number of tasks to process
        """
        with self._lock:
            self._total = total
            self._progress.update(self._task_id, total=total)

    def on_complete(self, success: bool) -> None:
        """Record task completion (thread-safe).

        Called by parallel_collect() for each completed task.
        Updates the progress display with current success/failure counts.

        Args:
            success: True if task succeeded, False if failed
        """
        with self._lock:
            if success:
                self._success += 1
            else:
                self._failed += 1
            self._update_display()

    def _update_display(self) -> None:
        """Update the progress bar display with current counts."""
        completed = self._success + self._failed
        # Description is updated with success/fail in SuccessFailColumn
        self._progress.update(self._task_id, completed=completed)

    @property
    def stats(self) -> tuple[int, int, int]:
        """Get current statistics (success, failed, total).

        Returns:
            Tuple of (success_count, failed_count, total_count)
        """
        with self._lock:
            return (self._success, self._failed, self._total)

    @property
    def success_count(self) -> int:
        """Get successful task count."""
        with self._lock:
            return self._success

    @property
    def failed_count(self) -> int:
        """Get failed task count."""
        with self._lock:
            return self._failed

    @property
    def total_count(self) -> int:
        """Get total task count."""
        with self._lock:
            return self._total


# =============================================================================
# StepTracker - Step-based workflow tracker
# =============================================================================


class StepTracker(BaseTracker):
    """Step-based workflow progress tracker.

    Tracks progress through a sequence of named steps.
    Supports nested parallel progress within each step.

    Display format:
        [spinner] (1/5) 데이터 수집 [progress bar] 00:15
    """

    def __init__(
        self,
        progress: Progress,
        task_id: TaskID,
        description: str,
        total_steps: int,
        console: Console,
    ) -> None:
        super().__init__(progress, task_id, description)
        self._total_steps = total_steps
        self._current_step = 0
        self._console = console
        self._progress.update(task_id, total=total_steps)

    def step(self, description: str) -> None:
        """Move to the next step.

        Args:
            description: Description of the current step
        """
        self._current_step += 1
        step_desc = f"[cyan]({self._current_step}/{self._total_steps}) {description}"
        self._progress.update(self._task_id, description=step_desc, completed=self._current_step - 1)

    def complete_step(self) -> None:
        """Mark the current step as complete."""
        self._progress.update(self._task_id, completed=self._current_step)

    @contextmanager
    def sub_parallel(self, description: str) -> Generator[ParallelTracker, None, None]:
        """Create a nested parallel progress tracker for the current step.

        This creates a second progress bar below the step progress for
        tracking parallel operations within a step.

        Args:
            description: Description for the parallel operation

        Yields:
            ParallelTracker for tracking parallel operations

        Example:
            with step_progress("분석", total_steps=3) as steps:
                steps.step("EC2 분석")
                with steps.sub_parallel("인스턴스 수집") as tracker:
                    parallel_collect(ctx, ec2_collector, progress_tracker=tracker)
        """
        # Create a nested parallel tracker within the same Progress context
        sub_task_id = self._progress.add_task(f"[cyan]  {description}", total=None)
        tracker = ParallelTracker(self._progress, sub_task_id, description)

        # Add success/fail column for sub tracker
        try:
            yield tracker
        finally:
            # Clean up the sub-task
            success, _failed, total = tracker.stats
            final_desc = f"[green]  {description} ({success}/{total} 성공)"
            self._progress.update(sub_task_id, description=final_desc, visible=False)


# =============================================================================
# DownloadTracker - Download/batch processing tracker
# =============================================================================


class DownloadTracker(BaseTracker):
    """Download and batch processing progress tracker.

    Simple M/N progress tracking for downloads and batch operations.
    Does not track success/failure separately (use ParallelTracker for that).

    Display format:
        [spinner] 파일 다운로드 15/100 [progress bar] 00:15
    """

    def __init__(
        self,
        progress: Progress,
        task_id: TaskID,
        description: str,
        total: int,
    ) -> None:
        super().__init__(progress, task_id, description)
        self._total = total
        self._completed = 0
        self._lock = threading.Lock()
        self._progress.update(task_id, total=total)

    def advance(self, count: int = 1) -> None:
        """Advance progress by count (thread-safe).

        Args:
            count: Number of items completed (default 1)
        """
        with self._lock:
            self._completed += count
            self._progress.advance(self._task_id, count)

    def update_description(self, description: str) -> None:
        """Update the progress description."""
        self._progress.update(self._task_id, description=f"[cyan]{description}")

    @property
    def completed(self) -> int:
        """Get current completed count."""
        with self._lock:
            return self._completed

    @property
    def total(self) -> int:
        """Get total count."""
        return self._total


# =============================================================================
# StatusTracker - Indeterminate progress tracker
# =============================================================================


class StatusTracker(BaseTracker):
    """Indeterminate progress tracker (spinner only).

    Use for operations where the total is unknown or indeterminate.

    Display format:
        [spinner] 검색 중...
    """

    def update(self, description: str) -> None:
        """Update the status message.

        Args:
            description: New status message
        """
        self._progress.update(self._task_id, description=f"[cyan]{description}")

    def complete(self, message: str = "완료") -> None:
        """Mark as complete.

        Args:
            message: Completion message
        """
        self._progress.update(self._task_id, description=f"[green]{message}")


# =============================================================================
# Context Managers
# =============================================================================


@contextmanager
def parallel_progress(
    description: str,
    console: Console | None = None,
) -> Generator[ParallelTracker, None, None]:
    """Context manager for parallel execution progress.

    Creates a progress bar with success/failure tracking designed for
    use with parallel_collect() and ParallelSessionExecutor.

    Args:
        description: Description for the progress bar
        console: Rich Console to use (default: cli.ui.console)

    Yields:
        ParallelTracker for tracking parallel operations

    Example:
        with parallel_progress("리소스 수집") as tracker:
            with quiet_mode():
                result = parallel_collect(ctx, collector, progress_tracker=tracker)

        success, failed, total = tracker.stats
        console.print(f"완료: {success}개 성공, {failed}개 실패")
    """
    cons = console or default_console

    # We need to create the tracker first to pass to SuccessFailColumn
    # So we create a placeholder Progress first
    tracker: ParallelTracker | None = None

    # Custom progress columns for parallel tracking
    def create_columns(t: ParallelTracker) -> list[ProgressColumn]:
        return [
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            SuccessFailColumn(t),
            TextColumn("/"),
            MofNCompleteColumn(),
            BarColumn(),
            TimeElapsedColumn(),
        ]

    # Create progress with basic columns first
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TextColumn(""),  # Placeholder for SuccessFailColumn
        TextColumn("/"),
        MofNCompleteColumn(),
        BarColumn(bar_width=40),
        TimeElapsedColumn(),
        console=cons,
        expand=False,
    )

    with progress:
        task_id = progress.add_task(f"[cyan]{description}", total=None)
        tracker = ParallelTracker(progress, task_id, description)

        # Replace placeholder column with actual SuccessFailColumn
        progress.columns = tuple(create_columns(tracker))

        try:
            yield tracker
        finally:
            # Update final status
            _success, failed, total = tracker.stats
            if total > 0:
                if failed == 0:
                    final_desc = f"[green]{description} 완료"
                else:
                    final_desc = f"[yellow]{description} 완료 ({failed}개 실패)"
                progress.update(task_id, description=final_desc)


@contextmanager
def step_progress(
    description: str,
    total_steps: int,
    console: Console | None = None,
) -> Generator[StepTracker, None, None]:
    """Context manager for step-based workflow progress.

    Creates a progress bar for tracking multi-step workflows.

    Args:
        description: Overall workflow description
        total_steps: Total number of steps
        console: Rich Console to use (default: cli.ui.console)

    Yields:
        StepTracker for tracking step progress

    Example:
        with step_progress("분석", total_steps=5) as steps:
            steps.step("EC2 분석")
            # do EC2 work
            steps.complete_step()

            steps.step("RDS 분석")
            # do RDS work
            steps.complete_step()
    """
    cons = console or default_console

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=cons,
        expand=False,
    )

    with progress:
        task_id = progress.add_task(f"[cyan]{description}", total=total_steps)
        tracker = StepTracker(progress, task_id, description, total_steps, cons)

        try:
            yield tracker
        finally:
            # Mark complete
            progress.update(task_id, description=f"[green]{description} 완료", completed=total_steps)


@contextmanager
def download_progress(
    description: str,
    total: int,
    console: Console | None = None,
) -> Generator[DownloadTracker, None, None]:
    """Context manager for download/batch processing progress.

    Creates a simple M/N progress bar for tracking downloads or batch processing.

    Args:
        description: Description for the progress bar
        total: Total number of items
        console: Rich Console to use (default: cli.ui.console)

    Yields:
        DownloadTracker for tracking progress

    Example:
        with download_progress("파일 다운로드", total=len(files)) as tracker:
            for file in files:
                download(file)
                tracker.advance()
    """
    cons = console or default_console

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=cons,
        expand=False,
    )

    with progress:
        task_id = progress.add_task(f"[cyan]{description}", total=total)
        tracker = DownloadTracker(progress, task_id, description, total)

        try:
            yield tracker
        finally:
            progress.update(task_id, description=f"[green]{description} 완료")


@contextmanager
def indeterminate_progress(
    description: str,
    console: Console | None = None,
) -> Generator[StatusTracker, None, None]:
    """Context manager for indeterminate progress (spinner only).

    Creates a spinner-only progress indicator for operations where
    the total is unknown.

    Args:
        description: Initial description
        console: Rich Console to use (default: cli.ui.console)

    Yields:
        StatusTracker for updating status

    Example:
        with indeterminate_progress("검색 중...") as status:
            status.update("데이터베이스 쿼리 중...")
            results = query_database()
            status.update("결과 처리 중...")
            process(results)
            status.complete("검색 완료")
    """
    cons = console or default_console

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=cons,
        expand=False,
    )

    with progress:
        task_id = progress.add_task(f"[cyan]{description}", total=None)
        tracker = StatusTracker(progress, task_id, description)

        try:
            yield tracker
        finally:
            pass  # StatusTracker.complete() handles final status


# =============================================================================
# Documentation: quiet_mode relationship
# =============================================================================

"""
quiet_mode와 Progress bar의 관계:

quiet_mode()는 parallel 실행 중 개별 worker의 console 출력을 억제합니다.

Progress bar와 quiet_mode 관계:
- Progress bar는 메인 스레드에서 동작 (quiet 영향 없음)
- Worker thread 내 console.print()는 quiet_mode에 의해 억제됨
- ParallelTracker.on_complete()는 Progress를 직접 업데이트하므로 quiet 영향 없음

사용 패턴:
    with parallel_progress("수집") as tracker:
        with quiet_mode():  # worker 출력만 억제, progress bar는 유지
            parallel_collect(ctx, collector, progress_tracker=tracker)
"""


__all__ = [
    # Trackers
    "BaseTracker",
    "ParallelTracker",
    "StepTracker",
    "DownloadTracker",
    "StatusTracker",
    # Context managers
    "parallel_progress",
    "step_progress",
    "download_progress",
    "indeterminate_progress",
    # Custom columns
    "SuccessFailColumn",
]
