# core/tools/io - 파일 입출력 모듈
"""
파일 입출력 유틸리티

구조:
    core/tools/io/csv/    - CSV 파일 읽기 (인코딩 감지)
    core/tools/io/excel/  - Excel 파일 쓰기 (결과 출력)
    core/tools/io/html/   - HTML 리포트 생성 (시각화)
    core/tools/io/file/   - 기본 파일 I/O
    core/tools/io/config.py - 출력 설정 (OutputFormat, OutputConfig)
    core/tools/io/compat.py - 호환성 헬퍼 (generate_reports)

사용 예시:
    from core.tools.io.csv import read_csv_robust
    from core.tools.io.excel import Workbook, ColumnDef
    from core.tools.io.html import AWSReport, create_aws_report
    from core.tools.io.file import ensure_dir
    from core.tools.io.config import OutputConfig, OutputFormat
    from core.tools.io.compat import generate_reports
    from core.tools.output import open_in_explorer, open_file
"""

from core.tools.io import csv, excel, file, html
from core.tools.io.compat import generate_dual_report, generate_reports
from core.tools.io.config import OutputConfig, OutputFormat

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
