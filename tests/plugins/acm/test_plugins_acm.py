"""
tests/test_plugins_acm.py - ACM 플러그인 테스트
"""

from datetime import datetime, timedelta, timezone

import pytest

from plugins.acm.unused import (
    ACMAnalysisResult,
    CertFinding,
    CertInfo,
    CertStatus,
    EXPIRING_DAYS_THRESHOLD,
    analyze_certificates,
)


class TestCertInfo:
    """CertInfo 데이터클래스 테스트"""

    def test_is_in_use_true(self):
        """사용 중인 인증서"""
        cert = CertInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            certificate_arn="arn:aws:acm:ap-northeast-2:123:certificate/abc",
            domain_name="example.com",
            status="ISSUED",
            cert_type="AMAZON_ISSUED",
            key_algorithm="RSA_2048",
            in_use_by=["arn:aws:elasticloadbalancing:..."],
            not_before=datetime.now(timezone.utc) - timedelta(days=30),
            not_after=datetime.now(timezone.utc) + timedelta(days=335),
            renewal_eligibility="ELIGIBLE",
        )
        assert cert.is_in_use is True

    def test_is_in_use_false(self):
        """미사용 인증서"""
        cert = CertInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            certificate_arn="arn",
            domain_name="example.com",
            status="ISSUED",
            cert_type="AMAZON_ISSUED",
            key_algorithm="RSA_2048",
            in_use_by=[],
            not_before=datetime.now(timezone.utc),
            not_after=datetime.now(timezone.utc) + timedelta(days=365),
            renewal_eligibility="ELIGIBLE",
        )
        assert cert.is_in_use is False

    def test_days_until_expiry(self):
        """만료까지 남은 일수"""
        expiry = datetime.now(timezone.utc) + timedelta(days=30)
        cert = CertInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            certificate_arn="arn",
            domain_name="example.com",
            status="ISSUED",
            cert_type="AMAZON_ISSUED",
            key_algorithm="RSA_2048",
            in_use_by=[],
            not_before=datetime.now(timezone.utc),
            not_after=expiry,
            renewal_eligibility="ELIGIBLE",
        )
        # 시간 계산 오차 허용 (29~30일)
        assert 29 <= cert.days_until_expiry <= 30

    def test_days_until_expiry_none(self):
        """만료일 없음"""
        cert = CertInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            certificate_arn="arn",
            domain_name="example.com",
            status="PENDING_VALIDATION",
            cert_type="AMAZON_ISSUED",
            key_algorithm="RSA_2048",
            in_use_by=[],
            not_before=None,
            not_after=None,
            renewal_eligibility="",
        )
        assert cert.days_until_expiry is None


class TestCertStatus:
    """CertStatus Enum 테스트"""

    def test_status_values(self):
        """상태 값 확인"""
        assert CertStatus.NORMAL.value == "normal"
        assert CertStatus.UNUSED.value == "unused"
        assert CertStatus.EXPIRING.value == "expiring"
        assert CertStatus.EXPIRED.value == "expired"
        assert CertStatus.PENDING.value == "pending"


