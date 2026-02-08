"""
analyzers/iam/user_snapshot.py - IAM 사용자 현황 보고서 도구

IAM 사용자 종합 현황 보고서 생성:
- 전체 사용자 목록 (Access Key, Git Credential, MFA 상태)
- 오래된 Access Key (90일+)
- 비활성 사용자 (자격 증명 없음)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from core.parallel import parallel_collect
from core.shared.io.output import OutputPath, get_context_identifier, open_in_explorer

from .iam_audit_analysis import IAMCollector
from .user_snapshot_reporter import UserSnapshotReporter

if TYPE_CHECKING:
    from core.cli.flow.context import ExecutionContext

    from .iam_audit_analysis.collector import IAMData

console = Console()


def _collect_user_data(session, account_id: str, account_name: str, region: str) -> IAMData | None:
    """단일 계정의 IAM 데이터 수집 (병렬 실행용)"""
    collector = IAMCollector()
    return collector.collect(session, account_id, account_name)


def run(ctx: ExecutionContext) -> None:
    """IAM 사용자 현황 보고서 실행"""
    console.print("[bold]IAM 사용자 현황 보고서 생성 중...[/bold]")

    # 1. 데이터 수집
    console.print("[cyan]Step 1: IAM 데이터 수집 중...[/cyan]")

    result = parallel_collect(ctx, _collect_user_data, max_workers=20, service="iam")

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
    reporter = UserSnapshotReporter(iam_data_list)
    filepath = reporter.generate(output_path)

    from core.shared.io.output import print_report_complete

    print_report_complete(filepath)
    open_in_explorer(output_path)


def _print_summary(iam_data_list: list[IAMData]) -> None:
    """분석 결과 요약 출력"""
    OLD_KEY_THRESHOLD = 90

    # 전체 통계 계산
    total_users = 0
    total_old_keys = 0
    total_inactive_users = 0

    for iam_data in iam_data_list:
        total_users += len(iam_data.users)

        for user in iam_data.users:
            # 오래된 키 계산
            for key in user.access_keys:
                if key.status == "Active" and key.age_days >= OLD_KEY_THRESHOLD:
                    total_old_keys += 1

            # 비활성 사용자 계산
            if not user.has_console_access and user.active_key_count == 0 and user.active_git_credential_count == 0:
                total_inactive_users += 1

    console.print("\n  [bold]사용자 현황[/bold]")
    console.print(f"    총 사용자: {total_users}명")
    if total_old_keys > 0:
        console.print(f"    [yellow]오래된 Access Key (90일+): {total_old_keys}개[/yellow]")
    if total_inactive_users > 0:
        console.print(f"    [yellow]비활성 사용자: {total_inactive_users}명[/yellow]")


def _create_output_directory(ctx) -> str:
    """출력 디렉토리 생성"""
    identifier = get_context_identifier(ctx)

    output_path = OutputPath(identifier).sub("iam", "user_snapshot").with_date().build()
    return output_path
