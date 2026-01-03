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

import click

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


def _build_help_text() -> str:
    """help 텍스트 생성"""
    lines = [
        "AA - AWS Automation CLI",
        "",
        "AWS 리소스 분석, 비용 최적화, 보안 점검, 보고서 생성 등",
        "AWS 운영 업무를 자동화하는 CLI 도구입니다.",
        "",
        "\b",  # Click 줄바꿈 유지 마커
        "[기본 사용법]",
        "  aa              대화형 메뉴 (검색/탐색/즐겨찾기)",
        "  aa <서비스>     특정 서비스 도구 실행",
        "",
        "\b",
        "[주요 서비스 명령어]",
        "  aa ec2          EC2 인스턴스 분석",
        "  aa ebs          EBS 볼륨 분석 (미사용, 암호화 등)",
        "  aa s3           S3 버킷 분석 (퍼블릭, 암호화 등)",
        "  aa rds          RDS 데이터베이스 분석",
        "  aa iam          IAM 사용자/역할/액세스키 분석",
        "  aa vpc          VPC 네트워크 분석",
        "  aa report       정기 보고서 생성",
        "",
        "\b",
        "[Headless CLI (CI/CD용)]",
        "  aa list-tools                      도구 목록 조회",
        "  aa run <도구경로> [옵션]           도구 실행",
        "",
        "  옵션:",
        "    -p, --profile       SSO Profile 또는 Access Key 프로파일",
        "    -g, --profile-group 프로파일 그룹 (aa group list로 확인)",
        "    -r, --region        리전 (다중 가능, 'all' 또는 패턴)",
        "    -f, --format        출력 형식 (console, json, csv)",
        "    -o, --output        출력 파일 경로",
        "    -q, --quiet         최소 출력 모드",
        "",
        "  예시:",
        "    aa run ec2/ebs_audit -p my-profile -r ap-northeast-2",
        "    aa run ec2/ebs_audit -p my-profile -r all -f json",
        "",
        "\b",
        "[프로파일 그룹]",
        "  aa group list         그룹 목록",
        "  aa group create       그룹 생성 (인터랙티브)",
        "  aa group show <이름>  그룹 상세",
        "  aa group delete <이름> 그룹 삭제",
        "",
        "\b",
        "[예시]",
        "  aa ec2 --help   EC2 카테고리 도움말 표시",
        "  aa              -> 대화형 메뉴 진입",
        "                  -> 키워드 검색 (예: '미사용', 'rds')",
        "                  -> 번호로 도구 선택 후 실행",
    ]

    return "\n".join(lines)


