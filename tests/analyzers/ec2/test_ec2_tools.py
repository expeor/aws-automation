"""
tests/analyzers/ec2/test_ec2_tools.py - EC2 Analyzer Tools 테스트

EC2 관련 도구의 유틸리티 함수 및 데이터 변환 로직 테스트
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_aws

from analyzers.ec2.ami_audit import (
    RECENT_DAYS,
    AMIFinding,
    AMIInfo,
    Severity,
    UsageStatus,
    _analyze_single_ami,
    analyze_amis,
)
from analyzers.ec2.eip_audit import (
    EIPFinding,
    EIPInfo,
    _analyze_single_eip,
    analyze_eips,
)
from analyzers.ec2.eip_audit import Severity as EIPSeverity
from analyzers.ec2.eip_audit import UsageStatus as EIPUsageStatus
from analyzers.ec2.unused import (
    EC2AnalysisResult,
    EC2InstanceInfo,
    InstanceFinding,
    InstanceStatus,
    analyze_instances,
)


class TestAMIAnalysis:
    """AMI 분석 테스트"""

    def test_ami_info_age_calculation(self):
        """AMI 나이 계산 테스트"""
        # 30일 전 생성
        creation_date = datetime.now(timezone.utc) - timedelta(days=30)
        ami = AMIInfo(
            id="ami-123",
            name="test-ami",
            description="test",
            state="available",
            architecture="x86_64",
            platform="Linux/UNIX",
            root_device_type="ebs",
            creation_date=creation_date,
            owner_id="123456789012",
            public=False,
            tags={},
            snapshot_ids=["snap-123"],
            total_size_gb=50,
        )

        assert ami.age_days == 30

    def test_ami_info_is_used(self):
        """AMI 사용 여부 테스트"""
        ami = AMIInfo(
            id="ami-123",
            name="test-ami",
            description="test",
            state="available",
            architecture="x86_64",
            platform="Linux/UNIX",
            root_device_type="ebs",
            creation_date=datetime.now(timezone.utc),
            owner_id="123456789012",
            public=False,
            tags={},
        )

        assert ami.is_used is False

        ami.used_by_instances = ["i-123", "i-456"]
        assert ami.is_used is True

    def test_ami_info_is_recent(self):
        """AMI 최근 생성 여부 테스트"""
        # 최근 생성 (7일 전)
        recent_ami = AMIInfo(
            id="ami-recent",
            name="recent",
            description="",
            state="available",
            architecture="x86_64",
            platform="Linux/UNIX",
            root_device_type="ebs",
            creation_date=datetime.now(timezone.utc) - timedelta(days=7),
            owner_id="123456789012",
            public=False,
            tags={},
        )
        assert recent_ami.is_recent is True

        # 오래된 AMI (20일 전)
        old_ami = AMIInfo(
            id="ami-old",
            name="old",
            description="",
            state="available",
            architecture="x86_64",
            platform="Linux/UNIX",
            root_device_type="ebs",
            creation_date=datetime.now(timezone.utc) - timedelta(days=20),
            owner_id="123456789012",
            public=False,
            tags={},
        )
        assert old_ami.is_recent is False

    def test_analyze_single_ami_in_use(self):
        """사용 중인 AMI 분석"""
        ami = AMIInfo(
            id="ami-123",
            name="in-use-ami",
            description="",
            state="available",
            architecture="x86_64",
            platform="Linux/UNIX",
            root_device_type="ebs",
            creation_date=datetime.now(timezone.utc) - timedelta(days=30),
            owner_id="123456789012",
            public=False,
            tags={},
            used_by_instances=["i-123"],
        )

        finding = _analyze_single_ami(ami)

        assert finding.usage_status == UsageStatus.NORMAL
        assert finding.severity == Severity.INFO
        assert "사용 중" in finding.description

    def test_analyze_single_ami_recent(self):
        """최근 생성 AMI 분석"""
        ami = AMIInfo(
            id="ami-recent",
            name="recent-ami",
            description="",
            state="available",
            architecture="x86_64",
            platform="Linux/UNIX",
            root_device_type="ebs",
            creation_date=datetime.now(timezone.utc) - timedelta(days=7),
            owner_id="123456789012",
            public=False,
            tags={},
            used_by_instances=[],
        )

        finding = _analyze_single_ami(ami)

        assert finding.usage_status == UsageStatus.NORMAL
        assert finding.severity == Severity.INFO
        assert "최근 생성" in finding.description

    def test_analyze_single_ami_unused_small(self):
        """미사용 소형 AMI (50GB 미만)"""
        ami = AMIInfo(
            id="ami-unused",
            name="unused-ami",
            description="",
            state="available",
            architecture="x86_64",
            platform="Linux/UNIX",
            root_device_type="ebs",
            creation_date=datetime.now(timezone.utc) - timedelta(days=30),
            owner_id="123456789012",
            public=False,
            tags={},
            total_size_gb=30,
            monthly_cost=1.5,
        )

        finding = _analyze_single_ami(ami)

        assert finding.usage_status == UsageStatus.UNUSED
        assert finding.severity == Severity.LOW

    def test_analyze_single_ami_unused_medium(self):
        """미사용 중형 AMI (50-100GB)"""
        ami = AMIInfo(
            id="ami-unused",
            name="unused-ami",
            description="",
            state="available",
            architecture="x86_64",
            platform="Linux/UNIX",
            root_device_type="ebs",
            creation_date=datetime.now(timezone.utc) - timedelta(days=30),
            owner_id="123456789012",
            public=False,
            tags={},
            total_size_gb=75,
            monthly_cost=3.75,
        )

        finding = _analyze_single_ami(ami)

        assert finding.usage_status == UsageStatus.UNUSED
        assert finding.severity == Severity.MEDIUM

    def test_analyze_single_ami_unused_large(self):
        """미사용 대형 AMI (100GB 이상)"""
        ami = AMIInfo(
            id="ami-unused",
            name="unused-ami",
            description="",
            state="available",
            architecture="x86_64",
            platform="Linux/UNIX",
            root_device_type="ebs",
            creation_date=datetime.now(timezone.utc) - timedelta(days=30),
            owner_id="123456789012",
            public=False,
            tags={},
            total_size_gb=200,
            monthly_cost=10.0,
        )

        finding = _analyze_single_ami(ami)

        assert finding.usage_status == UsageStatus.UNUSED
        assert finding.severity == Severity.HIGH

    def test_analyze_amis_summary(self):
        """AMI 분석 종합 테스트"""
        amis = [
            AMIInfo(
                id="ami-1",
                name="in-use",
                description="",
                state="available",
                architecture="x86_64",
                platform="Linux/UNIX",
                root_device_type="ebs",
                creation_date=datetime.now(timezone.utc) - timedelta(days=30),
                owner_id="123456789012",
                public=False,
                tags={},
                total_size_gb=50,
                monthly_cost=2.5,
            ),
            AMIInfo(
                id="ami-2",
                name="unused",
                description="",
                state="available",
                architecture="x86_64",
                platform="Linux/UNIX",
                root_device_type="ebs",
                creation_date=datetime.now(timezone.utc) - timedelta(days=60),
                owner_id="123456789012",
                public=False,
                tags={},
                total_size_gb=100,
                monthly_cost=5.0,
            ),
            AMIInfo(
                id="ami-3",
                name="recent",
                description="",
                state="available",
                architecture="x86_64",
                platform="Linux/UNIX",
                root_device_type="ebs",
                creation_date=datetime.now(timezone.utc) - timedelta(days=7),
                owner_id="123456789012",
                public=False,
                tags={},
                total_size_gb=30,
                monthly_cost=1.5,
            ),
        ]

        used_ami_ids = {"ami-1"}
        result = analyze_amis(amis, used_ami_ids, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_count == 3
        assert result.normal_count == 2  # ami-1 (used) + ami-3 (recent)
        assert result.unused_count == 1  # ami-2 (unused)
        assert result.total_size_gb == 180
        assert result.unused_size_gb == 100
        assert result.unused_monthly_cost == 5.0


class TestEIPAnalysis:
    """EIP 분석 테스트"""

    def test_eip_info_is_associated(self):
        """EIP 연결 여부 테스트"""
        # 연결됨
        eip_associated = EIPInfo(
            allocation_id="eipalloc-123",
            public_ip="1.2.3.4",
            domain="vpc",
            instance_id="i-123",
            association_id="eipassoc-456",
            network_interface_id="eni-123",
            private_ip="10.0.0.1",
            network_border_group="ap-northeast-2",
            tags={},
            name="test-eip",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert eip_associated.is_associated is True

        # 미연결
        eip_unassociated = EIPInfo(
            allocation_id="eipalloc-456",
            public_ip="5.6.7.8",
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
        assert eip_unassociated.is_associated is False

    def test_analyze_single_eip_associated(self):
        """연결된 EIP 분석"""
        eip = EIPInfo(
            allocation_id="eipalloc-123",
            public_ip="1.2.3.4",
            domain="vpc",
            instance_id="i-123",
            association_id="eipassoc-456",
            network_interface_id="eni-123",
            private_ip="10.0.0.1",
            network_border_group="ap-northeast-2",
            tags={},
            name="test-eip",
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_eip(eip)

        assert finding.usage_status == EIPUsageStatus.NORMAL
        assert finding.severity == EIPSeverity.INFO
        assert "사용 중" in finding.description

    def test_analyze_single_eip_unused(self):
        """미연결 EIP 분석"""
        eip = EIPInfo(
            allocation_id="eipalloc-456",
            public_ip="5.6.7.8",
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
            monthly_cost=3.6,
        )

        finding = _analyze_single_eip(eip)

        assert finding.usage_status == EIPUsageStatus.UNUSED
        assert finding.severity == EIPSeverity.HIGH
        assert "미연결" in finding.description

    def test_analyze_eips_summary(self):
        """EIP 분석 종합 테스트"""
        eips = [
            EIPInfo(
                allocation_id="eipalloc-1",
                public_ip="1.2.3.4",
                domain="vpc",
                instance_id="i-123",
                association_id="eipassoc-1",
                network_interface_id="eni-123",
                private_ip="10.0.0.1",
                network_border_group="ap-northeast-2",
                tags={},
                name="used-eip",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
            ),
            EIPInfo(
                allocation_id="eipalloc-2",
                public_ip="5.6.7.8",
                domain="vpc",
                instance_id="",
                association_id="",
                network_interface_id="",
                private_ip="",
                network_border_group="ap-northeast-2",
                tags={},
                name="unused-eip-1",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                monthly_cost=3.6,
            ),
            EIPInfo(
                allocation_id="eipalloc-3",
                public_ip="9.10.11.12",
                domain="vpc",
                instance_id="",
                association_id="",
                network_interface_id="",
                private_ip="",
                network_border_group="ap-northeast-2",
                tags={},
                name="unused-eip-2",
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                monthly_cost=3.6,
            ),
        ]

        result = analyze_eips(eips, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_count == 3
        assert result.normal_count == 1
        assert result.unused_count == 2
        assert result.unused_monthly_cost == 7.2


class TestEC2UnusedAnalysis:
    """EC2 미사용 분석 테스트"""

    def test_instance_info_estimated_monthly_cost(self):
        """인스턴스 비용 추정 테스트"""
        with patch("analyzers.ec2.unused.get_ec2_monthly_cost", return_value=50.0):
            # Linux 인스턴스
            linux_instance = EC2InstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                instance_id="i-123",
                instance_type="t3.large",
                state="running",
                name="linux-instance",
                launch_time=datetime.now(timezone.utc),
                platform="linux",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                private_ip="10.0.0.1",
                public_ip="1.2.3.4",
            )
            assert linux_instance.estimated_monthly_cost == 50.0

            # Windows 인스턴스 (1.5배)
            windows_instance = EC2InstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                instance_id="i-456",
                instance_type="t3.large",
                state="running",
                name="windows-instance",
                launch_time=datetime.now(timezone.utc),
                platform="windows",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                private_ip="10.0.0.2",
                public_ip="5.6.7.8",
            )
            assert windows_instance.estimated_monthly_cost == 75.0

    def test_instance_info_age_days(self):
        """인스턴스 생성 경과 일수 테스트"""
        launch_time = datetime.now(timezone.utc) - timedelta(days=45)
        instance = EC2InstanceInfo(
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
            instance_id="i-123",
            instance_type="t3.medium",
            state="running",
            name="test-instance",
            launch_time=launch_time,
            platform="linux",
            vpc_id="vpc-123",
            subnet_id="subnet-123",
            private_ip="10.0.0.1",
            public_ip="",
        )

        assert instance.age_days == 45

    def test_analyze_instances_stopped(self):
        """정지된 인스턴스 분석"""
        instances = [
            EC2InstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                instance_id="i-stopped",
                instance_type="t3.medium",
                state="stopped",
                name="stopped-instance",
                launch_time=datetime.now(timezone.utc) - timedelta(days=30),
                platform="linux",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                private_ip="10.0.0.1",
                public_ip="",
            )
        ]

        with patch("analyzers.ec2.unused.get_ec2_monthly_cost", return_value=30.0):
            result = analyze_instances(instances, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_instances == 1
        assert result.stopped_instances == 1
        assert result.stopped_monthly_cost == 30.0

    def test_analyze_instances_unused(self):
        """미사용 인스턴스 분석 (CPU < 2%, 네트워크 < 5MB, Disk < 100 ops)"""
        instances = [
            EC2InstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                instance_id="i-unused",
                instance_type="t3.medium",
                state="running",
                name="unused-instance",
                launch_time=datetime.now(timezone.utc),
                platform="linux",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                private_ip="10.0.0.1",
                public_ip="",
                avg_cpu=1.5,  # < 2%
                total_network_in=1024 * 1024,  # 1MB
                total_network_out=1024 * 1024,  # 1MB
                total_disk_read_ops=10,  # < 100
                total_disk_write_ops=10,  # < 100
            )
        ]

        with patch("analyzers.ec2.unused.get_ec2_monthly_cost", return_value=30.0):
            result = analyze_instances(instances, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_instances == 1
        assert result.unused_instances == 1
        assert result.unused_monthly_cost == 30.0
        assert len(result.findings) == 1
        assert result.findings[0].status == InstanceStatus.UNUSED

    def test_analyze_instances_low_usage(self):
        """저사용 인스턴스 분석 (CPU < 10%)"""
        instances = [
            EC2InstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                instance_id="i-low",
                instance_type="t3.large",
                state="running",
                name="low-usage-instance",
                launch_time=datetime.now(timezone.utc),
                platform="linux",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                private_ip="10.0.0.1",
                public_ip="",
                avg_cpu=5.0,  # 2-10%
                total_network_in=10 * 1024 * 1024,  # 10MB
                total_network_out=10 * 1024 * 1024,  # 10MB
                total_disk_read_ops=500,
                total_disk_write_ops=500,
            )
        ]

        with patch("analyzers.ec2.unused.get_ec2_monthly_cost", return_value=50.0):
            result = analyze_instances(instances, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_instances == 1
        assert result.low_usage_instances == 1
        assert result.low_usage_monthly_cost == 50.0
        assert len(result.findings) == 1
        assert result.findings[0].status == InstanceStatus.LOW_USAGE

    def test_analyze_instances_normal(self):
        """정상 사용 인스턴스 분석 (CPU >= 10%)"""
        instances = [
            EC2InstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                instance_id="i-normal",
                instance_type="t3.xlarge",
                state="running",
                name="normal-instance",
                launch_time=datetime.now(timezone.utc),
                platform="linux",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                private_ip="10.0.0.1",
                public_ip="",
                avg_cpu=50.0,  # >= 10%
                total_network_in=100 * 1024 * 1024,  # 100MB
                total_network_out=100 * 1024 * 1024,  # 100MB
                total_disk_read_ops=5000,
                total_disk_write_ops=5000,
            )
        ]

        with patch("analyzers.ec2.unused.get_ec2_monthly_cost", return_value=100.0):
            result = analyze_instances(instances, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_instances == 1
        assert result.normal_instances == 1
        assert len(result.findings) == 1
        assert result.findings[0].status == InstanceStatus.NORMAL

    def test_analyze_instances_mixed(self):
        """혼합 인스턴스 분석"""
        instances = [
            EC2InstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                instance_id="i-stopped",
                instance_type="t3.small",
                state="stopped",
                name="stopped",
                launch_time=datetime.now(timezone.utc) - timedelta(days=30),
                platform="linux",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                private_ip="10.0.0.1",
                public_ip="",
            ),
            EC2InstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                instance_id="i-unused",
                instance_type="t3.medium",
                state="running",
                name="unused",
                launch_time=datetime.now(timezone.utc),
                platform="linux",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                private_ip="10.0.0.2",
                public_ip="",
                avg_cpu=1.0,
                total_network_in=1024 * 1024,
                total_network_out=1024 * 1024,
                total_disk_read_ops=40,
                total_disk_write_ops=40,
            ),
            EC2InstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                instance_id="i-low",
                instance_type="t3.large",
                state="running",
                name="low",
                launch_time=datetime.now(timezone.utc),
                platform="linux",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                private_ip="10.0.0.3",
                public_ip="",
                avg_cpu=7.0,
                total_network_in=50 * 1024 * 1024,
                total_network_out=50 * 1024 * 1024,
                total_disk_read_ops=1000,
                total_disk_write_ops=1000,
            ),
            EC2InstanceInfo(
                account_id="123456789012",
                account_name="test",
                region="ap-northeast-2",
                instance_id="i-normal",
                instance_type="t3.xlarge",
                state="running",
                name="normal",
                launch_time=datetime.now(timezone.utc),
                platform="linux",
                vpc_id="vpc-123",
                subnet_id="subnet-123",
                private_ip="10.0.0.4",
                public_ip="",
                avg_cpu=60.0,
                total_network_in=500 * 1024 * 1024,
                total_network_out=500 * 1024 * 1024,
                total_disk_read_ops=10000,
                total_disk_write_ops=10000,
            ),
        ]

        with patch("analyzers.ec2.unused.get_ec2_monthly_cost", return_value=50.0):
            result = analyze_instances(instances, "123456789012", "test-account", "ap-northeast-2")

        assert result.total_instances == 4
        assert result.stopped_instances == 1
        assert result.unused_instances == 1
        assert result.low_usage_instances == 1
        assert result.normal_instances == 1
        # All instances get the same mocked cost
        assert result.stopped_monthly_cost == 50.0
        assert result.unused_monthly_cost == 50.0
        assert result.low_usage_monthly_cost == 50.0
