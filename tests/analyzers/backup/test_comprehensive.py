"""tests/analyzers/backup/test_comprehensive.py - 통합 백업 현황 분석 테스트"""

from __future__ import annotations

from datetime import datetime, timezone

from analyzers.backup.comprehensive import (
    BackupPlanTagCondition,
    BackupStatus,
    ComprehensiveBackupResult,
    FailedBackupJob,
    ServiceBackupSummary,
)

# =============================================================================
# 팩토리 함수
# =============================================================================


def _make_backup_status(
    resource_id: str = "vol-123",
    service: str = "ec2",
    resource_type: str = "instance",
    backup_enabled: bool = True,
    backup_method: str = "aws-backup",
    status: str = "OK",
    aws_backup_protected: bool = False,
    has_native_backup: bool = True,
    backup_retention_days: int = 7,
    account_id: str = "123456789012",
    account_name: str = "test-account",
    region: str = "ap-northeast-2",
    **kwargs,
) -> BackupStatus:
    """테스트용 BackupStatus 생성"""
    return BackupStatus(
        account_id=account_id,
        account_name=account_name,
        region=region,
        service=service,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_id,
        backup_enabled=backup_enabled,
        backup_method=backup_method,
        last_backup_time=datetime(2025, 1, 15, tzinfo=timezone.utc),
        backup_retention_days=backup_retention_days,
        status=status,
        message="",
        aws_backup_protected=aws_backup_protected,
        has_native_backup=has_native_backup,
        **kwargs,
    )


def _make_failed_job(
    job_id: str = "job-123",
    resource_arn: str = "arn:aws:ec2:ap-northeast-2:123456789012:volume/vol-123",
    status: str = "FAILED",
    account_id: str = "123456789012",
    account_name: str = "test-account",
    region: str = "ap-northeast-2",
) -> FailedBackupJob:
    """테스트용 FailedBackupJob 생성"""
    return FailedBackupJob(
        account_id=account_id,
        account_name=account_name,
        region=region,
        job_id=job_id,
        vault_name="Default",
        resource_arn=resource_arn,
        resource_type="EBS",
        status=status,
        status_message="Access denied",
        creation_date=datetime(2025, 1, 15, tzinfo=timezone.utc),
        completion_date=datetime(2025, 1, 15, 0, 30, tzinfo=timezone.utc),
    )


def _make_result(
    backup_statuses: list[BackupStatus] | None = None,
    tag_conditions: list[BackupPlanTagCondition] | None = None,
    failed_jobs: list[FailedBackupJob] | None = None,
    account_id: str = "123456789012",
    account_name: str = "test-account",
    region: str = "ap-northeast-2",
) -> ComprehensiveBackupResult:
    """테스트용 ComprehensiveBackupResult 생성"""
    return ComprehensiveBackupResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
        backup_statuses=backup_statuses or [],
        tag_conditions=tag_conditions or [],
        failed_jobs=failed_jobs or [],
    )


# =============================================================================
# BackupStatus 테스트
# =============================================================================


class TestBackupStatus:
    """BackupStatus 데이터 클래스 테스트"""

    def test_is_ok(self):
        status = _make_backup_status(status="OK")
        assert status.is_ok is True

    def test_is_not_ok(self):
        status = _make_backup_status(status="FAILED")
        assert status.is_ok is False

    def test_is_disabled(self):
        status = _make_backup_status(status="DISABLED")
        assert status.is_disabled is True

    def test_is_not_disabled(self):
        status = _make_backup_status(status="OK")
        assert status.is_disabled is False

    def test_protection_summary_no_native_backup_protected(self):
        """자체 백업 없는 서비스, AWS Backup 보호"""
        status = _make_backup_status(has_native_backup=False, aws_backup_protected=True)
        assert status.protection_summary == "AWS Backup"

    def test_protection_summary_no_native_backup_unprotected(self):
        """자체 백업 없는 서비스, 미보호"""
        status = _make_backup_status(has_native_backup=False, aws_backup_protected=False)
        assert status.protection_summary == "미보호"

    def test_protection_summary_both_enabled(self):
        """자체 백업 + AWS Backup 모두 활성화"""
        status = _make_backup_status(
            has_native_backup=True,
            backup_enabled=True,
            aws_backup_protected=True,
        )
        assert status.protection_summary == "자체+AWS Backup"

    def test_protection_summary_aws_backup_only(self):
        """AWS Backup만 활성화"""
        status = _make_backup_status(
            has_native_backup=True,
            backup_enabled=False,
            aws_backup_protected=True,
        )
        assert status.protection_summary == "AWS Backup만"

    def test_protection_summary_native_only(self):
        """자체 백업만 활성화"""
        status = _make_backup_status(
            has_native_backup=True,
            backup_enabled=True,
            aws_backup_protected=False,
        )
        assert status.protection_summary == "자체 백업만"

    def test_protection_summary_none(self):
        """미보호"""
        status = _make_backup_status(
            has_native_backup=True,
            backup_enabled=False,
            aws_backup_protected=False,
        )
        assert status.protection_summary == "미보호"

    def test_is_fully_protected_no_native_with_aws_backup(self):
        """자체 백업 없는 서비스: AWS Backup만 있으면 완전 보호"""
        status = _make_backup_status(has_native_backup=False, aws_backup_protected=True)
        assert status.is_fully_protected is True

    def test_is_fully_protected_no_native_without_aws_backup(self):
        """자체 백업 없는 서비스: AWS Backup 없으면 미보호"""
        status = _make_backup_status(has_native_backup=False, aws_backup_protected=False)
        assert status.is_fully_protected is False

    def test_is_fully_protected_native_both(self):
        """자체 백업 있는 서비스: 둘 다 있어야 완전 보호"""
        status = _make_backup_status(
            has_native_backup=True,
            backup_enabled=True,
            aws_backup_protected=True,
        )
        assert status.is_fully_protected is True

    def test_is_fully_protected_native_missing_aws(self):
        """자체 백업 있는 서비스: AWS Backup 없으면 불완전"""
        status = _make_backup_status(
            has_native_backup=True,
            backup_enabled=True,
            aws_backup_protected=False,
        )
        assert status.is_fully_protected is False


