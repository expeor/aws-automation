"""
plugins/health/analysis.py - PHD 전체 이벤트 분석

AWS Personal Health Dashboard 전체 이벤트 분석 및 보고서 생성

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from typing import Any, Dict

from core.auth.session import get_context_session
from core.tools.output import OutputPath

from .analyzer import REQUIRED_PERMISSIONS  # noqa: F401
from .collector import HealthCollector
from .reporter import PatchReporter


def run(ctx) -> Dict[str, Any]:
    """PHD 전체 이벤트 분석 및 보고서 생성"""
    # AWS Health API는 us-east-1에서만 사용 가능
    session = get_context_session(ctx, "us-east-1")

    collector = HealthCollector(session)
    result = collector.collect_all()

    reporter = PatchReporter(result)
    reporter.print_summary()

    # 출력 경로 생성
    identifier = ctx.profile_name or "default"
    output_dir = OutputPath(identifier).sub("phd").with_date().build()

    output_path = reporter.generate_report(
        output_dir=output_dir,
        file_prefix="phd_events",
    )

    return {
        "total_events": result.total_count,
        "patch_count": result.patch_count,
        "critical_count": result.critical_count,
        "report_path": str(output_path),
    }