class TestAnalyzeCertificates:
    """analyze_certificates 테스트"""

    def test_pending_validation_cert(self):
        """검증 대기 중 인증서"""
        certs = [
            CertInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                certificate_arn="arn",
                domain_name="pending.example.com",
                status="PENDING_VALIDATION",
                cert_type="AMAZON_ISSUED",
                key_algorithm="RSA_2048",
                in_use_by=[],
                not_before=None,
                not_after=None,
                renewal_eligibility="",
            )
        ]

        result = analyze_certificates(certs, "123456789012", "test", "ap-northeast-2")

        assert result.pending_certs == 1
        assert result.findings[0].status == CertStatus.PENDING

    def test_expired_cert(self):
        """만료된 인증서"""
        certs = [
            CertInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                certificate_arn="arn",
                domain_name="expired.example.com",
                status="EXPIRED",
                cert_type="AMAZON_ISSUED",
                key_algorithm="RSA_2048",
                in_use_by=[],
                not_before=datetime.now(timezone.utc) - timedelta(days=400),
                not_after=datetime.now(timezone.utc) - timedelta(days=35),
                renewal_eligibility="INELIGIBLE",
            )
        ]

        result = analyze_certificates(certs, "123456789012", "test", "ap-northeast-2")

        assert result.expired_certs == 1
        assert result.findings[0].status == CertStatus.EXPIRED

    def test_expiring_cert(self):
        """만료 임박 인증서"""
        certs = [
            CertInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                certificate_arn="arn",
                domain_name="expiring.example.com",
                status="ISSUED",
                cert_type="AMAZON_ISSUED",
                key_algorithm="RSA_2048",
                in_use_by=["arn:aws:elb:..."],
                not_before=datetime.now(timezone.utc) - timedelta(days=335),
                not_after=datetime.now(timezone.utc) + timedelta(days=15),  # 15일 남음
                renewal_eligibility="ELIGIBLE",
            )
        ]

        result = analyze_certificates(certs, "123456789012", "test", "ap-northeast-2")

        assert result.expiring_certs == 1
        assert result.findings[0].status == CertStatus.EXPIRING

    def test_unused_cert(self):
        """미사용 인증서"""
        certs = [
            CertInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                certificate_arn="arn",
                domain_name="unused.example.com",
                status="ISSUED",
                cert_type="AMAZON_ISSUED",
                key_algorithm="RSA_2048",
                in_use_by=[],  # 사용 안 함
                not_before=datetime.now(timezone.utc) - timedelta(days=30),
                not_after=datetime.now(timezone.utc) + timedelta(days=335),
                renewal_eligibility="ELIGIBLE",
            )
        ]

        result = analyze_certificates(certs, "123456789012", "test", "ap-northeast-2")

        assert result.unused_certs == 1
        assert result.findings[0].status == CertStatus.UNUSED

    def test_normal_cert(self):
        """정상 인증서"""
        certs = [
            CertInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                certificate_arn="arn",
                domain_name="normal.example.com",
                status="ISSUED",
                cert_type="AMAZON_ISSUED",
                key_algorithm="RSA_2048",
                in_use_by=["arn:aws:elb:..."],
                not_before=datetime.now(timezone.utc) - timedelta(days=30),
                not_after=datetime.now(timezone.utc) + timedelta(days=335),
                renewal_eligibility="ELIGIBLE",
            )
        ]

        result = analyze_certificates(certs, "123456789012", "test", "ap-northeast-2")

        assert result.normal_certs == 1
        assert result.findings[0].status == CertStatus.NORMAL

    def test_mixed_certs(self):
        """혼합 인증서 분석"""
        now = datetime.now(timezone.utc)
        certs = [
            CertInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                certificate_arn="arn1",
                domain_name="normal.example.com",
                status="ISSUED",
                cert_type="AMAZON_ISSUED",
                key_algorithm="RSA_2048",
                in_use_by=["elb1"],
                not_before=now - timedelta(days=30),
                not_after=now + timedelta(days=335),
                renewal_eligibility="ELIGIBLE",
            ),
            CertInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                certificate_arn="arn2",
                domain_name="unused.example.com",
                status="ISSUED",
                cert_type="AMAZON_ISSUED",
                key_algorithm="RSA_2048",
                in_use_by=[],
                not_before=now - timedelta(days=30),
                not_after=now + timedelta(days=335),
                renewal_eligibility="ELIGIBLE",
            ),
            CertInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                certificate_arn="arn3",
                domain_name="expiring.example.com",
                status="ISSUED",
                cert_type="AMAZON_ISSUED",
                key_algorithm="RSA_2048",
                in_use_by=["elb2"],
                not_before=now - timedelta(days=350),
                not_after=now + timedelta(days=15),
                renewal_eligibility="ELIGIBLE",
            ),
        ]

        result = analyze_certificates(certs, "123456789012", "test", "ap-northeast-2")

        assert result.total_certs == 3
        assert result.normal_certs == 1
        assert result.unused_certs == 1
        assert result.expiring_certs == 1


class TestACMAnalysisResult:
    """ACMAnalysisResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        result = ACMAnalysisResult(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert result.total_certs == 0
        assert result.unused_certs == 0
        assert result.expiring_certs == 0
        assert result.expired_certs == 0
        assert result.pending_certs == 0
        assert result.normal_certs == 0
        assert result.findings == []
