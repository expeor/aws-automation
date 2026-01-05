"""
tests/plugins/iam/test_plugins_iam_audit.py - IAM Audit 테스트
"""

from unittest.mock import MagicMock, patch


class TestCollectAndAnalyze:
    """_collect_and_analyze 함수 테스트"""

    @patch("plugins.iam.iam_audit.IAMAnalyzer")
    @patch("plugins.iam.iam_audit.IAMCollector")
    def test_collect_and_analyze(self, mock_collector_cls, mock_analyzer_cls):
        """정상적인 수집 및 분석"""
        from plugins.iam.iam_audit import _collect_and_analyze

        # Collector 설정
        mock_collector = MagicMock()
        mock_iam_data = MagicMock()
        mock_collector.collect.return_value = mock_iam_data
        mock_collector_cls.return_value = mock_collector

        # Analyzer 설정
        mock_analyzer = MagicMock()
        mock_analysis_result = {"users": [], "roles": []}
        mock_stats = {"total_users": 5, "total_roles": 10}
        mock_analyzer.analyze.return_value = mock_analysis_result
        mock_analyzer.get_summary_stats.return_value = mock_stats
        mock_analyzer_cls.return_value = mock_analyzer

        mock_session = MagicMock()
        result = _collect_and_analyze(
            mock_session, "123456789012", "test-account", "us-east-1"
        )

        assert result is not None
        assert result == (mock_analysis_result, mock_stats)
        mock_collector.collect.assert_called_once_with(
            mock_session, "123456789012", "test-account"
        )


class TestPrintSummary:
    """_print_summary 함수 테스트"""

    @patch("plugins.iam.iam_audit.console")
    def test_empty_stats_list(self, mock_console):
        """빈 통계 리스트"""
        from plugins.iam.iam_audit import _print_summary

        _print_summary([])

        # 콘솔 출력이 호출되었는지 확인
        assert mock_console.print.called

    @patch("plugins.iam.iam_audit.console")
    def test_with_critical_issues(self, mock_console):
        """Critical 이슈가 있는 경우"""
        from plugins.iam.iam_audit import _print_summary

        stats = [
            {
                "total_users": 10,
                "users_without_mfa": 3,
                "inactive_users": 2,
                "total_active_keys": 15,
                "old_keys": 5,
                "unused_keys": 2,
                "total_roles": 20,
                "unused_roles": 5,
                "admin_roles": 3,
                "critical_issues": 2,
                "high_issues": 5,
                "medium_issues": 10,
                "root_access_key": True,
                "root_mfa": False,
            }
        ]

        _print_summary(stats)

        # CRITICAL 관련 출력 확인
        calls_str = str(mock_console.print.call_args_list)
        assert "CRITICAL" in calls_str or "critical" in calls_str.lower()

    @patch("plugins.iam.iam_audit.console")
    def test_without_critical_issues(self, mock_console):
        """Critical 이슈가 없는 경우"""
        from plugins.iam.iam_audit import _print_summary

        stats = [
            {
                "total_users": 10,
                "users_without_mfa": 0,
                "inactive_users": 0,
                "total_active_keys": 15,
                "old_keys": 0,
                "unused_keys": 0,
                "total_roles": 20,
                "unused_roles": 0,
                "admin_roles": 0,
                "critical_issues": 0,
                "high_issues": 0,
                "medium_issues": 0,
                "root_access_key": False,
                "root_mfa": True,
            }
        ]

        _print_summary(stats)

        # 콘솔 출력이 호출되었는지 확인
        assert mock_console.print.called

    @patch("plugins.iam.iam_audit.console")
    def test_multiple_accounts_aggregation(self, mock_console):
        """여러 계정 통계 집계"""
        from plugins.iam.iam_audit import _print_summary

        stats = [
            {
                "total_users": 5,
                "users_without_mfa": 1,
                "inactive_users": 1,
                "total_active_keys": 8,
                "old_keys": 2,
                "unused_keys": 1,
                "total_roles": 10,
                "unused_roles": 2,
                "admin_roles": 1,
                "critical_issues": 1,
                "high_issues": 2,
                "medium_issues": 5,
                "root_access_key": False,
                "root_mfa": True,
            },
            {
                "total_users": 5,
                "users_without_mfa": 2,
                "inactive_users": 1,
                "total_active_keys": 7,
                "old_keys": 3,
                "unused_keys": 1,
                "total_roles": 10,
                "unused_roles": 3,
                "admin_roles": 2,
                "critical_issues": 0,
                "high_issues": 3,
                "medium_issues": 5,
                "root_access_key": True,
                "root_mfa": False,
            },
        ]

        _print_summary(stats)

        # 집계된 값이 출력됨
        assert mock_console.print.called

    @patch("plugins.iam.iam_audit.console")
    def test_root_access_key_warning(self, mock_console):
        """Root Access Key 경고"""
        from plugins.iam.iam_audit import _print_summary

        stats = [
            {
                "total_users": 5,
                "users_without_mfa": 0,
                "inactive_users": 0,
                "total_active_keys": 5,
                "old_keys": 0,
                "unused_keys": 0,
                "total_roles": 10,
                "unused_roles": 0,
                "admin_roles": 0,
                "critical_issues": 1,
                "high_issues": 0,
                "medium_issues": 0,
                "root_access_key": True,
                "root_mfa": True,
            }
        ]

        _print_summary(stats)

        # Root Access Key 관련 출력 확인
        calls_str = str(mock_console.print.call_args_list)
        assert "Root" in calls_str or "CRITICAL" in calls_str


