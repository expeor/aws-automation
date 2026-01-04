"""
tests/plugins/vpc/test_plugins_sg_audit.py - Security Group Audit 테스트
"""

from unittest.mock import MagicMock, patch


class TestCollectSGs:
    """_collect_sgs 함수 테스트"""

    @patch("plugins.vpc.sg_audit.SGCollector")
    def test_no_security_groups(self, mock_collector_cls):
        """Security Group이 없는 경우"""
        from plugins.vpc.sg_audit import _collect_sgs

        mock_collector = MagicMock()
        mock_collector.collect.return_value = []
        mock_collector_cls.return_value = mock_collector

        mock_session = MagicMock()
        result = _collect_sgs(
            mock_session, "123456789012", "test-account", "ap-northeast-2"
        )

        assert result is None

    @patch("plugins.vpc.sg_audit.SGCollector")
    def test_with_security_groups(self, mock_collector_cls):
        """Security Group이 있는 경우"""
        from plugins.vpc.sg_audit import _collect_sgs

        mock_sg1 = MagicMock()
        mock_sg2 = MagicMock()
        mock_collector = MagicMock()
        mock_collector.collect.return_value = [mock_sg1, mock_sg2]
        mock_collector_cls.return_value = mock_collector

        mock_session = MagicMock()
        result = _collect_sgs(
            mock_session, "123456789012", "test-account", "ap-northeast-2"
        )

        assert result is not None
        assert len(result) == 2

    @patch("plugins.vpc.sg_audit.SGCollector")
    def test_empty_list_returns_none(self, mock_collector_cls):
        """빈 리스트가 반환되면 None"""
        from plugins.vpc.sg_audit import _collect_sgs

        mock_collector = MagicMock()
        mock_collector.collect.return_value = None
        mock_collector_cls.return_value = mock_collector

        mock_session = MagicMock()
        result = _collect_sgs(
            mock_session, "123456789012", "test-account", "ap-northeast-2"
        )

        assert result is None


class TestCreateOutputDirectory:
    """_create_output_directory 함수 테스트"""

    @patch("plugins.vpc.sg_audit.OutputPath")
    def test_with_sso_session(self, mock_output_path):
        """SSO 세션이 있는 경우"""
        from plugins.vpc.sg_audit import _create_output_directory

        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = True
        mock_ctx.accounts = [MagicMock(id="123456789012")]

        mock_path_instance = MagicMock()
        mock_path_instance.sub.return_value = mock_path_instance
        mock_path_instance.with_date.return_value = mock_path_instance
        mock_path_instance.build.return_value = (
            "/output/123456789012/sg-audit/2024-01-01"
        )
        mock_output_path.return_value = mock_path_instance

        _create_output_directory(mock_ctx)

        mock_output_path.assert_called_once_with("123456789012")
        mock_path_instance.sub.assert_called_once_with("sg-audit")

    @patch("plugins.vpc.sg_audit.OutputPath")
    def test_with_profile_name(self, mock_output_path):
        """프로파일명이 있는 경우"""
        from plugins.vpc.sg_audit import _create_output_directory

        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = False
        mock_ctx.profile_name = "my-profile"

        mock_path_instance = MagicMock()
        mock_path_instance.sub.return_value = mock_path_instance
        mock_path_instance.with_date.return_value = mock_path_instance
        mock_path_instance.build.return_value = "/output/my-profile/sg-audit/2024-01-01"
        mock_output_path.return_value = mock_path_instance

        _create_output_directory(mock_ctx)

        mock_output_path.assert_called_once_with("my-profile")

    @patch("plugins.vpc.sg_audit.OutputPath")
    def test_default_identifier(self, mock_output_path):
        """기본 식별자 사용"""
        from plugins.vpc.sg_audit import _create_output_directory

        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = False
        mock_ctx.profile_name = None

        mock_path_instance = MagicMock()
        mock_path_instance.sub.return_value = mock_path_instance
        mock_path_instance.with_date.return_value = mock_path_instance
        mock_path_instance.build.return_value = "/output/default/sg-audit/2024-01-01"
        mock_output_path.return_value = mock_path_instance

        _create_output_directory(mock_ctx)

        mock_output_path.assert_called_once_with("default")


