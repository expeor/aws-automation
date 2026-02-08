"""
core/shared/aws/inventory/services/database.py - Database/Storage 리소스 수집

RDS Instance, S3 Bucket, DynamoDB Table, ElastiCache Cluster 수집.
"""

from __future__ import annotations

import logging

from core.parallel import get_client

from ..types import DynamoDBTable, ElastiCacheCluster, RDSCluster, RDSInstance, RedshiftCluster, S3Bucket

logger = logging.getLogger(__name__)


def collect_rds_instances(session, account_id: str, account_name: str, region: str) -> list[RDSInstance]:
    """RDS Instance 리소스를 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        RDSInstance 데이터 클래스 목록
    """
    rds = get_client(session, "rds", region_name=region)
    instances = []

    paginator = rds.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page.get("DBInstances", []):
            # 태그 조회
            tags = {}
            try:
                tags_resp = rds.list_tags_for_resource(ResourceName=db["DBInstanceArn"])
                tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("TagList", [])}
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            # Endpoint 정보
            endpoint = db.get("Endpoint", {})
            endpoint_address = endpoint.get("Address", "")
            port = endpoint.get("Port", 0)

            # VPC 정보
            vpc_id = ""
            if db.get("DBSubnetGroup"):
                vpc_id = db["DBSubnetGroup"].get("VpcId", "")

            instances.append(
                RDSInstance(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    db_instance_id=db["DBInstanceIdentifier"],
                    db_instance_arn=db["DBInstanceArn"],
                    db_instance_class=db.get("DBInstanceClass", ""),
                    engine=db.get("Engine", ""),
                    engine_version=db.get("EngineVersion", ""),
                    status=db.get("DBInstanceStatus", ""),
                    endpoint=endpoint_address,
                    port=port,
                    allocated_storage=db.get("AllocatedStorage", 0),
                    storage_type=db.get("StorageType", ""),
                    multi_az=db.get("MultiAZ", False),
                    publicly_accessible=db.get("PubliclyAccessible", False),
                    encrypted=db.get("StorageEncrypted", False),
                    vpc_id=vpc_id,
                    availability_zone=db.get("AvailabilityZone", ""),
                    db_cluster_id=db.get("DBClusterIdentifier", ""),
                    create_time=db.get("InstanceCreateTime"),
                    tags=tags,
                )
            )

    return instances


def collect_s3_buckets(session, account_id: str, account_name: str, region: str) -> list[S3Bucket]:
    """S3 Bucket 리소스를 수집합니다 (글로벌 서비스).

    S3는 글로벌 서비스이므로 us-east-1에서만 수집합니다. 각 버킷의 리전, 버저닝, 암호화,
    Public Access Block, 로깅, Lifecycle 규칙 등 상세 정보와 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드 (us-east-1이 아니면 빈 목록 반환)

    Returns:
        S3Bucket 데이터 클래스 목록
    """
    # S3는 글로벌 서비스이므로 us-east-1에서만 수집
    if region != "us-east-1":
        return []

    s3 = get_client(session, "s3", region_name=region)
    buckets = []

    try:
        resp = s3.list_buckets()
        for bucket in resp.get("Buckets", []):
            bucket_name = bucket["Name"]

            # 버킷 리전 확인
            bucket_region = ""
            try:
                loc_resp = s3.get_bucket_location(Bucket=bucket_name)
                bucket_region = loc_resp.get("LocationConstraint") or "us-east-1"
            except Exception as e:
                logger.debug("Failed to get bucket location: %s", e)
                bucket_region = "unknown"

            # 버저닝 상태
            versioning_status = ""
            try:
                ver_resp = s3.get_bucket_versioning(Bucket=bucket_name)
                versioning_status = ver_resp.get("Status", "Disabled")
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            # 암호화 설정
            encryption_type = ""
            try:
                enc_resp = s3.get_bucket_encryption(Bucket=bucket_name)
                rules = enc_resp.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
                if rules:
                    encryption_type = rules[0].get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm", "")
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            # Public Access Block
            public_access_block = True
            try:
                pab_resp = s3.get_public_access_block(Bucket=bucket_name)
                config = pab_resp.get("PublicAccessBlockConfiguration", {})
                public_access_block = all(
                    [
                        config.get("BlockPublicAcls", False),
                        config.get("IgnorePublicAcls", False),
                        config.get("BlockPublicPolicy", False),
                        config.get("RestrictPublicBuckets", False),
                    ]
                )
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            # 로깅 설정
            logging_enabled = False
            try:
                log_resp = s3.get_bucket_logging(Bucket=bucket_name)
                logging_enabled = bool(log_resp.get("LoggingEnabled"))
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            # 수명 주기 규칙
            lifecycle_rules_count = 0
            try:
                lc_resp = s3.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                lifecycle_rules_count = len(lc_resp.get("Rules", []))
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            # 태그
            tags = {}
            try:
                tags_resp = s3.get_bucket_tagging(Bucket=bucket_name)
                tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("TagSet", [])}
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            buckets.append(
                S3Bucket(
                    account_id=account_id,
                    account_name=account_name,
                    region=bucket_region,
                    bucket_name=bucket_name,
                    creation_date=bucket.get("CreationDate"),
                    versioning_status=versioning_status,
                    encryption_type=encryption_type,
                    public_access_block=public_access_block,
                    logging_enabled=logging_enabled,
                    lifecycle_rules_count=lifecycle_rules_count,
                    tags=tags,
                )
            )

    except Exception as e:
        logger.debug("Failed to list resources: %s", e)

    return buckets


