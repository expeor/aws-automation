"""
SSO Analyzer - IAM Identity Center 보안 분석

분석 항목:
1. Permission Set 위험 정책 검사
2. Admin 권한 계정별 상세 현황
3. 미사용 사용자 탐지 (할당 없음)
4. MFA 설정 현황 (Identity Center 설정 기반)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .collector import SSOData, SSOGroup, SSOPermissionSet, SSOUser


class IssueType(Enum):
    """이슈 타입"""

    # Permission Set
    ADMIN_PERMISSION_SET = "admin_permission_set"
    HIGH_RISK_POLICY = "high_risk_policy"
    DANGEROUS_INLINE_PERMISSION = "dangerous_inline_permission"
    WILDCARD_PERMISSION = "wildcard_permission"

    # User
    USER_NO_ASSIGNMENT = "user_no_assignment"
    USER_ADMIN_ACCESS = "user_admin_access"
    USER_MULTI_ADMIN_ACCOUNTS = "user_multi_admin_accounts"

    # Group
    EMPTY_GROUP = "empty_group"
    GROUP_ADMIN_ACCESS = "group_admin_access"

    # Account Assignment
    DIRECT_USER_ASSIGNMENT = "direct_user_assignment"


class Severity(Enum):
    """심각도"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Issue:
    """보안 이슈"""

    issue_type: IssueType
    severity: Severity
    resource_type: str  # permission_set, user, group, assignment
    resource_name: str
    resource_id: str
    description: str
    recommendation: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PermissionSetAnalysis:
    """Permission Set 분석 결과"""

    permission_set: SSOPermissionSet
    issues: list[Issue] = field(default_factory=list)
    risk_score: int = 0  # 0-100


@dataclass
class UserAnalysis:
    """User 분석 결과"""

    user: SSOUser
    issues: list[Issue] = field(default_factory=list)
    risk_score: int = 0


@dataclass
class GroupAnalysis:
    """Group 분석 결과"""

    group: SSOGroup
    issues: list[Issue] = field(default_factory=list)


@dataclass
class AdminAccountSummary:
    """계정별 Admin 권한 요약"""

    account_id: str
    account_name: str
    admin_users: list[str] = field(default_factory=list)  # display_name
    admin_groups: list[str] = field(default_factory=list)  # group_name
    permission_sets: list[str] = field(default_factory=list)  # ps_name


@dataclass
class SSOAnalysisResult:
    """SSO 전체 분석 결과"""

    sso_data: SSOData
    permission_set_analyses: list[PermissionSetAnalysis] = field(default_factory=list)
    user_analyses: list[UserAnalysis] = field(default_factory=list)
    group_analyses: list[GroupAnalysis] = field(default_factory=list)
    admin_account_summary: list[AdminAccountSummary] = field(default_factory=list)
    all_issues: list[Issue] = field(default_factory=list)
    # 요약 통계
    total_users: int = 0
    total_groups: int = 0
    total_permission_sets: int = 0
    users_with_admin: int = 0
    users_no_assignment: int = 0
    admin_permission_sets: int = 0
    high_risk_permission_sets: int = 0
    empty_groups: int = 0