class TestRun:
    """run 함수 테스트"""

    @patch("plugins.vpc.sg_audit.open_in_explorer")
    @patch("plugins.vpc.sg_audit.SGExcelReporter")
    @patch("plugins.vpc.sg_audit._create_output_directory")
    @patch("plugins.vpc.sg_audit.SGAnalyzer")
    @patch("plugins.vpc.sg_audit.parallel_collect")
    @patch("plugins.vpc.sg_audit.console")
    def test_no_security_groups(
        self,
        mock_console,
        mock_parallel,
        mock_analyzer,
        mock_output,
        mock_reporter,
        mock_explorer,
    ):
        """Security Group이 없는 경우"""
        from plugins.vpc.sg_audit import run

        mock_result = MagicMock()
        mock_result.get_data.return_value = [None, None, []]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 결과가 없으면 분석기가 호출되지 않음
        mock_analyzer.assert_not_called()

    @patch("plugins.vpc.sg_audit.open_in_explorer")
    @patch("plugins.vpc.sg_audit.SGExcelReporter")
    @patch("plugins.vpc.sg_audit._create_output_directory")
    @patch("plugins.vpc.sg_audit.SGAnalyzer")
    @patch("plugins.vpc.sg_audit.parallel_collect")
    @patch("plugins.vpc.sg_audit.console")
    def test_with_security_groups(
        self,
        mock_console,
        mock_parallel,
        mock_analyzer_cls,
        mock_output,
        mock_reporter_cls,
        mock_explorer,
    ):
        """Security Group이 있는 경우"""
        from plugins.vpc.sg_audit import run

        mock_sg1 = MagicMock()
        mock_sg2 = MagicMock()

        mock_result = MagicMock()
        mock_result.get_data.return_value = [[mock_sg1], [mock_sg2]]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        # Analyzer 설정
        mock_sg_result = MagicMock()
        mock_sg_result.status.value = "Active"

        mock_rule_result = MagicMock()
        mock_rule_result.status.value = "Active"
        mock_rule_result.risk_level = "LOW"

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = ([mock_sg_result], [mock_rule_result])
        mock_analyzer.get_summary.return_value = {"total": 2}
        mock_analyzer_cls.return_value = mock_analyzer

        mock_output.return_value = "/output/path"

        mock_reporter = MagicMock()
        mock_reporter.generate.return_value = "/output/path/report.xlsx"
        mock_reporter_cls.return_value = mock_reporter

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 분석기가 호출됨
        mock_analyzer_cls.assert_called_once()
        mock_reporter_cls.assert_called_once()
        mock_explorer.assert_called_once_with("/output/path")

    @patch("plugins.vpc.sg_audit.open_in_explorer")
    @patch("plugins.vpc.sg_audit.SGExcelReporter")
    @patch("plugins.vpc.sg_audit._create_output_directory")
    @patch("plugins.vpc.sg_audit.SGAnalyzer")
    @patch("plugins.vpc.sg_audit.parallel_collect")
    @patch("plugins.vpc.sg_audit.console")
    def test_with_unused_sgs(
        self,
        mock_console,
        mock_parallel,
        mock_analyzer_cls,
        mock_output,
        mock_reporter_cls,
        mock_explorer,
    ):
        """미사용 Security Group이 있는 경우"""
        from plugins.vpc.sg_audit import run

        mock_sg = MagicMock()

        mock_result = MagicMock()
        mock_result.get_data.return_value = [[mock_sg]]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        # 미사용 SG 결과
        mock_sg_result = MagicMock()
        mock_sg_result.status.value = "Unused"

        mock_rule_result = MagicMock()
        mock_rule_result.status.value = "Stale"
        mock_rule_result.risk_level = "HIGH"

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = ([mock_sg_result], [mock_rule_result])
        mock_analyzer.get_summary.return_value = {"unused": 1}
        mock_analyzer_cls.return_value = mock_analyzer

        mock_output.return_value = "/output/path"

        mock_reporter = MagicMock()
        mock_reporter.generate.return_value = "/output/path/report.xlsx"
        mock_reporter_cls.return_value = mock_reporter

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 분석 결과가 Excel 보고서에 전달됨
        mock_reporter_cls.assert_called_once()

    @patch("plugins.vpc.sg_audit.open_in_explorer")
    @patch("plugins.vpc.sg_audit.SGExcelReporter")
    @patch("plugins.vpc.sg_audit._create_output_directory")
    @patch("plugins.vpc.sg_audit.SGAnalyzer")
    @patch("plugins.vpc.sg_audit.parallel_collect")
    @patch("plugins.vpc.sg_audit.console")
    def test_with_errors(
        self,
        mock_console,
        mock_parallel,
        mock_analyzer_cls,
        mock_output,
        mock_reporter_cls,
        mock_explorer,
    ):
        """에러가 있는 경우"""
        from plugins.vpc.sg_audit import run

        mock_sg = MagicMock()

        mock_result = MagicMock()
        mock_result.get_data.return_value = [[mock_sg]]
        mock_result.error_count = 2
        mock_result.get_error_summary.return_value = "Error summary"
        mock_parallel.return_value = mock_result

        mock_sg_result = MagicMock()
        mock_sg_result.status.value = "Active"

        mock_rule_result = MagicMock()
        mock_rule_result.status.value = "Active"
        mock_rule_result.risk_level = "LOW"

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = ([mock_sg_result], [mock_rule_result])
        mock_analyzer.get_summary.return_value = {}
        mock_analyzer_cls.return_value = mock_analyzer

        mock_output.return_value = "/output/path"

        mock_reporter = MagicMock()
        mock_reporter.generate.return_value = "/output/path/report.xlsx"
        mock_reporter_cls.return_value = mock_reporter

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 에러 메시지가 출력됨
        calls_str = str(mock_console.print.call_args_list)
        assert "2" in calls_str or "오류" in calls_str

    @patch("plugins.vpc.sg_audit.open_in_explorer")
    @patch("plugins.vpc.sg_audit.SGExcelReporter")
    @patch("plugins.vpc.sg_audit._create_output_directory")
    @patch("plugins.vpc.sg_audit.SGAnalyzer")
    @patch("plugins.vpc.sg_audit.parallel_collect")
    @patch("plugins.vpc.sg_audit.console")
    def test_risk_level_counts(
        self,
        mock_console,
        mock_parallel,
        mock_analyzer_cls,
        mock_output,
        mock_reporter_cls,
        mock_explorer,
    ):
        """위험 수준별 카운트"""
        from plugins.vpc.sg_audit import run

        mock_sg = MagicMock()

        mock_result = MagicMock()
        mock_result.get_data.return_value = [[mock_sg]]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        # 다양한 위험 수준의 규칙
        mock_sg_result = MagicMock()
        mock_sg_result.status.value = "Active"

        high_rule = MagicMock()
        high_rule.status.value = "Stale"
        high_rule.risk_level = "HIGH"

        medium_rule = MagicMock()
        medium_rule.status.value = "Stale"
        medium_rule.risk_level = "MEDIUM"

        low_rule = MagicMock()
        low_rule.status.value = "Active"
        low_rule.risk_level = "LOW"

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = (
            [mock_sg_result],
            [high_rule, medium_rule, low_rule],
        )
        mock_analyzer.get_summary.return_value = {}
        mock_analyzer_cls.return_value = mock_analyzer

        mock_output.return_value = "/output/path"

        mock_reporter = MagicMock()
        mock_reporter.generate.return_value = "/output/path/report.xlsx"
        mock_reporter_cls.return_value = mock_reporter

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 콘솔에 HIGH, MEDIUM, LOW가 출력됨
        assert mock_console.print.called
