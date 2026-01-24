"""
plugins/vpc/nat_audit.py - NAT Gateway 미사용 분석 도구

NAT Gateway 비용 최적화:
- 미사용 NAT Gateway 탐지 (14일간 트래픽 0)
- 저사용 NAT Gateway 탐지 (일평균 < 1GB)
- 비용 절감 기회 식별

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from typing import Any

from rich.console import Console

from core.parallel import parallel_collect
from core.tools.output import OutputPath, open_in_explorer

from .nat_audit_analysis import NATAnalyzer, NATCollector, NATExcelReporter

console = Console()

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "ec2:DescribeNatGateways",
        "cloudwatch:GetMetricStatistics",
    ],
}


def _collect_and_analyze(session, account_id: str, account_name: str, region: str) -> tuple[Any, dict[str, Any]] | None:
    """단일 계정/리전의 NAT Gateway 수집 및 분석 (병렬 실행용)"""
    collector = NATCollector()
    audit_data = collector.collect(session, account_id, account_name, region)

    if not audit_data.nat_gateways:
        return None

    analyzer = NATAnalyzer(audit_data)
    analysis_result = analyzer.analyze()
    stats = analyzer.get_summary_stats()

    return (analysis_result, stats)


def run(ctx) -> None:
    """NAT Gateway 미사용 분석 실행"""
    console.print("[bold]NAT Gateway 미사용 분석 시작...[/bold]")

    # 병렬 수집 및 분석
    console.print("[cyan]Step 1: NAT Gateway 데이터 수집 중...[/cyan]")
    result = parallel_collect(ctx, _collect_and_analyze, max_workers=20, service="ec2")

    # None 필터링 및 결과 분리
    all_results = []
    all_stats = []
    for data in result.get_data():
        if data is not None:
            analysis_result, stats = data
            all_results.append(analysis_result)
            all_stats.append(stats)

    # 에러 출력
    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")
        console.print(f"[dim]{result.get_error_summary()}[/dim]")

    if not all_results:
        console.print("[yellow]분석할 NAT Gateway가 없습니다.[/yellow]")
        return

    # 2. 분석 결과 요약
    console.print("[cyan]Step 2: 분석 결과 요약[/cyan]")
    _print_summary(all_stats)

    # 3. Excel 보고서 생성
    console.print("[cyan]Step 3: Excel 보고서 생성 중...[/cyan]")

    output_path = _create_output_directory(ctx)
    reporter = NATExcelReporter(all_results, all_stats)
    filepath = reporter.generate(output_path)

    from core.tools.output import print_report_complete

    print_report_complete(filepath)

    # 폴더 열기
    open_in_explorer(output_path)


def _print_summary(stats_list: list[dict[str, Any]]) -> None:
    """분석 결과 요약 출력"""
    # 전체 통계
    totals = {
        "total_nat_count": sum(s.get("total_nat_count", 0) for s in stats_list),
        "unused_count": sum(s.get("unused_count", 0) for s in stats_list),
        "low_usage_count": sum(s.get("low_usage_count", 0) for s in stats_list),
        "normal_count": sum(s.get("normal_count", 0) for s in stats_list),
        "total_monthly_cost": sum(s.get("total_monthly_cost", 0) for s in stats_list),
        "total_monthly_waste": sum(s.get("total_monthly_waste", 0) for s in stats_list),
        "total_annual_savings": sum(s.get("total_annual_savings", 0) for s in stats_list),
    }

    console.print(f"\n  [bold]NAT Gateway:[/bold] 총 {totals['total_nat_count']}개")

    if totals["unused_count"] > 0:
        console.print(f"    [red bold]미사용 (삭제 권장): {totals['unused_count']}개[/red bold]")
    if totals["low_usage_count"] > 0:
        console.print(f"    [yellow]저사용 (검토 필요): {totals['low_usage_count']}개[/yellow]")
    if totals["normal_count"] > 0:
        console.print(f"    [green]정상 사용: {totals['normal_count']}개[/green]")

    console.print("\n  [bold]비용:[/bold]")
    console.print(f"    월간 총 비용: ${totals['total_monthly_cost']:,.2f}")

    if totals["total_monthly_waste"] > 0:
        console.print(f"    [red]월간 낭비 추정: ${totals['total_monthly_waste']:,.2f}[/red]")
        console.print(f"    [red]연간 절감 가능: ${totals['total_annual_savings']:,.2f}[/red]")


def _create_output_directory(ctx) -> str:
    """출력 디렉토리 생성"""
    # identifier 결정
    if hasattr(ctx, "is_sso_session") and ctx.is_sso_session() and ctx.accounts:
        identifier = ctx.accounts[0].id
    elif ctx.profile_name:
        identifier = ctx.profile_name
    else:
        identifier = "default"

    output_path = OutputPath(identifier).sub("vpc", "cost").with_date().build()
    return output_path
