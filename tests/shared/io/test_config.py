"""core/tools/io/config.py 테스트"""

from core.shared.io.config import OutputConfig, OutputFormat


class TestOutputFormat:
    """OutputFormat 테스트"""

    def test_format_flags(self):
        """Flag 동작 확인"""
        # 개별 형식
        assert OutputFormat.EXCEL != OutputFormat.NONE
        assert OutputFormat.HTML != OutputFormat.NONE
        assert OutputFormat.CONSOLE != OutputFormat.NONE

        # 형식 조합
        combined = OutputFormat.EXCEL | OutputFormat.HTML
        assert OutputFormat.EXCEL in combined
        assert OutputFormat.HTML in combined
        assert OutputFormat.CONSOLE not in combined

    def test_all_format(self):
        """ALL 형식 확인 (Excel + HTML)"""
        assert OutputFormat.EXCEL in OutputFormat.ALL
        assert OutputFormat.HTML in OutputFormat.ALL
        assert OutputFormat.CONSOLE not in OutputFormat.ALL

    def test_none_format(self):
        """NONE 형식 확인"""
        assert OutputFormat.EXCEL not in OutputFormat.NONE
        assert OutputFormat.HTML not in OutputFormat.NONE


class TestOutputConfig:
    """OutputConfig 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        config = OutputConfig()
        assert config.formats == OutputFormat.ALL
        assert config.output_dir is None
        assert config.auto_open is True
        assert config.lang == "ko"

    def test_should_output_methods(self):
        """출력 여부 메서드 확인"""
        # 기본값 (ALL = Excel + HTML)
        config = OutputConfig()
        assert config.should_output_excel() is True
        assert config.should_output_html() is True
        assert config.should_output_console() is False

        # Excel만
        config = OutputConfig(formats=OutputFormat.EXCEL)
        assert config.should_output_excel() is True
        assert config.should_output_html() is False

        # HTML만
        config = OutputConfig(formats=OutputFormat.HTML)
        assert config.should_output_excel() is False
        assert config.should_output_html() is True

        # Console만
        config = OutputConfig(formats=OutputFormat.CONSOLE)
        assert config.should_output_excel() is False
        assert config.should_output_html() is False
        assert config.should_output_console() is True

    def test_from_string_both(self):
        """문자열 'both' 변환 확인"""
        config = OutputConfig.from_string("both")
        assert config.formats == OutputFormat.ALL
        assert config.should_output_excel() is True
        assert config.should_output_html() is True

    def test_from_string_excel(self):
        """문자열 'excel' 변환 확인"""
        config = OutputConfig.from_string("excel")
        assert config.formats == OutputFormat.EXCEL
        assert config.should_output_excel() is True
        assert config.should_output_html() is False

    def test_from_string_html(self):
        """문자열 'html' 변환 확인"""
        config = OutputConfig.from_string("html")
        assert config.formats == OutputFormat.HTML
        assert config.should_output_excel() is False
        assert config.should_output_html() is True

    def test_from_string_console(self):
        """문자열 'console' 변환 확인"""
        config = OutputConfig.from_string("console")
        assert config.formats == OutputFormat.CONSOLE
        assert config.should_output_console() is True

    def test_from_string_case_insensitive(self):
        """대소문자 무시 확인"""
        config = OutputConfig.from_string("EXCEL")
        assert config.formats == OutputFormat.EXCEL

        config = OutputConfig.from_string("Html")
        assert config.formats == OutputFormat.HTML

    def test_from_string_unknown(self):
        """알 수 없는 문자열 시 기본값 확인"""
        config = OutputConfig.from_string("unknown")
        assert config.formats == OutputFormat.ALL

    def test_custom_output_dir(self):
        """커스텀 출력 디렉토리 설정"""
        config = OutputConfig(output_dir="/custom/path")
        assert config.output_dir == "/custom/path"

    def test_auto_open_disabled(self):
        """자동 열기 비활성화"""
        config = OutputConfig(auto_open=False)
        assert config.auto_open is False

    def test_lang_setting(self):
        """언어 설정"""
        config = OutputConfig(lang="en")
        assert config.lang == "en"
