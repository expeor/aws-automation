"""
IAM 분석기

분석 항목:
- User: MFA 미설정, 오래된 Access Key, 미사용 사용자
- Role: 미사용 Role, 과도한 권한
- Password Policy: 보안 수준 평가
- Account: Root Access Key, Root MFA
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .collector import (
    AccountSummary,
    IAMAccessKey,
    IAMData,
    IAMGroup,
    IAMRole,
    IAMUser,
    PasswordPolicy,
)


class Severity(Enum):
    """위험도 수준"""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFO = "Info"


class IssueType(Enum):
    """이슈 유형"""

    # User 관련
    NO_MFA = "MFA 미설정"
    OLD_ACCESS_KEY = "오래된 Access Key (90일+)"
    UNUSED_ACCESS_KEY = "미사용 Access Key"
    INACTIVE_USER = "비활성 사용자 (90일+)"
    MULTIPLE_ACCESS_KEYS = "다중 Access Key"
    NO_PASSWORD_NO_KEY = "인증 수단 없음"

    # Role 관련
    UNUSED_ROLE = "미사용 Role (90일+)"
    ADMIN_ACCESS = "관리자 권한 보유"

    # Trust Policy 위험
    PUBLIC_TRUST_POLICY = "Public Trust Policy (Principal: *)"
    EXTERNAL_ACCOUNT_NO_CONDITION = "외부 계정 ExternalId 없음"
    TRUST_POLICY_RISK = "Trust Policy 위험"

    # 권한 상승 위험 (Privilege Escalation)
    PASSROLE_WILDCARD = "iam:PassRole (Resource: *)"
    DANGEROUS_PERMISSIONS = "위험한 IAM 권한"
    PRIVESC_PATH = "권한 상승 경로 탐지"

    # Password Policy 관련
    NO_PASSWORD_POLICY = "비밀번호 정책 없음"
    WEAK_PASSWORD_POLICY = "취약한 비밀번호 정책"

    # Account 관련
    ROOT_ACCESS_KEY = "Root Access Key 존재"
    ROOT_NO_MFA = "Root MFA 미설정"

    # Group 관련
    EMPTY_GROUP = "멤버 없는 그룹"
    GROUP_ADMIN_ACCESS = "그룹에 관리자 권한"
    GROUP_DANGEROUS_PERMISSIONS = "그룹에 위험한 권한"


@dataclass
class Issue:
    """발견된 이슈"""

    issue_type: IssueType
    severity: Severity
    description: str
    recommendation: str


@dataclass
class UserAnalysisResult:
    """User 분석 결과"""

    user: IAMUser
    account_id: str
    account_name: str
    issues: list[Issue] = field(default_factory=list)
    risk_score: int = 0  # 0-100

    @property
    def has_critical_issues(self) -> bool:
        return any(i.severity == Severity.CRITICAL for i in self.issues)

    @property
    def has_high_issues(self) -> bool:
        return any(i.severity == Severity.HIGH for i in self.issues)


@dataclass
class KeyAnalysisResult:
    """Access Key 분석 결과"""

    key: IAMAccessKey
    account_id: str
    account_name: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def is_old(self) -> bool:
        return self.key.age_days >= 90

    @property
    def is_unused(self) -> bool:
        return self.key.days_since_last_use == -1 or self.key.days_since_last_use >= 90


@dataclass
class RoleAnalysisResult:
    """Role 분석 결과"""

    role: IAMRole
    account_id: str
    account_name: str
    issues: list[Issue] = field(default_factory=list)
    risk_score: int = 0

    @property
    def is_unused(self) -> bool:
        return self.role.days_since_last_use == -1 or self.role.days_since_last_use >= 90


@dataclass
class GroupAnalysisResult:
    """Group 분석 결과"""

    group: IAMGroup
    account_id: str
    account_name: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return self.group.member_count == 0


@dataclass
class PolicyAnalysisResult:
    """Password Policy 분석 결과"""

    policy: PasswordPolicy
    account_id: str
    account_name: str
    issues: list[Issue] = field(default_factory=list)
    score: int = 0  # 0-100, 높을수록 좋음


@dataclass
class AccountAnalysisResult:
    """Account 분석 결과"""

    summary: AccountSummary
    issues: list[Issue] = field(default_factory=list)


@dataclass
class IAMAnalysisResult:
    """전체 분석 결과"""

    account_id: str
    account_name: str
    user_results: list[UserAnalysisResult] = field(default_factory=list)
    key_results: list[KeyAnalysisResult] = field(default_factory=list)
    role_results: list[RoleAnalysisResult] = field(default_factory=list)
    group_results: list[GroupAnalysisResult] = field(default_factory=list)
    policy_result: PolicyAnalysisResult | None = None
    account_result: AccountAnalysisResult | None = None


class IAMAnalyzer:
    """IAM 분석기"""

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

    # 권한 상승 경로 정의 (Privilege Escalation Paths)
    # 이 권한 조합을 가지면 Admin 권한으로 상승 가능
    PRIVESC_PATHS = [
        {
            "name": "CreatePolicyVersion",
            "permissions": {"iam:CreatePolicyVersion"},
            "severity": "CRITICAL",
            "description": "기존 관리형 정책에 Admin 권한 추가 가능",
        },
        {
            "name": "SetDefaultPolicyVersion",
            "permissions": {"iam:SetDefaultPolicyVersion"},
            "severity": "CRITICAL",
            "description": "과거 정책 버전으로 롤백하여 권한 변경 가능",
        },
        {
            "name": "AttachPolicy",
            "permissions": {"iam:AttachUserPolicy"},
            "severity": "CRITICAL",
            "description": "자신에게 AdministratorAccess 정책 연결 가능",
        },
        {
            "name": "PutUserPolicy",
            "permissions": {"iam:PutUserPolicy"},
            "severity": "CRITICAL",
            "description": "인라인 정책으로 Admin 권한 주입 가능",
        },
        {
            "name": "CreateAccessKey",
            "permissions": {"iam:CreateAccessKey"},
            "severity": "HIGH",
            "description": "다른 Admin 유저의 Access Key 생성 가능",
        },
        {
            "name": "UpdateAssumeRolePolicy",
            "permissions": {"iam:UpdateAssumeRolePolicy"},
            "severity": "CRITICAL",
            "description": "Role의 Trust Policy 변경하여 Assume 가능",
        },
        {
            "name": "PassRole-Lambda",
            "permissions": {
                "iam:PassRole",
                "lambda:CreateFunction",
                "lambda:InvokeFunction",
            },
            "severity": "HIGH",
            "description": "Lambda에 Admin Role 붙여서 실행",
        },
        {
            "name": "PassRole-EC2",
            "permissions": {"iam:PassRole", "ec2:RunInstances"},
            "severity": "HIGH",
            "description": "EC2 인스턴스 프로필에서 고권한 Credential 탈취",
        },
        {
            "name": "PassRole-CloudFormation",
            "permissions": {"iam:PassRole", "cloudformation:CreateStack"},
            "severity": "HIGH",
            "description": "CloudFormation으로 IAM 리소스 직접 생성",
        },
        {
            "name": "PassRole-Glue",
            "permissions": {"iam:PassRole", "glue:CreateDevEndpoint"},
            "severity": "HIGH",
            "description": "Glue Dev Endpoint에 Admin Role 붙여서 실행",
        },
        {
            "name": "PassRole-SageMaker",
            "permissions": {"iam:PassRole", "sagemaker:CreateNotebookInstance"},
            "severity": "HIGH",
            "description": "SageMaker 노트북에 Admin Role 연결",
        },
        {
            "name": "PassRole-ECS",
            "permissions": {
                "iam:PassRole",
                "ecs:RegisterTaskDefinition",
                "ecs:RunTask",
            },
            "severity": "HIGH",
            "description": "ECS Task에 Admin Role로 실행",
        },
        {
            "name": "SSM-RunCommand",
            "permissions": {"ssm:SendCommand"},
            "severity": "HIGH",
            "description": "SSM으로 EC2에서 명령 실행하여 Credential 탈취",
        },
        {
            "name": "CodeBuild-Role",
            "permissions": {
                "iam:PassRole",
                "codebuild:CreateProject",
                "codebuild:StartBuild",
            },
            "severity": "HIGH",
            "description": "CodeBuild에 Admin Role로 빌드 실행",
        },
    ]

    # FullAccess 정책 → 암묵적 권한 매핑
    # 해당 정책이 있으면 이 권한들을 갖는다고 가정
    FULLACCESS_POLICY_PERMISSIONS = {
        "IAMFullAccess": {
            "iam:CreatePolicyVersion",
            "iam:SetDefaultPolicyVersion",
            "iam:AttachUserPolicy",
            "iam:AttachGroupPolicy",
            "iam:AttachRolePolicy",
            "iam:PutUserPolicy",
            "iam:PutGroupPolicy",
            "iam:PutRolePolicy",
            "iam:CreateAccessKey",
            "iam:UpdateAssumeRolePolicy",
            "iam:PassRole",
        },
        "AdministratorAccess": {
            "iam:CreatePolicyVersion",
            "iam:SetDefaultPolicyVersion",
            "iam:AttachUserPolicy",
            "iam:PutUserPolicy",
            "iam:CreateAccessKey",
            "iam:UpdateAssumeRolePolicy",
            "iam:PassRole",
            "lambda:CreateFunction",
            "lambda:InvokeFunction",
            "ec2:RunInstances",
            "cloudformation:CreateStack",
            "glue:CreateDevEndpoint",
            "sagemaker:CreateNotebookInstance",
            "ecs:RegisterTaskDefinition",
            "ecs:RunTask",
            "ssm:SendCommand",
            "codebuild:CreateProject",
            "codebuild:StartBuild",
        },
        "PowerUserAccess": {
            "lambda:CreateFunction",
            "lambda:InvokeFunction",
            "ec2:RunInstances",
            "cloudformation:CreateStack",
            "glue:CreateDevEndpoint",
            "sagemaker:CreateNotebookInstance",
            "ecs:RegisterTaskDefinition",
            "ecs:RunTask",
            "ssm:SendCommand",
            "codebuild:CreateProject",
            "codebuild:StartBuild",
        },
        "AWSLambdaFullAccess": {
            "lambda:CreateFunction",
            "lambda:InvokeFunction",
        },
        "AmazonEC2FullAccess": {
            "ec2:RunInstances",
        },
        "AWSCloudFormationFullAccess": {
            "cloudformation:CreateStack",
        },
        "AWSGlueConsoleFullAccess": {
            "glue:CreateDevEndpoint",
        },
        "AmazonSageMakerFullAccess": {
            "sagemaker:CreateNotebookInstance",
        },
        "AmazonECS_FullAccess": {
            "ecs:RegisterTaskDefinition",
            "ecs:RunTask",
        },
        "AmazonSSMFullAccess": {
            "ssm:SendCommand",
        },
        "AWSCodeBuildAdminAccess": {
            "codebuild:CreateProject",
            "codebuild:StartBuild",
        },
    }

    # 임계값 설정
    OLD_KEY_THRESHOLD_DAYS = 90
    UNUSED_THRESHOLD_DAYS = 90
    WEAK_PASSWORD_MIN_LENGTH = 14

    def __init__(self, iam_data: IAMData):
        self.iam_data = iam_data

    def analyze(self) -> IAMAnalysisResult:
        """전체 분석 실행"""
        result = IAMAnalysisResult(
            account_id=self.iam_data.account_id,
            account_name=self.iam_data.account_name,
        )

        # 1. Users 분석
        for user in self.iam_data.users:
            user_result = self._analyze_user(user)
            result.user_results.append(user_result)

            # Access Keys 분석
            for key in user.access_keys:
                key_result = self._analyze_access_key(key)
                result.key_results.append(key_result)

        # 2. Roles 분석
        for role in self.iam_data.roles:
            role_result = self._analyze_role(role)
            result.role_results.append(role_result)

        # 2-1. Groups 분석
        for group in self.iam_data.groups:
            group_result = self._analyze_group(group)
            result.group_results.append(group_result)

        # 3. Password Policy 분석
        if self.iam_data.password_policy:
            result.policy_result = self._analyze_password_policy(self.iam_data.password_policy)

        # 4. Account 분석
        if self.iam_data.account_summary:
            result.account_result = self._analyze_account(self.iam_data.account_summary)

        return result

    def _analyze_user(self, user: IAMUser) -> UserAnalysisResult:
        """User 분석"""
        result = UserAnalysisResult(
            user=user,
            account_id=self.iam_data.account_id,
            account_name=self.iam_data.account_name,
        )

        # 1. MFA 미설정 (Console 접근 가능한 경우)
        if user.has_console_access and not user.has_mfa:
            result.issues.append(
                Issue(
                    issue_type=IssueType.NO_MFA,
                    severity=Severity.HIGH,
                    description=f"사용자 '{user.user_name}'에 MFA가 설정되지 않음",
                    recommendation="MFA 디바이스를 등록하세요",
                )
            )

        # 2. 비활성 사용자 (90일 이상 로그인 없음)
        if user.has_console_access and user.days_since_last_login >= self.UNUSED_THRESHOLD_DAYS:
            result.issues.append(
                Issue(
                    issue_type=IssueType.INACTIVE_USER,
                    severity=Severity.MEDIUM,
                    description=f"사용자 '{user.user_name}'가 {user.days_since_last_login}일간 로그인하지 않음",
                    recommendation="계정 비활성화 또는 삭제를 검토하세요",
                )
            )

        # 3. 다중 Active Access Key
        if user.active_key_count > 1:
            result.issues.append(
                Issue(
                    issue_type=IssueType.MULTIPLE_ACCESS_KEYS,
                    severity=Severity.LOW,
                    description=f"사용자 '{user.user_name}'에 {user.active_key_count}개의 활성 Access Key가 있음",
                    recommendation="불필요한 Access Key를 비활성화하거나 삭제하세요",
                )
            )

        # 4. 인증 수단 없음
        if not user.has_console_access and user.active_key_count == 0:
            result.issues.append(
                Issue(
                    issue_type=IssueType.NO_PASSWORD_NO_KEY,
                    severity=Severity.LOW,
                    description=f"사용자 '{user.user_name}'에 활성화된 인증 수단이 없음",
                    recommendation="사용하지 않는 계정이면 삭제를 검토하세요",
                )
            )

        # 5. iam:PassRole 와일드카드 (권한 상승 위험)
        if user.has_passrole_wildcard:
            result.issues.append(
                Issue(
                    issue_type=IssueType.PASSROLE_WILDCARD,
                    severity=Severity.CRITICAL,
                    description=f"사용자 '{user.user_name}'에 iam:PassRole (Resource: *) 권한 존재",
                    recommendation="PassRole 권한을 특정 Role로 제한하세요. 권한 상승 공격에 취약합니다.",
                )
            )

        # 6. 위험한 IAM 권한
        if user.dangerous_permissions:
            # PassRole wildcard는 이미 위에서 처리
            other_perms = [p for p in user.dangerous_permissions if "PassRole" not in p]
            if other_perms:
                result.issues.append(
                    Issue(
                        issue_type=IssueType.DANGEROUS_PERMISSIONS,
                        severity=Severity.HIGH,
                        description=f"사용자 '{user.user_name}'에 위험한 권한: {', '.join(other_perms[:3])}",
                        recommendation="불필요한 IAM 권한을 제거하세요. 권한 상승 공격에 취약합니다.",
                    )
                )

        # 7. 권한 상승 경로 탐지 (Privilege Escalation Paths)
        privesc_paths = self._check_privesc_paths(
            dangerous_permissions=user.dangerous_permissions,
            attached_policies=user.attached_policies,
            has_passrole_wildcard=user.has_passrole_wildcard,
        )
        if privesc_paths:
            # user.privesc_paths에 경로명 저장
            user.privesc_paths = [p["name"] for p in privesc_paths]

            # CRITICAL 경로와 HIGH 경로 분리
            critical_paths = [p for p in privesc_paths if p["severity"] == "CRITICAL"]
            high_paths = [p for p in privesc_paths if p["severity"] == "HIGH"]

            if critical_paths:
                path_names = ", ".join(p["name"] for p in critical_paths[:3])
                result.issues.append(
                    Issue(
                        issue_type=IssueType.PRIVESC_PATH,
                        severity=Severity.CRITICAL,
                        description=f"사용자 '{user.user_name}'에 권한 상승 경로 탐지: {path_names}",
                        recommendation="즉시 불필요한 권한을 제거하세요. Admin 권한 탈취 가능!",
                    )
                )
            elif high_paths:
                path_names = ", ".join(p["name"] for p in high_paths[:3])
                result.issues.append(
                    Issue(
                        issue_type=IssueType.PRIVESC_PATH,
                        severity=Severity.HIGH,
                        description=f"사용자 '{user.user_name}'에 권한 상승 경로 탐지: {path_names}",
                        recommendation="PassRole 권한과 서비스 실행 권한 조합을 검토하세요.",
                    )
                )

        # Risk Score 계산
        result.risk_score = self._calculate_user_risk_score(result)

        return result

    def _analyze_access_key(self, key: IAMAccessKey) -> KeyAnalysisResult:
        """Access Key 분석"""
        result = KeyAnalysisResult(
            key=key,
            account_id=self.iam_data.account_id,
            account_name=self.iam_data.account_name,
        )

        # Active 키만 분석
        if key.status != "Active":
            return result

        # 1. 오래된 Access Key (90일 이상)
        if key.age_days >= self.OLD_KEY_THRESHOLD_DAYS:
            result.issues.append(
                Issue(
                    issue_type=IssueType.OLD_ACCESS_KEY,
                    severity=Severity.HIGH,
                    description=f"Access Key '{key.access_key_id[:8]}...'가 {key.age_days}일 경과",
                    recommendation="Access Key를 로테이션하세요",
                )
            )

        # 2. 미사용 Access Key (90일 이상 사용 없음)
        if key.days_since_last_use == -1:
            # 한 번도 사용되지 않음
            if key.age_days >= self.UNUSED_THRESHOLD_DAYS:
                result.issues.append(
                    Issue(
                        issue_type=IssueType.UNUSED_ACCESS_KEY,
                        severity=Severity.MEDIUM,
                        description=f"Access Key '{key.access_key_id[:8]}...'가 생성 후 한 번도 사용되지 않음 ({key.age_days}일 경과)",
                        recommendation="사용하지 않는 Access Key는 비활성화하거나 삭제하세요",
                    )
                )
        elif key.days_since_last_use >= self.UNUSED_THRESHOLD_DAYS:
            result.issues.append(
                Issue(
                    issue_type=IssueType.UNUSED_ACCESS_KEY,
                    severity=Severity.MEDIUM,
                    description=f"Access Key '{key.access_key_id[:8]}...'가 {key.days_since_last_use}일간 사용되지 않음",
                    recommendation="사용하지 않는 Access Key는 비활성화하거나 삭제하세요",
                )
            )

        return result

    def _analyze_role(self, role: IAMRole) -> RoleAnalysisResult:
        """Role 분석"""
        result = RoleAnalysisResult(
            role=role,
            account_id=self.iam_data.account_id,
            account_name=self.iam_data.account_name,
        )

        # Service-linked role은 제외
        if role.is_service_linked:
            return result

        # 1. 미사용 Role (90일 이상)
        if role.days_since_last_use == -1:
            # 한 번도 사용되지 않음
            if role.age_days >= self.UNUSED_THRESHOLD_DAYS:
                result.issues.append(
                    Issue(
                        issue_type=IssueType.UNUSED_ROLE,
                        severity=Severity.MEDIUM,
                        description=f"Role '{role.role_name}'이 생성 후 한 번도 사용되지 않음 ({role.age_days}일 경과)",
                        recommendation="사용하지 않는 Role은 삭제를 검토하세요",
                    )
                )
        elif role.days_since_last_use >= self.UNUSED_THRESHOLD_DAYS:
            result.issues.append(
                Issue(
                    issue_type=IssueType.UNUSED_ROLE,
                    severity=Severity.MEDIUM,
                    description=f"Role '{role.role_name}'이 {role.days_since_last_use}일간 사용되지 않음",
                    recommendation="사용하지 않는 Role은 삭제를 검토하세요",
                )
            )

        # 2. 관리자 권한 보유
        if role.has_admin_access:
            result.issues.append(
                Issue(
                    issue_type=IssueType.ADMIN_ACCESS,
                    severity=Severity.MEDIUM,
                    description=f"Role '{role.role_name}'이 관리자 수준 권한 보유",
                    recommendation="최소 권한 원칙에 따라 권한을 제한하세요",
                )
            )

        # 3. iam:PassRole 와일드카드 (권한 상승 위험)
        if role.has_passrole_wildcard:
            result.issues.append(
                Issue(
                    issue_type=IssueType.PASSROLE_WILDCARD,
                    severity=Severity.CRITICAL,
                    description=f"Role '{role.role_name}'에 iam:PassRole (Resource: *) 권한 존재",
                    recommendation="PassRole 권한을 특정 Role로 제한하세요. 권한 상승 공격에 취약합니다.",
                )
            )

        # 4. 위험한 IAM 권한
        if role.dangerous_permissions:
            other_perms = [p for p in role.dangerous_permissions if "PassRole" not in p]
            if other_perms:
                result.issues.append(
                    Issue(
                        issue_type=IssueType.DANGEROUS_PERMISSIONS,
                        severity=Severity.HIGH,
                        description=f"Role '{role.role_name}'에 위험한 권한: {', '.join(other_perms[:3])}",
                        recommendation="불필요한 IAM 권한을 제거하세요. 권한 상승 공격에 취약합니다.",
                    )
                )

        # 5. Trust Policy 위험 - Public Trust (Principal: *)
        if role.has_public_trust:
            result.issues.append(
                Issue(
                    issue_type=IssueType.PUBLIC_TRUST_POLICY,
                    severity=Severity.CRITICAL,
                    description=f"Role '{role.role_name}' - 누구나 Assume 가능 (Principal: *)",
                    recommendation="Trust Policy에서 Principal을 특정 계정/서비스로 제한하세요. 즉시 수정 필요!",
                )
            )

        # 6. Trust Policy 위험 - 외부 계정 ExternalId 없음
        if role.has_external_without_condition:
            external_accounts = ", ".join(role.external_account_ids[:3])
            if len(role.external_account_ids) > 3:
                external_accounts += f" 외 {len(role.external_account_ids) - 3}개"
            result.issues.append(
                Issue(
                    issue_type=IssueType.EXTERNAL_ACCOUNT_NO_CONDITION,
                    severity=Severity.HIGH,
                    description=f"Role '{role.role_name}' - 외부 계정({external_accounts}) ExternalId 조건 없음",
                    recommendation="Cross-account 신뢰에 sts:ExternalId 조건을 추가하세요. Confused Deputy 공격 취약.",
                )
            )

        # 7. 권한 상승 경로 탐지 (Privilege Escalation Paths)
        privesc_paths = self._check_privesc_paths(
            dangerous_permissions=role.dangerous_permissions,
            attached_policies=role.attached_policies,
            has_passrole_wildcard=role.has_passrole_wildcard,
        )
        if privesc_paths:
            # role.privesc_paths에 경로명 저장
            role.privesc_paths = [p["name"] for p in privesc_paths]

            # CRITICAL 경로와 HIGH 경로 분리
            critical_paths = [p for p in privesc_paths if p["severity"] == "CRITICAL"]
            high_paths = [p for p in privesc_paths if p["severity"] == "HIGH"]

            if critical_paths:
                path_names = ", ".join(p["name"] for p in critical_paths[:3])
                result.issues.append(
                    Issue(
                        issue_type=IssueType.PRIVESC_PATH,
                        severity=Severity.CRITICAL,
                        description=f"Role '{role.role_name}'에 권한 상승 경로 탐지: {path_names}",
                        recommendation="즉시 불필요한 권한을 제거하세요. Admin 권한 탈취 가능!",
                    )
                )
            elif high_paths:
                path_names = ", ".join(p["name"] for p in high_paths[:3])
                result.issues.append(
                    Issue(
                        issue_type=IssueType.PRIVESC_PATH,
                        severity=Severity.HIGH,
                        description=f"Role '{role.role_name}'에 권한 상승 경로 탐지: {path_names}",
                        recommendation="PassRole 권한과 서비스 실행 권한 조합을 검토하세요.",
                    )
                )

        # Risk Score 계산
        result.risk_score = self._calculate_role_risk_score(result)

        return result

    def _analyze_group(self, group: IAMGroup) -> GroupAnalysisResult:
        """Group 분석"""
        result = GroupAnalysisResult(
            group=group,
            account_id=self.iam_data.account_id,
            account_name=self.iam_data.account_name,
        )

        # 1. 멤버 없는 그룹
        if group.member_count == 0:
            result.issues.append(
                Issue(
                    issue_type=IssueType.EMPTY_GROUP,
                    severity=Severity.LOW,
                    description=f"그룹 '{group.group_name}'에 멤버가 없음",
                    recommendation="사용하지 않는 그룹은 삭제를 검토하세요",
                )
            )

        # 2. 관리자 권한 보유
        if group.has_admin_access:
            result.issues.append(
                Issue(
                    issue_type=IssueType.GROUP_ADMIN_ACCESS,
                    severity=Severity.MEDIUM,
                    description=f"그룹 '{group.group_name}'이 관리자 수준 권한 보유 (멤버: {group.member_count}명)",
                    recommendation="그룹 멤버를 검토하고 최소 권한 원칙을 적용하세요",
                )
            )

        # 3. 위험한 권한
        if group.dangerous_permissions:
            perms = ", ".join(group.dangerous_permissions[:3])
            result.issues.append(
                Issue(
                    issue_type=IssueType.GROUP_DANGEROUS_PERMISSIONS,
                    severity=Severity.HIGH,
                    description=f"그룹 '{group.group_name}'에 위험한 권한: {perms}",
                    recommendation="그룹 정책에서 불필요한 IAM 권한을 제거하세요",
                )
            )

        return result

    def _analyze_password_policy(self, policy: PasswordPolicy) -> PolicyAnalysisResult:
        """Password Policy 분석"""
        result = PolicyAnalysisResult(
            policy=policy,
            account_id=self.iam_data.account_id,
            account_name=self.iam_data.account_name,
        )

        if not policy.exists:
            result.issues.append(
                Issue(
                    issue_type=IssueType.NO_PASSWORD_POLICY,
                    severity=Severity.HIGH,
                    description="계정에 비밀번호 정책이 설정되지 않음",
                    recommendation="강력한 비밀번호 정책을 설정하세요",
                )
            )
            result.score = 0
            return result

        # 정책 점수 계산
        score = 0
        issues = []

        # 최소 길이 (최대 20점)
        if policy.minimum_length >= 14:
            score += 20
        elif policy.minimum_length >= 12:
            score += 15
        elif policy.minimum_length >= 8:
            score += 10
        else:
            issues.append("최소 비밀번호 길이가 8자 미만")

        # 복잡성 요구사항 (각 10점, 최대 40점)
        if policy.require_symbols:
            score += 10
        else:
            issues.append("특수문자 요구 없음")

        if policy.require_numbers:
            score += 10
        else:
            issues.append("숫자 요구 없음")

        if policy.require_uppercase:
            score += 10
        else:
            issues.append("대문자 요구 없음")

        if policy.require_lowercase:
            score += 10
        else:
            issues.append("소문자 요구 없음")

        # 비밀번호 만료 (20점)
        if policy.expire_passwords and policy.max_password_age <= 90:
            score += 20
        elif policy.expire_passwords:
            score += 10
            issues.append(f"비밀번호 만료 주기가 {policy.max_password_age}일로 너무 김")
        else:
            issues.append("비밀번호 만료 설정 없음")

        # 비밀번호 재사용 방지 (20점)
        if policy.password_reuse_prevention >= 12:
            score += 20
        elif policy.password_reuse_prevention >= 6:
            score += 10
        elif policy.password_reuse_prevention > 0:
            score += 5
        else:
            issues.append("비밀번호 재사용 방지 설정 없음")

        result.score = score

        if issues:
            result.issues.append(
                Issue(
                    issue_type=IssueType.WEAK_PASSWORD_POLICY,
                    severity=Severity.MEDIUM if score >= 50 else Severity.HIGH,
                    description=f"비밀번호 정책이 취약함: {'; '.join(issues)}",
                    recommendation="AWS 권장 비밀번호 정책을 적용하세요",
                )
            )

        return result

    def _analyze_account(self, summary: AccountSummary) -> AccountAnalysisResult:
        """Account 분석"""
        result = AccountAnalysisResult(summary=summary)

        # 1. Root Access Key 존재
        if summary.root_access_keys_present:
            result.issues.append(
                Issue(
                    issue_type=IssueType.ROOT_ACCESS_KEY,
                    severity=Severity.CRITICAL,
                    description="Root 계정에 Access Key가 존재함",
                    recommendation="Root Access Key를 즉시 삭제하세요",
                )
            )

        # 2. Root MFA 미설정
        if not summary.root_mfa_active:
            result.issues.append(
                Issue(
                    issue_type=IssueType.ROOT_NO_MFA,
                    severity=Severity.CRITICAL,
                    description="Root 계정에 MFA가 설정되지 않음",
                    recommendation="Root 계정에 MFA를 즉시 설정하세요",
                )
            )

        return result

    def _calculate_user_risk_score(self, result: UserAnalysisResult) -> int:
        """User 위험 점수 계산 (0-100)"""
        score = 0

        for issue in result.issues:
            if issue.severity == Severity.CRITICAL:
                score += 40
            elif issue.severity == Severity.HIGH:
                score += 25
            elif issue.severity == Severity.MEDIUM:
                score += 15
            elif issue.severity == Severity.LOW:
                score += 5

        return min(score, 100)

    def _calculate_role_risk_score(self, result: RoleAnalysisResult) -> int:
        """Role 위험 점수 계산 (0-100)"""
        score = 0

        for issue in result.issues:
            if issue.severity == Severity.CRITICAL:
                score += 40
            elif issue.severity == Severity.HIGH:
                score += 25
            elif issue.severity == Severity.MEDIUM:
                score += 15
            elif issue.severity == Severity.LOW:
                score += 5

        return min(score, 100)

    def get_summary_stats(self, result: IAMAnalysisResult) -> dict[str, Any]:
        """분석 결과 요약 통계"""
        stats: dict[str, Any] = {
            "account_id": result.account_id,
            "account_name": result.account_name,
            # User 통계
            "total_users": len(result.user_results),
            "users_without_mfa": 0,
            "inactive_users": 0,
            "users_with_issues": 0,
            # Access Key 통계
            "total_active_keys": 0,
            "old_keys": 0,
            "unused_keys": 0,
            # Role 통계
            "total_roles": len(result.role_results),
            "unused_roles": 0,
            "admin_roles": 0,
            # Password Policy
            "password_policy_score": 0,
            # Account 이슈
            "root_access_key": False,
            "root_mfa": True,
            # 전체 이슈 수
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 0,
            "low_issues": 0,
        }

        # User 분석
        for user_result in result.user_results:
            if user_result.issues:
                stats["users_with_issues"] += 1

            for issue in user_result.issues:
                if issue.issue_type == IssueType.NO_MFA:
                    stats["users_without_mfa"] += 1
                elif issue.issue_type == IssueType.INACTIVE_USER:
                    stats["inactive_users"] += 1

                self._count_severity(stats, issue.severity)

        # Access Key 분석
        for key_result in result.key_results:
            if key_result.key.status == "Active":
                stats["total_active_keys"] += 1

            for issue in key_result.issues:
                if issue.issue_type == IssueType.OLD_ACCESS_KEY:
                    stats["old_keys"] += 1
                elif issue.issue_type == IssueType.UNUSED_ACCESS_KEY:
                    stats["unused_keys"] += 1

                self._count_severity(stats, issue.severity)

        # Role 분석
        for role_result in result.role_results:
            for issue in role_result.issues:
                if issue.issue_type == IssueType.UNUSED_ROLE:
                    stats["unused_roles"] += 1
                elif issue.issue_type == IssueType.ADMIN_ACCESS:
                    stats["admin_roles"] += 1

                self._count_severity(stats, issue.severity)

        # Password Policy
        if result.policy_result:
            stats["password_policy_score"] = result.policy_result.score
            for issue in result.policy_result.issues:
                self._count_severity(stats, issue.severity)

        # Account
        if result.account_result:
            for issue in result.account_result.issues:
                if issue.issue_type == IssueType.ROOT_ACCESS_KEY:
                    stats["root_access_key"] = True
                elif issue.issue_type == IssueType.ROOT_NO_MFA:
                    stats["root_mfa"] = False

                self._count_severity(stats, issue.severity)

        return stats

    def _count_severity(self, stats: dict, severity: Severity) -> None:
        """심각도별 이슈 카운트"""
        if severity == Severity.CRITICAL:
            stats["critical_issues"] += 1
        elif severity == Severity.HIGH:
            stats["high_issues"] += 1
        elif severity == Severity.MEDIUM:
            stats["medium_issues"] += 1
        elif severity == Severity.LOW:
            stats["low_issues"] += 1

    def _check_privesc_paths(
        self,
        dangerous_permissions: list[str],
        attached_policies: list[str],
        has_passrole_wildcard: bool,
    ) -> list[dict[str, Any]]:
        """권한 상승 경로(Privilege Escalation Paths) 탐지

        Args:
            dangerous_permissions: 탐지된 위험 권한 목록
            attached_policies: 연결된 정책 이름 목록
            has_passrole_wildcard: iam:PassRole (Resource: *) 권한 보유 여부

        Returns:
            탐지된 privesc 경로 목록 (name, severity, description 포함)
        """
        # 1. 실제 권한 집합 구성
        effective_permissions: set[str] = set()

        # 1-1. dangerous_permissions에서 권한 추출
        for perm in dangerous_permissions:
            # "iam:CreatePolicyVersion" 형태
            if perm.startswith("iam:") and "(" not in perm:
                effective_permissions.add(perm)
            # "iam:* (Full IAM Access)" 형태 → 모든 IAM 권한
            elif "iam:*" in perm or "Full IAM Access" in perm:
                # IAM 전체 권한이면 모든 IAM 관련 privesc 경로 권한 추가
                for path in self.PRIVESC_PATHS:
                    for p in path["permissions"]:
                        if p.startswith("iam:"):
                            effective_permissions.add(p)

        # 1-2. PassRole wildcard가 있으면 iam:PassRole 추가
        if has_passrole_wildcard:
            effective_permissions.add("iam:PassRole")

        # 1-3. FullAccess 정책에서 암묵적 권한 추가
        for policy_name in attached_policies:
            if policy_name in self.FULLACCESS_POLICY_PERMISSIONS:
                effective_permissions.update(self.FULLACCESS_POLICY_PERMISSIONS[policy_name])

        # 2. 각 privesc 경로 검사
        detected_paths = []
        for path in self.PRIVESC_PATHS:
            required_perms: set[str] = set(path["permissions"])
            # 모든 필요 권한이 effective_permissions에 있는지 확인
            if required_perms.issubset(effective_permissions):
                detected_paths.append(
                    {
                        "name": path["name"],
                        "severity": path["severity"],
                        "description": path["description"],
                        "permissions": list(required_perms),
                    }
                )

        return detected_paths
