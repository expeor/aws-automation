"""
plugins/health/analysis.py - PHD 전체 이벤트 분석

AWS Personal Health Dashboard 전체 이벤트 분석 및 보고서 생성

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.auth.session import get_context_session
from core.tools.output import OutputPath

from shared.aws.health import REQUIRED_PERMISSIONS, HealthCollector, PatchReporter  # noqa: F401

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext


def run(ctx: ExecutionContext) -> None:
    """PHD 전체 이벤트 분석 및 보고서 생성"""
    # AWS Health API는 us-east-1에서만 사용 가능
    session = get_context_session(ctx, "us-east-1")

    collector = HealthCollector(session)
    result = collector.collect_all()

    reporter = PatchReporter(result)
    reporter.print_summary()

    # 출력 경로 생성
    identifier = ctx.profile_name or "default"
    output_dir = OutputPath(identifier).sub("health", "inventory").with_date().build()

    reporter.generate_report(
        output_dir=output_dir,
        file_prefix="phd_events",
    )