class SSOAnalyzer:
    """IAM Identity Center 보안 분석기"""

    def __init__(self, sso_data: SSOData):
        self.sso_data = sso_data
        self._admin_by_account: dict[str, AdminAccountSummary] = {}

    def analyze(self) -> SSOAnalysisResult:
        """전체 분석 수행"""
        result = SSOAnalysisResult(sso_data=self.sso_data)

        # 1. Permission Sets 분석
        for ps in self.sso_data.permission_sets:
            ps_analysis = self._analyze_permission_set(ps)
            result.permission_set_analyses.append(ps_analysis)
            result.all_issues.extend(ps_analysis.issues)

        # 2. Users 분석
        for user in self.sso_data.users:
            user_analysis = self._analyze_user(user)
            result.user_analyses.append(user_analysis)
            result.all_issues.extend(user_analysis.issues)

        # 3. Groups 분석
        for group in self.sso_data.groups:
            group_analysis = self._analyze_group(group)
            result.group_analyses.append(group_analysis)
            result.all_issues.extend(group_analysis.issues)

        # 4. Account Assignments 분석 (직접 사용자 할당 체크)
        self._analyze_assignments(result)

        # 5. Admin 계정별 요약 생성
        result.admin_account_summary = list(self._admin_by_account.values())

        # 통계 계산
        self._calculate_stats(result)

        return result

    def _analyze_permission_set(self, ps: SSOPermissionSet) -> PermissionSetAnalysis:
        """Permission Set 분석"""
        analysis = PermissionSetAnalysis(permission_set=ps)
        risk_score = 0

        # Admin Permission Set 체크
        if ps.has_admin_access:
            analysis.issues.append(
                Issue(
                    issue_type=IssueType.ADMIN_PERMISSION_SET,
                    severity=Severity.HIGH,
                    resource_type="permission_set",
                    resource_name=ps.name,
                    resource_id=ps.permission_set_arn,
                    description=f"'{ps.name}'은 관리자 수준의 권한을 가진 Permission Set입니다.",
                    recommendation="Admin 권한은 최소한의 사용자에게만 부여하세요.",
                    details={
                        "assigned_accounts": ps.assigned_account_names,
                        "managed_policies": ps.managed_policies,
                    },
                )
            )
            risk_score += 40

            # Admin 계정 요약에 추가
            for i, account_id in enumerate(ps.assigned_accounts):
                account_name = ps.assigned_account_names[i] if i < len(ps.assigned_account_names) else account_id
                self._add_admin_permission_set(account_id, account_name, ps.name)

        # 위험 관리형 정책 체크
        for policy_arn in ps.high_risk_policies:
            policy_name = policy_arn.split("/")[-1] if "/" in policy_arn else policy_arn
            analysis.issues.append(
                Issue(
                    issue_type=IssueType.HIGH_RISK_POLICY,
                    severity=Severity.HIGH,
                    resource_type="permission_set",
                    resource_name=ps.name,
                    resource_id=ps.permission_set_arn,
                    description=f"위험 관리형 정책 '{policy_name}'이 연결되어 있습니다.",
                    recommendation="필요한 최소 권한만 부여하는 정책으로 교체를 검토하세요.",
                    details={"policy_arn": policy_arn},
                )
            )
            risk_score += 20

        # Inline Policy 위험 권한 체크
        if ps.dangerous_permissions:
            for perm in ps.dangerous_permissions:
                severity = Severity.CRITICAL if perm == "*" else Severity.HIGH
                issue_type = IssueType.WILDCARD_PERMISSION if perm == "*" else IssueType.DANGEROUS_INLINE_PERMISSION

                analysis.issues.append(
                    Issue(
                        issue_type=issue_type,
                        severity=severity,
                        resource_type="permission_set",
                        resource_name=ps.name,
                        resource_id=ps.permission_set_arn,
                        description=f"Inline Policy에 위험한 권한 '{perm}'이 있습니다.",
                        recommendation="최소 권한 원칙에 따라 필요한 권한만 부여하세요.",
                        details={"permission": perm},
                    )
                )
                risk_score += 30 if perm == "*" else 15

        analysis.risk_score = min(risk_score, 100)
        return analysis

    def _analyze_user(self, user: SSOUser) -> UserAnalysis:
        """User 분석"""
        analysis = UserAnalysis(user=user)
        risk_score = 0

        # 할당이 없는 사용자 (미사용)
        if not user.assignments:
            analysis.issues.append(
                Issue(
                    issue_type=IssueType.USER_NO_ASSIGNMENT,
                    severity=Severity.INFO,
                    resource_type="user",
                    resource_name=user.display_name or user.user_name,
                    resource_id=user.user_id,
                    description="어떤 계정에도 권한이 할당되지 않은 사용자입니다.",
                    recommendation="사용하지 않는 사용자라면 삭제를 검토하세요.",
                )
            )
            risk_score += 5

        # Admin 권한 사용자
        if user.has_admin_access:
            analysis.issues.append(
                Issue(
                    issue_type=IssueType.USER_ADMIN_ACCESS,
                    severity=Severity.HIGH,
                    resource_type="user",
                    resource_name=user.display_name or user.user_name,
                    resource_id=user.user_id,
                    description=f"Admin 권한을 보유한 사용자입니다. ({len(user.admin_accounts)}개 계정)",
                    recommendation="Admin 권한이 정말 필요한지 검토하세요.",
                    details={"admin_accounts": user.admin_accounts},
                )
            )
            risk_score += 30

            # Admin 계정 요약에 추가
            for account_name in user.admin_accounts:
                # account_name으로 account_id 찾기
                for assign in user.assignments:
                    if assign.get("account_name") == account_name and assign.get("is_admin"):
                        self._add_admin_user(
                            assign.get("account_id", ""),
                            account_name,
                            user.display_name or user.user_name,
                        )

            # 여러 계정에 Admin 권한
            if len(user.admin_accounts) > 2:
                analysis.issues.append(
                    Issue(
                        issue_type=IssueType.USER_MULTI_ADMIN_ACCOUNTS,
                        severity=Severity.MEDIUM,
                        resource_type="user",
                        resource_name=user.display_name or user.user_name,
                        resource_id=user.user_id,
                        description=f"{len(user.admin_accounts)}개 계정에 Admin 권한이 있습니다.",
                        recommendation="계정별로 다른 Admin 사용자를 지정하는 것이 좋습니다.",
                        details={"admin_accounts": user.admin_accounts},
                    )
                )
                risk_score += 15

        analysis.risk_score = min(risk_score, 100)
        return analysis

    def _analyze_group(self, group: SSOGroup) -> GroupAnalysis:
        """Group 분석"""
        analysis = GroupAnalysis(group=group)

        # 빈 그룹
        if group.member_count == 0:
            analysis.issues.append(
                Issue(
                    issue_type=IssueType.EMPTY_GROUP,
                    severity=Severity.LOW,
                    resource_type="group",
                    resource_name=group.group_name,
                    resource_id=group.group_id,
                    description="멤버가 없는 빈 그룹입니다.",
                    recommendation="사용하지 않는 그룹이라면 삭제를 검토하세요.",
                )
            )

        # Admin 그룹
        if group.has_admin_access:
            analysis.issues.append(
                Issue(
                    issue_type=IssueType.GROUP_ADMIN_ACCESS,
                    severity=Severity.MEDIUM,
                    resource_type="group",
                    resource_name=group.group_name,
                    resource_id=group.group_id,
                    description=f"Admin 권한이 있는 그룹입니다. ({group.member_count}명의 멤버)",
                    recommendation="그룹 멤버를 주기적으로 검토하세요.",
                    details={"member_count": group.member_count},
                )
            )

            # Admin 계정 요약에 추가
            for assign in group.assignments:
                if assign.get("is_admin"):
                    self._add_admin_group(
                        assign.get("account_id", ""),
                        assign.get("account_name", ""),
                        group.group_name,
                    )

        return analysis

    def _analyze_assignments(self, result: SSOAnalysisResult) -> None:
        """Account Assignments 분석 - 직접 사용자 할당 체크"""
        for assignment in self.sso_data.account_assignments:
            # 그룹 대신 직접 사용자에게 할당된 경우
            if assignment.principal_type == "USER":
                issue = Issue(
                    issue_type=IssueType.DIRECT_USER_ASSIGNMENT,
                    severity=Severity.LOW,
                    resource_type="assignment",
                    resource_name=assignment.principal_name,
                    resource_id=assignment.principal_id,
                    description=(
                        f"'{assignment.principal_name}'이 '{assignment.account_name}' 계정에 직접 할당되어 있습니다."
                    ),
                    recommendation="그룹을 통한 권한 관리를 권장합니다.",
                    details={
                        "account": assignment.account_name,
                        "permission_set": assignment.permission_set_name,
                    },
                )
                result.all_issues.append(issue)

    def _add_admin_permission_set(self, account_id: str, account_name: str, ps_name: str) -> None:
        """Admin 계정 요약에 Permission Set 추가"""
        if account_id not in self._admin_by_account:
            self._admin_by_account[account_id] = AdminAccountSummary(account_id=account_id, account_name=account_name)
        if ps_name not in self._admin_by_account[account_id].permission_sets:
            self._admin_by_account[account_id].permission_sets.append(ps_name)

    def _add_admin_user(self, account_id: str, account_name: str, user_name: str) -> None:
        """Admin 계정 요약에 User 추가"""
        if account_id not in self._admin_by_account:
            self._admin_by_account[account_id] = AdminAccountSummary(account_id=account_id, account_name=account_name)
        if user_name not in self._admin_by_account[account_id].admin_users:
            self._admin_by_account[account_id].admin_users.append(user_name)

    def _add_admin_group(self, account_id: str, account_name: str, group_name: str) -> None:
        """Admin 계정 요약에 Group 추가"""
        if account_id not in self._admin_by_account:
            self._admin_by_account[account_id] = AdminAccountSummary(account_id=account_id, account_name=account_name)
        if group_name not in self._admin_by_account[account_id].admin_groups:
            self._admin_by_account[account_id].admin_groups.append(group_name)

    def _calculate_stats(self, result: SSOAnalysisResult) -> None:
        """통계 계산"""
        result.total_users = len(self.sso_data.users)
        result.total_groups = len(self.sso_data.groups)
        result.total_permission_sets = len(self.sso_data.permission_sets)

        # 사용자 통계
        result.users_with_admin = sum(1 for u in self.sso_data.users if u.has_admin_access)
        result.users_no_assignment = sum(1 for u in self.sso_data.users if not u.assignments)

        # Permission Set 통계
        result.admin_permission_sets = sum(1 for ps in self.sso_data.permission_sets if ps.has_admin_access)
        result.high_risk_permission_sets = sum(1 for ps in self.sso_data.permission_sets if ps.high_risk_policies)

        # Group 통계
        result.empty_groups = sum(1 for g in self.sso_data.groups if g.member_count == 0)

    def get_summary_stats(self, result: SSOAnalysisResult) -> dict[str, Any]:
        """요약 통계 반환"""
        # Issue 통계
        critical_count = sum(1 for i in result.all_issues if i.severity == Severity.CRITICAL)
        high_count = sum(1 for i in result.all_issues if i.severity == Severity.HIGH)
        medium_count = sum(1 for i in result.all_issues if i.severity == Severity.MEDIUM)
        low_count = sum(1 for i in result.all_issues if i.severity == Severity.LOW)

        return {
            "total_users": result.total_users,
            "total_groups": result.total_groups,
            "total_permission_sets": result.total_permission_sets,
            "users_with_admin": result.users_with_admin,
            "users_no_assignment": result.users_no_assignment,
            "admin_permission_sets": result.admin_permission_sets,
            "high_risk_permission_sets": result.high_risk_permission_sets,
            "empty_groups": result.empty_groups,
            "admin_accounts": len(result.admin_account_summary),
            "critical_issues": critical_count,
            "high_issues": high_count,
            "medium_issues": medium_count,
            "low_issues": low_count,
        }
