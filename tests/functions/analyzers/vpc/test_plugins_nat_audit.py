"""
tests/plugins/vpc/test_plugins_nat_audit.py - NAT Gateway Audit 테스트
"""

from unittest.mock import MagicMock, patch


class TestPrintSummary:
    """_print_summary 함수 테스트"""

    @patch("functions.analyzers.vpc.nat_audit.console")
    def test_empty_stats_list(self, mock_console):
        """빈 통계 리스트"""
        from functions.analyzers.vpc.nat_audit import _print_summary

        _print_summary([])

        # 콘솔 출력이 호출되었는지 확인
        assert mock_console.print.called

    @patch("functions.analyzers.vpc.nat_audit.console")
    def test_single_stats(self, mock_console):
        """단일 통계"""
        from functions.analyzers.vpc.nat_audit import _print_summary

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

    @patch("functions.analyzers.vpc.nat_audit.console")
    def test_multiple_stats_aggregation(self, mock_console):
        """여러 통계 집계"""
        from functions.analyzers.vpc.nat_audit import _print_summary

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

    @patch("functions.analyzers.vpc.nat_audit.console")
    def test_no_unused(self, mock_console):
        """미사용 NAT가 없는 경우"""
        from functions.analyzers.vpc.nat_audit import _print_summary

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


class TestCollectAndAnalyze:
    """_collect_and_analyze 함수 테스트"""

    @patch("functions.analyzers.vpc.nat_audit.NATAnalyzer")
    @patch("functions.analyzers.vpc.nat_audit.NATCollector")
    def test_no_nat_gateways(self, mock_collector_cls, mock_analyzer_cls):
        """NAT Gateway가 없는 경우"""
        from functions.analyzers.vpc.nat_audit import _collect_and_analyze

        mock_collector = MagicMock()
        mock_collector.collect.return_value = MagicMock(nat_gateways=[])
        mock_collector_cls.return_value = mock_collector

        mock_session = MagicMock()
        result = _collect_and_analyze(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert result is None

    @patch("functions.analyzers.vpc.nat_audit.NATAnalyzer")
    @patch("functions.analyzers.vpc.nat_audit.NATCollector")
    def test_with_nat_gateways(self, mock_collector_cls, mock_analyzer_cls):
        """NAT Gateway가 있는 경우"""
        from functions.analyzers.vpc.nat_audit import _collect_and_analyze

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

    @patch("functions.analyzers.vpc.nat_audit.open_in_explorer")
    @patch("functions.analyzers.vpc.nat_audit.NATExcelReporter")
    @patch("functions.analyzers.vpc.nat_audit.create_output_path")
    @patch("functions.analyzers.vpc.nat_audit._print_summary")
    @patch("functions.analyzers.vpc.nat_audit.parallel_collect")
    @patch("functions.analyzers.vpc.nat_audit.console")
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
        from functions.analyzers.vpc.nat_audit import run

        mock_result = MagicMock()
        mock_result.get_data.return_value = [None, None]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 결과가 없으면 Excel 보고서가 생성되지 않음
        mock_reporter.assert_not_called()

    @patch("functions.analyzers.vpc.nat_audit.open_in_explorer")
    @patch("functions.analyzers.vpc.nat_audit.generate_dual_report")
    @patch("functions.analyzers.vpc.nat_audit.NATExcelReporter")
    @patch("functions.analyzers.vpc.nat_audit.create_output_path")
    @patch("functions.analyzers.vpc.nat_audit._print_summary")
    @patch("functions.analyzers.vpc.nat_audit.parallel_collect")
    @patch("functions.analyzers.vpc.nat_audit.console")
    def test_with_results(
        self,
        mock_console,
        mock_parallel,
        mock_print,
        mock_output,
        mock_reporter_cls,
        mock_dual_report,
        mock_explorer,
    ):
        """결과가 있는 경우"""
        from functions.analyzers.vpc.nat_audit import run

        mock_analysis = MagicMock()
        mock_analysis.findings = []
        mock_stats = {"total_nat_count": 2, "unused_count": 0, "low_usage_count": 0, "total_monthly_waste": 0}

        mock_result = MagicMock()
        mock_result.get_data.return_value = [(mock_analysis, mock_stats)]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        mock_output.return_value = "/output/path"
        mock_dual_report.return_value = {"excel": "/output/path/report.xlsx"}

        mock_reporter = MagicMock()
        mock_reporter_cls.return_value = mock_reporter

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 보고서가 생성됨
        mock_reporter_cls.assert_called_once()
        mock_dual_report.assert_called_once()
        mock_explorer.assert_called_once_with("/output/path")

    @patch("functions.analyzers.vpc.nat_audit.open_in_explorer")
    @patch("functions.analyzers.vpc.nat_audit.generate_dual_report")
    @patch("functions.analyzers.vpc.nat_audit.NATExcelReporter")
    @patch("functions.analyzers.vpc.nat_audit.create_output_path")
    @patch("functions.analyzers.vpc.nat_audit._print_summary")
    @patch("functions.analyzers.vpc.nat_audit.parallel_collect")
    @patch("functions.analyzers.vpc.nat_audit.console")
    def test_with_errors(
        self,
        mock_console,
        mock_parallel,
        mock_print,
        mock_output,
        mock_reporter_cls,
        mock_dual_report,
        mock_explorer,
    ):
        """에러가 있는 경우"""
        from functions.analyzers.vpc.nat_audit import run

        mock_analysis = MagicMock()
        mock_analysis.findings = []
        mock_stats = {"total_nat_count": 2, "unused_count": 0, "low_usage_count": 0, "total_monthly_waste": 0}

        mock_result = MagicMock()
        mock_result.get_data.return_value = [(mock_analysis, mock_stats)]
        mock_result.error_count = 3
        mock_result.get_error_summary.return_value = "Error summary"
        mock_parallel.return_value = mock_result

        mock_output.return_value = "/output/path"
        mock_dual_report.return_value = {"excel": "/output/path/report.xlsx"}

        mock_reporter = MagicMock()
        mock_reporter_cls.return_value = mock_reporter

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 에러 메시지가 출력됨
        calls_str = str(mock_console.print.call_args_list)
        assert "3" in calls_str or "오류" in calls_str
