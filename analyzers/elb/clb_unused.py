"""
plugins/elb/clb_unused.py - CLB 미사용 분석

타겟이 없거나 비정상인 Classic Load Balancer 탐지

분석 기준:
- 등록된 인스턴스 없음
- 모든 인스턴스 unhealthy

월간 비용:
- CLB: ~$18.25/월 (고정) + 데이터 처리

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from core.parallel import parallel_collect
from shared.io.output import OutputPath, get_context_identifier, open_in_explorer

from .common import (
    LBAnalysisResult,
    analyze_load_balancers,
    collect_classic_load_balancers,
    generate_unused_report,
)

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

console = Console()

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeInstanceHealth",
        "elasticloadbalancing:DescribeTags",
    ],
}


def _collect_and_analyze(session, account_id: str, account_name: str, region: str) -> LBAnalysisResult | None:
    """단일 계정/리전의 CLB 수집 및 분석 (병렬 실행용)"""
    clbs = collect_classic_load_balancers(session, account_id, account_name, region)
    if not clbs:
        return None
    return analyze_load_balancers(clbs, account_id, account_name, region, lb_type_filter="classic")


def run(ctx: ExecutionContext) -> None:
    """CLB 미사용 분석 실행"""
    console.print("[bold]CLB 미사용 분석 시작...[/bold]")

    # 병렬 수집 및 분석
    result = parallel_collect(ctx, _collect_and_analyze, max_workers=20, service="elb")
    all_results: list[LBAnalysisResult] = [r for r in result.get_data() if r is not None]

    # 에러 출력
    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")

    if not all_results:
        console.print("[yellow]분석할 CLB 없음[/yellow]")
        return

    # 요약
    totals = {
        "total": sum(r.total_count for r in all_results),
        "unused": sum(r.unused_count for r in all_results),
        "unhealthy": sum(r.unhealthy_count for r in all_results),
        "normal": sum(r.normal_count for r in all_results),
        "unused_cost": sum(r.unused_monthly_cost for r in all_results),
    }

    console.print(f"\n[bold]전체 CLB: {totals['total']}개[/bold]")
    if totals["unused"] > 0:
        console.print(f"  [red bold]미사용: {totals['unused']}개[/red bold]")
    if totals["unhealthy"] > 0:
        console.print(f"  [yellow]Unhealthy: {totals['unhealthy']}개[/yellow]")
    console.print(f"  [green]정상: {totals['normal']}개[/green]")

    if totals["unused_cost"] > 0:
        console.print(f"\n  [red]미사용 월 비용: ${totals['unused_cost']:.2f}[/red]")

    # 보고서
    identifier = get_context_identifier(ctx)

    output_path = OutputPath(identifier).sub("elb", "unused").with_date().build()
    filepath = generate_unused_report(all_results, output_path, lb_type_name="CLB")

    console.print(f"\n[bold green]완료![/bold green] {filepath}")
    open_in_explorer(output_path)
