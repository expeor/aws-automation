"""
plugins/health/phd - AWS Personal Health Dashboard 플러그인

AWS Health API를 통해 계정별 Health 이벤트를 조회하고 분석합니다.

## 지원하는 이벤트 유형

### Event Categories
- **scheduledChange**: 예정된 유지보수, 패치
- **accountNotification**: 계정 알림
- **issue**: 서비스 장애

### 긴급도 분류
- **critical**: 3일 이내 조치 필요
- **high**: 7일 이내 조치 필요
- **medium**: 14일 이내 조치 필요
- **low**: 14일 이후

## AWS 문서 참조
- AWS Health API: https://docs.aws.amazon.com/health/latest/APIReference/
- Health Dashboard: https://docs.aws.amazon.com/health/latest/ug/

## 사용법

    from plugins.health.phd import HealthAnalyzer, HealthCollector
    from plugins.health.phd.reporter import generate_report

    # 분석기 직접 사용
    analyzer = HealthAnalyzer(session)
    events = analyzer.get_scheduled_changes()

    # 수집기 사용
    collector = HealthCollector(session)
    result = collector.collect_patches()

    # 리포트 생성
    generate_report(result, output_dir="./reports")

## Note
    - AWS Health API는 us-east-1 리전에서만 사용 가능
    - Business/Enterprise Support 플랜 필요
    - Organizations 사용 시 조직 전체 이벤트 조회 가능
"""

from .analyzer import (
    HEALTH_REGION,
    AffectedEntity,
    EventFilter,
    HealthAnalyzer,
    HealthEvent,
)
from .collector import (
    CollectionResult,
    HealthCollector,
    PatchItem,
)
from .reporter import (
    PatchReporter,
    generate_report,
)

__all__ = [
    # Analyzer
    "HealthAnalyzer",
    "HealthEvent",
    "AffectedEntity",
    "EventFilter",
    "HEALTH_REGION",
    # Collector
    "HealthCollector",
    "CollectionResult",
    "PatchItem",
    # Reporter
    "PatchReporter",
    "generate_report",
]


# CLI 진입점 함수들
def run_analysis(session, output_dir: str = "./reports", **kwargs):
    """PHD 전체 이벤트 분석 및 보고서 생성"""
    collector = HealthCollector(session)
    result = collector.collect_all()

    reporter = PatchReporter(result)
    reporter.print_summary()

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


def run_patch_analysis(session, output_dir: str = "./reports", **kwargs):
    """필수 패치 분석 보고서 생성"""
    collector = HealthCollector(session)
    result = collector.collect_patches(days_ahead=90)

    reporter = PatchReporter(result)
    reporter.print_summary()

    output_path = reporter.generate_report(
        output_dir=output_dir,
        file_prefix="patch_analysis",
        include_calendar=True,
    )

    return {
        "patch_count": result.patch_count,
        "critical_count": result.critical_count,
        "high_count": result.high_count,
        "affected_resources": result.affected_resource_count,
        "report_path": str(output_path),
    }


def run_issues(session, **kwargs):
    """서비스 장애 현황 조회"""
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
            desc = event.description[:100] + "..." if len(event.description) > 100 else event.description
            print(f"    설명: {desc}")
        print()

    return {
        "issue_count": len(issues),
        "issues": [e.to_dict() for e in issues],
    }


# CLI 도구 정의 (health 모듈에서 참조)
TOOLS = [
    {
        "name": "PHD 전체 분석",
        "description": "AWS Personal Health Dashboard 전체 이벤트 분석 및 보고서 생성",
        "permission": "read",
        "module": "phd",
        "function": "run_analysis",
        "area": "monitoring",
    },
    {
        "name": "필수 패치 분석",
        "description": "예정된 패치/유지보수 이벤트 분석 보고서 (월별 일정표 포함)",
        "permission": "read",
        "module": "phd",
        "function": "run_patch_analysis",
        "area": "monitoring",
    },
    {
        "name": "서비스 장애 현황",
        "description": "현재 진행 중인 AWS 서비스 장애 조회",
        "permission": "read",
        "module": "phd",
        "function": "run_issues",
        "area": "monitoring",
    },
]
