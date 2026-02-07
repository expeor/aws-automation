"""
shared/io/output - 출력 관리 모듈

OutputPath: 프로파일/계정별 출력 경로를 체계적으로 생성
renderers: 다양한 출력 형식 지원 (Console, Excel, HTML, JSON)

경로 구조: output/{profile}/{service}/{type}/{date}/
타입 체계:
  - Reports: inventory, security, cost, unused, audit,
             compliance, performance, network, backup, quota
  - Tools: log, search, cleanup, tag, sync
"""

from .builder import (
    DatePattern,
    OutputPath,
    OutputResult,
    create_report_directory,
    open_file,
    open_in_explorer,
    print_report_complete,
    single_report_directory,
)
from .helpers import create_output_path, get_context_identifier
from .report_types import (
    REPORT_TYPE_DESCRIPTIONS,
    TOOL_CATEGORIES,
    TOOL_TYPE_DESCRIPTIONS,
    ReportType,
    ToolType,
    get_all_types,
    get_report_types,
    get_tool_types,
    is_report_type,
    is_tool_type,
    is_valid_type,
)

# 레거시 호환 별칭
open_file_explorer = open_in_explorer

__all__: list[str] = [
    # Path builder
    "OutputPath",
    "OutputResult",
    "DatePattern",
    "get_context_identifier",
    "create_output_path",
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
