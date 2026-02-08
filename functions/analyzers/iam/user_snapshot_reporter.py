"""
analyzers/iam/user_snapshot_reporter.py - IAM 사용자 현황 Excel 보고서 생성

시트 구성:
- Summary: 계정별 통계
- Old Access Keys: 90일 이상 된 Active 키
- Inactive Users: 자격 증명 없는 비활성 사용자
- User Snapshot: 전체 사용자 현황
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from core.shared.io.excel import ColumnDef, Workbook

if TYPE_CHECKING:
    from .iam_audit_analysis.collector import IAMData

# 임계값 설정
OLD_KEY_THRESHOLD_DAYS = 90


@dataclass
class AccountStats:
    """계정별 통계"""

    account_id: str
    account_name: str
    total_users: int = 0
    users_with_console: int = 0
    users_with_mfa: int = 0
    total_access_keys: int = 0
    active_access_keys: int = 0
    old_access_keys: int = 0
    inactive_users: int = 0
    users_with_git_credentials: int = 0


@dataclass
class OldAccessKey:
    """오래된 Access Key 정보"""

    account_id: str
    account_name: str
    user_name: str
    access_key_id: str
    age_days: int
    last_used_days: int
    last_used_service: str
    last_used_region: str
    create_date: str


@dataclass
class InactiveUser:
    """비활성 사용자 정보"""

    account_id: str
    account_name: str
    user_name: str
    create_date: str
    groups: str
    attached_policies: str


@dataclass
class UserSnapshot:
    """사용자 스냅샷 정보"""

    account_id: str
    account_name: str
    user_name: str
    create_date: str
    has_console_access: bool
    has_mfa: bool
    active_key_count: int
    active_git_credential_count: int
    groups: str
    attached_policies: str
    days_since_last_login: int
    oldest_key_age_days: int


@dataclass
class UserSnapshotAnalysis:
    """분석 결과"""

    account_stats: list[AccountStats] = field(default_factory=list)
    old_access_keys: list[OldAccessKey] = field(default_factory=list)
    inactive_users: list[InactiveUser] = field(default_factory=list)
    user_snapshots: list[UserSnapshot] = field(default_factory=list)


class UserSnapshotReporter:
    """IAM 사용자 현황 보고서 생성기"""

    def __init__(self, iam_data_list: list[IAMData]):
        self.iam_data_list = iam_data_list
        self.analysis = self._analyze()

    def _analyze(self) -> UserSnapshotAnalysis:
        """IAM 데이터 분석"""
        analysis = UserSnapshotAnalysis()

        for iam_data in self.iam_data_list:
            account_id = iam_data.account_id
            account_name = iam_data.account_name

            # 계정 통계 초기화
            stats = AccountStats(
                account_id=account_id,
                account_name=account_name,
                total_users=len(iam_data.users),
            )

            for user in iam_data.users:
                # 통계 업데이트
                if user.has_console_access:
                    stats.users_with_console += 1
                if user.has_mfa:
                    stats.users_with_mfa += 1
                stats.total_access_keys += len(user.access_keys)
                stats.active_access_keys += user.active_key_count
                if user.active_git_credential_count > 0:
                    stats.users_with_git_credentials += 1

                # 오래된 Access Key 탐지
                oldest_key_age = 0
                for key in user.access_keys:
                    if key.age_days > oldest_key_age:
                        oldest_key_age = key.age_days

                    if key.status == "Active" and key.age_days >= OLD_KEY_THRESHOLD_DAYS:
                        stats.old_access_keys += 1
                        analysis.old_access_keys.append(
                            OldAccessKey(
                                account_id=account_id,
                                account_name=account_name,
                                user_name=user.user_name,
                                access_key_id=key.access_key_id,
                                age_days=key.age_days,
                                last_used_days=key.days_since_last_use,
                                last_used_service=key.last_used_service or "-",
                                last_used_region=key.last_used_region or "-",
                                create_date=key.create_date.strftime("%Y-%m-%d") if key.create_date else "-",
                            )
                        )

                # 비활성 사용자 탐지
                if not user.has_console_access and user.active_key_count == 0 and user.active_git_credential_count == 0:
                    stats.inactive_users += 1
                    analysis.inactive_users.append(
                        InactiveUser(
                            account_id=account_id,
                            account_name=account_name,
                            user_name=user.user_name,
                            create_date=user.create_date.strftime("%Y-%m-%d") if user.create_date else "-",
                            groups=", ".join(user.groups) if user.groups else "-",
                            attached_policies=", ".join(user.attached_policies) if user.attached_policies else "-",
                        )
                    )

                # 사용자 스냅샷 추가
                analysis.user_snapshots.append(
                    UserSnapshot(
                        account_id=account_id,
                        account_name=account_name,
                        user_name=user.user_name,
                        create_date=user.create_date.strftime("%Y-%m-%d") if user.create_date else "-",
                        has_console_access=user.has_console_access,
                        has_mfa=user.has_mfa,
                        active_key_count=user.active_key_count,
                        active_git_credential_count=user.active_git_credential_count,
                        groups=", ".join(user.groups) if user.groups else "-",
                        attached_policies=", ".join(user.attached_policies) if user.attached_policies else "-",
                        days_since_last_login=user.days_since_last_login,
                        oldest_key_age_days=oldest_key_age,
                    )
                )

            analysis.account_stats.append(stats)

        return analysis

    def generate(self, output_dir: str) -> str:
        """Excel 보고서 생성"""
        wb = Workbook()

        # 1. Summary 시트
        self._create_summary_sheet(wb)

        # 2. Old Access Keys 시트
        self._create_old_keys_sheet(wb)

        # 3. Inactive Users 시트
        self._create_inactive_users_sheet(wb)

        # 4. User Snapshot 시트
        self._create_user_snapshot_sheet(wb)

        # 저장
        today = datetime.now().strftime("%Y%m%d")
        filename = f"iam_user_snapshot_{today}.xlsx"
        filepath = Path(output_dir) / filename
        wb.save(str(filepath))

        return str(filepath)

    def _create_summary_sheet(self, wb: Workbook) -> None:
        """Summary 시트 생성"""
        summary = wb.new_summary_sheet()

        # 전체 통계 계산
        total_users = sum(s.total_users for s in self.analysis.account_stats)
        total_old_keys = len(self.analysis.old_access_keys)
        total_inactive = len(self.analysis.inactive_users)

        summary.add_title("IAM 사용자 현황 보고서")

        summary.add_section("전체 요약")
        summary.add_item("분석 계정 수", len(self.analysis.account_stats))
        summary.add_item("총 IAM 사용자", total_users)
        summary.add_item(
            f"오래된 Access Key ({OLD_KEY_THRESHOLD_DAYS}일+)",
            total_old_keys,
            highlight="warning" if total_old_keys > 0 else None,
        )
        summary.add_item(
            "비활성 사용자",
            total_inactive,
            highlight="warning" if total_inactive > 0 else None,
        )

        summary.add_blank_row()
        summary.add_section("계정별 통계")

        for stats in self.analysis.account_stats:
            summary.add_item(
                f"[{stats.account_name}]",
                "",
            )
            summary.add_item("  총 사용자", stats.total_users)
            summary.add_item("  콘솔 액세스", stats.users_with_console)
            summary.add_item("  MFA 활성화", stats.users_with_mfa)
            summary.add_item("  활성 Access Key", stats.active_access_keys)
            if stats.old_access_keys > 0:
                summary.add_item(
                    f"  오래된 Access Key ({OLD_KEY_THRESHOLD_DAYS}일+)",
                    stats.old_access_keys,
                    highlight="warning",
                )
            if stats.inactive_users > 0:
                summary.add_item("  비활성 사용자", stats.inactive_users, highlight="warning")

    def _create_old_keys_sheet(self, wb: Workbook) -> None:
        """Old Access Keys 시트 생성"""
        columns = [
            ColumnDef("계정 ID", width=15),
            ColumnDef("계정명", width=20),
            ColumnDef("사용자명", width=25),
            ColumnDef("Access Key ID", width=25),
            ColumnDef("키 나이 (일)", width=12, style="number"),
            ColumnDef("마지막 사용 (일 전)", width=15, style="number"),
            ColumnDef("마지막 사용 서비스", width=20),
            ColumnDef("마지막 사용 리전", width=18),
            ColumnDef("생성일", width=12),
        ]

        sheet = wb.new_sheet(f"Old Access Keys ({OLD_KEY_THRESHOLD_DAYS}일+)", columns)

        # 키 나이 기준 내림차순 정렬
        sorted_keys = sorted(self.analysis.old_access_keys, key=lambda x: x.age_days, reverse=True)

        for key in sorted_keys:
            last_used_display = str(key.last_used_days) if key.last_used_days >= 0 else "사용 안 함"
            sheet.add_row(
                [
                    key.account_id,
                    key.account_name,
                    key.user_name,
                    key.access_key_id,
                    key.age_days,
                    last_used_display,
                    key.last_used_service,
                    key.last_used_region,
                    key.create_date,
                ],
                style=wb.styles.warning() if key.age_days >= 180 else None,
            )

    def _create_inactive_users_sheet(self, wb: Workbook) -> None:
        """Inactive Users 시트 생성"""
        columns = [
            ColumnDef("계정 ID", width=15),
            ColumnDef("계정명", width=20),
            ColumnDef("사용자명", width=25),
            ColumnDef("생성일", width=12),
            ColumnDef("그룹", width=30),
            ColumnDef("연결된 정책", width=40),
        ]

        sheet = wb.new_sheet("Inactive Users", columns)

        for user in self.analysis.inactive_users:
            sheet.add_row(
                [
                    user.account_id,
                    user.account_name,
                    user.user_name,
                    user.create_date,
                    user.groups,
                    user.attached_policies,
                ]
            )

    def _create_user_snapshot_sheet(self, wb: Workbook) -> None:
        """User Snapshot 시트 생성"""
        columns = [
            ColumnDef("계정 ID", width=15),
            ColumnDef("계정명", width=20),
            ColumnDef("사용자명", width=25),
            ColumnDef("생성일", width=12),
            ColumnDef("콘솔 액세스", width=12, style="center"),
            ColumnDef("MFA", width=8, style="center"),
            ColumnDef("활성 Access Key", width=14, style="number"),
            ColumnDef("Git Credential", width=14, style="number"),
            ColumnDef("마지막 로그인 (일 전)", width=15, style="number"),
            ColumnDef("가장 오래된 키 (일)", width=15, style="number"),
            ColumnDef("그룹", width=25),
            ColumnDef("연결된 정책", width=35),
        ]

        sheet = wb.new_sheet("User Snapshot", columns)

        for user in self.analysis.user_snapshots:
            last_login_display = str(user.days_since_last_login) if user.days_since_last_login >= 0 else "-"
            oldest_key_display = str(user.oldest_key_age_days) if user.oldest_key_age_days > 0 else "-"

            style = None
            if user.oldest_key_age_days >= OLD_KEY_THRESHOLD_DAYS:
                style = wb.styles.warning()

            sheet.add_row(
                [
                    user.account_id,
                    user.account_name,
                    user.user_name,
                    user.create_date,
                    "O" if user.has_console_access else "-",
                    "O" if user.has_mfa else "-",
                    user.active_key_count,
                    user.active_git_credential_count,
                    last_login_display,
                    oldest_key_display,
                    user.groups,
                    user.attached_policies,
                ],
                style=style,
            )
