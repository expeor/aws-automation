# pkg/io/excel - Excel 출력 양식 (공통 스타일, 헬퍼)
"""
Excel 스타일 및 Workbook 유틸리티.

사용 예시:
    from core.tools.io.excel import Workbook, ColumnDef, Styles

    wb = Workbook()
    columns = [
        ColumnDef(header="ID", width=20, style="data"),
        ColumnDef(header="크기", width=10, style="number"),
        ColumnDef(header="상태", width=12, style="center"),
    ]

    sheet = wb.new_sheet(name="결과", columns=columns)
    sheet.add_row(["vol-123", 100, "available"])
    sheet.add_row(["vol-456", 50, "in-use"], style=Styles.warning())
    sheet.add_summary_row(["합계", 150, "-"])

    wb.save_as(output_dir, "report", "ap-northeast-2")

Note:
    이 모듈은 Lazy Import 패턴을 사용합니다.
    openpyxl 등 무거운 의존성을 실제 사용 시점에만 로드합니다.
"""

__all__ = [
    # 핵심 클래스
    "Workbook",
    "ColumnDef",
    "Sheet",
    "SummarySheet",
    "SummaryItem",
    "Styles",
    "RowStyle",
    # 색상 상수
    "COLOR_HEADER_BG",
    "COLOR_HEADER_FG",
    "COLOR_SUMMARY_BG",
    "COLOR_SUCCESS",
    "COLOR_SUCCESS_FG",
    "COLOR_WARNING",
    "COLOR_WARNING_FG",
    "COLOR_DANGER",
    "COLOR_DANGER_FG",
    "COLOR_ABUSE",
    "COLOR_ERROR",
    "COLOR_INFO",
    "COLOR_DATA_BG",
    "COLOR_ALT_ROW_BG",
    # 숫자 포맷
    "NUMBER_FORMAT_INTEGER",
    "NUMBER_FORMAT_DECIMAL",
    "NUMBER_FORMAT_CURRENCY",
    "NUMBER_FORMAT_PERCENT",
    "NUMBER_FORMAT_DATE",
    "NUMBER_FORMAT_DATETIME",
    "NUMBER_FORMAT_TEXT",
    "NUMBER_FORMAT_STATUS",
    "FMT_COUNT",
    "FMT_STATUS",
    "FMT_TEXT",
    # 정렬
    "ALIGN_LEFT",
    "ALIGN_CENTER",
    "ALIGN_RIGHT",
    "ALIGN_WRAP",
    "ALIGN_LEFT_WRAP",
    "ALIGN_CENTER_WRAP",
    "ALIGN_RIGHT_WRAP",
    # Fill 인스턴스
    "FILL_ABUSE",
    "FILL_WARN",
    "FILL_ERROR",
    "FILL_INFO",
    "FILL_SUCCESS",
    "FILL_DANGER",
    # 스타일 함수
    "get_thin_border",
    "get_header_font",
    "get_data_font",
    "get_summary_font",
    "get_header_fill",
    "get_summary_fill",
    "get_success_fill",
    "get_warning_fill",
    "get_danger_fill",
    "get_abuse_fill",
    "get_error_fill",
    "get_info_fill",
    "get_header_style",
    "get_basic_header_style",
    "get_center_header_style",
    "get_data_cell_style",
    "get_summary_cell_style",
    "get_center_alignment",
    "create_status_style",
    "create_summary_cell_style",
    "create_summary_dashboard_style",
    "create_summary_value_style",
    # 워크시트 포맷팅
    "calculate_optimal_column_width",
    "calculate_optimal_row_height",
    "apply_detail_sheet_formatting",
    "apply_summary_formatting",
    "apply_worksheet_settings",
    "save_to_csv",
    "save_dict_list_to_excel",
    "add_sheet_from_dict_list",
]

# styles.py 에서 가져올 항목들
_STYLES_ATTRS = {
    # 색상 상수
    "COLOR_HEADER_BG",
    "COLOR_HEADER_FG",
    "COLOR_SUMMARY_BG",
    "COLOR_SUCCESS",
    "COLOR_SUCCESS_FG",
    "COLOR_WARNING",
    "COLOR_WARNING_FG",
    "COLOR_DANGER",
    "COLOR_DANGER_FG",
    "COLOR_ABUSE",
    "COLOR_ERROR",
    "COLOR_INFO",
    "COLOR_DATA_BG",
    "COLOR_ALT_ROW_BG",
    # 숫자 포맷
    "NUMBER_FORMAT_INTEGER",
    "NUMBER_FORMAT_DECIMAL",
    "NUMBER_FORMAT_CURRENCY",
    "NUMBER_FORMAT_PERCENT",
    "NUMBER_FORMAT_DATE",
    "NUMBER_FORMAT_DATETIME",
    "NUMBER_FORMAT_TEXT",
    "NUMBER_FORMAT_STATUS",
    "FMT_COUNT",
    "FMT_STATUS",
    "FMT_TEXT",
    # 정렬
    "ALIGN_LEFT",
    "ALIGN_CENTER",
    "ALIGN_RIGHT",
    "ALIGN_WRAP",
    "ALIGN_LEFT_WRAP",
    "ALIGN_CENTER_WRAP",
    "ALIGN_RIGHT_WRAP",
    # Fill 인스턴스
    "FILL_ABUSE",
    "FILL_WARN",
    "FILL_ERROR",
    "FILL_INFO",
    "FILL_SUCCESS",
    "FILL_DANGER",
    # 스타일 클래스
    "Styles",
    "RowStyle",
    # 스타일 함수
    "get_thin_border",
    "get_header_font",
    "get_data_font",
    "get_summary_font",
    "get_header_fill",
    "get_summary_fill",
    "get_success_fill",
    "get_warning_fill",
    "get_danger_fill",
    "get_abuse_fill",
    "get_error_fill",
    "get_info_fill",
    "get_header_style",
    "get_basic_header_style",
    "get_center_header_style",
    "get_data_cell_style",
    "get_summary_cell_style",
    "get_center_alignment",
    "create_status_style",
    "create_summary_cell_style",
    "create_summary_dashboard_style",
    "create_summary_value_style",
}

# workbook.py 에서 가져올 항목들
_WORKBOOK_ATTRS = {
    "Workbook",
    "ColumnDef",
    "Sheet",
    "SummarySheet",
    "SummaryItem",
    "calculate_optimal_column_width",
    "calculate_optimal_row_height",
    "apply_detail_sheet_formatting",
    "apply_summary_formatting",
    "apply_worksheet_settings",
    "save_to_csv",
    "save_dict_list_to_excel",
    "add_sheet_from_dict_list",
}


def __getattr__(name: str):
    """Lazy import - 실제 사용 시점에만 모듈 로드"""
    if name in _STYLES_ATTRS:
        from . import styles

        return getattr(styles, name)

    if name in _WORKBOOK_ATTRS:
        from . import workbook

        return getattr(workbook, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
