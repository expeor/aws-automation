"""
tests/test_plugins_cloudwatch.py - CloudWatch 플러그인 테스트
"""

from datetime import datetime, timedelta, timezone

from analyzers.cloudwatch.loggroup_audit import (
    COST_PER_GB_MONTH,
    OLD_DAYS_THRESHOLD,
    LogGroupAnalysisResult,
    LogGroupInfo,
    LogGroupStatus,
    analyze_log_groups,
)


class TestLogGroupInfo:
    """LogGroupInfo 데이터클래스 테스트"""

    def test_stored_gb(self):
        """저장 크기 GB 변환"""
        lg = LogGroupInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            name="/aws/lambda/test",
            arn="arn:aws:logs:ap-northeast-2:123:log-group:/aws/lambda/test",
            creation_time=datetime.now(timezone.utc) - timedelta(days=30),
            stored_bytes=2 * 1024**3,  # 2GB
            retention_days=30,
            last_ingestion_time=datetime.now(timezone.utc),
            log_stream_count=10,
        )
        assert lg.stored_gb == 2.0

    def test_monthly_cost(self):
        """월간 비용 계산"""
        lg = LogGroupInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            name="/aws/lambda/test",
            arn="arn",
            creation_time=datetime.now(timezone.utc),
            stored_bytes=10 * 1024**3,  # 10GB
            retention_days=30,
            last_ingestion_time=datetime.now(timezone.utc),
            log_stream_count=5,
        )
        # 10GB * $0.03/GB = $0.30
        assert lg.monthly_cost == 10 * COST_PER_GB_MONTH

    def test_age_days(self):
        """생성 후 경과 일수"""
        lg = LogGroupInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            name="/test",
            arn="arn",
            creation_time=datetime.now(timezone.utc) - timedelta(days=100),
            stored_bytes=1000,
            retention_days=None,
            last_ingestion_time=None,
            log_stream_count=0,
        )
        assert lg.age_days == 100

    def test_days_since_ingestion(self):
        """마지막 ingestion 이후 일수"""
        lg = LogGroupInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            name="/test",
            arn="arn",
            creation_time=datetime.now(timezone.utc) - timedelta(days=100),
            stored_bytes=1000,
            retention_days=None,
            last_ingestion_time=datetime.now(timezone.utc) - timedelta(days=50),
            log_stream_count=1,
        )
        assert lg.days_since_ingestion == 50

    def test_days_since_ingestion_none(self):
        """ingestion 기록 없음"""
        lg = LogGroupInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            name="/test",
            arn="arn",
            creation_time=datetime.now(timezone.utc),
            stored_bytes=0,
            retention_days=None,
            last_ingestion_time=None,
            log_stream_count=0,
        )
        assert lg.days_since_ingestion is None


class TestLogGroupStatus:
    """LogGroupStatus Enum 테스트"""

    def test_status_values(self):
        """상태 값 확인"""
        assert LogGroupStatus.NORMAL.value == "normal"
        assert LogGroupStatus.EMPTY.value == "empty"
        assert LogGroupStatus.NO_RETENTION.value == "no_retention"
        assert LogGroupStatus.OLD.value == "old"


class TestAnalyzeLogGroups:
    """analyze_log_groups 테스트"""

    def test_empty_log_group(self):
        """빈 로그 그룹"""
        log_groups = [
            LogGroupInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="/empty-log-group",
                arn="arn",
                creation_time=datetime.now(timezone.utc) - timedelta(days=10),
                stored_bytes=0,  # 빈 로그
                retention_days=30,
                last_ingestion_time=None,
                log_stream_count=0,
            )
        ]

        result = analyze_log_groups(log_groups, "123456789012", "test", "ap-northeast-2")

        assert result.empty_count == 1
        assert result.findings[0].status == LogGroupStatus.EMPTY

    def test_old_log_group(self):
        """오래된 로그 그룹"""
        log_groups = [
            LogGroupInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="/old-log-group",
                arn="arn",
                creation_time=datetime.now(timezone.utc) - timedelta(days=365),
                stored_bytes=1024**3,  # 1GB
                retention_days=None,
                last_ingestion_time=datetime.now(timezone.utc) - timedelta(days=OLD_DAYS_THRESHOLD + 10),
                log_stream_count=5,
            )
        ]

        result = analyze_log_groups(log_groups, "123456789012", "test", "ap-northeast-2")

        assert result.old_count == 1
        assert result.findings[0].status == LogGroupStatus.OLD

    def test_no_retention_log_group(self):
        """보존 기간 미설정 로그 그룹"""
        log_groups = [
            LogGroupInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="/no-retention",
                arn="arn",
                creation_time=datetime.now(timezone.utc) - timedelta(days=30),
                stored_bytes=5 * 1024**3,
                retention_days=None,  # 무기한
                last_ingestion_time=datetime.now(timezone.utc),  # 최근 ingestion
                log_stream_count=10,
            )
        ]

        result = analyze_log_groups(log_groups, "123456789012", "test", "ap-northeast-2")

        assert result.no_retention_count == 1
        assert result.findings[0].status == LogGroupStatus.NO_RETENTION

    def test_normal_log_group(self):
        """정상 로그 그룹"""
        log_groups = [
            LogGroupInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="/normal-log-group",
                arn="arn",
                creation_time=datetime.now(timezone.utc) - timedelta(days=30),
                stored_bytes=1024**3,
                retention_days=30,
                last_ingestion_time=datetime.now(timezone.utc) - timedelta(days=1),
                log_stream_count=5,
            )
        ]

        result = analyze_log_groups(log_groups, "123456789012", "test", "ap-northeast-2")

        assert result.normal_count == 1
        assert result.findings[0].status == LogGroupStatus.NORMAL

    def test_mixed_log_groups(self):
        """혼합 로그 그룹 분석"""
        now = datetime.now(timezone.utc)
        log_groups = [
            LogGroupInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="/empty",
                arn="arn1",
                creation_time=now - timedelta(days=30),
                stored_bytes=0,
                retention_days=None,
                last_ingestion_time=None,
                log_stream_count=0,
            ),
            LogGroupInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="/old",
                arn="arn2",
                creation_time=now - timedelta(days=200),
                stored_bytes=1024**3,
                retention_days=30,
                last_ingestion_time=now - timedelta(days=100),
                log_stream_count=3,
            ),
            LogGroupInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="/no-retention",
                arn="arn3",
                creation_time=now - timedelta(days=10),
                stored_bytes=2 * 1024**3,
                retention_days=None,
                last_ingestion_time=now - timedelta(days=1),
                log_stream_count=5,
            ),
            LogGroupInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                name="/normal",
                arn="arn4",
                creation_time=now - timedelta(days=50),
                stored_bytes=3 * 1024**3,
                retention_days=30,
                last_ingestion_time=now - timedelta(days=2),
                log_stream_count=10,
            ),
        ]

        result = analyze_log_groups(log_groups, "123456789012", "test", "ap-northeast-2")

        assert result.total_count == 4
        assert result.empty_count == 1
        assert result.old_count == 1
        assert result.no_retention_count == 1
        assert result.normal_count == 1


class TestLogGroupAnalysisResult:
    """LogGroupAnalysisResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        result = LogGroupAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert result.total_count == 0
        assert result.empty_count == 0
        assert result.no_retention_count == 0
        assert result.old_count == 0
        assert result.normal_count == 0
        assert result.total_stored_gb == 0.0
        assert result.empty_monthly_cost == 0.0
        assert result.old_monthly_cost == 0.0
        assert result.findings == []
