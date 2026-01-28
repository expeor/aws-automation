"""DEPRECATED: Use shared.io.output instead.

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드에서는 shared.io.output을 사용하세요.
"""

import warnings

from shared.io.output import (
    REPORT_TYPE_DESCRIPTIONS,
    TOOL_CATEGORIES,
    TOOL_TYPE_DESCRIPTIONS,
    DatePattern,
    OutputPath,
    OutputResult,
    ReportType,
    ToolType,
    create_report_directory,
    get_all_types,
    get_report_types,
    get_tool_types,
    is_report_type,
    is_tool_type,
    is_valid_type,
    open_file,
    open_in_explorer,
    print_report_complete,
    single_report_directory,
)

warnings.warn(
    "core.tools.output is deprecated. Use shared.io.output instead.",
    DeprecationWarning,
    stacklevel=2,
)

# 레거시 호환 별칭
open_file_explorer = open_in_explorer

__all__: list[str] = [
    # Path builder
    "OutputPath",
    "OutputResult",
    "DatePattern",
    "create_report_directory",
    "single_report_directory",
    "open_in_explorer",
    "open_file_explorer",  # 레거시 호환
    "open_file",
    "print_report_complete",
    # Report types
    "ReportType",
    "ToolType",
    "REPORT_TYPE_DESCRIPTIONS",
    "TOOL_TYPE_DESCRIPTIONS",
    "TOOL_CATEGORIES",
    "get_all_types",
    "get_report_types",
    "get_tool_types",
    "is_valid_type",
    "is_report_type",
    "is_tool_type",
]
