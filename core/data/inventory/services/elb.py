"""
core/data/inventory/services/elb.py - Load Balancer resource collection

Collects ALB, NLB, GWLB, CLB, and Target Groups.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from botocore.exceptions import ClientError

from core.parallel import get_client

from ..types import LoadBalancer, TargetGroup

if TYPE_CHECKING:
    from boto3 import Session


def collect_load_balancers(
    session: "Session",
    account_id: str,
    account_name: str,
    region: str,
    lb_type_filter: str | None = None,
) -> list[LoadBalancer]:
    """Collect ALB/NLB/GWLB in a region

    Args:
        session: Boto3 session
        account_id: AWS account ID
        account_name: Account name for display
        region: AWS region
        lb_type_filter: Optional filter for lb type (application, network, gateway)

    Returns:
        List of LoadBalancer objects
    """
    load_balancers = []

    try:
        elbv2 = get_client(session, "elbv2", region_name=region)
        paginator = elbv2.get_paginator("describe_load_balancers")

        for page in paginator.paginate():
            for data in page.get("LoadBalancers", []):
                lb_arn = data.get("LoadBalancerArn", "")
                lb_type = data.get("Type", "application")

                # Apply filter if specified
                if lb_type_filter and lb_type != lb_type_filter:
                    continue

                # Get tags
                tags = _get_elbv2_tags(elbv2, lb_arn)

                lb = LoadBalancer(
                    arn=lb_arn,
                    name=data.get("LoadBalancerName", ""),
                    dns_name=data.get("DNSName", ""),
                    lb_type=lb_type,
                    scheme=data.get("Scheme", ""),
                    state=data.get("State", {}).get("Code", ""),
                    vpc_id=data.get("VpcId", ""),
                    availability_zones=[
                        az.get("ZoneName", "") for az in data.get("AvailabilityZones", [])
                    ],
                    created_time=data.get("CreatedTime"),
                    tags=tags,
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                )

                # Get target groups
                lb.target_groups = _get_target_groups_for_lb(elbv2, lb_arn, account_id, account_name, region)

                load_balancers.append(lb)

    except ClientError:
        pass

    return load_balancers


def collect_classic_lbs(
    session: "Session",
    account_id: str,
    account_name: str,
    region: str,
) -> list[LoadBalancer]:
    """Collect Classic Load Balancers in a region

    Args:
        session: Boto3 session
        account_id: AWS account ID
        account_name: Account name for display
        region: AWS region

    Returns:
        List of LoadBalancer objects
    """
    load_balancers = []

    try:
        elb = get_client(session, "elb", region_name=region)
        response = elb.describe_load_balancers()

        for data in response.get("LoadBalancerDescriptions", []):
            lb_name = data.get("LoadBalancerName", "")

            # Get tags
            tags = {}
            try:
                tag_response = elb.describe_tags(LoadBalancerNames=[lb_name])
                for tag_desc in tag_response.get("TagDescriptions", []):
                    for t in tag_desc.get("Tags", []):
                        key = t.get("Key", "")
                        if not key.startswith("aws:"):
                            tags[key] = t.get("Value", "")
            except ClientError:
                pass

            # Get instance health
            instances = data.get("Instances", [])
            healthy = 0
            try:
                if instances:
                    health_response = elb.describe_instance_health(LoadBalancerName=lb_name)
                    for state in health_response.get("InstanceStates", []):
                        if state.get("State") == "InService":
                            healthy += 1
            except ClientError:
                pass

            lb = LoadBalancer(
                arn=f"arn:aws:elasticloadbalancing:{region}:{account_id}:loadbalancer/{lb_name}",
                name=lb_name,
                dns_name=data.get("DNSName", ""),
                lb_type="classic",
                scheme=data.get("Scheme", ""),
                state="active",  # CLB doesn't have state
                vpc_id=data.get("VPCId", ""),
                availability_zones=data.get("AvailabilityZones", []),
                created_time=data.get("CreatedTime"),
                tags=tags,
                registered_instances=len(instances),
                healthy_instances=healthy,
                account_id=account_id,
                account_name=account_name,
                region=region,
            )
            load_balancers.append(lb)

    except ClientError as e:
        # CLB might not be available in some regions
        if "not available" not in str(e).lower():
            pass

    return load_balancers


def collect_target_groups(
    session: "Session",
    account_id: str,
    account_name: str,
    region: str,
) -> list[TargetGroup]:
    """Collect all Target Groups in a region

    Args:
        session: Boto3 session
        account_id: AWS account ID
        account_name: Account name for display
        region: AWS region

    Returns:
        List of TargetGroup objects
    """
    target_groups = []

    try:
        elbv2 = get_client(session, "elbv2", region_name=region)
        paginator = elbv2.get_paginator("describe_target_groups")

        for page in paginator.paginate():
            for data in page.get("TargetGroups", []):
                tg_arn = data.get("TargetGroupArn", "")

                # Get target health
                healthy, unhealthy, total = _get_target_health(elbv2, tg_arn)

                tg = TargetGroup(
                    arn=tg_arn,
                    name=data.get("TargetGroupName", ""),
                    target_type=data.get("TargetType", ""),
                    protocol=data.get("Protocol", ""),
                    port=data.get("Port", 0),
                    vpc_id=data.get("VpcId", ""),
                    health_check_enabled=data.get("HealthCheckEnabled", True),
                    total_targets=total,
                    healthy_targets=healthy,
                    unhealthy_targets=unhealthy,
                    load_balancer_arns=data.get("LoadBalancerArns", []),
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                )
                target_groups.append(tg)

    except ClientError:
        pass

    return target_groups


def _get_elbv2_tags(elbv2_client, resource_arn: str) -> dict[str, str]:
    """Get tags for an ELBv2 resource"""
    tags = {}
    try:
        tag_response = elbv2_client.describe_tags(ResourceArns=[resource_arn])
        for tag_desc in tag_response.get("TagDescriptions", []):
            for t in tag_desc.get("Tags", []):
                key = t.get("Key", "")
                if not key.startswith("aws:"):
                    tags[key] = t.get("Value", "")
    except ClientError:
        pass
    return tags


def _get_target_health(elbv2_client, target_group_arn: str) -> tuple[int, int, int]:
    """Get target health counts for a target group

    Returns:
        Tuple of (healthy, unhealthy, total) counts
    """
    healthy = 0
    unhealthy = 0
    total = 0

    try:
        response = elbv2_client.describe_target_health(TargetGroupArn=target_group_arn)
        for target in response.get("TargetHealthDescriptions", []):
            total += 1
            state = target.get("TargetHealth", {}).get("State", "")
            if state == "healthy":
                healthy += 1
            else:
                unhealthy += 1
    except ClientError:
        pass

    return healthy, unhealthy, total


def _get_target_groups_for_lb(
    elbv2_client,
    lb_arn: str,
    account_id: str,
    account_name: str,
    region: str,
) -> list[TargetGroup]:
    """Get target groups associated with a load balancer"""
    target_groups = []

    try:
        response = elbv2_client.describe_target_groups(LoadBalancerArn=lb_arn)

        for data in response.get("TargetGroups", []):
            tg_arn = data.get("TargetGroupArn", "")
            healthy, unhealthy, total = _get_target_health(elbv2_client, tg_arn)

            tg = TargetGroup(
                arn=tg_arn,
                name=data.get("TargetGroupName", ""),
                target_type=data.get("TargetType", ""),
                protocol=data.get("Protocol", ""),
                port=data.get("Port", 0),
                vpc_id=data.get("VpcId", ""),
                health_check_enabled=data.get("HealthCheckEnabled", True),
                total_targets=total,
                healthy_targets=healthy,
                unhealthy_targets=unhealthy,
                load_balancer_arns=data.get("LoadBalancerArns", []),
                account_id=account_id,
                account_name=account_name,
                region=region,
            )
            target_groups.append(tg)

    except ClientError:
        pass

    return target_groups
