"""
tests/test_plugins_kms.py - KMS 플러그인 테스트
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from analyzers.kms.unused import (
    KMSKeyAnalysisResult,
    KMSKeyInfo,
    KMSKeyStatus,
    analyze_kms_keys,
)


class TestKMSKeyInfo:
    """KMSKeyInfo 데이터클래스 테스트"""

    def test_is_customer_managed_true(self):
        """고객 관리 키"""
        key = KMSKeyInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            key_id="12345678-1234-1234-1234-123456789012",
            arn="arn:aws:kms:ap-northeast-2:123:key/12345678",
            description="Test CMK",
            key_state="Enabled",
            key_manager="CUSTOMER",
            creation_date=datetime.now(timezone.utc),
        )
        assert key.is_customer_managed is True

    def test_is_customer_managed_false(self):
        """AWS 관리 키"""
        key = KMSKeyInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            key_id="12345678-1234-1234-1234-123456789012",
            arn="arn:aws:kms:ap-northeast-2:123:key/12345678",
            description="AWS managed key",
            key_state="Enabled",
            key_manager="AWS",
            creation_date=datetime.now(timezone.utc),
        )
        assert key.is_customer_managed is False

    @patch("analyzers.kms.unused.get_kms_key_price")
    def test_monthly_cost_cmk(self, mock_price):
        """CMK 월간 비용"""
        mock_price.return_value = 1.0
        key = KMSKeyInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            key_id="key-123",
            arn="arn",
            description="CMK",
            key_state="Enabled",
            key_manager="CUSTOMER",
            creation_date=datetime.now(timezone.utc),
        )
        assert key.monthly_cost == 1.0
        mock_price.assert_called_with("ap-northeast-2", "CUSTOMER")

    @patch("analyzers.kms.unused.get_kms_key_price")
    def test_monthly_cost_aws_managed(self, mock_price):
        """AWS 관리 키 월간 비용 (무료)"""
        mock_price.return_value = 0.0
        key = KMSKeyInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            key_id="key-123",
            arn="arn",
            description="AWS managed",
            key_state="Enabled",
            key_manager="AWS",
            creation_date=datetime.now(timezone.utc),
        )
        assert key.monthly_cost == 0.0


class TestKMSKeyStatus:
    """KMSKeyStatus Enum 테스트"""

    def test_status_values(self):
        """상태 값 확인"""
        assert KMSKeyStatus.NORMAL.value == "normal"
        assert KMSKeyStatus.DISABLED.value == "disabled"
        assert KMSKeyStatus.PENDING_DELETE.value == "pending_delete"


class TestAnalyzeKMSKeys:
    """analyze_kms_keys 테스트"""

    @patch("analyzers.kms.unused.get_kms_key_price")
    def test_aws_managed_key(self, mock_price):
        """AWS 관리 키"""
        mock_price.return_value = 0.0
        keys = [
            KMSKeyInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                key_id="aws-key",
                arn="arn",
                description="AWS managed",
                key_state="Enabled",
                key_manager="AWS",
                creation_date=datetime.now(timezone.utc),
            )
        ]

        result = analyze_kms_keys(keys, "123456789012", "test", "ap-northeast-2")

        assert result.aws_managed_count == 1
        assert result.customer_managed_count == 0
        assert result.findings[0].status == KMSKeyStatus.NORMAL

    @patch("analyzers.kms.unused.get_kms_key_price")
    def test_disabled_cmk(self, mock_price):
        """비활성화된 CMK"""
        mock_price.return_value = 1.0
        keys = [
            KMSKeyInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                key_id="disabled-key",
                arn="arn",
                description="Disabled CMK",
                key_state="Disabled",
                key_manager="CUSTOMER",
                creation_date=datetime.now(timezone.utc),
            )
        ]

        result = analyze_kms_keys(keys, "123456789012", "test", "ap-northeast-2")

        assert result.disabled_count == 1
        assert result.disabled_monthly_cost == 1.0
        assert result.findings[0].status == KMSKeyStatus.DISABLED

    @patch("analyzers.kms.unused.get_kms_key_price")
    def test_pending_deletion_cmk(self, mock_price):
        """삭제 예정 CMK"""
        mock_price.return_value = 1.0
        keys = [
            KMSKeyInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                key_id="pending-key",
                arn="arn",
                description="Pending deletion",
                key_state="PendingDeletion",
                key_manager="CUSTOMER",
                creation_date=datetime.now(timezone.utc),
                deletion_date=datetime.now(timezone.utc) + timedelta(days=7),
            )
        ]

        result = analyze_kms_keys(keys, "123456789012", "test", "ap-northeast-2")

        assert result.pending_delete_count == 1
        assert result.findings[0].status == KMSKeyStatus.PENDING_DELETE

    @patch("analyzers.kms.unused.get_kms_key_price")
    def test_normal_cmk(self, mock_price):
        """정상 CMK"""
        mock_price.return_value = 1.0
        keys = [
            KMSKeyInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                key_id="normal-key",
                arn="arn",
                description="Normal CMK",
                key_state="Enabled",
                key_manager="CUSTOMER",
                creation_date=datetime.now(timezone.utc),
            )
        ]

        result = analyze_kms_keys(keys, "123456789012", "test", "ap-northeast-2")

        assert result.normal_count == 1
        assert result.findings[0].status == KMSKeyStatus.NORMAL

    @patch("analyzers.kms.unused.get_kms_key_price")
    def test_mixed_keys(self, mock_price):
        """혼합 키 분석"""
        mock_price.return_value = 1.0
        keys = [
            KMSKeyInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                key_id="aws-key",
                arn="arn1",
                description="AWS managed",
                key_state="Enabled",
                key_manager="AWS",
                creation_date=datetime.now(timezone.utc),
            ),
            KMSKeyInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                key_id="cmk-enabled",
                arn="arn2",
                description="Enabled CMK",
                key_state="Enabled",
                key_manager="CUSTOMER",
                creation_date=datetime.now(timezone.utc),
            ),
            KMSKeyInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                key_id="cmk-disabled",
                arn="arn3",
                description="Disabled CMK",
                key_state="Disabled",
                key_manager="CUSTOMER",
                creation_date=datetime.now(timezone.utc),
            ),
        ]

        result = analyze_kms_keys(keys, "123456789012", "test", "ap-northeast-2")

        assert result.total_count == 3
        assert result.aws_managed_count == 1
        assert result.customer_managed_count == 2
        assert result.disabled_count == 1
        assert result.normal_count == 2


class TestKMSKeyAnalysisResult:
    """KMSKeyAnalysisResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        result = KMSKeyAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert result.total_count == 0
        assert result.customer_managed_count == 0
        assert result.aws_managed_count == 0
        assert result.disabled_count == 0
        assert result.pending_delete_count == 0
        assert result.normal_count == 0
        assert result.disabled_monthly_cost == 0.0
        assert result.findings == []
