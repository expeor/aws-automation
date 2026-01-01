# core/tools/io - 파일 입출력 모듈
"""
파일 입출력 유틸리티

구조:
    core/tools/io/csv/    - CSV 파일 읽기 (인코딩 감지)
    core/tools/io/excel/  - Excel 파일 쓰기 (결과 출력)
    core/tools/io/file/   - 기본 파일 I/O

사용 예시:
    from core.tools.io.csv import read_csv_robust
    from core.tools.io.excel import Workbook, ColumnDef
    from core.tools.io.file import ensure_dir
    from core.tools.output import open_in_explorer, open_file
"""

from core.tools.io import csv, excel, file

__all__ = [
    "csv",
    "excel",
    "file",
]
