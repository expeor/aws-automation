"""
tests/core/parallel/test_parallel_quotas.py - Service Quotas 테스트
"""

from unittest.mock import MagicMock, patch

import pytest

from core.parallel.quotas import (
    COMMON_QUOTAS,
    QuotaStatus,
    ServiceQuotaChecker,
    ServiceQuotaInfo,
    get_quota_checker,
    reset_quota_checkers,
)


class TestQuotaStatus:
    """QuotaStatus 테스트"""

    def test_enum_values(self):
        """Enum 값 확인"""
        assert QuotaStatus.OK.value == "ok"
        assert QuotaStatus.WARNING.value == "warning"
        assert QuotaStatus.CRITICAL.value == "critical"
        assert QuotaStatus.EXCEEDED.value == "exceeded"
        assert QuotaStatus.UNKNOWN.value == "unknown"


class TestServiceQuotaInfo:
    """ServiceQuotaInfo 테스트"""

    def test_basic_creation(self):
        """기본 생성"""
        quota = ServiceQuotaInfo(
            service_code="ec2",
            quota_code="L-1216C47A",
            quota_name="Running On-Demand Standard instances",
            value=100.0,
        )

        assert quota.service_code == "ec2"
        assert quota.quota_code == "L-1216C47A"
        assert quota.value == 100.0
        assert quota.status == QuotaStatus.UNKNOWN

    def test_status_ok(self):
        """정상 상태 계산"""
        quota = ServiceQuotaInfo(
            service_code="ec2",
            quota_code="L-1216C47A",
            quota_name="Test",
            value=100.0,
            usage_value=50.0,
        )

        assert quota.status == QuotaStatus.OK
        assert quota.usage_percent == 50.0

    def test_status_warning(self):
        """경고 상태 계산 (80% 이상)"""
        quota = ServiceQuotaInfo(
            service_code="ec2",
            quota_code="L-1216C47A",
            quota_name="Test",
            value=100.0,
            usage_value=85.0,
        )

        assert quota.status == QuotaStatus.WARNING
        assert quota.usage_percent == 85.0

    def test_status_critical(self):
        """위험 상태 계산 (90% 이상)"""
        quota = ServiceQuotaInfo(
            service_code="ec2",
            quota_code="L-1216C47A",
            quota_name="Test",
            value=100.0,
            usage_value=95.0,
        )

        assert quota.status == QuotaStatus.CRITICAL
        assert quota.usage_percent == 95.0

    def test_status_exceeded(self):
        """초과 상태 계산 (100% 이상)"""
        quota = ServiceQuotaInfo(
            service_code="ec2",
            quota_code="L-1216C47A",
            quota_name="Test",
            value=100.0,
            usage_value=105.0,
        )

        assert quota.status == QuotaStatus.EXCEEDED
        assert quota.usage_percent == 105.0

    def test_to_dict(self):
        """딕셔너리 변환"""
        quota = ServiceQuotaInfo(
            service_code="ec2",
            quota_code="L-1216C47A",
            quota_name="Test Quota",
            value=100.0,
            unit="Count",
            adjustable=True,
            usage_value=50.0,
        )

        d = quota.to_dict()

        assert d["service_code"] == "ec2"
        assert d["quota_code"] == "L-1216C47A"
        assert d["quota_name"] == "Test Quota"
        assert d["value"] == 100.0
        assert d["unit"] == "Count"
        assert d["adjustable"] is True
        assert d["usage_value"] == 50.0
        assert d["status"] == "ok"


