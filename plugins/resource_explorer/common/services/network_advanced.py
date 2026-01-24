"""
plugins/resource_explorer/common/services/network_advanced.py - 고급 네트워크 리소스 수집

Transit Gateway, VPN, Network ACL, VPC Peering 수집.
"""

from core.parallel import get_client

from ..types import (
    NetworkACL,
    TransitGateway,
    TransitGatewayAttachment,
    VPCPeeringConnection,
    VPNConnection,
    VPNGateway,
)
from .helpers import parse_tags


def collect_transit_gateways(session, account_id: str, account_name: str, region: str) -> list[TransitGateway]:
    """Transit Gateway 수집"""
    ec2 = get_client(session, "ec2", region_name=region)
    tgws = []

    try:
        paginator = ec2.get_paginator("describe_transit_gateways")
        for page in paginator.paginate():
            for tgw in page.get("TransitGateways", []):
                tags = parse_tags(tgw.get("Tags"))
                options = tgw.get("Options", {})

                tgws.append(
                    TransitGateway(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        tgw_id=tgw.get("TransitGatewayId", ""),
                        tgw_arn=tgw.get("TransitGatewayArn", ""),
                        name=tags.get("Name", ""),
                        state=tgw.get("State", ""),
                        owner_id=tgw.get("OwnerId", ""),
                        description=tgw.get("Description", ""),
                        amazon_side_asn=options.get("AmazonSideAsn", 0),
                        default_route_table_id=options.get("AssociationDefaultRouteTableId", ""),
                        auto_accept_shared_attachments=options.get("AutoAcceptSharedAttachments", ""),
                        dns_support=options.get("DnsSupport", ""),
                        vpn_ecmp_support=options.get("VpnEcmpSupport", ""),
                        creation_time=tgw.get("CreationTime"),
                        tags=tags,
                    )
                )
    except Exception:
        pass

    return tgws


def collect_transit_gateway_attachments(
    session, account_id: str, account_name: str, region: str
) -> list[TransitGatewayAttachment]:
    """Transit Gateway Attachment 수집"""
    ec2 = get_client(session, "ec2", region_name=region)
    attachments = []

    try:
        paginator = ec2.get_paginator("describe_transit_gateway_attachments")
        for page in paginator.paginate():
            for att in page.get("TransitGatewayAttachments", []):
                tags = parse_tags(att.get("Tags"))

                attachments.append(
                    TransitGatewayAttachment(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        attachment_id=att.get("TransitGatewayAttachmentId", ""),
                        tgw_id=att.get("TransitGatewayId", ""),
                        resource_id=att.get("ResourceId", ""),
                        resource_type=att.get("ResourceType", ""),
                        resource_owner_id=att.get("ResourceOwnerId", ""),
                        state=att.get("State", ""),
                        association_state=att.get("Association", {}).get("State", ""),
                        creation_time=att.get("CreationTime"),
                        tags=tags,
                    )
                )
    except Exception:
        pass

    return attachments


def collect_vpn_gateways(session, account_id: str, account_name: str, region: str) -> list[VPNGateway]:
    """VPN Gateway 수집"""
    ec2 = get_client(session, "ec2", region_name=region)
    gateways = []

    try:
        resp = ec2.describe_vpn_gateways()
        for vgw in resp.get("VpnGateways", []):
            tags = parse_tags(vgw.get("Tags"))

            # VPC Attachment IDs
            vpc_attachments = [
                att.get("VpcId", "") for att in vgw.get("VpcAttachments", []) if att.get("State") == "attached"
            ]

            gateways.append(
                VPNGateway(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    vpn_gateway_id=vgw.get("VpnGatewayId", ""),
                    name=tags.get("Name", ""),
                    state=vgw.get("State", ""),
                    vpn_type=vgw.get("Type", ""),
                    amazon_side_asn=vgw.get("AmazonSideAsn", 0),
                    availability_zone=vgw.get("AvailabilityZone", ""),
                    vpc_attachments=vpc_attachments,
                    tags=tags,
                )
            )
    except Exception:
        pass

    return gateways


def collect_vpn_connections(session, account_id: str, account_name: str, region: str) -> list[VPNConnection]:
    """VPN Connection 수집"""
    ec2 = get_client(session, "ec2", region_name=region)
    connections = []

    try:
        resp = ec2.describe_vpn_connections()
        for vpn in resp.get("VpnConnections", []):
            tags = parse_tags(vpn.get("Tags"))

            connections.append(
                VPNConnection(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    vpn_connection_id=vpn.get("VpnConnectionId", ""),
                    name=tags.get("Name", ""),
                    state=vpn.get("State", ""),
                    vpn_type=vpn.get("Type", ""),
                    customer_gateway_id=vpn.get("CustomerGatewayId", ""),
                    vpn_gateway_id=vpn.get("VpnGatewayId", ""),
                    transit_gateway_id=vpn.get("TransitGatewayId", ""),
                    category=vpn.get("Category", ""),
                    static_routes_only=vpn.get("Options", {}).get("StaticRoutesOnly", False),
                    tags=tags,
                )
            )
    except Exception:
        pass

    return connections


def collect_network_acls(session, account_id: str, account_name: str, region: str) -> list[NetworkACL]:
    """Network ACL 수집"""
    ec2 = get_client(session, "ec2", region_name=region)
    nacls = []

    paginator = ec2.get_paginator("describe_network_acls")
    for page in paginator.paginate():
        for nacl in page.get("NetworkAcls", []):
            tags = parse_tags(nacl.get("Tags"))

            # 규칙 수 계산
            entries = nacl.get("Entries", [])
            inbound_count = len([e for e in entries if not e.get("Egress", False)])
            outbound_count = len([e for e in entries if e.get("Egress", False)])

            # 연결된 서브넷
            associated_subnets = [assoc.get("SubnetId", "") for assoc in nacl.get("Associations", [])]

            nacls.append(
                NetworkACL(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    nacl_id=nacl.get("NetworkAclId", ""),
                    name=tags.get("Name", ""),
                    vpc_id=nacl.get("VpcId", ""),
                    is_default=nacl.get("IsDefault", False),
                    inbound_rule_count=inbound_count,
                    outbound_rule_count=outbound_count,
                    associated_subnets=associated_subnets,
                    tags=tags,
                )
            )

    return nacls


def collect_vpc_peering_connections(
    session, account_id: str, account_name: str, region: str
) -> list[VPCPeeringConnection]:
    """VPC Peering Connection 수집"""
    ec2 = get_client(session, "ec2", region_name=region)
    peerings = []

    paginator = ec2.get_paginator("describe_vpc_peering_connections")
    for page in paginator.paginate():
        for pcx in page.get("VpcPeeringConnections", []):
            tags = parse_tags(pcx.get("Tags"))

            requester = pcx.get("RequesterVpcInfo", {})
            accepter = pcx.get("AccepterVpcInfo", {})

            peerings.append(
                VPCPeeringConnection(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    peering_id=pcx.get("VpcPeeringConnectionId", ""),
                    name=tags.get("Name", ""),
                    status=pcx.get("Status", {}).get("Code", ""),
                    requester_vpc_id=requester.get("VpcId", ""),
                    requester_owner_id=requester.get("OwnerId", ""),
                    requester_cidr=requester.get("CidrBlock", ""),
                    accepter_vpc_id=accepter.get("VpcId", ""),
                    accepter_owner_id=accepter.get("OwnerId", ""),
                    accepter_cidr=accepter.get("CidrBlock", ""),
                    tags=tags,
                )
            )

    return peerings
