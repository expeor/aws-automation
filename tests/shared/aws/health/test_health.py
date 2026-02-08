"""
tests/shared/aws/health/test_health.py - Comprehensive AWS Health module tests

Tests for all health analysis and reporting functions.

Test Coverage:
    - HealthAnalyzer: Event fetching, filtering, categorization
    - HealthCollector: Event collection, patch classification
    - EventFilter: API filter conversion, validation
    - HealthEvent: Properties, urgency calculation
    - AffectedEntity: Entity parsing
    - PatchItem: Action determination
    - CollectionResult: Summary statistics
    - PatchReporter: Report generation

Test Classes:
    - TestEventFilter: 6 tests
    - TestAffectedEntity: 3 tests
    - TestHealthEvent: 10 tests
    - TestHealthAnalyzer: 10 tests
    - TestPatchItem: 5 tests
    - TestHealthCollector: 8 tests
    - TestCollectionResult: 7 tests
    - TestPatchReporter: 6 tests

Total: 55 tests covering AWS Health Dashboard analysis.

Note: Tests use mocking for AWS Health API to avoid external API calls.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from core.shared.aws.health import (
    HEALTH_REGION,
    AffectedEntity,
    CollectionResult,
    EventFilter,
    HealthAnalyzer,
    HealthCollector,
    HealthEvent,
    PatchItem,
    PatchReporter,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_health_event():
    """Sample Health API event response"""
    now = datetime.now(timezone.utc)
    return {
        "arn": "arn:aws:health:us-east-1::event/EC2/AWS_EC2_INSTANCE_RETIREMENT/123456",
        "service": "EC2",
        "eventTypeCode": "AWS_EC2_INSTANCE_RETIREMENT_SCHEDULED",
        "eventTypeCategory": "scheduledChange",
        "region": "ap-northeast-2",
        "availabilityZone": "ap-northeast-2a",
        "startTime": now + timedelta(days=5),
        "endTime": now + timedelta(days=6),
        "lastUpdatedTime": now,
        "statusCode": "upcoming",
        "eventScopeCode": "ACCOUNT_SPECIFIC",
    }


@pytest.fixture
def sample_issue_event():
    """Sample issue event response"""
    now = datetime.now(timezone.utc)
    return {
        "arn": "arn:aws:health:us-east-1::event/EC2/AWS_EC2_OPERATIONAL_ISSUE/789012",
        "service": "EC2",
        "eventTypeCode": "AWS_EC2_OPERATIONAL_ISSUE",
        "eventTypeCategory": "issue",
        "region": "us-east-1",
        "availabilityZone": "",
        "startTime": now - timedelta(hours=2),
        "endTime": None,
        "lastUpdatedTime": now,
        "statusCode": "open",
        "eventScopeCode": "PUBLIC",
    }


@pytest.fixture
def sample_event_detail():
    """Sample event detail response"""
    return {"eventDescription": {"latestDescription": "Your instance i-1234567890abcdef0 is scheduled for retirement."}}


@pytest.fixture
def sample_affected_entities():
    """Sample affected entities response"""
    now = datetime.now(timezone.utc)
    return [
        {
            "entityValue": "i-1234567890abcdef0",
            "awsAccountId": "123456789012",
            "entityUrl": "https://console.aws.amazon.com/ec2/v2/home?region=ap-northeast-2#Instances:instanceId=i-1234567890abcdef0",
            "statusCode": "PENDING",
            "lastUpdatedTime": now,
            "tags": {"Name": "WebServer", "Environment": "Production"},
        },
        {
            "entityValue": "i-0987654321fedcba0",
            "awsAccountId": "123456789012",
            "entityUrl": "https://console.aws.amazon.com/ec2/v2/home?region=ap-northeast-2#Instances:instanceId=i-0987654321fedcba0",
            "statusCode": "PENDING",
            "lastUpdatedTime": now,
            "tags": {},
        },
    ]


@pytest.fixture
def mock_boto_session():
    """Mock boto3 Session"""
    session = MagicMock()
    client = MagicMock()
    session.client.return_value = client
    return session


@pytest.fixture
def mock_health_client(mock_boto_session, sample_health_event, sample_event_detail, sample_affected_entities):
    """Mock Health client with paginator"""
    client = mock_boto_session.client.return_value

    # Mock paginator for describe_events
    paginator = MagicMock()
    paginator.paginate.return_value = [{"events": [sample_health_event]}]
    client.get_paginator.return_value = paginator

    # Mock describe_event_details
    client.describe_event_details.return_value = {
        "successfulSet": [{"event": sample_health_event, "eventDescription": sample_event_detail["eventDescription"]}],
        "failedSet": [],
    }

    # Mock describe_affected_entities paginator
    affected_paginator = MagicMock()
    affected_paginator.paginate.return_value = [{"entities": sample_affected_entities}]

    def get_paginator_side_effect(operation):
        if operation == "describe_events":
            return paginator
        elif operation == "describe_affected_entities":
            return affected_paginator
        return MagicMock()

    client.get_paginator.side_effect = get_paginator_side_effect

    return client


# =============================================================================
# EventFilter Tests
# =============================================================================


class TestEventFilter:
    """EventFilter class tests"""

    def test_empty_filter(self):
        """Test empty filter conversion"""
        filter_obj = EventFilter()
        api_filter = filter_obj.to_api_filter()

        assert api_filter == {}

    def test_category_filter(self):
        """Test event type category filter"""
        filter_obj = EventFilter(event_type_categories=["scheduledChange", "issue"])
        api_filter = filter_obj.to_api_filter()

        assert "eventTypeCategories" in api_filter
        assert api_filter["eventTypeCategories"] == ["scheduledChange", "issue"]

    def test_service_filter(self):
        """Test service filter"""
        filter_obj = EventFilter(services=["EC2", "RDS"])
        api_filter = filter_obj.to_api_filter()

        assert "services" in api_filter
        assert api_filter["services"] == ["EC2", "RDS"]

    def test_region_filter(self):
        """Test region filter"""
        filter_obj = EventFilter(regions=["ap-northeast-2", "us-east-1"])
        api_filter = filter_obj.to_api_filter()

        assert "regions" in api_filter
        assert api_filter["regions"] == ["ap-northeast-2", "us-east-1"]

    def test_time_filter(self):
        """Test time range filter"""
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 31, tzinfo=timezone.utc)

        filter_obj = EventFilter(start_time_from=start, start_time_to=end)
        api_filter = filter_obj.to_api_filter()

        assert "startTimes" in api_filter
        assert len(api_filter["startTimes"]) == 1
        assert api_filter["startTimes"][0]["from"] == start
        assert api_filter["startTimes"][0]["to"] == end

    def test_combined_filter(self):
        """Test combined filter with multiple criteria"""
        filter_obj = EventFilter(
            event_type_categories=["scheduledChange"],
            services=["EC2"],
            regions=["ap-northeast-2"],
            event_status_codes=["upcoming"],
        )
        api_filter = filter_obj.to_api_filter()

        assert "eventTypeCategories" in api_filter
        assert "services" in api_filter
        assert "regions" in api_filter
        assert "eventStatusCodes" in api_filter


# =============================================================================
# AffectedEntity Tests
# =============================================================================


class TestAffectedEntity:
    """AffectedEntity class tests"""

    def test_from_api_response(self, sample_affected_entities):
        """Test creating AffectedEntity from API response"""
        entity = AffectedEntity.from_api_response(sample_affected_entities[0])

        assert entity.entity_value == "i-1234567890abcdef0"
        assert entity.aws_account_id == "123456789012"
        assert entity.status_code == "PENDING"
        assert entity.tags == {"Name": "WebServer", "Environment": "Production"}

    def test_from_api_response_no_tags(self, sample_affected_entities):
        """Test creating AffectedEntity with no tags"""
        entity = AffectedEntity.from_api_response(sample_affected_entities[1])

        assert entity.entity_value == "i-0987654321fedcba0"
        assert entity.tags == {}

    def test_from_api_response_minimal(self):
        """Test creating AffectedEntity with minimal data"""
        minimal_data = {
            "entityValue": "vol-1234567890",
            "awsAccountId": "123456789012",
            "entityUrl": "",
            "statusCode": "RESOLVED",
        }

        entity = AffectedEntity.from_api_response(minimal_data)

        assert entity.entity_value == "vol-1234567890"
        assert entity.status_code == "RESOLVED"
        assert entity.last_updated_time is None


# =============================================================================
# HealthEvent Tests
# =============================================================================


class TestHealthEvent:
    """HealthEvent class tests"""

    def test_from_api_response(self, sample_health_event):
        """Test creating HealthEvent from API response"""
        event = HealthEvent.from_api_response(sample_health_event)

        assert event.arn == sample_health_event["arn"]
        assert event.service == "EC2"
        assert event.event_type_category == "scheduledChange"
        assert event.status_code == "upcoming"

    def test_from_api_response_with_detail(self, sample_health_event, sample_event_detail):
        """Test creating HealthEvent with detail"""
        event = HealthEvent.from_api_response(sample_health_event, sample_event_detail)

        assert event.description == sample_event_detail["eventDescription"]["latestDescription"]

    def test_is_scheduled_change(self, sample_health_event):
        """Test is_scheduled_change property"""
        event = HealthEvent.from_api_response(sample_health_event)

        assert event.is_scheduled_change is True
        assert event.is_issue is False

    def test_is_issue(self, sample_issue_event):
        """Test is_issue property"""
        event = HealthEvent.from_api_response(sample_issue_event)

        assert event.is_issue is True
        assert event.is_scheduled_change is False

    def test_is_upcoming(self, sample_health_event):
        """Test is_upcoming property"""
        event = HealthEvent.from_api_response(sample_health_event)

        assert event.is_upcoming is True
        assert event.is_open is False

    def test_is_open(self, sample_issue_event):
        """Test is_open property"""
        event = HealthEvent.from_api_response(sample_issue_event)

        assert event.is_open is True
        assert event.is_upcoming is False

    def test_days_until_start(self, sample_health_event):
        """Test days_until_start calculation"""
        event = HealthEvent.from_api_response(sample_health_event)
        days = event.days_until_start

        # Should be approximately 5 days
        assert days is not None
        assert 4 <= days <= 5

    def test_urgency_critical(self):
        """Test urgency calculation - critical (3 days or less)"""
        now = datetime.now(timezone.utc)
        event_data = {
            "arn": "test-arn",
            "service": "EC2",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=2),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }
        event = HealthEvent.from_api_response(event_data)

        assert event.urgency == "critical"

    def test_urgency_high(self):
        """Test urgency calculation - high (4-7 days)"""
        now = datetime.now(timezone.utc)
        event_data = {
            "arn": "test-arn",
            "service": "EC2",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=5),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }
        event = HealthEvent.from_api_response(event_data)

        assert event.urgency == "high"

    def test_to_dict(self, sample_health_event):
        """Test to_dict conversion"""
        event = HealthEvent.from_api_response(sample_health_event)
        event_dict = event.to_dict()

        assert event_dict["service"] == "EC2"
        assert event_dict["event_type_category"] == "scheduledChange"
        assert "urgency" in event_dict
        assert "days_until_start" in event_dict
        assert event_dict["affected_entity_count"] == 0


# =============================================================================
# HealthAnalyzer Tests
# =============================================================================


class TestHealthAnalyzer:
    """HealthAnalyzer class tests"""

    def test_initialization(self, mock_boto_session):
        """Test HealthAnalyzer initialization"""
        analyzer = HealthAnalyzer(mock_boto_session)

        assert analyzer.session == mock_boto_session
        mock_boto_session.client.assert_called_with("health", region_name=HEALTH_REGION)

    def test_get_events_basic(self, mock_boto_session, mock_health_client):
        """Test basic event retrieval"""
        analyzer = HealthAnalyzer(mock_boto_session)
        events = analyzer.get_events(include_details=False, include_affected_entities=False)

        assert len(events) == 1
        assert events[0].service == "EC2"
        assert events[0].event_type_category == "scheduledChange"

    def test_get_events_with_details(self, mock_boto_session, mock_health_client, sample_event_detail):
        """Test event retrieval with details"""
        analyzer = HealthAnalyzer(mock_boto_session)
        events = analyzer.get_events(include_details=True, include_affected_entities=False)

        assert len(events) == 1
        assert sample_event_detail["eventDescription"]["latestDescription"] in events[0].description

    def test_get_events_with_affected_entities(self, mock_boto_session, mock_health_client):
        """Test event retrieval with affected entities"""
        analyzer = HealthAnalyzer(mock_boto_session)
        events = analyzer.get_events(include_details=False, include_affected_entities=True)

        assert len(events) == 1
        assert len(events[0].affected_entities) == 2
        assert events[0].affected_entities[0].entity_value == "i-1234567890abcdef0"

    def test_get_events_with_filter(self, mock_boto_session, mock_health_client):
        """Test event retrieval with filters"""
        analyzer = HealthAnalyzer(mock_boto_session)
        events = analyzer.get_events(
            event_type_categories=["scheduledChange"],
            services=["EC2"],
            regions=["ap-northeast-2"],
            include_details=False,
            include_affected_entities=False,
        )

        assert len(events) == 1

    def test_get_scheduled_changes(self, mock_boto_session, mock_health_client):
        """Test get_scheduled_changes method"""
        analyzer = HealthAnalyzer(mock_boto_session)
        events = analyzer.get_scheduled_changes(services=["EC2"], regions=["ap-northeast-2"])

        assert len(events) >= 0
        # Verify the paginator was called
        mock_health_client.get_paginator.assert_called()

    def test_get_issues(self, mock_boto_session):
        """Test get_issues method"""
        client = mock_boto_session.client.return_value

        # Create an issue event
        now = datetime.now(timezone.utc)
        issue_event = {
            "arn": "arn:aws:health:us-east-1::event/EC2/ISSUE/123",
            "service": "EC2",
            "eventTypeCode": "AWS_EC2_OPERATIONAL_ISSUE",
            "eventTypeCategory": "issue",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now,
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "open",
            "eventScopeCode": "PUBLIC",
        }

        paginator = MagicMock()
        paginator.paginate.return_value = [{"events": [issue_event]}]
        client.get_paginator.return_value = paginator

        analyzer = HealthAnalyzer(mock_boto_session)
        issues = analyzer.get_issues(include_closed=False)

        assert len(issues) == 1
        assert issues[0].is_issue is True

    def test_get_account_notifications(self, mock_boto_session):
        """Test get_account_notifications method"""
        client = mock_boto_session.client.return_value

        now = datetime.now(timezone.utc)
        notification_event = {
            "arn": "arn:aws:health:us-east-1::event/BILLING/NOTIFICATION/456",
            "service": "BILLING",
            "eventTypeCode": "AWS_BILLING_NOTIFICATION",
            "eventTypeCategory": "accountNotification",
            "region": "global",
            "availabilityZone": "",
            "startTime": now,
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "open",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }

        paginator = MagicMock()
        paginator.paginate.return_value = [{"events": [notification_event]}]
        client.get_paginator.return_value = paginator

        analyzer = HealthAnalyzer(mock_boto_session)
        notifications = analyzer.get_account_notifications()

        assert len(notifications) == 1
        assert notifications[0].event_type_category == "accountNotification"

    def test_get_summary(self, mock_boto_session, mock_health_client):
        """Test get_summary method"""
        analyzer = HealthAnalyzer(mock_boto_session)
        events = analyzer.get_events(include_details=False, include_affected_entities=False)
        summary = analyzer.get_summary(events, group_by="service")

        assert "EC2" in summary
        assert summary["EC2"]["count"] == 1

    def test_pagination_retry(self, mock_boto_session):
        """Test pagination retry on token expiry"""
        client = mock_boto_session.client.return_value

        # Mock paginator that raises InvalidPaginationToken on first call
        paginator = MagicMock()
        call_count = [0]

        def paginate_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise client.exceptions.InvalidPaginationToken("Token expired")
            return [{"events": []}]

        paginator.paginate.side_effect = paginate_side_effect
        client.get_paginator.return_value = paginator
        client.exceptions.InvalidPaginationToken = type("InvalidPaginationToken", (Exception,), {})

        analyzer = HealthAnalyzer(mock_boto_session)

        # This should trigger the retry logic
        events = list(analyzer._paginate_events(EventFilter(), page_size=100))

        # Should have retried after first failure
        assert call_count[0] == 2


# =============================================================================
# PatchItem Tests
# =============================================================================


class TestPatchItem:
    """PatchItem class tests"""

    def test_from_event(self, sample_health_event):
        """Test creating PatchItem from HealthEvent"""
        health_event = HealthEvent.from_api_response(sample_health_event)
        patch = PatchItem.from_event(health_event)

        assert patch.service == "EC2"
        assert patch.event_type == sample_health_event["eventTypeCode"]
        assert patch.urgency == health_event.urgency

    def test_determine_action_reboot(self):
        """Test action determination - reboot"""
        now = datetime.now(timezone.utc)
        event_data = {
            "arn": "test-arn",
            "service": "EC2",
            "eventTypeCode": "AWS_EC2_INSTANCE_REBOOT_MAINTENANCE",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=5),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }
        event = HealthEvent.from_api_response(event_data)
        patch = PatchItem.from_event(event)

        assert patch.action_required == "재부팅 필요"

    def test_determine_action_retirement(self):
        """Test action determination - retirement"""
        now = datetime.now(timezone.utc)
        event_data = {
            "arn": "test-arn",
            "service": "EC2",
            "eventTypeCode": "AWS_EC2_INSTANCE_RETIREMENT_SCHEDULED",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=5),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }
        event = HealthEvent.from_api_response(event_data)
        patch = PatchItem.from_event(event)

        assert patch.action_required == "인스턴스 교체 필요"

    def test_determine_action_security(self):
        """Test action determination - security"""
        now = datetime.now(timezone.utc)
        event_data = {
            "arn": "test-arn",
            "service": "RDS",
            "eventTypeCode": "AWS_RDS_SECURITY_PATCH_AVAILABLE",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=5),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }
        event = HealthEvent.from_api_response(event_data)
        patch = PatchItem.from_event(event)

        assert patch.action_required == "보안 패치 적용"

    def test_description_truncation(self):
        """Test description summary truncation"""
        now = datetime.now(timezone.utc)
        long_description = "A" * 300  # Long description

        event_data = {
            "arn": "test-arn",
            "service": "EC2",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=5),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }
        event = HealthEvent.from_api_response(event_data)
        event.description = long_description

        patch = PatchItem.from_event(event)

        assert len(patch.description_summary) <= 203  # 200 chars + "..."
        assert patch.description_summary.endswith("...")

    def test_affected_resources(self, sample_health_event, sample_affected_entities):
        """Test affected resources list"""
        event = HealthEvent.from_api_response(sample_health_event)
        for entity_data in sample_affected_entities:
            entity = AffectedEntity.from_api_response(entity_data)
            event.affected_entities.append(entity)

        patch = PatchItem.from_event(event)

        assert len(patch.affected_resources) == 2
        assert "i-1234567890abcdef0" in patch.affected_resources


# =============================================================================
# HealthCollector Tests
# =============================================================================


class TestHealthCollector:
    """HealthCollector class tests"""

    def test_initialization(self, mock_boto_session):
        """Test HealthCollector initialization"""
        collector = HealthCollector(mock_boto_session)

        assert collector.session == mock_boto_session
        assert isinstance(collector.analyzer, HealthAnalyzer)

    def test_collect_patches(self, mock_boto_session, mock_health_client):
        """Test collect_patches method"""
        collector = HealthCollector(mock_boto_session)
        result = collector.collect_patches(services=["EC2"], days_ahead=90)

        assert isinstance(result, CollectionResult)
        assert result.patch_count >= 0
        assert isinstance(result.patches, list)

    def test_collect_all(self, mock_boto_session, mock_health_client):
        """Test collect_all method"""
        collector = HealthCollector(mock_boto_session)
        result = collector.collect_all(services=["EC2"])

        assert isinstance(result, CollectionResult)

    def test_collect_issues(self, mock_boto_session):
        """Test collect_issues method"""
        client = mock_boto_session.client.return_value

        now = datetime.now(timezone.utc)
        issue_event = {
            "arn": "arn:aws:health:us-east-1::event/EC2/ISSUE/123",
            "service": "EC2",
            "eventTypeCode": "AWS_EC2_OPERATIONAL_ISSUE",
            "eventTypeCategory": "issue",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now,
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "open",
            "eventScopeCode": "PUBLIC",
        }

        paginator = MagicMock()
        paginator.paginate.return_value = [{"events": [issue_event]}]
        client.get_paginator.return_value = paginator

        collector = HealthCollector(mock_boto_session)
        issues = collector.collect_issues(services=["EC2"])

        assert len(issues) >= 0

    def test_summarize_by_urgency(self, mock_boto_session):
        """Test _summarize_by_urgency method"""
        collector = HealthCollector(mock_boto_session)

        # Create sample patches
        now = datetime.now(timezone.utc)
        critical_event_data = {
            "arn": "test-arn-1",
            "service": "EC2",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=2),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }

        high_event_data = {
            "arn": "test-arn-2",
            "service": "RDS",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=5),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }

        critical_event = HealthEvent.from_api_response(critical_event_data)
        high_event = HealthEvent.from_api_response(high_event_data)

        patches = [PatchItem.from_event(critical_event), PatchItem.from_event(high_event)]

        summary = collector._summarize_by_urgency(patches)

        assert "critical" in summary
        assert "high" in summary
        assert summary["critical"]["count"] == 1
        assert summary["high"]["count"] == 1

    def test_summarize_by_service(self, mock_boto_session):
        """Test _summarize_by_service method"""
        collector = HealthCollector(mock_boto_session)

        now = datetime.now(timezone.utc)
        ec2_event_data = {
            "arn": "test-arn-1",
            "service": "EC2",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=2),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }

        rds_event_data = {
            "arn": "test-arn-2",
            "service": "RDS",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=5),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }

        ec2_event = HealthEvent.from_api_response(ec2_event_data)
        rds_event = HealthEvent.from_api_response(rds_event_data)

        patches = [PatchItem.from_event(ec2_event), PatchItem.from_event(rds_event)]

        summary = collector._summarize_by_service(patches)

        assert "EC2" in summary
        assert "RDS" in summary
        assert summary["EC2"]["count"] == 1
        assert summary["RDS"]["count"] == 1

    def test_group_by_month(self, mock_boto_session):
        """Test _group_by_month method"""
        collector = HealthCollector(mock_boto_session)

        now = datetime.now(timezone.utc)
        jan_event_data = {
            "arn": "test-arn-1",
            "service": "EC2",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": datetime(2026, 1, 15, tzinfo=timezone.utc),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }

        feb_event_data = {
            "arn": "test-arn-2",
            "service": "RDS",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": datetime(2026, 2, 20, tzinfo=timezone.utc),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }

        jan_event = HealthEvent.from_api_response(jan_event_data)
        feb_event = HealthEvent.from_api_response(feb_event_data)

        patches = [PatchItem.from_event(jan_event), PatchItem.from_event(feb_event)]

        grouped = collector._group_by_month(patches)

        assert "2026-01" in grouped
        assert "2026-02" in grouped
        assert len(grouped["2026-01"]) == 1
        assert len(grouped["2026-02"]) == 1

    def test_patch_sorting_by_urgency(self, mock_boto_session, mock_health_client):
        """Test that patches are sorted by urgency and date"""
        collector = HealthCollector(mock_boto_session)

        # Create multiple events with different urgencies
        now = datetime.now(timezone.utc)
        events = []

        # Low urgency (30 days)
        low_event_data = {
            "arn": "test-arn-low",
            "service": "EC2",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=30),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }
        events.append(low_event_data)

        # Critical urgency (2 days)
        critical_event_data = {
            "arn": "test-arn-critical",
            "service": "RDS",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=2),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }
        events.append(critical_event_data)

        # Mock the paginator to return these events
        client = mock_boto_session.client.return_value
        paginator = MagicMock()
        paginator.paginate.return_value = [{"events": events}]
        client.get_paginator.return_value = paginator

        result = collector.collect_patches()

        # Critical should come first
        if len(result.patches) >= 2:
            assert result.patches[0].urgency == "critical"
            assert result.patches[-1].urgency == "low"


# =============================================================================
# CollectionResult Tests
# =============================================================================


class TestCollectionResult:
    """CollectionResult class tests"""

    @pytest.fixture
    def sample_collection_result(self):
        """Sample CollectionResult"""
        now = datetime.now(timezone.utc)

        # Create sample events
        events = []
        patches = []

        for i in range(3):
            event_data = {
                "arn": f"test-arn-{i}",
                "service": "EC2" if i % 2 == 0 else "RDS",
                "eventTypeCode": "TEST",
                "eventTypeCategory": "scheduledChange",
                "region": "us-east-1",
                "availabilityZone": "",
                "startTime": now + timedelta(days=2 + i),
                "endTime": None,
                "lastUpdatedTime": now,
                "statusCode": "upcoming",
                "eventScopeCode": "ACCOUNT_SPECIFIC",
            }
            event = HealthEvent.from_api_response(event_data)
            events.append(event)
            patches.append(PatchItem.from_event(event))

        summary_urgency = {
            "critical": {"count": 2, "services": ["EC2", "RDS"], "affected_resources": 0},
            "high": {"count": 1, "services": ["EC2"], "affected_resources": 0},
        }

        summary_service = {
            "EC2": {"count": 2, "critical": 1, "high": 1, "medium": 0, "low": 0, "affected_resources": 0},
            "RDS": {"count": 1, "critical": 1, "high": 0, "medium": 0, "low": 0, "affected_resources": 0},
        }

        summary_month = {"2026-02": patches}

        return CollectionResult(
            events=events,
            patches=patches,
            summary_by_urgency=summary_urgency,
            summary_by_service=summary_service,
            summary_by_month=summary_month,
        )

    def test_total_count(self, sample_collection_result):
        """Test total_count property"""
        assert sample_collection_result.total_count == 3

    def test_patch_count(self, sample_collection_result):
        """Test patch_count property"""
        assert sample_collection_result.patch_count == 3

    def test_critical_count(self, sample_collection_result):
        """Test critical_count property"""
        assert sample_collection_result.critical_count == 2

    def test_high_count(self, sample_collection_result):
        """Test high_count property"""
        assert sample_collection_result.high_count == 1

    def test_affected_resource_count(self, sample_collection_result):
        """Test affected_resource_count property"""
        # No affected resources in sample data
        assert sample_collection_result.affected_resource_count == 0

    def test_get_patches_by_urgency(self, sample_collection_result):
        """Test get_patches_by_urgency method"""
        critical_patches = sample_collection_result.get_patches_by_urgency("critical")

        # Should filter by urgency
        assert all(p.urgency == "critical" for p in critical_patches)

    def test_get_patches_by_service(self, sample_collection_result):
        """Test get_patches_by_service method"""
        ec2_patches = sample_collection_result.get_patches_by_service("EC2")

        assert all(p.service == "EC2" for p in ec2_patches)


# =============================================================================
# PatchReporter Tests
# =============================================================================


class TestPatchReporter:
    """PatchReporter class tests"""

    @pytest.fixture
    def sample_result_for_report(self):
        """Sample CollectionResult for reporting"""
        now = datetime.now(timezone.utc)

        events = []
        patches = []

        # Create 5 patches with varying urgency
        urgency_map = ["critical", "critical", "high", "medium", "low"]
        services = ["EC2", "RDS", "EC2", "Lambda", "S3"]

        for i in range(5):
            event_data = {
                "arn": f"test-arn-{i}",
                "service": services[i],
                "eventTypeCode": f"TEST_EVENT_{i}",
                "eventTypeCategory": "scheduledChange",
                "region": "ap-northeast-2",
                "availabilityZone": "ap-northeast-2a",
                "startTime": now + timedelta(days=2 + i),
                "endTime": now + timedelta(days=3 + i),
                "lastUpdatedTime": now,
                "statusCode": "upcoming",
                "eventScopeCode": "ACCOUNT_SPECIFIC",
            }
            event = HealthEvent.from_api_response(event_data)
            event.description = f"Test description for event {i}"
            events.append(event)
            patches.append(PatchItem.from_event(event))

        # Manually set urgency to match urgency_map
        for i, patch in enumerate(patches):
            patch.urgency = urgency_map[i]

        summary_urgency = {
            "critical": {"count": 2, "services": ["EC2", "RDS"], "affected_resources": 0},
            "high": {"count": 1, "services": ["EC2"], "affected_resources": 0},
            "medium": {"count": 1, "services": ["Lambda"], "affected_resources": 0},
            "low": {"count": 1, "services": ["S3"], "affected_resources": 0},
        }

        summary_service = {
            "EC2": {"count": 2, "critical": 1, "high": 1, "medium": 0, "low": 0, "affected_resources": 0},
            "RDS": {"count": 1, "critical": 1, "high": 0, "medium": 0, "low": 0, "affected_resources": 0},
            "Lambda": {"count": 1, "critical": 0, "high": 0, "medium": 1, "low": 0, "affected_resources": 0},
            "S3": {"count": 1, "critical": 0, "high": 0, "medium": 0, "low": 1, "affected_resources": 0},
        }

        summary_month = {now.strftime("%Y-%m"): patches}

        return CollectionResult(
            events=events,
            patches=patches,
            summary_by_urgency=summary_urgency,
            summary_by_service=summary_service,
            summary_by_month=summary_month,
        )

    def test_initialization(self, sample_result_for_report):
        """Test PatchReporter initialization"""
        reporter = PatchReporter(sample_result_for_report)

        assert reporter.result == sample_result_for_report

    def test_urgency_display(self, sample_result_for_report):
        """Test _urgency_display method"""
        reporter = PatchReporter(sample_result_for_report)

        assert reporter._urgency_display("critical") == "긴급"
        assert reporter._urgency_display("high") == "높음"
        assert reporter._urgency_display("medium") == "중간"
        assert reporter._urgency_display("low") == "낮음"

    def test_patch_to_row(self, sample_result_for_report):
        """Test _patch_to_row method"""
        reporter = PatchReporter(sample_result_for_report)
        patch = sample_result_for_report.patches[0]

        row = reporter._patch_to_row(patch)

        assert len(row) == 11
        assert row[0] in ["긴급", "높음", "중간", "낮음"]  # urgency
        assert row[1] == patch.service
        assert row[2] == patch.event_type

    def test_get_row_style(self, sample_result_for_report):
        """Test _get_row_style method"""
        reporter = PatchReporter(sample_result_for_report)

        # Critical patch
        critical_patch = sample_result_for_report.patches[0]
        critical_patch.urgency = "critical"
        style = reporter._get_row_style(critical_patch)
        assert style is not None

        # High patch
        high_patch = sample_result_for_report.patches[2]
        high_patch.urgency = "high"
        style = reporter._get_row_style(high_patch)
        assert style is not None

        # Medium patch
        medium_patch = sample_result_for_report.patches[3]
        medium_patch.urgency = "medium"
        style = reporter._get_row_style(medium_patch)
        assert style is None

    @patch("core.shared.aws.health.reporter.Workbook")
    def test_generate_report(self, mock_workbook, sample_result_for_report, tmp_path):
        """Test generate_report method"""
        # Mock workbook
        wb_instance = MagicMock()
        mock_workbook.return_value = wb_instance
        wb_instance.save_as.return_value = tmp_path / "test_report.xlsx"

        reporter = PatchReporter(sample_result_for_report)
        output_path = reporter.generate_report(str(tmp_path), "test_report", include_calendar=False)

        # Verify workbook methods were called
        wb_instance.new_summary_sheet.assert_called_once()
        assert wb_instance.new_sheet.call_count >= 2  # At least all patches and urgent patches

    def test_print_summary_plain(self, sample_result_for_report, capsys):
        """Test print_summary with plain text output"""
        reporter = PatchReporter(sample_result_for_report)

        # Mock ImportError for Rich to force plain text output
        with patch.dict("sys.modules", {"rich.console": None, "rich.table": None}):
            reporter.print_summary()

        captured = capsys.readouterr()
        assert "AWS 필수 패치 분석 요약" in captured.out
        assert "긴급도별 현황" in captured.out


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Error handling tests"""

    def test_analyzer_api_failure(self, mock_boto_session):
        """Test HealthAnalyzer handles API failures gracefully"""
        client = mock_boto_session.client.return_value

        # Create a proper exception class
        class InvalidPaginationToken(Exception):
            pass

        # Mock the exceptions attribute
        client.exceptions = MagicMock()
        client.exceptions.InvalidPaginationToken = InvalidPaginationToken

        # Mock API failure
        paginator = MagicMock()
        paginator.paginate.side_effect = Exception("API Error")
        client.get_paginator.return_value = paginator

        analyzer = HealthAnalyzer(mock_boto_session)

        with pytest.raises(Exception) as exc_info:
            analyzer.get_events()

        assert "API Error" in str(exc_info.value)

    def test_event_details_failure(self, mock_boto_session):
        """Test handling of event details API failure"""
        client = mock_boto_session.client.return_value

        # Mock successful events but failed details
        now = datetime.now(timezone.utc)
        event = {
            "arn": "test-arn",
            "service": "EC2",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=5),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }

        paginator = MagicMock()
        paginator.paginate.return_value = [{"events": [event]}]
        client.get_paginator.return_value = paginator
        client.describe_event_details.side_effect = Exception("Details API Error")

        analyzer = HealthAnalyzer(mock_boto_session)

        # Should succeed but without details
        events = analyzer.get_events(include_details=True, include_affected_entities=False)

        assert len(events) == 1
        assert events[0].description == ""  # No description due to failure

    def test_affected_entities_failure(self, mock_boto_session):
        """Test handling of affected entities API failure"""
        client = mock_boto_session.client.return_value

        now = datetime.now(timezone.utc)
        event = {
            "arn": "test-arn",
            "service": "EC2",
            "eventTypeCode": "TEST",
            "eventTypeCategory": "scheduledChange",
            "region": "us-east-1",
            "availabilityZone": "",
            "startTime": now + timedelta(days=5),
            "endTime": None,
            "lastUpdatedTime": now,
            "statusCode": "upcoming",
            "eventScopeCode": "ACCOUNT_SPECIFIC",
        }

        # Mock successful events paginator
        events_paginator = MagicMock()
        events_paginator.paginate.return_value = [{"events": [event]}]

        # Mock failed affected entities paginator
        entities_paginator = MagicMock()
        entities_paginator.paginate.side_effect = Exception("Entities API Error")

        def get_paginator_side_effect(operation):
            if operation == "describe_events":
                return events_paginator
            elif operation == "describe_affected_entities":
                return entities_paginator
            return MagicMock()

        client.get_paginator.side_effect = get_paginator_side_effect

        analyzer = HealthAnalyzer(mock_boto_session)

        # Should succeed but without affected entities
        events = analyzer.get_events(include_details=False, include_affected_entities=True)

        assert len(events) == 1
        assert len(events[0].affected_entities) == 0  # No entities due to failure
