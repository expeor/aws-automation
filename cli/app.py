"""
cli/app.py - 메인 CLI 엔트리포인트

Click 기반의 CLI 애플리케이션 진입점입니다.
플러그인 discovery 시스템을 통해 카테고리를 자동 등록합니다.

주요 기능:
    - 대화형 메인 메뉴 (서브명령 없이 실행 시)
    - 카테고리별 명령어 자동 등록 (discovery 기반)
    - 카테고리 별칭(aliases) 지원
    - 버전 정보 표시

명령어 구조:
    aa                      # 대화형 메인 메뉴
    aa --version            # 버전 표시
    aa <category>           # 카테고리별 도구 실행
    aa <category> --help    # 카테고리 도움말

    예시:
    aa ec2                  # EC2 관련 도구 실행
    aa ebs                  # EBS 관련 도구 실행
    aa s3                   # S3 관련 도구 실행

아키텍처:
    1. get_version(): core.config에서 버전 정보 로드
    2. cli(): Click 그룹 - 메인 엔트리포인트
    3. _register_category_commands(): discovery 기반 카테고리 자동 등록
       - discover_categories()로 플러그인 검색
       - 각 카테고리를 Click 명령어로 등록
       - 별칭(aliases)도 hidden 명령어로 등록

Usage:
    # 명령줄에서 직접 실행
    $ aa
    $ aa ec2
    $ aa --version

    # 모듈로 실행
    $ python -m cli.app
"""

import logging
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (plugins 모듈 임포트를 위함)
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import click  # noqa: E402
from click import Command, Context, HelpFormatter  # noqa: E402

from cli.i18n import t  # noqa: E402

# Keep lightweight, centralized logging config
# WARNING 레벨로 설정하여 INFO 로그가 도구 출력에 섞이지 않도록 함
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_version() -> str:
    """버전 문자열 반환

    version.txt 파일에서 버전을 읽어옴
    core.config.get_version()으로 대체됨
    """
    from core.config import get_version as config_get_version

    return config_get_version()


VERSION = get_version()

# 유틸리티 명령어 목록 (서비스 명령어와 분리 표시용)
UTILITY_COMMANDS = {"run", "list-tools", "group"}


class GroupedCommandsGroup(click.Group):
    """명령어를 서비스/유틸리티로 분리해서 표시하는 커스텀 Click 그룹"""

    def format_commands(self, ctx: Context, formatter: HelpFormatter) -> None:
        """명령어를 그룹화해서 표시"""
        commands: list[tuple[str, Command]] = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None or cmd.hidden:
                continue
            commands.append((subcommand, cmd))

        if not commands:
            return

        # 명령어 분류
        utility_cmds: list[tuple[str, str]] = []
        service_cmds: list[tuple[str, str]] = []

        for name, cmd in commands:
            help_text: str = cmd.get_short_help_str(limit=formatter.width)
            if name in UTILITY_COMMANDS:
                utility_cmds.append((name, help_text))
            else:
                service_cmds.append((name, help_text))

        # 유틸리티 명령어
        if utility_cmds:
            with formatter.section(t("cli.section_utilities")):
                formatter.write_dl(utility_cmds)

        # 서비스 명령어
        if service_cmds:
            with formatter.section(t("cli.section_aws_services")):
                formatter.write_dl(service_cmds)


