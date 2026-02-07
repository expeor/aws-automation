"""
tests/shared/io/excel/test_styles.py - Excel 스타일 테스트
"""


class TestStyles:
    """Styles 클래스 테스트"""

    def test_danger_style(self):
        """danger 스타일이 올바른 fill과 font를 반환"""
        from shared.io.excel.styles import Styles

        style = Styles.danger()
        assert "fill" in style
        assert "font" in style

    def test_warning_style(self):
        """warning 스타일이 올바른 fill과 font를 반환"""
        from shared.io.excel.styles import Styles

        style = Styles.warning()
        assert "fill" in style
        assert "font" in style

    def test_success_style(self):
        """success 스타일이 올바른 fill과 font를 반환"""
        from shared.io.excel.styles import Styles

        style = Styles.success()
        assert "fill" in style
        assert "font" in style

    def test_info_style(self):
        """info 스타일이 올바른 fill과 font를 반환"""
        from shared.io.excel.styles import Styles

        style = Styles.info()
        assert "fill" in style
        assert "font" in style

    def test_summary_style(self):
        """summary 스타일이 올바른 fill과 font를 반환"""
        from shared.io.excel.styles import Styles

        style = Styles.summary()
        assert "fill" in style
        assert "font" in style

    def test_data_style(self):
        """data 스타일이 올바른 font를 반환"""
        from shared.io.excel.styles import Styles

        style = Styles.data()
        assert "font" in style

    def test_abuse_style(self):
        """abuse 스타일이 올바른 fill과 font를 반환"""
        from shared.io.excel.styles import Styles

        style = Styles.abuse()
        assert "fill" in style
        assert "font" in style

    def test_error_style(self):
        """error 스타일이 올바른 fill과 font를 반환"""
        from shared.io.excel.styles import Styles

        style = Styles.error()
        assert "fill" in style
        assert "font" in style


class TestRowStyle:
    """RowStyle 클래스 테스트"""

    def test_data_style(self):
        """data 행 스타일"""
        from shared.io.excel.styles import RowStyle

        style = RowStyle.data()
        assert "font" in style
        assert style["fill"] is None

    def test_warning_style(self):
        """warning 행 스타일"""
        from shared.io.excel.styles import RowStyle

        style = RowStyle.warning()
        assert "fill" in style
        assert style["fill"] is not None

    def test_danger_style(self):
        """danger 행 스타일"""
        from shared.io.excel.styles import RowStyle

        style = RowStyle.danger()
        assert style["fill"] is not None

    def test_success_style(self):
        """success 행 스타일"""
        from shared.io.excel.styles import RowStyle

        style = RowStyle.success()
        assert style["fill"] is not None

    def test_summary_style(self):
        """summary 행 스타일"""
        from shared.io.excel.styles import RowStyle

        style = RowStyle.summary()
        assert style["fill"] is not None
        assert style["font"] is not None


