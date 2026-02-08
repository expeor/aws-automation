"""통합 백업 데이터 수집 함수"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from core.parallel import get_client

from .models import (
    BackupPlanTagCondition,
    BackupStatus,
    ComprehensiveBackupResult,
    FailedBackupJob,
)

logger = logging.getLogger(__name__)

# 최근 작업 조회 기간
JOB_DAYS = 30


# ============================================================================
# 수집 함수들
# ============================================================================


def _collect_rds_backup_status(session, account_id: str, account_name: str, region: str) -> list[BackupStatus]:
    """RDS DB 인스턴스와 Aurora 클러스터의 백업 상태를 수집한다.

    Aurora 클러스터는 클러스터 단위로 백업되므로 멤버 인스턴스는 별도로 조회하지 않는다.
    각 리소스의 자동 백업 활성화 여부와 보존 기간을 확인한다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        RDS/Aurora 리소스별 백업 상태 목록.
    """
    results: list[BackupStatus] = []
    rds = get_client(session, "rds", region_name=region)

    # 먼저 Aurora 클러스터 정보 수집 (멤버 인스턴스 참조용)
    cluster_info: dict[str, dict] = {}  # {cluster_id: {retention, latest_restorable}}
    try:
        paginator = rds.get_paginator("describe_db_clusters")
        for page in paginator.paginate():
            for cluster in page.get("DBClusters", []):
                cluster_id = cluster.get("DBClusterIdentifier", "")
                cluster_arn = cluster.get("DBClusterArn", "")
                retention = cluster.get("BackupRetentionPeriod", 0)
                backup_enabled = retention > 0
                latest_restorable = cluster.get("LatestRestorableTime")

                cluster_info[cluster_id] = {
                    "retention": retention,
                    "latest_restorable": latest_restorable,
                }

                if backup_enabled:
                    message = f"자동 백업 활성화 (보존 {retention}일)"
                else:
                    message = "자동 백업 비활성화"

                status = "OK" if backup_enabled else "DISABLED"

                results.append(
                    BackupStatus(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        service="Aurora",
                        resource_type="DB Cluster",
                        resource_id=cluster_id,
                        resource_name=cluster_id,
                        backup_enabled=backup_enabled,
                        backup_method="automated",
                        last_backup_time=latest_restorable,
                        backup_retention_days=retention,
                        status=status,
                        message=message,
                        resource_arn=cluster_arn,
                    )
                )
    except ClientError:
        pass

    # RDS DB Instances (Aurora 클러스터 멤버 제외 - 클러스터 단위로 백업됨)
    try:
        paginator = rds.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                # Aurora 클러스터 멤버는 스킵 (클러스터에서 이미 표시)
                cluster_id = db.get("DBClusterIdentifier", "")
                if cluster_id:
                    continue

                db_id = db.get("DBInstanceIdentifier", "")
                db_arn = db.get("DBInstanceArn", "")
                retention = db.get("BackupRetentionPeriod", 0)
                latest_restorable = db.get("LatestRestorableTime")

                # 일반 RDS
                backup_enabled = retention > 0
                if backup_enabled:
                    message = f"자동 백업 활성화 (보존 {retention}일)"
                else:
                    message = "자동 백업 비활성화"

                status = "OK" if backup_enabled else "DISABLED"

                results.append(
                    BackupStatus(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        service="RDS",
                        resource_type="DB Instance",
                        resource_id=db_id,
                        resource_name=db_id,
                        backup_enabled=backup_enabled,
                        backup_method="automated",
                        last_backup_time=latest_restorable,
                        backup_retention_days=retention,
                        status=status,
                        message=message,
                        resource_arn=db_arn,
                    )
                )
    except ClientError:
        pass

    return results


def _collect_dynamodb_backup_status(session, account_id: str, account_name: str, region: str) -> list[BackupStatus]:
    """DynamoDB 테이블의 PITR(Point-In-Time Recovery) 상태를 수집한다.

    PITR이 활성화된 경우 복원 가능한 기간 정보도 함께 수집한다.
    PITR 보존 기간은 35일로 고정되어 있다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        DynamoDB 테이블별 백업 상태 목록.
    """
    results: list[BackupStatus] = []
    dynamodb = get_client(session, "dynamodb", region_name=region)

    try:
        paginator = dynamodb.get_paginator("list_tables")
        for page in paginator.paginate():
            for table_name in page.get("TableNames", []):
                try:
                    backup_info = dynamodb.describe_continuous_backups(TableName=table_name)
                    cb_desc = backup_info.get("ContinuousBackupsDescription", {})
                    pitr_desc = cb_desc.get("PointInTimeRecoveryDescription", {})
                    pitr_status = pitr_desc.get("PointInTimeRecoveryStatus", "DISABLED")

                    backup_enabled = pitr_status == "ENABLED"
                    earliest_restorable = pitr_desc.get("EarliestRestorableDateTime")
                    latest_restorable = pitr_desc.get("LatestRestorableDateTime")

                    if backup_enabled:
                        message = "PITR 활성화"
                        if earliest_restorable and latest_restorable:
                            message += f" (복원 가능: {earliest_restorable.strftime('%Y-%m-%d')} ~ {latest_restorable.strftime('%Y-%m-%d')})"
                    else:
                        message = "PITR 비활성화"

                    status = "OK" if backup_enabled else "DISABLED"

                    # ARN 생성
                    table_arn = f"arn:aws:dynamodb:{region}:{account_id}:table/{table_name}"

                    results.append(
                        BackupStatus(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            service="DynamoDB",
                            resource_type="Table",
                            resource_id=table_name,
                            resource_name=table_name,
                            backup_enabled=backup_enabled,
                            backup_method="pitr",
                            last_backup_time=latest_restorable,
                            backup_retention_days=35 if backup_enabled else 0,  # PITR은 35일 고정
                            status=status,
                            message=message,
                            resource_arn=table_arn,
                        )
                    )
                except ClientError:
                    # 테이블 접근 권한 없음
                    pass
    except ClientError:
        pass

    return results


def _collect_efs_backup_status(session, account_id: str, account_name: str, region: str) -> list[BackupStatus]:
    """EFS 파일시스템의 백업 정책 상태를 수집한다.

    EFS는 네이티브 스냅샷 기능이 없으며, AWS Backup을 통해서만 보호할 수 있다.
    has_native_backup이 False로 설정된다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        EFS 파일시스템별 백업 상태 목록.
    """
    results: list[BackupStatus] = []
    efs = get_client(session, "efs", region_name=region)

    try:
        paginator = efs.get_paginator("describe_file_systems")
        for page in paginator.paginate():
            for fs in page.get("FileSystems", []):
                fs_id = fs.get("FileSystemId", "")
                fs_arn = fs.get("FileSystemArn", "")
                name = fs.get("Name", fs_id)

                # 백업 정책 조회
                backup_enabled = False
                message = "백업 정책 조회 실패"
                try:
                    backup_policy = efs.describe_backup_policy(FileSystemId=fs_id)
                    policy_status = backup_policy.get("BackupPolicy", {}).get("Status", "DISABLED")
                    backup_enabled = policy_status == "ENABLED"
                    message = "자동 백업 활성화" if backup_enabled else "자동 백업 비활성화"
                except ClientError as e:
                    if e.response.get("Error", {}).get("Code") == "PolicyNotFound":
                        message = "백업 정책 없음"
                    # 기타 에러는 무시

                status = "OK" if backup_enabled else "DISABLED"

                results.append(
                    BackupStatus(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        service="EFS",
                        resource_type="FileSystem",
                        resource_id=fs_id,
                        resource_name=name,
                        backup_enabled=backup_enabled,
                        backup_method="aws-backup",
                        last_backup_time=None,
                        backup_retention_days=0,
                        status=status,
                        message=message,
                        resource_arn=fs_arn,
                        has_native_backup=False,  # EFS는 네이티브 스냅샷 없음, AWS Backup만 가능
                    )
                )
    except ClientError:
        pass

    return results


def _collect_fsx_backup_status(session, account_id: str, account_name: str, region: str) -> list[BackupStatus]:
    """FSx 파일시스템의 자동 백업 상태를 수집한다.

    Windows, Lustre, ONTAP, OpenZFS 모든 FSx 유형을 지원하며,
    각 유형별 설정에서 자동 백업 보존 기간을 확인한다.
    최신 백업 시간은 describe_backups에서 추출한다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        FSx 파일시스템별 백업 상태 목록.
    """
    results: list[BackupStatus] = []
    fsx = get_client(session, "fsx", region_name=region)

    # 먼저 모든 백업 조회하여 파일시스템별 최신 백업 시간 추출
    # - Windows/Lustre/OpenZFS: FileSystem 레벨 백업
    # - ONTAP: Volume 레벨 백업 (Volume.FileSystemId로 매핑)
    fs_latest_backup: dict[str, datetime] = {}
    try:
        backup_paginator = fsx.get_paginator("describe_backups")
        for page in backup_paginator.paginate():
            for backup in page.get("Backups", []):
                backup_time = backup.get("CreationTime")
                if not backup_time:
                    continue

                # FileSystem 레벨 백업 (Windows, Lustre, OpenZFS)
                backup_fs_id = backup.get("FileSystem", {}).get("FileSystemId", "")

                # Volume 레벨 백업 (ONTAP) - Volume에서 FileSystemId 추출
                if not backup_fs_id:
                    backup_fs_id = backup.get("Volume", {}).get("FileSystemId", "")

                if backup_fs_id:
                    if backup_fs_id not in fs_latest_backup:
                        fs_latest_backup[backup_fs_id] = backup_time
                    else:
                        fs_latest_backup[backup_fs_id] = max(fs_latest_backup[backup_fs_id], backup_time)
    except ClientError:
        pass

    try:
        paginator = fsx.get_paginator("describe_file_systems")
        for page in paginator.paginate():
            for fs in page.get("FileSystems", []):
                fs_id = fs.get("FileSystemId", "")
                fs_arn = fs.get("ResourceARN", "")
                fs_type = fs.get("FileSystemType", "")

                # 이름은 태그에서 가져오기
                tags = fs.get("Tags", [])
                name = next((t["Value"] for t in tags if t["Key"] == "Name"), fs_id)

                # FSx 타입별 백업 설정 확인
                retention_days = 0

                if fs_type == "LUSTRE":
                    lustre_config = fs.get("LustreConfiguration", {})
                    retention_days = lustre_config.get("AutomaticBackupRetentionDays", 0)
                elif fs_type == "WINDOWS":
                    windows_config = fs.get("WindowsConfiguration", {})
                    retention_days = windows_config.get("AutomaticBackupRetentionDays", 0)
                elif fs_type == "ONTAP":
                    ontap_config = fs.get("OntapConfiguration", {})
                    retention_days = ontap_config.get("AutomaticBackupRetentionDays", 0)
                elif fs_type == "OPENZFS":
                    zfs_config = fs.get("OpenZFSConfiguration", {})
                    retention_days = zfs_config.get("AutomaticBackupRetentionDays", 0)

                backup_enabled = retention_days > 0
                latest_backup_time = fs_latest_backup.get(fs_id)

                if backup_enabled:
                    message = f"자동 백업 활성화 (보존 {retention_days}일)"
                else:
                    message = "자동 백업 비활성화"

                status = "OK" if backup_enabled else "DISABLED"

                results.append(
                    BackupStatus(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        service="FSx",
                        resource_type=f"FileSystem ({fs_type})",
                        resource_id=fs_id,
                        resource_name=name,
                        backup_enabled=backup_enabled,
                        backup_method="automated",
                        last_backup_time=latest_backup_time,
                        backup_retention_days=retention_days,
                        status=status,
                        message=message,
                        resource_arn=fs_arn,
                    )
                )
    except ClientError:
        pass

    return results


def _collect_ec2_backup_status(session, account_id: str, account_name: str, region: str) -> list[BackupStatus]:
    """EC2 인스턴스의 백업 상태를 수집한다.

    EC2는 자체 백업 기능이 없으므로 has_native_backup=False로 설정된다.
    AWS Backup 보호 여부는 나중에 _collect_comprehensive_backup_data에서 매핑된다.
    terminated 상태의 인스턴스는 제외한다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        EC2 인스턴스별 백업 상태 목록.
    """
    results: list[BackupStatus] = []
    ec2 = get_client(session, "ec2", region_name=region)

    try:
        paginator = ec2.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    instance_id = instance.get("InstanceId", "")
                    instance_state = instance.get("State", {}).get("Name", "")

                    # terminated 인스턴스는 제외
                    if instance_state == "terminated":
                        continue

                    # 이름은 태그에서 가져오기
                    tags = instance.get("Tags", [])
                    name = next((t["Value"] for t in tags if t["Key"] == "Name"), instance_id)

                    # ARN 생성
                    instance_arn = f"arn:aws:ec2:{region}:{account_id}:instance/{instance_id}"

                    # EC2는 자체 백업 기능 없음 (AWS Backup으로만 보호)
                    # aws_backup_protected는 나중에 매핑됨
                    message = f"상태: {instance_state}"

                    results.append(
                        BackupStatus(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            service="EC2",
                            resource_type="Instance",
                            resource_id=instance_id,
                            resource_name=name,
                            backup_enabled=False,  # EC2는 자체 백업 없음
                            backup_method="aws-backup",
                            last_backup_time=None,
                            backup_retention_days=0,
                            status="DISABLED",  # AWS Backup 매핑 후 업데이트됨
                            message=message,
                            resource_arn=instance_arn,
                            has_native_backup=False,  # EC2는 자체 백업 기능 없음
                        )
                    )
    except ClientError:
        pass

    return results


def _collect_documentdb_backup_status(session, account_id: str, account_name: str, region: str) -> list[BackupStatus]:
    """DocumentDB 클러스터의 백업 상태를 수집한다.

    DocumentDB는 docdb 서비스 엔드포인트를 사용하며, Engine이 'docdb'인
    클러스터만 필터링하여 자동 백업 보존 기간을 확인한다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        DocumentDB 클러스터별 백업 상태 목록.
    """
    results: list[BackupStatus] = []

    # DocumentDB는 RDS API를 사용하지만 별도 엔드포인트
    # docdb 서비스로 호출
    try:
        docdb = get_client(session, "docdb", region_name=region)
        paginator = docdb.get_paginator("describe_db_clusters")

        for page in paginator.paginate():
            for cluster in page.get("DBClusters", []):
                # DocumentDB 클러스터만 필터링 (Engine이 docdb)
                if cluster.get("Engine") != "docdb":
                    continue

                cluster_id = cluster.get("DBClusterIdentifier", "")
                cluster_arn = cluster.get("DBClusterArn", "")
                retention = cluster.get("BackupRetentionPeriod", 0)
                backup_enabled = retention > 0
                latest_restorable = cluster.get("LatestRestorableTime")

                if backup_enabled:
                    message = f"자동 백업 활성화 (보존 {retention}일)"
                else:
                    message = "자동 백업 비활성화"

                status = "OK" if backup_enabled else "DISABLED"

                results.append(
                    BackupStatus(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        service="DocumentDB",
                        resource_type="Cluster",
                        resource_id=cluster_id,
                        resource_name=cluster_id,
                        backup_enabled=backup_enabled,
                        backup_method="automated",
                        last_backup_time=latest_restorable,
                        backup_retention_days=retention,
                        status=status,
                        message=message,
                        resource_arn=cluster_arn,
                    )
                )
    except ClientError:
        pass

    return results


def _collect_neptune_backup_status(session, account_id: str, account_name: str, region: str) -> list[BackupStatus]:
    """Neptune 클러스터의 백업 상태를 수집한다.

    Engine이 'neptune'인 클러스터만 필터링하여 자동 백업 보존 기간을 확인한다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        Neptune 클러스터별 백업 상태 목록.
    """
    results: list[BackupStatus] = []

    try:
        neptune = get_client(session, "neptune", region_name=region)
        paginator = neptune.get_paginator("describe_db_clusters")

        for page in paginator.paginate():
            for cluster in page.get("DBClusters", []):
                # Neptune 클러스터만 필터링 (Engine이 neptune)
                if cluster.get("Engine") != "neptune":
                    continue

                cluster_id = cluster.get("DBClusterIdentifier", "")
                cluster_arn = cluster.get("DBClusterArn", "")
                retention = cluster.get("BackupRetentionPeriod", 0)
                backup_enabled = retention > 0
                latest_restorable = cluster.get("LatestRestorableTime")

                if backup_enabled:
                    message = f"자동 백업 활성화 (보존 {retention}일)"
                else:
                    message = "자동 백업 비활성화"

                status = "OK" if backup_enabled else "DISABLED"

                results.append(
                    BackupStatus(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        service="Neptune",
                        resource_type="Cluster",
                        resource_id=cluster_id,
                        resource_name=cluster_id,
                        backup_enabled=backup_enabled,
                        backup_method="automated",
                        last_backup_time=latest_restorable,
                        backup_retention_days=retention,
                        status=status,
                        message=message,
                        resource_arn=cluster_arn,
                    )
                )
    except ClientError:
        pass

    return results


def _collect_redshift_backup_status(session, account_id: str, account_name: str, region: str) -> list[BackupStatus]:
    """Redshift의 백업 상태를 수집한다 (Provisioned + Serverless).

    Provisioned 클러스터는 자동 스냅샷 보존 기간을 확인하고,
    Serverless Namespace는 스냅샷이 기본 활성화되어 있으므로 항상 OK로 처리한다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        Redshift 리소스별 백업 상태 목록.
    """
    results: list[BackupStatus] = []

    # 1. Provisioned Clusters
    try:
        redshift = get_client(session, "redshift", region_name=region)
        paginator = redshift.get_paginator("describe_clusters")
        for page in paginator.paginate():
            for cluster in page.get("Clusters", []):
                cluster_id = cluster.get("ClusterIdentifier", "")
                # ARN 생성
                cluster_arn = f"arn:aws:redshift:{region}:{account_id}:cluster:{cluster_id}"
                retention = cluster.get("AutomatedSnapshotRetentionPeriod", 0)
                backup_enabled = retention > 0

                if backup_enabled:
                    message = f"자동 스냅샷 활성화 (보존 {retention}일)"
                else:
                    message = "자동 스냅샷 비활성화"

                status = "OK" if backup_enabled else "DISABLED"

                results.append(
                    BackupStatus(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        service="Redshift",
                        resource_type="Cluster (Provisioned)",
                        resource_id=cluster_id,
                        resource_name=cluster_id,
                        backup_enabled=backup_enabled,
                        backup_method="snapshot",
                        last_backup_time=None,
                        backup_retention_days=retention,
                        status=status,
                        message=message,
                        resource_arn=cluster_arn,
                    )
                )
    except ClientError:
        pass

    # 2. Serverless Namespaces (스냅샷 기본 활성화)
    try:
        rs_serverless = get_client(session, "redshift-serverless", region_name=region)
        namespaces_resp = rs_serverless.list_namespaces()
        for ns in namespaces_resp.get("namespaces", []):
            ns_name = ns.get("namespaceName", "")
            ns_arn = ns.get("namespaceArn", "")
            ns_status = ns.get("status", "")

            # Serverless는 스냅샷이 기본 활성화됨 (recovery point 자동 생성)
            # 실제로 recovery points가 있는지 확인
            backup_enabled = True
            message = "Serverless 스냅샷 활성화 (기본)"

            # 상태가 AVAILABLE이 아니면 체크
            if ns_status != "AVAILABLE":
                message = f"Namespace 상태: {ns_status}"

            results.append(
                BackupStatus(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    service="Redshift Serverless",
                    resource_type="Namespace",
                    resource_id=ns_name,
                    resource_name=ns_name,
                    backup_enabled=backup_enabled,
                    backup_method="snapshot",
                    last_backup_time=None,
                    backup_retention_days=0,  # Serverless는 별도 설정
                    status="OK",
                    message=message,
                    resource_arn=ns_arn,
                )
            )
    except ClientError:
        pass  # Serverless 미사용 또는 권한 없음

    return results


def _collect_elasticache_backup_status(session, account_id: str, account_name: str, region: str) -> list[BackupStatus]:
    """ElastiCache의 백업 상태를 수집한다 (Redis/Valkey + Memcached).

    Redis/Valkey Replication Group의 스냅샷 보존 설정을 확인하고,
    Memcached는 스냅샷을 지원하지 않으므로 NOT_SUPPORTED로 기록한다.
    Replication Group 멤버 클러스터는 중복 방지를 위해 스킵한다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        ElastiCache 리소스별 백업 상태 목록.
    """
    results: list[BackupStatus] = []
    elasticache = get_client(session, "elasticache", region_name=region)

    # Redis/Valkey 클러스터 ID 추적 (중복 방지)
    redis_cluster_ids: set[str] = set()

    # 1. Redis/Valkey Replication Groups (스냅샷 지원)
    try:
        paginator = elasticache.get_paginator("describe_replication_groups")
        for page in paginator.paginate():
            for group in page.get("ReplicationGroups", []):
                group_id = group.get("ReplicationGroupId", "")
                group_arn = group.get("ARN", "")
                retention = group.get("SnapshotRetentionLimit", 0)
                backup_enabled = retention > 0

                # 멤버 클러스터 추적
                for member in group.get("MemberClusters", []):
                    redis_cluster_ids.add(member)

                if backup_enabled:
                    message = f"자동 스냅샷 활성화 (보존 {retention}일)"
                else:
                    message = "자동 스냅샷 비활성화"

                status = "OK" if backup_enabled else "DISABLED"

                results.append(
                    BackupStatus(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        service="ElastiCache",
                        resource_type="Replication Group (Redis/Valkey)",
                        resource_id=group_id,
                        resource_name=group_id,
                        backup_enabled=backup_enabled,
                        backup_method="snapshot",
                        last_backup_time=None,
                        backup_retention_days=retention,
                        status=status,
                        message=message,
                        resource_arn=group_arn,
                    )
                )
    except ClientError:
        pass

    # 2. Memcached 클러스터 (스냅샷 미지원)
    try:
        paginator = elasticache.get_paginator("describe_cache_clusters")
        for page in paginator.paginate():
            for cluster in page.get("CacheClusters", []):
                cluster_id = cluster.get("CacheClusterId", "")
                engine = cluster.get("Engine", "")

                # Replication Group 멤버인 Redis 클러스터는 스킵 (이미 위에서 처리)
                if cluster_id in redis_cluster_ids:
                    continue

                cluster_arn = cluster.get("ARN", "")

                if engine == "memcached":
                    # Memcached는 스냅샷 미지원
                    results.append(
                        BackupStatus(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            service="ElastiCache",
                            resource_type="Cluster (Memcached)",
                            resource_id=cluster_id,
                            resource_name=cluster_id,
                            backup_enabled=False,
                            backup_method="not_supported",
                            last_backup_time=None,
                            backup_retention_days=0,
                            status="NOT_SUPPORTED",
                            message="Memcached는 스냅샷 미지원",
                            resource_arn=cluster_arn,
                        )
                    )
                elif engine in ("redis", "valkey"):
                    # 단독 Redis/Valkey 클러스터 (Replication Group 없음)
                    retention = cluster.get("SnapshotRetentionLimit", 0)
                    backup_enabled = retention > 0

                    if backup_enabled:
                        message = f"자동 스냅샷 활성화 (보존 {retention}일)"
                    else:
                        message = "자동 스냅샷 비활성화"

                    status = "OK" if backup_enabled else "DISABLED"

                    results.append(
                        BackupStatus(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            service="ElastiCache",
                            resource_type=f"Cluster ({engine.capitalize()})",
                            resource_id=cluster_id,
                            resource_name=cluster_id,
                            backup_enabled=backup_enabled,
                            backup_method="snapshot",
                            last_backup_time=None,
                            backup_retention_days=retention,
                            status=status,
                            message=message,
                            resource_arn=cluster_arn,
                        )
                    )
    except ClientError:
        pass

    return results


def _collect_memorydb_backup_status(session, account_id: str, account_name: str, region: str) -> list[BackupStatus]:
    """MemoryDB 클러스터의 스냅샷 백업 상태를 수집한다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        MemoryDB 클러스터별 백업 상태 목록.
    """
    results: list[BackupStatus] = []

    try:
        memorydb = get_client(session, "memorydb", region_name=region)
        paginator = memorydb.get_paginator("describe_clusters")
        for page in paginator.paginate():
            for cluster in page.get("Clusters", []):
                cluster_name = cluster.get("Name", "")
                cluster_arn = cluster.get("ARN", "")
                retention = cluster.get("SnapshotRetentionLimit", 0)
                backup_enabled = retention > 0

                if backup_enabled:
                    message = f"자동 스냅샷 활성화 (보존 {retention}일)"
                else:
                    message = "자동 스냅샷 비활성화"

                status = "OK" if backup_enabled else "DISABLED"

                results.append(
                    BackupStatus(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        service="MemoryDB",
                        resource_type="Cluster",
                        resource_id=cluster_name,
                        resource_name=cluster_name,
                        backup_enabled=backup_enabled,
                        backup_method="snapshot",
                        last_backup_time=None,
                        backup_retention_days=retention,
                        status=status,
                        message=message,
                        resource_arn=cluster_arn,
                    )
                )
    except ClientError:
        pass

    return results


def _collect_opensearch_backup_status(session, account_id: str, account_name: str, region: str) -> list[BackupStatus]:
    """OpenSearch 도메인의 백업 상태를 수집한다.

    OpenSearch는 자동 스냅샷이 항상 활성화되어 있으며 14일간 보존된다.
    시작 시간만 설정 가능하므로 모든 도메인의 status는 ALWAYS_ON이다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        OpenSearch 도메인별 백업 상태 목록.
    """
    results: list[BackupStatus] = []

    try:
        opensearch = get_client(session, "opensearch", region_name=region)
        domains_resp = opensearch.list_domain_names()

        for domain_info in domains_resp.get("DomainNames", []):
            domain_name = domain_info.get("DomainName", "")

            try:
                domain_resp = opensearch.describe_domain(DomainName=domain_name)
                domain = domain_resp.get("DomainStatus", {})

                domain_arn = domain.get("ARN", "")
                snapshot_options = domain.get("SnapshotOptions", {})
                auto_hour = snapshot_options.get("AutomatedSnapshotStartHour")

                # OpenSearch는 자동 스냅샷이 항상 활성화 (14일 보존)
                # 시작 시간만 설정 가능
                if auto_hour is not None:
                    message = f"자동 스냅샷 활성화 (14일 보존, 시작: {auto_hour}:00 UTC)"
                else:
                    message = "자동 스냅샷 활성화 (14일 보존)"

                results.append(
                    BackupStatus(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        service="OpenSearch",
                        resource_type="Domain",
                        resource_id=domain_name,
                        resource_name=domain_name,
                        backup_enabled=True,  # 항상 활성화
                        backup_method="snapshot",
                        last_backup_time=None,
                        backup_retention_days=14,  # 고정
                        status="ALWAYS_ON",
                        message=message,
                        resource_arn=domain_arn,
                    )
                )
            except ClientError:
                pass  # 도메인 상세 조회 실패
    except ClientError:
        pass

    return results


def _collect_aws_backup_protected_resources(
    session, account_id: str, account_name: str, region: str
) -> dict[str, datetime | None]:
    """AWS Backup으로 보호되는 리소스 ARN과 마지막 백업 시간 수집

    Returns:
        {resource_arn: last_backup_time} - 마지막 백업 시간 (없으면 None)
    """
    protected_resources: dict[str, datetime | None] = {}
    backup = get_client(session, "backup", region_name=region)

    try:
        paginator = backup.get_paginator("list_protected_resources")
        for page in paginator.paginate():
            for resource in page.get("Results", []):
                arn = resource.get("ResourceArn", "")
                last_backup = resource.get("LastBackupTime")  # datetime or None
                if arn:
                    protected_resources[arn] = last_backup
    except ClientError:
        pass

    return protected_resources


def _collect_resource_backup_plan_mapping(
    session, account_id: str, account_name: str, region: str
) -> dict[str, set[str]]:
    """리소스별 할당된 Backup Plan 이름 수집

    최근 완료된 Backup Job에서 리소스와 Plan 매핑을 추출합니다.

    Returns:
        {resource_arn: {plan_name1, plan_name2, ...}}
    """
    resource_to_plans: dict[str, set[str]] = {}
    backup = get_client(session, "backup", region_name=region)

    # 1. Backup Plan ID -> Name 매핑 생성
    plan_id_to_name: dict[str, str] = {}
    try:
        plans_paginator = backup.get_paginator("list_backup_plans")
        for page in plans_paginator.paginate():
            for plan in page.get("BackupPlansList", []):
                plan_id = plan.get("BackupPlanId", "")
                plan_name = plan.get("BackupPlanName", "")
                if plan_id and plan_name:
                    plan_id_to_name[plan_id] = plan_name
    except ClientError:
        pass

    if not plan_id_to_name:
        return resource_to_plans

    # 2. 최근 완료된 Backup Job에서 리소스 -> Plan 매핑 추출
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=JOB_DAYS)

    try:
        paginator = backup.get_paginator("list_backup_jobs")
        for page in paginator.paginate(
            ByCreatedAfter=start_date,
            ByCreatedBefore=now,
            ByState="COMPLETED",
        ):
            for job in page.get("BackupJobs", []):
                resource_arn = job.get("ResourceArn", "")
                plan_id = job.get("BackupPlanId", "")

                if resource_arn and plan_id and plan_id in plan_id_to_name:
                    plan_name = plan_id_to_name[plan_id]
                    if resource_arn not in resource_to_plans:
                        resource_to_plans[resource_arn] = set()
                    resource_to_plans[resource_arn].add(plan_name)
    except ClientError:
        pass

    return resource_to_plans


def _collect_backup_plan_tag_conditions(
    session, account_id: str, account_name: str, region: str
) -> list[BackupPlanTagCondition]:
    """Backup Plan의 태그 기반 선택 조건 수집

    AWS 자동 생성 Plan은 제외:
    - aws/efs/automatic-backup-plan (EFS 자동 백업용)
    """
    results: list[BackupPlanTagCondition] = []
    backup = get_client(session, "backup", region_name=region)

    # AWS 관리형 Plan 이름 패턴 (제외 대상)
    aws_managed_plan_prefixes = ("aws/efs/", "aws/")

    try:
        # Backup Plans 조회
        plans_paginator = backup.get_paginator("list_backup_plans")
        for plans_page in plans_paginator.paginate():
            for plan in plans_page.get("BackupPlansList", []):
                plan_id = plan.get("BackupPlanId", "")
                plan_name = plan.get("BackupPlanName", "")

                # AWS 관리형 Plan 스킵
                if plan_name.startswith(aws_managed_plan_prefixes):
                    continue

                # 각 Plan의 Selection 조회
                try:
                    selections = backup.list_backup_selections(BackupPlanId=plan_id)
                    for sel in selections.get("BackupSelectionsList", []):
                        sel_id = sel.get("SelectionId", "")
                        sel_name = sel.get("SelectionName", "")

                        # Selection 상세 조회
                        try:
                            sel_detail = backup.get_backup_selection(BackupPlanId=plan_id, SelectionId=sel_id)
                            selection = sel_detail.get("BackupSelection", {})
                            list_of_tags = selection.get("ListOfTags", [])
                            resources = selection.get("Resources", [])
                            conditions = selection.get("Conditions", {})

                            # 리소스 타입 추출 (ARN에서)
                            resource_types = []
                            for r in resources:
                                if "::" in r:
                                    # arn:aws:ec2:*:*:volume/* 형태
                                    parts = r.split(":")
                                    if len(parts) >= 6:
                                        resource_types.append(parts[2])  # 서비스명

                            # ListOfTags에서 조건 추출
                            for tag_cond in list_of_tags:
                                cond_type = tag_cond.get("ConditionType", "STRINGEQUALS")
                                cond_key = tag_cond.get("ConditionKey", "")
                                cond_value = tag_cond.get("ConditionValue", "")

                                results.append(
                                    BackupPlanTagCondition(
                                        account_id=account_id,
                                        account_name=account_name,
                                        region=region,
                                        plan_id=plan_id,
                                        plan_name=plan_name,
                                        selection_id=sel_id,
                                        selection_name=sel_name,
                                        condition_type=cond_type,
                                        tag_key=cond_key,
                                        tag_value=cond_value,
                                        resource_types=resource_types,
                                    )
                                )

                            # Conditions.StringEquals에서도 추출
                            for str_eq in conditions.get("StringEquals", []):
                                results.append(
                                    BackupPlanTagCondition(
                                        account_id=account_id,
                                        account_name=account_name,
                                        region=region,
                                        plan_id=plan_id,
                                        plan_name=plan_name,
                                        selection_id=sel_id,
                                        selection_name=sel_name,
                                        condition_type="STRINGEQUALS",
                                        tag_key=str_eq.get("ConditionKey", ""),
                                        tag_value=str_eq.get("ConditionValue", ""),
                                        resource_types=resource_types,
                                    )
                                )

                            # Conditions.StringLike에서도 추출
                            for str_like in conditions.get("StringLike", []):
                                results.append(
                                    BackupPlanTagCondition(
                                        account_id=account_id,
                                        account_name=account_name,
                                        region=region,
                                        plan_id=plan_id,
                                        plan_name=plan_name,
                                        selection_id=sel_id,
                                        selection_name=sel_name,
                                        condition_type="STRINGLIKE",
                                        tag_key=str_like.get("ConditionKey", ""),
                                        tag_value=str_like.get("ConditionValue", ""),
                                        resource_types=resource_types,
                                    )
                                )

                        except ClientError:
                            pass
                except ClientError:
                    pass
    except ClientError:
        pass

    return results


def _collect_failed_backup_jobs(session, account_id: str, account_name: str, region: str) -> list[FailedBackupJob]:
    """최근 JOB_DAYS일 이내에 실패/중단/부분 완료된 AWS Backup 작업을 수집한다.

    FAILED, ABORTED, PARTIAL 상태의 작업을 각각 별도로 조회한다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        실패한 백업 작업 목록.
    """
    results: list[FailedBackupJob] = []
    backup = get_client(session, "backup", region_name=region)

    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=JOB_DAYS)

    try:
        paginator = backup.get_paginator("list_backup_jobs")

        # 실패 상태별로 조회
        for state in ["FAILED", "ABORTED", "PARTIAL"]:
            try:
                for page in paginator.paginate(
                    ByCreatedAfter=start_date,
                    ByCreatedBefore=now,
                    ByState=state,
                ):
                    for job in page.get("BackupJobs", []):
                        results.append(
                            FailedBackupJob(
                                account_id=account_id,
                                account_name=account_name,
                                region=region,
                                job_id=job.get("BackupJobId", ""),
                                vault_name=job.get("BackupVaultName", ""),
                                resource_arn=job.get("ResourceArn", ""),
                                resource_type=job.get("ResourceType", ""),
                                status=job.get("State", ""),
                                status_message=job.get("StatusMessage", ""),
                                creation_date=job.get("CreationDate"),
                                completion_date=job.get("CompletionDate"),
                            )
                        )
            except ClientError:
                pass
    except ClientError:
        pass

    return results


def _collect_resource_tags_by_arn(
    session, region: str, resource_arns: list[str], tag_keys: set[str]
) -> dict[str, dict[str, str]]:
    """리소스 ARN별 태그 조회 (필요한 태그 키만)

    Returns:
        {resource_arn: {tag_key: tag_value}}
    """
    if not resource_arns or not tag_keys:
        return {}

    result: dict[str, dict[str, str]] = {}
    tagging = get_client(session, "resourcegroupstaggingapi", region_name=region)

    try:
        paginator = tagging.get_paginator("get_resources")
        for page in paginator.paginate(
            ResourceTypeFilters=[
                "rds:db",
                "rds:cluster",
                "dynamodb:table",
                "elasticfilesystem:file-system",
                "fsx:file-system",
                "ec2:instance",
                "docdb:cluster",
                "neptune:cluster",
                "redshift:cluster",
                "elasticache:cluster",
                "elasticache:replicationgroup",
                "memorydb:cluster",
                "es:domain",
            ]
        ):
            for resource in page.get("ResourceTagMappingList", []):
                arn = resource.get("ResourceARN", "")
                if arn in resource_arns:
                    tags = {t["Key"]: t["Value"] for t in resource.get("Tags", [])}
                    # 필요한 태그 키만 필터링
                    filtered_tags = {k: v for k, v in tags.items() if k in tag_keys}
                    if filtered_tags:
                        result[arn] = filtered_tags
    except ClientError:
        pass

    return result


def _collect_comprehensive_backup_data(
    session, account_id: str, account_name: str, region: str
) -> ComprehensiveBackupResult | None:
    """parallel_collect 콜백: 단일 계정/리전의 통합 백업 데이터를 수집한다.

    11개 AWS 서비스(RDS, DynamoDB, EFS, FSx, EC2, DocumentDB, Neptune,
    Redshift, ElastiCache, MemoryDB, OpenSearch)의 백업 상태를 수집하고,
    AWS Backup 보호 여부와 Backup Plan 매핑 정보를 추가한다.

    Args:
        session: boto3 Session.
        account_id: AWS 계정 ID.
        account_name: AWS 계정 별칭.
        region: AWS 리전 코드.

    Returns:
        통합 백업 분석 결과. 데이터가 없으면 None.
    """
    result = ComprehensiveBackupResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
    )

    # AWS Backup으로 보호되는 리소스 목록 수집
    protected_resources = _collect_aws_backup_protected_resources(session, account_id, account_name, region)

    # 리소스별 Backup Plan 매핑 수집
    resource_plan_mapping = _collect_resource_backup_plan_mapping(session, account_id, account_name, region)

    # 각 서비스별 백업 상태 수집
    result.backup_statuses.extend(_collect_rds_backup_status(session, account_id, account_name, region))
    result.backup_statuses.extend(_collect_dynamodb_backup_status(session, account_id, account_name, region))
    result.backup_statuses.extend(_collect_efs_backup_status(session, account_id, account_name, region))
    result.backup_statuses.extend(_collect_fsx_backup_status(session, account_id, account_name, region))
    result.backup_statuses.extend(_collect_ec2_backup_status(session, account_id, account_name, region))
    result.backup_statuses.extend(_collect_documentdb_backup_status(session, account_id, account_name, region))
    result.backup_statuses.extend(_collect_neptune_backup_status(session, account_id, account_name, region))
    result.backup_statuses.extend(_collect_redshift_backup_status(session, account_id, account_name, region))
    result.backup_statuses.extend(_collect_elasticache_backup_status(session, account_id, account_name, region))
    result.backup_statuses.extend(_collect_memorydb_backup_status(session, account_id, account_name, region))
    result.backup_statuses.extend(_collect_opensearch_backup_status(session, account_id, account_name, region))

    # Backup Plan 태그 조건 수집
    result.tag_conditions = _collect_backup_plan_tag_conditions(session, account_id, account_name, region)

    # AWS Backup 보호 여부, 마지막 백업 시간, Backup Plan 매핑
    for status in result.backup_statuses:
        if status.resource_arn:
            # Backup Plan 이름 매핑
            if status.resource_arn in resource_plan_mapping:
                status.backup_plan_names = sorted(resource_plan_mapping[status.resource_arn])

            # AWS Backup 보호 여부 및 마지막 백업 시간
            if status.resource_arn in protected_resources:
                status.aws_backup_protected = True
                aws_backup_time = protected_resources[status.resource_arn]

                # AWS Backup 마지막 백업 시간 저장
                status.aws_backup_last_time = aws_backup_time

                # 메시지 업데이트 (자체 백업 유무에 따라 다르게 처리)
                if status.has_native_backup:
                    # 자체 백업 기능 있는 서비스 (RDS, DynamoDB, FSx 등)
                    if status.backup_enabled:
                        # 자체 백업 + AWS Backup 둘 다 있음
                        status.message += " + AWS Backup"
                        status.backup_method = f"{status.backup_method}+aws-backup"
                    else:
                        # AWS Backup만
                        status.status = "OK"
                        status.message += " (AWS Backup으로 보호됨)"
                        status.backup_method = "aws-backup"
                else:
                    # 자체 백업 기능 없는 서비스 (EFS, EC2)
                    # backup_enabled가 True여도 그것도 AWS Backup임
                    status.status = "OK"
                    if not status.backup_enabled:
                        status.message += " (AWS Backup으로 보호됨)"
                    # backup_method는 이미 "aws-backup"이므로 변경 불필요

    # 실패한 작업 수집
    result.failed_jobs = _collect_failed_backup_jobs(session, account_id, account_name, region)

    # 데이터가 하나라도 있으면 반환
    if result.backup_statuses or result.tag_conditions or result.failed_jobs:
        return result
    return None


# ============================================================================
# 보고서 생성
# ============================================================================
