"""
tests/test_plugins_s3.py - S3 플러그인 테스트
"""

from datetime import datetime, timezone

from plugins.s3.empty_bucket import (
    BucketInfo,
    BucketStatus,
    S3AnalysisResult,
    analyze_buckets,
)


class TestBucketInfo:
    """BucketInfo 데이터클래스 테스트"""

    def test_total_size_mb(self):
        """총 크기 MB 변환"""
        bucket = BucketInfo(
            account_id="123456789012",
            account_name="test",
            name="test-bucket",
            region="ap-northeast-2",
            created_at=datetime.now(timezone.utc),
            total_size_bytes=10 * 1024**2,  # 10MB
        )
        assert bucket.total_size_mb == 10.0

    def test_total_size_gb(self):
        """총 크기 GB 변환"""
        bucket = BucketInfo(
            account_id="123456789012",
            account_name="test",
            name="test-bucket",
            region="ap-northeast-2",
            created_at=datetime.now(timezone.utc),
            total_size_bytes=2 * 1024**3,  # 2GB
        )
        assert bucket.total_size_gb == 2.0

    def test_default_values(self):
        """기본값 확인"""
        bucket = BucketInfo(
            account_id="123456789012",
            account_name="test",
            name="test-bucket",
            region="ap-northeast-2",
            created_at=datetime.now(timezone.utc),
        )
        assert bucket.object_count == 0
        assert bucket.total_size_bytes == 0
        assert bucket.versioning_enabled is False
        assert bucket.has_lifecycle is False
        assert bucket.has_logging is False
        assert bucket.has_replication is False
        assert bucket.encryption_type == "None"


class TestBucketStatus:
    """BucketStatus Enum 테스트"""

    def test_status_values(self):
        """상태 값 확인"""
        assert BucketStatus.NORMAL.value == "normal"
        assert BucketStatus.EMPTY.value == "empty"
        assert BucketStatus.VERSIONING_ONLY.value == "versioning_only"
        assert BucketStatus.SMALL.value == "small"


class TestAnalyzeBuckets:
    """analyze_buckets 테스트"""

    def test_empty_bucket(self):
        """완전히 빈 버킷"""
        buckets = [
            BucketInfo(
                account_id="123456789012",
                account_name="test",
                name="empty-bucket",
                region="ap-northeast-2",
                created_at=datetime.now(timezone.utc),
                object_count=0,
                total_size_bytes=0,
            )
        ]

        result = analyze_buckets(buckets, "123456789012", "test")

        assert result.empty_buckets == 1
        assert result.findings[0].status == BucketStatus.EMPTY

    def test_versioning_only_bucket(self):
        """버전 데이터만 있는 버킷"""
        buckets = [
            BucketInfo(
                account_id="123456789012",
                account_name="test",
                name="versioning-bucket",
                region="ap-northeast-2",
                created_at=datetime.now(timezone.utc),
                object_count=0,
                total_size_bytes=100 * 1024**2,  # 100MB (버전 데이터)
                versioning_enabled=True,
            )
        ]

        result = analyze_buckets(buckets, "123456789012", "test")

        assert result.versioning_only_buckets == 1
        assert result.findings[0].status == BucketStatus.VERSIONING_ONLY

    def test_small_bucket(self):
        """매우 작은 버킷 (1MB 미만)"""
        buckets = [
            BucketInfo(
                account_id="123456789012",
                account_name="test",
                name="small-bucket",
                region="ap-northeast-2",
                created_at=datetime.now(timezone.utc),
                object_count=5,
                total_size_bytes=500 * 1024,  # 500KB
            )
        ]

        result = analyze_buckets(buckets, "123456789012", "test")

        assert result.small_buckets == 1
        assert result.findings[0].status == BucketStatus.SMALL

    def test_normal_bucket(self):
        """정상 버킷"""
        buckets = [
            BucketInfo(
                account_id="123456789012",
                account_name="test",
                name="normal-bucket",
                region="ap-northeast-2",
                created_at=datetime.now(timezone.utc),
                object_count=100,
                total_size_bytes=10 * 1024**3,  # 10GB
            )
        ]

        result = analyze_buckets(buckets, "123456789012", "test")

        assert result.empty_buckets == 0
        assert result.versioning_only_buckets == 0
        assert result.small_buckets == 0
        assert result.findings[0].status == BucketStatus.NORMAL

    def test_mixed_buckets(self):
        """혼합 버킷 분석"""
        buckets = [
            BucketInfo(
                account_id="123456789012",
                account_name="test",
                name="empty",
                region="ap-northeast-2",
                created_at=datetime.now(timezone.utc),
                object_count=0,
                total_size_bytes=0,
            ),
            BucketInfo(
                account_id="123456789012",
                account_name="test",
                name="versioning",
                region="ap-northeast-2",
                created_at=datetime.now(timezone.utc),
                object_count=0,
                total_size_bytes=50 * 1024**2,
            ),
            BucketInfo(
                account_id="123456789012",
                account_name="test",
                name="small",
                region="ap-northeast-2",
                created_at=datetime.now(timezone.utc),
                object_count=3,
                total_size_bytes=100 * 1024,
            ),
            BucketInfo(
                account_id="123456789012",
                account_name="test",
                name="normal",
                region="ap-northeast-2",
                created_at=datetime.now(timezone.utc),
                object_count=1000,
                total_size_bytes=5 * 1024**3,
            ),
        ]

        result = analyze_buckets(buckets, "123456789012", "test")

        assert result.total_buckets == 4
        assert result.empty_buckets == 1
        assert result.versioning_only_buckets == 1
        assert result.small_buckets == 1

    def test_total_size_calculation(self):
        """총 크기 계산"""
        buckets = [
            BucketInfo(
                account_id="123456789012",
                account_name="test",
                name="bucket1",
                region="ap-northeast-2",
                created_at=datetime.now(timezone.utc),
                object_count=10,
                total_size_bytes=1 * 1024**3,  # 1GB
            ),
            BucketInfo(
                account_id="123456789012",
                account_name="test",
                name="bucket2",
                region="ap-northeast-2",
                created_at=datetime.now(timezone.utc),
                object_count=20,
                total_size_bytes=2 * 1024**3,  # 2GB
            ),
        ]

        result = analyze_buckets(buckets, "123456789012", "test")

        assert result.total_size_gb == 3.0


class TestS3AnalysisResult:
    """S3AnalysisResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        result = S3AnalysisResult(
            account_id="123456789012",
            account_name="test",
        )
        assert result.total_buckets == 0
        assert result.empty_buckets == 0
        assert result.versioning_only_buckets == 0
        assert result.small_buckets == 0
        assert result.total_size_gb == 0.0
        assert result.findings == []
