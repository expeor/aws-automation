"""
tests/test_plugins_route53.py - Route53 플러그인 테스트
"""

from unittest.mock import patch

from functions.analyzers.route53.empty_zone import (
    HostedZoneInfo,
    Route53AnalysisResult,
    ZoneStatus,
    analyze_hosted_zones,
)


class TestHostedZoneInfo:
    """HostedZoneInfo 데이터클래스 테스트"""

    @patch("functions.analyzers.route53.empty_zone.get_hosted_zone_price")
    def test_monthly_cost(self, mock_price):
        """월간 비용"""
        mock_price.return_value = 0.50
        zone = HostedZoneInfo(
            account_id="123456789012",
            account_name="test",
            zone_id="Z12345678",
            name="example.com.",
            is_private=False,
            record_count=10,
            comment="Test zone",
        )
        assert zone.monthly_cost == 0.50

    def test_default_values(self):
        """기본값 확인"""
        zone = HostedZoneInfo(
            account_id="123456789012",
            account_name="test",
            zone_id="Z12345678",
            name="example.com.",
            is_private=False,
            record_count=0,
            comment="",
        )
        assert zone.vpcs == []
        assert zone.has_real_records is False


class TestZoneStatus:
    """ZoneStatus Enum 테스트"""

    def test_status_values(self):
        """상태 값 확인"""
        assert ZoneStatus.NORMAL.value == "normal"
        assert ZoneStatus.EMPTY.value == "empty"
        assert ZoneStatus.NS_SOA_ONLY.value == "ns_soa_only"


class TestAnalyzeHostedZones:
    """analyze_hosted_zones 테스트"""

    @patch("functions.analyzers.route53.empty_zone.get_hosted_zone_price")
    def test_empty_zone(self, mock_price):
        """완전히 빈 Zone"""
        mock_price.return_value = 0.50
        zones = [
            HostedZoneInfo(
                account_id="123456789012",
                account_name="test",
                zone_id="Z123",
                name="empty.com.",
                is_private=False,
                record_count=0,
                comment="Empty zone",
            )
        ]

        result = analyze_hosted_zones(zones, "123456789012", "test")

        assert result.empty_zones == 1
        assert result.wasted_monthly_cost == 0.50
        assert result.findings[0].status == ZoneStatus.EMPTY

    @patch("functions.analyzers.route53.empty_zone.get_hosted_zone_price")
    def test_ns_soa_only_zone(self, mock_price):
        """NS/SOA만 있는 Zone"""
        mock_price.return_value = 0.50
        zones = [
            HostedZoneInfo(
                account_id="123456789012",
                account_name="test",
                zone_id="Z123",
                name="ns-only.com.",
                is_private=False,
                record_count=2,  # NS, SOA
                comment="NS/SOA only",
                has_real_records=False,
            )
        ]

        result = analyze_hosted_zones(zones, "123456789012", "test")

        assert result.ns_soa_only_zones == 1
        assert result.wasted_monthly_cost == 0.50
        assert result.findings[0].status == ZoneStatus.NS_SOA_ONLY

    @patch("functions.analyzers.route53.empty_zone.get_hosted_zone_price")
    def test_normal_zone(self, mock_price):
        """정상 Zone (레코드 있음)"""
        mock_price.return_value = 0.50
        zones = [
            HostedZoneInfo(
                account_id="123456789012",
                account_name="test",
                zone_id="Z123",
                name="active.com.",
                is_private=False,
                record_count=10,
                comment="Active zone",
                has_real_records=True,
            )
        ]

        result = analyze_hosted_zones(zones, "123456789012", "test")

        assert result.empty_zones == 0
        assert result.ns_soa_only_zones == 0
        assert result.findings[0].status == ZoneStatus.NORMAL

    @patch("functions.analyzers.route53.empty_zone.get_hosted_zone_price")
    def test_private_zone(self, mock_price):
        """Private Zone"""
        mock_price.return_value = 0.50
        zones = [
            HostedZoneInfo(
                account_id="123456789012",
                account_name="test",
                zone_id="Z123",
                name="internal.local.",
                is_private=True,
                record_count=5,
                comment="Private zone",
                has_real_records=True,
                vpcs=["ap-northeast-2:vpc-123"],
            )
        ]

        result = analyze_hosted_zones(zones, "123456789012", "test")

        assert result.private_zones == 1
        assert result.public_zones == 0

    @patch("functions.analyzers.route53.empty_zone.get_hosted_zone_price")
    def test_mixed_zones(self, mock_price):
        """혼합 Zone 분석"""
        mock_price.return_value = 0.50
        zones = [
            HostedZoneInfo(
                account_id="123456789012",
                account_name="test",
                zone_id="Z1",
                name="empty.com.",
                is_private=False,
                record_count=0,
                comment="",
            ),
            HostedZoneInfo(
                account_id="123456789012",
                account_name="test",
                zone_id="Z2",
                name="ns-only.com.",
                is_private=False,
                record_count=2,
                comment="",
                has_real_records=False,
            ),
            HostedZoneInfo(
                account_id="123456789012",
                account_name="test",
                zone_id="Z3",
                name="active.com.",
                is_private=True,
                record_count=10,
                comment="",
                has_real_records=True,
            ),
        ]

        result = analyze_hosted_zones(zones, "123456789012", "test")

        assert result.total_zones == 3
        assert result.empty_zones == 1
        assert result.ns_soa_only_zones == 1
        assert result.public_zones == 2
        assert result.private_zones == 1
        assert result.wasted_monthly_cost == 1.0  # 2 zones * $0.50


class TestRoute53AnalysisResult:
    """Route53AnalysisResult 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        result = Route53AnalysisResult(
            account_id="123456789012",
            account_name="test",
        )
        assert result.total_zones == 0
        assert result.empty_zones == 0
        assert result.ns_soa_only_zones == 0
        assert result.private_zones == 0
        assert result.public_zones == 0
        assert result.wasted_monthly_cost == 0.0
        assert result.findings == []
