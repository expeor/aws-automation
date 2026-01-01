"""
plugins/vpc/ip_search.py - IP 검색 도구

Public 모드: 클라우드 제공자(AWS, GCP, Azure, Oracle) 공인 IP 범위 검색
Private 모드: AWS ENI 기반 사설 IP 검색

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

import csv
from datetime import datetime
from enum import Enum
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from core.auth import SessionIterator
from core.tools.output.builder import OutputPath

console = Console()


# =============================================================================
# 타입 정의
# =============================================================================


class SearchMode(Enum):
    """검색 모드"""
    PRIVATE_BASIC = "private_basic"      # 사설 IP 기본 검색
    PRIVATE_DETAILED = "private_detailed"  # 사설 IP 상세 검색
    PUBLIC = "public"                     # 공인 IP 범위 검색


# =============================================================================
# UI 함수
# =============================================================================


ASCII_LOGO = r"""
 ██╗██████╗     ███████╗███████╗ █████╗ ██████╗  ██████╗██╗  ██╗
 ██║██╔══██╗    ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║  ██║
 ██║██████╔╝    ███████╗█████╗  ███████║██████╔╝██║     ███████║
 ██║██╔═══╝     ╚════██║██╔══╝  ██╔══██║██╔══██╗██║     ██╔══██║
 ██║██║         ███████║███████╗██║  ██║██║  ██║╚██████╗██║  ██║
 ╚═╝╚═╝         ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝
