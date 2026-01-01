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

from typing import Any, Dict, List

from botocore.exceptions import ClientError
from rich.console import Console
from rich.table import Table

from core.auth import SessionIterator
from core.tools.output import OutputPath, open_in_explorer

from .iam_audit_analysis import (
    IAMCollector,
    IAMAnalyzer,
    IAMExcelReporter,
)

console = Console()


def run(ctx) -> None:
    """IAM 종합 점검 실행"""
    console.print("[bold]IAM 종합 점검 시작...[/bold]")

    # 1. 데이터 수집
    console.print("[cyan]Step 1: IAM 데이터 수집 중...[/cyan]")

    collector = IAMCollector()
    all_results = []
    all_stats = []
    skipped_accounts = []

    # 중복 방지를 위한 수집 완료 추적
    collected_accounts = set()

    with SessionIterator(ctx) as sessions:
        for session, identifier, region in sessions:
            try:
                # STS로 실제 Account ID 조회
                sts = session.client("sts")
                account_id = sts.get_caller_identity()["Account"]

                # IAM은 글로벌 서비스이므로 계정당 한 번만 수집
                if account_id in collected_accounts:
                    continue
                collected_accounts.add(account_id)

                # Account Name 결정
                account_name = identifier
                if hasattr(ctx, "accounts") and ctx.accounts:
                    for acc in ctx.accounts:
                        if acc.id == account_id:
                            account_name = acc.name
                            break

                console.print(f"  [dim]{account_name} ({account_id})[/dim]")

                # 데이터 수집
                iam_data = collector.collect(session, account_id, account_name)

                # 분석
                analyzer = IAMAnalyzer(iam_data)
                analysis_result = analyzer.analyze()
                stats = analyzer.get_summary_stats(analysis_result)

                all_results.append(analysis_result)
                all_stats.append(stats)

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                skipped_accounts.append(f"{identifier}: {error_code}")
                continue
            except Exception as e:
                skipped_accounts.append(f"{identifier}: {str(e)}")
                continue

    # 건너뛴 계정 출력
    if skipped_accounts:
        console.print(f"[dim]  (접근 불가 계정 {len(skipped_accounts)}개 건너뜀)[/dim]")

    if not all_results:
        console.print("[yellow]수집된 IAM 데이터가 없습니다.[/yellow]")
        if collector.errors:
            console.print("[red]오류 목록:[/red]")
            for err in collector.errors:
                console.print(f"  - {err}")
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
            console.print(
                f"    - Root MFA 미설정: {totals['root_no_mfa_count']}개 계정"
            )

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
