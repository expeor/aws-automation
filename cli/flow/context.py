# cli/flow/context.py
"""
실행 컨텍스트 정의

도구 실행에 필요한 모든 정보를 담는 컨텍스트 클래스입니다.
각 Step에서 컨텍스트를 점진적으로 채워나가며, 최종적으로 도구 실행에 사용됩니다.

주요 컴포넌트:
    Enum 타입:
        - ProviderKind: 인증 Provider 종류 (SSO_SESSION, SSO_PROFILE, STATIC, etc.)
        - FallbackStrategy: Role Fallback 전략 (USE_FALLBACK, SKIP_ACCOUNT)

    데이터 클래스:
        - RoleSelection: Role 선택 결과 (primary, fallback, 계정 매핑)
        - ToolInfo: 도구 정보 (name, description, permission, runner)
        - AuthContext: 인증 관련 정보 (분리된 컨텍스트)
        - ToolContext: 도구 관련 정보 (분리된 컨텍스트)
        - ExecutionContext: 통합 실행 컨텍스트 (하위 호환성)
        - FlowResult: Flow 실행 결과

    예외 클래스:
        - BackToMenu: 이전 메뉴 복귀 예외 (BackToMenuError 상속)

Context 분리 설계:
    AuthContext + ToolContext → ExecutionContext

    기존 코드 호환성을 위해 ExecutionContext를 유지하면서,
    새 코드에서는 AuthContext/ToolContext를 직접 사용 가능합니다.

Flow 단계별 컨텍스트 채우기:
    Step 1: 카테고리/도구 선택 → category, tool
    Step 2: 프로파일 선택 → profile_name, provider_kind, provider
    Step 3: Role 선택 (SSO) → role_selection, accounts
    Step 4: 리전 선택 → regions
    Step 5: 옵션 수집 → options

Usage:
    from cli.flow.context import ExecutionContext, ProviderKind, ToolInfo

    # 컨텍스트 생성 및 점진적 채우기
    ctx = ExecutionContext()
    ctx.category = "ec2"
    ctx.tool = ToolInfo(
        name="미사용 EC2",
        description="미사용 EC2 인스턴스 검색",
        category="ec2",
        permission="read",
    )
    ctx.provider_kind = ProviderKind.SSO_SESSION
    ctx.regions = ["ap-northeast-2", "us-east-1"]

    # SSO 인증 확인
    if ctx.is_sso():
        print("SSO 인증 사용")

    # 특정 계정의 실제 Role 확인
    role = ctx.get_effective_role("123456789012")

    # 실행 대상 계정 목록 (스킵 계정 제외)
    target_accounts = ctx.get_target_accounts()
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from core.auth import AccountInfo, Provider

# core.exceptions에서 BackToMenuError 재사용
from core.exceptions import BackToMenuError


class BackToMenu(BackToMenuError):
    """이전 메뉴로 돌아가기 예외

    각 Step에서 사용자가 '0'을 입력하면 발생.
    runner에서 이를 catch하여 이전 단계로 돌아감.

    Deprecated: core.exceptions.BackToMenuError 사용 권장
    """

    def __init__(self, step_name: str = "unknown"):
        super().__init__(step_name)


class ProviderKind(Enum):
    """인증 Provider 종류"""

    SSO_SESSION = "sso_session"
    SSO_PROFILE = "sso_profile"
    STATIC_CREDENTIALS = "static"


class FallbackStrategy(Enum):
    """Role Fallback 전략"""

    USE_FALLBACK = "use_fallback"  # Fallback Role 사용 (기본값)
    SKIP_ACCOUNT = "skip"  # 해당 계정 스킵


@dataclass
class RoleSelection:
    """Role 선택 결과"""

    primary_role: str
    fallback_role: Optional[str] = None
    fallback_strategy: FallbackStrategy = FallbackStrategy.USE_FALLBACK

    # Role별 계정 매핑 (role_name -> [account_ids])
    role_account_map: Dict[str, List[str]] = field(default_factory=dict)

    # 스킵될 계정 목록
    skipped_accounts: List[str] = field(default_factory=list)


@dataclass
class ToolInfo:
    """도구 정보"""

    name: str
    description: str
    category: str
    permission: str  # "read", "write", "delete"

    # 도구 실행 함수
    runner: Optional[Callable[["ExecutionContext"], Any]] = None

    # 도구별 추가 옵션 수집 함수 (Optional)
    options_collector: Optional[Callable[["ExecutionContext"], Dict[str, Any]]] = None

    # 선택 제약 옵션
    supports_single_region_only: bool = False  # 단일 리전만 지원
    supports_single_account_only: bool = False  # 단일 계정만 지원 (SSO)
    is_global: bool = False  # Global 서비스 (IAM, Route53 등) - 리전 선택 스킵


@dataclass
class AuthContext:
    """인증 컨텍스트

    인증 관련 정보만 분리하여 관리합니다.
    Provider, 계정, 역할 정보를 담습니다.

    Attributes:
        profile_name: 선택된 프로파일 이름 (SSO용, 단일)
        profiles: 선택된 프로파일 목록 (Static/MultiAccount용, 다중)
        provider_kind: 인증 Provider 종류
        provider: 인증 Provider 인스턴스 (SSO용)
        role_selection: Role 선택 정보 (SSO 전용)
        accounts: 대상 계정 목록 (SSO용)
        regions: 대상 리전 목록
    """

    profile_name: Optional[str] = None
    profiles: List[str] = field(default_factory=list)
    provider_kind: Optional[ProviderKind] = None
    provider: Optional["Provider"] = None
    role_selection: Optional[RoleSelection] = None
    accounts: List["AccountInfo"] = field(default_factory=list)
    regions: List[str] = field(default_factory=list)

    def is_sso(self) -> bool:
        """SSO 기반 인증인지 확인"""
        return self.provider_kind in (
            ProviderKind.SSO_SESSION,
            ProviderKind.SSO_PROFILE,
        )

    def is_sso_session(self) -> bool:
        """SSO Session 기반 인증인지 확인"""
        return self.provider_kind == ProviderKind.SSO_SESSION

    def is_sso_profile(self) -> bool:
        """SSO Profile 기반 인증인지 확인"""
        return self.provider_kind == ProviderKind.SSO_PROFILE

    def is_multi_profile(self) -> bool:
        """다중 프로파일이 선택되었는지 확인

        Static 또는 SSO Profile에서 여러 프로파일을 선택한 경우 True.
        프로파일 순차 실행 시 사용.
        """
        return len(self.profiles) > 1

    def is_multi_account(self) -> bool:
        """멀티 계정 지원 인증인지 확인"""
        return self.provider_kind == ProviderKind.SSO_SESSION

    def needs_role_selection(self) -> bool:
        """역할 선택이 필요한지 확인"""
        return self.provider_kind == ProviderKind.SSO_SESSION

    def get_effective_role(self, account_id: str) -> Optional[str]:
        """특정 계정에 대한 실제 사용할 Role 반환"""
        if not self.role_selection:
            return None

        rs = self.role_selection
        primary_accounts = rs.role_account_map.get(rs.primary_role, [])
        if account_id in primary_accounts:
            return rs.primary_role

        if rs.fallback_strategy == FallbackStrategy.SKIP_ACCOUNT:
            return None

        if rs.fallback_role:
            fallback_accounts = rs.role_account_map.get(rs.fallback_role, [])
            if account_id in fallback_accounts:
                return rs.fallback_role

        return None

    def get_target_accounts(self) -> List["AccountInfo"]:
        """실제 실행 대상 계정 목록 반환"""
        if not self.role_selection:
            return self.accounts

        skipped = set(self.role_selection.skipped_accounts)
        return [acc for acc in self.accounts if acc.id not in skipped]


@dataclass
class ToolContext:
    """도구 실행 컨텍스트

    도구 선택 및 실행 옵션 관련 정보를 담습니다.

    Attributes:
        category: 선택된 카테고리 (예: "ebs", "ec2")
        tool: 선택된 도구 정보
        options: 도구별 추가 옵션
    """

    category: Optional[str] = None
    tool: Optional[ToolInfo] = None
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """도구 실행 컨텍스트

    Flow의 각 단계에서 점진적으로 채워지며,
    최종적으로 도구 실행에 필요한 모든 정보를 담음.

    Attributes:
        category: 선택된 카테고리 (예: "ebs", "ec2")
        tool: 선택된 도구 정보
        profile_name: 선택된 프로파일 이름 (SSO용, 단일)
        profiles: 선택된 프로파일 목록 (Static/MultiAccount용, 다중)
        provider_kind: 인증 Provider 종류
        provider: 인증 Provider 인스턴스 (SSO용)
        role_selection: Role 선택 정보 (SSO 전용)
        accounts: 대상 계정 목록 (SSO용)
        regions: 대상 리전 목록
        options: 도구별 추가 옵션
    """

    # Step 1: 카테고리/도구 선택
    category: Optional[str] = None
    tool: Optional[ToolInfo] = None

    # Step 2: 프로파일 선택
    profile_name: Optional[str] = None  # SSO: 단일 프로파일
    profiles: List[str] = field(default_factory=list)  # Static/Multi: 다중 프로파일
    provider_kind: Optional[ProviderKind] = None
    provider: Optional["Provider"] = None  # SSO용 Provider

    # Step 3: Role 선택 (SSO 전용)
    role_selection: Optional[RoleSelection] = None

    # 대상 계정 목록 (SSO 인증 후 설정)
    accounts: List["AccountInfo"] = field(default_factory=list)

    # Step 4: 리전 선택
    regions: List[str] = field(default_factory=list)

    # Step 5: 도구별 추가 옵션
    options: Dict[str, Any] = field(default_factory=dict)

    # 실행 결과
    result: Optional[Any] = None
    error: Optional[Exception] = None

    def is_sso(self) -> bool:
        """SSO 기반 인증인지 확인 (SSO Session 또는 SSO Profile)"""
        return self.provider_kind in (
            ProviderKind.SSO_SESSION,
            ProviderKind.SSO_PROFILE,
        )

    def is_sso_session(self) -> bool:
        """SSO Session 기반 인증인지 확인 (동적 계정/역할 선택)"""
        return self.provider_kind == ProviderKind.SSO_SESSION

    def is_sso_profile(self) -> bool:
        """SSO Profile 기반 인증인지 확인 (고정 계정/역할)"""
        return self.provider_kind == ProviderKind.SSO_PROFILE

    def is_multi_profile(self) -> bool:
        """다중 프로파일이 선택되었는지 확인

        Static 또는 SSO Profile에서 여러 프로파일을 선택한 경우 True.
        SSO Session은 단일 프로파일 내에서 멀티 계정 지원 (is_multi_account).
        """
        return len(self.profiles) > 1

    def is_multi_account(self) -> bool:
        """멀티 계정 지원 인증인지 확인 (동적 계정 선택 필요)

        SSO Session만 멀티 계정 지원
        SSO Profile은 계정/역할이 고정되어 있어 단일 계정처럼 동작
        """
        return self.provider_kind == ProviderKind.SSO_SESSION

    def needs_role_selection(self) -> bool:
        """역할 선택이 필요한지 확인

        SSO Session만 역할 선택 필요
        SSO Profile은 이미 sso_role_name이 고정되어 있음
        """
        return self.provider_kind == ProviderKind.SSO_SESSION

    def get_effective_role(self, account_id: str) -> Optional[str]:
        """특정 계정에 대한 실제 사용할 Role 반환

        Args:
            account_id: AWS 계정 ID

        Returns:
            사용할 Role 이름 또는 None (스킵해야 하는 경우)
        """
        if not self.role_selection:
            return None

        rs = self.role_selection

        # Primary Role 사용 가능한 계정인지 확인
        primary_accounts = rs.role_account_map.get(rs.primary_role, [])
        if account_id in primary_accounts:
            return rs.primary_role

        # Fallback 전략에 따라 처리
        if rs.fallback_strategy == FallbackStrategy.SKIP_ACCOUNT:
            return None

        # Fallback Role 사용
        if rs.fallback_role:
            fallback_accounts = rs.role_account_map.get(rs.fallback_role, [])
            if account_id in fallback_accounts:
                return rs.fallback_role

        return None

    def get_target_accounts(self) -> List["AccountInfo"]:
        """실제 실행 대상 계정 목록 반환 (스킵 계정 제외)"""
        if not self.role_selection:
            return self.accounts

        skipped = set(self.role_selection.skipped_accounts)
        return [acc for acc in self.accounts if acc.id not in skipped]


@dataclass
class FlowResult:
    """Flow 실행 결과"""

    success: bool
    context: ExecutionContext
    message: str = ""

    # 후속 작업
    next_action: str = "home"  # "home", "category", "repeat", "exit"
