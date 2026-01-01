# core/tools/io - 파일 입출력 모듈
"""
파일 입출력 유틸리티

구조:
    core/tools/io/csv/    - CSV 파일 읽기 (인코딩 감지)
    core/tools/io/excel/  - Excel 파일 쓰기 (결과 출력)
    core/tools/io/file/   - 기본 파일 I/O

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
    탐색기 열기(open_in_explorer, open_file)는 core.tools.output으로 이동됨.

사용 예시:
    from core.tools.io.csv import read_csv_robust
    from core.tools.io.excel import Workbook, ColumnDef
    from core.tools.io.file import ensure_dir
    from core.tools.output import open_in_explorer, open_file
"""

__all__ = [
    # csv 모듈
    "csv",
    # excel 모듈
    "excel",
    # file 모듈
    "file",
]


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name == "csv":
        from core.tools.io import csv

        return csv

    if name == "excel":
        from core.tools.io import excel

        return excel

    if name == "file":
        from core.tools.io import file

        return file

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