class TestCreateOutputDirectory:
    """_create_output_directory 함수 테스트"""

    @patch("plugins.iam.iam_audit.OutputPath")
    def test_with_sso_session(self, mock_output_path):
        """SSO 세션이 있는 경우"""
        from plugins.iam.iam_audit import _create_output_directory

        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = True
        mock_ctx.accounts = [MagicMock(id="123456789012")]

        mock_path_instance = MagicMock()
        mock_path_instance.sub.return_value = mock_path_instance
        mock_path_instance.with_date.return_value = mock_path_instance
        mock_path_instance.build.return_value = (
            "/output/123456789012/iam/security/2024-01-01"
        )
        mock_output_path.return_value = mock_path_instance

        _create_output_directory(mock_ctx)

        mock_output_path.assert_called_once_with("123456789012")
        mock_path_instance.sub.assert_called_once_with("iam", "security")

    @patch("plugins.iam.iam_audit.OutputPath")
    def test_with_profile_name(self, mock_output_path):
        """프로파일명이 있는 경우"""
        from plugins.iam.iam_audit import _create_output_directory

        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = False
        mock_ctx.profile_name = "my-profile"

        mock_path_instance = MagicMock()
        mock_path_instance.sub.return_value = mock_path_instance
        mock_path_instance.with_date.return_value = mock_path_instance
        mock_path_instance.build.return_value = (
            "/output/my-profile/iam/security/2024-01-01"
        )
        mock_output_path.return_value = mock_path_instance

        _create_output_directory(mock_ctx)

        mock_output_path.assert_called_once_with("my-profile")

    @patch("plugins.iam.iam_audit.OutputPath")
    def test_default_identifier(self, mock_output_path):
        """기본 식별자 사용"""
        from plugins.iam.iam_audit import _create_output_directory

        mock_ctx = MagicMock()
        mock_ctx.is_sso_session.return_value = False
        mock_ctx.profile_name = None

        mock_path_instance = MagicMock()
        mock_path_instance.sub.return_value = mock_path_instance
        mock_path_instance.with_date.return_value = mock_path_instance
        mock_path_instance.build.return_value = "/output/default/iam/security/2024-01-01"
        mock_output_path.return_value = mock_path_instance

        _create_output_directory(mock_ctx)

        mock_output_path.assert_called_once_with("default")


class TestRun:
    """run 함수 테스트"""

    @patch("plugins.iam.iam_audit.open_in_explorer")
    @patch("plugins.iam.iam_audit.IAMExcelReporter")
    @patch("plugins.iam.iam_audit._create_output_directory")
    @patch("plugins.iam.iam_audit._print_summary")
    @patch("plugins.iam.iam_audit.parallel_collect")
    @patch("plugins.iam.iam_audit.console")
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
        from plugins.iam.iam_audit import run

        mock_result = MagicMock()
        mock_result.get_data.return_value = [None, None]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 결과가 없으면 Excel 보고서가 생성되지 않음
        mock_reporter.assert_not_called()

    @patch("plugins.iam.iam_audit.open_in_explorer")
    @patch("plugins.iam.iam_audit.IAMExcelReporter")
    @patch("plugins.iam.iam_audit._create_output_directory")
    @patch("plugins.iam.iam_audit._print_summary")
    @patch("plugins.iam.iam_audit.parallel_collect")
    @patch("plugins.iam.iam_audit.console")
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
        from plugins.iam.iam_audit import run

        mock_analysis = {"users": [], "roles": []}
        mock_stats = {"total_users": 5}

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

    @patch("plugins.iam.iam_audit.open_in_explorer")
    @patch("plugins.iam.iam_audit.IAMExcelReporter")
    @patch("plugins.iam.iam_audit._create_output_directory")
    @patch("plugins.iam.iam_audit._print_summary")
    @patch("plugins.iam.iam_audit.parallel_collect")
    @patch("plugins.iam.iam_audit.console")
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
        from plugins.iam.iam_audit import run

        mock_analysis = {"users": []}
        mock_stats = {"total_users": 5}

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

    @patch("plugins.iam.iam_audit.open_in_explorer")
    @patch("plugins.iam.iam_audit.IAMExcelReporter")
    @patch("plugins.iam.iam_audit._create_output_directory")
    @patch("plugins.iam.iam_audit._print_summary")
    @patch("plugins.iam.iam_audit.parallel_collect")
    @patch("plugins.iam.iam_audit.console")
    def test_multiple_accounts(
        self,
        mock_console,
        mock_parallel,
        mock_print,
        mock_output,
        mock_reporter_cls,
        mock_explorer,
    ):
        """여러 계정 처리"""
        from plugins.iam.iam_audit import run

        mock_result = MagicMock()
        mock_result.get_data.return_value = [
            ({"users": []}, {"total_users": 5}),
            ({"users": []}, {"total_users": 3}),
            None,  # 일부 실패
        ]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        mock_output.return_value = "/output/path"

        mock_reporter = MagicMock()
        mock_reporter.generate.return_value = "/output/path/report.xlsx"
        mock_reporter_cls.return_value = mock_reporter

        mock_ctx = MagicMock()

        run(mock_ctx)

        # 2개 계정만 처리됨
        calls = mock_print.call_args_list
        # _print_summary가 2개의 stats로 호출됨
        assert len(calls[0][0][0]) == 2
