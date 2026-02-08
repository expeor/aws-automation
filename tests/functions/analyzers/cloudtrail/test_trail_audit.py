"""tests/analyzers/cloudtrail/test_trail_audit.py - CloudTrail 감사 테스트"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from functions.analyzers.cloudtrail.trail_audit import (
    TrailAuditResult,
    TrailInfo,
    collect_trails,
)

# =============================================================================
# 팩토리 함수
# =============================================================================


def _make_trail_info(
    trail_name: str = "test-trail",
    is_logging: bool = True,
    management_events_enabled: bool = True,
    data_events_enabled: bool = False,
    is_multi_region: bool = True,
    include_global_events: bool = True,
    s3_bucket: str = "my-trail-bucket",
    kms_key_id: str = "",
    account_id: str = "123456789012",
    account_name: str = "test-account",
    region: str = "ap-northeast-2",
    error: str = "",
) -> TrailInfo:
    """테스트용 TrailInfo 생성"""
    return TrailInfo(
        account_id=account_id,
        account_name=account_name,
        region=region,
        trail_name=trail_name,
        trail_arn=f"arn:aws:cloudtrail:{region}:{account_id}:trail/{trail_name}",
        is_logging=is_logging,
        management_events_enabled=management_events_enabled,
        data_events_enabled=data_events_enabled,
        is_multi_region=is_multi_region,
        include_global_events=include_global_events,
        s3_bucket=s3_bucket,
        s3_prefix="",
        kms_key_id=kms_key_id,
        error=error,
    )


def _make_audit_result(
    trails: list[TrailInfo] | None = None,
    account_id: str = "123456789012",
    account_name: str = "test-account",
    region: str = "ap-northeast-2",
) -> TrailAuditResult:
    """테스트용 TrailAuditResult 생성"""
    trail_list = trails or []
    return TrailAuditResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
        trails=trail_list,
        total_count=len(trail_list),
        logging_enabled_count=sum(1 for t in trail_list if t.is_logging),
        management_events_count=sum(1 for t in trail_list if t.management_events_enabled),
        data_events_count=sum(1 for t in trail_list if t.data_events_enabled),
        multi_region_count=sum(1 for t in trail_list if t.is_multi_region),
    )


# =============================================================================
# TrailInfo 테스트
# =============================================================================


class TestTrailInfo:
    """TrailInfo 데이터 클래스 테스트"""

    def test_to_dict(self):
        """to_dict 메서드 테스트"""
        trail = _make_trail_info(trail_name="main-trail", is_logging=True)
        d = trail.to_dict()

        assert d["trail_name"] == "main-trail"
        assert d["is_logging"] is True
        assert d["account_id"] == "123456789012"
        assert d["region"] == "ap-northeast-2"
        assert d["s3_bucket"] == "my-trail-bucket"

    def test_to_dict_with_kms(self):
        """KMS 암호화 설정 포함 to_dict"""
        trail = _make_trail_info(kms_key_id="arn:aws:kms:ap-northeast-2:123:key/abc")
        d = trail.to_dict()
        assert d["kms_key_id"] == "arn:aws:kms:ap-northeast-2:123:key/abc"

    def test_to_dict_with_error(self):
        """오류 메시지 포함 to_dict"""
        trail = _make_trail_info(error="AccessDenied")
        d = trail.to_dict()
        assert d["error"] == "AccessDenied"

    def test_default_values(self):
        """기본값 테스트"""
        trail = _make_trail_info()
        assert trail.error == ""
        assert trail.s3_prefix == ""

    def test_all_features_enabled(self):
        """모든 기능 활성화된 트레일"""
        trail = _make_trail_info(
            is_logging=True,
            management_events_enabled=True,
            data_events_enabled=True,
            is_multi_region=True,
            include_global_events=True,
        )
        assert trail.is_logging is True
        assert trail.management_events_enabled is True
        assert trail.data_events_enabled is True

    def test_logging_disabled(self):
        """로깅 비활성화 트레일"""
        trail = _make_trail_info(is_logging=False)
        assert trail.is_logging is False


# =============================================================================
# TrailAuditResult 테스트
# =============================================================================


class TestTrailAuditResult:
    """TrailAuditResult 테스트"""

    def test_empty_result(self):
        """빈 결과"""
        result = _make_audit_result(trails=[])
        assert result.total_count == 0
        assert result.logging_enabled_count == 0

    def test_counts(self):
        """통계 카운트"""
        trails = [
            _make_trail_info(trail_name="t1", is_logging=True, management_events_enabled=True),
            _make_trail_info(trail_name="t2", is_logging=False, management_events_enabled=False, is_multi_region=False),
            _make_trail_info(trail_name="t3", is_logging=True, data_events_enabled=True),
        ]
        result = _make_audit_result(trails=trails)

        assert result.total_count == 3
        assert result.logging_enabled_count == 2
        assert result.management_events_count == 2
        assert result.data_events_count == 1
        assert result.multi_region_count == 2


# =============================================================================
# collect_trails 함수 테스트
# =============================================================================


class TestCollectTrails:
    """CloudTrail 수집 함수 테스트"""

    @patch("functions.analyzers.cloudtrail.trail_audit.get_client")
    def test_collect_single_trail(self, mock_get_client):
        """단일 트레일 수집"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        trail_arn = "arn:aws:cloudtrail:ap-northeast-2:123456789012:trail/main-trail"

        # list_trails 응답 (초기 목록 조회)
        mock_client.list_trails.return_value = {
            "Trails": [
                {
                    "Name": "main-trail",
                    "TrailARN": trail_arn,
                }
            ]
        }

        # describe_trails 응답 (상세 정보 조회)
        mock_client.describe_trails.return_value = {
            "trailList": [
                {
                    "Name": "main-trail",
                    "TrailARN": trail_arn,
                    "IsMultiRegionTrail": True,
                    "IncludeGlobalServiceEvents": True,
                    "S3BucketName": "my-bucket",
                    "S3KeyPrefix": "",
                    "KMSKeyId": "",
                }
            ]
        }

        # get_trail_status 응답
        mock_client.get_trail_status.return_value = {"IsLogging": True}

        # get_event_selectors 응답
        mock_client.get_event_selectors.return_value = {
            "EventSelectors": [
                {
                    "ReadWriteType": "All",
                    "IncludeManagementEvents": True,
                    "DataResources": [],
                }
            ],
            "AdvancedEventSelectors": [],
        }

        mock_session = MagicMock()
        trails = collect_trails(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(trails) == 1
        assert trails[0].trail_name == "main-trail"
        assert trails[0].is_logging is True
        assert trails[0].management_events_enabled is True
        assert trails[0].is_multi_region is True

    @patch("functions.analyzers.cloudtrail.trail_audit.get_client")
    def test_collect_no_trails(self, mock_get_client):
        """트레일 없는 경우"""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_trails.return_value = {"Trails": []}

        mock_session = MagicMock()
        trails = collect_trails(mock_session, "123456789012", "test-account", "ap-northeast-2")

        assert trails == []

    @patch("functions.analyzers.cloudtrail.trail_audit.get_client")
    def test_collect_client_error(self, mock_get_client):
        """ClientError 발생 시"""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_trails.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "Access Denied"}},
            "ListTrails",
        )

        mock_session = MagicMock()
        trails = collect_trails(mock_session, "123456789012", "test-account", "ap-northeast-2")

        # ClientError 시 빈 리스트
        assert isinstance(trails, list)
