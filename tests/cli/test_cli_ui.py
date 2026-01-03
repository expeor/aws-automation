# tests/test_cli_ui.py
"""
cli/ui 모듈 단위 테스트

콘솔 유틸리티, 배너, 메뉴 테스트.
"""


# =============================================================================
# Console 유틸리티 테스트
# =============================================================================


class TestConsoleUtilities:
    """콘솔 유틸리티 테스트"""

    def test_get_console_returns_console(self):
        """get_console이 Console 인스턴스 반환"""
        from rich.console import Console

        from cli.ui.console import get_console

        console = get_console()
        assert isinstance(console, Console)

    def test_get_progress_returns_progress(self):
        """get_progress가 Progress 인스턴스 반환"""
        from rich.progress import Progress

        from cli.ui.console import get_progress

        progress = get_progress()
        assert isinstance(progress, Progress)

    def test_console_singleton(self):
        """전역 console 인스턴스 확인"""
        from rich.console import Console

        from cli.ui.console import console

        assert isinstance(console, Console)


class TestPrintFunctions:
    """출력 함수 테스트"""

    def test_print_success_no_error(self):
        """print_success 호출 시 에러 없음"""
        from cli.ui.console import print_success

        # 에러 없이 실행되는지 확인
        print_success("테스트 성공 메시지")

    def test_print_error_no_error(self):
        """print_error 호출 시 에러 없음"""
        from cli.ui.console import print_error

        print_error("테스트 에러 메시지")

    def test_print_warning_no_error(self):
        """print_warning 호출 시 에러 없음"""
        from cli.ui.console import print_warning

        print_warning("테스트 경고 메시지")

    def test_print_info_no_error(self):
        """print_info 호출 시 에러 없음"""
        from cli.ui.console import print_info

        print_info("테스트 정보 메시지")

    def test_print_header_no_error(self):
        """print_header 호출 시 에러 없음"""
        from cli.ui.console import print_header

        print_header("테스트 헤더")

    def test_print_step_no_error(self):
        """print_step 호출 시 에러 없음"""
        from cli.ui.console import print_step

        print_step(1, 5, "테스트 단계")

    def test_print_table_no_error(self):
        """print_table 호출 시 에러 없음"""
        from cli.ui.console import print_table

        print_table(
            "테스트 테이블",
            ["컬럼1", "컬럼2"],
            [["값1", "값2"], ["값3", "값4"]],
        )


class TestSectionBox:
    """섹션 박스 UI 테스트"""

    def test_print_section_box(self):
        """print_section_box 호출 시 에러 없음"""
        from cli.ui.console import print_section_box

        print_section_box("테스트 박스", ["내용1", "내용2"])

    def test_print_section_box_without_content(self):
        """내용 없는 섹션 박스"""
        from cli.ui.console import print_section_box

        print_section_box("테스트 박스")

    def test_print_box_line(self):
        """print_box_line 호출 시 에러 없음"""
        from cli.ui.console import print_box_line

        print_box_line("테스트 라인")
        print_box_line("")  # 빈 라인

    def test_print_box_start_end(self):
        """박스 시작/끝 함수 테스트"""
        from cli.ui.console import print_box_end, print_box_start

        print_box_start("테스트 박스")
        print_box_end()


class TestPrintLegend:
    """범례 출력 테스트"""

    def test_print_legend_single_item(self):
        """단일 항목 범례"""
        from cli.ui.console import print_legend

        print_legend([("yellow", "사용 중")])

    def test_print_legend_multiple_items(self):
        """다중 항목 범례"""
        from cli.ui.console import print_legend

        print_legend(
            [
                ("yellow", "사용 중"),
                ("red", "에러"),
                ("green", "정상"),
            ]
        )

    def test_print_legend_unknown_color(self):
        """알 수 없는 색상도 처리"""
        from cli.ui.console import print_legend

        print_legend([("unknown_color", "설명")])


class TestPrintPanelHeader:
    """패널 헤더 테스트"""

    def test_panel_header_title_only(self):
        """제목만 있는 패널"""
        from cli.ui.console import print_panel_header

        print_panel_header("테스트 제목")

    def test_panel_header_with_subtitle(self):
        """부제목 있는 패널"""
        from cli.ui.console import print_panel_header

        print_panel_header("테스트 제목", "테스트 부제목")


# =============================================================================
# Banner 테스트
# =============================================================================


class TestBanner:
    """배너 테스트"""

    def test_get_version(self):
        """버전 문자열 반환"""
        from cli.ui.banner import get_version

        version = get_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_print_banner(self):
        """배너 출력 시 에러 없음"""
        from cli.ui.banner import print_banner
        from cli.ui.console import console

        print_banner(console)

    def test_print_simple_banner(self):
        """간단한 배너 출력 시 에러 없음"""
        from cli.ui.banner import print_simple_banner
        from cli.ui.console import console

        print_simple_banner(console)

    def test_compact_logo_defined(self):
        """COMPACT_LOGO 상수 정의됨"""
        from cli.ui.banner import COMPACT_LOGO

        assert isinstance(COMPACT_LOGO, str)
        assert "{version}" in COMPACT_LOGO

    def test_full_logo_defined(self):
        """FULL_LOGO 상수 정의됨"""
        from cli.ui.banner import FULL_LOGO

        assert isinstance(FULL_LOGO, str)
        assert "{version}" in FULL_LOGO or "█" in FULL_LOGO


# =============================================================================
# __init__.py re-export 테스트
# =============================================================================


class TestUIModuleExports:
    """UI 모듈 export 테스트"""

    def test_import_from_ui(self):
        """cli.ui에서 주요 함수 import 가능"""
        from cli.ui import (
            console,
            print_error,
            print_info,
            print_success,
            print_warning,
        )

        assert console is not None
        assert callable(print_success)
        assert callable(print_error)
        assert callable(print_warning)
        assert callable(print_info)


# =============================================================================
# Logger 테스트
# =============================================================================


class TestLogger:
    """로거 테스트"""

    def test_get_logger(self):
        """get_logger 반환 확인"""
        import logging

        from cli.ui.console import get_logger

        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)

    def test_logger_singleton(self):
        """전역 logger 인스턴스 확인"""
        import logging

        from cli.ui.console import logger

        assert isinstance(logger, logging.Logger)