"""


def show_logo():
    """로고 표시"""
    console.print(Panel(ASCII_LOGO, style="cyan", border_style="blue"))


def select_mode() -> SearchMode:
    """검색 모드 선택"""
    console.print("\n[bold cyan]검색 모드를 선택하세요:[/bold cyan]")
    console.print("  (f) Private 기본  - AWS ENI 기반 사설 IP 검색")
    console.print("  (d) Private 상세  - 리소스 매핑 포함 (EC2, RDS, Lambda 등)")
    console.print("  (u) Public        - 클라우드 공인 IP 범위 검색 (AWS, GCP, Azure, Oracle)")

    choice = Prompt.ask("\n선택", choices=["f", "d", "u"], default="f")

    mode_map = {
        "f": SearchMode.PRIVATE_BASIC,
        "d": SearchMode.PRIVATE_DETAILED,
        "u": SearchMode.PUBLIC,
    }
    return mode_map[choice]


def get_ip_input(save_csv: bool, mode: SearchMode, cache=None) -> tuple[List[str], bool, str]:
    """
    IP 입력 받기

    Returns:
        (IP 목록, 계속 여부, 명령어) - 명령어: 'c' (CSV 토글), 'r' (캐시 새로고침)
    """
    console.print("\n[bold cyan]검색할 IP 주소를 입력하세요:[/bold cyan]")
    console.print("[dim]여러 개는 쉼표(,)로 구분, CIDR 형식도 지원 (예: 10.0.0.0/24)[/dim]")

    # 옵션 표시
    csv_status = "[green]ON[/green]" if save_csv else "[dim]OFF[/dim]"
    console.print(f"[dim]c: CSV 저장 토글 ({csv_status})[/dim]")

    if mode in (SearchMode.PRIVATE_BASIC, SearchMode.PRIVATE_DETAILED) and cache:
        console.print(f"[dim]r: 캐시 새로고침 (현재: {cache.count()}개 ENI)[/dim]")

    console.print("[dim]0: 돌아가기[/dim]")

    ip_input = Prompt.ask("\nIP 주소").strip()

    # 명령어 처리
    if ip_input.lower() == "c":
        return [], True, "c"
    if ip_input.lower() == "r":
        return [], True, "r"
    if ip_input == "0" or ip_input.lower() == "q" or not ip_input:
        return [], False, ""

    ip_list = [ip.strip() for ip in ip_input.split(",") if ip.strip()]
    return ip_list, True, ""


# =============================================================================
# CSV 저장
# =============================================================================

# 현재 세션 이름 (run()에서 설정)
_current_session_name = "default"


def _get_output_dir() -> str:
    """출력 디렉토리 경로: output/{session_name}/ip_search/{date}/"""
    return (
        OutputPath(_current_session_name)
        .sub("ip_search")
        .with_date("daily")
        .build()
    )


def save_public_results_csv(results) -> str:
    """공인 IP 검색 결과 CSV 저장"""
    if not results:
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"public_ip_{timestamp}.csv"
    filepath = os.path.join(_get_output_dir(), filename)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["IP 주소", "제공자", "서비스", "IP 범위", "리전", "추가정보"])

        for r in results:
            extra = ", ".join(f"{k}={v}" for k, v in r.extra.items()) if r.extra else ""
            writer.writerow([
                r.ip_address,
                r.provider,
                r.service,
                r.ip_prefix,
                r.region,
                extra,
            ])

    return filepath


def save_private_results_csv(results) -> str:
    """사설 IP 검색 결과 CSV 저장"""
    if not results:
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"private_ip_{timestamp}.csv"
    filepath = os.path.join(_get_output_dir(), filename)

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "IP 주소", "계정 ID", "계정명", "리전", "ENI ID", "VPC ID", "Subnet ID",
            "Private IP", "Public IP", "인터페이스 타입", "상태", "설명",
            "Security Groups", "이름", "관리형", "관리자", "리소스"
        ])

        for r in results:
            writer.writerow([
                r.ip_address,
                r.account_id,
                r.account_name,
                r.region,
                r.eni_id,
                r.vpc_id,
                r.subnet_id,
                r.private_ip,
                r.public_ip,
                r.interface_type,
                r.status,
                r.description,
                ", ".join(r.security_groups),
                r.name,
                "Yes" if r.is_managed else "No",
                r.managed_by,
                r.mapped_resource,
            ])

    return filepath


# =============================================================================
# 결과 출력
# =============================================================================


def display_public_results(results, save_csv: bool = False):
    """공인 IP 검색 결과 출력"""
    if not results:
        console.print("\n[yellow]검색 결과가 없습니다.[/yellow]")
        return

    table = Table(title="공인 IP 검색 결과", show_header=True, header_style="bold magenta")
    table.add_column("IP 주소", style="cyan")
    table.add_column("제공자", style="green")
    table.add_column("서비스", style="blue")
    table.add_column("IP 범위", style="yellow")
    table.add_column("리전", style="white")

    for r in results:
        table.add_row(
            r.ip_address,
            r.provider,
            r.service or "-",
            r.ip_prefix or "-",
            r.region or "-",
        )

    console.print(table)
    console.print(f"\n[dim]총 {len(results)}개 결과[/dim]")

    # CSV 저장
    if save_csv:
        filepath = save_public_results_csv(results)
        if filepath:
            console.print(f"[green]CSV 저장: {filepath}[/green]")


def display_private_results(results, detailed: bool = False, save_csv: bool = False):
    """사설 IP 검색 결과 출력"""
    if not results:
        console.print("\n[yellow]검색 결과가 없습니다.[/yellow]")
        return

    title = "사설 IP 검색 결과 (ENI)" + (" [상세]" if detailed else "")
    table = Table(title=title, show_header=True, header_style="bold magenta")

    # 기본 컬럼
    table.add_column("IP 주소", style="cyan")
    table.add_column("계정", style="green")
    table.add_column("리전", style="blue")
    table.add_column("ENI ID", style="yellow")
    table.add_column("VPC", style="white")
    table.add_column("Subnet", style="white")

    if detailed:
        table.add_column("리소스", style="magenta")
        table.add_column("Public IP", style="cyan")
        table.add_column("타입", style="white")

    table.add_column("상태", style="white")

    for r in results:
        if detailed:
            table.add_row(
                r.ip_address,
                r.account_name,
                r.region,
                r.eni_id,
                r.vpc_id,
                r.subnet_id,
                r.mapped_resource or "-",
                r.public_ip or "-",
                r.interface_type or "-",
                r.status,
            )
        else:
            table.add_row(
                r.ip_address,
                r.account_name,
                r.region,
                r.eni_id,
                r.vpc_id,
                r.subnet_id,
                r.status,
            )

    console.print(table)
    console.print(f"\n[dim]총 {len(results)}개 결과[/dim]")

    # CSV 저장
    if save_csv:
        filepath = save_private_results_csv(results)
        if filepath:
            console.print(f"[green]CSV 저장: {filepath}[/green]")


# =============================================================================
# 메인 실행 함수
# =============================================================================


def run_public_search(ip_list: List[str], save_csv: bool = False):
    """공인 IP 검색 실행"""
    from plugins.vpc.ip_search_public import search_public_ip

    console.print("\n[cyan]클라우드 공인 IP 범위를 검색 중...[/cyan]")

    with console.status("[bold green]IP 범위 데이터 로딩 중..."):
        results = search_public_ip(ip_list)

    display_public_results(results, save_csv=save_csv)
    return results


def _prepare_private_cache(ctx, session_name: str, force_refresh: bool = False):
    """Private 모드용 ENI 캐시 준비 (검색 전 수집)"""
    from plugins.vpc.ip_search_private import ENICache, fetch_enis_from_account

    cache = ENICache(session_name=session_name)

    # 캐시가 유효하고 강제 새로고침이 아니면 바로 반환
    if cache.is_valid() and not force_refresh:
        console.print(f"\n[green]✓ 캐시 사용 ({cache.count()}개 ENI)[/green]")
        return cache

    # 캐시 수집
    if force_refresh:
        console.print("\n[cyan]ENI 캐시를 새로고침 중...[/cyan]")
        cache.clear()
    else:
        console.print("\n[cyan]ENI 데이터를 수집 중...[/cyan]")

    total_count = 0
    with console.status("[bold green]모든 리전에서 ENI 수집 중..."):
        with SessionIterator(ctx) as sessions:
            for session, identifier, region in sessions:
                try:
                    sts = session.client("sts")
                    account_id = sts.get_caller_identity()["Account"]

                    interfaces = fetch_enis_from_account(
                        session=session,
                        account_id=account_id,
                        account_name=identifier,
                        regions=[region],
                    )
                    cache.update(interfaces)
                    total_count += len(interfaces)
                except Exception:
                    continue

    cache.save()
    console.print(f"[green]✓ {total_count}개 ENI 캐시 완료[/green]")

    return cache


def _run_private_search_with_cache(ip_list: List[str], cache, detailed: bool, save_csv: bool = False):
    """캐시를 사용한 사설 IP 검색"""
    from plugins.vpc.ip_search_private import search_private_ip

    mode_text = "[상세 모드]" if detailed else "[기본 모드]"
    console.print(f"\n[cyan]사설 IP를 검색 중... {mode_text}[/cyan]")

    results = search_private_ip(ip_list, cache, detailed=detailed)
    display_private_results(results, detailed=detailed, save_csv=save_csv)

    return results


def run(ctx):
    """
    IP 검색 도구 실행

    Args:
        ctx: 실행 컨텍스트 (ExecutionContext 객체)
    """
    global _current_session_name

    show_logo()

    # 모드 선택
    mode = select_mode()

    # 세션 이름 결정 (프로파일 이름 또는 기본값)
    session_name = getattr(ctx, "profile_name", None) or "default"
    _current_session_name = session_name  # CSV 출력 경로용

    # 옵션 상태
    save_csv = False  # CSV 저장 기본값: OFF

    # Private 모드: 캐시 먼저 수집
    cache = None
    detailed = (mode == SearchMode.PRIVATE_DETAILED)

    if mode in (SearchMode.PRIVATE_BASIC, SearchMode.PRIVATE_DETAILED):
        cache = _prepare_private_cache(ctx, session_name)
        if cache is None:
            return

    # 검색 루프
    while True:
        ip_list, should_continue, command = get_ip_input(save_csv, mode, cache)

        if not should_continue:
            console.print("\n[dim]검색을 종료합니다.[/dim]")
            break

        # 명령어 처리
        if command == "c":
            save_csv = not save_csv
            status = "[green]ON[/green]" if save_csv else "[dim]OFF[/dim]"
            console.print(f"\n[cyan]CSV 저장: {status}[/cyan]")
            continue

        if command == "r":
            if mode in (SearchMode.PRIVATE_BASIC, SearchMode.PRIVATE_DETAILED):
                cache = _prepare_private_cache(ctx, session_name, force_refresh=True)
            else:
                console.print("\n[yellow]Public 모드에서는 캐시 새로고침이 필요 없습니다.[/yellow]")
            continue

        if not ip_list:
            continue

        console.print(f"\n[dim]검색 대상: {', '.join(ip_list)}[/dim]")

        # 검색 실행
        if mode == SearchMode.PUBLIC:
            run_public_search(ip_list, save_csv=save_csv)
        else:
            _run_private_search_with_cache(ip_list, cache, detailed, save_csv=save_csv)

    console.print("\n[green]✓ 검색 완료[/green]")


# =============================================================================
# 직접 실행용 (테스트)
# =============================================================================


if __name__ == "__main__":
    # 간단한 테스트
    test_ips = ["13.124.199.1", "8.8.8.8", "1.1.1.1"]

    console.print("[bold]Public IP 검색 테스트[/bold]")
    run_public_search(test_ips)
