"""
plugins/health/issues.py - 서비스 장애 현황 조회

현재 진행 중인 AWS 서비스 장애 조회

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.auth.session import get_context_session

from .common import REQUIRED_PERMISSIONS, HealthCollector  # noqa: F401

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext


def run(ctx: ExecutionContext) -> None:
    """서비스 장애 현황 조회"""
    # AWS Health API는 us-east-1에서만 사용 가능
    session = get_context_session(ctx, "us-east-1")

    collector = HealthCollector(session)
    issues = collector.collect_issues()

    if not issues:
        print("현재 진행 중인 서비스 장애가 없습니다.")
        return

    print(f"\n현재 {len(issues)}개의 서비스 장애가 진행 중입니다:\n")

    for event in issues:
        print(f"  [{event.service}] {event.event_type_code}")
        print(f"    리전: {event.region}")
        print(f"    시작: {event.start_time}")
        if event.description:
            desc = event.description[:100] + "..." if len(event.description) > 100 else event.description
            print(f"    설명: {desc}")
        print()
