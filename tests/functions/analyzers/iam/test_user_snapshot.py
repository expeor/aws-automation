"""
tests/analyzers/iam/test_user_snapshot.py - IAM User Snapshot 도구 테스트
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from functions.analyzers.iam.iam_audit_analysis.collector import (
    GitCredential,
    IAMAccessKey,
    IAMData,
    IAMUser,
)
from functions.analyzers.iam.user_snapshot import _collect_user_data, run
from functions.analyzers.iam.user_snapshot_reporter import (
    OLD_KEY_THRESHOLD_DAYS,
    UserSnapshotReporter,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_iam_data():
    """테스트용 IAMData 생성"""
    now = datetime.now(timezone.utc)

    # User 1: 정상 사용자 (콘솔 + MFA + 새 키)
    user1 = IAMUser(
        user_name="active-user",
        user_id="AIDA123",
        arn="arn:aws:iam::123456789012:user/active-user",
        create_date=now,
        has_console_access=True,
        has_mfa=True,
        active_key_count=1,
        access_keys=[
            IAMAccessKey(
                user_name="active-user",
                access_key_id="AKIA111",
                status="Active",
                create_date=now,
                age_days=30,
                days_since_last_use=5,
            )
        ],
    )

    # User 2: 오래된 키 보유 사용자
    user2 = IAMUser(
        user_name="old-key-user",
        user_id="AIDA456",
        arn="arn:aws:iam::123456789012:user/old-key-user",
        create_date=now,
        has_console_access=True,
        has_mfa=False,
        active_key_count=1,
        access_keys=[
            IAMAccessKey(
                user_name="old-key-user",
                access_key_id="AKIA222",
                status="Active",
                create_date=now,
                age_days=120,  # 90일 초과
                days_since_last_use=60,
            )
        ],
    )

    # User 3: 비활성 사용자 (자격 증명 없음)
    user3 = IAMUser(
        user_name="inactive-user",
        user_id="AIDA789",
        arn="arn:aws:iam::123456789012:user/inactive-user",
        create_date=now,
        has_console_access=False,
        has_mfa=False,
        active_key_count=0,
        active_git_credential_count=0,
        access_keys=[],
    )

    # User 4: Git Credential만 보유한 사용자
    user4 = IAMUser(
        user_name="git-user",
        user_id="AIDA012",
        arn="arn:aws:iam::123456789012:user/git-user",
        create_date=now,
        has_console_access=False,
        has_mfa=False,
        active_key_count=0,
        active_git_credential_count=1,
        git_credentials=[
            GitCredential(
                user_name="git-user",
                service_user_name="git-user-at-123456789012",
                service_specific_credential_id="ACCA123",
                status="Active",
                create_date=now,
                age_days=45,
            )
        ],
    )

    return IAMData(
        account_id="123456789012",
        account_name="test-account",
        users=[user1, user2, user3, user4],
    )


@pytest.fixture
def mock_ctx():
    """테스트용 ExecutionContext Mock"""
    ctx = MagicMock()
    ctx.profile_name = "test-profile"
    ctx.is_sso_session.return_value = False
    return ctx


# =============================================================================
# UserSnapshotReporter Tests
# =============================================================================


class TestUserSnapshotReporter:
    """UserSnapshotReporter 테스트"""

    def test_analyze_old_access_keys(self, mock_iam_data):
        """오래된 Access Key 탐지 테스트"""
        reporter = UserSnapshotReporter([mock_iam_data])
        analysis = reporter.analysis

        # 90일 이상 된 키가 1개 있어야 함
        assert len(analysis.old_access_keys) == 1
        assert analysis.old_access_keys[0].user_name == "old-key-user"
        assert analysis.old_access_keys[0].age_days == 120

    def test_analyze_inactive_users(self, mock_iam_data):
        """비활성 사용자 탐지 테스트"""
        reporter = UserSnapshotReporter([mock_iam_data])
        analysis = reporter.analysis

        # 비활성 사용자가 1명 있어야 함 (inactive-user)
        assert len(analysis.inactive_users) == 1
        assert analysis.inactive_users[0].user_name == "inactive-user"

    def test_analyze_user_snapshots(self, mock_iam_data):
        """전체 사용자 스냅샷 테스트"""
        reporter = UserSnapshotReporter([mock_iam_data])
        analysis = reporter.analysis

        # 4명의 사용자가 있어야 함
        assert len(analysis.user_snapshots) == 4

    def test_analyze_account_stats(self, mock_iam_data):
        """계정 통계 테스트"""
        reporter = UserSnapshotReporter([mock_iam_data])
        analysis = reporter.analysis

        assert len(analysis.account_stats) == 1
        stats = analysis.account_stats[0]

        assert stats.total_users == 4
        assert stats.users_with_console == 2  # active-user, old-key-user
        assert stats.users_with_mfa == 1  # active-user
        assert stats.old_access_keys == 1  # old-key-user
        assert stats.inactive_users == 1  # inactive-user
        assert stats.users_with_git_credentials == 1  # git-user

    def test_generate_creates_excel(self, mock_iam_data, tmp_path):
        """Excel 파일 생성 테스트"""
        reporter = UserSnapshotReporter([mock_iam_data])
        filepath = reporter.generate(str(tmp_path))

        assert filepath.endswith(".xlsx")
        assert "iam_user_snapshot_" in filepath

    def test_multiple_accounts(self):
        """멀티 계정 분석 테스트"""
        now = datetime.now(timezone.utc)

        # 계정 1
        data1 = IAMData(
            account_id="111111111111",
            account_name="account-1",
            users=[
                IAMUser(
                    user_name="user1",
                    user_id="AIDA1",
                    arn="arn:aws:iam::111111111111:user/user1",
                    create_date=now,
                    has_console_access=False,
                    active_key_count=0,
                    active_git_credential_count=0,
                )
            ],
        )

        # 계정 2
        data2 = IAMData(
            account_id="222222222222",
            account_name="account-2",
            users=[
                IAMUser(
                    user_name="user2",
                    user_id="AIDA2",
                    arn="arn:aws:iam::222222222222:user/user2",
                    create_date=now,
                    has_console_access=False,
                    active_key_count=0,
                    active_git_credential_count=0,
                )
            ],
        )

        reporter = UserSnapshotReporter([data1, data2])
        analysis = reporter.analysis

        assert len(analysis.account_stats) == 2
        assert len(analysis.inactive_users) == 2  # 둘 다 비활성


class TestOldKeyThreshold:
    """OLD_KEY_THRESHOLD_DAYS 테스트"""

    def test_threshold_value(self):
        """임계값이 90일인지 확인"""
        assert OLD_KEY_THRESHOLD_DAYS == 90

    def test_key_at_threshold_boundary(self):
        """경계값 테스트 (89일 vs 90일)"""
        now = datetime.now(timezone.utc)

        # 89일 된 키 (경계 미만)
        user_89 = IAMUser(
            user_name="user-89",
            user_id="AIDA89",
            arn="arn:aws:iam::123456789012:user/user-89",
            create_date=now,
            active_key_count=1,
            access_keys=[
                IAMAccessKey(
                    user_name="user-89",
                    access_key_id="AKIA89",
                    status="Active",
                    age_days=89,
                )
            ],
        )

        # 90일 된 키 (경계)
        user_90 = IAMUser(
            user_name="user-90",
            user_id="AIDA90",
            arn="arn:aws:iam::123456789012:user/user-90",
            create_date=now,
            active_key_count=1,
            access_keys=[
                IAMAccessKey(
                    user_name="user-90",
                    access_key_id="AKIA90",
                    status="Active",
                    age_days=90,
                )
            ],
        )

        data = IAMData(
            account_id="123456789012",
            account_name="test",
            users=[user_89, user_90],
        )

        reporter = UserSnapshotReporter([data])
        analysis = reporter.analysis

        # 90일 키만 Old Access Keys에 포함
        assert len(analysis.old_access_keys) == 1
        assert analysis.old_access_keys[0].user_name == "user-90"


# =============================================================================
# Collect Function Tests
# =============================================================================


class TestCollectUserData:
    """_collect_user_data 콜백 테스트"""

    @patch("functions.analyzers.iam.user_snapshot.IAMCollector")
    def test_collect_returns_iam_data(self, mock_collector_class):
        """IAMCollector를 사용하여 데이터 수집"""
        mock_session = MagicMock()
        mock_data = MagicMock(spec=IAMData)

        mock_collector = MagicMock()
        mock_collector.collect.return_value = mock_data
        mock_collector_class.return_value = mock_collector

        result = _collect_user_data(mock_session, "123456789012", "test-account", "us-east-1")

        assert result == mock_data
        mock_collector.collect.assert_called_once_with(mock_session, "123456789012", "test-account")


# =============================================================================
# Run Function Tests
# =============================================================================


class TestRun:
    """run() 함수 테스트"""

    @patch("functions.analyzers.iam.user_snapshot.open_in_explorer")
    @patch("functions.analyzers.iam.user_snapshot.UserSnapshotReporter")
    @patch("functions.analyzers.iam.user_snapshot.parallel_collect")
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

    @patch("functions.analyzers.iam.user_snapshot.open_in_explorer")
    @patch("core.shared.io.output.print_report_complete")
    @patch("functions.analyzers.iam.user_snapshot.UserSnapshotReporter")
    @patch("functions.analyzers.iam.user_snapshot.parallel_collect")
    @patch("functions.analyzers.iam.user_snapshot.OutputPath")
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

    @patch("functions.analyzers.iam.user_snapshot.open_in_explorer")
    @patch("core.shared.io.output.print_report_complete")
    @patch("functions.analyzers.iam.user_snapshot.UserSnapshotReporter")
    @patch("functions.analyzers.iam.user_snapshot.parallel_collect")
    @patch("functions.analyzers.iam.user_snapshot.OutputPath")
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