def collect_dynamodb_tables(session, account_id: str, account_name: str, region: str) -> list[DynamoDBTable]:
    """DynamoDB Table 리소스를 수집합니다.

    테이블 목록 조회 후 각 테이블의 상세 정보(Billing Mode, Provisioned Throughput,
    GSI/LSI 수, Stream, 암호화 등)와 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        DynamoDBTable 데이터 클래스 목록
    """
    dynamodb = get_client(session, "dynamodb", region_name=region)
    tables = []

    # 테이블 목록 조회
    table_names = []
    paginator = dynamodb.get_paginator("list_tables")
    for page in paginator.paginate():
        table_names.extend(page.get("TableNames", []))

    # 각 테이블 상세 정보 조회
    for table_name in table_names:
        try:
            resp = dynamodb.describe_table(TableName=table_name)
            table = resp.get("Table", {})

            # Billing Mode
            billing_mode = table.get("BillingModeSummary", {}).get("BillingMode", "PROVISIONED")

            # Provisioned throughput
            throughput = table.get("ProvisionedThroughput", {})
            read_capacity = throughput.get("ReadCapacityUnits", 0)
            write_capacity = throughput.get("WriteCapacityUnits", 0)

            # GSI/LSI 수
            gsi_count = len(table.get("GlobalSecondaryIndexes", []))
            lsi_count = len(table.get("LocalSecondaryIndexes", []))

            # Stream
            stream_spec = table.get("StreamSpecification", {})
            stream_enabled = stream_spec.get("StreamEnabled", False)

            # 암호화
            sse_desc = table.get("SSEDescription", {})
            encryption_type = sse_desc.get("SSEType", "")

            # 태그 조회
            tags = {}
            try:
                tags_resp = dynamodb.list_tags_of_resource(ResourceArn=table["TableArn"])
                tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("Tags", [])}
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            tables.append(
                DynamoDBTable(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    table_name=table_name,
                    table_arn=table.get("TableArn", ""),
                    status=table.get("TableStatus", ""),
                    billing_mode=billing_mode,
                    item_count=table.get("ItemCount", 0),
                    table_size_bytes=table.get("TableSizeBytes", 0),
                    read_capacity=read_capacity,
                    write_capacity=write_capacity,
                    gsi_count=gsi_count,
                    lsi_count=lsi_count,
                    stream_enabled=stream_enabled,
                    encryption_type=encryption_type,
                    create_time=table.get("CreationDateTime"),
                    tags=tags,
                )
            )
        except Exception as e:
            logger.debug("Failed to process item: %s", e)

    return tables


def collect_elasticache_clusters(session, account_id: str, account_name: str, region: str) -> list[ElastiCacheCluster]:
    """ElastiCache Cluster 리소스를 수집합니다.

    Cluster 목록 조회 후 각 Cluster의 노드 정보, Security Group, 암호화 설정 등과
    태그를 함께 수집합니다. VPC ID는 Subnet Group에서 별도 조회가 필요합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        ElastiCacheCluster 데이터 클래스 목록
    """
    elasticache = get_client(session, "elasticache", region_name=region)
    clusters = []

    paginator = elasticache.get_paginator("describe_cache_clusters")
    for page in paginator.paginate(ShowCacheNodeInfo=True):
        for cluster in page.get("CacheClusters", []):
            # Security Group IDs
            security_groups = [sg.get("SecurityGroupId", "") for sg in cluster.get("SecurityGroups", [])]

            # 태그 조회
            tags = {}
            try:
                arn = cluster.get("ARN", "")
                if arn:
                    tags_resp = elasticache.list_tags_for_resource(ResourceName=arn)
                    tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("TagList", [])}
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            clusters.append(
                ElastiCacheCluster(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    cluster_id=cluster.get("CacheClusterId", ""),
                    cluster_arn=cluster.get("ARN", ""),
                    engine=cluster.get("Engine", ""),
                    engine_version=cluster.get("EngineVersion", ""),
                    node_type=cluster.get("CacheNodeType", ""),
                    status=cluster.get("CacheClusterStatus", ""),
                    num_nodes=cluster.get("NumCacheNodes", 0),
                    availability_zone=cluster.get("PreferredAvailabilityZone", ""),
                    vpc_id="",  # VPC ID는 Subnet Group에서 조회 필요
                    subnet_group=cluster.get("CacheSubnetGroupName", ""),
                    security_groups=security_groups,
                    encryption_at_rest=cluster.get("AtRestEncryptionEnabled", False),
                    encryption_in_transit=cluster.get("TransitEncryptionEnabled", False),
                    create_time=cluster.get("CacheClusterCreateTime"),
                    tags=tags,
                )
            )

    return clusters


