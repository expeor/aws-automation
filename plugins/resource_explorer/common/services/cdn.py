"""
plugins/resource_explorer/common/services/cdn.py - CDN/DNS 리소스 수집

CloudFront Distribution, Route 53 Hosted Zone 수집.
"""

import logging

from core.parallel import get_client

from ..types import CloudFrontDistribution, Route53HostedZone

logger = logging.getLogger(__name__)


def collect_cloudfront_distributions(
    session, account_id: str, account_name: str, region: str
) -> list[CloudFrontDistribution]:
    """CloudFront Distribution 수집 (글로벌 리소스)"""
    # CloudFront는 글로벌 서비스이므로 us-east-1에서만 수집
    if region != "us-east-1":
        return []

    cf = get_client(session, "cloudfront", region_name=region)
    distributions = []

    paginator = cf.get_paginator("list_distributions")
    for page in paginator.paginate():
        dist_list = page.get("DistributionList", {})
        for dist in dist_list.get("Items", []):
            dist_id = dist["Id"]
            dist_arn = dist["ARN"]

            # Aliases
            aliases = dist.get("Aliases", {}).get("Items", [])

            # Origins 수
            origin_count = dist.get("Origins", {}).get("Quantity", 0)

            # 태그 조회
            tags = {}
            try:
                tags_resp = cf.list_tags_for_resource(Resource=dist_arn)
                for tag in tags_resp.get("Tags", {}).get("Items", []):
                    tags[tag["Key"]] = tag["Value"]
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            distributions.append(
                CloudFrontDistribution(
                    account_id=account_id,
                    account_name=account_name,
                    region="global",
                    distribution_id=dist_id,
                    distribution_arn=dist_arn,
                    domain_name=dist.get("DomainName", ""),
                    status=dist.get("Status", ""),
                    enabled=dist.get("Enabled", True),
                    origin_count=origin_count,
                    aliases=aliases,
                    price_class=dist.get("PriceClass", ""),
                    http_version=dist.get("HttpVersion", ""),
                    is_ipv6_enabled=dist.get("IsIPV6Enabled", False),
                    web_acl_id=dist.get("WebACLId", ""),
                    last_modified_time=dist.get("LastModifiedTime"),
                    tags=tags,
                )
            )

    return distributions


def collect_route53_hosted_zones(session, account_id: str, account_name: str, region: str) -> list[Route53HostedZone]:
    """Route 53 Hosted Zone 수집 (글로벌 리소스)"""
    # Route 53는 글로벌 서비스이므로 us-east-1에서만 수집
    if region != "us-east-1":
        return []

    route53 = get_client(session, "route53", region_name=region)
    zones = []

    paginator = route53.get_paginator("list_hosted_zones")
    for page in paginator.paginate():
        for zone in page.get("HostedZones", []):
            zone_id = zone["Id"].replace("/hostedzone/", "")
            zone_name = zone["Name"]
            is_private = zone.get("Config", {}).get("PrivateZone", False)
            comment = zone.get("Config", {}).get("Comment", "")
            record_count = zone.get("ResourceRecordSetCount", 0)

            # Private Zone의 경우 VPC 조회
            vpc_ids = []
            if is_private:
                try:
                    detail_resp = route53.get_hosted_zone(Id=zone_id)
                    for vpc in detail_resp.get("VPCs", []):
                        vpc_ids.append(vpc.get("VPCId", ""))
                except Exception:
                    pass

            # 태그 조회
            tags = {}
            try:
                tags_resp = route53.list_tags_for_resource(ResourceType="hostedzone", ResourceId=zone_id)
                for tag in tags_resp.get("ResourceTagSet", {}).get("Tags", []):
                    tags[tag["Key"]] = tag["Value"]
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            zones.append(
                Route53HostedZone(
                    account_id=account_id,
                    account_name=account_name,
                    region="global",
                    zone_id=zone_id,
                    name=zone_name,
                    record_count=record_count,
                    is_private=is_private,
                    comment=comment,
                    vpc_ids=vpc_ids,
                    tags=tags,
                )
            )

    return zones