# =============================================================================
# ComprehensiveBackupResult 테스트
# =============================================================================


class TestComprehensiveBackupResult:
    """ComprehensiveBackupResult 테스트"""

    def test_get_service_summary_empty(self):
        """빈 결과에서 서비스 요약"""
        result = _make_result(backup_statuses=[])
        summaries = result.get_service_summary()
        assert summaries == []

    def test_get_service_summary_single_service(self):
        """단일 서비스 요약"""
        statuses = [
            _make_backup_status(service="rds", backup_enabled=True, status="OK"),
            _make_backup_status(service="rds", backup_enabled=False, status="DISABLED", resource_id="db-2"),
            _make_backup_status(service="rds", backup_enabled=True, status="FAILED", resource_id="db-3"),
        ]
        result = _make_result(backup_statuses=statuses)
        summaries = result.get_service_summary()

        assert len(summaries) == 1
        s = summaries[0]
        assert s.service == "rds"
        assert s.total_resources == 3
        assert s.backup_enabled == 2  # 자체 백업 활성화 2개
        assert s.backup_disabled == 1
        assert s.failed_count == 1

    def test_get_service_summary_multiple_services(self):
        """여러 서비스 요약"""
        statuses = [
            _make_backup_status(service="rds", resource_id="db-1"),
            _make_backup_status(service="dynamodb", resource_id="table-1"),
            _make_backup_status(service="efs", resource_id="fs-1"),
        ]
        result = _make_result(backup_statuses=statuses)
        summaries = result.get_service_summary()

        services = {s.service for s in summaries}
        assert services == {"rds", "dynamodb", "efs"}

    def test_get_service_summary_aws_backup_counts_as_protected(self):
        """AWS Backup으로만 보호되는 리소스도 backup_enabled으로 카운트"""
        statuses = [
            _make_backup_status(
                service="ec2",
                backup_enabled=False,
                aws_backup_protected=True,
                status="OK",
            ),
        ]
        result = _make_result(backup_statuses=statuses)
        summaries = result.get_service_summary()

        assert summaries[0].backup_enabled == 1
        assert summaries[0].backup_disabled == 0

    def test_get_disabled_resources(self):
        """백업 비활성화된 리소스 필터링"""
        statuses = [
            _make_backup_status(status="OK", resource_id="ok-1"),
            _make_backup_status(status="DISABLED", resource_id="disabled-1"),
            _make_backup_status(status="DISABLED", resource_id="disabled-2"),
            _make_backup_status(status="WARNING", resource_id="warn-1"),
        ]
        result = _make_result(backup_statuses=statuses)
        disabled = result.get_disabled_resources()

        assert len(disabled) == 2
        assert all(r.is_disabled for r in disabled)

    def test_get_disabled_resources_empty(self):
        """모든 리소스가 보호됨"""
        statuses = [
            _make_backup_status(status="OK"),
        ]
        result = _make_result(backup_statuses=statuses)
        disabled = result.get_disabled_resources()

        assert len(disabled) == 0


# =============================================================================
# ServiceBackupSummary 테스트
# =============================================================================


class TestServiceBackupSummary:
    """ServiceBackupSummary 데이터 클래스 테스트"""

    def test_creation(self):
        summary = ServiceBackupSummary(
            service="rds",
            total_resources=10,
            backup_enabled=8,
            backup_disabled=2,
            failed_count=1,
            warning_count=0,
        )
        assert summary.service == "rds"
        assert summary.total_resources == 10
        assert summary.backup_enabled == 8


# =============================================================================
# BackupPlanTagCondition 테스트
# =============================================================================


class TestBackupPlanTagCondition:
    """BackupPlanTagCondition 데이터 클래스 테스트"""

    def test_creation(self):
        condition = BackupPlanTagCondition(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            plan_id="plan-123",
            plan_name="DailyBackup",
            selection_id="sel-123",
            selection_name="TagSelection",
            condition_type="STRINGEQUALS",
            tag_key="Environment",
            tag_value="production",
        )
        assert condition.plan_name == "DailyBackup"
        assert condition.tag_key == "Environment"
        assert condition.resource_types == []


# =============================================================================
# FailedBackupJob 테스트
# =============================================================================


class TestFailedBackupJob:
    """FailedBackupJob 데이터 클래스 테스트"""

    def test_creation(self):
        job = _make_failed_job()
        assert job.job_id == "job-123"
        assert job.status == "FAILED"
        assert job.vault_name == "Default"
