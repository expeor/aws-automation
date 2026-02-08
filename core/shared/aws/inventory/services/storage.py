"""
core/shared/aws/inventory/services/storage.py - Storage 리소스 수집

EFS File System, FSx File System 수집.
"""

from __future__ import annotations

import logging

from core.parallel import get_client

from ..types import EFSFileSystem, FSxFileSystem

logger = logging.getLogger(__name__)


def collect_efs_file_systems(session, account_id: str, account_name: str, region: str) -> list[EFSFileSystem]:
    """EFS File System 리소스를 수집합니다.

    File System 목록 조회 후 각 파일 시스템의 Performance Mode, Throughput Mode,
    크기, Mount Target 수, 암호화 설정 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        EFSFileSystem 데이터 클래스 목록
    """
    efs = get_client(session, "efs", region_name=region)
    file_systems = []

    paginator = efs.get_paginator("describe_file_systems")
    for page in paginator.paginate():
        for fs in page.get("FileSystems", []):
            # 태그 (EFS는 Tags가 직접 포함됨)
            tags = {tag["Key"]: tag["Value"] for tag in fs.get("Tags", [])}

            # Mount Target 수 조회
            mount_target_count = 0
            try:
                mt_resp = efs.describe_mount_targets(FileSystemId=fs["FileSystemId"])
                mount_target_count = len(mt_resp.get("MountTargets", []))
            except Exception as e:
                logger.debug("Failed to describe mount targets: %s", e)

            file_systems.append(
                EFSFileSystem(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    file_system_id=fs.get("FileSystemId", ""),
                    file_system_arn=fs.get("FileSystemArn", ""),
                    name=fs.get("Name", "") or tags.get("Name", ""),
                    life_cycle_state=fs.get("LifeCycleState", ""),
                    performance_mode=fs.get("PerformanceMode", ""),
                    throughput_mode=fs.get("ThroughputMode", ""),
                    provisioned_throughput=fs.get("ProvisionedThroughputInMibps", 0.0),
                    size_in_bytes=fs.get("SizeInBytes", {}).get("Value", 0),
                    number_of_mount_targets=mount_target_count,
                    encrypted=fs.get("Encrypted", False),
                    kms_key_id=fs.get("KmsKeyId", ""),
                    creation_time=fs.get("CreationTime"),
                    tags=tags,
                )
            )

    return file_systems


def collect_fsx_file_systems(session, account_id: str, account_name: str, region: str) -> list[FSxFileSystem]:
    """FSx File System 리소스를 수집합니다.

    File System 목록 조회 후 각 파일 시스템의 타입(Lustre, Windows, ONTAP, OpenZFS),
    스토리지 용량/타입, VPC/Subnet 정보, DNS Name 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        FSxFileSystem 데이터 클래스 목록
    """
    fsx = get_client(session, "fsx", region_name=region)
    file_systems = []

    try:
        paginator = fsx.get_paginator("describe_file_systems")
        for page in paginator.paginate():
            for fs in page.get("FileSystems", []):
                # 태그
                tags = {tag["Key"]: tag["Value"] for tag in fs.get("Tags", [])}

                file_systems.append(
                    FSxFileSystem(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        file_system_id=fs.get("FileSystemId", ""),
                        file_system_arn=fs.get("ResourceARN", ""),
                        file_system_type=fs.get("FileSystemType", ""),
                        lifecycle=fs.get("Lifecycle", ""),
                        storage_capacity=fs.get("StorageCapacity", 0),
                        storage_type=fs.get("StorageType", ""),
                        vpc_id=fs.get("VpcId", ""),
                        subnet_ids=fs.get("SubnetIds", []),
                        dns_name=fs.get("DNSName", ""),
                        kms_key_id=fs.get("KmsKeyId", ""),
                        creation_time=fs.get("CreationTime"),
                        tags=tags,
                    )
                )
    except Exception as e:
        logger.debug("Failed to list FSx file systems: %s", e)

    return file_systems
