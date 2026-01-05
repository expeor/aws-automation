"""
tests/plugins/vpc/test_plugins_nat_audit.py - NAT Gateway Audit 테스트
"""

from unittest.mock import MagicMock, patch


class TestPrintSummary:
    """_print_summary 함수 테스트"""

    @patch("plugins.vpc.nat_audit.console")
    def test_empty_stats_list(self, mock_console):
        """빈 통계 리스트"""
        from plugins.vpc.nat_audit import _print_summary

        _print_summary([])

        # 콘솔 출력이 호출되었는지 확인
        assert mock_console.print.called

    @patch("plugins.vpc.nat_audit.console")
    def test_single_stats(self, mock_console):
        """단일 통계"""
        from plugins.vpc.nat_audit import _print_summary

        stats = [
            {
                "total_nat_count": 5,
                "unused_count": 2,
                "low_usage_count": 1,
                "normal_count": 2,
                "total_monthly_cost": 100.0,
                "total_monthly_waste": 40.0,
                "total_annual_savings": 480.0,
            }
        ]

        _print_summary(stats)

        # 출력에 예상 값이 포함되는지 확인
        calls = str(mock_console.print.call_args_list)
        assert "5" in calls  # total_nat_count
        assert "2" in calls  # unused_count

    @patch("plugins.vpc.nat_audit.console")
    def test_multiple_stats_aggregation(self, mock_console):
        """여러 통계 집계"""
        from plugins.vpc.nat_audit import _print_summary

        stats = [
            {
                "total_nat_count": 3,
                "unused_count": 1,
                "low_usage_count": 1,
                "normal_count": 1,
                "total_monthly_cost": 60.0,
                "total_monthly_waste": 20.0,
                "total_annual_savings": 240.0,
            },
            {
                "total_nat_count": 2,
                "unused_count": 1,
                "low_usage_count": 0,
                "normal_count": 1,
                "total_monthly_cost": 40.0,
                "total_monthly_waste": 20.0,
                "total_annual_savings": 240.0,
            },
        ]

        _print_summary(stats)

        # 콘솔 출력이 호출되었는지 확인
        assert mock_console.print.called

    @patch("plugins.vpc.nat_audit.console")
    def test_no_unused(self, mock_console):
        """미사용 NAT가 없는 경우"""
        from plugins.vpc.nat_audit import _print_summary

        stats = [
            {
                "total_nat_count": 3,
                "unused_count": 0,
                "low_usage_count": 0,
                "normal_count": 3,
                "total_monthly_cost": 60.0,
                "total_monthly_waste": 0.0,
                "total_annual_savings": 0.0,
            }
        ]

        _print_summary(stats)

        # 콘솔 출력이 호출되었는지 확인
        assert mock_console.print.called


class TestCreateOutputDirectory:
    """_create_output_directory 함수 테스트"""

    @patch("plugins.vpc.nat_audit.OutputPath")
    def test_with_sso_session(self, mock_output_path):
        """SSO 세션이 있는 경우"""
        from plugins.vpc.nat_audit import _create_output_directory

        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = True
        mock_ctx.accounts = [MagicMock(id="123456789012")]

        mock_path_instance = MagicMock()
        mock_path_instance.sub.return_value = mock_path_instance
        mock_path_instance.with_date.return_value = mock_path_instance
        mock_path_instance.build.return_value = "/output/123456789012/vpc/cost/2024-01-01"
        mock_output_path.return_value = mock_path_instance

        result = _create_output_directory(mock_ctx)

        mock_output_path.assert_called_once_with("123456789012")
        mock_path_instance.sub.assert_called_once_with("vpc", "cost")
        assert result == "/output/123456789012/vpc/cost/2024-01-01"

    @patch("plugins.vpc.nat_audit.OutputPath")
    def test_with_profile_name(self, mock_output_path):
        """프로파일명이 있는 경우"""
        from plugins.vpc.nat_audit import _create_output_directory

        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = False
        mock_ctx.profile_name = "my-profile"

        mock_path_instance = MagicMock()
        mock_path_instance.sub.return_value = mock_path_instance
        mock_path_instance.with_date.return_value = mock_path_instance
        mock_path_instance.build.return_value = "/output/my-profile/vpc/cost/2024-01-01"
        mock_output_path.return_value = mock_path_instance

        _create_output_directory(mock_ctx)

        mock_output_path.assert_called_once_with("my-profile")

    @patch("plugins.vpc.nat_audit.OutputPath")
    def test_default_identifier(self, mock_output_path):
        """기본 식별자 사용"""
        from plugins.vpc.nat_audit import _create_output_directory

        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = False
        mock_ctx.profile_name = None

        mock_path_instance = MagicMock()
        mock_path_instance.sub.return_value = mock_path_instance
        mock_path_instance.with_date.return_value = mock_path_instance
        mock_path_instance.build.return_value = "/output/default/vpc/cost/2024-01-01"
        mock_output_path.return_value = mock_path_instance

        _create_output_directory(mock_ctx)

        mock_output_path.assert_called_once_with("default")


