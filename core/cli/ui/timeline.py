"""
cli/ui/timeline.py - Timeline progress component

Provides a vertical timeline UI for tool execution phases:
- Setup (collect_options)
- Collection (parallel_collect)
- Report generation (generate_reports)

Rendering example (active):
    ✓  설정                              0.5s
    │
    ⠹  수집  ━━━━━━━━━━━━━━╸──────  45/50  38✓ 7✗  12.3s
    │
    ○  보고서

Rendering example (completed):
    ✓  설정                              0.5s
    │
    ✓  수집  ━━━━━━━━━━━━━━━━━━━━  50/50  48✓ 2✗  2m 31s
    │
    ✓  보고서                            1.2s

Classes:
    TimelineTracker: Main controller (Rich.Live based)
    PhaseContext: Context manager for a single phase
    StepContext: Context manager for a step within a phase
    TimelineParallelTracker: Bridge to ParallelTracker interface
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from rich.live import Live
from rich.text import Text

from .console import SYMBOL_ERROR, SYMBOL_SUCCESS
from .console import console as default_console

if TYPE_CHECKING:
    from rich.console import Console, ConsoleOptions, RenderResult


# =============================================================================
# Symbols & Style Constants
# =============================================================================

# Braille spinner frames for smooth animation
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# Box drawing connector
CONNECTOR = "│"

# Progress bar characters
BAR_FILLED = "━"
BAR_TIP = "╸"
BAR_EMPTY = "─"
BAR_WIDTH = 24

# Colors
COLOR_ACTIVE = "#FF9900"  # AWS Orange
COLOR_DONE = "green"
COLOR_FAIL = "red"
COLOR_DIM = "dim"


# =============================================================================
# State enums
# =============================================================================


class PhaseState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class StepState(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# Data models
# =============================================================================


@dataclass
class StepInfo:
    """A step within a phase."""

    name: str
    state: StepState = StepState.PENDING
    detail: str = ""
    elapsed: float = 0.0
    start_time: float = 0.0
    error: str = ""


@dataclass
class PhaseInfo:
    """A phase in the timeline."""

    name: str
    state: PhaseState = PhaseState.PENDING
    steps: list[StepInfo] = field(default_factory=list)
    elapsed: float = 0.0
    start_time: float = 0.0
    # Progress tracking for parallel operations
    progress_current: int = 0
    progress_total: int = 0
    progress_success: int = 0
    progress_failed: int = 0


# =============================================================================
# Timeline Renderable
# =============================================================================


class TimelineRenderable:
    """Custom Rich renderable for polished timeline display.

    Uses Unicode box drawing, braille spinners, and AWS-orange styled
    progress bars for a visually appealing terminal experience.
    """

    def __init__(self, phases: list[PhaseInfo], spinner_frame: int = 0) -> None:
        self._phases = phases
        self._spinner_frame = spinner_frame

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        for i, phase in enumerate(self._phases):
            is_last = i == len(self._phases) - 1

            # Phase header line
            yield self._render_phase_header(phase)

            # Steps within this phase
            for step in phase.steps:
                yield self._render_step(step)

            # Connector to next phase (unless last)
            if not is_last:
                yield Text(f"  {CONNECTOR}", style=COLOR_DIM)

    def _render_phase_header(self, phase: PhaseInfo) -> Text:
        """Render a phase header line with marker, progress bar, and elapsed time."""
        text = Text()

        # ── Marker ──
        if phase.state == PhaseState.ACTIVE:
            spinner = SPINNER_FRAMES[self._spinner_frame % len(SPINNER_FRAMES)]
            text.append(f"  {spinner}  ", style=f"bold {COLOR_ACTIVE}")
        elif phase.state == PhaseState.COMPLETED:
            text.append(f"  {SYMBOL_SUCCESS}  ", style=f"bold {COLOR_DONE}")
        elif phase.state == PhaseState.FAILED:
            text.append(f"  {SYMBOL_ERROR}  ", style=f"bold {COLOR_FAIL}")
        else:
            text.append("  ○  ", style=COLOR_DIM)

        # ── Phase name ──
        if phase.state == PhaseState.ACTIVE:
            text.append(phase.name, style=f"bold {COLOR_ACTIVE}")
        elif phase.state == PhaseState.COMPLETED:
            text.append(phase.name, style=COLOR_DONE)
        elif phase.state == PhaseState.FAILED:
            text.append(phase.name, style=COLOR_FAIL)
        else:
            text.append(phase.name, style=COLOR_DIM)

        # ── Progress bar (for parallel operations) ──
        if phase.progress_total > 0:
            self._append_progress_bar(text, phase)

        # ── Elapsed time ──
        self._append_elapsed(text, phase)

        return text

    def _append_progress_bar(self, text: Text, phase: PhaseInfo) -> None:
        """Append a styled progress bar with stats to a Text object."""
        text.append("  ", style="")
        completed = phase.progress_success + phase.progress_failed
        ratio = completed / phase.progress_total if phase.progress_total > 0 else 0
        filled = int(BAR_WIDTH * ratio)

        # Tip only while actively progressing (not 100%)
        show_tip = filled < BAR_WIDTH and phase.state == PhaseState.ACTIVE
        tip = 1 if show_tip else 0
        empty = BAR_WIDTH - filled - tip

        # Bar color by state: green=done, red=failed, orange=active
        if phase.state == PhaseState.COMPLETED:
            bar_style = COLOR_DONE
        elif phase.state == PhaseState.FAILED:
            bar_style = COLOR_FAIL
        else:
            bar_style = COLOR_ACTIVE

        text.append(BAR_FILLED * filled, style=bar_style)
        if tip:
            text.append(BAR_TIP, style=bar_style)
        if empty > 0:
            text.append(BAR_EMPTY * empty, style=COLOR_DIM)

        # Count: completed/total
        text.append(f"  {completed}/{phase.progress_total}", style="bold")

        # Success count
        if phase.progress_success > 0:
            text.append(f"  {phase.progress_success}", style=f"bold {COLOR_DONE}")
            text.append(SYMBOL_SUCCESS, style=COLOR_DONE)

        # Failed count (only show when > 0 to reduce noise)
        if phase.progress_failed > 0:
            text.append(f" {phase.progress_failed}", style=f"bold {COLOR_FAIL}")
            text.append(SYMBOL_ERROR, style=COLOR_FAIL)

    def _append_elapsed(self, text: Text, phase: PhaseInfo) -> None:
        """Append formatted elapsed time to a Text object."""
        if phase.elapsed > 0:
            text.append(f"  {_format_elapsed(phase.elapsed)}", style=COLOR_DIM)
        elif phase.state == PhaseState.ACTIVE and phase.start_time > 0:
            elapsed = time.monotonic() - phase.start_time
            text.append(f"  {_format_elapsed(elapsed)}", style=COLOR_DIM)

    def _render_step(self, step: StepInfo) -> Text:
        """Render a step line within a phase."""
        text = Text()
        text.append(f"  {CONNECTOR}  ", style=COLOR_DIM)

        if step.state == StepState.COMPLETED:
            text.append(f"{SYMBOL_SUCCESS} ", style=COLOR_DONE)
            text.append(step.name, style=COLOR_DONE)
        elif step.state == StepState.FAILED:
            text.append(f"{SYMBOL_ERROR} ", style=COLOR_FAIL)
            text.append(step.name, style=COLOR_FAIL)
        elif step.state == StepState.IN_PROGRESS:
            spinner = SPINNER_FRAMES[self._spinner_frame % len(SPINNER_FRAMES)]
            text.append(f"{spinner} ", style=COLOR_ACTIVE)
            text.append(step.name, style=f"bold {COLOR_ACTIVE}")
        elif step.state == StepState.SKIPPED:
            text.append("─ ", style=COLOR_DIM)
            text.append(step.name, style=COLOR_DIM)
        else:
            text.append("  ", style=COLOR_DIM)
            text.append(step.name, style=COLOR_DIM)

        if step.detail:
            text.append(f" ({step.detail})", style=COLOR_DIM)

        if step.elapsed > 0:
            text.append(f"  {_format_elapsed(step.elapsed)}", style=COLOR_DIM)

        if step.error:
            text.append(f"  {step.error}", style=COLOR_FAIL)

        return text


def _format_elapsed(seconds: float) -> str:
    """Format elapsed time for display.

    Returns '1.5s' for short durations, '2m 31s' for longer ones.
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs:02d}s"


