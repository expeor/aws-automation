"""
Security Group 데이터 수집기

수집 항목:
- Security Groups (메타정보, 규칙)
- Network Interfaces (SG 연결 정보)
- VPCs (Default VPC 판단용)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from botocore.exceptions import ClientError

from core.parallel import get_client

logger = logging.getLogger(__name__)


@dataclass
class SGRule:
    """Security Group 개별 규칙 정보.

    인바운드 또는 아웃바운드 방향의 단일 규칙을 나타내며,
    IP CIDR, SG 참조, Prefix List 등 다양한 소스/대상 유형을 포함한다.

    Attributes:
        rule_id: 규칙 고유 식별자 (방향-프로토콜-포트-소스 조합).
        direction: 규칙 방향 (``inbound`` 또는 ``outbound``).
        protocol: 프로토콜 (``tcp``, ``udp``, ``ALL`` 등).
        port_range: 포트 범위 (``22``, ``80-443``, ``ALL`` 등).
        source_dest: 소스/대상 (IP CIDR, SG ID, 또는 Prefix List ID).
        source_dest_type: 소스/대상 유형 (``ip``, ``sg``, ``prefix-list``).
        referenced_sg_id: 참조된 Security Group ID (SG 참조인 경우).
        description: 규칙 설명.
        is_self_reference: 자기 자신 SG 참조 여부.
        is_cross_account: 다른 계정의 SG 참조 여부.
        referenced_account_id: 참조된 SG의 계정 ID (cross-account인 경우).
        is_ipv6: IPv6 규칙 여부.
    """

    rule_id: str
    direction: str  # inbound / outbound
    protocol: str
    port_range: str
    source_dest: str  # IP, SG ID, or Prefix List
    source_dest_type: str  # ip / sg / prefix-list
    referenced_sg_id: str | None = None
    description: str = ""
    # 추가 분석용 필드
    is_self_reference: bool = False  # 자기 자신 참조
    is_cross_account: bool = False  # 다른 계정 SG 참조
    referenced_account_id: str | None = None  # 참조된 SG의 계정 ID
    is_ipv6: bool = False  # IPv6 규칙 여부


@dataclass
class AttachedResource:
    """Security Group에 연결된 AWS 리소스 정보.

    ENI를 통해 파악된 리소스의 유형과 식별 정보를 담는다.

    Attributes:
        resource_type: 리소스 유형 (EC2, RDS, Lambda, ELB, ElastiCache, ECS 등).
        resource_id: 리소스 식별자.
        resource_name: 리소스 표시 이름 (Name 태그 또는 ID).
        eni_id: 연결된 ENI ID.
        private_ip: ENI의 프라이빗 IP 주소.
    """

    resource_type: str
    resource_id: str  # 리소스 ID
    resource_name: str  # 리소스 이름 (태그 Name 또는 ID)
    eni_id: str  # ENI ID
    private_ip: str  # 프라이빗 IP


@dataclass
class SecurityGroup:
    """Security Group 상세 정보.

    기본 메타데이터, 인바운드/아웃바운드 규칙, ENI 연결 정보,
    연결된 리소스 목록, 다른 SG에서의 참조 관계를 포함한다.

    Attributes:
        sg_id: Security Group ID (예: ``sg-0123456789abcdef0``).
        sg_name: Security Group 이름.
        description: Security Group 설명.
        vpc_id: 소속 VPC ID.
        account_id: AWS 계정 ID.
        account_name: 계정 표시 이름.
        region: AWS 리전 코드.
        is_default_sg: VPC 기본 Security Group 여부.
        is_default_vpc: Default VPC에 속하는지 여부.
        inbound_rules: 인바운드 규칙 목록.
        outbound_rules: 아웃바운드 규칙 목록.
        eni_count: 연결된 ENI 수.
        eni_descriptions: 연결된 ENI 설명 목록.
        attached_resources: ENI를 통해 파악된 연결 리소스 목록.
        referenced_by_sgs: 이 SG를 규칙에서 참조하는 다른 SG ID 집합.
    """

    sg_id: str
    sg_name: str
    description: str
    vpc_id: str
    account_id: str
    account_name: str
    region: str

    # 메타 정보
    is_default_sg: bool = False
    is_default_vpc: bool = False

    # 규칙
    inbound_rules: list[SGRule] = field(default_factory=list)
    outbound_rules: list[SGRule] = field(default_factory=list)

    # ENI 연결 정보
    eni_count: int = 0
    eni_descriptions: list[str] = field(default_factory=list)

    # 연결된 리소스 목록
    attached_resources: list[AttachedResource] = field(default_factory=list)

    # 참조 정보
    referenced_by_sgs: set[str] = field(default_factory=set)


class SGCollector:
    """Security Group 데이터 수집기.

    EC2 API를 사용하여 Security Group, VPC, ENI 정보를 수집하고
    SG 간 참조 관계와 ENI 연결 리소스를 분석한다.
    """

    def __init__(self):
        self.security_groups: dict[str, SecurityGroup] = {}  # sg_id -> SG
        self.vpc_default_map: dict[str, bool] = {}  # vpc_id -> is_default
        self.errors: list[str] = []

    def collect(self, session, account_id: str, account_name: str, region: str) -> list[SecurityGroup]:
        """단일 계정/리전에서 Security Group 데이터를 수집한다.

        VPC 정보, SG 목록, ENI 연결 정보를 순서대로 수집하고
        SG 간 참조 관계를 분석한다.

        Args:
            session: boto3 session.
            account_id: AWS 계정 ID.
            account_name: 계정 표시 이름.
            region: AWS 리전 코드.

        Returns:
            수집된 SecurityGroup 목록.
        """
        # 이전 수집 데이터 초기화 (중복 방지)
        self.security_groups.clear()
        self.vpc_default_map.clear()

        try:
            ec2 = get_client(session, "ec2", region_name=region)

            # 1. VPC 정보 수집 (Default VPC 판단용)
            self._collect_vpcs(ec2, account_id, region)

            # 2. Security Groups 수집
            self._collect_security_groups(ec2, account_id, account_name, region)

            # 3. ENI 정보 수집 (SG 연결 정보)
            self._collect_enis(ec2, account_id, region)

            # 4. SG 간 참조 관계 분석
            self._analyze_sg_references()

            return list(self.security_groups.values())

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            self.errors.append(f"{account_name}/{region}: {error_code}")
            logger.warning(f"수집 오류 [{account_id}/{region}]: {error_code}")
            return []

        except Exception as e:
            self.errors.append(f"{account_name}/{region}: {str(e)}")
            logger.error(f"수집 오류 [{account_id}/{region}]: {e}")
            return []

    def _collect_vpcs(self, ec2, account_id: str, region: str) -> None:
        """VPC 목록을 수집하여 Default VPC 여부를 매핑한다."""
        try:
            paginator = ec2.get_paginator("describe_vpcs")
            for page in paginator.paginate():
                for vpc in page.get("Vpcs", []):
                    vpc_id = vpc["VpcId"]
                    is_default = vpc.get("IsDefault", False)
                    self.vpc_default_map[vpc_id] = is_default

        except ClientError as e:
            logger.warning(f"VPC 수집 실패: {e}")

    def _collect_security_groups(self, ec2, account_id: str, account_name: str, region: str) -> None:
        """Security Group 목록을 수집하고 인바운드/아웃바운드 규칙을 파싱한다."""
        paginator = ec2.get_paginator("describe_security_groups")

        for page in paginator.paginate():
            for sg in page.get("SecurityGroups", []):
                sg_id = sg["GroupId"]
                vpc_id = sg.get("VpcId", "")

                security_group = SecurityGroup(
                    sg_id=sg_id,
                    sg_name=sg.get("GroupName", ""),
                    description=sg.get("Description", ""),
                    vpc_id=vpc_id,
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    is_default_sg=(sg.get("GroupName", "") == "default"),
                    is_default_vpc=self.vpc_default_map.get(vpc_id, False),
                )

                # 인바운드 규칙 파싱
                for rule in sg.get("IpPermissions", []):
                    security_group.inbound_rules.extend(self._parse_rules(rule, "inbound", sg_id, account_id))

                # 아웃바운드 규칙 파싱
                for rule in sg.get("IpPermissionsEgress", []):
                    security_group.outbound_rules.extend(self._parse_rules(rule, "outbound", sg_id, account_id))

                self.security_groups[sg_id] = security_group

    def _parse_rules(self, rule: dict[str, Any], direction: str, sg_id: str, account_id: str) -> list[SGRule]:
        """EC2 API 응답의 IpPermission을 SGRule 목록으로 파싱한다.

        IPv4, IPv6, SG 참조, Prefix List 등 모든 소스/대상 유형을 처리한다.

        Args:
            rule: EC2 IpPermission 딕셔너리.
            direction: 규칙 방향 (``inbound`` 또는 ``outbound``).
            sg_id: 소속 Security Group ID.
            account_id: 현재 계정 ID (cross-account 판별용).

        Returns:
            파싱된 SGRule 목록.
        """
        rules = []

        protocol = rule.get("IpProtocol", "-1")
        if protocol == "-1":
            protocol = "ALL"

        from_port = rule.get("FromPort")
        to_port = rule.get("ToPort")

        if protocol == "ALL" or from_port is None or to_port is None:
            port_range = "ALL"
        elif from_port == -1 or to_port == -1:
            # ICMP 등 포트 개념이 없는 프로토콜은 -1 반환
            port_range = "N/A"
        elif from_port == to_port:
            port_range = str(from_port)
        else:
            port_range = f"{from_port}-{to_port}"

        # IP ranges (IPv4)
        for ip_range in rule.get("IpRanges", []):
            cidr = ip_range.get("CidrIp", "")
            rules.append(
                SGRule(
                    rule_id=f"{direction}-{protocol}-{port_range}-{cidr}",
                    direction=direction,
                    protocol=protocol,
                    port_range=port_range,
                    source_dest=cidr,
                    source_dest_type="ip",
                    description=ip_range.get("Description", ""),
                    is_ipv6=False,
                )
            )

        # IPv6 ranges
        for ip_range in rule.get("Ipv6Ranges", []):
            cidr = ip_range.get("CidrIpv6", "")
            rules.append(
                SGRule(
                    rule_id=f"{direction}-{protocol}-{port_range}-{cidr}",
                    direction=direction,
                    protocol=protocol,
                    port_range=port_range,
                    source_dest=cidr,
                    source_dest_type="ip",
                    description=ip_range.get("Description", ""),
                    is_ipv6=True,
                )
            )

        # Security Group references
        for sg_ref in rule.get("UserIdGroupPairs", []):
            ref_sg_id = sg_ref.get("GroupId", "")
            ref_account_id = sg_ref.get("UserId", "")

            # Self 참조 및 Cross-account 판단
            is_self = ref_sg_id == sg_id
            is_cross = ref_account_id != "" and ref_account_id != account_id

            rules.append(
                SGRule(
                    rule_id=f"{direction}-{protocol}-{port_range}-{ref_sg_id}",
                    direction=direction,
                    protocol=protocol,
                    port_range=port_range,
                    source_dest=ref_sg_id,
                    source_dest_type="sg",
                    referenced_sg_id=ref_sg_id,
                    description=sg_ref.get("Description", ""),
                    is_self_reference=is_self,
                    is_cross_account=is_cross,
                    referenced_account_id=ref_account_id if is_cross else None,
                )
            )

        # Prefix lists
        for pl_ref in rule.get("PrefixListIds", []):
            pl_id = pl_ref.get("PrefixListId", "")
            rules.append(
                SGRule(
                    rule_id=f"{direction}-{protocol}-{port_range}-{pl_id}",
                    direction=direction,
                    protocol=protocol,
                    port_range=port_range,
                    source_dest=pl_id,
                    source_dest_type="prefix-list",
                    description=pl_ref.get("Description", ""),
                )
            )

        return rules

    def _collect_enis(self, ec2, account_id: str, region: str) -> None:
        """ENI 목록을 수집하고 각 SG에 연결된 리소스 정보를 매핑한다."""
        try:
            paginator = ec2.get_paginator("describe_network_interfaces")

            for page in paginator.paginate():
                for eni in page.get("NetworkInterfaces", []):
                    eni_id = eni.get("NetworkInterfaceId", "")
                    eni_desc = eni.get("Description", "")
                    private_ip = eni.get("PrivateIpAddress", "")

                    # 리소스 유형 및 ID 파악
                    resource_type, resource_id, resource_name = self._parse_eni_resource(eni)

                    # 이 ENI에 연결된 SG들
                    for group in eni.get("Groups", []):
                        sg_id = group.get("GroupId")
                        if sg_id in self.security_groups:
                            self.security_groups[sg_id].eni_count += 1
                            if eni_desc:
                                self.security_groups[sg_id].eni_descriptions.append(eni_desc)

                            # 연결된 리소스 정보 추가
                            if resource_type:
                                attached = AttachedResource(
                                    resource_type=resource_type,
                                    resource_id=resource_id,
                                    resource_name=resource_name,
                                    eni_id=eni_id,
                                    private_ip=private_ip,
                                )
                                self.security_groups[sg_id].attached_resources.append(attached)

        except ClientError as e:
            logger.warning(f"ENI 수집 실패: {e}")

    def _parse_eni_resource(self, eni: dict[str, Any]) -> tuple[str, str, str]:
        """ENI에서 연결된 리소스 유형/ID 파악

        Returns:
            (resource_type, resource_id, resource_name)
        """
        eni_desc = eni.get("Description", "")
        attachment = eni.get("Attachment", {})
        instance_id = attachment.get("InstanceId", "")

        # EC2 인스턴스
        if instance_id:
            # 태그에서 Name 추출
            tags = {t["Key"]: t["Value"] for t in eni.get("TagSet", [])}
            instance_name = tags.get("Name", instance_id)
            return "EC2", instance_id, instance_name

        # Description 기반 리소스 파악
        desc_lower = eni_desc.lower()

        # RDS
        if "rds" in desc_lower or eni_desc.startswith("RDS"):
            # "RDSNetworkInterface" 또는 DB 식별자 추출
            resource_id = eni_desc
            if ":" in eni_desc:
                parts = eni_desc.split(":")
                resource_id = parts[-1] if parts else eni_desc
            return "RDS", resource_id, eni_desc

        # Lambda
        if "lambda" in desc_lower or eni_desc.startswith("AWS Lambda VPC ENI"):
            # 함수 이름 추출 시도
            if ":" in eni_desc:
                parts = eni_desc.split(":")
                func_name = parts[-1] if parts else eni_desc
                return "Lambda", func_name, func_name
            return "Lambda", eni_desc, eni_desc

        # ELB (ALB/NLB/CLB)
        if eni_desc.startswith("ELB ") or "elb" in desc_lower:
            # "ELB app/my-alb/..." 또는 "ELB net/my-nlb/..."
            parts = eni_desc.split("/")
            if len(parts) >= 2:
                elb_type = "ALB" if "app/" in eni_desc else "NLB" if "net/" in eni_desc else "CLB"
                elb_name = parts[1] if len(parts) > 1 else eni_desc
                return elb_type, elb_name, eni_desc
            return "ELB", eni_desc, eni_desc

        # ElastiCache
        if "elasticache" in desc_lower:
            return "ElastiCache", eni_desc, eni_desc

        # ECS
        if "ecs" in desc_lower or eni_desc.startswith("ecs-managed"):
            return "ECS", eni_desc, eni_desc

        # VPC Endpoint
        if "vpce" in desc_lower or eni_desc.startswith("VPC Endpoint"):
            return "VPCEndpoint", eni_desc, eni_desc

        # NAT Gateway
        if "nat" in desc_lower and "gateway" in desc_lower:
            return "NATGateway", eni_desc, eni_desc

        # OpenSearch / Elasticsearch
        if "opensearch" in desc_lower or "elasticsearch" in desc_lower:
            return "OpenSearch", eni_desc, eni_desc

        # Redshift
        if "redshift" in desc_lower:
            return "Redshift", eni_desc, eni_desc

        # 기타 (Description이 있으면)
        if eni_desc:
            return "Other", eni_desc, eni_desc

        return "", "", ""

    def _analyze_sg_references(self) -> None:
        """SG 간 참조 관계를 분석하여 ``referenced_by_sgs`` 필드를 갱신한다."""
        for sg in self.security_groups.values():
            all_rules = sg.inbound_rules + sg.outbound_rules

            for rule in all_rules:
                if rule.source_dest_type == "sg" and rule.referenced_sg_id:
                    ref_sg_id = rule.referenced_sg_id
                    # 참조되는 SG에 "누가 나를 참조하는지" 기록
                    if ref_sg_id in self.security_groups:
                        self.security_groups[ref_sg_id].referenced_by_sgs.add(sg.sg_id)