def _build_help_text(lang: str = "ko") -> str:
    """help 텍스트 생성"""
    if lang == "en":
        lines = [
            "AA - AWS Automation CLI",
            "",
            t("cli.help_intro"),
            "",
            "\b",  # Click keeps line breaks
            t("cli.help_basic_usage"),
            f"  aa              {t('cli.help_interactive_menu')}",
            f"  aa <service>    {t('cli.help_service_run')}",
            "",
            "\b",
            t("cli.help_headless_mode"),
            f"  aa run <tool_path> [options]    {t('cli.help_run_tool')}",
            f"  aa list-tools                   {t('cli.help_list_tools')}",
            "",
            f"  {t('cli.help_examples')}",
            "    aa run ec2/ebs_audit -p my-profile -r ap-northeast-2",
            "    aa run ec2/ebs_audit -g 'Dev Team' -r all -f json",
            "",
            "\b",
            t("cli.help_profile_groups"),
            "  aa group list / create / show / delete",
            "",
            "\b",
            t("cli.help_cli_examples"),
            f"  aa ec2          {t('cli.help_ec2_tools')}",
            f"  aa iam          {t('cli.help_iam_audit')}",
            f"  aa cost         {t('cli.help_cost_analysis')}",
        ]
    else:
        lines = [
            "AA - AWS Automation CLI",
            "",
            "AWS 리소스 분석, 비용 최적화, 보안 점검 등",
            "AWS 운영 업무를 자동화하는 CLI 도구입니다.",
            "",
            "\b",  # Click 줄바꿈 유지 마커
            "[기본 사용법]",
            "  aa              대화형 메뉴 (검색/탐색/즐겨찾기)",
            "  aa <서비스>     특정 서비스 도구 실행",
            "",
            "\b",
            "[Headless 모드 (CI/CD용)]",
            "  aa run <도구경로> [옵션]    도구 실행",
            "  aa list-tools               도구 목록 조회",
            "",
            "  예시:",
            "    aa run ec2/ebs_audit -p my-profile -r ap-northeast-2",
            "    aa run ec2/ebs_audit -g 'Dev Team' -r all -f json",
            "",
            "\b",
            "[프로파일 그룹]",
            "  aa group list / create / show / delete",
            "",
            "\b",
            "[예시]",
            "  aa ec2          EC2 도구 실행",
            "  aa iam          IAM 보안 감사",
            "  aa cost         비용 최적화 분석",
        ]

    return "\n".join(lines)


@click.group(cls=GroupedCommandsGroup, invoke_without_command=True)
@click.version_option(VERSION, prog_name="aa")
@click.option(
    "--lang",
    type=click.Choice(["ko", "en"]),
    default="ko",
    help="UI 언어 설정 / UI language (ko: 한국어, en: English)",
)
@click.pass_context
def cli(ctx: Context, lang: str) -> None:
    """AA - AWS Automation CLI"""
    # Set language for i18n
    from cli.i18n import set_lang

    set_lang(lang)

    # Store lang in click context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["lang"] = lang

    if ctx.invoked_subcommand is None:
        # 서브 명령어 없이 실행된 경우 새로운 메인 메뉴 표시
        from cli.ui.main_menu import show_main_menu

        show_main_menu(lang=lang)


# help 텍스트 동적 설정
cli.help = _build_help_text()


# =============================================================================
# Headless CLI 명령어
# =============================================================================


