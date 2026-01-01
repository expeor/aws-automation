"""
core/tools/output - 출력 관리 모듈

OutputPath: 프로파일/계정별 출력 경로를 체계적으로 생성
renderers: 다양한 출력 형식 지원 (Console, Excel, HTML, JSON)
"""

from .builder import (
    DatePattern,
    OutputPath,
    OutputResult,
    create_report_directory,
    open_file,
    open_in_explorer,
    single_report_directory,
)

# 레거시 호환 별칭
open_file_explorer = open_in_explorer

__all__ = [
    # Path builder
    "OutputPath",
    "OutputResult",
    "DatePattern",
    "create_report_directory",
    "single_report_directory",
    "open_in_explorer",
    "open_file_explorer",  # 레거시 호환
    "open_file",
]
