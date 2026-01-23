"""
plugins/resource_explorer/common/services/elb.py - ELB 리소스 수집
"""

from core.parallel import get_client

from ..types import LoadBalancer, TargetGroup
from .helpers import parse_tags


def collect_load_balancers(
    session, account_id: str, account_name: str, region: str, include_classic: bool = False
) -> list[LoadBalancer]:
    """Load Balancer 수집 (ALB/NLB/GWLB, 선택적 CLB) - 상세 정보 포함"""
    load_balancers = []

    # ALB/NLB/GWLB (elbv2)
    elbv2 = get_client(session, "elbv2", region_name=region)

    paginator = elbv2.get_paginator("describe_load_balancers")
    for page in paginator.paginate():
        for lb in page.get("LoadBalancers", []):
            # AZ 추출
            availability_zones = [az.get("ZoneName", "") for az in lb.get("AvailabilityZones", [])]

            load_balancers.append(
                LoadBalancer(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    name=lb.get("LoadBalancerName", ""),
                    arn=lb.get("LoadBalancerArn", ""),
                    lb_type=lb.get("Type", ""),
                    scheme=lb.get("Scheme", ""),
                    state=lb.get("State", {}).get("Code", ""),
                    vpc_id=lb.get("VpcId", ""),
                    dns_name=lb.get("DNSName", ""),
                    target_groups=[],
                    total_targets=0,
                    healthy_targets=0,
                    # 추가 상세 정보
                    created_time=lb.get("CreatedTime"),
                    availability_zones=availability_zones,
                    security_group_ids=lb.get("SecurityGroups", []),
                    access_logs_enabled=False,  # 아래에서 attributes 조회 후 설정
                    tags={},  # 아래에서 태그 조회 후 설정
                )
            )

    # 태그 및 속성 일괄 조회 (API 호출 최소화)
    if load_balancers:
        _populate_lb_details(elbv2, load_balancers)

    # CLB (elb classic)
    if include_classic:
        elb = get_client(session, "elb", region_name=region)

        paginator = elb.get_paginator("describe_load_balancers")
        for page in paginator.paginate():
            for lb in page.get("LoadBalancerDescriptions", []):
                # AZ 추출
                availability_zones = lb.get("AvailabilityZones", [])

                load_balancers.append(
                    LoadBalancer(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        name=lb.get("LoadBalancerName", ""),
                        arn="",  # CLB has no ARN
                        lb_type="classic",
                        scheme=lb.get("Scheme", ""),
                        state="active",  # CLB doesn't have state
                        vpc_id=lb.get("VPCId", ""),
                        dns_name=lb.get("DNSName", ""),
                        target_groups=[],
                        total_targets=len(lb.get("Instances", [])),
                        healthy_targets=0,  # Need separate health check
                        # 추가 상세 정보
                        created_time=lb.get("CreatedTime"),
                        availability_zones=availability_zones,
                        security_group_ids=lb.get("SecurityGroups", []),
                        access_logs_enabled=False,  # CLB: 별도 조회 필요
                        tags={},  # CLB: 별도 조회 필요
                    )
                )

    return load_balancers


def _populate_lb_details(elbv2, load_balancers: list[LoadBalancer]) -> None:
    """
    Load Balancer 태그 및 속성 일괄 조회.

    API 호출 최적화를 위해 배치로 처리.
    """
    # ARN -> LoadBalancer 매핑
    lb_map: dict[str, LoadBalancer] = {lb.arn: lb for lb in load_balancers if lb.arn}

    if not lb_map:
        return

    # 태그 조회 (최대 20개씩 배치)
    arns = list(lb_map.keys())
    batch_size = 20

    for i in range(0, len(arns), batch_size):
        batch_arns = arns[i : i + batch_size]

        try:
            tags_resp = elbv2.describe_tags(ResourceArns=batch_arns)
            for tag_desc in tags_resp.get("TagDescriptions", []):
                arn = tag_desc.get("ResourceArn", "")
                if arn in lb_map:
                    tags = parse_tags(tag_desc.get("Tags"))
                    lb_map[arn].tags = tags
        except Exception:
            pass

    # Access Logs 속성 조회 (개별 조회 필요)
    for arn, lb in lb_map.items():
        try:
            attrs_resp = elbv2.describe_load_balancer_attributes(LoadBalancerArn=arn)
            for attr in attrs_resp.get("Attributes", []):
                if attr.get("Key") == "access_logs.s3.enabled":
                    lb.access_logs_enabled = attr.get("Value", "false").lower() == "true"
                    break
        except Exception:
            pass


