"""
analyzers/iam/unused_roles_reporter.py - 미사용 IAM Role Excel 보고서 생성

시트 구성:
- Summary: 계정별 Role 통계
- Unused Roles: 365일+ 미사용 Role 상세 (Trust Policy, 연결 리소스 포함)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from core.shared.io.excel import ColumnDef, Workbook

if TYPE_CHECKING:
    from .iam_audit_analysis.collector import IAMData


@dataclass
class RoleStats:
    """계정별 Role 통계"""

    account_id: str
    account_name: str
    total_roles: int = 0
    service_linked_roles: int = 0
    aws_managed_roles: int = 0
    custom_roles: int = 0
    unused_roles: int = 0
    admin_roles: int = 0
    config_enabled: bool = False


@dataclass
class UnusedRole:
    """미사용 Role 정보"""

    account_id: str
    account_name: str
    role_name: str
    role_arn: str
    description: str
    create_date: str
    age_days: int
    last_used_date: str
    days_since_last_use: int
    last_used_region: str
    trusted_entities: str
    attached_policies: str
    connected_resources: str
    has_admin_access: bool
    path: str


@dataclass
class UnusedRolesAnalysis:
    """분석 결과"""

    role_stats: list[RoleStats] = field(default_factory=list)
    unused_roles: list[UnusedRole] = field(default_factory=list)


class UnusedRolesReporter:
    """미사용 IAM Role 보고서 생성기"""

    def __init__(self, iam_data_list: list[IAMData], threshold_days: int = 365):
        self.iam_data_list = iam_data_list
        self.threshold_days = threshold_days
        self.analysis = self._analyze()

    def _analyze(self) -> UnusedRolesAnalysis:
        """IAM 데이터 분석"""
        analysis = UnusedRolesAnalysis()

        for iam_data in self.iam_data_list:
            account_id = iam_data.account_id
            account_name = iam_data.account_name

            # 계정 통계 초기화
            stats = RoleStats(
                account_id=account_id,
                account_name=account_name,
                total_roles=len(iam_data.roles),
                config_enabled=iam_data.config_enabled,
            )

            for role in iam_data.roles:
                # Role 타입 분류
                if role.is_service_linked:
                    stats.service_linked_roles += 1
                    continue  # Service-linked roles 제외
                elif role.is_aws_managed:
                    stats.aws_managed_roles += 1
                else:
                    stats.custom_roles += 1

                if role.has_admin_access:
                    stats.admin_roles += 1

                # 미사용 Role 판정
                # 조건: (미사용 기록 OR threshold_days 이상 미사용) AND 생성된 지 threshold_days 이상
                is_unused = (
                    role.days_since_last_use == -1 or role.days_since_last_use >= self.threshold_days
                ) and role.age_days >= self.threshold_days

                if is_unused:
                    stats.unused_roles += 1

                    # 연결 리소스 문자열 생성
                    connected_resources_str = "-"
                    if role.connected_resources:
                        resources = []
                        for res in role.connected_resources[:5]:  # 최대 5개
                            resources.append(f"{res.resource_type}: {res.resource_name}")
                        connected_resources_str = "\n".join(resources)
                        if len(role.connected_resources) > 5:
                            connected_resources_str += f"\n... 외 {len(role.connected_resources) - 5}개"

                    # 마지막 사용일 표시
                    last_used_display = "-"
                    if role.last_used_date:
                        last_used_display = role.last_used_date.strftime("%Y-%m-%d")

                    analysis.unused_roles.append(
                        UnusedRole(
                            account_id=account_id,
                            account_name=account_name,
                            role_name=role.role_name,
                            role_arn=role.arn,
                            description=role.description or "-",
                            create_date=role.create_date.strftime("%Y-%m-%d") if role.create_date else "-",
                            age_days=role.age_days,
                            last_used_date=last_used_display,
                            days_since_last_use=role.days_since_last_use,
                            last_used_region=role.last_used_region or "-",
                            trusted_entities="\n".join(role.trusted_entities) if role.trusted_entities else "-",
                            attached_policies=", ".join(role.attached_policies) if role.attached_policies else "-",
                            connected_resources=connected_resources_str,
                            has_admin_access=role.has_admin_access,
                            path=role.path,
                        )
                    )

            analysis.role_stats.append(stats)

        return analysis

    def generate(self, output_dir: str) -> str:
        """Excel 보고서 생성"""
        wb = Workbook()

        # 1. Summary 시트
        self._create_summary_sheet(wb)

        # 2. Unused Roles 시트
        self._create_unused_roles_sheet(wb)

        # 저장
        today = datetime.now().strftime("%Y%m%d")
        filename = f"iam_unused_roles_{today}.xlsx"
        filepath = Path(output_dir) / filename
        wb.save(str(filepath))

        return str(filepath)

    def _create_summary_sheet(self, wb: Workbook) -> None:
        """Summary 시트 생성"""
        summary = wb.new_summary_sheet()

        # 전체 통계 계산
        total_roles = sum(s.total_roles for s in self.analysis.role_stats)
        total_service_linked = sum(s.service_linked_roles for s in self.analysis.role_stats)
        total_unused = len(self.analysis.unused_roles)

        summary.add_title("미사용 IAM Role 탐지 보고서")

        summary.add_section("전체 요약")
        summary.add_item("분석 계정 수", len(self.analysis.role_stats))
        summary.add_item("총 IAM Role", total_roles)
        summary.add_item("Service-linked Role (분석 제외)", total_service_linked)
        summary.add_item(
            f"미사용 Role ({self.threshold_days}일+)",
            total_unused,
            highlight="warning" if total_unused > 0 else "success",
        )

        summary.add_blank_row()
        summary.add_section("계정별 통계")

        for stats in self.analysis.role_stats:
            config_status = " [Config O]" if stats.config_enabled else " [Config X]"
            summary.add_item(
                f"[{stats.account_name}]{config_status}",
                "",
            )
            summary.add_item("  총 Role", stats.total_roles)
            summary.add_item("  Service-linked Role", stats.service_linked_roles)
            summary.add_item("  AWS Managed Role", stats.aws_managed_roles)
            summary.add_item("  Custom Role", stats.custom_roles)
            if stats.unused_roles > 0:
                summary.add_item(
                    f"  미사용 Role ({self.threshold_days}일+)",
                    stats.unused_roles,
                    highlight="warning",
                )
            if stats.admin_roles > 0:
                summary.add_item("  Admin 권한 Role", stats.admin_roles)

    def _create_unused_roles_sheet(self, wb: Workbook) -> None:
        """Unused Roles 시트 생성"""
        columns = [
            ColumnDef("계정 ID", width=15),
            ColumnDef("계정명", width=20),
            ColumnDef("Role 이름", width=35),
            ColumnDef("설명", width=30),
            ColumnDef("Path", width=20),
            ColumnDef("생성일", width=12),
            ColumnDef("나이 (일)", width=10, style="number"),
            ColumnDef("마지막 사용일", width=12),
            ColumnDef("미사용 (일)", width=10, style="number"),
            ColumnDef("Admin", width=8, style="center"),
            ColumnDef("Trust Policy", width=40),
            ColumnDef("연결된 정책", width=35),
            ColumnDef("연결된 리소스", width=40),
        ]

        sheet = wb.new_sheet(f"Unused Roles ({self.threshold_days}일+)", columns)

        # 미사용 기간 기준 내림차순 정렬 (never used 먼저)
        sorted_roles = sorted(
            self.analysis.unused_roles,
            key=lambda x: x.days_since_last_use if x.days_since_last_use >= 0 else 9999,
            reverse=True,
        )

        for role in sorted_roles:
            days_display = str(role.days_since_last_use) if role.days_since_last_use >= 0 else "사용 안 함"

            style = None
            if role.has_admin_access:
                style = wb.styles.danger()
            elif role.days_since_last_use == -1 or role.days_since_last_use >= 730:  # 2년+
                style = wb.styles.warning()

            sheet.add_row(
                [
                    role.account_id,
                    role.account_name,
                    role.role_name,
                    role.description,
                    role.path,
                    role.create_date,
                    role.age_days,
                    role.last_used_date,
                    days_display,
                    "O" if role.has_admin_access else "-",
                    role.trusted_entities,
                    role.attached_policies,
                    role.connected_resources,
                ],
                style=style,
            )
