"""
functions/analyzers/health/common/analyzer.py - AWS Personal Health Dashboard 분석기

AWS Health API를 호출하여 계정별 Health 이벤트를 조회합니다.
- scheduledChange: 예정된 유지보수, 패치
- accountNotification: 계정 알림
- issue: 서비스 장애

Note:
    AWS Health API는 us-east-1에서만 사용 가능합니다.
    Business/Enterprise Support 플랜이 필요합니다.

사용법:
    from functions.analyzers.health.phd.analyzer import HealthAnalyzer

    analyzer = HealthAnalyzer(session)
    events = analyzer.get_events(
        event_type_categories=["scheduledChange"],
        services=["EC2", "RDS"],
    )
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# AWS Health API는 us-east-1에서만 사용 가능
HEALTH_REGION = "us-east-1"

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "health:DescribeEvents",
        "health:DescribeEventDetails",
        "health:DescribeAffectedEntities",
    ],
}


@dataclass
class EventFilter:
    """AWS Health API 이벤트 조회 필터.

    Attributes:
        event_type_categories: 이벤트 카테고리 목록 (scheduledChange, accountNotification, issue, investigation).
        services: AWS 서비스명 목록 (EC2, RDS 등).
        regions: 리전 목록.
        availability_zones: 가용 영역 목록.
        event_type_codes: 이벤트 유형 코드 목록.
        event_status_codes: 상태 코드 목록 (open, upcoming, closed).
        start_time_from: 시작 시간 필터 (from).
        start_time_to: 시작 시간 필터 (to).
        end_time_from: 종료 시간 필터 (from).
        end_time_to: 종료 시간 필터 (to).
    """

    event_type_categories: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    regions: list[str] = field(default_factory=list)
    availability_zones: list[str] = field(default_factory=list)
    event_type_codes: list[str] = field(default_factory=list)
    event_status_codes: list[str] = field(default_factory=list)
    start_time_from: datetime | None = None
    start_time_to: datetime | None = None
    end_time_from: datetime | None = None
    end_time_to: datetime | None = None

    # 지원되는 Event Type Categories
    VALID_EVENT_CATEGORIES = [
        "scheduledChange",  # 예정된 유지보수, 패치
        "accountNotification",  # 계정 알림
        "issue",  # 서비스 장애
        "investigation",  # 조사 중
    ]

    # 지원되는 Event Status Codes
    VALID_STATUS_CODES = [
        "open",  # 진행 중
        "upcoming",  # 예정됨
        "closed",  # 완료됨
    ]

    def to_api_filter(self) -> dict[str, Any]:
        """AWS Health API의 describe_events 필터 형식으로 변환한다.

        Returns:
            AWS Health API filter 파라미터 딕셔너리.
        """
        api_filter: dict[str, Any] = {}

        if self.event_type_categories:
            api_filter["eventTypeCategories"] = self.event_type_categories
        if self.services:
            api_filter["services"] = self.services
        if self.regions:
            api_filter["regions"] = self.regions
        if self.availability_zones:
            api_filter["availabilityZones"] = self.availability_zones
        if self.event_type_codes:
            api_filter["eventTypeCodes"] = self.event_type_codes
        if self.event_status_codes:
            api_filter["eventStatusCodes"] = self.event_status_codes

        # 시간 필터
        if self.start_time_from or self.start_time_to:
            api_filter["startTimes"] = []
            if self.start_time_from:
                api_filter["startTimes"].append({"from": self.start_time_from})
            if self.start_time_to:
                if api_filter["startTimes"]:
                    api_filter["startTimes"][0]["to"] = self.start_time_to
                else:
                    api_filter["startTimes"].append({"to": self.start_time_to})

        if self.end_time_from or self.end_time_to:
            api_filter["endTimes"] = []
            if self.end_time_from:
                api_filter["endTimes"].append({"from": self.end_time_from})
            if self.end_time_to:
                if api_filter["endTimes"]:
                    api_filter["endTimes"][0]["to"] = self.end_time_to
                else:
                    api_filter["endTimes"].append({"to": self.end_time_to})

        return api_filter


@dataclass
class AffectedEntity:
    """Health 이벤트에 영향받는 AWS 리소스 정보.

    Attributes:
        entity_value: 리소스 ID (예: i-1234567890abcdef0).
        aws_account_id: 리소스가 속한 AWS 계정 ID.
        entity_url: 리소스 콘솔 URL.
        status_code: 리소스 영향 상태 (PENDING, RESOLVED 등).
        last_updated_time: 마지막 업데이트 시각.
        tags: 리소스 태그 딕셔너리.
    """

    entity_value: str  # 리소스 ID (예: i-1234567890abcdef0)
    aws_account_id: str
    entity_url: str
    status_code: str  # PENDING, RESOLVED, etc.
    last_updated_time: datetime | None = None
    tags: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, item: dict[str, Any]) -> AffectedEntity:
        """AWS Health API 응답에서 AffectedEntity 객체를 생성한다.

        Args:
            item: describe_affected_entities 응답의 개별 엔티티 딕셔너리.

        Returns:
            AffectedEntity 인스턴스.
        """
        tags_list = item.get("tags", {})
        tags_dict = tags_list if isinstance(tags_list, dict) else {}

        return cls(
            entity_value=item.get("entityValue", ""),
            aws_account_id=item.get("awsAccountId", ""),
            entity_url=item.get("entityUrl", ""),
            status_code=item.get("statusCode", ""),
            last_updated_time=item.get("lastUpdatedTime"),
            tags=tags_dict,
        )


@dataclass
class HealthEvent:
    """AWS Health 이벤트 상세 정보.

    Attributes:
        arn: 이벤트 ARN.
        service: AWS 서비스명 (EC2, RDS 등).
        event_type_code: 이벤트 유형 코드 (AWS_EC2_PERSISTENT_INSTANCE_RETIREMENT 등).
        event_type_category: 이벤트 카테고리 (scheduledChange, issue, accountNotification).
        region: 이벤트 발생 리전.
        availability_zone: 영향받는 가용 영역.
        start_time: 이벤트 시작 시각.
        end_time: 이벤트 종료 시각.
        last_updated_time: 마지막 업데이트 시각.
        status_code: 이벤트 상태 (open, upcoming, closed).
        event_scope_code: 이벤트 범위 (ACCOUNT_SPECIFIC, PUBLIC 등).
        description: 이벤트 상세 설명.
        affected_entities: 영향받는 리소스 목록.
        account_id: AWS 계정 ID (멀티 계정 지원용).
        account_name: AWS 계정 이름 (멀티 계정 지원용).
    """

    arn: str
    service: str
    event_type_code: str
    event_type_category: str
    region: str
    availability_zone: str
    start_time: datetime | None
    end_time: datetime | None
    last_updated_time: datetime | None
    status_code: str
    event_scope_code: str  # ACCOUNT_SPECIFIC, PUBLIC, etc.
    description: str
    affected_entities: list[AffectedEntity] = field(default_factory=list)
    # 멀티 계정 지원을 위한 필드
    account_id: str = ""
    account_name: str = ""

    @property
    def is_scheduled_change(self) -> bool:
        """예정된 변경(scheduledChange) 이벤트인지 여부.

        Returns:
            scheduledChange 카테고리이면 True.
        """
        return self.event_type_category == "scheduledChange"

    @property
    def is_issue(self) -> bool:
        """서비스 장애(issue) 이벤트인지 여부.

        Returns:
            issue 카테고리이면 True.
        """
        return self.event_type_category == "issue"

    @property
    def is_upcoming(self) -> bool:
        """예정된(upcoming) 이벤트인지 여부.

        Returns:
            상태가 upcoming이면 True.
        """
        return self.status_code == "upcoming"

    @property
    def is_open(self) -> bool:
        """진행 중인(open) 이벤트인지 여부.

        Returns:
            상태가 open이면 True.
        """
        return self.status_code == "open"

    @property
    def days_until_start(self) -> int | None:
        """이벤트 시작까지 남은 일수.

        Returns:
            남은 일수. start_time이 없으면 None, 이미 시작된 경우 0.
        """
        if not self.start_time:
            return None
        now = datetime.now(timezone.utc)
        delta = self.start_time - now
        return max(0, delta.days)

    @property
    def urgency(self) -> str:
        """이벤트 시작일까지 남은 일수 기반 긴급도 판단.

        3일 이내: critical, 7일 이내: high, 14일 이내: medium, 그 외: low.

        Returns:
            긴급도 문자열 (critical, high, medium, low).
        """
        days = self.days_until_start

        if days is None:
            return "medium"
        if days <= 3:
            return "critical"
        if days <= 7:
            return "high"
        if days <= 14:
            return "medium"
        return "low"

    @classmethod
    def from_api_response(
        cls,
        event_item: dict[str, Any],
        detail_item: dict[str, Any] | None = None,
    ) -> HealthEvent:
        """AWS Health API 응답에서 HealthEvent 객체를 생성한다.

        Args:
            event_item: describe_events 응답의 개별 이벤트 딕셔너리.
            detail_item: describe_event_details 응답의 상세 정보 (선택).

        Returns:
            HealthEvent 인스턴스.
        """
        description = ""
        if detail_item:
            desc_list = detail_item.get("eventDescription", {}).get("latestDescription", "")
            description = desc_list

        return cls(
            arn=event_item.get("arn", ""),
            service=event_item.get("service", ""),
            event_type_code=event_item.get("eventTypeCode", ""),
            event_type_category=event_item.get("eventTypeCategory", ""),
            region=event_item.get("region", ""),
            availability_zone=event_item.get("availabilityZone", ""),
            start_time=event_item.get("startTime"),
            end_time=event_item.get("endTime"),
            last_updated_time=event_item.get("lastUpdatedTime"),
            status_code=event_item.get("statusCode", ""),
            event_scope_code=event_item.get("eventScopeCode", ""),
            description=description,
        )

    def to_dict(self) -> dict[str, Any]:
        """이벤트 정보를 딕셔너리로 변환한다 (리포트 출력용).

        Returns:
            이벤트 정보 딕셔너리.
        """
        return {
            "arn": self.arn,
            "service": self.service,
            "event_type_code": self.event_type_code,
            "event_type_category": self.event_type_category,
            "region": self.region,
            "availability_zone": self.availability_zone,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "last_updated_time": (self.last_updated_time.isoformat() if self.last_updated_time else None),
            "status_code": self.status_code,
            "event_scope_code": self.event_scope_code,
            "description": self.description,
            "urgency": self.urgency,
            "days_until_start": self.days_until_start,
            "affected_entity_count": len(self.affected_entities),
        }


class HealthAnalyzer:
    """AWS Health 분석기

    AWS Health API를 호출하여 계정별 Health 이벤트를 조회합니다.

    Attributes:
        session: boto3 Session 객체
        client: health 클라이언트
        account_id: AWS 계정 ID
        account_name: 계정 이름

    Example:
        analyzer = HealthAnalyzer(session, "123456789012", "my-account")

        # 모든 이벤트 조회
        all_events = analyzer.get_events()

        # 예정된 변경만 조회
        scheduled = analyzer.get_events(
            event_type_categories=["scheduledChange"],
        )

        # 특정 서비스 이벤트 조회
        ec2_events = analyzer.get_events(
            services=["EC2"],
        )
    """

    def __init__(self, session, account_id: str = "", account_name: str = ""):
        """초기화

        Args:
            session: boto3.Session 객체
            account_id: AWS 계정 ID (멀티 계정 지원용)
            account_name: 계정 이름 (멀티 계정 지원용)
        """
        self.session = session
        self.client = session.client("health", region_name=HEALTH_REGION)
        self.account_id = account_id
        self.account_name = account_name

    def get_events(
        self,
        event_type_categories: list[str] | None = None,
        services: list[str] | None = None,
        regions: list[str] | None = None,
        event_status_codes: list[str] | None = None,
        start_time_from: datetime | None = None,
        start_time_to: datetime | None = None,
        include_details: bool = True,
        include_affected_entities: bool = True,
        page_size: int = 100,
    ) -> list[HealthEvent]:
        """Health 이벤트 조회

        Args:
            event_type_categories: 이벤트 카테고리 필터
            services: 서비스 필터 (EC2, RDS 등)
            regions: 리전 필터
            event_status_codes: 상태 필터 (open, upcoming, closed)
            start_time_from: 시작 시간 필터 (from)
            start_time_to: 시작 시간 필터 (to)
            include_details: 상세 설명 포함 여부
            include_affected_entities: 영향받는 리소스 포함 여부
            page_size: 페이지당 항목 수

        Returns:
            HealthEvent 객체 리스트
        """
        event_filter = EventFilter(
            event_type_categories=event_type_categories or [],
            services=services or [],
            regions=regions or [],
            event_status_codes=event_status_codes or [],
            start_time_from=start_time_from,
            start_time_to=start_time_to,
        )

        events = []
        event_arns = []

        # 이벤트 목록 조회
        for item in self._paginate_events(event_filter, page_size):
            event = HealthEvent.from_api_response(item)
            # 멀티 계정 지원: 계정 정보 설정
            event.account_id = self.account_id
            event.account_name = self.account_name
            events.append(event)
            event_arns.append(event.arn)

        # 상세 정보 조회
        if include_details and event_arns:
            details = self._get_event_details(event_arns)
            for event in events:
                if event.arn in details:
                    event.description = details[event.arn]

        # 영향받는 리소스 조회
        if include_affected_entities and event_arns:
            affected = self._get_affected_entities(event_arns)
            for event in events:
                if event.arn in affected:
                    event.affected_entities = affected[event.arn]

        logger.info(f"총 {len(events)}개의 Health 이벤트 조회됨")
        return events

    def _paginate_events(
        self,
        event_filter: EventFilter,
        page_size: int,
    ) -> Iterator[dict[str, Any]]:
        """describe_events API의 페이지네이션을 처리하여 이벤트를 순회한다.

        Args:
            event_filter: 이벤트 필터.
            page_size: 페이지당 항목 수.

        Yields:
            개별 이벤트 딕셔너리.
        """
        try:
            paginator = self.client.get_paginator("describe_events")

            api_filter = event_filter.to_api_filter()

            paginate_params = {
                "PaginationConfig": {"PageSize": page_size},
            }

            if api_filter:
                paginate_params["filter"] = api_filter

            page_iterator = paginator.paginate(**paginate_params)

            for page in page_iterator:
                items = page.get("events", [])
                logger.debug(f"페이지에서 {len(items)}개 이벤트 조회")
                yield from items

        except self.client.exceptions.InvalidPaginationToken:
            logger.warning("페이지네이션 토큰 만료, 재시도")
            yield from self._paginate_events(event_filter, page_size)
        except Exception as e:
            logger.error(f"이벤트 조회 실패: {e}")
            raise

    def _get_event_details(self, event_arns: list[str]) -> dict[str, str]:
        """이벤트 ARN 목록에 대한 상세 설명을 조회한다.

        API는 한 번에 최대 10개까지 조회 가능하므로 배치 처리한다.

        Args:
            event_arns: 조회할 이벤트 ARN 목록.

        Returns:
            이벤트 ARN을 키로, 상세 설명을 값으로 하는 딕셔너리.
        """
        details = {}

        # API는 한 번에 최대 10개까지 조회 가능
        for i in range(0, len(event_arns), 10):
            batch = event_arns[i : i + 10]
            try:
                response = self.client.describe_event_details(eventArns=batch)
                for item in response.get("successfulSet", []):
                    arn = item.get("event", {}).get("arn", "")
                    desc = item.get("eventDescription", {}).get("latestDescription", "")
                    if arn and desc:
                        details[arn] = desc
            except Exception as e:
                logger.warning(f"이벤트 상세 조회 실패: {e}")

        return details

    def _get_affected_entities(self, event_arns: list[str]) -> dict[str, list[AffectedEntity]]:
        """이벤트별로 영향받는 리소스를 조회한다.

        Args:
            event_arns: 조회할 이벤트 ARN 목록.

        Returns:
            이벤트 ARN을 키로, AffectedEntity 목록을 값으로 하는 딕셔너리.
        """
        affected = {}

        for arn in event_arns:
            try:
                paginator = self.client.get_paginator("describe_affected_entities")
                page_iterator = paginator.paginate(
                    filter={"eventArns": [arn]},
                )

                entities = []
                for page in page_iterator:
                    for item in page.get("entities", []):
                        entity = AffectedEntity.from_api_response(item)
                        entities.append(entity)

                if entities:
                    affected[arn] = entities

            except Exception as e:
                logger.warning(f"영향받는 리소스 조회 실패 ({arn}): {e}")

        return affected

    def get_scheduled_changes(
        self,
        services: list[str] | None = None,
        regions: list[str] | None = None,
        days_ahead: int = 90,
    ) -> list[HealthEvent]:
        """예정된 변경(패치/유지보수) 조회

        Args:
            services: 서비스 필터
            regions: 리전 필터
            days_ahead: 조회할 미래 일수

        Returns:
            예정된 변경 이벤트 리스트
        """
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=days_ahead)

        return self.get_events(
            event_type_categories=["scheduledChange"],
            services=services,
            regions=regions,
            event_status_codes=["upcoming", "open"],
            start_time_to=future,
        )

    def get_issues(
        self,
        services: list[str] | None = None,
        regions: list[str] | None = None,
        include_closed: bool = False,
    ) -> list[HealthEvent]:
        """서비스 장애 조회

        Args:
            services: 서비스 필터
            regions: 리전 필터
            include_closed: 완료된 장애 포함 여부

        Returns:
            서비스 장애 이벤트 리스트
        """
        status_codes = ["open"]
        if include_closed:
            status_codes.append("closed")

        return self.get_events(
            event_type_categories=["issue"],
            services=services,
            regions=regions,
            event_status_codes=status_codes,
        )

    def get_account_notifications(
        self,
        services: list[str] | None = None,
    ) -> list[HealthEvent]:
        """계정 알림 조회

        Args:
            services: 서비스 필터

        Returns:
            계정 알림 이벤트 리스트
        """
        return self.get_events(
            event_type_categories=["accountNotification"],
            services=services,
            event_status_codes=["open", "upcoming"],
        )

    def get_summary(
        self,
        events: list[HealthEvent] | None = None,
        group_by: str = "service",
    ) -> dict[str, dict[str, Any]]:
        """이벤트 요약 통계

        Args:
            events: 이벤트 리스트 (없으면 새로 조회)
            group_by: 그룹화 기준 (service, event_type_category, region, urgency)

        Returns:
            그룹별 요약
        """
        if events is None:
            events = self.get_events()

        summary = {}

        for event in events:
            if group_by == "service":
                key = event.service
            elif group_by == "event_type_category":
                key = event.event_type_category
            elif group_by == "region":
                key = event.region
            elif group_by == "urgency":
                key = event.urgency
            else:
                key = "all"

            if key not in summary:
                summary[key] = {
                    "count": 0,
                    "open": 0,
                    "upcoming": 0,
                    "closed": 0,
                    "affected_entities": 0,
                }

            summary[key]["count"] += 1
            summary[key][event.status_code] = summary[key].get(event.status_code, 0) + 1
            summary[key]["affected_entities"] += len(event.affected_entities)

        return summary
