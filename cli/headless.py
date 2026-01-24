"""
cli/headless.py - Headless CLI Runner

CI/CD 파이프라인 및 자동화를 위한 비대화형 실행 모드입니다.
SSO Session, SSO Profile, Access Key 프로파일을 지원합니다.

Usage:
    # SSO Profile / Access Key
    aa run ec2/ebs_audit -p my-profile -r ap-northeast-2

    # SSO Session (멀티 계정)
    aa run ec2/ebs_audit -s my-sso --account 111122223333 --role AdminRole

    # SSO Session (전체 계정)
    aa run ec2/ebs_audit -s my-sso --account all --role AdminRole -r all

    # SSO Session + Fallback Role
    aa run ec2/ebs_audit -s my-sso --account all --role AdminRole --fallback-role ReadOnlyRole

    # 다중 리전
    aa run ec2/ebs_audit -p my-profile -r ap-northeast-2 -r us-east-1

    # JSON 출력
    aa run ec2/ebs_audit -p my-profile -f json -o result.json

옵션:
    -p, --profile: SSO Profile 또는 Access Key 프로파일
    -s, --sso-session: SSO Session 이름 (멀티 계정 지원)
    --account: 계정 ID (다중 가능, 'all'=전체) - SSO Session 전용
    --role: Primary Role 이름 - SSO Session 전용
    --fallback-role: Fallback Role 이름 (선택적) - SSO Session 전용
    -r, --region: 리전 또는 리전 패턴 (기본: ap-northeast-2)
    -f, --format: 출력 형식 (기본: both = Excel + HTML, excel, html, console, json, csv)
    -o, --output: 출력 파일 경로 (기본: 자동 생성)
    -q, --quiet: 최소 출력 모드
"""

import sys
from dataclasses import dataclass, field

from rich.console import Console

from cli.flow.context import ExecutionContext, ProviderKind, ToolInfo
from cli.i18n import t
from core.filter import expand_region_pattern

console = Console()


@dataclass
class HeadlessConfig:
    """Headless 실행 설정"""

    # 도구 지정
    category: str
    tool_module: str

    # 인증 (profile 또는 sso_session 중 하나 사용)
    profile: str | None = None

    # SSO Session 인증 (멀티 계정)
    sso_session: str | None = None
    accounts: list[str] = field(default_factory=list)  # 계정 ID 목록 또는 ["all"]
    role: str | None = None  # Primary Role
    fallback_role: str | None = None  # Fallback Role (선택적)

    # 대상
    regions: list[str] = field(default_factory=list)

    # 출력
    format: str = "both"  # excel, html, both, console, json, csv
    output: str | None = None
    quiet: bool = False


