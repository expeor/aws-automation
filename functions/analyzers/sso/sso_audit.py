"""
functions/analyzers/sso/sso_audit.py - IAM Identity Center 종합 점검 도구

IAM Identity Center(SSO) 보안 감사:
- Permission Set: 위험 정책 분석, Admin 권한 현황
- Users: 미사용 사용자, Admin 권한 현황
- Groups: 빈 그룹, Admin 그룹
- Account Assignments: 직접 할당 검토

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
    - collect_options(ctx): 선택. 추가 옵션 수집.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from botocore.exceptions import ClientError
from rich.console import Console

from core.auth import SessionIterator
from core.parallel import get_client
from core.shared.io.output import OutputPath, get_context_identifier, open_in_explorer

from .sso_audit_analysis import SSOAnalyzer, SSOCollector, SSOExcelReporter

if TYPE_CHECKING:
    from core.cli.flow.context import ExecutionContext

logger = logging.getLogger(__name__)

console = Console()

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "sso:ListInstances",
        "sso:ListPermissionSets",
        "sso:DescribePermissionSet",
        "sso:ListAccountAssignments",
        "identitystore:ListUsers",
        "identitystore:ListGroups",
        "identitystore:ListGroupMemberships",
    ],
}


def run(ctx: ExecutionContext) -> None:
    """IAM Identity Center 종합 점검 도구의 메인 실행 함수.

    SSO 데이터를 수집(Permission Set, Users, Groups, Account Assignments)하고
    보안 분석을 수행한 뒤, 결과를 콘솔에 요약 출력하고 Excel 보고서를 생성한다.
    SSO는 글로벌 서비스이므로 Identity Center 관리 계정에서 한 번만 수집한다.

    Args:
        ctx: 실행 컨텍스트 (인증 정보, 계정/리전 목록, 옵션 등 포함).
    """
    console.print("[bold]IAM Identity Center 종합 점검 시작...[/bold]")

    # 1. 데이터 수집
    console.print("[cyan]Step 1: SSO 데이터 수집 중...[/cyan]")

    collector = SSOCollector()
    all_results = []
    all_stats = []
    collected = False

    with SessionIterator(ctx) as sessions:
        for session, identifier, _region in sessions:
            # SSO는 글로벌 서비스이므로 한 번만 수집
            if collected:
                break

            # Initialize account_name before try block
            account_name = identifier
            try:
                # STS로 Account ID 조회
                sts = get_client(session, "sts")
                account_id = sts.get_caller_identity()["Account"]

                # Account Name 결정 (override if found in ctx.accounts)
                if hasattr(ctx, "accounts") and ctx.accounts:
                    for acc in ctx.accounts:
                        if acc.id == account_id:
                            account_name = acc.name
                            break

                console.print(f"  [dim]{account_name} ({account_id})[/dim]")

                # 데이터 수집 (Identity Center 관리 계정에서만 가능)
                sso_data = collector.collect(session, account_id, account_name)

                if sso_data is None:
                    console.print("[yellow]이 계정에서 Identity Center에 접근할 수 없습니다.[/yellow]")
                    console.print("[dim]Identity Center 관리 계정으로 다시 시도하세요.[/dim]")
                    continue

                # 분석
                analyzer = SSOAnalyzer(sso_data)
                analysis_result = analyzer.analyze()
                stats = analyzer.get_summary_stats(analysis_result)

                all_results.append(analysis_result)
                all_stats.append(stats)
                collected = True

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_msg = e.response.get("Error", {}).get("Message", str(e))

                if error_code == "AccessDeniedException":
                    logger.info(f"SSO 접근 권한 부족: {error_code} - {error_msg}")
                    console.print(f"[yellow]접근 권한 부족: {error_msg}[/yellow]")
                    console.print("[dim]sso-admin:* 및 identitystore:* 권한이 필요합니다.[/dim]")
                else:
                    logger.warning(f"SSO 오류: {error_code} - {error_msg}")
                    console.print(f"[red]오류: {error_code} - {error_msg}[/red]")
                continue
            except Exception as e:
                logger.error(f"{account_name} 수집 오류: {type(e).__name__} - {e}")
                console.print(f"[red]{account_name} 수집 오류: {type(e).__name__} - {e}[/red]")
                continue

    # 건너뛴 계정/오류 출력
    if collector.errors:
        console.print(f"[dim]  (오류 {len(collector.errors)}건)[/dim]")

    if not all_results:
        console.print("[yellow]수집된 SSO 데이터가 없습니다.[/yellow]")
        if collector.errors:
            console.print("[red]오류 목록:[/red]")
            for err in collector.errors[:5]:
                console.print(f"  - {err}")
        return

    console.print("[green]SSO 데이터 수집 완료[/green]")

    # 2. 분석 결과 출력
    console.print("[cyan]Step 2: 분석 결과 요약[/cyan]")
    _print_summary(all_stats)

    # 3. Excel 보고서 생성
    console.print("[cyan]Step 3: Excel 보고서 생성 중...[/cyan]")

    output_path = _create_output_directory(ctx)
    reporter = SSOExcelReporter(all_results, all_stats)
    filepath = reporter.generate(output_path)

    from core.shared.io.output import print_report_complete

    print_report_complete(filepath)

    # 오류 출력
    if collector.errors:
        console.print(f"\n[yellow]수집 중 오류 {len(collector.errors)}건:[/yellow]")
        for err in collector.errors[:5]:
            console.print(f"  - {err}")
        if len(collector.errors) > 5:
            console.print(f"  ... 외 {len(collector.errors) - 5}건")

    # 폴더 열기
    open_in_explorer(output_path)


def _print_summary(stats_list: list[dict[str, Any]]) -> None:
    """SSO 분석 결과를 콘솔에 요약 출력한다.

    Critical/High 이슈, Permission Set 통계(Admin/위험 정책),
    User 통계(Admin 권한/미할당), Group 통계(빈 그룹)를 표시한다.

    Args:
        stats_list: 계정별 분석 통계 딕셔너리 목록.
    """
    # 전체 통계 계산
    totals = {
        "total_users": sum(s.get("total_users", 0) for s in stats_list),
        "total_groups": sum(s.get("total_groups", 0) for s in stats_list),
        "total_permission_sets": sum(s.get("total_permission_sets", 0) for s in stats_list),
        "users_with_admin": sum(s.get("users_with_admin", 0) for s in stats_list),
        "users_no_assignment": sum(s.get("users_no_assignment", 0) for s in stats_list),
        "admin_permission_sets": sum(s.get("admin_permission_sets", 0) for s in stats_list),
        "high_risk_permission_sets": sum(s.get("high_risk_permission_sets", 0) for s in stats_list),
        "empty_groups": sum(s.get("empty_groups", 0) for s in stats_list),
        "critical_issues": sum(s.get("critical_issues", 0) for s in stats_list),
        "high_issues": sum(s.get("high_issues", 0) for s in stats_list),
        "medium_issues": sum(s.get("medium_issues", 0) for s in stats_list),
        "low_issues": sum(s.get("low_issues", 0) for s in stats_list),
    }

    # Critical/High Issues
    if totals["critical_issues"] > 0:
        console.print(f"  [red bold]CRITICAL 이슈: {totals['critical_issues']}건[/red bold]")
    if totals["high_issues"] > 0:
        console.print(f"  [yellow]HIGH 이슈: {totals['high_issues']}건[/yellow]")

    # Permission Set 통계
    console.print(f"\n  [bold]Permission Sets:[/bold] 총 {totals['total_permission_sets']}개")
    if totals["admin_permission_sets"] > 0:
        console.print(f"    - Admin 권한: [yellow]{totals['admin_permission_sets']}개[/yellow]")
    if totals["high_risk_permission_sets"] > 0:
        console.print(f"    - 위험 정책 포함: [yellow]{totals['high_risk_permission_sets']}개[/yellow]")

    # User 통계
    console.print(f"\n  [bold]Users:[/bold] 총 {totals['total_users']}명")
    if totals["users_with_admin"] > 0:
        console.print(f"    - Admin 권한: [yellow]{totals['users_with_admin']}명[/yellow]")
    if totals["users_no_assignment"] > 0:
        console.print(f"    - 미할당 (미사용): [dim]{totals['users_no_assignment']}명[/dim]")

    # Group 통계
    console.print(f"\n  [bold]Groups:[/bold] 총 {totals['total_groups']}개")
    if totals["empty_groups"] > 0:
        console.print(f"    - 빈 그룹: [dim]{totals['empty_groups']}개[/dim]")


def _create_output_directory(ctx) -> str:
    """SSO 보고서 출력 디렉토리 경로를 생성한다.

    Args:
        ctx: 실행 컨텍스트.

    Returns:
        날짜가 포함된 출력 디렉토리 경로 문자열.
    """
    # identifier 결정
    identifier = get_context_identifier(ctx)

    output_path = OutputPath(identifier).sub("sso", "inventory").with_date().build()
    return output_path
