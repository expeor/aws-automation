"""
plugins/health/issues.py - 서비스 장애 현황 조회

현재 진행 중인 AWS 서비스 장애 조회
멀티 계정 지원: parallel_collect 패턴 사용

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from core.parallel import parallel_collect

from .common import REQUIRED_PERMISSIONS, HealthCollector, HealthEvent  # noqa: F401

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

console = Console()


def _collect_issues(
    session, account_id: str, account_name: str, region: str
) -> list[HealthEvent] | None:
    """단일 계정의 서비스 장애 수집 (병렬 실행용)

    Args:
        session: boto3 Session
        account_id: AWS 계정 ID
        account_name: 계정 이름
        region: 리전 (Health API는 항상 us-east-1 사용)

    Returns:
        HealthEvent 리스트 또는 None
    """
    try:
        collector = HealthCollector(session, account_id, account_name)
        issues = collector.collect_issues()

        if not issues:
            return None

        return issues
    except Exception as e:
        # Health API 접근 불가 (Business/Enterprise Support 필요)
        if "SubscriptionRequiredException" in str(e):
            return None
        raise


def run(ctx: ExecutionContext) -> None:
    """서비스 장애 현황 조회"""
    console.print("[bold]서비스 장애 현황 조회 중...[/bold]\n")

    # 병렬 수집
    result = parallel_collect(ctx, _collect_issues, max_workers=10, service="health")

    # 결과 평탄화 (리스트의 리스트 → 단일 리스트)
    all_issues: list[HealthEvent] = []
    for issues in result.get_data():
        if issues is not None:
            all_issues.extend(issues)

    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")

    if not all_issues:
        console.print("[green]현재 진행 중인 서비스 장애가 없습니다.[/green]")
        return

    # 중복 제거 (같은 ARN의 이벤트)
    seen_arns = set()
    unique_issues = []
    for event in all_issues:
        if event.arn not in seen_arns:
            seen_arns.add(event.arn)
            unique_issues.append(event)

    console.print(f"[bold red]현재 {len(unique_issues)}개의 서비스 장애가 진행 중입니다:[/bold red]\n")

    # 테이블로 표시
    table = Table(title="서비스 장애 현황")
    table.add_column("서비스", style="cyan", width=12)
    table.add_column("이벤트 유형", width=30)
    table.add_column("리전", width=15)
    table.add_column("시작 시간", width=20)
    table.add_column("계정", width=20)
    table.add_column("설명", width=50)

    for event in unique_issues:
        start_time = event.start_time.strftime("%Y-%m-%d %H:%M") if event.start_time else "-"
        account_info = f"{event.account_name}" if event.account_name else event.account_id or "-"
        desc = event.description[:50] + "..." if len(event.description) > 50 else event.description
        desc = desc.replace("\n", " ")

        table.add_row(
            event.service,
            event.event_type_code,
            event.region,
            start_time,
            account_info,
            desc,
        )

    console.print(table)