# =============================================================================
# TimelineParallelTracker - Bridge to ParallelTracker interface
# =============================================================================


class TimelineParallelTracker:
    """Bridges TimelineTracker with the ParallelTracker interface.

    Implements set_total() and on_complete() as expected by
    ParallelSessionExecutor.execute().
    """

    def __init__(self, tracker: TimelineTracker, phase_index: int) -> None:
        self._tracker = tracker
        self._phase_index = phase_index
        self._lock = threading.Lock()
        self._success = 0
        self._failed = 0
        self._total = 0

    def set_total(self, total: int) -> None:
        """Set total task count."""
        with self._lock:
            self._total = total
            self._tracker.set_phase_progress(
                self._phase_index,
                current=0,
                total=total,
                success=0,
                failed=0,
            )

    def on_complete(self, success: bool) -> None:
        """Record task completion (thread-safe)."""
        with self._lock:
            if success:
                self._success += 1
            else:
                self._failed += 1
            self._tracker.set_phase_progress(
                self._phase_index,
                current=self._success + self._failed,
                total=self._total,
                success=self._success,
                failed=self._failed,
            )

    @property
    def stats(self) -> tuple[int, int, int]:
        """Get (success, failed, total)."""
        with self._lock:
            return (self._success, self._failed, self._total)

    @property
    def success_count(self) -> int:
        with self._lock:
            return self._success

    @property
    def failed_count(self) -> int:
        with self._lock:
            return self._failed

    @property
    def total_count(self) -> int:
        with self._lock:
            return self._total


