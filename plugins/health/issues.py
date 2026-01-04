"""
plugins/health/issues.py - 서비스 장애 현황 조회

현재 진행 중인 AWS 서비스 장애 조회

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from typing import Any

from core.auth.session import get_context_session

from .analyzer import REQUIRED_PERMISSIONS  # noqa: F401
from .collector import HealthCollector


def run(ctx) -> dict[str, Any]:
    """서비스 장애 현황 조회"""
    # AWS Health API는 us-east-1에서만 사용 가능
    session = get_context_session(ctx, "us-east-1")

    collector = HealthCollector(session)
    issues = collector.collect_issues()

    if not issues:
        print("현재 진행 중인 서비스 장애가 없습니다.")
        return {"issue_count": 0, "issues": []}

    print(f"\n현재 {len(issues)}개의 서비스 장애가 진행 중입니다:\n")

    for event in issues:
        print(f"  [{event.service}] {event.event_type_code}")
        print(f"    리전: {event.region}")
        print(f"    시작: {event.start_time}")
        if event.description:
            desc = (
                event.description[:100] + "..."
                if len(event.description) > 100
                else event.description
            )
            print(f"    설명: {desc}")
        print()

    return {
        "issue_count": len(issues),
        "issues": [e.to_dict() for e in issues],
    }
