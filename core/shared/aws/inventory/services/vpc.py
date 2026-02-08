"""
shared/aws/inventory/services/vpc.py - VPC/Network 리소스 수집
"""

from __future__ import annotations

from core.parallel import get_client
from functions.reports.ip_search.parser import parse_eni_description

from ..types import ENI, VPC, ElasticIP, InternetGateway, NATGateway, RouteTable, Subnet, VPCEndpoint
from .helpers import parse_tags


def collect_vpcs(session, account_id: str, account_name: str, region: str) -> list[VPC]:
    """VPC 리소스를 수집합니다.

    VPC 목록 조회 후 각 VPC의 CIDR Block, 상태, Default 여부,
    Instance Tenancy, DHCP Options 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        VPC 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    vpcs = []

    paginator = ec2.get_paginator("describe_vpcs")
    for page in paginator.paginate():
        for vpc in page.get("Vpcs", []):
            tags = parse_tags(vpc.get("Tags"))
            vpcs.append(
                VPC(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    vpc_id=vpc["VpcId"],
                    name=tags.get("Name", ""),
                    cidr_block=vpc.get("CidrBlock", ""),
                    state=vpc.get("State", ""),
                    is_default=vpc.get("IsDefault", False),
                    instance_tenancy=vpc.get("InstanceTenancy", "default"),
                    dhcp_options_id=vpc.get("DhcpOptionsId", ""),
                    tags=tags,
                )
            )

    return vpcs


def collect_subnets(session, account_id: str, account_name: str, region: str) -> list[Subnet]:
    """Subnet 리소스를 수집합니다.

    Subnet 목록 조회 후 각 Subnet의 CIDR Block, Availability Zone,
    사용 가능 IP 수, Public IP 자동 할당 여부 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        Subnet 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    subnets = []

    paginator = ec2.get_paginator("describe_subnets")
    for page in paginator.paginate():
        for subnet in page.get("Subnets", []):
            tags = parse_tags(subnet.get("Tags"))
            subnets.append(
                Subnet(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    subnet_id=subnet["SubnetId"],
                    name=tags.get("Name", ""),
                    vpc_id=subnet.get("VpcId", ""),
                    cidr_block=subnet.get("CidrBlock", ""),
                    availability_zone=subnet.get("AvailabilityZone", ""),
                    state=subnet.get("State", ""),
                    available_ip_count=subnet.get("AvailableIpAddressCount", 0),
                    map_public_ip_on_launch=subnet.get("MapPublicIpOnLaunch", False),
                    is_default=subnet.get("DefaultForAz", False),
                    tags=tags,
                )
            )

    return subnets


def collect_route_tables(session, account_id: str, account_name: str, region: str) -> list[RouteTable]:
    """Route Table 리소스를 수집합니다.

    Route Table 목록 조회 후 각 테이블의 Main 여부, 경로 수,
    연결된 Subnet 목록 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        RouteTable 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    route_tables = []

    paginator = ec2.get_paginator("describe_route_tables")
    for page in paginator.paginate():
        for rt in page.get("RouteTables", []):
            tags = parse_tags(rt.get("Tags"))
            associations = rt.get("Associations", [])
            is_main = any(assoc.get("Main", False) for assoc in associations)
            subnet_ids = [assoc.get("SubnetId") for assoc in associations if assoc.get("SubnetId")]

            route_tables.append(
                RouteTable(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    route_table_id=rt["RouteTableId"],
                    name=tags.get("Name", ""),
                    vpc_id=rt.get("VpcId", ""),
                    is_main=is_main,
                    route_count=len(rt.get("Routes", [])),
                    association_count=len(associations),
                    subnet_ids=subnet_ids,
                    tags=tags,
                )
            )

    return route_tables


def collect_internet_gateways(session, account_id: str, account_name: str, region: str) -> list[InternetGateway]:
    """Internet Gateway 리소스를 수집합니다.

    Internet Gateway 목록 조회 후 각 게이트웨이의 연결된 VPC,
    Attachment 상태 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        InternetGateway 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    igws = []

    paginator = ec2.get_paginator("describe_internet_gateways")
    for page in paginator.paginate():
        for igw in page.get("InternetGateways", []):
            tags = parse_tags(igw.get("Tags"))
            attachments = igw.get("Attachments", [])
            vpc_id = attachments[0].get("VpcId", "") if attachments else ""
            state = attachments[0].get("State", "") if attachments else "detached"

            igws.append(
                InternetGateway(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    igw_id=igw["InternetGatewayId"],
                    name=tags.get("Name", ""),
                    state=state,
                    vpc_id=vpc_id,
                    tags=tags,
                )
            )

    return igws


