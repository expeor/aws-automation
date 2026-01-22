"""
core/data/inventory/services/vpc.py - VPC resource collection

Collects ENIs, NAT Gateways, and VPC Endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from botocore.exceptions import ClientError

from core.parallel import get_client

from ..types import NATGateway, NetworkInterface, VPCEndpoint

if TYPE_CHECKING:
    from boto3 import Session


def collect_enis(
    session: "Session",
    account_id: str,
    account_name: str,
    region: str,
) -> list[NetworkInterface]:
    """Collect Elastic Network Interfaces in a region

    Args:
        session: Boto3 session
        account_id: AWS account ID
        account_name: Account name for display
        region: AWS region

    Returns:
        List of NetworkInterface objects
    """
    enis = []

    try:
        ec2 = get_client(session, "ec2", region_name=region)
        paginator = ec2.get_paginator("describe_network_interfaces")

        for page in paginator.paginate():
            for data in page.get("NetworkInterfaces", []):
                attachment = data.get("Attachment")

                # Parse tags
                tags = {}
                name = ""
                for tag in data.get("TagSet", []):
                    key = tag.get("Key", "")
                    value = tag.get("Value", "")
                    if not key.startswith("aws:"):
                        tags[key] = value
                    if key == "Name":
                        name = value

                # Security groups
                sgs = [g.get("GroupId", "") for g in data.get("Groups", [])]

                eni = NetworkInterface(
                    eni_id=data.get("NetworkInterfaceId", ""),
                    status=data.get("Status", ""),
                    vpc_id=data.get("VpcId", ""),
                    subnet_id=data.get("SubnetId", ""),
                    availability_zone=data.get("AvailabilityZone", ""),
                    description=data.get("Description", ""),
                    private_ip=data.get("PrivateIpAddress", ""),
                    public_ip=(
                        data.get("Association", {}).get("PublicIp", "")
                        if data.get("Association")
                        else ""
                    ),
                    interface_type=data.get("InterfaceType", ""),
                    requester_id=data.get("RequesterId", ""),
                    owner_id=data.get("OwnerId", ""),
                    instance_id=attachment.get("InstanceId", "") if attachment else "",
                    attachment_status=attachment.get("Status", "") if attachment else "",
                    security_groups=sgs,
                    tags=tags,
                    name=name,
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                )
                enis.append(eni)

    except ClientError:
        pass

    return enis


def collect_nat_gateways(
    session: "Session",
    account_id: str,
    account_name: str,
    region: str,
) -> list[NATGateway]:
    """Collect NAT Gateways in a region

    Args:
        session: Boto3 session
        account_id: AWS account ID
        account_name: Account name for display
        region: AWS region

    Returns:
        List of NATGateway objects
    """
    nat_gateways = []

    try:
        ec2 = get_client(session, "ec2", region_name=region)
        paginator = ec2.get_paginator("describe_nat_gateways")

        for page in paginator.paginate():
            for data in page.get("NatGateways", []):
                # Parse tags
                tags = {}
                name = ""
                for tag in data.get("Tags", []):
                    key = tag.get("Key", "")
                    value = tag.get("Value", "")
                    if not key.startswith("aws:"):
                        tags[key] = value
                    if key == "Name":
                        name = value

                # Get IPs from addresses
                public_ip = ""
                private_ip = ""
                for addr in data.get("NatGatewayAddresses", []):
                    if addr.get("PublicIp"):
                        public_ip = addr.get("PublicIp", "")
                    if addr.get("PrivateIp"):
                        private_ip = addr.get("PrivateIp", "")

                nat = NATGateway(
                    nat_gateway_id=data.get("NatGatewayId", ""),
                    vpc_id=data.get("VpcId", ""),
                    subnet_id=data.get("SubnetId", ""),
                    state=data.get("State", ""),
                    connectivity_type=data.get("ConnectivityType", "public"),
                    public_ip=public_ip,
                    private_ip=private_ip,
                    create_time=data.get("CreateTime"),
                    tags=tags,
                    name=name,
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                )
                nat_gateways.append(nat)

    except ClientError:
        pass

    return nat_gateways


def collect_vpc_endpoints(
    session: "Session",
    account_id: str,
    account_name: str,
    region: str,
) -> list[VPCEndpoint]:
    """Collect VPC Endpoints in a region

    Args:
        session: Boto3 session
        account_id: AWS account ID
        account_name: Account name for display
        region: AWS region

    Returns:
        List of VPCEndpoint objects
    """
    endpoints = []

    try:
        ec2 = get_client(session, "ec2", region_name=region)
        paginator = ec2.get_paginator("describe_vpc_endpoints")

        for page in paginator.paginate():
            for data in page.get("VpcEndpoints", []):
                # Parse tags
                tags = {}
                name = ""
                for tag in data.get("Tags", []):
                    key = tag.get("Key", "")
                    value = tag.get("Value", "")
                    if not key.startswith("aws:"):
                        tags[key] = value
                    if key == "Name":
                        name = value

                endpoint = VPCEndpoint(
                    endpoint_id=data.get("VpcEndpointId", ""),
                    endpoint_type=data.get("VpcEndpointType", "Unknown"),
                    service_name=data.get("ServiceName", ""),
                    vpc_id=data.get("VpcId", ""),
                    state=data.get("State", ""),
                    creation_time=data.get("CreationTimestamp"),
                    name=name,
                    tags=tags,
                    subnet_ids=data.get("SubnetIds", []),
                    network_interface_ids=data.get("NetworkInterfaceIds", []),
                    private_dns_enabled=data.get("PrivateDnsEnabled", False),
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                )
                endpoints.append(endpoint)

    except ClientError:
        pass

    return endpoints
