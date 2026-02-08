"""tests/analyzers/sso/test_sso_audit.py - SSO 보안 감사 테스트"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from functions.analyzers.sso.sso_audit import _create_output_directory, _print_summary, run

# =============================================================================
# _print_summary 테스트
# =============================================================================


class TestPrintSummary:
    """분석 결과 요약 출력 테스트"""

    def test_empty_stats(self):
        """빈 통계 출력"""
        _print_summary([])

    def test_single_stats(self):
        """단일 통계 출력"""
        stats = [
            {
                "total_users": 10,
                "total_groups": 3,
                "total_permission_sets": 5,
                "users_with_admin": 2,
                "users_no_assignment": 1,
                "admin_permission_sets": 1,
                "high_risk_permission_sets": 2,
                "empty_groups": 0,
                "critical_issues": 0,
                "high_issues": 1,
                "medium_issues": 2,
                "low_issues": 3,
            }
        ]
        # Should not raise
        _print_summary(stats)

    def test_multiple_stats_aggregation(self):
        """여러 통계 합산"""
        stats = [
            {
                "total_users": 5,
                "total_groups": 2,
                "total_permission_sets": 3,
                "users_with_admin": 1,
                "users_no_assignment": 0,
                "admin_permission_sets": 1,
                "high_risk_permission_sets": 0,
                "empty_groups": 1,
                "critical_issues": 1,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
            },
            {
                "total_users": 8,
                "total_groups": 4,
                "total_permission_sets": 2,
                "users_with_admin": 0,
                "users_no_assignment": 2,
                "admin_permission_sets": 0,
                "high_risk_permission_sets": 1,
                "empty_groups": 2,
                "critical_issues": 0,
                "high_issues": 3,
                "medium_issues": 1,
                "low_issues": 5,
            },
        ]
        # Should aggregate and not raise
        _print_summary(stats)

    def test_stats_with_zero_values(self):
        """모든 값이 0인 통계"""
        stats = [
            {
                "total_users": 0,
                "total_groups": 0,
                "total_permission_sets": 0,
                "users_with_admin": 0,
                "users_no_assignment": 0,
                "admin_permission_sets": 0,
                "high_risk_permission_sets": 0,
                "empty_groups": 0,
                "critical_issues": 0,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0,
            }
        ]
        _print_summary(stats)


# =============================================================================
# _create_output_directory 테스트
# =============================================================================


class TestCreateOutputDirectory:
    """출력 디렉토리 생성 테스트"""

    def test_with_sso_session(self, mock_context):
        """SSO 세션 컨텍스트에서 출력 경로 생성"""
        mock_context.is_sso_session = MagicMock(return_value=True)

        output_path = _create_output_directory(mock_context)
        assert isinstance(output_path, str)
        assert "sso" in output_path
        assert "inventory" in output_path

    def test_with_profile(self, mock_context):
        """프로파일 기반 컨텍스트에서 출력 경로 생성"""
        mock_context.accounts = []
        mock_context.profile_name = "my-profile"

        output_path = _create_output_directory(mock_context)
        assert isinstance(output_path, str)
        assert "my-profile" in output_path


# =============================================================================
# run 통합 테스트
# =============================================================================


class TestRun:
    """SSO 감사 실행 통합 테스트"""

    @patch("functions.analyzers.sso.sso_audit.open_in_explorer")
    @patch("functions.analyzers.sso.sso_audit.SSOExcelReporter")
    @patch("functions.analyzers.sso.sso_audit.SSOAnalyzer")
    @patch("functions.analyzers.sso.sso_audit.SSOCollector")
    @patch("functions.analyzers.sso.sso_audit.SessionIterator")
    @patch("functions.analyzers.sso.sso_audit.get_client")
    def test_run_successful(
        self,
        mock_get_client,
        mock_session_iter,
        mock_collector_cls,
        mock_analyzer_cls,
        mock_reporter_cls,
        mock_open_explorer,
        mock_context,
    ):
        """정상 수집 및 보고서 생성"""
        # SessionIterator 모킹
        mock_session = MagicMock()
        mock_iterator = MagicMock()
        mock_iterator.__enter__ = MagicMock(return_value=mock_iterator)
        mock_iterator.__exit__ = MagicMock(return_value=None)
        mock_iterator.__iter__ = MagicMock(return_value=iter([(mock_session, "123456789012", "ap-northeast-2")]))
        mock_session_iter.return_value = mock_iterator

        # STS 모킹
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_get_client.return_value = mock_sts

        # Collector 모킹
        mock_collector = MagicMock()
        mock_collector.collect.return_value = MagicMock()  # SSOData
        mock_collector.errors = []
        mock_collector_cls.return_value = mock_collector

        # Analyzer 모킹
        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = MagicMock()  # analysis result
        mock_analyzer.get_summary_stats.return_value = {
            "total_users": 5,
            "total_groups": 2,
            "total_permission_sets": 3,
            "users_with_admin": 0,
            "users_no_assignment": 0,
            "admin_permission_sets": 0,
            "high_risk_permission_sets": 0,
            "empty_groups": 0,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "low_issues": 0,
        }
        mock_analyzer_cls.return_value = mock_analyzer

        # Reporter 모킹
        mock_reporter = MagicMock()
        mock_reporter.generate.return_value = "/tmp/sso_report.xlsx"
        mock_reporter_cls.return_value = mock_reporter

        with patch("core.shared.io.output.print_report_complete"):
            run(mock_context)

        mock_collector.collect.assert_called_once()
        mock_analyzer.analyze.assert_called_once()
        mock_reporter.generate.assert_called_once()

    @patch("functions.analyzers.sso.sso_audit.SSOCollector")
    @patch("functions.analyzers.sso.sso_audit.SessionIterator")
    @patch("functions.analyzers.sso.sso_audit.get_client")
    def test_run_no_data(
        self,
        mock_get_client,
        mock_session_iter,
        mock_collector_cls,
        mock_context,
    ):
        """데이터 수집 실패 시 조기 종료"""
        # SessionIterator 모킹
        mock_session = MagicMock()
        mock_iterator = MagicMock()
        mock_iterator.__enter__ = MagicMock(return_value=mock_iterator)
        mock_iterator.__exit__ = MagicMock(return_value=None)
        mock_iterator.__iter__ = MagicMock(return_value=iter([(mock_session, "123456789012", "ap-northeast-2")]))
        mock_session_iter.return_value = mock_iterator

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_get_client.return_value = mock_sts

        # Collector returns None (no access)
        mock_collector = MagicMock()
        mock_collector.collect.return_value = None
        mock_collector.errors = []
        mock_collector_cls.return_value = mock_collector

        # Should return early without error
        run(mock_context)

    @patch("functions.analyzers.sso.sso_audit.SSOCollector")
    @patch("functions.analyzers.sso.sso_audit.SessionIterator")
    @patch("functions.analyzers.sso.sso_audit.get_client")
    def test_run_access_denied(
        self,
        mock_get_client,
        mock_session_iter,
        mock_collector_cls,
        mock_context,
    ):
        """AccessDeniedException 처리"""
        from botocore.exceptions import ClientError

        mock_session = MagicMock()
        mock_iterator = MagicMock()
        mock_iterator.__enter__ = MagicMock(return_value=mock_iterator)
        mock_iterator.__exit__ = MagicMock(return_value=None)
        mock_iterator.__iter__ = MagicMock(return_value=iter([(mock_session, "123456789012", "ap-northeast-2")]))
        mock_session_iter.return_value = mock_iterator

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Not authorized"}},
            "GetCallerIdentity",
        )
        mock_get_client.return_value = mock_sts

        mock_collector = MagicMock()
        mock_collector.errors = []
        mock_collector_cls.return_value = mock_collector

        # Should handle error gracefully
        run(mock_context)