class TestCollectAndAnalyze:
    """_collect_and_analyze 함수 테스트"""

    @patch("plugins.vpc.nat_audit.NATAnalyzer")
    @patch("plugins.vpc.nat_audit.NATCollector")
    def test_no_nat_gateways(self, mock_collector_cls, mock_analyzer_cls):
        """NAT Gateway가 없는 경우"""
        from plugins.vpc.nat_audit import _collect_and_analyze

        mock_collector = MagicMock()
        mock_collector.collect.return_value = MagicMock(nat_gateways=[])
        mock_collector_cls.return_value = mock_collector

        mock_session = MagicMock()
        result = _collect_and_analyze(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert result is None

    @patch("plugins.vpc.nat_audit.NATAnalyzer")
    @patch("plugins.vpc.nat_audit.NATCollector")
    def test_with_nat_gateways(self, mock_collector_cls, mock_analyzer_cls):
        """NAT Gateway가 있는 경우"""
        from plugins.vpc.nat_audit import _collect_and_analyze

        # Collector 설정
        mock_collector = MagicMock()
        mock_audit_data = MagicMock()
        mock_audit_data.nat_gateways = [MagicMock(), MagicMock()]
        mock_collector.collect.return_value = mock_audit_data
        mock_collector_cls.return_value = mock_collector

        # Analyzer 설정
        mock_analyzer = MagicMock()
        mock_analysis_result = {"results": []}
        mock_stats = {"total": 2}
        mock_analyzer.analyze.return_value = mock_analysis_result
        mock_analyzer.get_summary_stats.return_value = mock_stats
        mock_analyzer_cls.return_value = mock_analyzer

        mock_session = MagicMock()
        result = _collect_and_analyze(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert result is not None
        assert result == (mock_analysis_result, mock_stats)


class TestRun:
    """run 함수 테스트"""

    @patch("plugins.vpc.nat_audit.open_in_explorer")
    @patch("plugins.vpc.nat_audit.NATExcelReporter")
    @patch("plugins.vpc.nat_audit._create_output_directory")
    @patch("plugins.vpc.nat_audit._print_summary")
    @patch("plugins.vpc.nat_audit.parallel_collect")
    @patch("plugins.vpc.nat_audit.console")
    def test_no_results(
        self,
        mock_console,
        mock_parallel,
        mock_print,
        mock_output,
        mock_reporter,
        mock_explorer,
    ):
        """결과가 없는 경우"""
        from plugins.vpc.nat_audit import run

        mock_result = MagicMock()
        mock_result.get_data.return_value = [None, None]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 결과가 없으면 Excel 보고서가 생성되지 않음
        mock_reporter.assert_not_called()

    @patch("plugins.vpc.nat_audit.open_in_explorer")
    @patch("plugins.vpc.nat_audit.NATExcelReporter")
    @patch("plugins.vpc.nat_audit._create_output_directory")
    @patch("plugins.vpc.nat_audit._print_summary")
    @patch("plugins.vpc.nat_audit.parallel_collect")
    @patch("plugins.vpc.nat_audit.console")
    def test_with_results(
        self,
        mock_console,
        mock_parallel,
        mock_print,
        mock_output,
        mock_reporter_cls,
        mock_explorer,
    ):
        """결과가 있는 경우"""
        from plugins.vpc.nat_audit import run

        mock_analysis = {"results": []}
        mock_stats = {"total": 2}

        mock_result = MagicMock()
        mock_result.get_data.return_value = [(mock_analysis, mock_stats)]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        mock_output.return_value = "/output/path"

        mock_reporter = MagicMock()
        mock_reporter.generate.return_value = "/output/path/report.xlsx"
        mock_reporter_cls.return_value = mock_reporter

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 보고서가 생성됨
        mock_reporter_cls.assert_called_once()
        mock_reporter.generate.assert_called_once_with("/output/path")
        mock_explorer.assert_called_once_with("/output/path")

    @patch("plugins.vpc.nat_audit.open_in_explorer")
    @patch("plugins.vpc.nat_audit.NATExcelReporter")
    @patch("plugins.vpc.nat_audit._create_output_directory")
    @patch("plugins.vpc.nat_audit._print_summary")
    @patch("plugins.vpc.nat_audit.parallel_collect")
    @patch("plugins.vpc.nat_audit.console")
    def test_with_errors(
        self,
        mock_console,
        mock_parallel,
        mock_print,
        mock_output,
        mock_reporter_cls,
        mock_explorer,
    ):
        """에러가 있는 경우"""
        from plugins.vpc.nat_audit import run

        mock_analysis = {"results": []}
        mock_stats = {"total": 2}

        mock_result = MagicMock()
        mock_result.get_data.return_value = [(mock_analysis, mock_stats)]
        mock_result.error_count = 3
        mock_result.get_error_summary.return_value = "Error summary"
        mock_parallel.return_value = mock_result

        mock_output.return_value = "/output/path"

        mock_reporter = MagicMock()
        mock_reporter.generate.return_value = "/output/path/report.xlsx"
        mock_reporter_cls.return_value = mock_reporter

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 에러 메시지가 출력됨
        calls_str = str(mock_console.print.call_args_list)
        assert "3" in calls_str or "오류" in calls_str
