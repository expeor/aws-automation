"""
tests/shared/io/test_compat.py - 호환성 모듈 테스트
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from shared.io.compat import (
    _generate_html_from_data,
    _get_default_output_dir,
    _get_output_config,
    generate_dual_report,
    generate_reports,
)


@pytest.fixture
def mock_context():
    """Mock ExecutionContext 픽스처"""
    ctx = MagicMock()
    ctx.lang = "ko"
    ctx.profile_name = "test-profile"
    ctx.category = "test-category"
    ctx.tool = MagicMock()
    ctx.tool.name = "test tool"
    ctx.accounts = []
    ctx.output_config = None

    # is_sso_session 메서드 추가
    ctx.is_sso_session = MagicMock(return_value=False)

    return ctx


@pytest.fixture
def sample_data():
    """테스트용 샘플 데이터"""
    return [
        {"Name": "Item1", "Value": 100, "Status": "active"},
        {"Name": "Item2", "Value": 200, "Status": "inactive"},
        {"Name": "Item3", "Value": 150, "Status": "active"},
    ]


class TestGetOutputConfig:
    """출력 설정 가져오기 테스트"""

    def test_get_output_config_from_context(self, mock_context):
        """컨텍스트에서 출력 설정 가져오기"""
        from shared.io.config import OutputConfig

        output_config = OutputConfig(lang="ko", formats=["excel"])
        mock_context.output_config = output_config

        result = _get_output_config(mock_context)

        assert result is output_config
        assert result.lang == "ko"

    def test_get_output_config_default(self, mock_context):
        """기본 출력 설정 생성"""
        mock_context.output_config = None
        mock_context.lang = "en"

        result = _get_output_config(mock_context)

        assert result is not None
        assert result.lang == "en"

    def test_get_output_config_no_output_config_attr(self):
        """output_config 속성이 없는 경우"""
        ctx = MagicMock()
        ctx.lang = "ko"
        del ctx.output_config  # 속성 제거

        result = _get_output_config(ctx)

        assert result is not None
        assert result.lang == "ko"


class TestGetDefaultOutputDir:
    """기본 출력 디렉토리 생성 테스트"""

    def test_default_output_dir_with_profile(self, mock_context):
        """프로파일 기반 출력 디렉토리"""
        mock_context.profile_name = "my-profile"
        mock_context.category = "ec2"
        mock_context.tool.name = "unused instances"

        result = _get_default_output_dir(mock_context)

        assert result is not None
        assert "my-profile" in result
        assert "ec2" in result

    def test_default_output_dir_with_sso_session(self, mock_context):
        """SSO 세션 기반 출력 디렉토리"""
        mock_context.is_sso_session.return_value = True
        account = MagicMock()
        account.id = "123456789012"
        mock_context.accounts = [account]
        mock_context.category = "vpc"
        mock_context.tool.name = "security groups"

        result = _get_default_output_dir(mock_context)

        assert result is not None
        assert "123456789012" in result
        assert "vpc" in result

    def test_default_output_dir_no_profile_or_account(self, mock_context):
        """프로파일이나 계정 없는 경우"""
        mock_context.profile_name = None
        mock_context.is_sso_session.return_value = False
        mock_context.accounts = []
        mock_context.category = "lambda"
        mock_context.tool.name = "unused functions"

        result = _get_default_output_dir(mock_context)

        assert result is not None
        assert "default" in result

    def test_default_output_dir_no_category(self, mock_context):
        """카테고리 없는 경우"""
        mock_context.category = None
        mock_context.profile_name = "test-profile"

        result = _get_default_output_dir(mock_context)

        assert result is not None
        assert "report" in result

    def test_default_output_dir_no_tool(self, mock_context):
        """도구 정보 없는 경우"""
        mock_context.tool = None
        mock_context.profile_name = "test-profile"
        mock_context.category = "ec2"

        result = _get_default_output_dir(mock_context)

        assert result is not None
        assert "output" in result


class TestGenerateHtmlFromData:
    """HTML 생성 테스트"""

    @patch("shared.io.html.create_aws_report")
    def test_generate_html_basic(self, mock_create_report, mock_context, sample_data):
        """기본 HTML 생성"""
        mock_report = MagicMock()
        mock_create_report.return_value = mock_report

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "title": "Test Report",
                "service": "EC2",
                "tool_name": "unused",
            }

            result = _generate_html_from_data(mock_context, sample_data, config, tmpdir)

            assert result is not None
            assert result.endswith(".html")
            assert "ec2" in result.lower()
            mock_create_report.assert_called_once()
            mock_report.save.assert_called_once()

    @patch("shared.io.html.create_aws_report")
    def test_generate_html_with_metrics(self, mock_create_report, mock_context, sample_data):
        """메트릭 포함 HTML 생성"""
        mock_report = MagicMock()
        mock_create_report.return_value = mock_report

        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                "title": "Cost Report",
                "service": "Cost",
                "tool_name": "analysis",
                "total": 100,
                "found": 25,
                "savings": 1500.50,
            }

            result = _generate_html_from_data(mock_context, sample_data, config, tmpdir)

            assert result is not None
            call_kwargs = mock_create_report.call_args[1]
            assert call_kwargs["total"] == 100
            assert call_kwargs["found"] == 25
            assert call_kwargs["savings"] == 1500.50

    @patch("shared.io.html.create_aws_report")
    def test_generate_html_creates_directory(self, mock_create_report, mock_context, sample_data):
        """디렉토리 자동 생성"""
        mock_report = MagicMock()
        mock_create_report.return_value = mock_report

        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = Path(tmpdir) / "level1" / "level2"
            config = {
                "title": "Test",
                "service": "EC2",
                "tool_name": "test",
            }

            result = _generate_html_from_data(mock_context, sample_data, config, str(nested_dir))

            assert result is not None
            assert Path(result).parent.exists()


class TestGenerateReports:
    """리포트 생성 테스트"""

    @patch("shared.io.html.open_in_browser")
    def test_generate_reports_excel_only(self, mock_open_browser, mock_context, sample_data):
        """Excel만 생성"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.EXCEL)

        excel_path = None

        def excel_generator(output_dir):
            nonlocal excel_path
            excel_path = str(Path(output_dir) / "test.xlsx")
            # 실제 파일 생성
            Path(excel_path).parent.mkdir(parents=True, exist_ok=True)
            Path(excel_path).touch()
            return excel_path

        with tempfile.TemporaryDirectory() as tmpdir:
            results = generate_reports(
                mock_context, sample_data, excel_generator=excel_generator, html_config=None, output_dir=tmpdir
            )

            assert "excel" in results
            assert results["excel"] == excel_path
            assert "html" not in results
            mock_open_browser.assert_not_called()

    @patch("shared.io.html.open_in_browser")
    @patch("shared.io.compat._generate_html_from_data")
    def test_generate_reports_html_only(
        self, mock_generate_html, mock_open_browser, mock_context, sample_data
    ):
        """HTML만 생성"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.HTML, auto_open=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = str(Path(tmpdir) / "test.html")
            mock_generate_html.return_value = html_path

            html_config = {"title": "Test", "service": "EC2", "tool_name": "test"}

            results = generate_reports(
                mock_context, sample_data, excel_generator=None, html_config=html_config, output_dir=tmpdir
            )

            assert "html" in results
            assert results["html"] == html_path
            assert "excel" not in results
            mock_open_browser.assert_not_called()

    @patch("shared.io.html.open_in_browser")
    @patch("shared.io.compat._generate_html_from_data")
    def test_generate_reports_both_formats(
        self, mock_generate_html, mock_open_browser, mock_context, sample_data
    ):
        """Excel과 HTML 모두 생성"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.ALL, auto_open=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            excel_path = str(Path(tmpdir) / "test.xlsx")
            html_path = str(Path(tmpdir) / "test.html")

            Path(excel_path).touch()
            mock_generate_html.return_value = html_path

            def excel_generator(output_dir):
                return excel_path

            html_config = {"title": "Test", "service": "EC2", "tool_name": "test"}

            results = generate_reports(
                mock_context, sample_data, excel_generator=excel_generator, html_config=html_config, output_dir=tmpdir
            )

            assert "excel" in results
            assert "html" in results
            assert results["excel"] == excel_path
            assert results["html"] == html_path
            mock_open_browser.assert_called_once_with(html_path)

    @patch("shared.io.html.open_in_browser")
    def test_generate_reports_no_data(self, mock_open_browser, mock_context):
        """데이터 없음"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.HTML)

        with tempfile.TemporaryDirectory() as tmpdir:
            html_config = {"title": "Test", "service": "EC2", "tool_name": "test"}

            results = generate_reports(
                mock_context, [], excel_generator=None, html_config=html_config, output_dir=tmpdir
            )

            # 데이터가 없으면 HTML 생성 안 됨
            assert "html" not in results

    def test_generate_reports_no_output_dir(self, mock_context, sample_data):
        """출력 디렉토리 지정 안 함"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.EXCEL)

        excel_path = None

        def excel_generator(output_dir):
            nonlocal excel_path
            excel_path = str(Path(output_dir) / "test.xlsx")
            Path(excel_path).parent.mkdir(parents=True, exist_ok=True)
            Path(excel_path).touch()
            return excel_path

        # output_dir=None이면 자동 생성
        results = generate_reports(mock_context, sample_data, excel_generator=excel_generator, html_config=None)

        assert "excel" in results

    def test_generate_reports_excel_generation_error(self, mock_context, sample_data):
        """Excel 생성 에러 처리"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.EXCEL)

        def failing_excel_generator(output_dir):
            raise Exception("Excel generation failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            # 에러가 발생해도 예외를 발생시키지 않고 빈 결과 반환
            results = generate_reports(
                mock_context, sample_data, excel_generator=failing_excel_generator, output_dir=tmpdir
            )

            assert "excel" not in results

    @patch("shared.io.compat._generate_html_from_data", side_effect=Exception("HTML generation failed"))
    def test_generate_reports_html_generation_error(self, mock_generate_html, mock_context, sample_data):
        """HTML 생성 에러 처리"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.HTML)

        with tempfile.TemporaryDirectory() as tmpdir:
            html_config = {"title": "Test", "service": "EC2", "tool_name": "test"}

            # 에러가 발생해도 예외를 발생시키지 않고 빈 결과 반환
            results = generate_reports(
                mock_context, sample_data, excel_generator=None, html_config=html_config, output_dir=tmpdir
            )

            assert "html" not in results