@click.group(invoke_without_command=True)
@click.version_option(VERSION, prog_name="aa")
@click.pass_context
def cli(ctx):
    """AA - AWS Automation CLI"""
    if ctx.invoked_subcommand is None:
        # 서브 명령어 없이 실행된 경우 새로운 메인 메뉴 표시
        from cli.ui.main_menu import show_main_menu

        show_main_menu()


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
    required=False,
    help="SSO Profile 또는 Access Key 프로파일",
)
@click.option(
    "-g",
    "--profile-group",
    "profile_group",
    required=False,
    help="저장된 프로파일 그룹 이름 (aa group list로 확인)",
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
    type=click.Choice(["console", "json", "csv"]),
    default="console",
    help="출력 형식 (기본: console)",
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
    tool_path, profile, profile_group, region, format, output, quiet
):
    """비대화형 도구 실행 (CI/CD용)

    SSO Profile 또는 Access Key 프로파일만 지원합니다.

    \b
    TOOL_PATH: category/module 형식 (aa list-tools로 확인)
        예: ec2/ebs_audit, iam/unused_users, s3/public_buckets

    \b
    Examples:
        # 기본 실행
        aa run ec2/ebs_audit -p my-profile -r ap-northeast-2

        # 프로파일 그룹으로 실행
        aa run ec2/ebs_audit -g "개발 환경" -r ap-northeast-2

        # 다중 리전
        aa run ec2/ebs_audit -p my-profile -r ap-northeast-2 -r us-east-1

        # 전체 리전
        aa run ec2/ebs_audit -p my-profile -r all

        # JSON 출력
        aa run ec2/ebs_audit -p my-profile -f json -o result.json
    """
    from cli.headless import run_headless

    # 프로파일 또는 그룹 둘 중 하나는 필수
    if not profile and not profile_group:
        click.echo("오류: -p/--profile 또는 -g/--profile-group 중 하나를 지정하세요.", err=True)
        raise SystemExit(1)

    if profile and profile_group:
        click.echo("오류: -p/--profile과 -g/--profile-group은 동시에 사용할 수 없습니다.", err=True)
        raise SystemExit(1)

    # 프로파일 그룹 처리
    profiles_to_run = []
    if profile_group:
        from core.tools.history import ProfileGroupsManager

        manager = ProfileGroupsManager()
        group = manager.get_by_name(profile_group)
        if not group:
            click.echo(f"오류: 그룹을 찾을 수 없습니다: {profile_group}", err=True)
            click.echo("사용 가능한 그룹: aa group list", err=True)
            raise SystemExit(1)
        profiles_to_run = group.profiles
    else:
        profiles_to_run = [profile]

    # 여러 프로파일 실행
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
def list_tools_command(category, as_json):
    """사용 가능한 도구 목록

    \b
    Examples:
        aa list-tools              # 전체 도구 목록
        aa list-tools -c ec2       # EC2 카테고리만
        aa list-tools --json       # JSON 출력
    """
    import json as json_module

    from rich.table import Table

    from core.tools.discovery import discover_categories

    categories = discover_categories(include_aws_services=True)

    if category:
        categories = [c for c in categories if c["name"] == category]
        if not categories:
            click.echo(f"카테고리를 찾을 수 없습니다: {category}", err=True)
            raise SystemExit(1)

    if as_json:
        output_data = []
        for cat in categories:
            for tool in cat.get("tools", []):
                if isinstance(tool, dict):
                    output_data.append(
                        {
                            "category": cat["name"],
                            "module": tool.get("module", ""),
                            "name": tool.get("name", ""),
                            "description": tool.get("description", ""),
                            "permission": tool.get("permission", "read"),
                        }
                    )
        click.echo(json_module.dumps(output_data, ensure_ascii=False, indent=2))
    else:
        from rich.console import Console

        console = Console()

        table = Table(title="사용 가능한 도구", show_header=True)
        table.add_column("경로", style="cyan")
        table.add_column("이름", style="white")
        table.add_column("권한", style="yellow")

        for cat in categories:
            for tool in cat.get("tools", []):
                if isinstance(tool, dict):
                    path = f"{cat['name']}/{tool.get('module', '')}"
                    name = tool.get("name", "")
                    perm = tool.get("permission", "read")
                    perm_str = {"read": "R", "write": "W", "delete": "D"}.get(
                        perm, perm
                    )
                    table.add_row(path, name, perm_str)

        console.print(table)
        console.print()
        console.print("[dim]사용법: aa run <경로> -p <프로파일> -r <리전>[/dim]")


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
def group_list(as_json):
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
            console.print("[dim]저장된 프로파일 그룹이 없습니다.[/dim]")
            console.print("[dim]aa group create 로 새 그룹을 만드세요.[/dim]")
        return

    if as_json:
        output = []
        for g in groups:
            output.append(
                {
                    "name": g.name,
                    "kind": g.kind,
                    "profiles": g.profiles,
                    "added_at": g.added_at,
                }
            )
        click.echo(json_module.dumps(output, ensure_ascii=False, indent=2))
    else:
        kind_labels = {"sso_profile": "SSO", "static": "Key"}

        table = Table(title="프로파일 그룹", show_header=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("이름", style="cyan")
        table.add_column("타입", style="yellow", width=5)
        table.add_column("프로파일", style="white")

        for i, g in enumerate(groups, 1):
            kind_label = kind_labels.get(g.kind, g.kind)
            profiles_str = ", ".join(g.profiles[:3])
            if len(g.profiles) > 3:
                profiles_str += f" 외 {len(g.profiles) - 3}개"
            table.add_row(str(i), g.name, kind_label, profiles_str)

        console.print(table)


@group_cmd.command("show")
@click.argument("name")
def group_show(name):
    """그룹 상세 보기"""
    from rich.console import Console
    from rich.panel import Panel

    from core.tools.history import ProfileGroupsManager

    console = Console()
    manager = ProfileGroupsManager()
    group = manager.get_by_name(name)

    if not group:
        console.print(f"[red]그룹을 찾을 수 없습니다: {name}[/red]")
        raise SystemExit(1)

    kind_labels = {"sso_profile": "SSO 프로파일", "static": "IAM Access Key"}
    kind_label = kind_labels.get(group.kind, group.kind)

    lines = [
        f"[cyan]이름:[/cyan] {group.name}",
        f"[cyan]타입:[/cyan] {kind_label}",
        f"[cyan]생성:[/cyan] {group.added_at[:10]}",
        "",
        "[cyan]프로파일:[/cyan]",
    ]
    for p in group.profiles:
        lines.append(f"  • {p}")

    console.print(Panel("\n".join(lines), title=f"그룹: {group.name}"))


@group_cmd.command("create")
def group_create():
    """그룹 생성 (인터랙티브)"""
    from rich.console import Console

    from core.tools.history import ProfileGroupsManager

    console = Console()

    # 1. 인증 타입 선택
    console.print("\n[bold]프로파일 그룹 생성[/bold]\n")
    console.print("그룹에 포함할 인증 타입을 선택하세요:")
    console.print("  [cyan]1)[/cyan] SSO 프로파일")
    console.print("  [cyan]2)[/cyan] IAM Access Key")
    console.print()

    choice = click.prompt("선택", type=click.IntRange(1, 2))
    kind = "sso_profile" if choice == 1 else "static"

    # 2. 해당 타입의 프로파일 목록 가져오기
    available = _get_profiles_by_kind(kind)
    type_label = "SSO 프로파일" if kind == "sso_profile" else "IAM Access Key"

    if not available:
        console.print(f"\n[red]사용 가능한 {type_label}이 없습니다.[/red]")
        raise SystemExit(1)

    # 3. 프로파일 선택 (멀티, 2개 이상)
    console.print(f"\n[bold]{type_label} 선택[/bold] (2개 이상 선택)\n")
    for i, p in enumerate(available, 1):
        console.print(f"  [cyan]{i:2})[/cyan] {p}")
    console.print()
    console.print("[dim]예: 1 2 3 또는 1,2,3 또는 1-3[/dim]")

    selection = click.prompt("선택")
    selected = _parse_selection(selection, len(available))

    if len(selected) < 2:
        console.print("[red]그룹은 2개 이상 프로파일이 필요합니다. (1개면 단일 선택 사용)[/red]")
        raise SystemExit(1)

    selected_profiles = [available[i] for i in selected]

    # 4. 그룹 이름 입력
    console.print(f"\n선택된 프로파일: {', '.join(selected_profiles)}\n")
    name = click.prompt("그룹 이름")

    # 5. 저장
    manager = ProfileGroupsManager()
    if manager.add(name, kind, selected_profiles):
        console.print(
            f"\n[green]✓ 그룹 '{name}' 저장됨 ({len(selected_profiles)}개 프로파일)[/green]"
        )
    else:
        console.print(f"\n[red]그룹 저장 실패 (이미 존재하거나 최대 개수 초과)[/red]")
        raise SystemExit(1)


def _parse_selection(selection: str, max_count: int) -> list:
    """선택 문자열 파싱 (1 2 3, 1,2,3, 1-3 지원)"""
    result = set()
    selection = selection.strip()

    # 공백 또는 콤마로 분리
    parts = selection.replace(",", " ").split()

    for part in parts:
        if "-" in part and not part.startswith("-"):
            # 범위 (1-3)
            try:
                start, end = part.split("-", 1)
                start, end = int(start), int(end)
                for i in range(start, end + 1):
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


def _get_profiles_by_kind(kind: str) -> list:
    """인증 타입별 프로파일 목록 조회

    Args:
        kind: "sso_profile" 또는 "static"

    Returns:
        프로파일 이름 목록
    """
    from core.auth import detect_provider_type, list_profiles, load_config
    from core.auth.types import ProviderType

    result = []
    try:
        config_data = load_config()

        for profile_name in list_profiles():
            profile_config = config_data.profiles.get(profile_name)
            if not profile_config:
                continue

            provider_type = detect_provider_type(profile_config)

            if kind == "sso_profile" and provider_type == ProviderType.SSO_PROFILE:
                result.append(profile_name)
            elif kind == "static" and provider_type == ProviderType.STATIC_CREDENTIALS:
                result.append(profile_name)
    except Exception:
        pass

    return result


@group_cmd.command("delete")
@click.argument("name")
@click.option("-y", "--yes", is_flag=True, help="확인 없이 삭제")
def group_delete(name, yes):
    """그룹 삭제"""
    from rich.console import Console

    from core.tools.history import ProfileGroupsManager

    console = Console()
    manager = ProfileGroupsManager()
    group = manager.get_by_name(name)

    if not group:
        console.print(f"[red]그룹을 찾을 수 없습니다: {name}[/red]")
        raise SystemExit(1)

    if not yes:
        console.print(f"그룹 '{name}' ({len(group.profiles)}개 프로파일)을 삭제하시겠습니까?")
        if not click.confirm("삭제"):
            console.print("[dim]취소됨[/dim]")
            return

    if manager.remove(name):
        console.print(f"[green]✓ 그룹 '{name}' 삭제됨[/green]")
    else:
        console.print("[red]삭제 실패[/red]")
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

    # 등록된 명령어 추적 (중복 방지)
    registered_commands = set()

    for cat in categories:
        name = cat.get("name", "")
        desc = cat.get("description", "")
        tools = cat.get("tools", [])
        aliases = cat.get("aliases", [])
        sub_services = cat.get("sub_services", [])

        # 도구 목록으로 help 텍스트 생성 (\b로 줄바꿈 유지)
        tool_lines = [desc, "", "\b", "도구 목록:"]
        for tool in tools:
            perm = tool.get("permission", "read")
            perm_marker = " [!]" if perm in ("write", "delete") else ""
            tool_lines.append(f"  - {tool.get('name', '')}{perm_marker}")
        help_text = "\n".join(tool_lines)

        # 클로저로 카테고리명 캡처 (전체 도구)
        def make_cmd(category_name):
            @click.pass_context
            def cmd(ctx):
                from cli.flow import create_flow_runner

                runner = create_flow_runner()
                runner.run(category_name)

            return cmd

        # 클로저로 하위 서비스명 캡처 (필터링된 도구)
        def make_sub_service_cmd(sub_service_name):
            @click.pass_context
            def cmd(ctx):
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
            sub_tools = [t for t in tools if t.get("sub_service") == sub_svc]
            sub_tool_lines = [f"{desc} ({sub_svc.upper()} only)", "", "\b", "도구 목록:"]
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
