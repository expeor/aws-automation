"""
shared/aws/inventory/services/ec2.py - EC2 리소스 수집
"""

from __future__ import annotations

from core.parallel import get_client
from functions.reports.ip_search.parser import parse_eni_description

from ..types import EC2Instance, SecurityGroup
from .helpers import count_rules, has_public_access_rule, parse_tags


def collect_ec2_instances(session, account_id: str, account_name: str, region: str) -> list[EC2Instance]:
    """EC2 Instance 리소스를 수집합니다.

    인스턴스 목록 조회 후 태그, EBS Volume ID, Security Group ID, IAM Role 등
    상세 정보를 함께 수집합니다. IAM Role은 Instance Profile ARN에서 역할 이름을 추출합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        EC2Instance 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    instances = []

    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                # 태그 파싱
                tags = parse_tags(inst.get("Tags"))
                name = tags.get("Name", "")

                # EBS Volume IDs 추출
                ebs_volume_ids = []
                for block_device in inst.get("BlockDeviceMappings", []):
                    ebs = block_device.get("Ebs", {})
                    if ebs.get("VolumeId"):
                        ebs_volume_ids.append(ebs["VolumeId"])

                # Security Group IDs 추출
                security_group_ids = [sg.get("GroupId", "") for sg in inst.get("SecurityGroups", [])]

                # IAM Role 추출 (ARN에서 역할 이름 추출: arn:aws:iam::123456789012:instance-profile/my-role)
                iam_role = ""
                if inst.get("IamInstanceProfile"):
                    arn = inst["IamInstanceProfile"].get("Arn", "")
                    iam_role = arn.split("/")[-1] if "/" in arn else arn

                instances.append(
                    EC2Instance(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        instance_id=inst["InstanceId"],
                        name=name,
                        instance_type=inst.get("InstanceType", ""),
                        state=inst.get("State", {}).get("Name", ""),
                        private_ip=inst.get("PrivateIpAddress", ""),
                        public_ip=inst.get("PublicIpAddress", ""),
                        vpc_id=inst.get("VpcId", ""),
                        platform=inst.get("PlatformDetails", "Linux/UNIX"),
                        # 추가 상세 정보
                        launch_time=inst.get("LaunchTime"),
                        subnet_id=inst.get("SubnetId", ""),
                        availability_zone=inst.get("Placement", {}).get("AvailabilityZone", ""),
                        iam_role=iam_role,
                        key_name=inst.get("KeyName", ""),
                        ebs_volume_ids=ebs_volume_ids,
                        security_group_ids=security_group_ids,
                        tags=tags,
                    )
                )

    return instances


def collect_security_groups(
    session, account_id: str, account_name: str, region: str, populate_attachments: bool = True
) -> list[SecurityGroup]:
    """Security Group 리소스를 수집합니다.

    Security Group 목록 조회 후 인바운드/아웃바운드 규칙 수, 퍼블릭 접근 여부 등을 분석합니다.
    populate_attachments가 True이면 ENI 조회를 통해 연결된 리소스(EC2, ELB, Lambda 등)를
    식별합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드
        populate_attachments: True면 ENI 조회로 연결된 리소스를 식별합니다.
            추가 API 호출이 발생하므로 대규모 환경에서는 False로 설정할 수 있습니다.

    Returns:
        SecurityGroup 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    security_groups = []

    paginator = ec2.get_paginator("describe_security_groups")
    for page in paginator.paginate():
        for sg in page.get("SecurityGroups", []):
            tags = parse_tags(sg.get("Tags"))
            inbound_rules = sg.get("IpPermissions", [])
            outbound_rules = sg.get("IpPermissionsEgress", [])

            security_groups.append(
                SecurityGroup(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    group_id=sg["GroupId"],
                    group_name=sg.get("GroupName", ""),
                    vpc_id=sg.get("VpcId", ""),
                    description=sg.get("Description", ""),
                    inbound_rules=inbound_rules,
                    outbound_rules=outbound_rules,
                    attached_enis=[],
                    # 추가 상세 정보
                    owner_id=sg.get("OwnerId", ""),
                    tags=tags,
                    rule_count=count_rules(inbound_rules) + count_rules(outbound_rules),
                    has_public_access=has_public_access_rule(inbound_rules),
                    attached_resource_ids=[],
                    attached_resource_types=[],
                )
            )

    # 연결된 리소스 조회
    if populate_attachments and security_groups:
        _populate_sg_attachments(ec2, security_groups)

    return security_groups


def _populate_sg_attachments(ec2, security_groups: list[SecurityGroup]) -> None:
    """Security Group에 연결된 리소스를 조회하여 in-place로 업데이트합니다.

    모든 ENI를 조회하여 각 ENI에 연결된 Security Group을 확인하고,
    ENI Description을 파싱하여 연결된 리소스 타입과 ID를 식별합니다.
    결과는 SecurityGroup 객체의 attached_enis, attached_resource_ids,
    attached_resource_types 필드에 직접 반영됩니다.

    Args:
        ec2: Rate limiting이 적용된 EC2 클라이언트
        security_groups: 연결 정보를 채울 SecurityGroup 목록
    """
    # SG ID -> SecurityGroup 객체 매핑
    sg_map: dict[str, SecurityGroup] = {sg.group_id: sg for sg in security_groups}

    # 모든 ENI 조회
    paginator = ec2.get_paginator("describe_network_interfaces")
    for page in paginator.paginate():
        for eni in page.get("NetworkInterfaces", []):
            # ENI에 연결된 Security Group들
            for group in eni.get("Groups", []):
                sg_id = group.get("GroupId", "")
                if sg_id not in sg_map:
                    continue

                sg = sg_map[sg_id]
                eni_id = eni.get("NetworkInterfaceId", "")

                # ENI ID 추가
                if eni_id and eni_id not in sg.attached_enis:
                    sg.attached_enis.append(eni_id)

                # 리소스 파싱
                parsed = parse_eni_description(
                    description=eni.get("Description", ""),
                    interface_type=eni.get("InterfaceType", ""),
                    attachment=eni.get("Attachment"),
                )

                if parsed:
                    resource_id = parsed.resource_id or parsed.resource_name
                    resource_type = parsed.resource_type

                    # 중복 방지
                    if resource_id and resource_id not in sg.attached_resource_ids:
                        sg.attached_resource_ids.append(resource_id)
                        sg.attached_resource_types.append(resource_type)