@cli.command("run")
@click.argument("tool_path")
@click.option(
    "-p",
    "--profile",
    "profiles",
    multiple=True,
    help="SSO Profile 또는 Access Key 프로파일 (다중 가능, 쉼표 구분 지원)",
)
@click.option(
    "-g",
    "--profile-group",
    "profile_group",
    required=False,
    help="저장된 프로파일 그룹 이름 (aa group list로 확인)",
)
@click.option(
    "-s",
    "--sso-session",
    "sso_session",
    required=False,
    help="SSO Session 이름 (멀티 계정 지원)",
)
@click.option(
    "--account",
    "accounts",
    multiple=True,
    help="계정 ID (다중 가능, 'all'=전체) - SSO Session 전용",
)
@click.option(
    "--role",
    "role",
    required=False,
    help="사용할 Role 이름 - SSO Session 전용",
)
@click.option(
    "--fallback-role",
    "fallback_role",
    required=False,
    help="Fallback Role 이름 (Primary Role 없는 계정용) - SSO Session 전용",
)
@click.option(
    "-r",
    "--region",
    multiple=True,
    default=["ap-northeast-2"],
    help="리전 (다중 가능, 'all'=전체, 패턴 가능: 'ap-*')",
)
@click.option(
    "-f",
    "--format",
    type=click.Choice(["excel", "html", "both", "console", "json", "csv"]),
    default="both",
    help="출력 형식 (기본: both = Excel + HTML)",
)
@click.option(
    "-o",
    "--output",
    default=None,
    help="출력 파일 경로 (기본: 자동 생성)",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="최소 출력 모드",
)
def run_command(
    tool_path: str,
    profiles: tuple[str, ...],
    profile_group: str | None,
    sso_session: str | None,
    accounts: tuple[str, ...],
    role: str | None,
    fallback_role: str | None,
    region: tuple[str, ...],
    format: str,
    output: str | None,
    quiet: bool,
) -> None:
    """비대화형 도구 실행 (CI/CD용)

    SSO Session, SSO Profile, Access Key 프로파일을 지원합니다.

    \b
    TOOL_PATH: category/module 형식 (aa list-tools로 확인)
        예: ec2/ebs_audit, iam/unused_users, s3/public_buckets

    \b
    Examples:
        # SSO Profile / Access Key 실행
        aa run ec2/ebs_audit -p my-profile -r ap-northeast-2

        # 다중 프로파일 실행 (순차)
        aa run ec2/ebs_audit -p dev-profile -p staging-profile -p prod-profile

        # 다중 프로파일 (쉼표 구분)
        aa run ec2/ebs_audit -p dev,staging,prod -r all

        # 프로파일 그룹으로 실행
        aa run ec2/ebs_audit -g "개발 환경" -r ap-northeast-2

        # SSO Session으로 멀티 계정 실행
        aa run ec2/ebs_audit -s my-sso --account 111122223333 --account 444455556666 --role AdminRole

        # SSO Session 전체 계정 실행
        aa run ec2/ebs_audit -s my-sso --account all --role AdminRole -r all

        # SSO Session + Fallback Role
        aa run ec2/ebs_audit -s my-sso --account all --role AdminRole --fallback-role ReadOnlyRole

        # 다중 리전
        aa run ec2/ebs_audit -p my-profile -r ap-northeast-2 -r us-east-1

        # JSON 출력
        aa run ec2/ebs_audit -p my-profile -f json -o result.json
    """
    from cli.headless import run_headless

    # 인증 옵션 검증: profiles, profile_group, sso_session 중 하나만 사용
    auth_options = [bool(profiles), bool(profile_group), bool(sso_session)]
    if sum(auth_options) == 0:
        click.echo(t("cli.run_auth_required"), err=True)
        raise SystemExit(1)

    if sum(auth_options) > 1:
        click.echo(t("cli.run_auth_conflict"), err=True)
        raise SystemExit(1)

    # SSO Session 옵션 검증
    if sso_session:
        if not role:
            click.echo(t("cli.run_sso_role_required"), err=True)
            raise SystemExit(1)
        if not accounts:
            click.echo(t("cli.run_sso_account_required"), err=True)
            raise SystemExit(1)

    # SSO Session 실행
    if sso_session:
        exit_code = run_headless(
            tool_path=tool_path,
            sso_session=sso_session,
            accounts=list(accounts),
            role=role,
            fallback_role=fallback_role,
            regions=list(region),
            format=format,
            output=output,
            quiet=quiet,
        )
        raise SystemExit(exit_code)

    # 프로파일 목록 구성
    profiles_to_run: list[str] = []

    if profile_group:
        # 프로파일 그룹에서 가져오기
        from core.tools.history import ProfileGroupsManager

        manager = ProfileGroupsManager()
        group = manager.get_by_name(profile_group)
        if not group:
            click.echo(t("cli.run_group_not_found", name=profile_group), err=True)
            click.echo(t("cli.run_group_list_hint"), err=True)
            raise SystemExit(1)
        profiles_to_run = group.profiles
    else:
        # -p 옵션에서 프로파일 파싱 (쉼표 구분 지원)
        for p in profiles:
            if "," in p:
                # 쉼표로 구분된 프로파일 분리
                profiles_to_run.extend([x.strip() for x in p.split(",") if x.strip()])
            else:
                profiles_to_run.append(p)

    if not profiles_to_run:
        click.echo(t("cli.run_auth_required"), err=True)
        raise SystemExit(1)

    # 다중 프로파일 안내
    if len(profiles_to_run) > 1 and not quiet:
        click.echo(t("cli.run_multi_profile", count=len(profiles_to_run)))

    # 여러 프로파일 순차 실행
    total_exit_code = 0
    for p in profiles_to_run:
        exit_code = run_headless(
            tool_path=tool_path,
            profile=p,
            regions=list(region),
            format=format,
            output=output,
            quiet=quiet,
        )
        if exit_code != 0:
            total_exit_code = exit_code

    raise SystemExit(total_exit_code)