class TestServiceQuotaChecker:
    """ServiceQuotaChecker 테스트"""

    def setup_method(self):
        """테스트 전 리셋"""
        reset_quota_checkers()

    def test_creation(self):
        """생성 테스트"""
        session = MagicMock()
        checker = ServiceQuotaChecker(session=session, region="ap-northeast-2")

        assert checker.session == session
        assert checker.region == "ap-northeast-2"

    @patch("core.parallel.quotas.ServiceQuotaChecker._get_client")
    def test_get_service_quotas(self, mock_get_client):
        """서비스 쿼터 조회"""
        session = MagicMock()
        checker = ServiceQuotaChecker(session=session, region="us-east-1")

        # Mock 클라이언트 설정
        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Quotas": [
                    {
                        "QuotaCode": "L-1216C47A",
                        "QuotaName": "Running On-Demand Standard instances",
                        "Value": 100.0,
                        "Unit": "None",
                        "Adjustable": True,
                        "GlobalQuota": False,
                    },
                    {
                        "QuotaCode": "L-34B43A08",
                        "QuotaName": "All Standard Spot Instance Requests",
                        "Value": 50.0,
                        "Unit": "None",
                        "Adjustable": True,
                        "GlobalQuota": False,
                    },
                ]
            }
        ]

        quotas = checker.get_service_quotas("ec2")

        assert len(quotas) == 2
        assert quotas[0].quota_code == "L-1216C47A"
        assert quotas[0].value == 100.0
        assert quotas[1].quota_code == "L-34B43A08"

    @patch("core.parallel.quotas.ServiceQuotaChecker._get_client")
    def test_get_quota_by_name(self, mock_get_client):
        """이름으로 쿼터 조회"""
        session = MagicMock()
        checker = ServiceQuotaChecker(session=session, region="us-east-1")

        mock_client = MagicMock()
        mock_paginator = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Quotas": [
                    {
                        "QuotaCode": "L-1216C47A",
                        "QuotaName": "Running On-Demand Standard instances",
                        "Value": 100.0,
                    },
                ]
            }
        ]

        quota = checker.get_quota("ec2", "Running On-Demand")

        assert quota is not None
        assert "On-Demand" in quota.quota_name

    def test_cache_set_get(self):
        """캐시 set/get 기능"""
        session = MagicMock()
        checker = ServiceQuotaChecker(session=session, region="us-east-1", cache_ttl=60.0)

        # 캐시에 데이터 추가
        test_data = [ServiceQuotaInfo("ec2", "test", "Test Quota", 100.0)]
        checker._set_cached("test_key", test_data)

        # 캐시에서 조회
        cached = checker._get_cached("test_key")
        assert cached == test_data

        # 없는 키 조회
        assert checker._get_cached("unknown_key") is None

    def test_clear_cache(self):
        """캐시 초기화"""
        session = MagicMock()
        checker = ServiceQuotaChecker(session=session, region="us-east-1")

        # 캐시에 데이터 추가
        checker._set_cached("test_key", "test_value")

        # 캐시 확인
        assert checker._get_cached("test_key") == "test_value"

        # 캐시 초기화
        checker.clear_cache()

        # 캐시가 비어있어야 함
        assert checker._get_cached("test_key") is None


class TestGetQuotaChecker:
    """get_quota_checker 싱글톤 테스트"""

    def setup_method(self):
        """테스트 전 리셋"""
        reset_quota_checkers()

    def test_returns_same_instance(self):
        """동일 세션/리전에 대해 같은 인스턴스 반환"""
        session = MagicMock()
        checker1 = get_quota_checker(session, "us-east-1")
        checker2 = get_quota_checker(session, "us-east-1")

        assert checker1 is checker2

    def test_different_regions_different_instances(self):
        """다른 리전은 다른 인스턴스"""
        session = MagicMock()
        checker1 = get_quota_checker(session, "us-east-1")
        checker2 = get_quota_checker(session, "ap-northeast-2")

        assert checker1 is not checker2


class TestCommonQuotas:
    """COMMON_QUOTAS 테스트"""

    def test_ec2_quotas(self):
        """EC2 쿼터 정의"""
        assert "ec2" in COMMON_QUOTAS
        assert "L-1216C47A" in COMMON_QUOTAS["ec2"]

    def test_lambda_quotas(self):
        """Lambda 쿼터 정의"""
        assert "lambda" in COMMON_QUOTAS
        assert "L-B99A9384" in COMMON_QUOTAS["lambda"]  # Concurrent executions

    def test_iam_quotas(self):
        """IAM 쿼터 정의"""
        assert "iam" in COMMON_QUOTAS
        assert "L-F4A5425F" in COMMON_QUOTAS["iam"]  # Roles
