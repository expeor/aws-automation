"""
IAM 데이터 수집기

수집 항목:
- IAM Users (MFA, Access Keys, Password, Git Credentials)
- IAM Roles (LastUsed, Policies, Connected Resources)
- Password Policy
- Account Summary (Root Account 정보)
- AWS Config (Role-Resource 관계)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from botocore.exceptions import ClientError

from core.parallel import get_client

logger = logging.getLogger(__name__)


@dataclass
class IAMAccessKey:
    """IAM Access Key 정보"""

    user_name: str
    access_key_id: str
    status: str  # Active / Inactive
    create_date: datetime | None = None
    last_used_date: datetime | None = None
    last_used_service: str = ""
    last_used_region: str = ""
    # 계산된 값
    age_days: int = 0
    days_since_last_use: int = -1  # -1 = 사용 기록 없음


@dataclass
class GitCredential:
    """CodeCommit Git Credential 정보"""

    user_name: str
    service_user_name: str
    service_specific_credential_id: str
    status: str  # Active / Inactive
    create_date: datetime | None = None
    # 계산된 값
    age_days: int = 0


@dataclass
class IAMUserChangeHistory:
    """IAM User 변경 이력 (AWS Config History)"""

    capture_time: datetime | None = None
    status: str = ""  # OK, ResourceDeleted, ResourceDiscovered
    change_type: str = ""  # CREATE, UPDATE, DELETE
    related_events: list[str] = field(default_factory=list)  # CloudTrail Event IDs
    # 변경 전후 상태 요약
    configuration_diff: str = ""


@dataclass
class RoleResourceRelation:
    """Role-Resource 연결 정보 (AWS Config)"""

    resource_type: str
    resource_name: str
    resource_id: str = ""


@dataclass
class IAMUser:
    """IAM User 정보"""

    user_name: str
    user_id: str
    arn: str
    create_date: datetime | None = None
    password_last_used: datetime | None = None
    # MFA
    has_mfa: bool = False
    mfa_devices: list[str] = field(default_factory=list)
    # Console Access (Password)
    has_console_access: bool = False
    password_last_changed: datetime | None = None
    password_next_rotation: datetime | None = None
    # Access Keys
    access_keys: list[IAMAccessKey] = field(default_factory=list)
    active_key_count: int = 0
    # Git Credentials (CodeCommit)
    git_credentials: list[GitCredential] = field(default_factory=list)
    active_git_credential_count: int = 0
    # Change History (AWS Config)
    change_history: list[IAMUserChangeHistory] = field(default_factory=list)
    # Groups & Policies
    groups: list[str] = field(default_factory=list)
    attached_policies: list[str] = field(default_factory=list)
    inline_policies: list[str] = field(default_factory=list)
    # 위험한 권한 (iam:PassRole 등)
    dangerous_permissions: list[str] = field(default_factory=list)
    has_passrole_wildcard: bool = False
    # 권한 상승 경로 (Privilege Escalation Paths)
    privesc_paths: list[str] = field(default_factory=list)
    # 계산된 값
    days_since_last_login: int = -1  # -1 = 로그인 기록 없음
    days_since_password_change: int = -1


@dataclass
class IAMRole:
    """IAM Role 정보"""

    role_name: str
    role_id: str
    arn: str
    create_date: datetime | None = None
    description: str = ""
    path: str = "/"
    # Trust Policy
    trust_policy: dict[str, Any] = field(default_factory=dict)
    trusted_entities: list[str] = field(default_factory=list)
    # Last Used
    last_used_date: datetime | None = None
    last_used_region: str = ""
    # Policies
    attached_policies: list[str] = field(default_factory=list)
    inline_policies: list[str] = field(default_factory=list)
    # Connected Resources (AWS Config)
    connected_resources: list[RoleResourceRelation] = field(default_factory=list)
    # 분석용 플래그
    is_service_linked: bool = False
    is_aws_managed: bool = False
    has_admin_access: bool = False
    # 위험한 권한 (iam:PassRole 등)
    dangerous_permissions: list[str] = field(default_factory=list)
    has_passrole_wildcard: bool = False
    # Trust Policy 위험 분석
    trust_policy_risks: list[str] = field(default_factory=list)
    has_public_trust: bool = False  # Principal: * 허용
    has_external_without_condition: bool = False  # 외부 계정 ExternalId 없음
    external_account_ids: list[str] = field(default_factory=list)  # 외부 계정 목록
    # 권한 상승 경로 (Privilege Escalation Paths)
    privesc_paths: list[str] = field(default_factory=list)
    # 계산된 값
    age_days: int = 0
    days_since_last_use: int = -1  # -1 = 사용 기록 없음


@dataclass
class IAMGroup:
    """IAM Group 정보"""

    group_name: str
    group_id: str
    arn: str
    create_date: datetime | None = None
    path: str = "/"
    # 멤버
    members: list[str] = field(default_factory=list)  # User names
    member_count: int = 0
    # Policies
    attached_policies: list[str] = field(default_factory=list)
    inline_policies: list[str] = field(default_factory=list)
    # 분석 플래그
    has_admin_access: bool = False
    dangerous_permissions: list[str] = field(default_factory=list)
    # 계산된 값
    age_days: int = 0


@dataclass
class PasswordPolicy:
    """비밀번호 정책"""

    exists: bool = False
    minimum_length: int = 0
    require_symbols: bool = False
    require_numbers: bool = False
    require_uppercase: bool = False
    require_lowercase: bool = False
    allow_users_to_change: bool = True
    expire_passwords: bool = False
    max_password_age: int = 0
    password_reuse_prevention: int = 0
    hard_expiry: bool = False


@dataclass
class AccountSummary:
    """계정 요약 정보"""

    account_id: str
    account_name: str
    # Root Account
    root_access_keys_present: bool = False
    root_mfa_active: bool = False
    # 통계
    users: int = 0
    groups: int = 0
    roles: int = 0
    policies: int = 0
    mfa_devices: int = 0
    access_keys_per_user_quota: int = 2


@dataclass
class IAMData:
    """수집된 IAM 데이터"""

    account_id: str
    account_name: str
    users: list[IAMUser] = field(default_factory=list)
    groups: list[IAMGroup] = field(default_factory=list)
    roles: list[IAMRole] = field(default_factory=list)
    password_policy: PasswordPolicy | None = None
    account_summary: AccountSummary | None = None
    # AWS Config 상태
    config_enabled: bool = False
    config_error: str = ""


class IAMCollector:
    """IAM 데이터 수집기"""

    # 관리자 수준 권한 정책 (경고 대상)
    # Tier 1: 직접 권한 상승 가능
    ADMIN_POLICIES = {
        # 핵심 Admin 정책
        "AdministratorAccess",
        "PowerUserAccess",
        "IAMFullAccess",
        # 직접 권한 상승 가능 (PassRole + 서비스)
        "AWSCloudFormationFullAccess",  # IAM 리소스 생성 가능
        "AmazonEC2FullAccess",  # PassRole + RunInstances
        "AWSLambdaFullAccess",  # PassRole + Lambda
        "AmazonECS_FullAccess",  # PassRole + ECS Task
        "AWSGlueConsoleFullAccess",  # PassRole + Glue
        "AWSCodeStarFullAccess",  # PassRole + CodeStar
        "AWSCodePipelineFullAccess",  # Role 조작
        # 간접적 권한 상승 가능
        "AmazonSageMakerFullAccess",  # PassRole + Notebook
        "AWSDataPipelineFullAccess",  # PassRole + DataPipeline
        "AmazonSSMFullAccess",  # RunCommand로 EC2 명령 실행
    }

    # 단독으로 위험한 IAM 권한 (Privilege Escalation 가능)
    DANGEROUS_PERMISSIONS = {
        # 정책 조작 - 가장 치명적
        "iam:CreatePolicyVersion",  # 기존 정책에 Admin 권한 추가
        "iam:SetDefaultPolicyVersion",  # 과거 버전으로 롤백
        "iam:AttachUserPolicy",  # 자기한테 Admin 정책 붙이기
        "iam:AttachGroupPolicy",  # 그룹에 Admin 정책 붙이기
        "iam:AttachRolePolicy",  # Role에 정책 붙이기
        "iam:PutUserPolicy",  # 인라인 정책 직접 주입
        "iam:PutGroupPolicy",
        "iam:PutRolePolicy",
        # 자격 증명 탈취
        "iam:CreateAccessKey",  # 다른 Admin 유저의 Access Key 생성
        "iam:CreateLoginProfile",  # 콘솔 비밀번호 새로 설정
        "iam:UpdateLoginProfile",  # 기존 비밀번호 변경
        # Trust Policy 조작
        "iam:UpdateAssumeRolePolicy",  # 역할의 신뢰 관계 변경
        # Deny 우회
        "iam:DeleteUserPolicy",
        "iam:DeleteGroupPolicy",
        "iam:DeleteRolePolicy",
        "iam:DetachUserPolicy",
        "iam:DetachGroupPolicy",
        "iam:DetachRolePolicy",
    }

    def __init__(self):
        self.errors: list[str] = []

    def collect(self, session, account_id: str, account_name: str) -> IAMData:
        """단일 계정에서 IAM 데이터 수집

        Args:
            session: boto3 Session
            account_id: AWS 계정 ID
            account_name: 계정 이름 (표시용)

        Returns:
            IAMData: 수집된 IAM 데이터
        """
        iam_data = IAMData(account_id=account_id, account_name=account_name)

        try:
            iam = get_client(session, "iam")

            # 1. Account Summary
            iam_data.account_summary = self._collect_account_summary(iam, account_id, account_name)

            # 2. Password Policy
            iam_data.password_policy = self._collect_password_policy(iam)

            # 3. IAM Users (Access Keys, Git Credentials 포함)
            iam_data.users = self._collect_users(iam)

            # 3-1. IAM Groups
            iam_data.groups = self._collect_groups(iam)

            # 4. IAM Roles
            iam_data.roles = self._collect_roles(iam)

            # 4-1. Trust Policy 위험 분석
            for role in iam_data.roles:
                self._analyze_trust_policy(role, account_id)

            # 5. AWS Config - Role-Resource 관계 수집
            self._collect_config_relationships(session, iam_data)

            # 6. AWS Config - User 변경 이력 수집 (Config 활성화 시에만)
            if iam_data.config_enabled:
                self._collect_user_change_history(session, iam_data)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.errors.append(f"{account_name}: {error_code}")
            logger.warning(f"수집 오류 [{account_id}]: {error_code}")

        except Exception as e:
            self.errors.append(f"{account_name}: {str(e)}")
            logger.error(f"수집 오류 [{account_id}]: {e}")

        return iam_data

    def _collect_account_summary(self, iam, account_id: str, account_name: str) -> AccountSummary:
        """Account Summary 수집"""
        summary = AccountSummary(account_id=account_id, account_name=account_name)

        try:
            response = iam.get_account_summary()
            summary_map = response.get("SummaryMap", {})

            summary.users = summary_map.get("Users", 0)
            summary.groups = summary_map.get("Groups", 0)
            summary.roles = summary_map.get("Roles", 0)
            summary.policies = summary_map.get("Policies", 0)
            summary.mfa_devices = summary_map.get("MFADevices", 0)
            summary.access_keys_per_user_quota = summary_map.get("AccessKeysPerUserQuota", 2)

            # Root Account 정보
            summary.root_access_keys_present = summary_map.get("AccountAccessKeysPresent", 0) > 0
            summary.root_mfa_active = summary_map.get("AccountMFAEnabled", 0) > 0

        except ClientError as e:
            logger.warning(f"Account Summary 수집 실패: {e}")

        return summary

    def _collect_password_policy(self, iam) -> PasswordPolicy:
        """Password Policy 수집"""
        policy = PasswordPolicy(exists=False)

        try:
            response = iam.get_account_password_policy()
            pw_policy = response.get("PasswordPolicy", {})

            policy.exists = True
            policy.minimum_length = pw_policy.get("MinimumPasswordLength", 0)
            policy.require_symbols = pw_policy.get("RequireSymbols", False)
            policy.require_numbers = pw_policy.get("RequireNumbers", False)
            policy.require_uppercase = pw_policy.get("RequireUppercaseCharacters", False)
            policy.require_lowercase = pw_policy.get("RequireLowercaseCharacters", False)
            policy.allow_users_to_change = pw_policy.get("AllowUsersToChangePassword", True)
            policy.expire_passwords = pw_policy.get("ExpirePasswords", False)
            policy.max_password_age = pw_policy.get("MaxPasswordAge", 0)
            policy.password_reuse_prevention = pw_policy.get("PasswordReusePrevention", 0)
            policy.hard_expiry = pw_policy.get("HardExpiry", False)

        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchEntity":
                # 비밀번호 정책이 설정되지 않음
                policy.exists = False
            else:
                logger.warning(f"Password Policy 수집 실패: {e}")

        return policy

    def _collect_users(self, iam) -> list[IAMUser]:
        """IAM Users 수집"""
        users = []
        now = datetime.now(timezone.utc)

        try:
            paginator = iam.get_paginator("list_users")

            for page in paginator.paginate():
                for user_data in page.get("Users", []):
                    user = IAMUser(
                        user_name=user_data["UserName"],
                        user_id=user_data["UserId"],
                        arn=user_data["Arn"],
                        create_date=user_data.get("CreateDate"),
                        password_last_used=user_data.get("PasswordLastUsed"),
                    )

                    # 마지막 로그인 일수 계산
                    if user.password_last_used:
                        delta = now - user.password_last_used
                        user.days_since_last_login = delta.days

                    # MFA 정보
                    self._collect_user_mfa(iam, user)

                    # Access Keys
                    self._collect_user_access_keys(iam, user, now)

                    # Git Credentials (CodeCommit)
                    self._collect_user_git_credentials(iam, user, now)

                    # Login Profile (Console Access)
                    self._collect_user_login_profile(iam, user, now)

                    # Groups
                    self._collect_user_groups(iam, user)

                    # Policies
                    self._collect_user_policies(iam, user)

                    users.append(user)

        except ClientError as e:
            logger.warning(f"Users 수집 실패: {e}")

        return users

    def _collect_user_mfa(self, iam, user: IAMUser) -> None:
        """사용자 MFA 정보 수집"""
        try:
            response = iam.list_mfa_devices(UserName=user.user_name)
            mfa_devices = response.get("MFADevices", [])
            user.has_mfa = len(mfa_devices) > 0
            user.mfa_devices = [d["SerialNumber"] for d in mfa_devices]
        except ClientError:
            pass

    def _collect_user_access_keys(self, iam, user: IAMUser, now: datetime) -> None:
        """사용자 Access Keys 수집"""
        try:
            response = iam.list_access_keys(UserName=user.user_name)

            for key_data in response.get("AccessKeyMetadata", []):
                key = IAMAccessKey(
                    user_name=user.user_name,
                    access_key_id=key_data["AccessKeyId"],
                    status=key_data["Status"],
                    create_date=key_data.get("CreateDate"),
                )

                # 키 나이 계산
                if key.create_date:
                    delta = now - key.create_date
                    key.age_days = delta.days

                # Last Used 정보
                try:
                    last_used_response = iam.get_access_key_last_used(AccessKeyId=key.access_key_id)
                    last_used = last_used_response.get("AccessKeyLastUsed", {})
                    key.last_used_date = last_used.get("LastUsedDate")
                    key.last_used_service = last_used.get("ServiceName", "")
                    key.last_used_region = last_used.get("Region", "")

                    if key.last_used_date:
                        delta = now - key.last_used_date
                        key.days_since_last_use = delta.days
                except ClientError:
                    pass

                user.access_keys.append(key)

                if key.status == "Active":
                    user.active_key_count += 1

        except ClientError:
            pass

    def _collect_user_git_credentials(self, iam, user: IAMUser, now: datetime) -> None:
        """사용자 Git Credentials (CodeCommit) 수집"""
        try:
            response = iam.list_service_specific_credentials(
                UserName=user.user_name,
                ServiceName="codecommit.amazonaws.com",
            )

            for cred_data in response.get("ServiceSpecificCredentials", []):
                cred = GitCredential(
                    user_name=user.user_name,
                    service_user_name=cred_data.get("ServiceUserName", ""),
                    service_specific_credential_id=cred_data.get("ServiceSpecificCredentialId", ""),
                    status=cred_data.get("Status", ""),
                    create_date=cred_data.get("CreateDate"),
                )

                # 나이 계산
                if cred.create_date:
                    delta = now - cred.create_date
                    cred.age_days = delta.days

                user.git_credentials.append(cred)

                if cred.status == "Active":
                    user.active_git_credential_count += 1

        except ClientError:
            pass

    def _collect_user_login_profile(self, iam, user: IAMUser, now: datetime) -> None:
        """사용자 Login Profile (Console Access) 수집"""
        try:
            response = iam.get_login_profile(UserName=user.user_name)
            user.has_console_access = True
            login_profile = response.get("LoginProfile", {})
            user.password_last_changed = login_profile.get("CreateDate")

            if user.password_last_changed:
                delta = now - user.password_last_changed
                user.days_since_password_change = delta.days
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchEntity":
                user.has_console_access = False

    def _collect_user_groups(self, iam, user: IAMUser) -> None:
        """사용자 그룹 수집"""
        try:
            response = iam.list_groups_for_user(UserName=user.user_name)
            user.groups = [g["GroupName"] for g in response.get("Groups", [])]
        except ClientError:
            pass

    def _collect_user_policies(self, iam, user: IAMUser) -> None:
        """사용자 정책 수집 및 위험 권한 분석"""
        try:
            # Attached Policies
            response = iam.list_attached_user_policies(UserName=user.user_name)
            user.attached_policies = [p["PolicyName"] for p in response.get("AttachedPolicies", [])]

            # Inline Policies
            response = iam.list_user_policies(UserName=user.user_name)
            user.inline_policies = response.get("PolicyNames", [])

            # Inline Policy 상세 분석 (위험 권한 검사)
            for policy_name in user.inline_policies:
                try:
                    policy_response = iam.get_user_policy(
                        UserName=user.user_name,
                        PolicyName=policy_name,
                    )
                    policy_doc = policy_response.get("PolicyDocument", {})
                    self._analyze_policy_document(policy_doc, user)
                except ClientError:
                    pass

        except ClientError:
            pass

    def _analyze_policy_document(self, policy_doc: dict[str, Any], entity: Any) -> None:
        """정책 문서에서 위험한 권한 분석

        Args:
            policy_doc: IAM 정책 문서
            entity: IAMUser 또는 IAMRole 객체
        """
        statements = policy_doc.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]

        for stmt in statements:
            if stmt.get("Effect") != "Allow":
                continue

            actions = stmt.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]

            resources = stmt.get("Resource", [])
            if isinstance(resources, str):
                resources = [resources]

            # 위험한 권한 검사
            for action in actions:
                # iam:PassRole with * resource 검사
                if action in ("iam:PassRole", "iam:*", "*") and ("*" in resources or any("*" in r for r in resources)):
                    entity.has_passrole_wildcard = True
                    if "iam:PassRole (Resource: *)" not in entity.dangerous_permissions:
                        entity.dangerous_permissions.append("iam:PassRole (Resource: *)")

                # 단독 위험 권한 검사
                if action in self.DANGEROUS_PERMISSIONS and action not in entity.dangerous_permissions:
                    entity.dangerous_permissions.append(action)

                # 와일드카드 권한 검사
                if action in ("iam:*", "*") and "iam:* (Full IAM Access)" not in entity.dangerous_permissions:
                    entity.dangerous_permissions.append("iam:* (Full IAM Access)")

    def _collect_groups(self, iam) -> list[IAMGroup]:
        """IAM Groups 수집"""
        groups = []
        now = datetime.now(timezone.utc)

        try:
            paginator = iam.get_paginator("list_groups")

            for page in paginator.paginate():
                for group_data in page.get("Groups", []):
                    group = IAMGroup(
                        group_name=group_data["GroupName"],
                        group_id=group_data["GroupId"],
                        arn=group_data["Arn"],
                        create_date=group_data.get("CreateDate"),
                        path=group_data.get("Path", "/"),
                    )

                    # Group 나이 계산
                    if group.create_date:
                        delta = now - group.create_date
                        group.age_days = delta.days

                    # 멤버 수집
                    self._collect_group_members(iam, group)

                    # 정책 수집
                    self._collect_group_policies(iam, group)

                    groups.append(group)

        except ClientError as e:
            logger.warning(f"Groups 수집 실패: {e}")

        return groups

    def _collect_group_members(self, iam, group: IAMGroup) -> None:
        """그룹 멤버 수집"""
        try:
            paginator = iam.get_paginator("get_group")

            for page in paginator.paginate(GroupName=group.group_name):
                for user in page.get("Users", []):
                    group.members.append(user["UserName"])

            group.member_count = len(group.members)

        except ClientError:
            pass

    def _collect_group_policies(self, iam, group: IAMGroup) -> None:
        """그룹 정책 수집 및 위험 권한 분석"""
        try:
            # Attached Policies
            response = iam.list_attached_group_policies(GroupName=group.group_name)
            attached = response.get("AttachedPolicies", [])
            group.attached_policies = [p["PolicyName"] for p in attached]

            # Admin 권한 확인
            for policy in attached:
                if policy["PolicyName"] in self.ADMIN_POLICIES:
                    group.has_admin_access = True
                    break

            # Inline Policies
            response = iam.list_group_policies(GroupName=group.group_name)
            group.inline_policies = response.get("PolicyNames", [])

            # Inline Policy 상세 분석 (위험 권한 검사)
            for policy_name in group.inline_policies:
                try:
                    policy_response = iam.get_group_policy(
                        GroupName=group.group_name,
                        PolicyName=policy_name,
                    )
                    policy_doc = policy_response.get("PolicyDocument", {})
                    self._analyze_group_policy_document(policy_doc, group)
                except ClientError:
                    pass

        except ClientError:
            pass

    def _analyze_group_policy_document(self, policy_doc: dict[str, Any], group: IAMGroup) -> None:
        """그룹 정책 문서에서 위험한 권한 분석"""
        statements = policy_doc.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]

        for stmt in statements:
            if stmt.get("Effect") != "Allow":
                continue

            actions = stmt.get("Action", [])
            if isinstance(actions, str):
                actions = [actions]

            # 위험한 권한 검사
            for action in actions:
                if action in self.DANGEROUS_PERMISSIONS and action not in group.dangerous_permissions:
                    group.dangerous_permissions.append(action)

                if action in ("iam:*", "*") and "iam:* (Full IAM Access)" not in group.dangerous_permissions:
                    group.dangerous_permissions.append("iam:* (Full IAM Access)")

    def _collect_roles(self, iam) -> list[IAMRole]:
        """IAM Roles 수집"""
        roles = []
        now = datetime.now(timezone.utc)

        try:
            paginator = iam.get_paginator("list_roles")

            for page in paginator.paginate():
                for role_data in page.get("Roles", []):
                    role = IAMRole(
                        role_name=role_data["RoleName"],
                        role_id=role_data["RoleId"],
                        arn=role_data["Arn"],
                        create_date=role_data.get("CreateDate"),
                        description=role_data.get("Description", ""),
                        path=role_data.get("Path", "/"),
                    )

                    # Role 나이 계산
                    if role.create_date:
                        delta = now - role.create_date
                        role.age_days = delta.days

                    # Service-linked role 확인
                    role.is_service_linked = role.path.startswith("/aws-service-role/")

                    # AWS managed role 확인
                    role.is_aws_managed = role.path.startswith("/service-role/")

                    # Trust Policy
                    trust_policy = role_data.get("AssumeRolePolicyDocument", {})
                    role.trust_policy = trust_policy
                    role.trusted_entities = self._extract_trusted_entities(trust_policy)

                    # Last Used
                    last_used = role_data.get("RoleLastUsed", {})
                    role.last_used_date = last_used.get("LastUsedDate")
                    role.last_used_region = last_used.get("Region", "")

                    if role.last_used_date:
                        delta = now - role.last_used_date
                        role.days_since_last_use = delta.days

                    # Policies
                    self._collect_role_policies(iam, role)

                    roles.append(role)

        except ClientError as e:
            logger.warning(f"Roles 수집 실패: {e}")

        return roles

    def _collect_role_policies(self, iam, role: IAMRole) -> None:
        """Role 정책 수집 및 위험 권한 분석"""
        try:
            # Attached Policies
            response = iam.list_attached_role_policies(RoleName=role.role_name)
            attached = response.get("AttachedPolicies", [])
            role.attached_policies = [p["PolicyName"] for p in attached]

            # Admin 권한 확인
            for policy in attached:
                if policy["PolicyName"] in self.ADMIN_POLICIES:
                    role.has_admin_access = True
                    break

            # Inline Policies
            response = iam.list_role_policies(RoleName=role.role_name)
            role.inline_policies = response.get("PolicyNames", [])

            # Inline Policy 상세 분석 (위험 권한 검사)
            for policy_name in role.inline_policies:
                try:
                    policy_response = iam.get_role_policy(
                        RoleName=role.role_name,
                        PolicyName=policy_name,
                    )
                    policy_doc = policy_response.get("PolicyDocument", {})
                    self._analyze_policy_document(policy_doc, role)
                except ClientError:
                    pass

        except ClientError:
            pass

    def _extract_trusted_entities(self, trust_policy: dict[str, Any]) -> list[str]:
        """Trust Policy에서 신뢰 엔티티 추출"""
        entities = []

        statements = trust_policy.get("Statement", [])
        for stmt in statements:
            principal = stmt.get("Principal", {})

            if isinstance(principal, str):
                entities.append(principal)
            elif isinstance(principal, dict):
                # Service
                service = principal.get("Service", [])
                if isinstance(service, str):
                    entities.append(f"Service: {service}")
                elif isinstance(service, list):
                    entities.extend([f"Service: {s}" for s in service])

                # AWS (accounts/roles)
                aws = principal.get("AWS", [])
                if isinstance(aws, str):
                    entities.append(f"AWS: {aws}")
                elif isinstance(aws, list):
                    entities.extend([f"AWS: {a}" for a in aws])

                # Federated
                federated = principal.get("Federated", [])
                if isinstance(federated, str):
                    entities.append(f"Federated: {federated}")
                elif isinstance(federated, list):
                    entities.extend([f"Federated: {f}" for f in federated])

        return entities

    def _analyze_trust_policy(self, role: IAMRole, current_account_id: str) -> None:
        """Trust Policy 위험 분석

        탐지 대상:
        - Principal: * (누구나 Assume 가능)
        - 외부 AWS 계정 + ExternalId Condition 없음
        - sts:AssumeRoleWithSAML 남용

        Args:
            role: IAMRole 객체
            current_account_id: 현재 계정 ID (외부 계정 판별용)
        """
        trust_policy = role.trust_policy
        if not trust_policy:
            return

        statements = trust_policy.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]

        for stmt in statements:
            # Effect가 Allow인 경우만 분석
            if stmt.get("Effect") != "Allow":
                continue

            principal = stmt.get("Principal", {})
            condition = stmt.get("Condition", {})
            action = stmt.get("Action", [])
            if isinstance(action, str):
                action = [action]

            # === 1. Principal: * 검사 (가장 위험) ===
            if principal == "*":
                role.has_public_trust = True
                role.trust_policy_risks.append("CRITICAL: Principal '*' - 누구나 Assume 가능")
                continue

            if isinstance(principal, dict):
                aws_principal = principal.get("AWS", [])
                if isinstance(aws_principal, str):
                    aws_principal = [aws_principal]

                for aws_arn in aws_principal:
                    # === 2. AWS: "*" 검사 ===
                    if aws_arn == "*":
                        role.has_public_trust = True
                        role.trust_policy_risks.append("CRITICAL: Principal AWS:'*' - 모든 AWS 계정 허용")
                        continue

                    # === 3. 외부 계정 검사 ===
                    external_account_id = self._extract_account_from_arn(aws_arn)
                    if external_account_id and external_account_id != current_account_id:
                        role.external_account_ids.append(external_account_id)

                        # ExternalId 조건 있는지 확인
                        has_external_id = self._has_external_id_condition(condition)

                        if not has_external_id:
                            role.has_external_without_condition = True
                            role.trust_policy_risks.append(
                                f"HIGH: 외부 계정 {external_account_id} - ExternalId 조건 없음 (Confused Deputy 취약)"
                            )

                # === 4. SAML 페더레이션 무제한 검사 ===
                federated = principal.get("Federated", [])
                if isinstance(federated, str):
                    federated = [federated]

                for fed in federated:
                    # SAML 페더레이션에 조건이 없으면 위험
                    if "saml-provider" in fed.lower() and not condition:
                        role.trust_policy_risks.append(f"MEDIUM: SAML 페더레이션 조건 없음 - {fed}")

    def _extract_account_from_arn(self, arn: str) -> str | None:
        """ARN에서 계정 ID 추출

        Examples:
            arn:aws:iam::123456789012:root -> 123456789012
            arn:aws:iam::123456789012:role/RoleName -> 123456789012
            123456789012 -> 123456789012
        """
        if not arn:
            return None

        # 단순 계정 ID인 경우
        if arn.isdigit() and len(arn) == 12:
            return arn

        # ARN 파싱
        parts = arn.split(":")
        if len(parts) >= 5:
            return parts[4] if parts[4] else None

        return None

    def _has_external_id_condition(self, condition: dict[str, Any]) -> bool:
        """Condition에 ExternalId가 있는지 확인"""
        if not condition:
            return False

        # StringEquals에서 ExternalId 확인
        string_equals = condition.get("StringEquals", {})
        if "sts:ExternalId" in string_equals:
            return True

        # StringLike도 확인
        string_like = condition.get("StringLike", {})
        return "sts:ExternalId" in string_like

    def _collect_config_relationships(self, session, iam_data: IAMData) -> None:
        """AWS Config에서 Role-Resource 관계 수집

        AWS Config 서비스가 비활성화되거나 권한이 없는 경우 예외 처리
        """
        import json

        try:
            config_client = get_client(session, "config")

            # Role 이름 -> Role 객체 매핑
            role_map = {role.role_name: role for role in iam_data.roles}

            if not role_map:
                return

            # AWS Config 쿼리 - IAM Role을 참조하는 리소스 조회
            query = """
            SELECT
                resourceName,
                resourceType,
                relationships.resourceId,
                relationships.resourceName
            WHERE
                relationships.resourceType = 'AWS::IAM::Role'
                AND resourceType != 'AWS::IAM::Policy'
            """

            try:
                paginator = config_client.get_paginator("select_resource_config")

                for page in paginator.paginate(Expression=query, Limit=100):
                    for item in page.get("Results", []):
                        try:
                            resource = json.loads(item)

                            resource_type = resource.get("resourceType", "")
                            resource_name = resource.get("resourceName", "")

                            # relationships에서 Role 이름 추출
                            relationships = resource.get("relationships", [])
                            if isinstance(relationships, list):
                                for rel in relationships:
                                    role_name = rel.get("resourceName")
                                    if role_name and role_name in role_map:
                                        role_map[role_name].connected_resources.append(
                                            RoleResourceRelation(
                                                resource_type=resource_type,
                                                resource_name=resource_name,
                                                resource_id=rel.get("resourceId", ""),
                                            )
                                        )
                            elif isinstance(relationships, dict):
                                role_name = relationships.get("resourceName")
                                if role_name and role_name in role_map:
                                    role_map[role_name].connected_resources.append(
                                        RoleResourceRelation(
                                            resource_type=resource_type,
                                            resource_name=resource_name,
                                            resource_id=relationships.get("resourceId", ""),
                                        )
                                    )

                        except (json.JSONDecodeError, KeyError, TypeError) as e:
                            logger.debug(f"Config 결과 파싱 오류: {e}")
                            continue

                iam_data.config_enabled = True

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                error_msg = e.response.get("Error", {}).get("Message", "")

                if error_code in (
                    "NoSuchConfigurationRecorderException",
                    "NoSuchConfigurationAggregatorException",
                ):
                    iam_data.config_error = "AWS Config가 활성화되지 않음"
                    logger.info(f"AWS Config 비활성화 [{iam_data.account_name}]: {error_msg}")
                elif error_code == "AccessDeniedException":
                    iam_data.config_error = "AWS Config 접근 권한 없음"
                    logger.info(f"AWS Config 권한 없음 [{iam_data.account_name}]: {error_msg}")
                else:
                    iam_data.config_error = f"AWS Config 오류: {error_code}"
                    logger.warning(f"AWS Config 오류 [{iam_data.account_name}]: {error_code}")

        except Exception as e:
            iam_data.config_error = f"Config 수집 실패: {str(e)}"
            logger.warning(f"Config 수집 실패 [{iam_data.account_name}]: {e}")

    def _collect_user_change_history(self, session, iam_data: IAMData) -> None:
        """AWS Config에서 IAM User 변경 이력 수집

        수정/삭제 이력만 수집 (CREATE는 무시)
        """
        try:
            config_client = get_client(session, "config")

            # User 이름 -> User 객체 매핑
            user_map = {user.user_name: user for user in iam_data.users}

            if not user_map:
                return

            for user_name, user in user_map.items():
                try:
                    # AWS Config에서 해당 User의 변경 이력 조회
                    paginator = config_client.get_paginator("get_resource_config_history")

                    prev_config = None
                    for page in paginator.paginate(
                        resourceType="AWS::IAM::User",
                        resourceId=user_name,
                        limit=50,  # 최근 50개 이력
                    ):
                        for item in page.get("configurationItems", []):
                            status = item.get("configurationItemStatus", "")

                            # CREATE는 건너뜀 (수정/삭제만)
                            if status == "ResourceDiscovered":
                                prev_config = item.get("configuration")
                                continue

                            # 변경 타입 결정
                            change_type = ""
                            if status == "ResourceDeleted":
                                change_type = "DELETE"
                            elif status == "OK":
                                change_type = "UPDATE"
                            else:
                                continue

                            # 변경 내용 요약 생성
                            config_diff = ""
                            if change_type == "UPDATE" and prev_config:
                                config_diff = self._summarize_config_diff(prev_config, item.get("configuration"))

                            history = IAMUserChangeHistory(
                                capture_time=item.get("configurationItemCaptureTime"),
                                status=status,
                                change_type=change_type,
                                related_events=item.get("relatedEvents", []),
                                configuration_diff=config_diff,
                            )
                            user.change_history.append(history)

                            # 현재 설정을 이전 설정으로 저장
                            prev_config = item.get("configuration")

                except ClientError as e:
                    error_code = e.response.get("Error", {}).get("Code", "")
                    if error_code == "ResourceNotDiscoveredException":
                        # 해당 User가 Config에서 추적되지 않음
                        continue
                    logger.debug(f"User 변경 이력 조회 실패 [{user_name}]: {error_code}")
                    continue

        except Exception as e:
            logger.warning(f"User 변경 이력 수집 실패 [{iam_data.account_name}]: {e}")

    def _summarize_config_diff(self, old_config: str, new_config: str) -> str:
        """설정 변경 사항 요약

        JSON 문자열로 된 설정을 비교하여 변경 사항 요약
        """
        import json

        try:
            if not old_config or not new_config:
                return ""

            old = json.loads(old_config) if isinstance(old_config, str) else old_config
            new = json.loads(new_config) if isinstance(new_config, str) else new_config

            changes = []

            # MFA 변경
            old_mfa = old.get("mfaDevices", [])
            new_mfa = new.get("mfaDevices", [])
            if old_mfa != new_mfa:
                if len(new_mfa) > len(old_mfa):
                    changes.append("MFA 추가")
                elif len(new_mfa) < len(old_mfa):
                    changes.append("MFA 제거")
                else:
                    changes.append("MFA 변경")

            # Policy 변경
            old_policies = set(p.get("policyName", "") for p in old.get("attachedManagedPolicies", []))
            new_policies = set(p.get("policyName", "") for p in new.get("attachedManagedPolicies", []))
            if old_policies != new_policies:
                added = new_policies - old_policies
                removed = old_policies - new_policies
                if added:
                    changes.append(f"정책 추가: {', '.join(added)}")
                if removed:
                    changes.append(f"정책 제거: {', '.join(removed)}")

            # Group 변경
            old_groups = set(g.get("groupName", "") for g in old.get("groupList", []))
            new_groups = set(g.get("groupName", "") for g in new.get("groupList", []))
            if old_groups != new_groups:
                added = new_groups - old_groups
                removed = old_groups - new_groups
                if added:
                    changes.append(f"그룹 추가: {', '.join(added)}")
                if removed:
                    changes.append(f"그룹 제거: {', '.join(removed)}")

            # Access Key 변경
            old_keys = old.get("accessKeyMetadata", [])
            new_keys = new.get("accessKeyMetadata", [])
            if len(old_keys) != len(new_keys):
                if len(new_keys) > len(old_keys):
                    changes.append("Access Key 추가")
                else:
                    changes.append("Access Key 제거")

            return "; ".join(changes) if changes else "설정 변경"

        except (json.JSONDecodeError, TypeError, KeyError):
            return "설정 변경"
