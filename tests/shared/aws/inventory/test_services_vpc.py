"""
tests/shared/aws/inventory/test_services_vpc.py - VPC 서비스 수집기 테스트

VPC, Subnet, Route Table 등 네트워크 리소스 수집 함수를 테스트합니다.
"""

from unittest.mock import MagicMock, patch

from shared.aws.inventory.services.vpc import (
    collect_elastic_ips,
    collect_internet_gateways,
    collect_nat_gateways,
    collect_route_tables,
    collect_subnets,
    collect_vpcs,
)


class TestCollectVPCs:
    """collect_vpcs 함수 테스트"""

    def test_collect_basic_vpc(self, mock_boto3_session):
        """기본 VPC 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "Vpcs": [
                {
                    "VpcId": "vpc-12345678",
                    "CidrBlock": "10.0.0.0/16",
                    "State": "available",
                    "IsDefault": False,
                    "InstanceTenancy": "default",
                    "DhcpOptionsId": "dopt-12345678",
                    "Tags": [{"Key": "Name", "Value": "production-vpc"}],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            vpcs = collect_vpcs(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(vpcs) == 1
        assert vpcs[0].vpc_id == "vpc-12345678"
        assert vpcs[0].name == "production-vpc"
        assert vpcs[0].cidr_block == "10.0.0.0/16"
        assert vpcs[0].state == "available"
        assert vpcs[0].is_default is False

    def test_collect_default_vpc(self, mock_boto3_session):
        """기본 VPC 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "Vpcs": [
                {
                    "VpcId": "vpc-default",
                    "CidrBlock": "172.31.0.0/16",
                    "State": "available",
                    "IsDefault": True,
                    "InstanceTenancy": "default",
                    "DhcpOptionsId": "dopt-default",
                    "Tags": [],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            vpcs = collect_vpcs(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert vpcs[0].is_default is True
        assert vpcs[0].cidr_block == "172.31.0.0/16"

    def test_collect_multiple_vpcs(self, mock_boto3_session):
        """여러 VPC 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "Vpcs": [
                {
                    "VpcId": "vpc-prod",
                    "CidrBlock": "10.0.0.0/16",
                    "State": "available",
                    "IsDefault": False,
                    "Tags": [{"Key": "Name", "Value": "production"}],
                },
                {
                    "VpcId": "vpc-dev",
                    "CidrBlock": "10.1.0.0/16",
                    "State": "available",
                    "IsDefault": False,
                    "Tags": [{"Key": "Name", "Value": "development"}],
                },
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            vpcs = collect_vpcs(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(vpcs) == 2
        assert vpcs[0].vpc_id == "vpc-prod"
        assert vpcs[1].vpc_id == "vpc-dev"


class TestCollectSubnets:
    """collect_subnets 함수 테스트"""

    def test_collect_basic_subnet(self, mock_boto3_session):
        """기본 Subnet 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "Subnets": [
                {
                    "SubnetId": "subnet-12345678",
                    "VpcId": "vpc-12345678",
                    "CidrBlock": "10.0.1.0/24",
                    "AvailabilityZone": "ap-northeast-2a",
                    "State": "available",
                    "AvailableIpAddressCount": 251,
                    "MapPublicIpOnLaunch": True,
                    "DefaultForAz": False,
                    "Tags": [{"Key": "Name", "Value": "public-subnet-a"}],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            subnets = collect_subnets(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(subnets) == 1
        assert subnets[0].subnet_id == "subnet-12345678"
        assert subnets[0].name == "public-subnet-a"
        assert subnets[0].vpc_id == "vpc-12345678"
        assert subnets[0].cidr_block == "10.0.1.0/24"
        assert subnets[0].availability_zone == "ap-northeast-2a"
        assert subnets[0].available_ip_count == 251
        assert subnets[0].map_public_ip_on_launch is True

    def test_collect_private_subnet(self, mock_boto3_session):
        """Private Subnet 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "Subnets": [
                {
                    "SubnetId": "subnet-private",
                    "VpcId": "vpc-12345678",
                    "CidrBlock": "10.0.2.0/24",
                    "AvailabilityZone": "ap-northeast-2a",
                    "State": "available",
                    "AvailableIpAddressCount": 251,
                    "MapPublicIpOnLaunch": False,
                    "DefaultForAz": False,
                    "Tags": [{"Key": "Name", "Value": "private-subnet-a"}],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            subnets = collect_subnets(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert subnets[0].map_public_ip_on_launch is False

    def test_collect_multiple_subnets(self, mock_boto3_session):
        """여러 Subnet 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "Subnets": [
                {
                    "SubnetId": "subnet-1",
                    "VpcId": "vpc-12345678",
                    "CidrBlock": "10.0.1.0/24",
                    "AvailabilityZone": "ap-northeast-2a",
                    "State": "available",
                    "Tags": [{"Key": "Name", "Value": "subnet-a"}],
                },
                {
                    "SubnetId": "subnet-2",
                    "VpcId": "vpc-12345678",
                    "CidrBlock": "10.0.2.0/24",
                    "AvailabilityZone": "ap-northeast-2c",
                    "State": "available",
                    "Tags": [{"Key": "Name", "Value": "subnet-c"}],
                },
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            subnets = collect_subnets(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(subnets) == 2
        assert subnets[0].availability_zone == "ap-northeast-2a"
        assert subnets[1].availability_zone == "ap-northeast-2c"


class TestCollectRouteTables:
    """collect_route_tables 함수 테스트"""

    def test_collect_basic_route_table(self, mock_boto3_session):
        """기본 Route Table 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "RouteTables": [
                {
                    "RouteTableId": "rtb-12345678",
                    "VpcId": "vpc-12345678",
                    "Routes": [
                        {"DestinationCidrBlock": "10.0.0.0/16", "GatewayId": "local"},
                        {"DestinationCidrBlock": "0.0.0.0/0", "GatewayId": "igw-12345678"},
                    ],
                    "Associations": [
                        {
                            "RouteTableAssociationId": "rtbassoc-12345678",
                            "Main": False,
                            "SubnetId": "subnet-12345678",
                        }
                    ],
                    "Tags": [{"Key": "Name", "Value": "public-rt"}],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            route_tables = collect_route_tables(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(route_tables) == 1
        assert route_tables[0].route_table_id == "rtb-12345678"
        assert route_tables[0].name == "public-rt"
        assert route_tables[0].vpc_id == "vpc-12345678"
        assert route_tables[0].is_main is False
        assert route_tables[0].route_count == 2
        assert route_tables[0].association_count == 1
        assert "subnet-12345678" in route_tables[0].subnet_ids

    def test_collect_main_route_table(self, mock_boto3_session):
        """Main Route Table 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "RouteTables": [
                {
                    "RouteTableId": "rtb-main",
                    "VpcId": "vpc-12345678",
                    "Routes": [{"DestinationCidrBlock": "10.0.0.0/16", "GatewayId": "local"}],
                    "Associations": [
                        {
                            "RouteTableAssociationId": "rtbassoc-main",
                            "Main": True,
                        }
                    ],
                    "Tags": [],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            route_tables = collect_route_tables(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert route_tables[0].is_main is True

    def test_collect_route_table_with_multiple_subnets(self, mock_boto3_session):
        """여러 Subnet에 연결된 Route Table"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "RouteTables": [
                {
                    "RouteTableId": "rtb-12345678",
                    "VpcId": "vpc-12345678",
                    "Routes": [],
                    "Associations": [
                        {"Main": False, "SubnetId": "subnet-1"},
                        {"Main": False, "SubnetId": "subnet-2"},
                        {"Main": False, "SubnetId": "subnet-3"},
                    ],
                    "Tags": [],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            route_tables = collect_route_tables(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(route_tables[0].subnet_ids) == 3
        assert "subnet-1" in route_tables[0].subnet_ids
        assert route_tables[0].association_count == 3


class TestCollectInternetGateways:
    """collect_internet_gateways 함수 테스트"""

    def test_collect_basic_internet_gateway(self, mock_boto3_session):
        """기본 Internet Gateway 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "InternetGateways": [
                {
                    "InternetGatewayId": "igw-12345678",
                    "Attachments": [
                        {
                            "State": "available",
                            "VpcId": "vpc-12345678",
                        }
                    ],
                    "Tags": [{"Key": "Name", "Value": "main-igw"}],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            igws = collect_internet_gateways(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(igws) == 1
        assert igws[0].igw_id == "igw-12345678"
        assert igws[0].name == "main-igw"
        assert igws[0].state == "available"
        assert igws[0].vpc_id == "vpc-12345678"

    def test_collect_detached_internet_gateway(self, mock_boto3_session):
        """분리된 Internet Gateway"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "InternetGateways": [
                {
                    "InternetGatewayId": "igw-detached",
                    "Attachments": [],
                    "Tags": [],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            igws = collect_internet_gateways(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert igws[0].state == "detached"
        assert igws[0].vpc_id == ""


class TestCollectElasticIPs:
    """collect_elastic_ips 함수 테스트"""

    def test_collect_attached_elastic_ip(self, mock_boto3_session):
        """연결된 Elastic IP"""
        mock_ec2 = MagicMock()

        mock_response = {
            "Addresses": [
                {
                    "AllocationId": "eipalloc-12345678",
                    "PublicIp": "54.123.45.67",
                    "Domain": "vpc",
                    "InstanceId": "i-1234567890abcdef0",
                    "NetworkInterfaceId": "eni-12345678",
                    "PrivateIpAddress": "10.0.0.1",
                    "AssociationId": "eipassoc-12345678",
                    "Tags": [{"Key": "Name", "Value": "web-eip"}],
                }
            ]
        }

        mock_ec2.describe_addresses.return_value = mock_response

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            eips = collect_elastic_ips(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(eips) == 1
        assert eips[0].allocation_id == "eipalloc-12345678"
        assert eips[0].public_ip == "54.123.45.67"
        assert eips[0].name == "web-eip"
        assert eips[0].is_attached is True
        assert eips[0].instance_id == "i-1234567890abcdef0"

    def test_collect_unattached_elastic_ip(self, mock_boto3_session):
        """연결되지 않은 Elastic IP"""
        mock_ec2 = MagicMock()

        mock_response = {
            "Addresses": [
                {
                    "AllocationId": "eipalloc-unattached",
                    "PublicIp": "54.123.45.99",
                    "Domain": "vpc",
                    "Tags": [],
                }
            ]
        }

        mock_ec2.describe_addresses.return_value = mock_response

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            eips = collect_elastic_ips(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert eips[0].is_attached is False
        assert eips[0].instance_id == ""
        assert eips[0].network_interface_id == ""


class TestCollectNATGateways:
    """collect_nat_gateways 함수 테스트"""

    def test_collect_basic_nat_gateway(self, mock_boto3_session):
        """기본 NAT Gateway 수집"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "NatGateways": [
                {
                    "NatGatewayId": "nat-12345678",
                    "State": "available",
                    "VpcId": "vpc-12345678",
                    "SubnetId": "subnet-12345678",
                    "ConnectivityType": "public",
                    "CreateTime": "2024-01-01T00:00:00Z",
                    "NatGatewayAddresses": [
                        {
                            "AllocationId": "eipalloc-12345678",
                            "NetworkInterfaceId": "eni-12345678",
                            "PrivateIp": "10.0.0.1",
                            "PublicIp": "54.123.45.67",
                        }
                    ],
                    "Tags": [{"Key": "Name", "Value": "main-nat"}],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            nat_gateways = collect_nat_gateways(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert len(nat_gateways) == 1
        assert nat_gateways[0].nat_gateway_id == "nat-12345678"
        assert nat_gateways[0].name == "main-nat"
        assert nat_gateways[0].state == "available"
        assert nat_gateways[0].connectivity_type == "public"
        assert nat_gateways[0].public_ip == "54.123.45.67"
        assert nat_gateways[0].private_ip == "10.0.0.1"

    def test_collect_private_nat_gateway(self, mock_boto3_session):
        """Private NAT Gateway"""
        mock_ec2 = MagicMock()
        mock_paginator = MagicMock()

        mock_response = {
            "NatGateways": [
                {
                    "NatGatewayId": "nat-private",
                    "State": "available",
                    "VpcId": "vpc-12345678",
                    "SubnetId": "subnet-12345678",
                    "ConnectivityType": "private",
                    "NatGatewayAddresses": [
                        {
                            "NetworkInterfaceId": "eni-12345678",
                            "PrivateIp": "10.0.0.1",
                        }
                    ],
                    "Tags": [],
                }
            ]
        }

        mock_paginator.paginate.return_value = [mock_response]
        mock_ec2.get_paginator.return_value = mock_paginator

        with patch("shared.aws.inventory.services.vpc.get_client", return_value=mock_ec2):
            nat_gateways = collect_nat_gateways(mock_boto3_session, "123456789012", "test-account", "ap-northeast-2")

        assert nat_gateways[0].connectivity_type == "private"
        assert nat_gateways[0].public_ip == ""
