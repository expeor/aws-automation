"""
cli/headless.py - Headless CLI Runner

CI/CD 파이프라인 및 자동화를 위한 비대화형 실행 모드입니다.
SSO Profile 또는 Access Key 프로파일만 지원합니다.

Usage:
    aa run ec2/ebs_audit -p my-profile -r ap-northeast-2

    # 다중 리전
    aa run ec2/ebs_audit -p my-profile -r ap-northeast-2 -r us-east-1

    # 전체 리전
    aa run ec2/ebs_audit -p my-profile -r all

    # JSON 출력
    aa run ec2/ebs_audit -p my-profile -f json -o result.json

옵션:
    -p, --profile: SSO Profile 또는 Access Key 프로파일 (필수)
    -r, --region: 리전 또는 리전 패턴 (기본: ap-northeast-2)
    -f, --format: 출력 형식 (console, json, csv)
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

    # 인증
    profile: str

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
        profile_name = self.config.profile

        # SSO Session은 지원하지 않음
        if profile_name in config.sessions:
            console.print(f"[red]{t('flow.sso_session_not_supported', profile=profile_name)}[/red]")
            console.print(f"[dim]{t('flow.use_sso_or_access_key')}[/dim]")
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
        console.print(f"  {t('flow.profile_label')} {self._ctx.profile_name}")

        if len(self._ctx.regions) == 1:
            console.print(f"  {t('flow.region_label')} {self._ctx.regions[0]}")
        else:
            console.print(f"  {t('flow.region_label')} {t('flow.regions_count', count=len(self._ctx.regions))}")


def run_headless(
    tool_path: str,
    profile: str,
    regions: list[str],
    format: str = "console",
    output: str | None = None,
    quiet: bool = False,
) -> int:
    """Headless 실행 편의 함수

    SSO Profile 또는 Access Key 프로파일만 지원합니다.

    Args:
        tool_path: 도구 경로 (category/module 형식)
        profile: SSO Profile 또는 Access Key 프로파일
        regions: 리전 목록
        format: 출력 형식
        output: 출력 파일 경로
        quiet: 최소 출력 모드

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
        regions=regions if regions else ["ap-northeast-2"],
        format=format,
        output=output,
        quiet=quiet,
    )

    runner = HeadlessRunner(config)
    return runner.run()