def collect_target_groups(session, account_id: str, account_name: str, region: str) -> list[TargetGroup]:
    """Target Group 수집 (상세 정보 포함)"""
    elbv2 = get_client(session, "elbv2", region_name=region)
    target_groups = []

    paginator = elbv2.get_paginator("describe_target_groups")
    for page in paginator.paginate():
        for tg in page.get("TargetGroups", []):
            tg_arn = tg.get("TargetGroupArn", "")

            # Target health 조회
            total = 0
            healthy = 0
            unhealthy = 0

            try:
                health_resp = elbv2.describe_target_health(TargetGroupArn=tg_arn)
                for target in health_resp.get("TargetHealthDescriptions", []):
                    total += 1
                    state = target.get("TargetHealth", {}).get("State", "")
                    if state == "healthy":
                        healthy += 1
                    elif state == "unhealthy":
                        unhealthy += 1
            except Exception:
                pass

            # Health check 설정 추출
            health_check_path = tg.get("HealthCheckPath", "")
            health_check_protocol = tg.get("HealthCheckProtocol", "")
            health_check_interval = tg.get("HealthCheckIntervalSeconds", 30)

            target_groups.append(
                TargetGroup(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    name=tg.get("TargetGroupName", ""),
                    arn=tg_arn,
                    target_type=tg.get("TargetType", ""),
                    protocol=tg.get("Protocol", ""),
                    port=tg.get("Port", 0),
                    vpc_id=tg.get("VpcId", ""),
                    total_targets=total,
                    healthy_targets=healthy,
                    unhealthy_targets=unhealthy,
                    load_balancer_arns=tg.get("LoadBalancerArns", []),
                    # 추가 상세 정보
                    health_check_path=health_check_path,
                    health_check_protocol=health_check_protocol,
                    health_check_interval=health_check_interval,
                    deregistration_delay=300,  # 아래에서 attributes 조회 후 설정
                    tags={},  # 아래에서 태그 조회 후 설정
                )
            )

    # 태그 및 속성 일괄 조회
    if target_groups:
        _populate_tg_details(elbv2, target_groups)

    return target_groups


def _populate_tg_details(elbv2, target_groups: list[TargetGroup]) -> None:
    """
    Target Group 태그 및 속성 일괄 조회.
    """
    # ARN -> TargetGroup 매핑
    tg_map: dict[str, TargetGroup] = {tg.arn: tg for tg in target_groups if tg.arn}

    if not tg_map:
        return

    # 태그 조회 (최대 20개씩 배치)
    arns = list(tg_map.keys())
    batch_size = 20

    for i in range(0, len(arns), batch_size):
        batch_arns = arns[i : i + batch_size]

        try:
            tags_resp = elbv2.describe_tags(ResourceArns=batch_arns)
            for tag_desc in tags_resp.get("TagDescriptions", []):
                arn = tag_desc.get("ResourceArn", "")
                if arn in tg_map:
                    tags = parse_tags(tag_desc.get("Tags"))
                    tg_map[arn].tags = tags
        except Exception:
            pass

    # Deregistration delay 속성 조회 (개별 조회 필요)
    for arn, tg in tg_map.items():
        try:
            attrs_resp = elbv2.describe_target_group_attributes(TargetGroupArn=arn)
            for attr in attrs_resp.get("Attributes", []):
                if attr.get("Key") == "deregistration_delay.timeout_seconds":
                    tg.deregistration_delay = int(attr.get("Value", 300))
                    break
        except Exception:
            pass
