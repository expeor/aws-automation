"""
core/shared/aws/health/collector.py - AWS Health 이벤트 수집기

Health 이벤트를 수집하고 패치/유지보수 중심으로 분류합니다.
- 긴급도별 분류 (critical, high, medium, low)
- 서비스별 분류
- 영향받는 리소스 집계

사용법:
    from functions.analyzers.health.phd.collector import HealthCollector

    collector = HealthCollector(session)
    result = collector.collect_patches()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .analyzer import HealthAnalyzer, HealthEvent

logger = logging.getLogger(__name__)


@dataclass
class PatchItem:
    """패치/유지보수 항목

    HealthEvent를 패치 분석에 적합한 형태로 가공한 데이터 클래스입니다.

    Attributes:
        event: 원본 HealthEvent 객체
        service: AWS 서비스 이름
        event_type: 이벤트 타입 코드
        urgency: 긴급도 (critical, high, medium, low)
        scheduled_date: 예정 일시
        deadline: 조치 마감 일시
        affected_resources: 영향받는 리소스 ID 목록
        action_required: 필요한 조치 설명 (한글)
        description_summary: 이벤트 설명 요약 (최대 200자)
    """

    event: HealthEvent
    service: str
    event_type: str
    urgency: str
    scheduled_date: datetime | None
    deadline: datetime | None
    affected_resources: list[str]
    action_required: str
    description_summary: str

    @classmethod
    def from_event(cls, event: HealthEvent) -> PatchItem:
        """HealthEvent에서 PatchItem 생성

        이벤트 설명을 요약하고, 이벤트 타입 코드에 따라 필요한 조치를 자동 판단합니다.

        Args:
            event: 원본 HealthEvent 객체

        Returns:
            변환된 PatchItem 인스턴스
        """
        # 설명에서 요약 추출 (첫 200자)
        summary = event.description[:200] + "..." if len(event.description) > 200 else event.description
        summary = summary.replace("\n", " ").strip()

        # 영향받는 리소스 목록
        affected = [e.entity_value for e in event.affected_entities]

        # 필요한 조치 판단
        action = cls._determine_action(event)

        return cls(
            event=event,
            service=event.service,
            event_type=event.event_type_code,
            urgency=event.urgency,
            scheduled_date=event.start_time,
            deadline=event.end_time,
            affected_resources=affected,
            action_required=action,
            description_summary=summary,
        )

    @staticmethod
    def _determine_action(event: HealthEvent) -> str:
        """필요한 조치 판단

        이벤트 타입 코드에서 키워드를 분석하여 한글 조치 메시지를 반환합니다.

        Args:
            event: HealthEvent 객체

        Returns:
            필요한 조치 설명 문자열 (한글)
        """
        code = event.event_type_code.lower()

        if "reboot" in code or "restart" in code:
            return "재부팅 필요"
        if "maintenance" in code:
            return "유지보수 예정"
        if "retirement" in code:
            return "인스턴스 교체 필요"
        if "persistent" in code:
            return "영구적 하드웨어 문제"
        if "security" in code:
            return "보안 패치 적용"
        if "update" in code or "upgrade" in code:
            return "업데이트 필요"
        if "deprecation" in code:
            return "서비스 종료 예정"

        return "확인 필요"


@dataclass
class CollectionResult:
    """수집 결과

    HealthCollector의 수집 결과를 담는 데이터 클래스입니다.

    Attributes:
        events: 전체 HealthEvent 목록
        patches: PatchItem 목록 (긴급도순 정렬)
        summary_by_urgency: 긴급도별 요약 (count, services, affected_resources)
        summary_by_service: 서비스별 요약 (count, 긴급도별 개수, affected_resources)
        summary_by_month: 월별 PatchItem 그룹 ("YYYY-MM" 키)
    """

    events: list[HealthEvent]
    patches: list[PatchItem]
    summary_by_urgency: dict[str, dict[str, Any]]
    summary_by_service: dict[str, dict[str, Any]]
    summary_by_month: dict[str, list[PatchItem]]

    @property
    def total_count(self) -> int:
        """전체 이벤트 수"""
        return len(self.events)

    @property
    def patch_count(self) -> int:
        """패치 항목 수"""
        return len(self.patches)

    @property
    def critical_count(self) -> int:
        """긴급 패치 수"""
        count: int = self.summary_by_urgency.get("critical", {}).get("count", 0)
        return count

    @property
    def high_count(self) -> int:
        """높은 우선순위 패치 수"""
        count: int = self.summary_by_urgency.get("high", {}).get("count", 0)
        return count

    @property
    def affected_resource_count(self) -> int:
        """영향받는 리소스 총 수"""
        return sum(len(p.affected_resources) for p in self.patches)

    def get_patches_by_urgency(self, urgency: str) -> list[PatchItem]:
        """긴급도별 패치 목록

        Args:
            urgency: 긴급도 ("critical", "high", "medium", "low")

        Returns:
            해당 긴급도의 PatchItem 리스트
        """
        return [p for p in self.patches if p.urgency == urgency]

    def get_patches_by_service(self, service: str) -> list[PatchItem]:
        """서비스별 패치 목록

        Args:
            service: AWS 서비스 이름 (예: "EC2", "RDS")

        Returns:
            해당 서비스의 PatchItem 리스트
        """
        return [p for p in self.patches if p.service == service]


class HealthCollector:
    """AWS Health 이벤트 수집기

    Health 이벤트를 수집하고 패치 분석에 필요한 형태로 가공합니다.
    """

    def __init__(self, session):
        """초기화

        Args:
            session: boto3.Session 객체
        """
        self.session = session
        self.analyzer = HealthAnalyzer(session)

    def collect_patches(
        self,
        services: list[str] | None = None,
        regions: list[str] | None = None,
        days_ahead: int = 90,
        include_open: bool = True,
    ) -> CollectionResult:
        """패치/유지보수 이벤트 수집

        Args:
            services: 서비스 필터
            regions: 리전 필터
            days_ahead: 조회할 미래 일수
            include_open: 진행 중인 이벤트 포함 여부

        Returns:
            CollectionResult 객체
        """
        # 예정된 변경 조회
        events = self.analyzer.get_scheduled_changes(
            services=services,
            regions=regions,
            days_ahead=days_ahead,
        )

        # 상태 필터링
        if not include_open:
            events = [e for e in events if e.status_code == "upcoming"]

        # PatchItem 변환
        patches = [PatchItem.from_event(e) for e in events]

        # 긴급도순 정렬
        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        patches.sort(
            key=lambda p: (
                urgency_order.get(p.urgency, 99),
                p.scheduled_date or datetime.max.replace(tzinfo=timezone.utc),
            )
        )

        # 요약 생성
        summary_by_urgency = self._summarize_by_urgency(patches)
        summary_by_service = self._summarize_by_service(patches)
        summary_by_month = self._group_by_month(patches)

        logger.info(
            f"패치 수집 완료: 전체 {len(events)}개, 긴급 {summary_by_urgency.get('critical', {}).get('count', 0)}개"
        )

        return CollectionResult(
            events=events,
            patches=patches,
            summary_by_urgency=summary_by_urgency,
            summary_by_service=summary_by_service,
            summary_by_month=summary_by_month,
        )

    def collect_all(
        self,
        services: list[str] | None = None,
        regions: list[str] | None = None,
    ) -> CollectionResult:
        """모든 Health 이벤트 수집

        Args:
            services: 서비스 필터
            regions: 리전 필터

        Returns:
            CollectionResult 객체
        """
        events = self.analyzer.get_events(
            services=services,
            regions=regions,
            event_status_codes=["open", "upcoming"],
        )

        # scheduledChange만 패치로 분류
        patch_events = [e for e in events if e.is_scheduled_change]
        patches = [PatchItem.from_event(e) for e in patch_events]

        urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        patches.sort(
            key=lambda p: (
                urgency_order.get(p.urgency, 99),
                p.scheduled_date or datetime.max.replace(tzinfo=timezone.utc),
            )
        )

        summary_by_urgency = self._summarize_by_urgency(patches)
        summary_by_service = self._summarize_by_service(patches)
        summary_by_month = self._group_by_month(patches)

        return CollectionResult(
            events=events,
            patches=patches,
            summary_by_urgency=summary_by_urgency,
            summary_by_service=summary_by_service,
            summary_by_month=summary_by_month,
        )

    def collect_issues(
        self,
        services: list[str] | None = None,
        regions: list[str] | None = None,
    ) -> list[HealthEvent]:
        """서비스 장애 이벤트 수집

        Args:
            services: 서비스 필터
            regions: 리전 필터

        Returns:
            장애 이벤트 리스트
        """
        issues: list[HealthEvent] = self.analyzer.get_issues(
            services=services,
            regions=regions,
            include_closed=False,
        )
        return issues

    def _summarize_by_urgency(self, patches: list[PatchItem]) -> dict[str, dict[str, Any]]:
        """긴급도별 요약

        Args:
            patches: PatchItem 목록

        Returns:
            긴급도를 키로 하는 요약 딕셔너리
        """
        summary: dict[str, dict[str, Any]] = {}

        for patch in patches:
            urgency = patch.urgency
            if urgency not in summary:
                summary[urgency] = {
                    "count": 0,
                    "services": set(),
                    "affected_resources": 0,
                }

            summary[urgency]["count"] += 1
            summary[urgency]["services"].add(patch.service)
            summary[urgency]["affected_resources"] += len(patch.affected_resources)

        # set을 list로 변환
        for urgency in summary:
            summary[urgency]["services"] = list(summary[urgency]["services"])

        return summary

    def _summarize_by_service(self, patches: list[PatchItem]) -> dict[str, dict[str, Any]]:
        """서비스별 요약

        Args:
            patches: PatchItem 목록

        Returns:
            서비스명을 키로 하는 요약 딕셔너리
        """
        summary: dict[str, dict[str, Any]] = {}

        for patch in patches:
            service = patch.service
            if service not in summary:
                summary[service] = {
                    "count": 0,
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                    "affected_resources": 0,
                }

            summary[service]["count"] += 1
            summary[service][patch.urgency] = summary[service].get(patch.urgency, 0) + 1
            summary[service]["affected_resources"] += len(patch.affected_resources)

        return summary

    def _group_by_month(self, patches: list[PatchItem]) -> dict[str, list[PatchItem]]:
        """월별 그룹화

        Args:
            patches: PatchItem 목록

        Returns:
            "YYYY-MM" 또는 "미정"을 키로, PatchItem 리스트를 값으로 하는 딕셔너리
        """
        grouped: dict[str, list[PatchItem]] = {}

        for patch in patches:
            month_key = patch.scheduled_date.strftime("%Y-%m") if patch.scheduled_date else "미정"

            if month_key not in grouped:
                grouped[month_key] = []

            grouped[month_key].append(patch)

        return grouped