class TestStyleFunctions:
    """스타일 유틸리티 함수 테스트"""

    def test_get_header_font(self):
        """헤더 폰트가 올바르게 생성됨"""
        from shared.io.excel.styles import get_header_font

        font = get_header_font()
        assert font.bold is True
        assert font.size == 10

    def test_get_data_font(self):
        """데이터 폰트가 올바르게 생성됨"""
        from shared.io.excel.styles import get_data_font

        font = get_data_font()
        assert font.size == 10

    def test_get_summary_font(self):
        """요약 폰트가 올바르게 생성됨"""
        from shared.io.excel.styles import get_summary_font

        font = get_summary_font()
        assert font.bold is True

    def test_get_header_fill(self):
        """헤더 채우기가 올바르게 생성됨"""
        from shared.io.excel.styles import get_header_fill

        fill = get_header_fill()
        assert fill.fill_type == "solid"

    def test_get_summary_fill(self):
        """요약 채우기가 올바르게 생성됨"""
        from shared.io.excel.styles import get_summary_fill

        fill = get_summary_fill()
        assert fill.fill_type == "solid"

    def test_get_success_fill(self):
        """성공 채우기가 올바르게 생성됨"""
        from shared.io.excel.styles import get_success_fill

        fill = get_success_fill()
        assert fill.fill_type == "solid"

    def test_get_warning_fill(self):
        """경고 채우기가 올바르게 생성됨"""
        from shared.io.excel.styles import get_warning_fill

        fill = get_warning_fill()
        assert fill.fill_type == "solid"

    def test_get_danger_fill(self):
        """위험 채우기가 올바르게 생성됨"""
        from shared.io.excel.styles import get_danger_fill

        fill = get_danger_fill()
        assert fill.fill_type == "solid"

    def test_get_abuse_fill(self):
        """악성 채우기가 올바르게 생성됨"""
        from shared.io.excel.styles import get_abuse_fill

        fill = get_abuse_fill()
        assert fill.fill_type == "solid"

    def test_get_error_fill(self):
        """에러 채우기가 올바르게 생성됨"""
        from shared.io.excel.styles import get_error_fill

        fill = get_error_fill()
        assert fill.fill_type == "solid"

    def test_get_info_fill(self):
        """정보 채우기가 올바르게 생성됨"""
        from shared.io.excel.styles import get_info_fill

        fill = get_info_fill()
        assert fill.fill_type == "solid"

    def test_get_thin_border(self):
        """얇은 테두리가 올바르게 생성됨"""
        from shared.io.excel.styles import get_thin_border

        border = get_thin_border()
        assert border.left is not None
        assert border.right is not None
        assert border.top is not None
        assert border.bottom is not None

    def test_get_center_alignment_default(self):
        """중앙 정렬이 기본값으로 생성됨"""
        from shared.io.excel.styles import get_center_alignment

        align = get_center_alignment()
        assert align.horizontal == "center"
        assert align.vertical == "center"

    def test_get_center_alignment_with_wrap(self):
        """중앙 정렬이 줄바꿈 옵션과 함께 생성됨"""
        from shared.io.excel.styles import get_center_alignment

        align = get_center_alignment(wrap_text=True)
        assert align.wrap_text is True

    def test_get_center_alignment_without_wrap(self):
        """중앙 정렬이 줄바꿈 없이 생성됨"""
        from shared.io.excel.styles import get_center_alignment

        align = get_center_alignment(wrap_text=False)
        assert align.wrap_text is False

    def test_get_basic_header_style(self):
        """기본 헤더 스타일이 모든 요소를 포함"""
        from shared.io.excel.styles import get_basic_header_style

        style = get_basic_header_style()
        assert "font" in style
        assert "fill" in style
        assert "alignment" in style
        assert "border" in style

    def test_get_header_style(self):
        """헤더 스타일이 모든 요소를 포함"""
        from shared.io.excel.styles import get_header_style

        style = get_header_style()
        assert "font" in style
        assert "fill" in style
        assert "alignment" in style
        assert "border" in style

    def test_get_center_header_style(self):
        """중앙 정렬 헤더 스타일"""
        from shared.io.excel.styles import get_center_header_style

        style = get_center_header_style()
        assert "font" in style
        assert "fill" in style

    def test_get_data_cell_style(self):
        """데이터 셀 스타일"""
        from shared.io.excel.styles import get_data_cell_style

        style = get_data_cell_style()
        assert "font" in style
        assert "alignment" in style

    def test_get_summary_cell_style(self):
        """요약 셀 스타일"""
        from shared.io.excel.styles import get_summary_cell_style

        style = get_summary_cell_style()
        assert "font" in style


class TestStatusStyles:
    """상태 스타일 함수 테스트"""

    def test_create_status_style_success(self):
        """성공 상태 스타일"""
        from shared.io.excel.styles import create_status_style

        style = create_status_style("success")
        assert "fill" in style
        assert "font" in style

    def test_create_status_style_failed(self):
        """실패 상태 스타일"""
        from shared.io.excel.styles import create_status_style

        style = create_status_style("failed")
        assert "fill" in style

    def test_create_status_style_warning(self):
        """경고 상태 스타일"""
        from shared.io.excel.styles import create_status_style

        style = create_status_style("warning")
        assert "fill" in style

    def test_create_status_style_info(self):
        """정보 상태 스타일"""
        from shared.io.excel.styles import create_status_style

        style = create_status_style("info")
        assert "fill" in style

    def test_create_status_style_unknown(self):
        """알 수 없는 상태 - 기본 스타일"""
        from shared.io.excel.styles import create_status_style

        style = create_status_style("unknown_status")
        assert "fill" in style