@cli.command("list-tools")
@click.option(
    "-c",
    "--category",
    default=None,
    help="특정 카테고리만 표시",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="JSON 형식으로 출력",
)
def list_tools_command(category: str | None, as_json: bool) -> None:
    """사용 가능한 도구 목록

    \b
    Examples:
        aa list-tools              # 전체 도구 목록
        aa list-tools -c ec2       # EC2 카테고리만
        aa list-tools --json       # JSON 출력
    """
    import json as json_module
    from typing import Any

    from rich.table import Table

    from core.tools.discovery import discover_categories

    categories: list[dict[str, Any]] = discover_categories(include_aws_services=True)

    if category:
        categories = [c for c in categories if c["name"] == category]
        if not categories:
            click.echo(t("cli.category_not_found", name=category), err=True)
            raise SystemExit(1)

    if as_json:
        output_data: list[dict[str, str]] = []
        for cat in categories:
            tools_list: list[dict[str, Any]] = cat.get("tools", [])
            for tool in tools_list:
                output_data.append(
                    {
                        "category": str(cat.get("name", "")),
                        "module": str(tool.get("module", "")),
                        "name": str(tool.get("name", "")),
                        "description": str(tool.get("description", "")),
                        "permission": str(tool.get("permission", "read")),
                    }
                )
        click.echo(json_module.dumps(output_data, ensure_ascii=False, indent=2))
    else:
        from rich.console import Console

        console = Console()

        table = Table(title=t("cli.available_tools"), show_header=True)
        table.add_column(t("cli.col_path"), style="cyan")
        table.add_column(t("cli.col_name"), style="white")
        table.add_column(t("cli.col_permission"), style="yellow")

        for cat in categories:
            tools_list: list[dict[str, Any]] = cat.get("tools", [])
            for tool in tools_list:
                path: str = f"{cat.get('name', '')}/{tool.get('module', '')}"
                tool_name: str = str(tool.get("name", ""))
                perm: str = str(tool.get("permission", "read"))
                perm_str: str = {"read": "R", "write": "W", "delete": "D"}.get(perm, perm)
                table.add_row(path, tool_name, perm_str)

        console.print(table)
        console.print()
        console.print(f"[dim]{t('cli.usage_hint')}[/dim]")


# =============================================================================
# 프로파일 그룹 관리 명령어
# =============================================================================


@cli.group("group")
def group_cmd():
    """프로파일 그룹 관리

    \b
    자주 사용하는 프로파일 조합을 그룹으로 저장하고 관리합니다.

    \b
    Examples:
        aa group list              # 그룹 목록
        aa group show "개발 환경"   # 그룹 상세 보기
        aa group create            # 그룹 생성 (인터랙티브)
        aa group delete "개발 환경" # 그룹 삭제
    """
    pass