class HeadlessRunner:
    """Headless CLI Runner

    대화형 프롬프트 없이 도구를 실행합니다.
    CI/CD 파이프라인 및 스크립트 자동화에 적합합니다.
    """

    def __init__(self, config: HeadlessConfig):
        self.config = config
        self._ctx: ExecutionContext | None = None

    def run(self) -> int:
        """Headless 실행

        Returns:
            0: 성공
            1: 실패
        """
        try:
            # 1. 도구 로드 및 검증
            tool_meta = self._load_tool()
            if not tool_meta:
                return 1

            # 2. Context 구성
            self._ctx = self._build_context(tool_meta)

            # 3. 인증 및 세션 설정
            if not self._setup_auth():
                return 1

            # 4. 리전 설정
            if not self._setup_regions():
                return 1

            # 5. 실행
            return self._execute()

        except KeyboardInterrupt:
            if not self.config.quiet:
                console.print(f"\n[dim]{t('flow.cancelled')}[/dim]")
            return 130
        except Exception as e:
            console.print(f"[red]{t('flow.error_label', message=str(e))}[/red]")
            if "--debug" in sys.argv:
                import traceback

                traceback.print_exc()
            return 1

    def _load_tool(self) -> dict | None:
        """도구 메타데이터 로드"""
        from core.tools.discovery import discover_categories

        categories = discover_categories(include_aws_services=True)

        for cat in categories:
            if cat["name"] == self.config.category:
                for tool_meta in cat.get("tools", []):
                    if not isinstance(tool_meta, dict):
                        continue
                    if tool_meta.get("module") == self.config.tool_module:
                        return tool_meta

        console.print(
            f"[red]{t('flow.tool_not_found', category=self.config.category, tool=self.config.tool_module)}[/red]"
        )
        return None

    def _build_context(self, tool_meta: dict) -> ExecutionContext:
        """ExecutionContext 구성"""
        from core.tools.io.config import OutputConfig

        ctx = ExecutionContext()
        ctx.category = self.config.category
        ctx.tool = ToolInfo(
            name=tool_meta.get("name", self.config.tool_module),
            description=tool_meta.get("description", ""),
            category=self.config.category,
            permission=tool_meta.get("permission", "read"),
            supports_single_region_only=tool_meta.get("supports_single_region_only", False),
            supports_single_account_only=tool_meta.get("supports_single_account_only", False),
            is_global=tool_meta.get("is_global", False),
        )

        # 출력 설정 (format 옵션에 따라 OutputConfig 생성)
        ctx.output_config = OutputConfig.from_string(self.config.format)

        # quiet 모드이면 자동 열기 비활성화
        if self.config.quiet:
            ctx.output_config.auto_open = False

        return ctx

    def _setup_auth(self) -> bool:
        """인증 설정"""
        from core.auth.config import detect_provider_type, load_config
        from core.auth.types import ProviderType

        config = load_config()

        # SSO Session 인증
        if self.config.sso_session:
            return self._setup_sso_session(config)

        # Profile 인증
        profile_name = self.config.profile
        if not profile_name:
            console.print(f"[red]{t('flow.profile_not_found', profile='')}[/red]")
            return False

        # Profile인지 확인
        if profile_name in config.profiles:
            profile = config.profiles[profile_name]
            provider_type = detect_provider_type(profile)

            if provider_type == ProviderType.SSO_PROFILE:
                return self._setup_sso_profile()
            elif provider_type == ProviderType.STATIC_CREDENTIALS:
                return self._setup_static()
            else:
                console.print(f"[red]{t('flow.unsupported_profile_type', type=str(provider_type))}[/red]")
                return False

        # 찾을 수 없음
        console.print(f"[red]{t('flow.profile_not_found', profile=profile_name)}[/red]")
        console.print(f"[dim]{t('flow.available_profiles')}[/dim]")
        for name in list(config.profiles.keys())[:5]:
            console.print(f"  [dim]- {name}[/dim]")
        return False

    def _setup_sso_profile(self) -> bool:
        """SSO Profile 인증 설정"""
        assert self._ctx is not None
        self._ctx.provider_kind = ProviderKind.SSO_PROFILE
        self._ctx.profiles = [self.config.profile]
        self._ctx.profile_name = self.config.profile

        if not self.config.quiet:
            console.print(f"[dim]{t('flow.using_sso_profile', profile=self.config.profile)}[/dim]")

        return True

    def _setup_static(self) -> bool:
        """Static Credentials 인증 설정"""
        assert self._ctx is not None
        self._ctx.provider_kind = ProviderKind.STATIC_CREDENTIALS
        self._ctx.profiles = [self.config.profile]
        self._ctx.profile_name = self.config.profile

        if not self.config.quiet:
            console.print(f"[dim]{t('flow.using_static_profile', profile=self.config.profile)}[/dim]")

        return True

    def _setup_sso_session(self, config) -> bool:
        """SSO Session 인증 설정 (멀티 계정 지원)"""
        from core.auth.provider import SSOSessionProvider
        from core.auth.provider.sso_session import SSOSessionConfig

        assert self._ctx is not None
        session_name = self.config.sso_session

        # SSO Session 설정 확인
        if session_name not in config.sessions:
            console.print(f"[red]{t('flow.sso_session_not_found', session=session_name)}[/red]")
            console.print(f"[dim]{t('flow.available_sessions')}[/dim]")
            for name in list(config.sessions.keys())[:5]:
                console.print(f"  [dim]- {name}[/dim]")
            return False

        session_config = config.sessions[session_name]

        # Provider 생성 및 인증
        sso_config = SSOSessionConfig(
            session_name=session_name,
            start_url=session_config.get("sso_start_url", ""),
            region=session_config.get("sso_region", "us-east-1"),
        )
        provider = SSOSessionProvider(sso_config)

        if not self.config.quiet:
            console.print(f"[dim]{t('flow.authenticating_sso', session=session_name)}[/dim]")

        try:
            provider.authenticate()
        except Exception as e:
            console.print(f"[red]{t('flow.sso_auth_failed', error=str(e))}[/red]")
            return False

        # 계정 목록 조회
        all_accounts = provider.list_accounts()
        if not all_accounts:
            console.print(f"[red]{t('flow.no_accounts')}[/red]")
            return False

        # 계정 필터링
        target_accounts = []
        if "all" in [a.lower() for a in self.config.accounts]:
            target_accounts = list(all_accounts.values())
        else:
            for acc_id in self.config.accounts:
                if acc_id in all_accounts:
                    target_accounts.append(all_accounts[acc_id])
                else:
                    console.print(f"[yellow]{t('flow.account_not_found', account=acc_id)}[/yellow]")

        if not target_accounts:
            console.print(f"[red]{t('flow.no_valid_accounts')}[/red]")
            return False

        # Role 설정 및 검증
        role_selection = self._setup_role_selection(target_accounts, provider)
        if not role_selection:
            return False

        # Context 설정
        self._ctx.provider_kind = ProviderKind.SSO_SESSION
        self._ctx.provider = provider
        self._ctx.profile_name = session_name
        self._ctx.accounts = target_accounts
        self._ctx.role_selection = role_selection

        if not self.config.quiet:
            console.print(f"[dim]{t('flow.sso_session_ready', session=session_name, count=len(target_accounts))}[/dim]")

        return True

    def _setup_role_selection(self, accounts: list, provider) -> "RoleSelection | None":
        """Role 선택 설정"""
        from collections import defaultdict

        from cli.flow.context import FallbackStrategy, RoleSelection

        primary_role = self.config.role
        fallback_role = self.config.fallback_role

        # Role별 계정 매핑 생성
        role_account_map: dict[str, list[str]] = defaultdict(list)
        for account in accounts:
            for role in getattr(account, "roles", []):
                role_name = role if isinstance(role, str) else role.role_name
                role_account_map[role_name].append(account.id)

        # Primary Role 검증
        if primary_role not in role_account_map:
            console.print(f"[red]{t('flow.role_not_found', role=primary_role)}[/red]")
            console.print(f"[dim]{t('flow.available_roles')}[/dim]")
            for role_name in sorted(role_account_map.keys())[:10]:
                console.print(f"  [dim]- {role_name}[/dim]")
            return None

        primary_accounts = set(role_account_map[primary_role])
        all_account_ids = {acc.id for acc in accounts}
        missing_accounts = all_account_ids - primary_accounts

        # 모든 계정에 Primary Role이 있으면 완료
        if not missing_accounts:
            return RoleSelection(
                primary_role=primary_role,
                role_account_map=dict(role_account_map),
            )

        # Fallback 처리
        skipped_accounts: list[str] = []

        if fallback_role:
            # Fallback Role 검증
            if fallback_role not in role_account_map:
                console.print(f"[yellow]{t('flow.fallback_role_not_found', role=fallback_role)}[/yellow]")
                skipped_accounts = list(missing_accounts)
            else:
                fallback_accounts = set(role_account_map[fallback_role])
                still_missing = missing_accounts - fallback_accounts
                skipped_accounts = list(still_missing)

                if not self.config.quiet and still_missing:
                    console.print(
                        f"[yellow]{t('flow.accounts_without_roles', count=len(still_missing))}[/yellow]"
                    )
        else:
            # Fallback 없으면 해당 계정 스킵
            skipped_accounts = list(missing_accounts)
            if not self.config.quiet and missing_accounts:
                console.print(
                    f"[yellow]{t('flow.accounts_skipped_no_role', role=primary_role, count=len(missing_accounts))}[/yellow]"
                )

        return RoleSelection(
            primary_role=primary_role,
            fallback_role=fallback_role,
            fallback_strategy=FallbackStrategy.USE_FALLBACK if fallback_role else FallbackStrategy.SKIP_ACCOUNT,
            role_account_map=dict(role_account_map),
            skipped_accounts=skipped_accounts,
        )

    def _setup_regions(self) -> bool:
        """리전 설정"""
        assert self._ctx is not None
        regions: list[str] = []

        for r in self.config.regions:
            if r.lower() == "all":
                from core.region import ALL_REGIONS

                regions.extend(ALL_REGIONS)
            elif "*" in r or "?" in r:
                expanded = expand_region_pattern(r)
                regions.extend(expanded)
            else:
                regions.append(r)

        # 중복 제거
        seen: set[str] = set()
        unique_regions: list[str] = []
        for r in regions:
            if r not in seen:
                seen.add(r)
                unique_regions.append(r)

        self._ctx.regions = unique_regions

        if not self.config.quiet:
            if len(unique_regions) == 1:
                console.print(f"[dim]{t('flow.region_label')} {unique_regions[0]}[/dim]")
            else:
                console.print(
                    f"[dim]{t('flow.region_label')} {t('flow.regions_count', count=len(unique_regions))}[/dim]"
                )

        return True

    def _execute(self) -> int:
        """도구 실행"""
        assert self._ctx is not None
        assert self._ctx.tool is not None
        assert self._ctx.category is not None
        from core.tools.discovery import load_tool

        tool = load_tool(self._ctx.category, self._ctx.tool.name)
        if tool is None:
            console.print(
                f"[red]{t('flow.tool_load_failed', category=self._ctx.category, tool=self._ctx.tool.name)}[/red]"
            )
            return 1

        if not self.config.quiet:
            self._print_summary()
            console.print()

        # 실행
        run_fn = tool.get("run")
        if not run_fn:
            console.print(f"[red]{t('flow.tool_no_run_function')}[/red]")
            return 1

        self._ctx.result = run_fn(self._ctx)

        return 0

    def _print_summary(self) -> None:
        """실행 요약 출력"""
        assert self._ctx is not None
        assert self._ctx.tool is not None
        console.print(f"[bold]{self._ctx.tool.name}[/bold]")

        # SSO Session의 경우 세션 이름 + 계정 수 표시
        if self._ctx.is_sso_session():
            console.print(f"  {t('flow.session_label')} {self._ctx.profile_name}")
            target_accounts = self._ctx.get_target_accounts()
            console.print(f"  {t('flow.accounts_label')} {t('flow.accounts_count', count=len(target_accounts))}")
            if self._ctx.role_selection:
                console.print(f"  {t('flow.role_label')} {self._ctx.role_selection.primary_role}")
        else:
            console.print(f"  {t('flow.profile_label')} {self._ctx.profile_name}")

        if len(self._ctx.regions) == 1:
            console.print(f"  {t('flow.region_label')} {self._ctx.regions[0]}")
        else:
            console.print(f"  {t('flow.region_label')} {t('flow.regions_count', count=len(self._ctx.regions))}")


