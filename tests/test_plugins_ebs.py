"""
tests/test_plugins_ebs.py - EBS 플러그인 테스트
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from moto import mock_aws

from plugins.ec2.ebs_audit import (
    EBSInfo,
    EBSFinding,
    UsageStatus,
    Severity,
    collect_ebs,
    analyze_ebs,
    _analyze_single_volume,
)


class TestEBSInfo:
    """EBSInfo 데이터클래스 테스트"""

    def test_is_attached_true(self):
        """연결된 볼륨"""
        volume = EBSInfo(
            id="vol-123",
            name="test",
            state="in-use",
            volume_type="gp3",
            size_gb=100,
            iops=3000,
            throughput=125,
            encrypted=True,
            kms_key_id="",
            availability_zone="ap-northeast-2a",
            create_time=datetime.now(),
            snapshot_id="",
            attachments=[{"InstanceId": "i-123"}],
            tags={},
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert volume.is_attached is True
        assert volume.attached_instance_id == "i-123"

    def test_is_attached_false(self):
        """미연결 볼륨"""
        volume = EBSInfo(
            id="vol-123",
            name="test",
            state="available",
            volume_type="gp3",
            size_gb=100,
            iops=3000,
            throughput=125,
            encrypted=True,
            kms_key_id="",
            availability_zone="ap-northeast-2a",
            create_time=datetime.now(),
            snapshot_id="",
            attachments=[],
            tags={},
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )
        assert volume.is_attached is False
        assert volume.attached_instance_id == ""


class TestAnalyzeSingleVolume:
    """개별 볼륨 분석 테스트"""

    def test_attached_volume(self):
        """연결된 볼륨 = 정상"""
        volume = EBSInfo(
            id="vol-123",
            name="attached",
            state="in-use",
            volume_type="gp3",
            size_gb=100,
            iops=3000,
            throughput=125,
            encrypted=True,
            kms_key_id="",
            availability_zone="ap-northeast-2a",
            create_time=datetime.now(),
            snapshot_id="",
            attachments=[{"InstanceId": "i-123"}],
            tags={},
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_volume(volume)

        assert finding.usage_status == UsageStatus.NORMAL
        assert finding.severity == Severity.INFO

    def test_available_volume_small(self):
        """미사용 소형 볼륨"""
        volume = EBSInfo(
            id="vol-123",
            name="unused",
            state="available",
            volume_type="gp3",
            size_gb=50,
            iops=3000,
            throughput=125,
            encrypted=True,
            kms_key_id="",
            availability_zone="ap-northeast-2a",
            create_time=datetime.now(),
            snapshot_id="",
            attachments=[],
            tags={},
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_volume(volume)

        assert finding.usage_status == UsageStatus.UNUSED
        assert finding.severity == Severity.LOW

    def test_available_volume_medium(self):
        """미사용 중형 볼륨 (100GB+)"""
        volume = EBSInfo(
            id="vol-123",
            name="unused",
            state="available",
            volume_type="gp3",
            size_gb=200,
            iops=3000,
            throughput=125,
            encrypted=True,
            kms_key_id="",
            availability_zone="ap-northeast-2a",
            create_time=datetime.now(),
            snapshot_id="",
            attachments=[],
            tags={},
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_volume(volume)

        assert finding.usage_status == UsageStatus.UNUSED
        assert finding.severity == Severity.MEDIUM

    def test_available_volume_large(self):
        """미사용 대형 볼륨 (500GB+)"""
        volume = EBSInfo(
            id="vol-123",
            name="unused",
            state="available",
            volume_type="gp3",
            size_gb=1000,
            iops=3000,
            throughput=125,
            encrypted=True,
            kms_key_id="",
            availability_zone="ap-northeast-2a",
            create_time=datetime.now(),
            snapshot_id="",
            attachments=[],
            tags={},
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_volume(volume)

        assert finding.usage_status == UsageStatus.UNUSED
        assert finding.severity == Severity.HIGH

    def test_pending_volume(self):
        """기타 상태 볼륨"""
        volume = EBSInfo(
            id="vol-123",
            name="creating",
            state="creating",
            volume_type="gp3",
            size_gb=100,
            iops=3000,
            throughput=125,
            encrypted=True,
            kms_key_id="",
            availability_zone="ap-northeast-2a",
            create_time=datetime.now(),
            snapshot_id="",
            attachments=[],
            tags={},
            account_id="123456789012",
            account_name="test",
            region="ap-northeast-2",
        )

        finding = _analyze_single_volume(volume)

        assert finding.usage_status == UsageStatus.PENDING
        assert finding.severity == Severity.INFO


class TestAnalyzeEBS:
    """EBS 분석 결과 테스트"""

    def test_analyze_mixed_volumes(self):
        """혼합 볼륨 분석"""
        volumes = [
            EBSInfo(
                id="vol-1", name="in-use", state="in-use", volume_type="gp3",
                size_gb=100, iops=3000, throughput=125, encrypted=True,
                kms_key_id="", availability_zone="ap-northeast-2a",
                create_time=datetime.now(), snapshot_id="",
                attachments=[{"InstanceId": "i-1"}], tags={},
                account_id="123456789012", account_name="test", region="ap-northeast-2",
                monthly_cost=10.0,
            ),
            EBSInfo(
                id="vol-2", name="unused", state="available", volume_type="gp3",
                size_gb=200, iops=3000, throughput=125, encrypted=True,
                kms_key_id="", availability_zone="ap-northeast-2a",
                create_time=datetime.now(), snapshot_id="",
                attachments=[], tags={},
                account_id="123456789012", account_name="test", region="ap-northeast-2",
                monthly_cost=20.0,
            ),
            EBSInfo(
                id="vol-3", name="creating", state="creating", volume_type="gp3",
                size_gb=50, iops=3000, throughput=125, encrypted=True,
                kms_key_id="", availability_zone="ap-northeast-2a",
                create_time=datetime.now(), snapshot_id="",
                attachments=[], tags={},
                account_id="123456789012", account_name="test", region="ap-northeast-2",
                monthly_cost=5.0,
            ),
        ]

        result = analyze_ebs(volumes, "123456789012", "test", "ap-northeast-2")

        assert result.total_count == 3
        assert result.normal_count == 1
        assert result.unused_count == 1
        assert result.pending_count == 1
        assert result.unused_size_gb == 200
        assert result.unused_monthly_cost == 20.0


class TestCollectEBS:
    """EBS 수집 테스트"""

    @mock_aws
    def test_collect_ebs_with_moto(self):
        """moto로 EBS 수집 테스트"""
        import boto3

        # EC2 리소스 생성
        ec2 = boto3.client("ec2", region_name="ap-northeast-2")
        volume = ec2.create_volume(
            AvailabilityZone="ap-northeast-2a",
            Size=100,
            VolumeType="gp3",
            TagSpecifications=[
                {
                    "ResourceType": "volume",
                    "Tags": [{"Key": "Name", "Value": "test-volume"}],
                }
            ],
        )

        # 세션 모킹
        session = boto3.Session(region_name="ap-northeast-2")

        # 수집
        with patch("plugins.ec2.ebs_audit.get_ebs_monthly_cost", return_value=10.0):
            volumes = collect_ebs(session, "123456789012", "test", "ap-northeast-2")

        assert len(volumes) == 1
        assert volumes[0].name == "test-volume"
        assert volumes[0].size_gb == 100
        assert volumes[0].volume_type == "gp3"
        assert volumes[0].state == "available"
