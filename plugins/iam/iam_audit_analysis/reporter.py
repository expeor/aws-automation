"""
IAM Audit Excel 보고서 생성기

시트 구성:
1. Summary - 계정별 IAM 현황 요약
2. Critical Issues - 심각한 보안 이슈 (Root Access Key, MFA 미설정 등)
3. Users - IAM 사용자 상세
4. Access Keys - Access Key 상세 (오래된 키, 미사용 키)
5. Roles - IAM Role 상세
6. Groups - IAM Group 상세
7. Password Policy - 비밀번호 정책 점검
8. User Changes - IAM User 변경 이력 (AWS Config History)
"""

from __future__ import annotations

from typing import Any

from core.tools.io.excel import ColumnDef, Workbook

from .analyzer import (
    IAMAnalysisResult,
    Severity,
)


class IAMExcelReporter:
    """IAM Audit Excel 보고서 생성기"""

    def __init__(
        self,
        results: list[IAMAnalysisResult],
        summary_stats: list[dict[str, Any]],
    ):
        self.results = results
        self.summary_stats = summary_stats

    def generate(self, output_dir: str) -> str:
        """Excel 보고서 생성"""

        wb = Workbook()

        # 1. Summary 시트
        self._add_summary_sheet(wb)

        # 2. Critical Issues 시트
        self._add_critical_issues_sheet(wb)

        # 3. Users 시트
        self._add_users_sheet(wb)

        # 4. Access Keys 시트
        self._add_access_keys_sheet(wb)

        # 5. Roles 시트
        self._add_roles_sheet(wb)

        # 6. Groups 시트
        self._add_groups_sheet(wb)

        # 7. Password Policy 시트
        self._add_password_policy_sheet(wb)

        # 7. User Changes 시트 (변경 이력이 있는 경우만)
        self._add_user_changes_sheet(wb)

        return str(wb.save_as(output_dir, "IAM_Audit_Report"))

    def _add_summary_sheet(self, wb: Workbook) -> None:
        """Summary 시트 추가"""
        columns = [
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=25, style="data"),
            # User 통계
            ColumnDef(header="Total Users", width=12, style="number"),
            ColumnDef(header="No MFA", width=10, style="number"),
            ColumnDef(header="Inactive", width=10, style="number"),
            # Access Key 통계
            ColumnDef(header="Active Keys", width=12, style="number"),
            ColumnDef(header="Old Keys", width=10, style="number"),
            ColumnDef(header="Unused Keys", width=12, style="number"),
            # Role 통계
            ColumnDef(header="Total Roles", width=12, style="number"),
            ColumnDef(header="Unused Roles", width=12, style="number"),
            ColumnDef(header="Admin Roles", width=12, style="number"),
            # Password Policy
            ColumnDef(header="PW Policy Score", width=15, style="number"),
            # Root Account
            ColumnDef(header="Root Key", width=10, style="center"),
            ColumnDef(header="Root MFA", width=10, style="center"),
            # 이슈 수
            ColumnDef(header="Critical", width=10, style="number"),
            ColumnDef(header="High", width=10, style="number"),
            ColumnDef(header="Medium", width=10, style="number"),
        ]

        ws = wb.new_sheet("Summary", columns=columns)

        for stats in self.summary_stats:
            ws.add_row(
                [
                    str(stats["account_id"]),
                    stats["account_name"],
                    int(stats["total_users"]),
                    int(stats["users_without_mfa"]),
                    int(stats["inactive_users"]),
                    int(stats["total_active_keys"]),
                    int(stats["old_keys"]),
                    int(stats["unused_keys"]),
                    int(stats["total_roles"]),
                    int(stats["unused_roles"]),
                    int(stats["admin_roles"]),
                    int(stats["password_policy_score"]),
                    "Y" if stats["root_access_key"] else "N",
                    "Y" if stats["root_mfa"] else "N",
                    int(stats["critical_issues"]),
                    int(stats["high_issues"]),
                    int(stats["medium_issues"]),
                ]
            )

        # 합계
        if len(self.summary_stats) > 1:
            totals = {
                "total_users": sum(s["total_users"] for s in self.summary_stats),
                "users_without_mfa": sum(s["users_without_mfa"] for s in self.summary_stats),
                "inactive_users": sum(s["inactive_users"] for s in self.summary_stats),
                "total_active_keys": sum(s["total_active_keys"] for s in self.summary_stats),
                "old_keys": sum(s["old_keys"] for s in self.summary_stats),
                "unused_keys": sum(s["unused_keys"] for s in self.summary_stats),
                "total_roles": sum(s["total_roles"] for s in self.summary_stats),
                "unused_roles": sum(s["unused_roles"] for s in self.summary_stats),
                "admin_roles": sum(s["admin_roles"] for s in self.summary_stats),
                "critical_issues": sum(s["critical_issues"] for s in self.summary_stats),
                "high_issues": sum(s["high_issues"] for s in self.summary_stats),
                "medium_issues": sum(s["medium_issues"] for s in self.summary_stats),
            }
            ws.add_row(
                [
                    "TOTAL",
                    "",
                    int(totals["total_users"]),
                    int(totals["users_without_mfa"]),
                    int(totals["inactive_users"]),
                    int(totals["total_active_keys"]),
                    int(totals["old_keys"]),
                    int(totals["unused_keys"]),
                    int(totals["total_roles"]),
                    int(totals["unused_roles"]),
                    int(totals["admin_roles"]),
                    "",
                    "",
                    "",
                    int(totals["critical_issues"]),
                    int(totals["high_issues"]),
                    int(totals["medium_issues"]),
                ]
            )

    def _add_critical_issues_sheet(self, wb: Workbook) -> None:
        """Critical Issues 시트 (CRITICAL/HIGH 이슈만)"""
        columns = [
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="Severity", width=10, style="center"),
            ColumnDef(header="Category", width=15, style="center"),
            ColumnDef(header="Resource", width=30, style="data"),
            ColumnDef(header="Issue Type", width=25, style="data"),
            ColumnDef(header="Description", width=50, style="data"),
            ColumnDef(header="Recommendation", width=50, style="data"),
        ]

        ws = wb.new_sheet("Critical Issues", columns=columns)

        for result in self.results:
            # Account Issues
            if result.account_result:
                for issue in result.account_result.issues:
                    if issue.severity in (Severity.CRITICAL, Severity.HIGH):
                        ws.add_row(
                            [
                                str(result.account_id),
                                result.account_name,
                                issue.severity.value,
                                "Account",
                                "Root Account",
                                issue.issue_type.value,
                                issue.description,
                                issue.recommendation,
                            ]
                        )

            # User Issues
            for user_result in result.user_results:
                for issue in user_result.issues:
                    if issue.severity in (Severity.CRITICAL, Severity.HIGH):
                        ws.add_row(
                            [
                                str(result.account_id),
                                result.account_name,
                                issue.severity.value,
                                "User",
                                user_result.user.user_name,
                                issue.issue_type.value,
                                issue.description,
                                issue.recommendation,
                            ]
                        )

            # Access Key Issues
            for key_result in result.key_results:
                for issue in key_result.issues:
                    if issue.severity in (Severity.CRITICAL, Severity.HIGH):
                        ws.add_row(
                            [
                                str(result.account_id),
                                result.account_name,
                                issue.severity.value,
                                "Access Key",
                                f"{key_result.key.user_name} / {key_result.key.access_key_id[:12]}...",
                                issue.issue_type.value,
                                issue.description,
                                issue.recommendation,
                            ]
                        )

            # Password Policy Issues
            if result.policy_result:
                for issue in result.policy_result.issues:
                    if issue.severity in (Severity.CRITICAL, Severity.HIGH):
                        ws.add_row(
                            [
                                str(result.account_id),
                                result.account_name,
                                issue.severity.value,
                                "Password Policy",
                                "Account Policy",
                                issue.issue_type.value,
                                issue.description,
                                issue.recommendation,
                            ]
                        )

    def _add_users_sheet(self, wb: Workbook) -> None:
        """Users 시트 추가"""
        columns = [
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="User Name", width=25, style="data"),
            ColumnDef(header="Created", width=12, style="data"),
            ColumnDef(header="Access Type", width=12, style="center"),  # Console/Key/Both/None
            ColumnDef(header="Console", width=8, style="center"),
            ColumnDef(header="MFA", width=8, style="center"),
            ColumnDef(header="Last Login", width=12, style="data"),
            ColumnDef(header="Days Since Login", width=15, style="number"),
            ColumnDef(header="Active Keys", width=12, style="number"),
            ColumnDef(header="Git Creds", width=10, style="number"),
            ColumnDef(header="Groups", width=30, style="data"),
            ColumnDef(header="Privesc Paths", width=40, style="data"),
            ColumnDef(header="Issues", width=10, style="number"),
            ColumnDef(header="Risk Score", width=12, style="number"),
            ColumnDef(header="Issue Details", width=50, style="data"),
        ]

        ws = wb.new_sheet("Users", columns=columns)

        for result in self.results:
            for user_result in result.user_results:
                user = user_result.user

                # 날짜 포맷
                created_str = ""
                if user.create_date:
                    created_str = user.create_date.strftime("%Y-%m-%d")

                last_login_str = ""
                if user.password_last_used:
                    last_login_str = user.password_last_used.strftime("%Y-%m-%d")

                # 이슈 목록
                issue_details = "; ".join([f"[{i.severity.value}] {i.issue_type.value}" for i in user_result.issues])

                # Privesc Paths
                privesc_str = ", ".join(user.privesc_paths) if user.privesc_paths else ""

                # Access Type 결정 (Console/Key/Both/None)
                has_console = user.has_console_access
                has_keys = user.active_key_count > 0
                if has_console and has_keys:
                    access_type = "Both"
                elif has_console:
                    access_type = "Console"
                elif has_keys:
                    access_type = "Key"
                else:
                    access_type = "None"

                ws.add_row(
                    [
                        str(result.account_id),
                        result.account_name,
                        user.user_name,
                        created_str,
                        access_type,
                        "Y" if user.has_console_access else "N",
                        "Y" if user.has_mfa else "N",
                        last_login_str,
                        user.days_since_last_login if user.days_since_last_login >= 0 else "",
                        int(user.active_key_count),
                        int(user.active_git_credential_count),
                        ", ".join(user.groups),
                        privesc_str,
                        int(len(user_result.issues)),
                        int(user_result.risk_score),
                        issue_details,
                    ]
                )

    def _add_access_keys_sheet(self, wb: Workbook) -> None:
        """Access Keys 시트 추가"""
        columns = [
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="User Name", width=25, style="data"),
            ColumnDef(header="Access Key ID", width=25, style="data"),
            ColumnDef(header="Status", width=10, style="center"),
            ColumnDef(header="Created", width=12, style="data"),
            ColumnDef(header="Age (Days)", width=12, style="number"),
            ColumnDef(header="Last Used", width=12, style="data"),
            ColumnDef(header="Days Unused", width=12, style="number"),
            ColumnDef(header="Last Service", width=20, style="data"),
            ColumnDef(header="Last Region", width=15, style="data"),
            ColumnDef(header="Old Key", width=10, style="center"),
            ColumnDef(header="Unused", width=10, style="center"),
            ColumnDef(header="Issues", width=40, style="data"),
        ]

        ws = wb.new_sheet("Access Keys", columns=columns)

        for result in self.results:
            for key_result in result.key_results:
                key = key_result.key

                # 날짜 포맷
                created_str = ""
                if key.create_date:
                    created_str = key.create_date.strftime("%Y-%m-%d")

                last_used_str = ""
                if key.last_used_date:
                    last_used_str = key.last_used_date.strftime("%Y-%m-%d")
                elif key.days_since_last_use == -1:
                    last_used_str = "Never"

                # 이슈 목록
                issue_details = "; ".join([i.issue_type.value for i in key_result.issues])

                ws.add_row(
                    [
                        str(result.account_id),
                        result.account_name,
                        key.user_name,
                        key.access_key_id,
                        key.status,
                        created_str,
                        int(key.age_days),
                        last_used_str,
                        key.days_since_last_use if key.days_since_last_use >= 0 else "",
                        key.last_used_service,
                        key.last_used_region,
                        "Y" if key_result.is_old else "",
                        "Y" if key_result.is_unused else "",
                        issue_details,
                    ]
                )

    def _add_roles_sheet(self, wb: Workbook) -> None:
        """Roles 시트 추가"""
        columns = [
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="Role Name", width=35, style="data"),
            ColumnDef(header="Path", width=25, style="data"),
            ColumnDef(header="Created", width=12, style="data"),
            ColumnDef(header="Age (Days)", width=12, style="number"),
            ColumnDef(header="Last Used", width=12, style="data"),
            ColumnDef(header="Days Unused", width=12, style="number"),
            ColumnDef(header="Last Region", width=15, style="data"),
            ColumnDef(header="Service Linked", width=12, style="center"),
            ColumnDef(header="Admin Access", width=12, style="center"),
            ColumnDef(header="Public Trust", width=12, style="center"),
            ColumnDef(header="External No Cond", width=14, style="center"),
            ColumnDef(header="Trust Risks", width=50, style="data"),
            ColumnDef(header="Privesc Paths", width=40, style="data"),
            ColumnDef(header="Trusted Entities", width=40, style="data"),
            ColumnDef(header="Attached Policies", width=40, style="data"),
            ColumnDef(header="Connected Resources", width=50, style="data"),
            ColumnDef(header="Unused", width=10, style="center"),
            ColumnDef(header="Issues", width=40, style="data"),
        ]

        ws = wb.new_sheet("Roles", columns=columns)

        for result in self.results:
            for role_result in result.role_results:
                role = role_result.role

                # 날짜 포맷
                created_str = ""
                if role.create_date:
                    created_str = role.create_date.strftime("%Y-%m-%d")

                last_used_str = ""
                if role.last_used_date:
                    last_used_str = role.last_used_date.strftime("%Y-%m-%d")
                elif role.days_since_last_use == -1:
                    last_used_str = "Never"

                # Trusted entities (최대 3개)
                trusted_str = "; ".join(role.trusted_entities[:3])
                if len(role.trusted_entities) > 3:
                    trusted_str += f" (+{len(role.trusted_entities) - 3})"

                # Attached policies (최대 3개)
                policies_str = ", ".join(role.attached_policies[:3])
                if len(role.attached_policies) > 3:
                    policies_str += f" (+{len(role.attached_policies) - 3})"

                # Connected Resources (AWS Config)
                connected_str = ""
                if role.connected_resources:
                    resources = [f"{r.resource_type}: {r.resource_name}" for r in role.connected_resources[:5]]
                    connected_str = "; ".join(resources)
                    if len(role.connected_resources) > 5:
                        connected_str += f" (+{len(role.connected_resources) - 5})"

                # Trust Policy 위험 요약
                trust_risks_str = "; ".join(role.trust_policy_risks[:2])
                if len(role.trust_policy_risks) > 2:
                    trust_risks_str += f" (+{len(role.trust_policy_risks) - 2})"

                # Privesc Paths
                privesc_str = ", ".join(role.privesc_paths) if role.privesc_paths else ""

                # 이슈 목록
                issue_details = "; ".join([i.issue_type.value for i in role_result.issues])

                ws.add_row(
                    [
                        str(result.account_id),
                        result.account_name,
                        role.role_name,
                        role.path,
                        created_str,
                        int(role.age_days),
                        last_used_str,
                        role.days_since_last_use if role.days_since_last_use >= 0 else "",
                        role.last_used_region,
                        "Y" if role.is_service_linked else "",
                        "Y" if role.has_admin_access else "",
                        "Y" if role.has_public_trust else "",
                        "Y" if role.has_external_without_condition else "",
                        trust_risks_str,
                        privesc_str,
                        trusted_str,
                        policies_str,
                        connected_str,
                        "Y" if role_result.is_unused else "",
                        issue_details,
                    ]
                )

    def _add_groups_sheet(self, wb: Workbook) -> None:
        """Groups 시트 추가"""
        columns = [
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="Group Name", width=30, style="data"),
            ColumnDef(header="Path", width=20, style="data"),
            ColumnDef(header="Created", width=12, style="data"),
            ColumnDef(header="Age (Days)", width=12, style="number"),
            ColumnDef(header="Members", width=10, style="number"),
            ColumnDef(header="Member List", width=40, style="data"),
            ColumnDef(header="Admin Access", width=12, style="center"),
            ColumnDef(header="Attached Policies", width=40, style="data"),
            ColumnDef(header="Inline Policies", width=30, style="data"),
            ColumnDef(header="Dangerous Perms", width=40, style="data"),
            ColumnDef(header="Empty", width=8, style="center"),
            ColumnDef(header="Issues", width=40, style="data"),
        ]

        ws = wb.new_sheet("Groups", columns=columns)

        for result in self.results:
            for group_result in result.group_results:
                group = group_result.group

                # 날짜 포맷
                created_str = ""
                if group.create_date:
                    created_str = group.create_date.strftime("%Y-%m-%d")

                # 멤버 목록 (최대 5명)
                members_str = ", ".join(group.members[:5])
                if len(group.members) > 5:
                    members_str += f" (+{len(group.members) - 5})"

                # Attached policies (최대 3개)
                policies_str = ", ".join(group.attached_policies[:3])
                if len(group.attached_policies) > 3:
                    policies_str += f" (+{len(group.attached_policies) - 3})"

                # Inline policies
                inline_str = ", ".join(group.inline_policies[:3])
                if len(group.inline_policies) > 3:
                    inline_str += f" (+{len(group.inline_policies) - 3})"

                # Dangerous permissions
                dangerous_str = ", ".join(group.dangerous_permissions[:3])
                if len(group.dangerous_permissions) > 3:
                    dangerous_str += f" (+{len(group.dangerous_permissions) - 3})"

                # 이슈 목록
                issue_details = "; ".join([i.issue_type.value for i in group_result.issues])

                ws.add_row(
                    [
                        str(result.account_id),
                        result.account_name,
                        group.group_name,
                        group.path,
                        created_str,
                        int(group.age_days),
                        int(group.member_count),
                        members_str,
                        "Y" if group.has_admin_access else "",
                        policies_str,
                        inline_str,
                        dangerous_str,
                        "Y" if group_result.is_empty else "",
                        issue_details,
                    ]
                )

    def _add_password_policy_sheet(self, wb: Workbook) -> None:
        """Password Policy 시트 추가"""
        columns = [
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="Policy Exists", width=12, style="center"),
            ColumnDef(header="Min Length", width=12, style="number"),
            ColumnDef(header="Require Symbols", width=15, style="center"),
            ColumnDef(header="Require Numbers", width=15, style="center"),
            ColumnDef(header="Require Upper", width=15, style="center"),
            ColumnDef(header="Require Lower", width=15, style="center"),
            ColumnDef(header="Expire Password", width=15, style="center"),
            ColumnDef(header="Max Age (Days)", width=15, style="number"),
            ColumnDef(header="Reuse Prevention", width=15, style="number"),
            ColumnDef(header="Score", width=10, style="number"),
            ColumnDef(header="Issues", width=60, style="data"),
        ]

        ws = wb.new_sheet("Password Policy", columns=columns)

        for result in self.results:
            if not result.policy_result:
                continue

            policy = result.policy_result.policy

            # 이슈 목록
            issue_details = "; ".join([i.description for i in result.policy_result.issues])

            ws.add_row(
                [
                    str(result.account_id),
                    result.account_name,
                    "Y" if policy.exists else "N",
                    int(policy.minimum_length) if policy.exists else "",
                    "Y" if policy.require_symbols else "N",
                    "Y" if policy.require_numbers else "N",
                    "Y" if policy.require_uppercase else "N",
                    "Y" if policy.require_lowercase else "N",
                    "Y" if policy.expire_passwords else "N",
                    int(policy.max_password_age) if policy.expire_passwords else "",
                    int(policy.password_reuse_prevention) if policy.password_reuse_prevention > 0 else "",
                    int(result.policy_result.score),
                    issue_details,
                ]
            )

    def _add_user_changes_sheet(self, wb: Workbook) -> None:
        """User Changes 시트 추가 (AWS Config History)"""
        # 변경 이력이 있는지 확인
        has_changes = any(
            user.change_history
            for result in self.results
            for user_result in result.user_results
            for user in [user_result.user]
        )

        if not has_changes:
            return

        columns = [
            ColumnDef(header="Account ID", width=15, style="text"),
            ColumnDef(header="Account Name", width=20, style="data"),
            ColumnDef(header="User Name", width=25, style="data"),
            ColumnDef(header="Change Time", width=20, style="data"),
            ColumnDef(header="Change Type", width=12, style="center"),
            ColumnDef(header="Status", width=15, style="center"),
            ColumnDef(header="Changes", width=60, style="data"),
            ColumnDef(header="CloudTrail Events", width=50, style="data"),
        ]

        ws = wb.new_sheet("User Changes", columns=columns)

        for result in self.results:
            for user_result in result.user_results:
                user = user_result.user

                for change in user.change_history:
                    # 변경 시간 포맷
                    change_time_str = ""
                    if change.capture_time:
                        change_time_str = change.capture_time.strftime("%Y-%m-%d %H:%M:%S")

                    # CloudTrail 이벤트 (최대 3개)
                    events_str = ", ".join(change.related_events[:3])
                    if len(change.related_events) > 3:
                        events_str += f" (+{len(change.related_events) - 3})"

                    ws.add_row(
                        [
                            str(result.account_id),
                            result.account_name,
                            user.user_name,
                            change_time_str,
                            change.change_type,
                            change.status,
                            change.configuration_diff or "N/A",
                            events_str,
                        ]
                    )
