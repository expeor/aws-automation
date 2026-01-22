"""
core/data/inventory/services/ec2.py - EC2 resource collection

Collects EC2 instances and Security Groups.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from botocore.exceptions import ClientError

from core.parallel import get_client

from ..types import EC2Instance, SecurityGroup

if TYPE_CHECKING:
    from boto3 import Session


def collect_ec2_instances(
    session: "Session",
    account_id: str,
    account_name: str,
    region: str,
) -> list[EC2Instance]:
    """Collect EC2 instances in a region

    Args:
        session: Boto3 session
        account_id: AWS account ID
        account_name: Account name for display
        region: AWS region

    Returns:
        List of EC2Instance objects
    """
    instances = []

    try:
        ec2 = get_client(session, "ec2", region_name=region)
        paginator = ec2.get_paginator("describe_instances")

        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                for data in reservation.get("Instances", []):
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

                    # Security groups
                    sgs = [sg.get("GroupId", "") for sg in data.get("SecurityGroups", [])]

                    instance = EC2Instance(
                        instance_id=data.get("InstanceId", ""),
                        instance_type=data.get("InstanceType", ""),
                        state=data.get("State", {}).get("Name", ""),
                        name=name,
                        private_ip=data.get("PrivateIpAddress", ""),
                        public_ip=data.get("PublicIpAddress", ""),
                        vpc_id=data.get("VpcId", ""),
                        subnet_id=data.get("SubnetId", ""),
                        availability_zone=data.get("Placement", {}).get("AvailabilityZone", ""),
                        platform=data.get("PlatformDetails", ""),
                        launch_time=data.get("LaunchTime"),
                        tags=tags,
                        security_groups=sgs,
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                    )
                    instances.append(instance)

    except ClientError:
        pass

    return instances


def collect_security_groups(
    session: "Session",
    account_id: str,
    account_name: str,
    region: str,
) -> list[SecurityGroup]:
    """Collect Security Groups in a region

    Args:
        session: Boto3 session
        account_id: AWS account ID
        account_name: Account name for display
        region: AWS region

    Returns:
        List of SecurityGroup objects
    """
    security_groups = []

    try:
        ec2 = get_client(session, "ec2", region_name=region)
        paginator = ec2.get_paginator("describe_security_groups")

        for page in paginator.paginate():
            for data in page.get("SecurityGroups", []):
                # Parse tags
                tags = {}
                for tag in data.get("Tags", []):
                    key = tag.get("Key", "")
                    if not key.startswith("aws:"):
                        tags[key] = tag.get("Value", "")

                sg = SecurityGroup(
                    group_id=data.get("GroupId", ""),
                    group_name=data.get("GroupName", ""),
                    vpc_id=data.get("VpcId", ""),
                    description=data.get("Description", ""),
                    owner_id=data.get("OwnerId", ""),
                    inbound_rules=data.get("IpPermissions", []),
                    outbound_rules=data.get("IpPermissionsEgress", []),
                    tags=tags,
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                )
                security_groups.append(sg)

    except ClientError:
        pass

    return security_groups


def collect_sg_usage(
    session: "Session",
    region: str,
    security_groups: list[SecurityGroup],
) -> None:
    """Populate ENI attachment info for security groups (mutates in place)

    Args:
        session: Boto3 session
        region: AWS region
        security_groups: List of security groups to update
    """
    sg_map = {sg.group_id: sg for sg in security_groups}

    try:
        ec2 = get_client(session, "ec2", region_name=region)
        paginator = ec2.get_paginator("describe_network_interfaces")

        for page in paginator.paginate():
            for eni in page.get("NetworkInterfaces", []):
                eni_id = eni.get("NetworkInterfaceId", "")
                for group in eni.get("Groups", []):
                    sg_id = group.get("GroupId", "")
                    if sg_id in sg_map:
                        sg_map[sg_id].attached_enis.append(eni_id)

    except ClientError:
        pass
