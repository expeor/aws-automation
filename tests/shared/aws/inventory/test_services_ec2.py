"""
tests/shared/aws/inventory/test_services_ec2.py - EC2 서비스 수집기 테스트

EC2 및 Security Group 수집 함수를 직접 테스트합니다.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from core.shared.aws.inventory.services.ec2 import (
    _populate_sg_attachments,
    collect_ec2_instances,
    collect_security_groups,
)
from core.shared.aws.inventory.types import SecurityGroup


class TestCollectEC2Instances:
    """collect_ec2_instances 함수 테스트"""

    def test_collect_basic_instance(self, mock_boto3_session):
        """기본 EC2 인스턴스 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        # Mock 응답 데이터
        mock_response = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-1234567890abcdef0",
                            "InstanceType": "t3.micro",
                            "State": {"Name": "running"},
                            "PrivateIpAddress": "10.0.0.1",
                            "PublicIpAddress": "54.123.45.67",
                            "VpcId": "vpc-12345678",
                            "PlatformDetails": "Linux/UNIX",
                            "SubnetId": "subnet-12345678",
                            "Placement": {"AvailabilityZone": "ap-northeast-2a"},
                            "LaunchTime": datetime(2024, 1, 1, 0, 0, 0),
                            "Tags": [{"Key": "Name", "Value": "web-server"}],
                            "BlockDeviceMappings": [],
                            "SecurityGroups": [],
                        }
                    ]
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.get_client", return_value=mock_ec2):
            instances = collect_ec2_instances(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(instances) == 1
        assert instances[0].instance_id == "i-1234567890abcdef0"
        assert instances[0].name == "web-server"
        assert instances[0].instance_type == "t3.micro"
        assert instances[0].state == "running"
        assert instances[0].private_ip == "10.0.0.1"
        assert instances[0].public_ip == "54.123.45.67"

    def test_collect_instance_with_ebs_volumes(self, mock_boto3_session):
        """EBS Volume이 연결된 인스턴스"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-1234567890abcdef0",
                            "InstanceType": "t3.micro",
                            "State": {"Name": "running"},
                            "PrivateIpAddress": "10.0.0.1",
                            "VpcId": "vpc-12345678",
                            "PlatformDetails": "Linux/UNIX",
                            "Tags": [],
                            "BlockDeviceMappings": [
                                {
                                    "DeviceName": "/dev/xvda",
                                    "Ebs": {"VolumeId": "vol-12345678"},
                                },
                                {
                                    "DeviceName": "/dev/xvdb",
                                    "Ebs": {"VolumeId": "vol-87654321"},
                                },
                            ],
                            "SecurityGroups": [],
                        }
                    ]
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.get_client", return_value=mock_ec2):
            instances = collect_ec2_instances(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(instances[0].ebs_volume_ids) == 2
        assert "vol-12345678" in instances[0].ebs_volume_ids
        assert "vol-87654321" in instances[0].ebs_volume_ids

    def test_collect_instance_with_security_groups(self, mock_boto3_session):
        """Security Group이 연결된 인스턴스"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-1234567890abcdef0",
                            "InstanceType": "t3.micro",
                            "State": {"Name": "running"},
                            "PrivateIpAddress": "10.0.0.1",
                            "VpcId": "vpc-12345678",
                            "PlatformDetails": "Linux/UNIX",
                            "Tags": [],
                            "BlockDeviceMappings": [],
                            "SecurityGroups": [
                                {"GroupId": "sg-12345678"},
                                {"GroupId": "sg-87654321"},
                            ],
                        }
                    ]
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.get_client", return_value=mock_ec2):
            instances = collect_ec2_instances(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(instances[0].security_group_ids) == 2
        assert "sg-12345678" in instances[0].security_group_ids

    def test_collect_instance_with_iam_role(self, mock_boto3_session):
        """IAM Role이 연결된 인스턴스"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-1234567890abcdef0",
                            "InstanceType": "t3.micro",
                            "State": {"Name": "running"},
                            "PrivateIpAddress": "10.0.0.1",
                            "VpcId": "vpc-12345678",
                            "PlatformDetails": "Linux/UNIX",
                            "Tags": [],
                            "BlockDeviceMappings": [],
                            "SecurityGroups": [],
                            "IamInstanceProfile": {"Arn": "arn:aws:iam::123456789012:instance-profile/WebServerRole"},
                        }
                    ]
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.get_client", return_value=mock_ec2):
            instances = collect_ec2_instances(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert instances[0].iam_role == "WebServerRole"

    def test_collect_multiple_instances(self, mock_boto3_session):
        """여러 인스턴스 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-instance1",
                            "InstanceType": "t3.micro",
                            "State": {"Name": "running"},
                            "PrivateIpAddress": "10.0.0.1",
                            "VpcId": "vpc-12345678",
                            "PlatformDetails": "Linux/UNIX",
                            "Tags": [{"Key": "Name", "Value": "web-1"}],
                            "BlockDeviceMappings": [],
                            "SecurityGroups": [],
                        },
                        {
                            "InstanceId": "i-instance2",
                            "InstanceType": "t3.small",
                            "State": {"Name": "stopped"},
                            "PrivateIpAddress": "10.0.0.2",
                            "VpcId": "vpc-12345678",
                            "PlatformDetails": "Windows",
                            "Tags": [{"Key": "Name", "Value": "web-2"}],
                            "BlockDeviceMappings": [],
                            "SecurityGroups": [],
                        },
                    ]
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.get_client", return_value=mock_ec2):
            instances = collect_ec2_instances(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(instances) == 2
        assert instances[0].instance_id == "i-instance1"
        assert instances[1].instance_id == "i-instance2"
        assert instances[0].state == "running"
        assert instances[1].state == "stopped"

    def test_collect_empty_instances(self, mock_boto3_session):
        """인스턴스가 없는 경우"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {"Reservations": []}

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.get_client", return_value=mock_ec2):
            instances = collect_ec2_instances(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(instances) == 0


class TestCollectSecurityGroups:
    """collect_security_groups 함수 테스트"""

    def test_collect_basic_security_group(self, mock_boto3_session):
        """기본 Security Group 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "SecurityGroups": [
                {
                    "GroupId": "sg-12345678",
                    "GroupName": "web-sg",
                    "VpcId": "vpc-12345678",
                    "Description": "Web server security group",
                    "OwnerId": "123456789012",
                    "IpPermissions": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 80,
                            "ToPort": 80,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                    "IpPermissionsEgress": [
                        {
                            "IpProtocol": "-1",
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                    "Tags": [{"Key": "Name", "Value": "web-sg"}],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.get_client", return_value=mock_ec2):
            sgs = collect_security_groups(
                mock_boto3_session, "123456789012", "test-account", "ap-northeast-2", populate_attachments=False
            )

        assert len(sgs) == 1
        assert sgs[0].group_id == "sg-12345678"
        assert sgs[0].group_name == "web-sg"
        assert sgs[0].description == "Web server security group"
        assert sgs[0].has_public_access is True
        assert sgs[0].rule_count == 2  # 1 inbound + 1 outbound

    def test_collect_security_group_with_multiple_rules(self, mock_boto3_session):
        """여러 규칙이 있는 Security Group"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "SecurityGroups": [
                {
                    "GroupId": "sg-12345678",
                    "GroupName": "complex-sg",
                    "VpcId": "vpc-12345678",
                    "Description": "Complex security group",
                    "OwnerId": "123456789012",
                    "IpPermissions": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 22,
                            "ToPort": 22,
                            "IpRanges": [{"CidrIp": "10.0.0.0/8"}],
                        },
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 80,
                            "ToPort": 80,
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        },
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 443,
                            "ToPort": 443,
                            "UserIdGroupPairs": [{"GroupId": "sg-87654321"}],
                        },
                    ],
                    "IpPermissionsEgress": [
                        {
                            "IpProtocol": "-1",
                            "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                        }
                    ],
                    "Tags": [],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.get_client", return_value=mock_ec2):
            sgs = collect_security_groups(
                mock_boto3_session, "123456789012", "test-account", "ap-northeast-2", populate_attachments=False
            )

        # 3 inbound rules (1 + 1 + 1 sg ref) + 1 outbound = 4 total
        assert sgs[0].rule_count == 4
        assert sgs[0].has_public_access is True

    def test_collect_security_group_no_public_access(self, mock_boto3_session):
        """공개 접근이 없는 Security Group"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "SecurityGroups": [
                {
                    "GroupId": "sg-12345678",
                    "GroupName": "private-sg",
                    "VpcId": "vpc-12345678",
                    "Description": "Private security group",
                    "OwnerId": "123456789012",
                    "IpPermissions": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 22,
                            "ToPort": 22,
                            "IpRanges": [{"CidrIp": "10.0.0.0/8"}],
                        }
                    ],
                    "IpPermissionsEgress": [],
                    "Tags": [],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.get_client", return_value=mock_ec2):
            sgs = collect_security_groups(
                mock_boto3_session, "123456789012", "test-account", "ap-northeast-2", populate_attachments=False
            )

        assert sgs[0].has_public_access is False

    def test_collect_security_group_with_attachments(self, mock_boto3_session):
        """연결된 리소스 조회 포함"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        sg_response = {
            "SecurityGroups": [
                {
                    "GroupId": "sg-12345678",
                    "GroupName": "web-sg",
                    "VpcId": "vpc-12345678",
                    "Description": "Web server security group",
                    "OwnerId": "123456789012",
                    "IpPermissions": [],
                    "IpPermissionsEgress": [],
                    "Tags": [],
                }
            ]
        }

        eni_response = {
            "NetworkInterfaces": [
                {
                    "NetworkInterfaceId": "eni-12345678",
                    "Groups": [{"GroupId": "sg-12345678"}],
                    "Description": "Primary network interface",
                    "InterfaceType": "interface",
                    "Attachment": {
                        "InstanceId": "i-1234567890abcdef0",
                        "InstanceOwnerId": "123456789012",
                    },
                }
            ]
        }

        # 두 개의 paginator 설정
        sg_paginator = MagicMock()
        sg_paginator.paginate.return_value = [sg_response]

        eni_paginator = MagicMock()
        eni_paginator.paginate.return_value = [eni_response]

        def get_paginator_side_effect(operation_name):
            if operation_name == "describe_security_groups":
                return sg_paginator
            elif operation_name == "describe_network_interfaces":
                return eni_paginator
            raise ValueError(f"Unknown operation: {operation_name}")

        mock_ec2.get_paginator.side_effect = get_paginator_side_effect

        with patch("core.shared.aws.inventory.services.ec2.get_client", return_value=mock_ec2):
            sgs = collect_security_groups(
                mock_boto3_session, "123456789012", "test-account", "ap-northeast-2", populate_attachments=True
            )

        assert len(sgs[0].attached_enis) == 1
        assert "eni-12345678" in sgs[0].attached_enis

    def test_collect_multiple_security_groups(self, mock_boto3_session):
        """여러 Security Group 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "SecurityGroups": [
                {
                    "GroupId": "sg-12345678",
                    "GroupName": "web-sg",
                    "VpcId": "vpc-12345678",
                    "Description": "Web",
                    "OwnerId": "123456789012",
                    "IpPermissions": [],
                    "IpPermissionsEgress": [],
                    "Tags": [],
                },
                {
                    "GroupId": "sg-87654321",
                    "GroupName": "db-sg",
                    "VpcId": "vpc-12345678",
                    "Description": "Database",
                    "OwnerId": "123456789012",
                    "IpPermissions": [],
                    "IpPermissionsEgress": [],
                    "Tags": [],
                },
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.get_client", return_value=mock_ec2):
            sgs = collect_security_groups(
                mock_boto3_session, "123456789012", "test-account", "ap-northeast-2", populate_attachments=False
            )

        assert len(sgs) == 2
        assert sgs[0].group_id == "sg-12345678"
        assert sgs[1].group_id == "sg-87654321"


class TestPopulateSGAttachments:
    """_populate_sg_attachments 함수 테스트"""

    def test_populate_with_ec2_instance(self):
        """EC2 인스턴스에 연결된 SG"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        # Security Group 객체
        sg = SecurityGroup(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            group_id="sg-12345678",
            group_name="web-sg",
            vpc_id="vpc-12345678",
            description="Web SG",
        )

        # ENI 응답
        eni_response = {
            "NetworkInterfaces": [
                {
                    "NetworkInterfaceId": "eni-12345678",
                    "Groups": [{"GroupId": "sg-12345678"}],
                    "Description": "Primary network interface",
                    "InterfaceType": "interface",
                    "Attachment": {
                        "InstanceId": "i-1234567890abcdef0",
                        "InstanceOwnerId": "123456789012",
                    },
                }
            ]
        }

        mock_paginator.paginate.return_value = [eni_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.parse_eni_description") as mock_parse:
            mock_parse.return_value = Mock(
                resource_id="i-1234567890abcdef0",
                resource_name="",
                resource_type="EC2",
            )

            _populate_sg_attachments(mock_ec2, [sg])

        assert len(sg.attached_enis) == 1
        assert "eni-12345678" in sg.attached_enis
        assert len(sg.attached_resource_ids) == 1
        assert "i-1234567890abcdef0" in sg.attached_resource_ids

    def test_populate_with_multiple_enis(self):
        """여러 ENI에 연결된 SG"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        sg = SecurityGroup(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            group_id="sg-12345678",
            group_name="web-sg",
            vpc_id="vpc-12345678",
            description="Web SG",
        )

        eni_response = {
            "NetworkInterfaces": [
                {
                    "NetworkInterfaceId": "eni-12345678",
                    "Groups": [{"GroupId": "sg-12345678"}],
                    "Description": "Primary network interface",
                    "InterfaceType": "interface",
                },
                {
                    "NetworkInterfaceId": "eni-87654321",
                    "Groups": [{"GroupId": "sg-12345678"}],
                    "Description": "Secondary network interface",
                    "InterfaceType": "interface",
                },
            ]
        }

        mock_paginator.paginate.return_value = [eni_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("core.shared.aws.inventory.services.ec2.parse_eni_description", return_value=None):
            _populate_sg_attachments(mock_ec2, [sg])

        assert len(sg.attached_enis) == 2
        assert "eni-12345678" in sg.attached_enis
        assert "eni-87654321" in sg.attached_enis

    def test_populate_with_no_enis(self):
        """ENI가 연결되지 않은 SG"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        sg = SecurityGroup(
            account_id="123456789012",
            account_name="test-account",
            region="ap-northeast-2",
            group_id="sg-12345678",
            group_name="web-sg",
            vpc_id="vpc-12345678",
            description="Web SG",
        )

        eni_response = {"NetworkInterfaces": []}

        mock_paginator.paginate.return_value = [eni_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        _populate_sg_attachments(mock_ec2, [sg])

        assert len(sg.attached_enis) == 0
        assert len(sg.attached_resource_ids) == 0
