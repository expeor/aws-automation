"""
analyzers/iam/unused_roles.py - 미사용 IAM Role 탐지 도구

365일 이상 미사용 Role 탐지:
- 사용 기록이 없거나 365일 이상 미사용
- 생성된 지 365일 이상
- Service-linked roles 제외
- AWS Config 기반 연결 리소스 분석
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from core.parallel import parallel_collect
from core.shared.io.output import OutputPath, get_context_identifier, open_in_explorer

from .iam_audit_analysis import IAMCollector
from .unused_roles_reporter import UnusedRolesReporter

if TYPE_CHECKING:
    from core.cli.flow.context import ExecutionContext

    from .iam_audit_analysis.collector import IAMData

console = Console()

# 임계값 설정
UNUSED_ROLE_THRESHOLD_DAYS = 365


def _collect_role_data(session, account_id: str, account_name: str, region: str) -> IAMData | None:
    """단일 계정의 IAM 데이터 수집 (병렬 실행용)"""
    collector = IAMCollector()
    return collector.collect(session, account_id, account_name)


def run(ctx: ExecutionContext) -> None:
    """미사용 IAM Role 탐지 실행"""
    console.print("[bold]미사용 IAM Role 탐지 중...[/bold]")

    # 1. 데이터 수집
    console.print("[cyan]Step 1: IAM 데이터 수집 중...[/cyan]")

    result = parallel_collect(ctx, _collect_role_data, max_workers=20, service="iam")

    # 결과 수집
    iam_data_list: list[IAMData] = []
    for data in result.get_data():
        if data is not None:
            iam_data_list.append(data)

    # 에러 출력
    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")
        console.print(f"[dim]{result.get_error_summary()}[/dim]")

    if not iam_data_list:
        console.print("[yellow]수집된 IAM 데이터가 없습니다.[/yellow]")
        return

    console.print(f"[green]{len(iam_data_list)}개 계정 데이터 수집 완료[/green]")

    # 2. 통계 요약 출력
    console.print("[cyan]Step 2: 분석 결과 요약[/cyan]")
    _print_summary(iam_data_list)

    # 3. 보고서 생성
    console.print("[cyan]Step 3: Excel 보고서 생성 중...[/cyan]")

    output_path = _create_output_directory(ctx)
    reporter = UnusedRolesReporter(iam_data_list, threshold_days=UNUSED_ROLE_THRESHOLD_DAYS)
    filepath = reporter.generate(output_path)

    from core.shared.io.output import print_report_complete

    print_report_complete(filepath)
    open_in_explorer(output_path)


def _print_summary(iam_data_list: list[IAMData]) -> None:
    """분석 결과 요약 출력"""
    total_roles = 0
    service_linked_roles = 0
    unused_roles = 0

    for iam_data in iam_data_list:
        for role in iam_data.roles:
            total_roles += 1

            if role.is_service_linked:
                service_linked_roles += 1
                continue

            # 미사용 Role 판정
            # 조건: (미사용 기록 OR 365일 이상 미사용) AND 생성된 지 365일 이상
            is_unused = (
                role.days_since_last_use == -1 or role.days_since_last_use >= UNUSED_ROLE_THRESHOLD_DAYS
            ) and role.age_days >= UNUSED_ROLE_THRESHOLD_DAYS

            if is_unused:
                unused_roles += 1

    console.print("  [bold]Role 현황[/bold]")
    console.print(f"    총 Role: {total_roles}개")
    console.print(f"    Service-linked Role: {service_linked_roles}개")
    if unused_roles > 0:
        console.print(f"    [yellow]미사용 Role ({UNUSED_ROLE_THRESHOLD_DAYS}일+): {unused_roles}개[/yellow]")
    else:
        console.print("    [green]미사용 Role 없음[/green]")


def _create_output_directory(ctx) -> str:
    """출력 디렉토리 생성"""
    identifier = get_context_identifier(ctx)

    output_path = OutputPath(identifier).sub("iam", "unused_roles").with_date().build()
    return output_path