def collect_elastic_ips(session, account_id: str, account_name: str, region: str) -> list[ElasticIP]:
    """Elastic IP 리소스를 수집합니다.

    Elastic IP 목록 조회 후 각 EIP의 Public/Private IP, 연결된 인스턴스,
    ENI, Association 상태 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        ElasticIP 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    eips = []

    resp = ec2.describe_addresses()
    for addr in resp.get("Addresses", []):
        tags = parse_tags(addr.get("Tags"))
        eips.append(
            ElasticIP(
                account_id=account_id,
                account_name=account_name,
                region=region,
                allocation_id=addr.get("AllocationId", ""),
                public_ip=addr.get("PublicIp", ""),
                name=tags.get("Name", ""),
                domain=addr.get("Domain", "vpc"),
                instance_id=addr.get("InstanceId", ""),
                network_interface_id=addr.get("NetworkInterfaceId", ""),
                private_ip=addr.get("PrivateIpAddress", ""),
                association_id=addr.get("AssociationId", ""),
                is_attached=bool(addr.get("AssociationId")),
                tags=tags,
            )
        )

    return eips


def collect_enis(session, account_id: str, account_name: str, region: str) -> list[ENI]:
    """ENI (Elastic Network Interface) 리소스를 수집합니다.

    ENI 목록 조회 후 각 인터페이스의 Public/Private IP, Security Group,
    Attachment 정보, 연결된 리소스 타입/ID 등과 태그를 함께 수집합니다.
    연결된 리소스는 ENI Description을 파싱하여 식별합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        ENI 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    enis = []

    paginator = ec2.get_paginator("describe_network_interfaces")
    for page in paginator.paginate():
        for eni in page.get("NetworkInterfaces", []):
            # Public IP 추출
            public_ip = ""
            if eni.get("Association"):
                public_ip = eni["Association"].get("PublicIp", "")

            # 태그 파싱
            tags = parse_tags(eni.get("TagSet"))
            name = tags.get("Name", "")

            # Security Group IDs 추출
            security_group_ids = [sg.get("GroupId", "") for sg in eni.get("Groups", [])]

            # Attachment 정보
            attachment = eni.get("Attachment", {})
            attachment_time = attachment.get("AttachTime")
            instance_id = attachment.get("InstanceId", "")

            # 연결된 리소스 파싱
            parsed = parse_eni_description(
                description=eni.get("Description", ""),
                interface_type=eni.get("InterfaceType", ""),
                attachment=attachment,
            )

            connected_resource_type = ""
            connected_resource_id = ""
            if parsed:
                connected_resource_type = parsed.resource_type
                connected_resource_id = parsed.resource_id or parsed.resource_name

            enis.append(
                ENI(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    eni_id=eni["NetworkInterfaceId"],
                    name=name,
                    status=eni.get("Status", ""),
                    interface_type=eni.get("InterfaceType", ""),
                    private_ip=eni.get("PrivateIpAddress", ""),
                    public_ip=public_ip,
                    vpc_id=eni.get("VpcId", ""),
                    subnet_id=eni.get("SubnetId", ""),
                    instance_id=instance_id,
                    # 추가 상세 정보
                    availability_zone=eni.get("AvailabilityZone", ""),
                    security_group_ids=security_group_ids,
                    attachment_time=attachment_time,
                    requester_id=eni.get("RequesterId", ""),
                    requester_managed=eni.get("RequesterManaged", False),
                    tags=tags,
                    connected_resource_type=connected_resource_type,
                    connected_resource_id=connected_resource_id,
                )
            )

    return enis


def collect_nat_gateways(session, account_id: str, account_name: str, region: str) -> list[NATGateway]:
    """NAT Gateway 리소스를 수집합니다.

    NAT Gateway 목록 조회 후 각 게이트웨이의 Public/Private IP,
    Connectivity Type, EIP Allocation ID, VPC/Subnet 정보 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        NATGateway 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    nat_gateways = []

    paginator = ec2.get_paginator("describe_nat_gateways")
    for page in paginator.paginate():
        for nat in page.get("NatGateways", []):
            # IP 주소 및 EIP Allocation ID 추출
            public_ip = ""
            private_ip = ""
            allocation_id = ""
            for addr in nat.get("NatGatewayAddresses", []):
                if addr.get("PublicIp"):
                    public_ip = addr["PublicIp"]
                if addr.get("PrivateIp"):
                    private_ip = addr["PrivateIp"]
                if addr.get("AllocationId"):
                    allocation_id = addr["AllocationId"]

            # 태그 파싱
            tags = parse_tags(nat.get("Tags"))
            name = tags.get("Name", "")

            nat_gateways.append(
                NATGateway(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    nat_gateway_id=nat["NatGatewayId"],
                    name=name,
                    state=nat.get("State", ""),
                    connectivity_type=nat.get("ConnectivityType", "public"),
                    public_ip=public_ip,
                    private_ip=private_ip,
                    vpc_id=nat.get("VpcId", ""),
                    subnet_id=nat.get("SubnetId", ""),
                    # 추가 상세 정보
                    create_time=nat.get("CreateTime"),
                    allocation_id=allocation_id,
                    tags=tags,
                )
            )

    return nat_gateways


def collect_vpc_endpoints(session, account_id: str, account_name: str, region: str) -> list[VPCEndpoint]:
    """VPC Endpoint 리소스를 수집합니다.

    VPC Endpoint 목록 조회 후 각 Endpoint의 타입(Gateway/Interface),
    서비스 이름, Private DNS 설정, Route Table/Subnet/ENI 연결 정보,
    Policy Document 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        VPCEndpoint 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    endpoints = []

    paginator = ec2.get_paginator("describe_vpc_endpoints")
    for page in paginator.paginate():
        for ep in page.get("VpcEndpoints", []):
            # 태그 파싱
            tags = parse_tags(ep.get("Tags"))
            name = tags.get("Name", "")

            # Policy document (있으면 JSON 문자열로 저장)
            policy_document = ""
            if ep.get("PolicyDocument"):
                policy_document = ep["PolicyDocument"]

            endpoints.append(
                VPCEndpoint(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    endpoint_id=ep["VpcEndpointId"],
                    name=name,
                    endpoint_type=ep.get("VpcEndpointType", ""),
                    state=ep.get("State", ""),
                    service_name=ep.get("ServiceName", ""),
                    vpc_id=ep.get("VpcId", ""),
                    private_dns_enabled=ep.get("PrivateDnsEnabled", False),
                    # 추가 상세 정보
                    creation_timestamp=ep.get("CreationTimestamp"),
                    route_table_ids=ep.get("RouteTableIds", []),
                    subnet_ids=ep.get("SubnetIds", []),
                    network_interface_ids=ep.get("NetworkInterfaceIds", []),
                    policy_document=policy_document,
                    tags=tags,
                )
            )

    return endpoints
