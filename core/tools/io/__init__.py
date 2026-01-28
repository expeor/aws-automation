"""DEPRECATED: Use shared.io instead.

이 모듈은 하위 호환성을 위해 유지됩니다.
새 코드에서는 shared.io를 사용하세요.

Migration:
    # Before
    from core.tools.io.csv import read_csv_robust
    from core.tools.io.excel import Workbook, ColumnDef
    from core.tools.io.html import AWSReport, create_aws_report
    from core.tools.io.config import OutputConfig, OutputFormat
    from core.tools.io.compat import generate_reports

    # After
    from shared.io.csv import read_csv_robust
    from shared.io.excel import Workbook, ColumnDef
    from shared.io.html import AWSReport, create_aws_report
    from shared.io.config import OutputConfig, OutputFormat
    from shared.io.compat import generate_reports
"""

import warnings

# Re-export submodules from shared.io
from shared.io import csv, excel, file, html
from shared.io.compat import generate_dual_report, generate_reports
from shared.io.config import OutputConfig, OutputFormat

warnings.warn(
    "core.tools.io is deprecated. Use shared.io instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__: list[str] = [
    "csv",
    "excel",
    "html",
    "file",
    "OutputConfig",
    "OutputFormat",
    "generate_reports",
    "generate_dual_report",
]
