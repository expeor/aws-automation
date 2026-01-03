"""
plugins/iam/iam_audit.py - IAM 종합 점검 도구

IAM 보안 감사 및 모범 사례 점검:
- Users: MFA 설정, Access Key 관리, 비활성 사용자
- Roles: 미사용 Role, 과도한 권한
- Password Policy: 보안 수준 평가
- Account: Root 계정 보안

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
    - collect_options(ctx): 선택. 추가 옵션 수집.
"""

from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.table import Table

from core.parallel import parallel_collect
from core.tools.output import OutputPath, open_in_explorer

from .iam_audit_analysis import IAMAnalyzer, IAMCollector, IAMExcelReporter

console = Console()


def _collect_and_analyze(
    session, account_id: str, account_name: str, region: str
) -> Optional[Tuple[Any, Dict[str, Any]]]:
    """단일 계정의 IAM 수집 및 분석 (병렬 실행용)"""
    collector = IAMCollector()
    iam_data = collector.collect(session, account_id, account_name)
    analyzer = IAMAnalyzer(iam_data)
    analysis_result = analyzer.analyze()
    stats = analyzer.get_summary_stats(analysis_result)
    return (analysis_result, stats)


def run(ctx) -> None:
    """IAM 종합 점검 실행"""
    console.print("[bold]IAM 종합 점검 시작...[/bold]")

    # 1. 데이터 수집 (IAM은 글로벌이지만 병렬 처리 프레임워크 사용)
    console.print("[cyan]Step 1: IAM 데이터 수집 중...[/cyan]")

    # 병렬 수집 및 분석
    result = parallel_collect(ctx, _collect_and_analyze, max_workers=20, service="iam")

    # 결과 분리
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
        console.print("[yellow]수집된 IAM 데이터가 없습니다.[/yellow]")
        return

    console.print(f"[green]{len(all_results)}개 계정 데이터 수집 완료[/green]")

    # 2. 분석 결과 출력
    console.print("[cyan]Step 2: 분석 결과 요약[/cyan]")
    _print_summary(all_stats)

    # 3. Excel 보고서 생성
    console.print("[cyan]Step 3: Excel 보고서 생성 중...[/cyan]")

    output_path = _create_output_directory(ctx)
    reporter = IAMExcelReporter(all_results, all_stats)
    filepath = reporter.generate(output_path)

    console.print(f"[bold green]보고서 생성 완료![/bold green]")
    console.print(f"  경로: {filepath}")

    # 폴더 열기
    open_in_explorer(output_path)


def _print_summary(stats_list: List[Dict[str, Any]]) -> None:
    """분석 결과 요약 출력"""
    # 전체 통계 계산
    totals = {
        "total_users": sum(s["total_users"] for s in stats_list),
        "users_without_mfa": sum(s["users_without_mfa"] for s in stats_list),
        "inactive_users": sum(s["inactive_users"] for s in stats_list),
        "total_active_keys": sum(s["total_active_keys"] for s in stats_list),
        "old_keys": sum(s["old_keys"] for s in stats_list),
        "unused_keys": sum(s["unused_keys"] for s in stats_list),
        "total_roles": sum(s["total_roles"] for s in stats_list),
        "unused_roles": sum(s["unused_roles"] for s in stats_list),
        "admin_roles": sum(s["admin_roles"] for s in stats_list),
        "critical_issues": sum(s["critical_issues"] for s in stats_list),
        "high_issues": sum(s["high_issues"] for s in stats_list),
        "medium_issues": sum(s["medium_issues"] for s in stats_list),
        "root_access_key_count": sum(1 for s in stats_list if s["root_access_key"]),
        "root_no_mfa_count": sum(1 for s in stats_list if not s["root_mfa"]),
    }

    # Critical Issues
    if totals["critical_issues"] > 0 or totals["root_access_key_count"] > 0:
        console.print(
            f"  [red bold]CRITICAL 이슈: {totals['critical_issues']}건[/red bold]"
        )
        if totals["root_access_key_count"] > 0:
            console.print(
                f"    - Root Access Key 존재: {totals['root_access_key_count']}개 계정"
            )
        if totals["root_no_mfa_count"] > 0:
            console.print(f"    - Root MFA 미설정: {totals['root_no_mfa_count']}개 계정")

    if totals["high_issues"] > 0:
        console.print(f"  [yellow]HIGH 이슈: {totals['high_issues']}건[/yellow]")

    # User 통계
    console.print(f"\n  [bold]Users:[/bold] 총 {totals['total_users']}명")
    if totals["users_without_mfa"] > 0:
        console.print(f"    - MFA 미설정: [yellow]{totals['users_without_mfa']}명[/yellow]")
    if totals["inactive_users"] > 0:
        console.print(f"    - 비활성 (90일+): [yellow]{totals['inactive_users']}명[/yellow]")

    # Access Key 통계
    console.print(f"\n  [bold]Access Keys:[/bold] 총 {totals['total_active_keys']}개 활성")
    if totals["old_keys"] > 0:
        console.print(f"    - 오래된 키 (90일+): [yellow]{totals['old_keys']}개[/yellow]")
    if totals["unused_keys"] > 0:
        console.print(f"    - 미사용 키: [yellow]{totals['unused_keys']}개[/yellow]")

    # Role 통계
    console.print(f"\n  [bold]Roles:[/bold] 총 {totals['total_roles']}개")
    if totals["unused_roles"] > 0:
        console.print(f"    - 미사용 (90일+): [yellow]{totals['unused_roles']}개[/yellow]")
    if totals["admin_roles"] > 0:
        console.print(f"    - 관리자 권한: [dim]{totals['admin_roles']}개[/dim]")


def _create_output_directory(ctx) -> str:
    """출력 디렉토리 생성"""
    # identifier 결정
    if hasattr(ctx, "is_sso_session") and ctx.is_sso_session() and ctx.accounts:
        identifier = ctx.accounts[0].id
    elif ctx.profile_name:
        identifier = ctx.profile_name
    else:
        identifier = "default"

    output_path = OutputPath(identifier).sub("iam-audit").with_date().build()
    return output_path
