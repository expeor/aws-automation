"""
tests/analyzers/iam/test_unused_roles.py - 미사용 IAM Role 탐지 도구 테스트
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from functions.analyzers.iam.iam_audit_analysis.collector import (
    IAMData,
    IAMRole,
    RoleResourceRelation,
)
from functions.analyzers.iam.unused_roles import UNUSED_ROLE_THRESHOLD_DAYS, _collect_role_data, run
from functions.analyzers.iam.unused_roles_reporter import UnusedRolesReporter

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_iam_data():
    """테스트용 IAMData 생성"""
    now = datetime.now(timezone.utc)

    # Role 1: 최근 사용된 Role (사용 중)
    role1 = IAMRole(
        role_name="recently-used-role",
        role_id="AROA111",
        arn="arn:aws:iam::123456789012:role/recently-used-role",
        create_date=now,
        age_days=400,
        days_since_last_use=30,  # 30일 전 사용
        trusted_entities=["Service: lambda.amazonaws.com"],
    )

    # Role 2: 오래된 미사용 Role (365일 이상)
    role2 = IAMRole(
        role_name="unused-role",
        role_id="AROA222",
        arn="arn:aws:iam::123456789012:role/unused-role",
        create_date=now,
        age_days=500,
        days_since_last_use=400,  # 400일 전 사용
        trusted_entities=["Service: ec2.amazonaws.com"],
        attached_policies=["AmazonEC2ReadOnlyAccess"],
    )

    # Role 3: 한 번도 사용된 적 없는 Role
    role3 = IAMRole(
        role_name="never-used-role",
        role_id="AROA333",
        arn="arn:aws:iam::123456789012:role/never-used-role",
        create_date=now,
        age_days=400,
        days_since_last_use=-1,  # 사용 기록 없음
        trusted_entities=["AWS: arn:aws:iam::111111111111:root"],
    )

    # Role 4: Service-linked Role (분석 제외)
    role4 = IAMRole(
        role_name="AWSServiceRoleForElasticLoadBalancing",
        role_id="AROA444",
        arn="arn:aws:iam::123456789012:role/aws-service-role/elasticloadbalancing.amazonaws.com/AWSServiceRoleForElasticLoadBalancing",
        create_date=now,
        path="/aws-service-role/elasticloadbalancing.amazonaws.com/",
        age_days=500,
        days_since_last_use=-1,
        is_service_linked=True,
    )

    # Role 5: 새로 생성된 미사용 Role (365일 미만이라 제외)
    role5 = IAMRole(
        role_name="new-unused-role",
        role_id="AROA555",
        arn="arn:aws:iam::123456789012:role/new-unused-role",
        create_date=now,
        age_days=100,  # 생성된 지 100일
        days_since_last_use=-1,  # 사용 기록 없음
    )

    # Role 6: Admin 권한을 가진 미사용 Role
    role6 = IAMRole(
        role_name="admin-unused-role",
        role_id="AROA666",
        arn="arn:aws:iam::123456789012:role/admin-unused-role",
        create_date=now,
        age_days=400,
        days_since_last_use=380,
        has_admin_access=True,
        attached_policies=["AdministratorAccess"],
        connected_resources=[
            RoleResourceRelation(
                resource_type="AWS::EC2::Instance",
                resource_name="i-12345678",
                resource_id="i-12345678",
            )
        ],
    )

    return IAMData(
        account_id="123456789012",
        account_name="test-account",
        roles=[role1, role2, role3, role4, role5, role6],
        config_enabled=True,
    )


@pytest.fixture
def mock_ctx():
    """테스트용 ExecutionContext Mock"""
    ctx = MagicMock()
    ctx.profile_name = "test-profile"
    ctx.is_sso_session.return_value = False
    return ctx


# =============================================================================
# UnusedRolesReporter Tests
# =============================================================================


class TestUnusedRolesReporter:
    """UnusedRolesReporter 테스트"""

    def test_analyze_unused_roles(self, mock_iam_data):
        """미사용 Role 탐지 테스트"""
        reporter = UnusedRolesReporter([mock_iam_data], threshold_days=365)
        analysis = reporter.analysis

        # 미사용 Role: unused-role, never-used-role, admin-unused-role
        # (recently-used-role: 30일 전 사용, service-linked: 제외, new-unused-role: 100일 미만)
        assert len(analysis.unused_roles) == 3

        unused_names = {r.role_name for r in analysis.unused_roles}
        assert "unused-role" in unused_names
        assert "never-used-role" in unused_names
        assert "admin-unused-role" in unused_names

    def test_exclude_service_linked_roles(self, mock_iam_data):
        """Service-linked Role 제외 테스트"""
        reporter = UnusedRolesReporter([mock_iam_data], threshold_days=365)
        analysis = reporter.analysis

        # Service-linked Role이 포함되지 않아야 함
        unused_names = {r.role_name for r in analysis.unused_roles}
        assert "AWSServiceRoleForElasticLoadBalancing" not in unused_names

    def test_exclude_new_roles(self, mock_iam_data):
        """생성된 지 365일 미만인 Role 제외 테스트"""
        reporter = UnusedRolesReporter([mock_iam_data], threshold_days=365)
        analysis = reporter.analysis

        # 새로 생성된 Role이 포함되지 않아야 함
        unused_names = {r.role_name for r in analysis.unused_roles}
        assert "new-unused-role" not in unused_names

    def test_analyze_role_stats(self, mock_iam_data):
        """계정 통계 테스트"""
        reporter = UnusedRolesReporter([mock_iam_data], threshold_days=365)
        analysis = reporter.analysis

        assert len(analysis.role_stats) == 1
        stats = analysis.role_stats[0]

        assert stats.total_roles == 6
        assert stats.service_linked_roles == 1
        assert stats.unused_roles == 3
        assert stats.config_enabled is True

    def test_connected_resources_included(self, mock_iam_data):
        """연결된 리소스 포함 테스트"""
        reporter = UnusedRolesReporter([mock_iam_data], threshold_days=365)
        analysis = reporter.analysis

        admin_role = next(r for r in analysis.unused_roles if r.role_name == "admin-unused-role")
        assert "AWS::EC2::Instance" in admin_role.connected_resources

    def test_generate_creates_excel(self, mock_iam_data, tmp_path):
        """Excel 파일 생성 테스트"""
        reporter = UnusedRolesReporter([mock_iam_data], threshold_days=365)
        filepath = reporter.generate(str(tmp_path))

        assert filepath.endswith(".xlsx")
        assert "iam_unused_roles_" in filepath

    def test_custom_threshold(self):
        """커스텀 임계값 테스트"""
        now = datetime.now(timezone.utc)

        role = IAMRole(
            role_name="test-role",
            role_id="AROA001",
            arn="arn:aws:iam::123456789012:role/test-role",
            create_date=now,
            age_days=200,
            days_since_last_use=180,
        )

        data = IAMData(
            account_id="123456789012",
            account_name="test",
            roles=[role],
        )

        # 365일 임계값: 제외됨 (age_days=200 < 365)
        reporter_365 = UnusedRolesReporter([data], threshold_days=365)
        assert len(reporter_365.analysis.unused_roles) == 0

        # 150일 임계값: 포함됨 (age_days=200 >= 150, days_since_last_use=180 >= 150)
        reporter_150 = UnusedRolesReporter([data], threshold_days=150)
        assert len(reporter_150.analysis.unused_roles) == 1


class TestUnusedRoleThreshold:
    """UNUSED_ROLE_THRESHOLD_DAYS 테스트"""

    def test_threshold_value(self):
        """임계값이 365일인지 확인"""
        assert UNUSED_ROLE_THRESHOLD_DAYS == 365

    def test_role_at_threshold_boundary(self):
        """경계값 테스트 (364일 vs 365일)"""
        now = datetime.now(timezone.utc)

        # 364일 사용 안 함 (경계 미만)
        role_364 = IAMRole(
            role_name="role-364",
            role_id="AROA364",
            arn="arn:aws:iam::123456789012:role/role-364",
            create_date=now,
            age_days=400,
            days_since_last_use=364,
        )

        # 365일 사용 안 함 (경계)
        role_365 = IAMRole(
            role_name="role-365",
            role_id="AROA365",
            arn="arn:aws:iam::123456789012:role/role-365",
            create_date=now,
            age_days=400,
            days_since_last_use=365,
        )

        data = IAMData(
            account_id="123456789012",
            account_name="test",
            roles=[role_364, role_365],
        )

        reporter = UnusedRolesReporter([data], threshold_days=365)
        analysis = reporter.analysis

        # 365일 Role만 Unused Roles에 포함
        assert len(analysis.unused_roles) == 1
        assert analysis.unused_roles[0].role_name == "role-365"


class TestMultipleAccounts:
    """멀티 계정 테스트"""

    def test_multiple_accounts_analysis(self):
        """멀티 계정 분석 테스트"""
        now = datetime.now(timezone.utc)

        # 계정 1
        data1 = IAMData(
            account_id="111111111111",
            account_name="account-1",
            roles=[
                IAMRole(
                    role_name="unused-role-1",
                    role_id="AROA1",
                    arn="arn:aws:iam::111111111111:role/unused-role-1",
                    create_date=now,
                    age_days=400,
                    days_since_last_use=400,
                )
            ],
            config_enabled=True,
        )

        # 계정 2
        data2 = IAMData(
            account_id="222222222222",
            account_name="account-2",
            roles=[
                IAMRole(
                    role_name="unused-role-2",
                    role_id="AROA2",
                    arn="arn:aws:iam::222222222222:role/unused-role-2",
                    create_date=now,
                    age_days=500,
                    days_since_last_use=-1,
                )
            ],
            config_enabled=False,
        )

        reporter = UnusedRolesReporter([data1, data2], threshold_days=365)
        analysis = reporter.analysis

        assert len(analysis.role_stats) == 2
        assert len(analysis.unused_roles) == 2

        # Config 상태 확인
        stats_1 = next(s for s in analysis.role_stats if s.account_id == "111111111111")
        stats_2 = next(s for s in analysis.role_stats if s.account_id == "222222222222")
        assert stats_1.config_enabled is True
        assert stats_2.config_enabled is False


# =============================================================================
# Collect Function Tests
# =============================================================================


class TestCollectRoleData:
    """_collect_role_data 콜백 테스트"""

    @patch("functions.analyzers.iam.unused_roles.IAMCollector")
    def test_collect_returns_iam_data(self, mock_collector_class):
        """IAMCollector를 사용하여 데이터 수집"""
        mock_session = MagicMock()
        mock_data = MagicMock(spec=IAMData)

        mock_collector = MagicMock()
        mock_collector.collect.return_value = mock_data
        mock_collector_class.return_value = mock_collector

        result = _collect_role_data(mock_session, "123456789012", "test-account", "us-east-1")

        assert result == mock_data
        mock_collector.collect.assert_called_once_with(mock_session, "123456789012", "test-account")


# =============================================================================
# Run Function Tests
# =============================================================================


class TestRun:
    """run() 함수 테스트"""

    @patch("functions.analyzers.iam.unused_roles.open_in_explorer")
    @patch("functions.analyzers.iam.unused_roles.UnusedRolesReporter")
    @patch("functions.analyzers.iam.unused_roles.parallel_collect")
    def test_run_with_no_data(self, mock_parallel, mock_reporter, mock_explorer, mock_ctx, capsys):
        """데이터 없을 때 처리"""
        mock_result = MagicMock()
        mock_result.get_data.return_value = []
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        run(mock_ctx)

        captured = capsys.readouterr()
        assert "수집된 IAM 데이터가 없습니다" in captured.out
        mock_reporter.assert_not_called()

    @patch("functions.analyzers.iam.unused_roles.open_in_explorer")
    @patch("core.shared.io.output.print_report_complete")
    @patch("functions.analyzers.iam.unused_roles.UnusedRolesReporter")
    @patch("functions.analyzers.iam.unused_roles.parallel_collect")
    @patch("functions.analyzers.iam.unused_roles.OutputPath")
    def test_run_with_data(
        self, mock_output_path, mock_parallel, mock_reporter, mock_print, mock_explorer, mock_ctx, mock_iam_data
    ):
        """데이터 있을 때 정상 처리"""
        mock_result = MagicMock()
        mock_result.get_data.return_value = [mock_iam_data]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        mock_output_path.return_value.sub.return_value.with_date.return_value.build.return_value = "/tmp/output"

        mock_reporter_instance = MagicMock()
        mock_reporter_instance.generate.return_value = "/tmp/output/report.xlsx"
        mock_reporter.return_value = mock_reporter_instance

        run(mock_ctx)

        mock_reporter.assert_called_once()
        mock_reporter_instance.generate.assert_called_once()

    @patch("functions.analyzers.iam.unused_roles.open_in_explorer")
    @patch("core.shared.io.output.print_report_complete")
    @patch("functions.analyzers.iam.unused_roles.UnusedRolesReporter")
    @patch("functions.analyzers.iam.unused_roles.parallel_collect")
    @patch("functions.analyzers.iam.unused_roles.OutputPath")
    def test_run_with_errors(
        self, mock_output_path, mock_parallel, mock_reporter, mock_print, mock_explorer, mock_ctx, mock_iam_data, capsys
    ):
        """에러 발생 시 처리"""
        mock_result = MagicMock()
        mock_result.get_data.return_value = [mock_iam_data]
        mock_result.error_count = 2
        mock_result.get_error_summary.return_value = "Error 1, Error 2"
        mock_parallel.return_value = mock_result

        mock_output_path.return_value.sub.return_value.with_date.return_value.build.return_value = "/tmp/output"

        mock_reporter_instance = MagicMock()
        mock_reporter_instance.generate.return_value = "/tmp/output/report.xlsx"
        mock_reporter.return_value = mock_reporter_instance

        run(mock_ctx)

        captured = capsys.readouterr()
        assert "일부 오류 발생: 2건" in captured.out

    @patch("functions.analyzers.iam.unused_roles.open_in_explorer")
    @patch("core.shared.io.output.print_report_complete")
    @patch("functions.analyzers.iam.unused_roles.UnusedRolesReporter")
    @patch("functions.analyzers.iam.unused_roles.parallel_collect")
    @patch("functions.analyzers.iam.unused_roles.OutputPath")
    def test_run_no_unused_roles(
        self, mock_output_path, mock_parallel, mock_reporter, mock_print, mock_explorer, mock_ctx, capsys
    ):
        """미사용 Role 없을 때 메시지 출력"""
        now = datetime.now(timezone.utc)

        # 최근 사용된 Role만 있는 데이터
        data = IAMData(
            account_id="123456789012",
            account_name="test-account",
            roles=[
                IAMRole(
                    role_name="active-role",
                    role_id="AROA001",
                    arn="arn:aws:iam::123456789012:role/active-role",
                    create_date=now,
                    age_days=400,
                    days_since_last_use=30,
                )
            ],
        )

        mock_result = MagicMock()
        mock_result.get_data.return_value = [data]
        mock_result.error_count = 0
        mock_parallel.return_value = mock_result

        mock_output_path.return_value.sub.return_value.with_date.return_value.build.return_value = "/tmp/output"

        mock_reporter_instance = MagicMock()
        mock_reporter_instance.generate.return_value = "/tmp/output/report.xlsx"
        mock_reporter.return_value = mock_reporter_instance

        run(mock_ctx)

        captured = capsys.readouterr()
        assert "미사용 Role 없음" in captured.out