# =============================================================================
# StepContext - Context manager for steps
# =============================================================================


class StepContext:
    """Context manager for a step within a phase."""

    def __init__(self, tracker: TimelineTracker, phase_index: int, step_index: int) -> None:
        self._tracker = tracker
        self._phase_index = phase_index
        self._step_index = step_index
        self._start_time = 0.0

    def complete(self, detail: str = "") -> None:
        """Mark step as completed."""
        elapsed = time.monotonic() - self._start_time if self._start_time > 0 else 0.0
        with self._tracker._lock:
            phase = self._tracker._phases[self._phase_index]
            step = phase.steps[self._step_index]
            step.state = StepState.COMPLETED
            step.elapsed = elapsed
            if detail:
                step.detail = detail

    def fail(self, error: str = "") -> None:
        """Mark step as failed."""
        elapsed = time.monotonic() - self._start_time if self._start_time > 0 else 0.0
        with self._tracker._lock:
            phase = self._tracker._phases[self._phase_index]
            step = phase.steps[self._step_index]
            step.state = StepState.FAILED
            step.elapsed = elapsed
            step.error = error

    def __enter__(self) -> StepContext:
        self._start_time = time.monotonic()
        with self._tracker._lock:
            phase = self._tracker._phases[self._phase_index]
            step = phase.steps[self._step_index]
            step.state = StepState.IN_PROGRESS
            step.start_time = self._start_time
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        with self._tracker._lock:
            phase = self._tracker._phases[self._phase_index]
            step = phase.steps[self._step_index]
            if step.state == StepState.IN_PROGRESS:
                # Auto-complete if not explicitly completed or failed
                if exc_type is not None:
                    step.state = StepState.FAILED
                    step.error = str(exc_val) if exc_val else ""
                else:
                    step.state = StepState.COMPLETED
                step.elapsed = time.monotonic() - self._start_time


# =============================================================================
# PhaseContext - Context manager for phases
# =============================================================================


class PhaseContext:
    """Context manager for a timeline phase."""

    def __init__(self, tracker: TimelineTracker, phase_index: int) -> None:
        self._tracker = tracker
        self._phase_index = phase_index

    def step(self, name: str) -> StepContext:
        """Add and return a step context manager."""
        with self._tracker._lock:
            phase = self._tracker._phases[self._phase_index]
            step_info = StepInfo(name=name)
            phase.steps.append(step_info)
            step_index = len(phase.steps) - 1
        return StepContext(self._tracker, self._phase_index, step_index)

    def parallel_tracker(self) -> TimelineParallelTracker:
        """Create a parallel tracker for this phase."""
        return self._tracker.create_parallel_tracker(self._phase_index)

    def __enter__(self) -> PhaseContext:
        self._tracker.activate_phase(self._phase_index)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        failed = exc_type is not None
        self._tracker.complete_phase(self._phase_index, failed=failed)


# =============================================================================
# TimelineTracker - Main controller
# =============================================================================


