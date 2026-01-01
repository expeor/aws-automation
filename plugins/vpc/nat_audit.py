"""
plugins/vpc/nat_audit.py - NAT Gateway 미사용 분석 도구

NAT Gateway 비용 최적화:
- 미사용 NAT Gateway 탐지 (14일간 트래픽 0)
- 저사용 NAT Gateway 탐지 (일평균 < 1GB)
- 비용 절감 기회 식별

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from typing import Any, Dict, List

from botocore.exceptions import ClientError
from rich.console import Console

from core.auth import SessionIterator
from core.tools.output import OutputPath, open_in_explorer

from .nat_audit_analysis import (
    NATCollector,
    NATAnalyzer,
    NATExcelReporter,
)

console = Console()


def run(ctx) -> None:
    """NAT Gateway 미사용 분석 실행"""
    console.print("[bold]NAT Gateway 미사용 분석 시작...[/bold]")

    # 1. 데이터 수집
    console.print("[cyan]Step 1: NAT Gateway 데이터 수집 중...[/cyan]")

    collector = NATCollector()
    all_results = []
    all_stats = []

    # 계정/리전별 수집 추적
    collected_pairs = set()

    with SessionIterator(ctx) as sessions:
        for session, identifier, region in sessions:
            try:
                # STS로 Account ID 조회
                sts = session.client("sts")
                account_id = sts.get_caller_identity()["Account"]

                # 계정+리전 조합 중복 방지
                pair_key = f"{account_id}:{region}"
                if pair_key in collected_pairs:
                    continue
                collected_pairs.add(pair_key)

                # Account Name 결정
                account_name = identifier
                if hasattr(ctx, "accounts") and ctx.accounts:
                    for acc in ctx.accounts:
                        if acc.id == account_id:
                            account_name = acc.name
                            break

                console.print(f"  [dim]{account_name} / {region}[/dim]")

                # 데이터 수집
                audit_data = collector.collect(session, account_id, account_name, region)

                if not audit_data.nat_gateways:
                    console.print(f"    [dim](NAT Gateway 없음)[/dim]")
                    continue

                # 분석
                analyzer = NATAnalyzer(audit_data)
                analysis_result = analyzer.analyze()
                stats = analyzer.get_summary_stats()

                all_results.append(analysis_result)
                all_stats.append(stats)

                # 간단 요약 출력
                if stats["unused_count"] > 0:
                    console.print(
                        f"    [red]미사용: {stats['unused_count']}개[/red] "
                        f"(월 ${stats['total_monthly_waste']:,.0f} 낭비)"
                    )
                elif stats["low_usage_count"] > 0:
                    console.print(
                        f"    [yellow]저사용: {stats['low_usage_count']}개[/yellow]"
                    )
                else:
                    console.print(
                        f"    [green]{stats['total_nat_count']}개 정상[/green]"
                    )

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                console.print(f"    [yellow]오류: {error_code}[/yellow]")
                continue
            except Exception as e:
                console.print(f"    [red]오류: {e}[/red]")
                continue

    # 오류 출력
    if collector.errors:
        console.print(f"[dim]  (오류 {len(collector.errors)}건)[/dim]")

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

    console.print("[bold green]보고서 생성 완료![/bold green]")
    console.print(f"  경로: {filepath}")

    # 오류 출력
    if collector.errors:
        console.print(f"\n[yellow]수집 중 오류 {len(collector.errors)}건:[/yellow]")
        for err in collector.errors[:5]:
            console.print(f"  - {err}")
        if len(collector.errors) > 5:
            console.print(f"  ... 외 {len(collector.errors) - 5}건")

    # 폴더 열기
    open_in_explorer(output_path)


def _print_summary(stats_list: List[Dict[str, Any]]) -> None:
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
        console.print(
            f"    [red bold]미사용 (삭제 권장): {totals['unused_count']}개[/red bold]"
        )
    if totals["low_usage_count"] > 0:
        console.print(
            f"    [yellow]저사용 (검토 필요): {totals['low_usage_count']}개[/yellow]"
        )
    if totals["normal_count"] > 0:
        console.print(
            f"    [green]정상 사용: {totals['normal_count']}개[/green]"
        )

    console.print(f"\n  [bold]비용:[/bold]")
    console.print(f"    월간 총 비용: ${totals['total_monthly_cost']:,.2f}")

    if totals["total_monthly_waste"] > 0:
        console.print(
            f"    [red]월간 낭비 추정: ${totals['total_monthly_waste']:,.2f}[/red]"
        )
        console.print(
            f"    [red]연간 절감 가능: ${totals['total_annual_savings']:,.2f}[/red]"
        )


def _create_output_directory(ctx) -> str:
    """출력 디렉토리 생성"""
    # identifier 결정
    if hasattr(ctx, "is_sso_session") and ctx.is_sso_session() and ctx.accounts:
        identifier = ctx.accounts[0].id
    elif ctx.profile_name:
        identifier = ctx.profile_name
    else:
        identifier = "default"

    output_path = OutputPath(identifier).sub("nat-audit").with_date().build()
    return output_path
