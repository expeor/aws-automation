"""
plugins/vpc/sg_audit.py - Security Group Audit 도구

SG 현황 및 미사용 SG/규칙 분석

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
    - collect_options(ctx): 선택. 추가 옵션 수집.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from core.parallel import parallel_collect
from core.tools.output import OutputPath, open_in_explorer

from .sg_audit_analysis import SGAnalyzer, SGCollector, SGExcelReporter

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

console = Console()

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeInstances",
    ],
}


def _collect_sgs(session, account_id: str, account_name: str, region: str) -> list | None:
    """단일 계정/리전의 Security Group 수집 (병렬 실행용)"""
    collector = SGCollector()
    sgs = collector.collect(session, account_id, account_name, region)
    return sgs if sgs else None


def run(ctx: ExecutionContext) -> None:
    """Security Group Audit 실행"""
    console.print("[bold]Security Group Audit 시작...[/bold]")

    # 1. 데이터 수집
    console.print("[cyan]Step 1: Security Group 데이터 수집 중...[/cyan]")

    # 병렬 수집
    result = parallel_collect(ctx, _collect_sgs, max_workers=20, service="ec2")

    # 결과 평탄화 (각 리전의 SG 목록을 하나로 합침)
    all_sgs = []
    for sgs in result.get_data():
        if sgs:
            all_sgs.extend(sgs)

    # 에러 출력
    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")
        console.print(f"[dim]{result.get_error_summary()}[/dim]")

    if not all_sgs:
        console.print("[yellow]수집된 Security Group이 없습니다.[/yellow]")
        return

    console.print(f"[green]총 {len(all_sgs)}개 Security Group 수집 완료[/green]")

    # 2. 분석
    console.print("[cyan]Step 2: 미사용 SG 및 Stale Rule 분석 중...[/cyan]")

    analyzer = SGAnalyzer(all_sgs)
    sg_results, rule_results = analyzer.analyze()
    summary = analyzer.get_summary(sg_results)

    # 통계 출력
    unused_count = sum(1 for r in sg_results if r.status.value == "Unused")
    stale_count = sum(1 for r in rule_results if r.status.value != "Active")
    high_count = sum(1 for r in rule_results if r.risk_level == "HIGH")
    medium_count = sum(1 for r in rule_results if r.risk_level == "MEDIUM")
    low_count = sum(1 for r in rule_results if r.risk_level == "LOW")

    console.print(f"  - 미사용 SG: [yellow]{unused_count}[/yellow]개")
    console.print(f"  - Stale 규칙: [yellow]{stale_count}[/yellow]개")
    if high_count > 0:
        console.print(f"  - [red bold]HIGH 위험 규칙: {high_count}개[/red bold] (위험 포트 노출)")
    if medium_count > 0:
        console.print(f"  - [yellow]MEDIUM 위험 규칙: {medium_count}개[/yellow] (일반 포트 노출)")
    if low_count > 0:
        console.print(f"  - [dim]LOW 규칙: {low_count}개[/dim] (웹 포트 - 일반적 허용)")

    # 3. Excel 보고서 생성
    console.print("[cyan]Step 3: Excel 보고서 생성 중...[/cyan]")

    output_path = _create_output_directory(ctx)
    reporter = SGExcelReporter(sg_results, rule_results, summary)
    filepath = reporter.generate(output_path)

    from core.tools.output import print_report_complete

    print_report_complete(filepath)

    # 폴더 열기
    open_in_explorer(output_path)


def _create_output_directory(ctx) -> str:
    """출력 디렉토리 생성"""
    # identifier 결정
    if hasattr(ctx, "is_sso_session") and ctx.is_sso_session() and ctx.accounts:
        identifier = ctx.accounts[0].id
    elif ctx.profile_name:
        identifier = ctx.profile_name
    else:
        identifier = "default"

    output_path = OutputPath(identifier).sub("vpc", "security").with_date().build()
    return output_path
