"""통합 백업 분석 데이터 모델"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# ============================================================================
# 데이터 클래스 정의
# ============================================================================


@dataclass
class BackupStatus:
    """개별 리소스의 백업 상태"""

    account_id: str
    account_name: str
    region: str
    service: str  # rds, dynamodb, efs, fsx, aws-backup
    resource_type: str  # db-instance, db-cluster, table, filesystem 등
    resource_id: str
    resource_name: str
    backup_enabled: bool  # 서비스 자체 자동 백업 활성화 여부
    backup_method: str  # automated, pitr, aws-backup
    last_backup_time: datetime | None  # 자체 백업 마지막 시간
    backup_retention_days: int
    status: str  # OK, WARNING, FAILED, DISABLED
    message: str  # 상세 메시지
    resource_arn: str = ""
    aws_backup_protected: bool = False  # AWS Backup으로 보호되는지 여부
    aws_backup_last_time: datetime | None = None  # AWS Backup 마지막 백업 시간
    has_native_backup: bool = True  # 해당 서비스가 자체 백업 기능을 가지는지 (EC2는 False)
    backup_plan_names: list[str] = field(default_factory=list)  # 할당된 Backup Plan 이름들

    @property
    def is_ok(self) -> bool:
        return self.status == "OK"

    @property
    def is_disabled(self) -> bool:
        return self.status == "DISABLED"

    @property
    def protection_summary(self) -> str:
        """보호 상태 요약"""
        if not self.has_native_backup:
            # EC2 등 자체 백업 기능 없는 서비스
            return "AWS Backup" if self.aws_backup_protected else "미보호"
        else:
            # 자체 백업 기능 있는 서비스 (RDS, DynamoDB 등)
            if self.backup_enabled and self.aws_backup_protected:
                return "자체+AWS Backup"
            elif self.aws_backup_protected:
                return "AWS Backup만"
            elif self.backup_enabled:
                return "자체 백업만"
            else:
                return "미보호"

    @property
    def is_fully_protected(self) -> bool:
        """완전 보호 여부 (서비스 특성 고려)"""
        if not self.has_native_backup:
            # 자체 백업 없는 서비스: AWS Backup만 있으면 완전 보호
            return self.aws_backup_protected
        else:
            # 자체 백업 있는 서비스: 둘 다 있어야 완전 보호
            return self.backup_enabled and self.aws_backup_protected


@dataclass
class ServiceBackupSummary:
    """서비스별 백업 요약"""

    service: str
    total_resources: int
    backup_enabled: int
    backup_disabled: int
    failed_count: int
    warning_count: int


@dataclass
class BackupPlanTagCondition:
    """Backup Plan의 태그 선택 조건"""

    account_id: str
    account_name: str
    region: str
    plan_id: str
    plan_name: str
    selection_id: str
    selection_name: str
    condition_type: str  # STRINGEQUALS, STRINGLIKE 등
    tag_key: str
    tag_value: str
    resource_types: list[str] = field(default_factory=list)  # 대상 리소스 타입


@dataclass
class FailedBackupJob:
    """실패한 AWS Backup 작업"""

    account_id: str
    account_name: str
    region: str
    job_id: str
    vault_name: str
    resource_arn: str
    resource_type: str
    status: str
    status_message: str
    creation_date: datetime | None
    completion_date: datetime | None


@dataclass
class ComprehensiveBackupResult:
    """통합 백업 분석 결과 (단일 계정/리전)"""

    account_id: str
    account_name: str
    region: str
    backup_statuses: list[BackupStatus] = field(default_factory=list)
    tag_conditions: list[BackupPlanTagCondition] = field(default_factory=list)
    failed_jobs: list[FailedBackupJob] = field(default_factory=list)

    def get_service_summary(self) -> list[ServiceBackupSummary]:
        """서비스별 요약 통계 계산"""
        summaries: dict[str, ServiceBackupSummary] = {}

        for status in self.backup_statuses:
            key = status.service
            if key not in summaries:
                summaries[key] = ServiceBackupSummary(
                    service=key,
                    total_resources=0,
                    backup_enabled=0,
                    backup_disabled=0,
                    failed_count=0,
                    warning_count=0,
                )

            s = summaries[key]
            s.total_resources += 1

            # 보호 여부: 자체 백업 OR AWS Backup 중 하나라도 있으면 보호됨
            is_protected = status.backup_enabled or status.aws_backup_protected
            if is_protected:
                s.backup_enabled += 1
            else:
                s.backup_disabled += 1

            if status.status == "FAILED":
                s.failed_count += 1
            elif status.status == "WARNING":
                s.warning_count += 1

        return list(summaries.values())

    def get_disabled_resources(self) -> list[BackupStatus]:
        """백업 비활성화된 리소스 목록"""
        return [s for s in self.backup_statuses if s.is_disabled]
