"""
tests/test_plugins_secretsmanager.py - Secrets Manager 플러그인 테스트
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from analyzers.secretsmanager.unused import (
    UNUSED_DAYS_THRESHOLD,
    SecretAnalysisResult,
    SecretInfo,
    SecretStatus,
    analyze_secrets,
)


class TestSecretInfo:
    """SecretInfo 데이터클래스 테스트"""

    @patch("analyzers.secretsmanager.unused.get_secret_price")
    def test_monthly_cost(self, mock_price):
        """월간 비용"""
        mock_price.return_value = 0.40
        secret = SecretInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            arn="arn:aws:secretsmanager:ap-northeast-2:123:secret:test",
            name="test-secret",
            description="Test",
            created_date=datetime.now(timezone.utc),
            last_accessed_date=None,
            last_changed_date=None,
            rotation_enabled=False,
        )
        assert secret.monthly_cost == 0.40

    def test_days_since_access_with_date(self):
        """마지막 액세스 이후 일수 계산"""
        last_access = datetime.now(timezone.utc) - timedelta(days=30)
        secret = SecretInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            arn="arn",
            name="test",
            description="",
            created_date=datetime.now(timezone.utc),
            last_accessed_date=last_access,
            last_changed_date=None,
            rotation_enabled=False,
        )
        assert secret.days_since_access == 30

    def test_days_since_access_none(self):
        """마지막 액세스 날짜 없음"""
        secret = SecretInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            arn="arn",
            name="test",
            description="",
            created_date=datetime.now(timezone.utc),
            last_accessed_date=None,
            last_changed_date=None,
            rotation_enabled=False,
        )
        assert secret.days_since_access is None


class TestSecretStatus:
    """SecretStatus Enum 테스트"""

    def test_status_values(self):
        """상태 값 확인"""
        assert SecretStatus.NORMAL.value == "normal"
        assert SecretStatus.UNUSED.value == "unused"
        assert SecretStatus.PENDING_DELETE.value == "pending_delete"


class TestAnalyzeSecrets:
    """analyze_secrets 테스트"""

    @patch("analyzers.secretsmanager.unused.get_secret_price")
    def test_pending_delete_secret(self, mock_price):
        """삭제 예정 시크릿"""
        mock_price.return_value = 0.40
        secrets = [
            SecretInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                arn="arn",
                name="deleted-secret",
                description="",
                created_date=datetime.now(timezone.utc) - timedelta(days=100),
                last_accessed_date=None,
                last_changed_date=None,
                rotation_enabled=False,
                deleted_date=datetime.now(timezone.utc),
            )
        ]

        result = analyze_secrets(secrets, "123456789012", "test", "ap-northeast-2")

        assert result.pending_delete_count == 1
        assert result.findings[0].status == SecretStatus.PENDING_DELETE

    @patch("analyzers.secretsmanager.unused.get_secret_price")
    def test_unused_secret_old_access(self, mock_price):
        """오래된 액세스 - 미사용"""
        mock_price.return_value = 0.40
        old_access = datetime.now(timezone.utc) - timedelta(days=UNUSED_DAYS_THRESHOLD + 10)
        secrets = [
            SecretInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                arn="arn",
                name="unused-secret",
                description="",
                created_date=datetime.now(timezone.utc) - timedelta(days=200),
                last_accessed_date=old_access,
                last_changed_date=None,
                rotation_enabled=False,
            )
        ]

        result = analyze_secrets(secrets, "123456789012", "test", "ap-northeast-2")

        assert result.unused_count == 1
        assert result.findings[0].status == SecretStatus.UNUSED

    @patch("analyzers.secretsmanager.unused.get_secret_price")
    def test_unused_secret_never_accessed(self, mock_price):
        """액세스 없음 + 오래된 생성일"""
        mock_price.return_value = 0.40
        old_created = datetime.now(timezone.utc) - timedelta(days=UNUSED_DAYS_THRESHOLD + 10)
        secrets = [
            SecretInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                arn="arn",
                name="never-accessed",
                description="",
                created_date=old_created,
                last_accessed_date=None,
                last_changed_date=None,
                rotation_enabled=False,
            )
        ]

        result = analyze_secrets(secrets, "123456789012", "test", "ap-northeast-2")

        assert result.unused_count == 1
        assert result.findings[0].status == SecretStatus.UNUSED

    @patch("analyzers.secretsmanager.unused.get_secret_price")
    def test_normal_secret(self, mock_price):
        """정상 시크릿"""
        mock_price.return_value = 0.40
        recent_access = datetime.now(timezone.utc) - timedelta(days=10)
        secrets = [
            SecretInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                arn="arn",
                name="normal-secret",
                description="",
                created_date=datetime.now(timezone.utc) - timedelta(days=30),
                last_accessed_date=recent_access,
                last_changed_date=None,
                rotation_enabled=True,
            )
        ]

        result = analyze_secrets(secrets, "123456789012", "test", "ap-northeast-2")

        assert result.normal_count == 1
        assert result.findings[0].status == SecretStatus.NORMAL

    @patch("analyzers.secretsmanager.unused.get_secret_price")
    def test_mixed_secrets(self, mock_price):
        """혼합 시크릿 분석"""
        mock_price.return_value = 0.40
        now = datetime.now(timezone.utc)
        secrets = [
            SecretInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                arn="arn1",
                name="normal",
                description="",
                created_date=now - timedelta(days=30),
                last_accessed_date=now - timedelta(days=5),
                last_changed_date=None,
                rotation_enabled=True,
            ),
            SecretInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                arn="arn2",
                name="unused",
                description="",
                created_date=now - timedelta(days=200),
                last_accessed_date=now - timedelta(days=100),
                last_changed_date=None,
                rotation_enabled=False,
            ),
            SecretInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                arn="arn3",
                name="deleted",
                description="",
                created_date=now - timedelta(days=100),
                last_accessed_date=None,
                last_changed_date=None,
                rotation_enabled=False,
                deleted_date=now,
            ),
        ]

        result = analyze_secrets(secrets, "123456789012", "test", "ap-northeast-2")

        assert result.total_count == 3
        assert result.normal_count == 1
        assert result.unused_count == 1
        assert result.pending_delete_count == 1


class TestSecretAnalysisResult:
    """SecretAnalysisResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        result = SecretAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert result.total_count == 0
        assert result.unused_count == 0
        assert result.pending_delete_count == 0
        assert result.normal_count == 0
        assert result.total_monthly_cost == 0.0
        assert result.unused_monthly_cost == 0.0
        assert result.findings == []