def collect_rds_clusters(session, account_id: str, account_name: str, region: str) -> list[RDSCluster]:
    """RDS Cluster (Aurora) 리소스를 수집합니다.

    Aurora DB Cluster 목록 조회 후 각 Cluster의 엔진, Endpoint, Multi-AZ,
    암호화, 백업 보존 기간 등 상세 정보와 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        RDSCluster 데이터 클래스 목록
    """
    rds = get_client(session, "rds", region_name=region)
    clusters = []

    paginator = rds.get_paginator("describe_db_clusters")
    for page in paginator.paginate():
        for cluster in page.get("DBClusters", []):
            # 태그 조회
            tags = {}
            try:
                tags_resp = rds.list_tags_for_resource(ResourceName=cluster["DBClusterArn"])
                tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("TagList", [])}
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            # VPC 정보
            vpc_id = ""
            if cluster.get("DBSubnetGroup"):
                vpc_id = cluster["DBSubnetGroup"] if isinstance(cluster["DBSubnetGroup"], str) else ""

            clusters.append(
                RDSCluster(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    cluster_id=cluster.get("DBClusterIdentifier", ""),
                    cluster_arn=cluster.get("DBClusterArn", ""),
                    engine=cluster.get("Engine", ""),
                    engine_version=cluster.get("EngineVersion", ""),
                    status=cluster.get("Status", ""),
                    endpoint=cluster.get("Endpoint", ""),
                    reader_endpoint=cluster.get("ReaderEndpoint", ""),
                    port=cluster.get("Port", 0),
                    db_cluster_members=len(cluster.get("DBClusterMembers", [])),
                    multi_az=cluster.get("MultiAZ", False),
                    storage_encrypted=cluster.get("StorageEncrypted", False),
                    kms_key_id=cluster.get("KmsKeyId", ""),
                    vpc_id=vpc_id,
                    availability_zones=cluster.get("AvailabilityZones", []),
                    backup_retention_period=cluster.get("BackupRetentionPeriod", 0),
                    cluster_create_time=cluster.get("ClusterCreateTime"),
                    tags=tags,
                )
            )

    return clusters


def collect_redshift_clusters(session, account_id: str, account_name: str, region: str) -> list[RedshiftCluster]:
    """Redshift Cluster 리소스를 수집합니다.

    Cluster 목록 조회 후 각 Cluster의 노드 타입, 노드 수, Endpoint, 암호화 설정,
    퍼블릭 접근 가능 여부 등 상세 정보와 태그를 함께 수집합니다.
    ARN은 리전, 계정 ID, Cluster ID로 직접 구성합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        RedshiftCluster 데이터 클래스 목록
    """
    redshift = get_client(session, "redshift", region_name=region)
    clusters = []

    paginator = redshift.get_paginator("describe_clusters")
    for page in paginator.paginate():
        for cluster in page.get("Clusters", []):
            # 태그
            tags = {tag["Key"]: tag["Value"] for tag in cluster.get("Tags", [])}

            # Endpoint
            endpoint = ""
            port = 5439
            if cluster.get("Endpoint"):
                endpoint = cluster["Endpoint"].get("Address", "")
                port = cluster["Endpoint"].get("Port", 5439)

            # ARN 구성
            cluster_id = cluster.get("ClusterIdentifier", "")
            cluster_arn = f"arn:aws:redshift:{region}:{account_id}:cluster:{cluster_id}"

            clusters.append(
                RedshiftCluster(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    cluster_id=cluster_id,
                    cluster_arn=cluster_arn,
                    node_type=cluster.get("NodeType", ""),
                    cluster_status=cluster.get("ClusterStatus", ""),
                    number_of_nodes=cluster.get("NumberOfNodes", 1),
                    db_name=cluster.get("DBName", ""),
                    endpoint=endpoint,
                    port=port,
                    vpc_id=cluster.get("VpcId", ""),
                    availability_zone=cluster.get("AvailabilityZone", ""),
                    encrypted=cluster.get("Encrypted", False),
                    kms_key_id=cluster.get("KmsKeyId", ""),
                    publicly_accessible=cluster.get("PubliclyAccessible", False),
                    cluster_create_time=cluster.get("ClusterCreateTime"),
                    tags=tags,
                )
            )

    return clusters
