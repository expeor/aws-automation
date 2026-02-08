"""
core/shared/aws/inventory/services/compute.py - Compute 리소스 수집

EBS Volume, Lambda Function, ECS Cluster/Service, ASG, Launch Template, EKS, AMI, Snapshot 수집.
"""

from __future__ import annotations

import logging

from core.parallel import get_client

from ..types import (
    AMI,
    AutoScalingGroup,
    EBSVolume,
    ECSCluster,
    ECSService,
    EKSCluster,
    EKSNodeGroup,
    LambdaFunction,
    LaunchTemplate,
    Snapshot,
)
from .helpers import parse_tags

logger = logging.getLogger(__name__)


def collect_ebs_volumes(session, account_id: str, account_name: str, region: str) -> list[EBSVolume]:
    """EBS Volume 리소스를 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        EBSVolume 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    volumes = []

    paginator = ec2.get_paginator("describe_volumes")
    for page in paginator.paginate():
        for vol in page.get("Volumes", []):
            tags = parse_tags(vol.get("Tags"))

            # 연결된 인스턴스 정보
            attachments = vol.get("Attachments", [])
            instance_id = ""
            device_name = ""
            if attachments:
                instance_id = attachments[0].get("InstanceId", "")
                device_name = attachments[0].get("Device", "")

            volumes.append(
                EBSVolume(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    volume_id=vol["VolumeId"],
                    name=tags.get("Name", ""),
                    size_gb=vol.get("Size", 0),
                    volume_type=vol.get("VolumeType", ""),
                    state=vol.get("State", ""),
                    availability_zone=vol.get("AvailabilityZone", ""),
                    iops=vol.get("Iops", 0),
                    throughput=vol.get("Throughput", 0),
                    encrypted=vol.get("Encrypted", False),
                    kms_key_id=vol.get("KmsKeyId", ""),
                    snapshot_id=vol.get("SnapshotId", ""),
                    instance_id=instance_id,
                    device_name=device_name,
                    create_time=vol.get("CreateTime"),
                    tags=tags,
                )
            )

    return volumes


def collect_lambda_functions(session, account_id: str, account_name: str, region: str) -> list[LambdaFunction]:
    """Lambda Function 리소스를 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        LambdaFunction 데이터 클래스 목록
    """
    lambda_client = get_client(session, "lambda", region_name=region)
    functions = []

    paginator = lambda_client.get_paginator("list_functions")
    for page in paginator.paginate():
        for func in page.get("Functions", []):
            # VPC 설정
            vpc_config = func.get("VpcConfig", {})
            vpc_id = vpc_config.get("VpcId", "")
            subnet_ids = vpc_config.get("SubnetIds", [])
            security_group_ids = vpc_config.get("SecurityGroupIds", [])

            # 태그 조회 (별도 API 호출 필요)
            tags = {}
            try:
                tags_resp = lambda_client.list_tags(Resource=func["FunctionArn"])
                tags = tags_resp.get("Tags", {})
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            functions.append(
                LambdaFunction(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    function_name=func["FunctionName"],
                    function_arn=func["FunctionArn"],
                    runtime=func.get("Runtime", ""),
                    handler=func.get("Handler", ""),
                    code_size=func.get("CodeSize", 0),
                    memory_size=func.get("MemorySize", 128),
                    timeout=func.get("Timeout", 3),
                    state=func.get("State", ""),
                    last_modified=func.get("LastModified", ""),
                    description=func.get("Description", ""),
                    role=func.get("Role", ""),
                    vpc_id=vpc_id,
                    subnet_ids=subnet_ids,
                    security_group_ids=security_group_ids,
                    tags=tags,
                )
            )

    return functions


def collect_ecs_clusters(session, account_id: str, account_name: str, region: str) -> list[ECSCluster]:
    """ECS Cluster 리소스를 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        ECSCluster 데이터 클래스 목록
    """
    ecs = get_client(session, "ecs", region_name=region)
    clusters: list[ECSCluster] = []

    # 클러스터 ARN 목록 조회
    cluster_arns = []
    paginator = ecs.get_paginator("list_clusters")
    for page in paginator.paginate():
        cluster_arns.extend(page.get("clusterArns", []))

    if not cluster_arns:
        return clusters

    # 클러스터 상세 정보 조회 (100개씩 배치)
    batch_size = 100
    for i in range(0, len(cluster_arns), batch_size):
        batch_arns = cluster_arns[i : i + batch_size]
        try:
            resp = ecs.describe_clusters(clusters=batch_arns, include=["TAGS"])
            for cluster in resp.get("clusters", []):
                # 태그 파싱
                tags = {tag["key"]: tag["value"] for tag in cluster.get("tags", [])}

                clusters.append(
                    ECSCluster(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        cluster_name=cluster.get("clusterName", ""),
                        cluster_arn=cluster.get("clusterArn", ""),
                        status=cluster.get("status", ""),
                        running_tasks_count=cluster.get("runningTasksCount", 0),
                        pending_tasks_count=cluster.get("pendingTasksCount", 0),
                        active_services_count=cluster.get("activeServicesCount", 0),
                        registered_container_instances_count=cluster.get("registeredContainerInstancesCount", 0),
                        capacity_providers=cluster.get("capacityProviders", []),
                        tags=tags,
                    )
                )
        except Exception as e:
            logger.debug("Failed to process batch: %s", e)

    return clusters


def collect_ecs_services(session, account_id: str, account_name: str, region: str) -> list[ECSService]:
    """ECS Service 리소스를 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        ECSService 데이터 클래스 목록
    """
    ecs = get_client(session, "ecs", region_name=region)
    services = []

    # 먼저 클러스터 목록 조회
    cluster_arns = []
    paginator = ecs.get_paginator("list_clusters")
    for page in paginator.paginate():
        cluster_arns.extend(page.get("clusterArns", []))

    # 각 클러스터별 서비스 조회
    for cluster_arn in cluster_arns:
        service_arns = []
        try:
            paginator = ecs.get_paginator("list_services")
            for page in paginator.paginate(cluster=cluster_arn):
                service_arns.extend(page.get("serviceArns", []))
        except Exception as e:
            logger.debug("Failed to process item: %s", e)
            continue

        if not service_arns:
            continue

        # 서비스 상세 정보 조회 (10개씩 배치)
        batch_size = 10
        for i in range(0, len(service_arns), batch_size):
            batch_arns = service_arns[i : i + batch_size]
            try:
                resp = ecs.describe_services(cluster=cluster_arn, services=batch_arns, include=["TAGS"])
                for svc in resp.get("services", []):
                    tags = {tag["key"]: tag["value"] for tag in svc.get("tags", [])}

                    services.append(
                        ECSService(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            service_name=svc.get("serviceName", ""),
                            service_arn=svc.get("serviceArn", ""),
                            cluster_arn=svc.get("clusterArn", ""),
                            status=svc.get("status", ""),
                            desired_count=svc.get("desiredCount", 0),
                            running_count=svc.get("runningCount", 0),
                            pending_count=svc.get("pendingCount", 0),
                            launch_type=svc.get("launchType", ""),
                            task_definition=svc.get("taskDefinition", ""),
                            load_balancer_count=len(svc.get("loadBalancers", [])),
                            created_at=svc.get("createdAt"),
                            tags=tags,
                        )
                    )
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

    return services


def collect_auto_scaling_groups(session, account_id: str, account_name: str, region: str) -> list[AutoScalingGroup]:
    """Auto Scaling Group 리소스를 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        AutoScalingGroup 데이터 클래스 목록
    """
    asg = get_client(session, "autoscaling", region_name=region)
    groups = []

    paginator = asg.get_paginator("describe_auto_scaling_groups")
    for page in paginator.paginate():
        for group in page.get("AutoScalingGroups", []):
            # 태그
            tags = {tag["Key"]: tag["Value"] for tag in group.get("Tags", [])}

            # Launch Template 정보
            lt_id = ""
            lt_name = ""
            lc_name = ""
            if group.get("LaunchTemplate"):
                lt = group["LaunchTemplate"]
                lt_id = lt.get("LaunchTemplateId", "")
                lt_name = lt.get("LaunchTemplateName", "")
            elif group.get("MixedInstancesPolicy"):
                lt = group["MixedInstancesPolicy"].get("LaunchTemplate", {}).get("LaunchTemplateSpecification", {})
                lt_id = lt.get("LaunchTemplateId", "")
                lt_name = lt.get("LaunchTemplateName", "")
            elif group.get("LaunchConfigurationName"):
                lc_name = group["LaunchConfigurationName"]

            groups.append(
                AutoScalingGroup(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    asg_name=group.get("AutoScalingGroupName", ""),
                    asg_arn=group.get("AutoScalingGroupARN", ""),
                    launch_template_id=lt_id,
                    launch_template_name=lt_name,
                    launch_config_name=lc_name,
                    min_size=group.get("MinSize", 0),
                    max_size=group.get("MaxSize", 0),
                    desired_capacity=group.get("DesiredCapacity", 0),
                    current_capacity=len(group.get("Instances", [])),
                    health_check_type=group.get("HealthCheckType", ""),
                    availability_zones=group.get("AvailabilityZones", []),
                    target_group_arns=group.get("TargetGroupARNs", []),
                    vpc_zone_identifier=group.get("VPCZoneIdentifier", ""),
                    status=group.get("Status", ""),
                    created_time=group.get("CreatedTime"),
                    tags=tags,
                )
            )

    return groups


def collect_launch_templates(session, account_id: str, account_name: str, region: str) -> list[LaunchTemplate]:
    """Launch Template 리소스를 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        LaunchTemplate 데이터 클래스 목록
    """
    ec2 = get_client(session, "ec2", region_name=region)
    templates = []

    paginator = ec2.get_paginator("describe_launch_templates")
    for page in paginator.paginate():
        for lt in page.get("LaunchTemplates", []):
            tags = parse_tags(lt.get("Tags"))
            template_id = lt["LaunchTemplateId"]

            # 기본 버전의 상세 정보 조회
            instance_type = ""
            ami_id = ""
            key_name = ""
            security_group_ids = []
            try:
                ver_resp = ec2.describe_launch_template_versions(LaunchTemplateId=template_id, Versions=["$Default"])
                versions = ver_resp.get("LaunchTemplateVersions", [])
                if versions:
                    data = versions[0].get("LaunchTemplateData", {})
                    instance_type = data.get("InstanceType", "")
                    ami_id = data.get("ImageId", "")
                    key_name = data.get("KeyName", "")
                    security_group_ids = data.get("SecurityGroupIds", [])
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            templates.append(
                LaunchTemplate(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    template_id=template_id,
                    template_name=lt.get("LaunchTemplateName", ""),
                    version_number=lt.get("LatestVersionNumber", 0),
                    default_version=lt.get("DefaultVersionNumber", 0),
                    latest_version=lt.get("LatestVersionNumber", 0),
                    instance_type=instance_type,
                    ami_id=ami_id,
                    key_name=key_name,
                    security_group_ids=security_group_ids,
                    created_by=lt.get("CreatedBy", ""),
                    create_time=lt.get("CreateTime"),
                    tags=tags,
                )
            )

    return templates


def collect_eks_clusters(session, account_id: str, account_name: str, region: str) -> list[EKSCluster]:
    """EKS Cluster 리소스를 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        EKSCluster 데이터 클래스 목록
    """
    eks = get_client(session, "eks", region_name=region)
    clusters: list[EKSCluster] = []

    # 클러스터 이름 목록 조회
    cluster_names = []
    try:
        paginator = eks.get_paginator("list_clusters")
        for page in paginator.paginate():
            cluster_names.extend(page.get("clusters", []))
    except Exception as e:
        logger.debug("Failed to list EKS clusters: %s", e)
        return clusters

    # 각 클러스터 상세 정보
    for name in cluster_names:
        try:
            resp = eks.describe_cluster(name=name)
            cluster = resp.get("cluster", {})

            vpc_config = cluster.get("resourcesVpcConfig", {})

            clusters.append(
                EKSCluster(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    cluster_name=cluster.get("name", ""),
                    cluster_arn=cluster.get("arn", ""),
                    status=cluster.get("status", ""),
                    version=cluster.get("version", ""),
                    endpoint=cluster.get("endpoint", ""),
                    role_arn=cluster.get("roleArn", ""),
                    vpc_id=vpc_config.get("vpcId", ""),
                    subnet_ids=vpc_config.get("subnetIds", []),
                    security_group_ids=vpc_config.get("securityGroupIds", []),
                    cluster_security_group_id=vpc_config.get("clusterSecurityGroupId", ""),
                    endpoint_public_access=vpc_config.get("endpointPublicAccess", True),
                    endpoint_private_access=vpc_config.get("endpointPrivateAccess", False),
                    created_at=cluster.get("createdAt"),
                    tags=cluster.get("tags", {}),
                )
            )
        except Exception as e:
            logger.debug("Failed to process batch: %s", e)

    return clusters


def collect_eks_node_groups(session, account_id: str, account_name: str, region: str) -> list[EKSNodeGroup]:
    """EKS Node Group 리소스를 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        EKSNodeGroup 데이터 클래스 목록
    """
    eks = get_client(session, "eks", region_name=region)
    node_groups: list[EKSNodeGroup] = []

    # 클러스터 목록 조회
    cluster_names = []
    try:
        paginator = eks.get_paginator("list_clusters")
        for page in paginator.paginate():
            cluster_names.extend(page.get("clusters", []))
    except Exception as e:
        logger.debug("Failed to list EKS clusters: %s", e)
        return node_groups

    # 각 클러스터의 노드 그룹
    for cluster_name in cluster_names:
        try:
            ng_paginator = eks.get_paginator("list_nodegroups")
            ng_names = []
            for page in ng_paginator.paginate(clusterName=cluster_name):
                ng_names.extend(page.get("nodegroups", []))

            for ng_name in ng_names:
                try:
                    resp = eks.describe_nodegroup(clusterName=cluster_name, nodegroupName=ng_name)
                    ng = resp.get("nodegroup", {})
                    scaling = ng.get("scalingConfig", {})

                    node_groups.append(
                        EKSNodeGroup(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            cluster_name=cluster_name,
                            nodegroup_name=ng.get("nodegroupName", ""),
                            nodegroup_arn=ng.get("nodegroupArn", ""),
                            status=ng.get("status", ""),
                            capacity_type=ng.get("capacityType", ""),
                            instance_types=ng.get("instanceTypes", []),
                            scaling_desired=scaling.get("desiredSize", 0),
                            scaling_min=scaling.get("minSize", 0),
                            scaling_max=scaling.get("maxSize", 0),
                            ami_type=ng.get("amiType", ""),
                            disk_size=ng.get("diskSize", 0),
                            subnet_ids=ng.get("subnets", []),
                            created_at=ng.get("createdAt"),
                            tags=ng.get("tags", {}),
                        )
                    )
                except Exception as e:
                    logger.debug("Failed to get nodegroup details: %s", e)
        except Exception as e:
            logger.debug("Failed to process batch: %s", e)

    return node_groups


def collect_amis(session, account_id: str, account_name: str, region: str) -> list[AMI]:
    """자체 소유 EC2 AMI 리소스를 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        AMI 데이터 클래스 목록 (자체 소유 이미지만 포함)
    """
    ec2 = get_client(session, "ec2", region_name=region)
    amis = []

    try:
        resp = ec2.describe_images(Owners=["self"])
        for image in resp.get("Images", []):
            tags = parse_tags(image.get("Tags"))

            amis.append(
                AMI(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    image_id=image.get("ImageId", ""),
                    name=image.get("Name", ""),
                    description=image.get("Description", ""),
                    state=image.get("State", ""),
                    owner_id=image.get("OwnerId", ""),
                    is_public=image.get("Public", False),
                    architecture=image.get("Architecture", ""),
                    platform=image.get("PlatformDetails", ""),
                    root_device_type=image.get("RootDeviceType", ""),
                    virtualization_type=image.get("VirtualizationType", ""),
                    ena_support=image.get("EnaSupport", False),
                    creation_date=image.get("CreationDate", ""),
                    tags=tags,
                )
            )
    except Exception as e:
        logger.debug("Failed to list resources: %s", e)

    return amis


def collect_snapshots(session, account_id: str, account_name: str, region: str) -> list[Snapshot]:
    """자체 소유 EC2 Snapshot 리소스를 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        Snapshot 데이터 클래스 목록 (자체 소유 스냅샷만 포함)
    """
    ec2 = get_client(session, "ec2", region_name=region)
    snapshots = []

    paginator = ec2.get_paginator("describe_snapshots")
    for page in paginator.paginate(OwnerIds=["self"]):
        for snap in page.get("Snapshots", []):
            tags = parse_tags(snap.get("Tags"))

            snapshots.append(
                Snapshot(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    snapshot_id=snap.get("SnapshotId", ""),
                    name=tags.get("Name", ""),
                    volume_id=snap.get("VolumeId", ""),
                    volume_size=snap.get("VolumeSize", 0),
                    state=snap.get("State", ""),
                    description=snap.get("Description", ""),
                    encrypted=snap.get("Encrypted", False),
                    kms_key_id=snap.get("KmsKeyId", ""),
                    owner_id=snap.get("OwnerId", ""),
                    progress=snap.get("Progress", ""),
                    start_time=snap.get("StartTime"),
                    tags=tags,
                )
            )

    return snapshots