@group_cmd.command("list")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="JSON 형식으로 출력",
)
def group_list(as_json: bool) -> None:
    """저장된 프로파일 그룹 목록"""
    import json as json_module

    from rich.console import Console
    from rich.table import Table

    from core.tools.history import ProfileGroupsManager

    console = Console()
    manager = ProfileGroupsManager()
    groups = manager.get_all()

    if not groups:
        if as_json:
            click.echo("[]")
        else:
            console.print(f"[dim]{t('cli.no_groups_saved')}[/dim]")
            console.print(f"[dim]{t('cli.group_create_hint')}[/dim]")
        return

    if as_json:
        output_list: list[dict[str, str | list[str]]] = []
        for g in groups:
            output_list.append(
                {
                    "name": g.name,
                    "kind": g.kind,
                    "profiles": g.profiles,
                    "added_at": g.added_at,
                }
            )
        click.echo(json_module.dumps(output_list, ensure_ascii=False, indent=2))
    else:
        kind_labels = {"sso_profile": "SSO", "static": "Key"}

        table = Table(title=t("cli.profile_groups_title"), show_header=True)
        table.add_column("#", style="dim", width=3)
        table.add_column(t("cli.col_name"), style="cyan")
        table.add_column(t("cli.col_type"), style="yellow", width=5)
        table.add_column(t("cli.col_profiles"), style="white")

        for i, g in enumerate(groups, 1):
            kind_label = kind_labels.get(g.kind, g.kind)
            profiles_str = ", ".join(g.profiles[:3])
            if len(g.profiles) > 3:
                profiles_str += f" {t('cli.and_n_more', count=len(g.profiles) - 3)}"
            table.add_row(str(i), g.name, kind_label, profiles_str)

        console.print(table)


@group_cmd.command("show")
@click.argument("name")
def group_show(name: str) -> None:
    """그룹 상세 보기"""
    from rich.console import Console
    from rich.panel import Panel

    from core.tools.history import ProfileGroupsManager

    console = Console()
    manager = ProfileGroupsManager()
    group = manager.get_by_name(name)

    if not group:
        console.print(f"[red]{t('cli.group_not_found', name=name)}[/red]")
        raise SystemExit(1)

    kind_labels = {"sso_profile": t("cli.sso_profile"), "static": t("cli.iam_access_key")}
    kind_label = kind_labels.get(group.kind, group.kind)

    lines = [
        f"[cyan]{t('cli.label_name')}[/cyan] {group.name}",
        f"[cyan]{t('cli.label_type')}[/cyan] {kind_label}",
        f"[cyan]{t('cli.label_created')}[/cyan] {group.added_at[:10]}",
        "",
        f"[cyan]{t('cli.label_profiles')}[/cyan]",
    ]
    for p in group.profiles:
        lines.append(f"  - {p}")

    console.print(Panel("\n".join(lines), title=t("cli.group_title", name=group.name)))


@group_cmd.command("create")
def group_create():
    """그룹 생성 (인터랙티브)"""
    from rich.console import Console

    from core.tools.history import ProfileGroupsManager

    console = Console()

    # 1. 인증 타입 선택
    console.print(f"\n[bold]{t('cli.create_group_title')}[/bold]\n")
    console.print(t("cli.select_auth_type"))
    console.print(f"  [cyan]1)[/cyan] {t('cli.sso_profile')}")
    console.print(f"  [cyan]2)[/cyan] {t('cli.iam_access_key')}")
    console.print()

    choice = click.prompt(t("cli.select_prompt"), type=click.IntRange(1, 2))
    kind = "sso_profile" if choice == 1 else "static"

    # 2. 해당 타입의 프로파일 목록 가져오기
    available: list[str] = _get_profiles_by_kind(kind)
    type_label: str = t("cli.sso_profile") if kind == "sso_profile" else t("cli.iam_access_key")

    if not available:
        console.print(f"\n[red]{t('cli.no_profiles_available', type=type_label)}[/red]")
        raise SystemExit(1)

    # 3. 프로파일 선택 (멀티, 2개 이상)
    console.print(f"\n[bold]{t('cli.select_profiles_title', type=type_label)}[/bold] {t('cli.select_2_or_more')}\n")
    for i, profile in enumerate(available, 1):
        console.print(f"  [cyan]{i:2})[/cyan] {profile}")
    console.print()
    console.print(f"[dim]{t('cli.selection_hint')}[/dim]")

    selection: str = click.prompt(t("cli.select_prompt"))
    selected: list[int] = _parse_selection(selection, len(available))

    if len(selected) < 2:
        console.print(f"[red]{t('cli.min_2_profiles')}[/red]")
        raise SystemExit(1)

    selected_profiles: list[str] = [available[idx] for idx in selected]

    # 4. 그룹 이름 입력
    console.print(f"\n{t('cli.selected_profiles')} {', '.join(selected_profiles)}\n")
    name = click.prompt(t("cli.group_name_prompt"))

    # 5. 저장
    manager = ProfileGroupsManager()
    if manager.add(name, kind, selected_profiles):
        console.print(f"\n[green]* {t('cli.group_saved', name=name, count=len(selected_profiles))}[/green]")
    else:
        console.print(f"\n[red]{t('cli.group_save_failed')}[/red]")
        raise SystemExit(1)


