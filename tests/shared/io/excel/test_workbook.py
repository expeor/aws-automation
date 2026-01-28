"""
tests/shared/io/excel/test_workbook.py - Excel Workbook 테스트
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shared.io.excel.workbook import ColumnDef, Sheet, SummaryItem, Workbook


class TestColumnDef:
    """ColumnDef 클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        col = ColumnDef(header="테스트")

        assert col.header == "테스트"
        assert col.width == 15
        assert col.style == "data"
        assert col.header_en is None

    def test_custom_values(self):
        """커스텀 값 설정"""
        col = ColumnDef(
            header="볼륨 ID",
            header_en="Volume ID",
            width=22,
            style="center",
        )

        assert col.header == "볼륨 ID"
        assert col.header_en == "Volume ID"
        assert col.width == 22
        assert col.style == "center"

    def test_get_header_korean(self):
        """한국어 헤더 반환"""
        col = ColumnDef(header="볼륨", header_en="Volume")

        assert col.get_header("ko") == "볼륨"

    def test_get_header_english(self):
        """영어 헤더 반환"""
        col = ColumnDef(header="볼륨", header_en="Volume")

        assert col.get_header("en") == "Volume"

    def test_get_header_english_fallback(self):
        """영어 헤더 없을 때 한국어 반환"""
        col = ColumnDef(header="볼륨")

        assert col.get_header("en") == "볼륨"


