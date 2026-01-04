"""
tests/test_plugins_eip.py - EIP 플러그인 테스트
"""

from unittest.mock import patch

from moto import mock_aws

from plugins.ec2.eip_audit import (
    EIPInfo,
    Severity,
    UsageStatus,
    _analyze_single_eip,
    analyze_eips,
    collect_eips,
)


class TestEIPInfo:
    """EIPInfo 데이터클래스 테스트"""

    def test_is_associated_true(self):
        """연결된 EIP"""
        eip = EIPInfo(
            allocation_id="eipalloc-123",
            public_ip="1.2.3.4",
            domain="vpc",
            instance_id="i-123",
            association_id="eipassoc-123",
            network_interface_id="eni-123",
            private_ip="10.0.0.1",
            network_border_group="ap-northeast-2",
            tags={},
            name="test-eip",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert eip.is_associated is True

    def test_is_associated_false(self):
        """미연결 EIP"""
        eip = EIPInfo(
            allocation_id="eipalloc-123",
            public_ip="1.2.3.4",
            domain="vpc",
            instance_id="",
            association_id="",
            network_interface_id="",
            private_ip="",
            network_border_group="ap-northeast-2",
            tags={},
            name="test-eip",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert eip.is_associated is False


class TestAnalyzeSingleEIP:
    """개별 EIP 분석 테스트"""

    def test_associated_eip(self):
        """연결된 EIP = 정상"""
        eip = EIPInfo(
            allocation_id="eipalloc-123",
            public_ip="1.2.3.4",
            domain="vpc",
            instance_id="i-123",
            association_id="eipassoc-123",
            network_interface_id="eni-123",
            private_ip="10.0.0.1",
            network_border_group="ap-northeast-2",
            tags={},
            name="attached-eip",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_eip(eip)

        assert finding.usage_status == UsageStatus.NORMAL
        assert finding.severity == Severity.INFO
        assert "i-123" in finding.description

    def test_unassociated_eip(self):
        """미연결 EIP = 미사용"""
        eip = EIPInfo(
            allocation_id="eipalloc-123",
            public_ip="1.2.3.4",
            domain="vpc",
            instance_id="",
            association_id="",
            network_interface_id="",
            private_ip="",
            network_border_group="ap-northeast-2",
            tags={},
            name="unused-eip",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        with patch("plugins.ec2.eip_audit.get_eip_monthly_cost", return_value=3.60):
            finding = _analyze_single_eip(eip)

        assert finding.usage_status == UsageStatus.UNUSED
        assert finding.severity == Severity.HIGH
        assert "미연결" in finding.description

    def test_associated_to_eni_only(self):
        """ENI에만 연결된 EIP"""
        eip = EIPInfo(
            allocation_id="eipalloc-123",
            public_ip="1.2.3.4",
            domain="vpc",
            instance_id="",
            association_id="eipassoc-123",
            network_interface_id="eni-123",
            private_ip="10.0.0.1",
            network_border_group="ap-northeast-2",
            tags={},
            name="eni-eip",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_eip(eip)

        assert finding.usage_status == UsageStatus.NORMAL
        assert "eni-123" in finding.description


class TestAnalyzeEIPs:
    """EIP 분석 결과 테스트"""

    def test_analyze_mixed_eips(self):
        """혼합 EIP 분석"""
        eips = [
            EIPInfo(
                allocation_id="eipalloc-1",
                public_ip="1.1.1.1",
                domain="vpc",
                instance_id="i-1",
                association_id="eipassoc-1",
                network_interface_id="eni-1",
                private_ip="10.0.0.1",
                network_border_group="ap-northeast-2",
                tags={},
                name="attached",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                monthly_cost=0.0,
            ),
            EIPInfo(
                allocation_id="eipalloc-2",
                public_ip="2.2.2.2",
                domain="vpc",
                instance_id="",
                association_id="",
                network_interface_id="",
                private_ip="",
                network_border_group="ap-northeast-2",
                tags={},
                name="unused",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                monthly_cost=3.60,
            ),
        ]

        with patch("plugins.ec2.eip_audit.get_eip_monthly_cost", return_value=3.60):
            result = analyze_eips(eips, "123456789012", "test", "ap-northeast-2")

        assert result.total_count == 2
        assert result.normal_count == 1
        assert result.unused_count == 1
        assert result.unused_monthly_cost == 3.60


class TestCollectEIPs:
    """EIP 수집 테스트"""

    @mock_aws
    def test_collect_eips_with_moto(self):
        """moto로 EIP 수집 테스트"""
        import boto3

        # EIP 할당
        ec2 = boto3.client("ec2", region_name="ap-northeast-2")
        eip = ec2.allocate_address(Domain="vpc")

        # 태그 추가
        ec2.create_tags(
            Resources=[eip["AllocationId"]],
            Tags=[{"Key": "Name", "Value": "test-eip"}],
        )

        # 세션 모킹
        session = boto3.Session(region_name="ap-northeast-2")

        # 수집
        with patch("plugins.ec2.eip_audit.get_eip_monthly_cost", return_value=3.60):
            eips = collect_eips(session, "123456789012", "test", "ap-northeast-2")

        assert len(eips) == 1
        assert eips[0].name == "test-eip"
        assert eips[0].public_ip == eip["PublicIp"]
        assert eips[0].is_associated is False