def _parse_selection(selection: str, max_count: int) -> list[int]:
    """선택 문자열 파싱 (1 2 3, 1,2,3, 1-3 지원)"""
    result: set[int] = set()
    selection = selection.strip()

    # 공백 또는 콤마로 분리
    parts = selection.replace(",", " ").split()

    for part in parts:
        if "-" in part and not part.startswith("-"):
            # 범위 (1-3)
            try:
                start_str, end_str = part.split("-", 1)
                start_int, end_int = int(start_str), int(end_str)
                for i in range(start_int, end_int + 1):
                    if 1 <= i <= max_count:
                        result.add(i - 1)  # 0-indexed
            except ValueError:
                continue
        else:
            # 단일 숫자
            try:
                num = int(part)
                if 1 <= num <= max_count:
                    result.add(num - 1)
            except ValueError:
                continue

    return sorted(result)


def _get_profiles_by_kind(kind: str) -> list[str]:
    """인증 타입별 프로파일 목록 조회

    Args:
        kind: "sso_profile" 또는 "static"

    Returns:
        프로파일 이름 목록
    """
    from core.auth import detect_provider_type, list_profiles, load_config
    from core.auth.types import ProviderType

    result: list[str] = []
    try:
        config_data = load_config()

        for profile_name in list_profiles():
            profile_config = config_data.profiles.get(profile_name)
            if not profile_config:
                continue

            provider_type = detect_provider_type(profile_config)

            if (kind == "sso_profile" and provider_type == ProviderType.SSO_PROFILE) or (
                kind == "static" and provider_type == ProviderType.STATIC_CREDENTIALS
            ):
                result.append(profile_name)
    except Exception:
        pass  # nosec B110 - Config parsing errors are non-critical

    return result


@group_cmd.command("delete")
@click.argument("name")
@click.option("-y", "--yes", is_flag=True, help="확인 없이 삭제")
def group_delete(name: str, yes: bool) -> None:
    """그룹 삭제"""
    from rich.console import Console

    from core.tools.history import ProfileGroupsManager

    console = Console()
    manager = ProfileGroupsManager()
    group = manager.get_by_name(name)

    if not group:
        console.print(f"[red]{t('cli.group_not_found', name=name)}[/red]")
        raise SystemExit(1)

    if not yes:
        console.print(t("cli.confirm_delete_group", name=name, count=len(group.profiles)))
        if not click.confirm(t("cli.delete_prompt")):
            console.print(f"[dim]{t('cli.cancelled')}[/dim]")
            return

    if manager.remove(name):
        console.print(f"[green]* {t('cli.group_deleted', name=name)}[/green]")
    else:
        console.print(f"[red]{t('cli.delete_failed')}[/red]")
        raise SystemExit(1)