def run_headless(
    tool_path: str,
    profile: str | None = None,
    regions: list[str] | None = None,
    format: str = "both",
    output: str | None = None,
    quiet: bool = False,
    # SSO Session 옵션
    sso_session: str | None = None,
    accounts: list[str] | None = None,
    role: str | None = None,
    fallback_role: str | None = None,
) -> int:
    """Headless 실행 편의 함수

    SSO Session, SSO Profile, Access Key 프로파일을 지원합니다.

    Args:
        tool_path: 도구 경로 (category/module 형식)
        profile: SSO Profile 또는 Access Key 프로파일
        regions: 리전 목록
        format: 출력 형식
        output: 출력 파일 경로
        quiet: 최소 출력 모드
        sso_session: SSO Session 이름 (멀티 계정)
        accounts: 계정 ID 목록 또는 ["all"]
        role: Primary Role 이름
        fallback_role: Fallback Role 이름 (선택적)

    Returns:
        0: 성공, 1: 실패
    """
    # tool_path 파싱
    parts = tool_path.split("/")
    if len(parts) != 2:
        console.print(f"[red]{t('flow.invalid_tool_path', path=tool_path)}[/red]")
        console.print(f"[dim]{t('flow.tool_path_format_hint')}[/dim]")
        return 1

    category, tool_module = parts

    config = HeadlessConfig(
        category=category,
        tool_module=tool_module,
        profile=profile,
        sso_session=sso_session,
        accounts=accounts if accounts else [],
        role=role,
        fallback_role=fallback_role,
        regions=regions if regions else ["ap-northeast-2"],
        format=format,
        output=output,
        quiet=quiet,
    )

    runner = HeadlessRunner(config)
    return runner.run()
