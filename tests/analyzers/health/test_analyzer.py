"""
tests/plugins/health/test_analyzer.py - HealthAnalyzer 테스트

AWS Health API 분석기 테스트
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from analyzers.health.common.analyzer import (
    AffectedEntity,
    EventFilter,
    HealthAnalyzer,
    HealthEvent,
)


class TestEventFilter:
    """EventFilter 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        f = EventFilter()
        assert f.event_type_categories == []
        assert f.services == []
        assert f.regions == []
        assert f.start_time_from is None
        assert f.start_time_to is None
        assert f.end_time_from is None
        assert f.end_time_to is None

    def test_to_api_filter_empty(self):
        """빈 필터"""
        f = EventFilter()
        api_filter = f.to_api_filter()
        assert api_filter == {}

    def test_to_api_filter_services(self):
        """서비스 필터"""
        f = EventFilter(services=["EC2", "RDS"])
        api_filter = f.to_api_filter()
        assert api_filter["services"] == ["EC2", "RDS"]

    def test_to_api_filter_start_times(self):
        """startTimes 필터"""
        now = datetime.now(timezone.utc)
        f = EventFilter(
            start_time_from=now - timedelta(days=7),
            start_time_to=now,
        )
        api_filter = f.to_api_filter()
        assert "startTimes" in api_filter
        assert len(api_filter["startTimes"]) == 1
        assert "from" in api_filter["startTimes"][0]
        assert "to" in api_filter["startTimes"][0]

    def test_to_api_filter_end_times(self):
        """endTimes 필터"""
        now = datetime.now(timezone.utc)
        f = EventFilter(
            end_time_from=now - timedelta(days=7),
            end_time_to=now,
        )
        api_filter = f.to_api_filter()
        assert "endTimes" in api_filter
        assert len(api_filter["endTimes"]) == 1
        assert "from" in api_filter["endTimes"][0]
        assert "to" in api_filter["endTimes"][0]

    def test_to_api_filter_combined(self):
        """복합 필터"""
        now = datetime.now(timezone.utc)
        f = EventFilter(
            services=["EC2"],
            regions=["ap-northeast-2"],
            event_type_categories=["scheduledChange"],
            start_time_from=now - timedelta(days=7),
            start_time_to=now,
        )
        api_filter = f.to_api_filter()
        assert api_filter["services"] == ["EC2"]
        assert api_filter["regions"] == ["ap-northeast-2"]
        assert api_filter["eventTypeCategories"] == ["scheduledChange"]
        assert "startTimes" in api_filter


class TestHealthEvent:
    """HealthEvent 테스트"""

    def test_from_api_response(self):
        """API 응답에서 이벤트 생성"""
        api_item = {
            "arn": "arn:aws:health:us-east-1::event/EC2/123",
            "service": "EC2",
            "eventTypeCode": "AWS_EC2_SYSTEM_MAINTENANCE_EVENT",
            "eventTypeCategory": "scheduledChange",
            "region": "ap-northeast-2",
            "availabilityZone": "ap-northeast-2a",
            "startTime": datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            "endTime": datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
            "lastUpdatedTime": datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }

        event = HealthEvent.from_api_response(api_item)
        assert event.arn == "arn:aws:health:us-east-1::event/EC2/123"
        assert event.service == "EC2"
        assert event.event_type_category == "scheduledChange"
        assert event.status_code == "upcoming"
        assert event.is_scheduled_change is True
        assert event.is_upcoming is True

    def test_urgency_critical(self):
        """긴급도 - critical (3일 이내)"""
        event = HealthEvent(
            arn="test",
            service="EC2",
            event_type_code="TEST",
            event_type_category="scheduledChange",
            region="ap-northeast-2",
            availability_zone="",
            start_time=datetime.now(timezone.utc) + timedelta(days=2),
            end_time=None,
            last_updated_time=None,
            status_code="upcoming",
            event_scope_code="ACCOUNT_SPECIFIC",
            description="",
        )
        assert event.urgency == "critical"

    def test_urgency_high(self):
        """긴급도 - high (7일 이내)"""
        event = HealthEvent(
            arn="test",
            service="EC2",
            event_type_code="TEST",
            event_type_category="scheduledChange",
            region="ap-northeast-2",
            availability_zone="",
            start_time=datetime.now(timezone.utc) + timedelta(days=5),
            end_time=None,
            last_updated_time=None,
            status_code="upcoming",
            event_scope_code="ACCOUNT_SPECIFIC",
            description="",
        )
        assert event.urgency == "high"


class TestAffectedEntity:
    """AffectedEntity 테스트"""

    def test_from_api_response(self):
        """API 응답에서 엔티티 생성"""
        api_item = {
            "entityValue": "i-1234567890abcdef0",
            "awsAccountId": "123456789012",
            "entityUrl": "https://console.aws.amazon.com/...",
            "statusCode": "PENDING",
            "lastUpdatedTime": datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
            "tags": {"Name": "web-server"},
        }

        entity = AffectedEntity.from_api_response(api_item)
        assert entity.entity_value == "i-1234567890abcdef0"
        assert entity.aws_account_id == "123456789012"
        assert entity.status_code == "PENDING"
        assert entity.tags == {"Name": "web-server"}