def _register_category_commands():
    """discovery 기반 카테고리 명령어 자동 등록 (별칭, 하위 서비스 포함)

    AWS 서비스 카테고리(ec2, ebs 등)와 분석 카테고리(report 등) 모두 등록.
    하위 서비스(sub_services)도 별도 명령어로 등록됩니다.
    예: aa elb → 전체 ELB 도구, aa alb → ALB 도구만
    """
    try:
        from core.tools.discovery import discover_categories

        # AWS 서비스 카테고리 포함하여 모든 플러그인 로드
        categories = discover_categories(include_aws_services=True)
    except ImportError as e:
        logging.getLogger(__name__).warning(f"Discovery 모듈 로드 실패: {e}")
        return
    except (OSError, ValueError) as e:
        logging.getLogger(__name__).warning(f"카테고리 검색 실패: {e}")
        return

    from collections.abc import Callable
    from typing import Any

    # 등록된 명령어 추적 (중복 방지)
    registered_commands: set[str] = set()

    for cat in categories:
        name: str = cat.get("name", "")
        desc: str = cat.get("description", "")
        tools: list[dict[str, Any]] = cat.get("tools", [])
        aliases: list[str] = cat.get("aliases", [])
        sub_services: list[str] = cat.get("sub_services", [])

        # 도구 목록으로 help 텍스트 생성 (\b로 줄바꿈 유지)
        tool_lines: list[str] = [desc, "", "\b", t("cli.tool_list")]
        for tool in tools:
            perm: str = tool.get("permission", "read")
            perm_marker = " [!]" if perm in ("write", "delete") else ""
            tool_lines.append(f"  - {tool.get('name', '')}{perm_marker}")
        help_text = "\n".join(tool_lines)

        # 클로저로 카테고리명 캡처 (전체 도구)
        def make_cmd(category_name: str) -> Callable[[], None]:
            @click.pass_context
            def cmd(ctx: Context) -> None:
                from cli.flow import create_flow_runner

                runner = create_flow_runner()
                runner.run(category_name)

            return cmd

        # 클로저로 하위 서비스명 캡처 (필터링된 도구)
        def make_sub_service_cmd(sub_service_name: str) -> Callable[[], None]:
            @click.pass_context
            def cmd(ctx: Context) -> None:
                from cli.flow import create_flow_runner

                runner = create_flow_runner()
                # 하위 서비스명으로 실행 (FlowRunner에서 resolve_category 사용)
                runner.run(sub_service_name)

            return cmd

        # 메인 명령어 등록
        cmd_func = make_cmd(name)
        cmd_func.__doc__ = help_text
        cli.command(name=name)(cmd_func)
        registered_commands.add(name)

        # 하위 서비스(sub_services) 명령어 등록 (필터링 기능)
        for sub_svc in sub_services:
            if sub_svc in registered_commands:
                continue  # 이미 등록된 명령어는 스킵

            # 해당 sub_service에 속하는 도구만 필터링하여 help 텍스트 생성
            sub_tools = [tl for tl in tools if tl.get("sub_service") == sub_svc]
            sub_tool_lines = [f"{desc} ({sub_svc.upper()} only)", "", "\b", t("cli.tool_list")]
            for tool in sub_tools:
                perm = tool.get("permission", "read")
                perm_marker = " [!]" if perm in ("write", "delete") else ""
                sub_tool_lines.append(f"  - {tool.get('name', '')}{perm_marker}")
            sub_help_text = "\n".join(sub_tool_lines)

            sub_cmd = make_sub_service_cmd(sub_svc)
            sub_cmd.__doc__ = sub_help_text
            cli.command(name=sub_svc)(sub_cmd)
            registered_commands.add(sub_svc)

        # 별칭(aliases) 등록 (하위 서비스와 중복되지 않는 것만)
        for alias in aliases:
            if alias in registered_commands:
                continue  # sub_services에서 이미 등록된 경우 스킵

            alias_cmd = make_cmd(name)  # 원본 카테고리명으로 실행
            alias_cmd.__doc__ = f"{desc} (→ {name})"
            cli.command(name=alias, hidden=True)(alias_cmd)
            registered_commands.add(alias)


# 카테고리 명령어 자동 등록
_register_category_commands()


if __name__ == "__main__":
    cli()