class TestNumberFormats:
    """숫자 포맷 상수 테스트"""

    def test_number_format_integer(self):
        """정수 포맷이 정의됨"""
        from shared.io.excel.styles import NUMBER_FORMAT_INTEGER

        assert NUMBER_FORMAT_INTEGER is not None
        assert "#,##0" in NUMBER_FORMAT_INTEGER

    def test_number_format_decimal(self):
        """소수점 포맷이 정의됨"""
        from shared.io.excel.styles import NUMBER_FORMAT_DECIMAL

        assert NUMBER_FORMAT_DECIMAL is not None
        assert "." in NUMBER_FORMAT_DECIMAL

    def test_number_format_currency(self):
        """통화 포맷이 정의됨"""
        from shared.io.excel.styles import NUMBER_FORMAT_CURRENCY

        assert NUMBER_FORMAT_CURRENCY is not None

    def test_number_format_percent(self):
        """퍼센트 포맷이 정의됨"""
        from shared.io.excel.styles import NUMBER_FORMAT_PERCENT

        assert NUMBER_FORMAT_PERCENT is not None
        assert "%" in NUMBER_FORMAT_PERCENT

    def test_number_format_date(self):
        """날짜 포맷이 정의됨"""
        from shared.io.excel.styles import NUMBER_FORMAT_DATE

        assert NUMBER_FORMAT_DATE is not None

    def test_number_format_datetime(self):
        """날짜시간 포맷이 정의됨"""
        from shared.io.excel.styles import NUMBER_FORMAT_DATETIME

        assert NUMBER_FORMAT_DATETIME is not None

    def test_number_format_text(self):
        """텍스트 포맷이 정의됨"""
        from shared.io.excel.styles import NUMBER_FORMAT_TEXT

        assert NUMBER_FORMAT_TEXT == "@"

    def test_number_format_status(self):
        """상태 포맷이 정의됨"""
        from shared.io.excel.styles import NUMBER_FORMAT_STATUS

        assert NUMBER_FORMAT_STATUS is not None


class TestAlignmentConstants:
    """정렬 상수 테스트"""

    def test_align_center(self):
        """중앙 정렬 상수가 정의됨"""
        from shared.io.excel.styles import ALIGN_CENTER

        assert ALIGN_CENTER.horizontal == "center"
        assert ALIGN_CENTER.vertical == "center"

    def test_align_left(self):
        """왼쪽 정렬 상수가 정의됨"""
        from shared.io.excel.styles import ALIGN_LEFT

        assert ALIGN_LEFT.horizontal == "left"

    def test_align_right(self):
        """오른쪽 정렬 상수가 정의됨"""
        from shared.io.excel.styles import ALIGN_RIGHT

        assert ALIGN_RIGHT.horizontal == "right"

    def test_align_wrap(self):
        """줄바꿈 정렬 상수가 정의됨"""
        from shared.io.excel.styles import ALIGN_WRAP

        assert ALIGN_WRAP.wrap_text is True

    def test_align_left_wrap(self):
        """왼쪽 줄바꿈 정렬 상수가 정의됨"""
        from shared.io.excel.styles import ALIGN_LEFT_WRAP

        assert ALIGN_LEFT_WRAP.horizontal == "left"
        assert ALIGN_LEFT_WRAP.wrap_text is True

    def test_align_center_wrap(self):
        """중앙 줄바꿈 정렬 상수가 정의됨"""
        from shared.io.excel.styles import ALIGN_CENTER_WRAP

        assert ALIGN_CENTER_WRAP.horizontal == "center"
        assert ALIGN_CENTER_WRAP.wrap_text is True

    def test_align_right_wrap(self):
        """오른쪽 줄바꿈 정렬 상수가 정의됨"""
        from shared.io.excel.styles import ALIGN_RIGHT_WRAP

        assert ALIGN_RIGHT_WRAP.horizontal == "right"
        assert ALIGN_RIGHT_WRAP.wrap_text is True


class TestColorConstants:
    """색상 상수 테스트"""

    def test_color_header_bg(self):
        """헤더 배경 색상"""
        from shared.io.excel.styles import COLOR_HEADER_BG

        assert COLOR_HEADER_BG is not None
        assert len(COLOR_HEADER_BG) == 6

    def test_color_header_fg(self):
        """헤더 글자 색상"""
        from shared.io.excel.styles import COLOR_HEADER_FG

        assert COLOR_HEADER_FG is not None

    def test_color_success(self):
        """성공 색상"""
        from shared.io.excel.styles import COLOR_SUCCESS

        assert COLOR_SUCCESS is not None

    def test_color_warning(self):
        """경고 색상"""
        from shared.io.excel.styles import COLOR_WARNING

        assert COLOR_WARNING is not None

    def test_color_danger(self):
        """위험 색상"""
        from shared.io.excel.styles import COLOR_DANGER

        assert COLOR_DANGER is not None