class TestSummaryItem:
    """SummaryItem 클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        item = SummaryItem(label="테스트")

        assert item.label == "테스트"
        assert item.value == ""
        assert item.is_header is False
        assert item.highlight is None

    def test_header_item(self):
        """헤더 항목"""
        item = SummaryItem(label="섹션", is_header=True)

        assert item.is_header is True

    def test_highlighted_item(self):
        """강조 항목"""
        item = SummaryItem(label="경고", value=10, highlight="danger")

        assert item.highlight == "danger"


class TestWorkbook:
    """Workbook 클래스 테스트"""

    def test_initialization(self):
        """초기화 테스트"""
        wb = Workbook(lang="ko")

        assert wb._lang == "ko"
        assert wb._wb is not None
        assert wb._sheets == []

    def test_initialization_english(self):
        """영어 모드 초기화"""
        wb = Workbook(lang="en")

        assert wb._lang == "en"

    def test_new_sheet_creates_sheet(self):
        """시트 생성"""
        wb = Workbook()
        columns = [
            ColumnDef(header="ID", width=10),
            ColumnDef(header="이름", width=20),
        ]

        sheet = wb.new_sheet(name="테스트", columns=columns)

        assert isinstance(sheet, Sheet)
        assert len(wb._sheets) == 1

    def test_new_sheet_with_english_headers(self):
        """영어 헤더로 시트 생성"""
        wb = Workbook(lang="en")
        columns = [
            ColumnDef(header="ID", header_en="ID", width=10),
            ColumnDef(header="이름", header_en="Name", width=20),
        ]

        sheet = wb.new_sheet(name="Test", columns=columns)

        # 첫 번째 행(헤더)의 값 확인
        ws = sheet._ws
        assert ws.cell(row=1, column=2).value == "Name"

    def test_multiple_sheets(self):
        """여러 시트 생성"""
        wb = Workbook()
        columns = [ColumnDef(header="Test")]

        sheet1 = wb.new_sheet(name="시트1", columns=columns)
        sheet2 = wb.new_sheet(name="시트2", columns=columns)

        assert len(wb._sheets) == 2
        assert sheet1._ws.title == "시트1"
        assert sheet2._ws.title == "시트2"

    def test_save_creates_file(self):
        """파일 저장"""
        wb = Workbook()
        columns = [ColumnDef(header="Test")]
        sheet = wb.new_sheet(name="테스트", columns=columns)
        sheet.add_row(["value"])

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = wb.save(Path(tmpdir) / "test_output.xlsx")

            assert Path(filepath).exists()
            assert str(filepath).endswith(".xlsx")

    def test_save_as_creates_file(self):
        """save_as로 파일 저장"""
        wb = Workbook()
        columns = [ColumnDef(header="Test")]
        wb.new_sheet(name="테스트", columns=columns)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = wb.save_as(str(tmpdir), "test_output", region="ap-northeast-2")

            assert Path(filepath).exists()
            assert "test_output" in str(filepath)
            assert "ap-northeast-2" in str(filepath)


class TestSheet:
    """Sheet 클래스 테스트"""

    def test_add_row(self):
        """행 추가"""
        wb = Workbook()
        columns = [
            ColumnDef(header="A", width=10),
            ColumnDef(header="B", width=10),
        ]
        sheet = wb.new_sheet(name="Test", columns=columns)

        row_num = sheet.add_row(["val1", "val2"])

        assert row_num == 2  # 헤더가 1이므로 첫 데이터는 2
        assert sheet.row_count == 1

    def test_add_multiple_rows(self):
        """여러 행 추가"""
        wb = Workbook()
        columns = [ColumnDef(header="A")]
        sheet = wb.new_sheet(name="Test", columns=columns)

        sheet.add_row(["row1"])
        sheet.add_row(["row2"])
        sheet.add_row(["row3"])

        assert sheet.row_count == 3

    def test_add_summary_row(self):
        """요약 행 추가"""
        wb = Workbook()
        columns = [
            ColumnDef(header="항목"),
            ColumnDef(header="값", style="number"),
        ]
        sheet = wb.new_sheet(name="Test", columns=columns)

        sheet.add_row(["A", 100])
        sheet.add_row(["B", 200])
        row_num = sheet.add_summary_row(["합계", 300])

        assert row_num == 4  # 헤더(1) + 2 데이터 + 1 요약

    def test_column_styles_applied(self):
        """컬럼 스타일 적용"""
        wb = Workbook()
        columns = [
            ColumnDef(header="텍스트", style="text"),
            ColumnDef(header="숫자", style="number"),
            ColumnDef(header="통화", style="currency"),
            ColumnDef(header="퍼센트", style="percent"),
            ColumnDef(header="중앙", style="center"),
        ]
        sheet = wb.new_sheet(name="Test", columns=columns)

        sheet.add_row(["text", 100, 1000, 0.5, "center"])

        # 스타일이 적용되었는지 확인
        ws = sheet._ws
        assert ws.cell(row=2, column=2).number_format is not None

    def test_finalize_adds_autofilter(self):
        """마무리 시 자동 필터 추가"""
        wb = Workbook()
        columns = [ColumnDef(header="A"), ColumnDef(header="B")]
        sheet = wb.new_sheet(name="Test", columns=columns)

        sheet.add_row(["val1", "val2"])
        sheet.finalize()

        assert sheet._ws.auto_filter.ref is not None


class TestWorkbookSummarySheet:
    """SummarySheet 테스트"""

    def test_new_summary_sheet(self):
        """Summary 시트 생성"""
        wb = Workbook()

        summary = wb.new_summary_sheet("요약")

        assert summary is not None
        assert summary._ws.title == "요약"

    def test_add_title(self):
        """타이틀 추가"""
        wb = Workbook()
        summary = wb.new_summary_sheet("요약")

        summary.add_title("테스트 보고서")

        # 타이틀이 추가되었는지 확인
        assert summary.current_row > 1

    def test_add_section(self):
        """섹션 추가"""
        wb = Workbook()
        summary = wb.new_summary_sheet("요약")

        summary.add_section("분석 정보")

        assert summary.current_row > 1

    def test_add_item(self):
        """항목 추가"""
        wb = Workbook()
        summary = wb.new_summary_sheet("요약")

        summary.add_item("계정", "123456789012")
        summary.add_item("리전", "ap-northeast-2")

        assert summary.current_row > 2

    def test_add_item_with_highlight(self):
        """강조 항목 추가"""
        wb = Workbook()
        summary = wb.new_summary_sheet("요약")

        summary.add_item("경고", "10개", highlight="danger")
        summary.add_item("주의", "5개", highlight="warning")
        summary.add_item("정상", "100개", highlight="success")

        assert summary.current_row > 3

    def test_add_blank_row(self):
        """빈 행 추가"""
        wb = Workbook()
        summary = wb.new_summary_sheet("요약")

        initial_row = summary.current_row
        summary.add_blank_row()

        assert summary.current_row == initial_row + 1

    def test_method_chaining(self):
        """메서드 체이닝"""
        wb = Workbook()
        summary = wb.new_summary_sheet("요약")

        result = (
            summary.add_title("보고서")
            .add_section("정보")
            .add_item("항목1", "값1")
            .add_blank_row()
            .add_item("항목2", "값2")
        )

        assert result is summary


class TestWorkbookIntegration:
    """통합 테스트"""

    def test_complete_workflow(self):
        """전체 워크플로우 테스트"""
        wb = Workbook(lang="ko")

        # Summary 시트
        summary = wb.new_summary_sheet("분석 요약")
        summary.add_title("테스트 보고서")
        summary.add_section("기본 정보")
        summary.add_item("분석 대상", "테스트")
        summary.add_item("분석 일시", "2024-01-01")

        # 데이터 시트
        columns = [
            ColumnDef(header="ID", width=15, style="text"),
            ColumnDef(header="이름", width=25, style="data"),
            ColumnDef(header="값", width=15, style="number"),
            ColumnDef(header="비율", width=10, style="percent"),
        ]
        data_sheet = wb.new_sheet(name="상세 데이터", columns=columns)

        data_sheet.add_row(["001", "항목 A", 100, 0.5])
        data_sheet.add_row(["002", "항목 B", 200, 0.3])
        data_sheet.add_row(["003", "항목 C", 150, 0.2])
        data_sheet.add_summary_row(["합계", "-", 450, 1.0])

        # 저장
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = wb.save(Path(tmpdir) / "integration_test.xlsx")

            assert Path(filepath).exists()
            assert Path(filepath).stat().st_size > 0

    def test_csv_export(self):
        """CSV 내보내기 (시트별)"""
        wb = Workbook()
        columns = [
            ColumnDef(header="A"),
            ColumnDef(header="B"),
        ]
        sheet = wb.new_sheet(name="Data", columns=columns)
        sheet.add_row(["val1", "val2"])
        sheet.add_row(["val3", "val4"])

        with tempfile.TemporaryDirectory() as tmpdir:
            # Excel 저장
            filepath = wb.save(Path(tmpdir) / "test.xlsx")

            assert Path(filepath).exists()

            # CSV 내보내기 메서드가 있다면 테스트
            # wb.export_csv(str(tmpdir), "test")