class TestGenerateDualReport:
    """듀얼 리포트 생성 테스트"""

    @patch("shared.io.html.open_in_browser")
    @patch("shared.io.compat._generate_html_from_data")
    def test_generate_dual_report_both_formats(
        self, mock_generate_html, mock_open_browser, mock_context, sample_data
    ):
        """Excel과 HTML 모두 생성"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.ALL, auto_open=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = str(Path(tmpdir) / "test.html")
            mock_generate_html.return_value = html_path

            # Mock Workbook
            mock_wb = MagicMock()
            excel_path = Path(tmpdir) / "test.xlsx"
            mock_wb.save_as.return_value = excel_path

            def excel_builder():
                return mock_wb

            html_config = {"title": "Test", "service": "EC2", "tool_name": "unused"}

            results = generate_dual_report(
                mock_context,
                sample_data,
                tmpdir,
                "ec2_unused",
                excel_builder,
                html_config,
                region="ap-northeast-2",
            )

            assert "excel" in results
            assert "html" in results
            mock_wb.save_as.assert_called_once()
            mock_open_browser.assert_called_once_with(html_path)

    @patch("shared.io.html.open_in_browser")
    def test_generate_dual_report_excel_only(self, mock_open_browser, mock_context, sample_data):
        """Excel만 생성"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.EXCEL, auto_open=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_wb = MagicMock()
            excel_path = Path(tmpdir) / "test.xlsx"
            mock_wb.save_as.return_value = excel_path

            def excel_builder():
                return mock_wb

            html_config = {"title": "Test", "service": "EC2", "tool_name": "test"}

            results = generate_dual_report(
                mock_context, sample_data, tmpdir, "ec2_test", excel_builder, html_config
            )

            assert "excel" in results
            assert "html" not in results
            mock_open_browser.assert_not_called()

    @patch("shared.io.html.open_in_browser")
    @patch("shared.io.compat._generate_html_from_data")
    def test_generate_dual_report_html_only(
        self, mock_generate_html, mock_open_browser, mock_context, sample_data
    ):
        """HTML만 생성"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.HTML, auto_open=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = str(Path(tmpdir) / "test.html")
            mock_generate_html.return_value = html_path

            mock_wb = MagicMock()

            def excel_builder():
                return mock_wb

            html_config = {"title": "Test", "service": "EC2", "tool_name": "test"}

            results = generate_dual_report(
                mock_context, sample_data, tmpdir, "ec2_test", excel_builder, html_config
            )

            assert "html" in results
            assert "excel" not in results
            mock_wb.save_as.assert_not_called()

    def test_generate_dual_report_creates_directory(self, mock_context, sample_data):
        """디렉토리 자동 생성"""
        from shared.io.config import OutputConfig

        mock_context.output_config = OutputConfig(lang="ko", formats=["excel"])

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "level1" / "level2"

            mock_wb = MagicMock()
            mock_wb.save_as.return_value = output_dir / "test.xlsx"

            def excel_builder():
                return mock_wb

            html_config = {"title": "Test", "service": "EC2", "tool_name": "test"}

            results = generate_dual_report(
                mock_context, sample_data, str(output_dir), "ec2_test", excel_builder, html_config
            )

            assert output_dir.exists()

    def test_generate_dual_report_excel_error(self, mock_context, sample_data):
        """Excel 생성 에러 처리"""
        from shared.io.config import OutputConfig

        mock_context.output_config = OutputConfig(lang="ko", formats=["excel"])

        with tempfile.TemporaryDirectory() as tmpdir:

            def failing_excel_builder():
                raise Exception("Excel build failed")

            html_config = {"title": "Test", "service": "EC2", "tool_name": "test"}

            # 에러가 발생해도 예외를 발생시키지 않음
            results = generate_dual_report(
                mock_context, sample_data, tmpdir, "ec2_test", failing_excel_builder, html_config
            )

            assert "excel" not in results

    @patch("shared.io.compat._generate_html_from_data", side_effect=Exception("HTML failed"))
    def test_generate_dual_report_html_error(self, mock_generate_html, mock_context, sample_data):
        """HTML 생성 에러 처리"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.HTML)

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_wb = MagicMock()

            def excel_builder():
                return mock_wb

            html_config = {"title": "Test", "service": "EC2", "tool_name": "test"}

            # 에러가 발생해도 예외를 발생시키지 않음
            results = generate_dual_report(
                mock_context, sample_data, tmpdir, "ec2_test", excel_builder, html_config
            )

            assert "html" not in results

    @patch("shared.io.html.open_in_browser")
    @patch("shared.io.compat._generate_html_from_data")
    def test_generate_dual_report_no_data(self, mock_generate_html, mock_open_browser, mock_context):
        """데이터 없음"""
        from shared.io.config import OutputConfig, OutputFormat

        mock_context.output_config = OutputConfig(lang="ko", formats=OutputFormat.HTML)

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_wb = MagicMock()

            def excel_builder():
                return mock_wb

            html_config = {"title": "Test", "service": "EC2", "tool_name": "test"}

            results = generate_dual_report(mock_context, [], tmpdir, "ec2_test", excel_builder, html_config)

            # 데이터가 없으면 HTML 생성 안 됨
            assert "html" not in results
            mock_generate_html.assert_not_called()
