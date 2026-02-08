"""
functions/analyzers/health/analysis.py - PHD 전체 이벤트 분석

AWS Personal Health Dashboard 전체 이벤트 분석 및 보고서 생성
멀티 계정 지원: parallel_collect 패턴 사용

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from core.parallel import parallel_collect
from core.shared.aws.health import (
    REQUIRED_PERMISSIONS,  # noqa: F401
    CollectionResult,
    HealthCollector,
    PatchReporter,
)
from core.shared.io.output import OutputPath, open_in_explorer

if TYPE_CHECKING:
    from core.cli.flow.context import ExecutionContext

console = Console()


def _collect_health_events(session, account_id: str, account_name: str, region: str) -> CollectionResult | None:
    """parallel_collect 콜백: 단일 계정의 AWS Health 이벤트를 수집한다.

    HealthCollector를 사용하여 open/upcoming 상태의 모든 Health 이벤트를
    수집한다. Business/Enterprise Support 플랜이 필요하다.

    Args:
        session: boto3 Session 객체.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 이름.
        region: 리전 (Health API는 항상 us-east-1에서 동작).

    Returns:
        수집 결과 CollectionResult. 이벤트가 없으면 None.
    """
    try:
        collector = HealthCollector(session, account_id, account_name)
        result = collector.collect_all()

        if result.total_count == 0:
            return None

        return result
    except Exception as e:
        # Health API 접근 불가 (Business/Enterprise Support 필요)
        if "SubscriptionRequiredException" in str(e):
            console.print(f"  [dim]{account_name}: Business/Enterprise Support 필요[/dim]")
            return None
        raise


def run(ctx: ExecutionContext) -> None:
    """PHD 전체 이벤트 분석 도구의 메인 실행 함수.

    AWS Personal Health Dashboard의 모든 이벤트(패치, 알림, 장애)를
    수집하여 분석 요약을 출력하고 Excel 보고서를 생성한다.

    Args:
        ctx: 실행 컨텍스트. 계정 정보, 리전, 프로파일 등을 포함한다.
    """
    console.print("[bold]AWS Health 이벤트 분석 시작...[/bold]\n")

    # 병렬 수집 (Health API는 us-east-1에서만 동작하지만 리전 파라미터는 그대로 전달)
    result = parallel_collect(ctx, _collect_health_events, max_workers=10, service="health")

    # 결과 필터링 (None 제외)
    collection_results: list[CollectionResult] = [r for r in result.get_data() if r is not None]

    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")
        console.print(result.get_error_summary())

    if not collection_results:
        console.print("[yellow]Health 이벤트가 없습니다.[/yellow]")
        return

    # 여러 계정의 결과 병합
    merged_result = CollectionResult.merge(collection_results)

    # 요약 출력
    reporter = PatchReporter(merged_result)
    reporter.print_summary()

    # 출력 경로 생성
    identifier = ctx.profile_name or "default"
    output_dir = OutputPath(identifier).sub("health", "inventory").with_date().build()

    # 보고서 생성
    report_path = reporter.generate_report(
        output_dir=output_dir,
        file_prefix="phd_events",
    )

    console.print("\n[green]보고서 생성 완료![/green]")
    console.print(f"  {report_path}")
    open_in_explorer(output_dir)
