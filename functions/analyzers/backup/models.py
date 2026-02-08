"""통합 백업 분석 데이터 모델"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# ============================================================================
# 데이터 클래스 정의
# ============================================================================


@dataclass
class BackupStatus:
    """개별 AWS 리소스의 백업 상태 정보.

    서비스 자체 백업(RDS 자동 백업, DynamoDB PITR 등)과 AWS Backup 보호 여부를
    모두 추적하며, 보호 수준을 종합적으로 판단한다.

    Attributes:
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.
        service: AWS 서비스명 (RDS, DynamoDB, EFS, FSx 등).
        resource_type: 리소스 유형 (DB Instance, Table, FileSystem 등).
        resource_id: 리소스 식별자.
        resource_name: 리소스 이름.
        backup_enabled: 서비스 자체 자동 백업 활성화 여부.
        backup_method: 백업 방식 (automated, pitr, aws-backup, snapshot 등).
        last_backup_time: 자체 백업 마지막 시간.
        backup_retention_days: 백업 보존 기간 (일).
        status: 상태 코드 (OK, WARNING, FAILED, DISABLED, NOT_SUPPORTED, ALWAYS_ON).
        message: 사람이 읽을 수 있는 상세 메시지.
        resource_arn: 리소스 ARN.
        aws_backup_protected: AWS Backup으로 보호되는지 여부.
        aws_backup_last_time: AWS Backup을 통한 마지막 백업 시간.
        has_native_backup: 서비스에 자체 백업 기능이 있는지 여부 (EC2, EFS는 False).
        backup_plan_names: 할당된 Backup Plan 이름 목록.
    """

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
        """상태가 OK인지 확인한다.

        Returns:
            status가 "OK"이면 True.
        """
        return self.status == "OK"

    @property
    def is_disabled(self) -> bool:
        """백업이 비활성화 상태인지 확인한다.

        Returns:
            status가 "DISABLED"이면 True.
        """
        return self.status == "DISABLED"

    @property
    def protection_summary(self) -> str:
        """보호 상태를 사람이 읽을 수 있는 요약 문자열로 반환한다.

        서비스 자체 백업 유무와 AWS Backup 보호 여부를 조합하여
        "자체+AWS Backup", "AWS Backup만", "자체 백업만", "미보호" 중 하나를 반환한다.

        Returns:
            보호 상태 요약 문자열.
        """
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
        """완전 보호 여부를 서비스 특성을 고려하여 판단한다.

        자체 백업 기능이 없는 서비스(EC2, EFS)는 AWS Backup만 있으면 완전 보호로 판정하고,
        자체 백업 기능이 있는 서비스(RDS, DynamoDB 등)는 자체 백업과 AWS Backup
        모두 있어야 완전 보호로 판정한다.

        Returns:
            완전 보호 상태이면 True.
        """
        if not self.has_native_backup:
            # 자체 백업 없는 서비스: AWS Backup만 있으면 완전 보호
            return self.aws_backup_protected
        else:
            # 자체 백업 있는 서비스: 둘 다 있어야 완전 보호
            return self.backup_enabled and self.aws_backup_protected


@dataclass
class ServiceBackupSummary:
    """서비스별 백업 상태 요약 통계.

    Attributes:
        service: AWS 서비스명.
        total_resources: 전체 리소스 수.
        backup_enabled: 백업이 활성화된 리소스 수 (자체 또는 AWS Backup).
        backup_disabled: 백업이 비활성화된 리소스 수.
        failed_count: 백업 실패 상태인 리소스 수.
        warning_count: 경고 상태인 리소스 수.
    """

    service: str
    total_resources: int
    backup_enabled: int
    backup_disabled: int
    failed_count: int
    warning_count: int


@dataclass
class BackupPlanTagCondition:
    """AWS Backup Plan의 태그 기반 리소스 선택 조건.

    Backup Selection에 설정된 태그 조건을 나타내며, 어떤 태그를 가진 리소스가
    자동으로 백업 대상에 포함되는지 추적한다.

    Attributes:
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.
        plan_id: Backup Plan ID.
        plan_name: Backup Plan 이름.
        selection_id: Backup Selection ID.
        selection_name: Backup Selection 이름.
        condition_type: 조건 유형 (STRINGEQUALS, STRINGLIKE 등).
        tag_key: 태그 키.
        tag_value: 태그 값.
        resource_types: 대상 리소스 타입 목록 (ARN에서 추출한 서비스명).
    """

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
    """실패/중단된 AWS Backup 작업 정보.

    FAILED, ABORTED, PARTIAL 상태의 백업 작업을 기록한다.

    Attributes:
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.
        job_id: Backup Job ID.
        vault_name: 대상 Backup Vault 이름.
        resource_arn: 백업 대상 리소스 ARN.
        resource_type: 리소스 유형 (EC2, RDS 등).
        status: 작업 상태 (FAILED, ABORTED, PARTIAL).
        status_message: 실패 원인 메시지.
        creation_date: 작업 생성 일시.
        completion_date: 작업 완료(또는 실패) 일시.
    """

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
    """단일 계정/리전의 통합 백업 분석 결과.

    여러 AWS 서비스의 백업 상태, Backup Plan 태그 조건, 실패 작업을
    하나의 결과 객체로 집계한다.

    Attributes:
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.
        backup_statuses: 개별 리소스별 백업 상태 목록.
        tag_conditions: Backup Plan 태그 선택 조건 목록.
        failed_jobs: 실패/중단된 Backup 작업 목록.
    """

    account_id: str
    account_name: str
    region: str
    backup_statuses: list[BackupStatus] = field(default_factory=list)
    tag_conditions: list[BackupPlanTagCondition] = field(default_factory=list)
    failed_jobs: list[FailedBackupJob] = field(default_factory=list)

    def get_service_summary(self) -> list[ServiceBackupSummary]:
        """서비스별 백업 상태 요약 통계를 계산한다.

        자체 백업 또는 AWS Backup 중 하나라도 활성화되어 있으면 backup_enabled로 카운트한다.

        Returns:
            서비스별 요약 통계 목록.
        """
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
        """백업이 비활성화된 리소스 목록을 반환한다.

        Returns:
            status가 DISABLED인 BackupStatus 목록.
        """
        return [s for s in self.backup_statuses if s.is_disabled]
