"""
plugins/vpc/ip_search/detail.py - ENI 상세 조회

AWS API를 호출하여 ENI에 연결된 리소스의 상세 정보를 조회합니다.
캐시 기반 빠른 검색과 달리, 정확한 실시간 정보를 제공합니다.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import botocore.config
import botocore.exceptions

logger = logging.getLogger(__name__)

# API 호출 타임아웃 설정
_API_CONFIG = botocore.config.Config(
    read_timeout=8,
    connect_timeout=3,
    retries={"max_attempts": 1},
)


def get_detailed_resource_info(session, eni: dict[str, Any]) -> str | None:
    """
    ENI에 연결된 리소스의 상세 정보를 API 호출로 조회

    Args:
        session: boto3 세션
        eni: ENI 정보 딕셔너리

    Returns:
        상세 리소스 정보 문자열 또는 None
    """
    if not session or not eni:
        return None

    interface_type = eni.get("InterfaceType", "")
    description = eni.get("Description", "")
    attachment = eni.get("Attachment", {})
    eni_id = eni.get("NetworkInterfaceId", "")
    region = eni.get("Region", "")

    # FAST PATH: Description에서 빠르게 추출 가능한 경우
    fast_result = _fast_extract_from_description(description, interface_type)
    if fast_result:
        return fast_result

    try:
        # EC2 Instance
        if attachment.get("InstanceId"):
            return _get_ec2_info(session, attachment["InstanceId"], region)

        # ECS Task
        if "ecs" in interface_type.lower() or "ecs" in description.lower():
            result = _get_ecs_info(session, eni_id, region)
            if result:
                return result

        # EKS Fargate
        if "fargate" in description.lower():
            result = _get_eks_fargate_info(session, eni, region)
            if result:
                return result

        # Lambda
        if "lambda" in description.lower():
            result = _get_lambda_info(session, eni, region, eni_id)
            if result:
                return result

        # VPC Endpoint
        if "vpc endpoint" in description.lower():
            result = _get_vpc_endpoint_info(session, eni_id, region)
            if result:
                return result

        # OpenSearch / Elasticsearch
        if "opensearch" in description.lower() or "elasticsearch" in description.lower():
            result = _get_opensearch_info(session, eni, region)
            if result:
                return result

        # ElastiCache
        if "elasticache" in description.lower():
            result = _get_elasticache_info(session, eni, region)
            if result:
                return result

        # NAT Gateway
        if "nat gateway" in description.lower() or interface_type == "nat_gateway":
            result = _get_nat_gateway_info(session, description, region)
            if result:
                return result

        # Transit Gateway
        if "transit gateway" in description.lower():
            result = _get_transit_gateway_info(session, description, region)
            if result:
                return result

        # API Gateway
        if "api gateway" in description.lower():
            result = _get_api_gateway_info(session, eni_id, description, region)
            if result:
                return result

        # Route 53 Resolver
        if "route 53 resolver" in description.lower():
            result = _get_route53_resolver_info(session, eni, region)
            if result:
                return result

        # EFS
        if "efs" in description.lower() or "mount target" in description.lower():
            result = _get_efs_info(session, eni_id, description, region)
            if result:
                return result

        # FSx
        if "fsx" in description.lower():
            result = _get_fsx_info(session, eni_id, description, region)
            if result:
                return result

        return description if description else None

    except Exception as e:
        logger.debug(f"ENI {eni_id} 상세 조회 중 오류: {e}")
        return None


def enrich_resources_parallel(
    enis: list[dict[str, Any]],
    session,
    max_workers: int = 10,
) -> dict[str, str | None]:
    """
    Enrich multiple ENIs with detailed resource information in parallel.

    Uses ThreadPoolExecutor to make concurrent API calls, significantly
    speeding up detail enrichment for multiple ENIs.

    Args:
        enis: List of ENI data dictionaries
        session: boto3 session for API calls
        max_workers: Maximum number of concurrent workers (default: 10)

    Returns:
        Dictionary mapping ENI ID to enriched resource info string
    """
    if not enis or not session:
        return {}

    results: dict[str, str | None] = {}

    def _enrich_single(eni: dict[str, Any]) -> tuple[str, str | None]:
        """Enrich a single ENI and return (eni_id, result)."""
        eni_id = eni.get("NetworkInterfaceId", "")
        try:
            result = get_detailed_resource_info(session, eni)
            return (eni_id, result)
        except Exception as e:
            logger.debug(f"Error enriching {eni_id}: {e}")
            return (eni_id, None)

    # Use ThreadPoolExecutor for parallel API calls
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_eni = {executor.submit(_enrich_single, eni): eni for eni in enis}

        # Collect results as they complete
        for future in as_completed(future_to_eni):
            try:
                eni_id, enriched_info = future.result()
                results[eni_id] = enriched_info
            except Exception as e:
                eni = future_to_eni[future]
                eni_id = eni.get("NetworkInterfaceId", "unknown")
                logger.debug(f"Future error for {eni_id}: {e}")
                results[eni_id] = None

    return results


def _fast_extract_from_description(description: str, interface_type: str) -> str | None:
    """Description에서 빠르게 정보 추출 (API 호출 없음)"""
    from plugins.vpc.ip_search.parser import parse_eni_description

    parsed = parse_eni_description(description, interface_type)
    if parsed:
        return str(parsed)
    return None


def _get_ec2_info(session, instance_id: str, region: str) -> str | None:
    """EC2 인스턴스 상세 정보"""
    try:
        ec2 = session.client("ec2", region_name=region, config=_API_CONFIG)
        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = response["Reservations"][0]["Instances"][0]

        name = next(
            (tag["Value"] for tag in instance.get("Tags", []) if tag["Key"] == "Name"),
            "Unnamed",
        )
        instance_type = instance.get("InstanceType", "")
        state = instance.get("State", {}).get("Name", "")

        return f"EC2: {name} ({instance_type}) - {state}"
    except Exception as e:
        logger.debug(f"EC2 정보 조회 실패: {e}")
        return f"EC2: {instance_id}"


def _get_ecs_info(session, eni_id: str, region: str) -> str | None:
    """ECS 서비스 정보"""
    try:
        ec2 = session.client("ec2", region_name=region, config=_API_CONFIG)
        ecs = session.client("ecs", region_name=region, config=_API_CONFIG)

        eni_response = ec2.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
        description = eni_response["NetworkInterfaces"][0].get("Description", "")

        if "attachment" not in description:
            return "ECS Task"

        attachment_id = (
            description.split("attachment/")[-1] if "attachment/" in description else description.split("/")[-1]
        )
        if not attachment_id:
            return "ECS Task"

        clusters = ecs.list_clusters().get("clusterArns", [])

        for cluster in clusters[:5]:
            try:
                tasks = ecs.list_tasks(cluster=cluster).get("taskArns", [])
                if not tasks:
                    continue

                task_details = ecs.describe_tasks(cluster=cluster, tasks=tasks[:10])
                for task in task_details.get("tasks", []):
                    for att in task.get("attachments", []):
                        if att.get("id") == attachment_id:
                            group = task.get("group", "")
                            service_name = group.split("service:")[1] if group.startswith("service:") else "Unknown"
                            cluster_name = cluster.split("/")[-1]
                            return f"ECS: {service_name} (Cluster: {cluster_name})"
            except Exception as e:
                logger.debug("Failed to get details: %s", e)
                continue

        return "ECS Task"
    except Exception as e:
        logger.debug(f"ECS 정보 조회 실패: {e}")
        return "ECS Task"


def _get_eks_fargate_info(session, eni: dict[str, Any], region: str) -> str | None:
    """EKS Fargate Pod 정보"""
    try:
        eks = session.client("eks", region_name=region, config=_API_CONFIG)
        clusters = eks.list_clusters().get("clusters", [])

        for cluster_name in clusters[:3]:
            try:
                profiles = eks.list_fargate_profiles(clusterName=cluster_name).get("fargateProfileNames", [])
                for profile in profiles:
                    profile_details = eks.describe_fargate_profile(
                        clusterName=cluster_name, fargateProfileName=profile
                    ).get("fargateProfile", {})

                    if eni.get("SubnetId") in profile_details.get("subnets", []):
                        namespaces = [s.get("namespace") for s in profile_details.get("selectors", [])]
                        return f"EKS Fargate: {cluster_name}/{profile} (NS: {', '.join(namespaces)})"
            except Exception as e:
                logger.debug("Failed to get details: %s", e)
                continue

        return "EKS Fargate Pod"
    except Exception as e:
        logger.debug(f"EKS Fargate 정보 조회 실패: {e}")
        return "EKS Fargate Pod"


def _get_lambda_info(session, eni: dict[str, Any], region: str, eni_id: str) -> str | None:
    """Lambda 함수 정보"""
    try:
        lambda_client = session.client("lambda", region_name=region, config=_API_CONFIG)

        eni_vpc_id = eni.get("VpcId")
        eni_subnet_id = eni.get("SubnetId")
        eni_security_groups = set(sg.get("GroupId") for sg in eni.get("Groups", []))

        paginator = lambda_client.get_paginator("list_functions")

        for page in paginator.paginate():
            for function in page.get("Functions", []):
                vpc_config = function.get("VpcConfig")
                if not vpc_config:
                    continue

                if vpc_config.get("VpcId") != eni_vpc_id:
                    continue

                if eni_subnet_id not in set(vpc_config.get("SubnetIds", [])):
                    continue

                func_sgs = set(vpc_config.get("SecurityGroupIds", []))
                if not (eni_security_groups & func_sgs):
                    continue

                runtime = function.get("Runtime", "Unknown")
                return f"Lambda: {function['FunctionName']} ({runtime})"

        return "Lambda Function"
    except Exception as e:
        logger.debug(f"Lambda 정보 조회 실패: {e}")
        return "Lambda Function"


def _get_vpc_endpoint_info(session, eni_id: str, region: str) -> str | None:
    """VPC Endpoint 정보"""
    try:
        ec2 = session.client("ec2", region_name=region, config=_API_CONFIG)
        endpoints = ec2.describe_vpc_endpoints().get("VpcEndpoints", [])

        for endpoint in endpoints:
            if eni_id in endpoint.get("NetworkInterfaceIds", []):
                endpoint_id = endpoint.get("VpcEndpointId")
                service_name = endpoint.get("ServiceName", "").split(".")[-1]

                name = next(
                    (tag["Value"] for tag in endpoint.get("Tags", []) if tag["Key"] == "Name"),
                    None,
                )
                display = name or endpoint_id
                return f"VPC Endpoint: {display} ({service_name})"

        return "VPC Endpoint"
    except Exception as e:
        logger.debug(f"VPC Endpoint 정보 조회 실패: {e}")
        return "VPC Endpoint"


def _get_opensearch_info(session, eni: dict[str, Any], region: str) -> str | None:
    """OpenSearch 도메인 정보"""
    try:
        opensearch = session.client("opensearch", region_name=region, config=_API_CONFIG)
        domains = opensearch.list_domain_names().get("DomainNames", [])

        eni_vpc_id = eni.get("VpcId")
        eni_subnet_id = eni.get("SubnetId")
        eni_security_groups = set(sg.get("GroupId") for sg in eni.get("Groups", []))

        for domain_info in domains[:5]:
            domain_name = domain_info.get("DomainName")
            try:
                detail = opensearch.describe_domain(DomainName=domain_name).get("DomainStatus", {})
                vpc_options = detail.get("VPCOptions", {})

                if vpc_options.get("VPCId") != eni_vpc_id:
                    continue
                if eni_subnet_id not in set(vpc_options.get("SubnetIds", [])):
                    continue

                domain_sgs = set(vpc_options.get("SecurityGroupIds", []))
                if not (eni_security_groups & domain_sgs):
                    continue

                engine_version = detail.get("EngineVersion", "").replace("OpenSearch_", "")
                return f"OpenSearch: {domain_name} (v{engine_version})"
            except Exception as e:
                logger.debug("Failed to get details: %s", e)
                continue

        return "OpenSearch Domain"
    except Exception as e:
        logger.debug(f"OpenSearch 정보 조회 실패: {e}")
        return "OpenSearch Domain"


def _get_elasticache_info(session, eni: dict[str, Any], region: str) -> str | None:
    """ElastiCache 클러스터 정보"""
    try:
        elasticache = session.client("elasticache", region_name=region, config=_API_CONFIG)

        eni_vpc_id = eni.get("VpcId")
        eni_subnet_id = eni.get("SubnetId")

        clusters = elasticache.describe_cache_clusters(ShowCacheNodeInfo=True).get("CacheClusters", [])

        for cluster in clusters[:10]:
            cluster_id = cluster.get("CacheClusterId")
            engine = cluster.get("Engine", "")
            cache_subnet_group = cluster.get("CacheSubnetGroupName")

            if not cache_subnet_group:
                continue

            try:
                subnet_group = elasticache.describe_cache_subnet_groups(CacheSubnetGroupName=cache_subnet_group).get(
                    "CacheSubnetGroups", [{}]
                )[0]

                if subnet_group.get("VpcId") != eni_vpc_id:
                    continue

                subnet_ids = set(s["SubnetIdentifier"] for s in subnet_group.get("Subnets", []))
                if eni_subnet_id not in subnet_ids:
                    continue

                return f"ElastiCache: {cluster_id} ({engine})"
            except Exception as e:
                logger.debug("Failed to get details: %s", e)
                continue

        return "ElastiCache Cluster"
    except Exception as e:
        logger.debug(f"ElastiCache 정보 조회 실패: {e}")
        return "ElastiCache Cluster"


def _get_nat_gateway_info(session, description: str, region: str) -> str | None:
    """NAT Gateway 정보"""
    try:
        nat_match = re.search(r"nat-[a-zA-Z0-9]+", description)
        if not nat_match:
            return "NAT Gateway"

        nat_id = nat_match.group(0)
        ec2 = session.client("ec2", region_name=region, config=_API_CONFIG)
        response = ec2.describe_nat_gateways(NatGatewayIds=[nat_id])

        if response.get("NatGateways"):
            nat = response["NatGateways"][0]
            name = next(
                (tag["Value"] for tag in nat.get("Tags", []) if tag["Key"] == "Name"),
                None,
            )
            state = nat.get("State", "")
            display = name or nat_id
            return f"NAT Gateway: {display} ({state})"

        return f"NAT Gateway: {nat_id}"
    except Exception as e:
        logger.debug(f"NAT Gateway 정보 조회 실패: {e}")
        return "NAT Gateway"


def _get_transit_gateway_info(session, description: str, region: str) -> str | None:
    """Transit Gateway 정보"""
    try:
        tgw_match = re.search(r"tgw-attach-[a-zA-Z0-9]+", description)
        if not tgw_match:
            return "Transit Gateway"

        attachment_id = tgw_match.group(0)
        ec2 = session.client("ec2", region_name=region, config=_API_CONFIG)
        response = ec2.describe_transit_gateway_attachments(TransitGatewayAttachmentIds=[attachment_id])

        if response.get("TransitGatewayAttachments"):
            att = response["TransitGatewayAttachments"][0]
            name = next(
                (tag["Value"] for tag in att.get("Tags", []) if tag["Key"] == "Name"),
                None,
            )
            display = name or attachment_id
            return f"Transit Gateway: {display}"

        return f"Transit Gateway: {attachment_id}"
    except Exception as e:
        logger.debug(f"Transit Gateway 정보 조회 실패: {e}")
        return "Transit Gateway"


def _get_api_gateway_info(session, eni_id: str, description: str, region: str) -> str | None:
    """API Gateway 정보"""
    try:
        if "VPC Link" in description:
            apigw = session.client("apigateway", region_name=region, config=_API_CONFIG)
            vpc_links = apigw.get_vpc_links().get("items", [])

            for vpc_link in vpc_links:
                name = vpc_link.get("name", "Unnamed")
                status = vpc_link.get("status", "")
                return f"API Gateway VPC Link: {name} ({status})"

        return "API Gateway"
    except Exception as e:
        logger.debug(f"API Gateway 정보 조회 실패: {e}")
        return "API Gateway"


def _get_route53_resolver_info(session, eni: dict[str, Any], region: str) -> str | None:
    """Route 53 Resolver 정보"""
    try:
        resolver = session.client("route53resolver", region_name=region, config=_API_CONFIG)
        endpoints = resolver.list_resolver_endpoints().get("ResolverEndpoints", [])

        eni_subnet_id = eni.get("SubnetId")

        for endpoint in endpoints:
            endpoint_id = endpoint.get("Id")
            endpoint_name = endpoint.get("Name", "Unnamed")
            direction = endpoint.get("Direction", "")

            try:
                detail = resolver.get_resolver_endpoint(ResolverEndpointId=endpoint_id)
                ip_addresses = detail.get("ResolverEndpoint", {}).get("IpAddresses", [])

                for ip_addr in ip_addresses:
                    if ip_addr.get("SubnetId") == eni_subnet_id:
                        return f"Route53 Resolver: {endpoint_name} ({direction.lower()})"
            except Exception as e:
                logger.debug("Failed to get details: %s", e)
                continue

        return "Route53 Resolver"
    except Exception as e:
        logger.debug(f"Route53 Resolver 정보 조회 실패: {e}")
        return "Route53 Resolver"


def _get_efs_info(session, eni_id: str, description: str, region: str) -> str | None:
    """EFS 정보"""
    try:
        fs_match = re.search(r"fs-[a-zA-Z0-9]+", description)
        if fs_match:
            fs_id = fs_match.group(0)
            efs = session.client("efs", region_name=region, config=_API_CONFIG)

            try:
                fs_info = efs.describe_file_systems(FileSystemId=fs_id).get("FileSystems", [{}])[0]
                name = next(
                    (tag["Value"] for tag in fs_info.get("Tags", []) if tag["Key"] == "Name"),
                    None,
                )
                size = fs_info.get("SizeInBytes", {}).get("Value", 0) / (1024**3)
                display = name or fs_id
                return f"EFS: {display} ({size:.1f} GB)"
            except Exception as e:
                logger.debug("Failed to get EFS details: %s", e)
                return f"EFS: {fs_id}"

        return "EFS"
    except Exception as e:
        logger.debug(f"EFS 정보 조회 실패: {e}")
        return "EFS"


def _get_fsx_info(session, eni_id: str, description: str, region: str) -> str | None:
    """FSx 정보"""
    try:
        fs_match = re.search(r"fs-[a-zA-Z0-9]+", description)
        if fs_match:
            fs_id = fs_match.group(0)
            fsx = session.client("fsx", region_name=region, config=_API_CONFIG)

            try:
                fs_info = fsx.describe_file_systems(FileSystemIds=[fs_id]).get("FileSystems", [{}])[0]
                fs_type = fs_info.get("FileSystemType", "Unknown")
                storage = fs_info.get("StorageCapacity", 0)
                return f"FSx ({fs_type}): {fs_id} ({storage} GB)"
            except Exception as e:
                logger.debug("Failed to get FSx details: %s", e)
                return f"FSx: {fs_id}"

        return "FSx"
    except Exception as e:
        logger.debug(f"FSx 정보 조회 실패: {e}")
        return "FSx"
