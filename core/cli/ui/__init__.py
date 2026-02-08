# cli/ui - TUI 컴포넌트 (questionary, rich)
"""
TUI 컴포넌트 모듈

CLI 전용 UI 컴포넌트들 (대화형 선택, 콘솔 출력 등)
"""

# Direct imports (rich/questionary are commonly used, no lazy import needed)
from .banner import print_banner, print_simple_banner
from .console import (  # 섹션 박스 UI; Rich 유틸리티
    BOX_STYLE,
    BOX_WIDTH,
    INDENT,
    SYMBOL_ERROR,
    SYMBOL_INFO,
    SYMBOL_PROGRESS,
    SYMBOL_SUCCESS,
    SYMBOL_WARNING,
    console,
    get_console,
    get_logger,
    get_progress,
    logger,
    print_box_end,
    print_box_line,
    print_box_start,
    print_error,
    print_error_tree,
    print_execution_summary,
    print_header,
    print_info,
    print_legend,
    print_panel_header,
    print_result_tree,
    print_results_json,
    print_rule,
    print_section_box,
    print_stat_columns,
    print_step,
    print_step_header,
    print_sub_error,
    print_sub_info,
    print_sub_task,
    print_sub_task_done,
    print_sub_warning,
    print_success,
    print_table,
    print_warning,
)
from .main_menu import MainMenu, show_main_menu
from .progress import (  # Progress tracking components
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
from .search import (
    SearchResult,
    ToolSearchEngine,
    get_search_engine,
    init_search_engine,
)
from .timeline import (
    TimelineParallelTracker,
    TimelineTracker,
    timeline_progress,
)

__all__: list[str] = [
    "MainMenu",
    "show_main_menu",
    "print_banner",
    "print_simple_banner",
    "console",
    "logger",
    "get_console",
    "get_progress",
    "get_logger",
    # 표준 출력 심볼
    "SYMBOL_SUCCESS",
    "SYMBOL_ERROR",
    "SYMBOL_WARNING",
    "SYMBOL_INFO",
    "SYMBOL_PROGRESS",
    # 메시지 출력
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "print_header",
    "print_step",
    "print_step_header",
    "print_sub_task",
    "print_sub_task_done",
    "print_sub_info",
    "print_sub_warning",
    "print_sub_error",
    "INDENT",
    "print_panel_header",
    "print_table",
    "print_legend",
    # 섹션 박스 UI
    "BOX_STYLE",
    "BOX_WIDTH",
    "print_section_box",
    "print_box_line",
    "print_box_end",
    "print_box_start",
    # 검색 엔진
    "ToolSearchEngine",
    "SearchResult",
    "get_search_engine",
    "init_search_engine",
    # Progress tracking
    "BaseTracker",
    "ParallelTracker",
    "StepTracker",
    "DownloadTracker",
    "StatusTracker",
    "parallel_progress",
    "step_progress",
    "download_progress",
    "indeterminate_progress",
    # Timeline
    "TimelineTracker",
    "TimelineParallelTracker",
    "timeline_progress",
    # Rich utilities
    "print_rule",
    "print_result_tree",
    "print_error_tree",
    "print_stat_columns",
    "print_execution_summary",
    "print_results_json",
]