class TimelineTracker:
    """Main timeline tracker using Rich.Live for rendering.

    Usage:
        with timeline_progress(["Setup", "Collection", "Report"]) as tl:
            with tl.phase(0) as p:
                with p.step("Collecting options") as s:
                    collect_options(ctx)
                    s.complete("Done")

            with tl.phase(1) as p:
                tracker = p.parallel_tracker()
                parallel_collect(ctx, func, progress_tracker=tracker)

            with tl.phase(2) as p:
                generate_reports(ctx, data)
    """

    def __init__(
        self,
        phases: list[str],
        console: Console | None = None,
    ) -> None:
        self._console = console or default_console
        self._phases: list[PhaseInfo] = [PhaseInfo(name=name) for name in phases]
        self._lock = threading.Lock()
        self._live: Live | None = None
        self._spinner_frame = 0
        self._refresh_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def add_phase(self, name: str) -> int:
        """Add a new phase and return its index."""
        with self._lock:
            phase = PhaseInfo(name=name)
            self._phases.append(phase)
            return len(self._phases) - 1

    def phase(self, index: int) -> PhaseContext:
        """Get a phase context manager."""
        return PhaseContext(self, index)

    def activate_phase(self, index: int) -> None:
        """Mark a phase as active."""
        with self._lock:
            if 0 <= index < len(self._phases):
                phase = self._phases[index]
                phase.state = PhaseState.ACTIVE
                phase.start_time = time.monotonic()
                self._refresh()

    def complete_phase(self, index: int, failed: bool = False) -> None:
        """Mark a phase as completed or failed."""
        with self._lock:
            if 0 <= index < len(self._phases):
                phase = self._phases[index]
                phase.state = PhaseState.FAILED if failed else PhaseState.COMPLETED
                if phase.start_time > 0:
                    phase.elapsed = time.monotonic() - phase.start_time
                self._refresh()

    def set_phase_progress(
        self,
        index: int,
        current: int,
        total: int,
        success: int,
        failed: int,
    ) -> None:
        """Update progress for a phase (thread-safe)."""
        with self._lock:
            if 0 <= index < len(self._phases):
                phase = self._phases[index]
                phase.progress_current = current
                phase.progress_total = total
                phase.progress_success = success
                phase.progress_failed = failed
                self._refresh()

    def create_parallel_tracker(self, phase_index: int) -> TimelineParallelTracker:
        """Create a parallel tracker for a specific phase."""
        return TimelineParallelTracker(self, phase_index)

    def start(self) -> None:
        """Start the Live display and refresh thread."""
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=8,
            transient=False,
        )
        self._live.start()
        self._stop_event.clear()
        self._refresh_thread = threading.Thread(target=self._auto_refresh, daemon=True)
        self._refresh_thread.start()

    def stop(self) -> None:
        """Stop the Live display and refresh thread."""
        self._stop_event.set()
        if self._refresh_thread:
            self._refresh_thread.join(timeout=2)
            self._refresh_thread = None
        if self._live:
            # Final render
            self._live.update(self._render())
            self._live.stop()
            self._live = None

    def _auto_refresh(self) -> None:
        """Background thread that increments spinner and refreshes display."""
        while not self._stop_event.is_set():
            self._spinner_frame += 1
            self._refresh()
            self._stop_event.wait(0.125)  # 8Hz

    def _refresh(self) -> None:
        """Refresh the Live display."""
        if self._live:
            with contextlib.suppress(Exception):
                self._live.update(self._render())

    def _render(self) -> TimelineRenderable:
        """Create a renderable snapshot of the timeline."""
        return TimelineRenderable(self._phases, self._spinner_frame)


# =============================================================================
# Convenience context manager
# =============================================================================


@contextmanager
def timeline_progress(
    phases: list[str],
    console: Console | None = None,
) -> Generator[TimelineTracker, None, None]:
    """Top-level context manager for timeline progress.

    Args:
        phases: List of phase names
        console: Rich Console to use (default: cli.ui.console)

    Yields:
        TimelineTracker instance

    Example:
        with timeline_progress(["Setup", "Collection", "Report"]) as tl:
            with tl.phase(0):
                do_setup()
            with tl.phase(1):
                do_collection()
            with tl.phase(2):
                do_report()
    """
    tracker = TimelineTracker(phases, console=console)
    tracker.start()
    try:
        yield tracker
    finally:
        tracker.stop()