class TestHealthAnalyzer:
    """HealthAnalyzer 테스트"""

    @pytest.fixture
    def mock_session(self):
        """Mock boto3 session"""
        session = MagicMock()
        return session

    @pytest.fixture
    def analyzer(self, mock_session):
        """HealthAnalyzer 인스턴스"""
        mock_client = MagicMock()
        mock_session.client.return_value = mock_client
        return HealthAnalyzer(mock_session)

    def test_get_events_basic(self, analyzer):
        """기본 이벤트 조회"""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "events": [
                    {
                        "arn": "arn:aws:health:us-east-1::event/EC2/1",
                        "service": "EC2",
                        "eventTypeCode": "TEST",
                        "eventTypeCategory": "scheduledChange",
                        "region": "ap-northeast-2",
                        "availabilityZone": "",
                        "statusCode": "upcoming",
                        "eventScopeCode": "ACCOUNT_SPECIFIC",
                    }
                ]
            }
        ]
        analyzer.client.get_paginator.return_value = mock_paginator
        analyzer.client.describe_event_details.return_value = {"successfulSet": []}

        events = analyzer.get_events(
            include_details=False,
            include_affected_entities=False,
        )

        assert len(events) == 1
        assert events[0].service == "EC2"

    def test_get_events_with_time_filter(self, analyzer):
        """시간 필터 적용 테스트"""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"events": []}]
        analyzer.client.get_paginator.return_value = mock_paginator

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)
        end = now

        analyzer.get_events(
            start_time_from=start,
            start_time_to=end,
            include_details=False,
            include_affected_entities=False,
        )

        # paginate 호출 시 필터 확인
        call_args = mock_paginator.paginate.call_args
        api_filter = call_args.kwargs.get("filter", {})

        # 시간 범위 필터 확인
        assert "startTimes" in api_filter
        start_times = api_filter["startTimes"][0]
        assert start_times["from"] == start
        assert start_times["to"] == end

    def test_get_events_with_service_filter(self, analyzer):
        """서비스 필터 적용 테스트"""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"events": []}]
        analyzer.client.get_paginator.return_value = mock_paginator

        analyzer.get_events(
            services=["EC2", "RDS"],
            include_details=False,
            include_affected_entities=False,
        )

        # paginate 호출 시 필터 확인
        call_args = mock_paginator.paginate.call_args
        api_filter = call_args.kwargs.get("filter", {})

        assert api_filter["services"] == ["EC2", "RDS"]


class TestHealthAnalyzerScheduledChanges:
    """예정된 변경 조회 테스트"""

    @pytest.fixture
    def analyzer(self):
        """HealthAnalyzer 인스턴스"""
        session = MagicMock()
        mock_client = MagicMock()
        session.client.return_value = mock_client
        return HealthAnalyzer(session)

    def test_get_scheduled_changes(self, analyzer):
        """예정된 변경 조회"""
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [
            {
                "events": [
                    {
                        "arn": "arn:aws:health:us-east-1::event/EC2/maintenance",
                        "service": "EC2",
                        "eventTypeCode": "AWS_EC2_SYSTEM_MAINTENANCE_EVENT",
                        "eventTypeCategory": "scheduledChange",
                        "region": "ap-northeast-2",
                        "availabilityZone": "",
                        "statusCode": "upcoming",
                        "eventScopeCode": "ACCOUNT_SPECIFIC",
                    }
                ]
            }
        ]
        analyzer.client.get_paginator.return_value = mock_paginator
        analyzer.client.describe_event_details.return_value = {"successfulSet": []}

        events = analyzer.get_scheduled_changes(services=["EC2"])

        assert len(events) == 1
        assert events[0].event_type_category == "scheduledChange"


class TestHealthAnalyzerSummary:
    """이벤트 요약 테스트"""

    def test_get_summary_by_service(self):
        """서비스별 요약"""
        session = MagicMock()
        mock_client = MagicMock()
        session.client.return_value = mock_client
        analyzer = HealthAnalyzer(session)

        events = [
            HealthEvent(
                arn="test1",
                service="EC2",
                event_type_code="TEST",
                event_type_category="scheduledChange",
                region="ap-northeast-2",
                availability_zone="",
                start_time=None,
                end_time=None,
                last_updated_time=None,
                status_code="open",
                event_scope_code="ACCOUNT_SPECIFIC",
                description="",
            ),
            HealthEvent(
                arn="test2",
                service="EC2",
                event_type_code="TEST",
                event_type_category="scheduledChange",
                region="ap-northeast-2",
                availability_zone="",
                start_time=None,
                end_time=None,
                last_updated_time=None,
                status_code="upcoming",
                event_scope_code="ACCOUNT_SPECIFIC",
                description="",
            ),
            HealthEvent(
                arn="test3",
                service="RDS",
                event_type_code="TEST",
                event_type_category="issue",
                region="ap-northeast-2",
                availability_zone="",
                start_time=None,
                end_time=None,
                last_updated_time=None,
                status_code="open",
                event_scope_code="ACCOUNT_SPECIFIC",
                description="",
            ),
        ]

        summary = analyzer.get_summary(events, group_by="service")

        assert "EC2" in summary
        assert "RDS" in summary
        assert summary["EC2"]["count"] == 2
        assert summary["EC2"]["open"] == 1
        assert summary["EC2"]["upcoming"] == 1
        assert summary["RDS"]["count"] == 1
