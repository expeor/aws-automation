"""
functions/analyzers/health/patch_analysis.py - 필수 패치 분석

예정된 패치/유지보수 이벤트 분석 보고서 (월별 일정표 포함)
HTML 대시보드 + Excel 보고서 생성
멀티 계정 지원: parallel_collect 패턴 사용

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console

from core.parallel import parallel_collect
from core.shared.aws.health import (
    REQUIRED_PERMISSIONS,  # noqa: F401
    CollectionResult,
    HealthCollector,
    HealthDashboard,
    PatchReporter,
)
from core.shared.io.output import OutputPath, open_in_explorer

if TYPE_CHECKING:
    from core.cli.flow.context import ExecutionContext

console = Console()


def _collect_patches(session, account_id: str, account_name: str, region: str) -> CollectionResult | None:
    """parallel_collect 콜백: 단일 계정의 예정된 패치/유지보수 이벤트를 수집한다.

    HealthCollector를 사용하여 향후 90일간의 scheduledChange 이벤트를
    수집한다. Business/Enterprise Support 플랜이 필요하다.

    Args:
        session: boto3 Session 객체.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 이름.
        region: 리전 (Health API는 항상 us-east-1에서 동작).

    Returns:
        수집 결과 CollectionResult. 패치가 없으면 None.
    """
    try:
        collector = HealthCollector(session, account_id, account_name)
        result = collector.collect_patches(days_ahead=90)

        if result.patch_count == 0:
            return None

        return result
    except Exception as e:
        # Health API 접근 불가 (Business/Enterprise Support 필요)
        if "SubscriptionRequiredException" in str(e):
            console.print(f"  [dim]{account_name}: Business/Enterprise Support 필요[/dim]")
            return None
        raise


def run(ctx: ExecutionContext) -> None:
    """필수 패치 분석 도구의 메인 실행 함수.

    예정된 패치/유지보수 이벤트를 분석하여 긴급도별로 분류하고,
    Excel 보고서(월별 캘린더 포함)와 HTML 대시보드를 생성한다.

    Args:
        ctx: 실행 컨텍스트. 계정 정보, 리전, 프로파일 등을 포함한다.
    """
    console.print("[bold]필수 패치 분석 시작...[/bold]\n")

    # 병렬 수집
    result = parallel_collect(ctx, _collect_patches, max_workers=10, service="health")

    # 결과 필터링 (None 제외)
    collection_results: list[CollectionResult] = [r for r in result.get_data() if r is not None]

    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")
        console.print(result.get_error_summary())

    if not collection_results:
        console.print("[yellow]예정된 패치가 없습니다.[/yellow]")
        return

    # 여러 계정의 결과 병합
    merged_result = CollectionResult.merge(collection_results)

    # 요약 출력
    reporter = PatchReporter(merged_result)
    reporter.print_summary()

    # 출력 경로 생성
    identifier = ctx.profile_name or "default"
    output_dir = OutputPath(identifier).sub("health", "compliance").with_date().build()

    # Excel 보고서 생성
    excel_path = reporter.generate_report(
        output_dir=output_dir,
        file_prefix="patch_analysis",
        include_calendar=True,
    )

    # HTML 대시보드 생성
    html_path = Path(output_dir) / "health_dashboard.html"
    dashboard = HealthDashboard(merged_result)
    dashboard.generate(html_path, auto_open=True)

    console.print("\n[green]보고서 생성 완료![/green]")
    console.print(f"  Excel: {excel_path}")
    console.print(f"  HTML: {html_path}")
    open_in_explorer(output_dir)
