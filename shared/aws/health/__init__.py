"""
shared/aws/health - AWS Health 공통 모듈

- HealthAnalyzer: AWS Health API 호출
- HealthCollector: 이벤트 수집 및 분류
- PatchReporter: Excel 보고서 생성
- HealthDashboard: HTML 대시보드 생성
"""

from .analyzer import (
    HEALTH_REGION,
    REQUIRED_PERMISSIONS,
    AffectedEntity,
    EventFilter,
    HealthAnalyzer,
    HealthEvent,
)
from .collector import CollectionResult, HealthCollector, PatchItem
from .html_reporter import HealthDashboard, generate_dashboard
from .reporter import PatchReporter, generate_report

__all__ = [
    # analyzer
    "HEALTH_REGION",
    "REQUIRED_PERMISSIONS",
    "EventFilter",
    "AffectedEntity",
    "HealthEvent",
    "HealthAnalyzer",
    # collector
    "PatchItem",
    "CollectionResult",
    "HealthCollector",
    # reporter
    "PatchReporter",
    "generate_report",
    # html_reporter
    "HealthDashboard",
    "generate_dashboard",
]
