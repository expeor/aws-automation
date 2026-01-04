"""
SSO Collector - IAM Identity Center 데이터 수집

수집 대상:
- Identity Store: Users, Groups, Group Memberships
- SSO Admin: Permission Sets (Inline/Managed Policies), Account Assignments
- MFA 설정 상태
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from botocore.exceptions import ClientError
from rich.console import Console

from core.parallel import get_client

console = Console()


# 위험 관리형 정책 목록
HIGH_RISK_MANAGED_POLICIES = [
    "arn:aws:iam::aws:policy/AdministratorAccess",
    "arn:aws:iam::aws:policy/IAMFullAccess",
    "arn:aws:iam::aws:policy/PowerUserAccess",
    "arn:aws:iam::aws:policy/SecurityAudit",
    "arn:aws:iam::aws:policy/ViewOnlyAccess",
]

# Admin 관련 Permission Set 패턴
ADMIN_PERMISSION_PATTERNS = [
    "admin",
    "administrator",
    "poweruser",
    "full-access",
    "emergency",
    "break-glass",
]


@dataclass
class SSOUser:
    """Identity Center 사용자"""

    user_id: str
    user_name: str  # email 형식
    display_name: str = ""
    email: str = ""
    identity_store_id: str = ""
    user_type: str = ""
    status: str = "UNKNOWN"
    mfa_enabled: bool = False
    created_date: datetime | None = None
    last_login: datetime | None = None
    days_since_last_login: int = 0
    # 할당된 Permission Set 및 계정
    assignments: list[dict[str, Any]] = field(default_factory=list)
    has_admin_access: bool = False
    admin_accounts: list[str] = field(default_factory=list)


@dataclass
class SSOGroup:
    """Identity Center 그룹"""

    group_id: str
    group_name: str
    display_name: str = ""
    description: str = ""
    identity_store_id: str = ""
    member_count: int = 0
    members: list[str] = field(default_factory=list)  # user_ids
    # 할당된 Permission Set 및 계정
    assignments: list[dict[str, Any]] = field(default_factory=list)
    has_admin_access: bool = False


@dataclass
class SSOPermissionSet:
    """Permission Set 정보"""

    permission_set_arn: str
    name: str
    description: str = ""
    session_duration: str = ""
    created_date: datetime | None = None
    # 정책 정보
    managed_policies: list[str] = field(default_factory=list)
    inline_policy: str | None = None
    customer_managed_policies: list[dict[str, str]] = field(default_factory=list)
    permissions_boundary: dict[str, str] | None = None
    # 위험 분석
    has_admin_access: bool = False
    high_risk_policies: list[str] = field(default_factory=list)
    dangerous_permissions: list[str] = field(default_factory=list)
    # 계정 할당
    assigned_accounts: list[str] = field(default_factory=list)
    assigned_account_names: list[str] = field(default_factory=list)


@dataclass
class SSOAccountAssignment:
    """계정별 권한 할당 정보"""

    account_id: str
    account_name: str
    permission_set_arn: str
    permission_set_name: str
    principal_type: str  # USER or GROUP
    principal_id: str
    principal_name: str = ""


@dataclass
class SSOData:
    """SSO 전체 데이터"""

    instance_arn: str
    identity_store_id: str
    region: str = ""
    users: list[SSOUser] = field(default_factory=list)
    groups: list[SSOGroup] = field(default_factory=list)
    permission_sets: list[SSOPermissionSet] = field(default_factory=list)
    account_assignments: list[SSOAccountAssignment] = field(default_factory=list)
    # 조회 메타
    collected_at: datetime | None = None


class SSOCollector:
    """IAM Identity Center 데이터 수집기"""

    def __init__(self):
        self.errors: list[str] = []
        self._user_cache: dict[str, SSOUser] = {}
        self._group_cache: dict[str, SSOGroup] = {}
        self._account_name_cache: dict[str, str] = {}

    def collect(
        self,
        session,
        central_account_id: str,
        central_account_name: str,
    ) -> SSOData | None:
        """SSO 전체 데이터 수집

        Args:
            session: boto3 session (Identity Center 관리 계정)
            central_account_id: 중앙 관리 계정 ID
            central_account_name: 중앙 관리 계정 이름

        Returns:
            SSOData or None
        """
        try:
            # SSO 인스턴스 정보 조회
            sso_admin = get_client(session, "sso-admin")
            identity_store = get_client(session, "identitystore")

            instances = sso_admin.list_instances().get("Instances", [])
            if not instances:
                self.errors.append("IAM Identity Center 인스턴스가 없습니다.")
                return None

            instance = instances[0]
            instance_arn = instance["InstanceArn"]
            identity_store_id = instance["IdentityStoreId"]

            sso_data = SSOData(
                instance_arn=instance_arn,
                identity_store_id=identity_store_id,
                region=session.region_name or "",
                collected_at=datetime.now(timezone.utc),
            )

            # 1. 계정 이름 캐싱 (Organizations)
            self._cache_account_names(session)

            # 2. Permission Sets 수집
            console.print("  [dim]Permission Sets 수집 중...[/dim]")
            sso_data.permission_sets = self._collect_permission_sets(sso_admin, instance_arn)

            # 3. Users 수집
            console.print("  [dim]Users 수집 중...[/dim]")
            sso_data.users = self._collect_users(identity_store, identity_store_id)

            # 4. Groups 수집
            console.print("  [dim]Groups 수집 중...[/dim]")
            sso_data.groups = self._collect_groups(identity_store, identity_store_id)

            # 5. Account Assignments 수집
            console.print("  [dim]Account Assignments 수집 중...[/dim]")
            sso_data.account_assignments = self._collect_account_assignments(
                sso_admin, instance_arn, sso_data.permission_sets
            )

            # 6. 사용자/그룹에 할당 정보 매핑
            self._map_assignments_to_principals(sso_data)

            return sso_data

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.errors.append(f"SSO 데이터 수집 오류: {error_code} - {e}")
            return None
        except Exception as e:
            self.errors.append(f"SSO 데이터 수집 오류: {e}")
            return None

    def _cache_account_names(self, session) -> None:
        """Organizations에서 계정 이름 캐싱"""
        try:
            org = get_client(session, "organizations")
            paginator = org.get_paginator("list_accounts")
            for page in paginator.paginate():
                for account in page.get("Accounts", []):
                    self._account_name_cache[account["Id"]] = account["Name"]
        except ClientError:
            # Organizations 접근 권한이 없을 수 있음
            pass

    def _collect_permission_sets(self, sso_admin, instance_arn: str) -> list[SSOPermissionSet]:
        """Permission Sets 수집"""
        permission_sets = []

        try:
            paginator = sso_admin.get_paginator("list_permission_sets")
            ps_arns = []
            for page in paginator.paginate(InstanceArn=instance_arn):
                ps_arns.extend(page.get("PermissionSets", []))

            for ps_arn in ps_arns:
                ps = self._get_permission_set_detail(sso_admin, instance_arn, ps_arn)
                if ps:
                    permission_sets.append(ps)

        except ClientError as e:
            self.errors.append(f"Permission Sets 수집 오류: {e}")

        return permission_sets

    def _get_permission_set_detail(self, sso_admin, instance_arn: str, ps_arn: str) -> SSOPermissionSet | None:
        """Permission Set 상세 정보 조회"""
        try:
            # 기본 정보
            detail = sso_admin.describe_permission_set(InstanceArn=instance_arn, PermissionSetArn=ps_arn).get(
                "PermissionSet", {}
            )

            ps = SSOPermissionSet(
                permission_set_arn=ps_arn,
                name=detail.get("Name", ""),
                description=detail.get("Description", ""),
                session_duration=detail.get("SessionDuration", ""),
                created_date=detail.get("CreatedDate"),
            )

            # AWS Managed Policies
            try:
                managed_resp = sso_admin.list_managed_policies_in_permission_set(
                    InstanceArn=instance_arn, PermissionSetArn=ps_arn
                )
                ps.managed_policies = [p.get("Arn", "") for p in managed_resp.get("AttachedManagedPolicies", [])]
            except ClientError:
                pass

            # Customer Managed Policies
            try:
                customer_resp = sso_admin.list_customer_managed_policy_references_in_permission_set(
                    InstanceArn=instance_arn, PermissionSetArn=ps_arn
                )
                ps.customer_managed_policies = [
                    {"Name": p.get("Name", ""), "Path": p.get("Path", "/")}
                    for p in customer_resp.get("CustomerManagedPolicyReferences", [])
                ]
            except ClientError:
                pass

            # Inline Policy
            try:
                inline_resp = sso_admin.get_inline_policy_for_permission_set(
                    InstanceArn=instance_arn, PermissionSetArn=ps_arn
                )
                ps.inline_policy = inline_resp.get("InlinePolicy")
            except ClientError:
                pass

            # Permissions Boundary
            try:
                boundary_resp = sso_admin.get_permissions_boundary_for_permission_set(
                    InstanceArn=instance_arn, PermissionSetArn=ps_arn
                )
                boundary = boundary_resp.get("PermissionsBoundary", {})
                if boundary:
                    ps.permissions_boundary = {
                        "ManagedPolicyArn": boundary.get("ManagedPolicyArn", ""),
                        "CustomerManagedPolicyReference": boundary.get("CustomerManagedPolicyReference", {}),
                    }
            except ClientError:
                pass

            # 위험 분석
            self._analyze_permission_set_risk(ps)

            # Assigned Accounts
            try:
                paginator = sso_admin.get_paginator("list_accounts_for_provisioned_permission_set")
                for page in paginator.paginate(InstanceArn=instance_arn, PermissionSetArn=ps_arn):
                    for account_id in page.get("AccountIds", []):
                        ps.assigned_accounts.append(account_id)
                        ps.assigned_account_names.append(self._account_name_cache.get(account_id, account_id))
            except ClientError:
                pass

            return ps

        except ClientError as e:
            self.errors.append(f"Permission Set {ps_arn} 조회 오류: {e}")
            return None

    def _analyze_permission_set_risk(self, ps: SSOPermissionSet) -> None:
        """Permission Set 위험도 분석"""
        # 위험 관리형 정책 체크
        for policy_arn in ps.managed_policies:
            if policy_arn in HIGH_RISK_MANAGED_POLICIES:
                ps.high_risk_policies.append(policy_arn)
            if "AdministratorAccess" in policy_arn:
                ps.has_admin_access = True

        # 이름 패턴으로 Admin 체크
        name_lower = ps.name.lower()
        for pattern in ADMIN_PERMISSION_PATTERNS:
            if pattern in name_lower:
                ps.has_admin_access = True
                break

        # Inline Policy 위험 권한 분석
        if ps.inline_policy:
            self._analyze_inline_policy_risk(ps)

    def _analyze_inline_policy_risk(self, ps: SSOPermissionSet) -> None:
        """Inline Policy 위험 권한 분석"""
        import json

        dangerous_actions = [
            "iam:*",
            "iam:CreatePolicyVersion",
            "iam:SetDefaultPolicyVersion",
            "iam:PassRole",
            "iam:CreateAccessKey",
            "iam:AttachUserPolicy",
            "iam:AttachRolePolicy",
            "iam:PutUserPolicy",
            "iam:PutRolePolicy",
            "sts:AssumeRole",
            "lambda:CreateFunction",
            "lambda:InvokeFunction",
            "ec2:RunInstances",
            "cloudformation:CreateStack",
            "s3:*",
        ]

        try:
            policy_doc = json.loads(ps.inline_policy) if ps.inline_policy else {}
            statements = policy_doc.get("Statement", [])

            for stmt in statements:
                if stmt.get("Effect") != "Allow":
                    continue

                actions = stmt.get("Action", [])
                if isinstance(actions, str):
                    actions = [actions]

                for action in actions:
                    action_lower = action.lower()
                    # * 와일드카드는 항상 위험
                    if action == "*":
                        ps.dangerous_permissions.append("*")
                        ps.has_admin_access = True
                        continue

                    for dangerous in dangerous_actions:
                        if dangerous.lower() == action_lower or (
                            "*" in dangerous and action_lower.startswith(dangerous.split("*")[0])
                        ):
                            ps.dangerous_permissions.append(action)
                            break

        except (json.JSONDecodeError, TypeError):
            pass

    def _collect_users(self, identity_store, identity_store_id: str) -> list[SSOUser]:
        """Identity Store Users 수집"""
        users = []

        try:
            paginator = identity_store.get_paginator("list_users")
            for page in paginator.paginate(IdentityStoreId=identity_store_id):
                for user_data in page.get("Users", []):
                    user = SSOUser(
                        user_id=user_data.get("UserId", ""),
                        user_name=user_data.get("UserName", ""),
                        display_name=user_data.get("DisplayName", ""),
                        identity_store_id=identity_store_id,
                    )

                    # 이메일 추출
                    emails = user_data.get("Emails", [])
                    if emails:
                        user.email = emails[0].get("Value", user.user_name)
                    else:
                        user.email = user.user_name

                    # 캐시에 저장
                    self._user_cache[user.user_id] = user
                    users.append(user)

        except ClientError as e:
            self.errors.append(f"Users 수집 오류: {e}")

        return users

    def _collect_groups(self, identity_store, identity_store_id: str) -> list[SSOGroup]:
        """Identity Store Groups 수집"""
        groups = []

        try:
            paginator = identity_store.get_paginator("list_groups")
            for page in paginator.paginate(IdentityStoreId=identity_store_id):
                for group_data in page.get("Groups", []):
                    group = SSOGroup(
                        group_id=group_data.get("GroupId", ""),
                        group_name=group_data.get("DisplayName", ""),
                        display_name=group_data.get("DisplayName", ""),
                        description=group_data.get("Description", ""),
                        identity_store_id=identity_store_id,
                    )

                    # Group Members 수집
                    group.members = self._get_group_members(identity_store, identity_store_id, group.group_id)
                    group.member_count = len(group.members)

                    # 캐시에 저장
                    self._group_cache[group.group_id] = group
                    groups.append(group)

        except ClientError as e:
            self.errors.append(f"Groups 수집 오류: {e}")

        return groups

    def _get_group_members(self, identity_store, identity_store_id: str, group_id: str) -> list[str]:
        """그룹 멤버 목록 조회"""
        members = []
        try:
            paginator = identity_store.get_paginator("list_group_memberships")
            for page in paginator.paginate(IdentityStoreId=identity_store_id, GroupId=group_id):
                for membership in page.get("GroupMemberships", []):
                    member_id = membership.get("MemberId", {}).get("UserId", "")
                    if member_id:
                        members.append(member_id)
        except ClientError:
            pass
        return members

    def _collect_account_assignments(
        self,
        sso_admin,
        instance_arn: str,
        permission_sets: list[SSOPermissionSet],
    ) -> list[SSOAccountAssignment]:
        """계정별 권한 할당 수집"""
        assignments = []

        # Permission Set별로 할당된 계정 조회
        for ps in permission_sets:
            for account_id in ps.assigned_accounts:
                account_name = self._account_name_cache.get(account_id, account_id)

                try:
                    paginator = sso_admin.get_paginator("list_account_assignments")
                    for page in paginator.paginate(
                        InstanceArn=instance_arn,
                        AccountId=account_id,
                        PermissionSetArn=ps.permission_set_arn,
                    ):
                        for assign in page.get("AccountAssignments", []):
                            principal_type = assign.get("PrincipalType", "")
                            principal_id = assign.get("PrincipalId", "")

                            # Principal 이름 조회
                            principal_name = ""
                            if principal_type == "USER":
                                cached_user = self._user_cache.get(principal_id)
                                principal_name = cached_user.display_name if cached_user else principal_id
                            elif principal_type == "GROUP":
                                cached_group = self._group_cache.get(principal_id)
                                principal_name = cached_group.group_name if cached_group else principal_id

                            assignment = SSOAccountAssignment(
                                account_id=account_id,
                                account_name=account_name,
                                permission_set_arn=ps.permission_set_arn,
                                permission_set_name=ps.name,
                                principal_type=principal_type,
                                principal_id=principal_id,
                                principal_name=principal_name,
                            )
                            assignments.append(assignment)

                except ClientError as e:
                    self.errors.append(f"Account {account_id} / PS {ps.name} 할당 조회 오류: {e}")

        return assignments

    def _map_assignments_to_principals(self, sso_data: SSOData) -> None:
        """할당 정보를 User/Group에 매핑"""
        # Permission Set ARN -> name 매핑
        ps_name_map = {ps.permission_set_arn: ps for ps in sso_data.permission_sets}

        for assignment in sso_data.account_assignments:
            ps = ps_name_map.get(assignment.permission_set_arn)

            assign_info = {
                "account_id": assignment.account_id,
                "account_name": assignment.account_name,
                "permission_set": assignment.permission_set_name,
                "is_admin": ps.has_admin_access if ps else False,
            }

            if assignment.principal_type == "USER":
                user = self._user_cache.get(assignment.principal_id)
                if user:
                    user.assignments.append(assign_info)
                    if assign_info["is_admin"]:
                        user.has_admin_access = True
                        if assignment.account_name not in user.admin_accounts:
                            user.admin_accounts.append(assignment.account_name)

            elif assignment.principal_type == "GROUP":
                group = self._group_cache.get(assignment.principal_id)
                if group:
                    group.assignments.append(assign_info)
                    if assign_info["is_admin"]:
                        group.has_admin_access = True

                    # 그룹 멤버에게도 Admin 권한 부여
                    if assign_info["is_admin"] and group.members:
                        for member_id in group.members:
                            member = self._user_cache.get(member_id)
                            if member:
                                member.has_admin_access = True
                                if assignment.account_name not in member.admin_accounts:
                                    member.admin_accounts.append(assignment.account_name)
