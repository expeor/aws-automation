"""입출력 유틸리티.

하위 모듈:
- excel: Excel 파일 출력 (openpyxl 기반)
- html: HTML 보고서 생성 (ECharts 시각화)
- csv: CSV 파일 처리 (인코딩 자동 감지)
- file: 기본 파일 I/O 유틸리티
- output: 출력 경로 관리 및 빌더
- config: 출력 설정 (OutputConfig, OutputFormat)
- compat: 호환성 헬퍼 (generate_reports, generate_dual_report)
"""

from . import csv, excel, file, html, output
from .compat import generate_dual_report, generate_reports
from .config import OutputConfig, OutputFormat

__all__: list[str] = [
    # 하위 모듈
    "excel",
    "html",
    "csv",
    "file",
    "output",
    # 설정
    "OutputConfig",
    "OutputFormat",
    # 고수준 API
    "generate_reports",
    "generate_dual_report",
]
