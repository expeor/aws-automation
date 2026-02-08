"""
core/shared/aws/inventory/services/analytics.py - Analytics 리소스 수집

Kinesis Stream, Kinesis Firehose, Glue Database 수집.
"""

from __future__ import annotations

import logging

from core.parallel import get_client

from ..types import GlueDatabase, KinesisFirehose, KinesisStream

logger = logging.getLogger(__name__)


def collect_kinesis_streams(session, account_id: str, account_name: str, region: str) -> list[KinesisStream]:
    """Kinesis Data Stream 리소스를 수집합니다.

    스트림 목록 조회 후 각 스트림의 상세 정보(샤드 수, 보존 기간, 암호화 등)와 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        KinesisStream 데이터 클래스 목록
    """
    kinesis = get_client(session, "kinesis", region_name=region)
    streams = []

    try:
        paginator = kinesis.get_paginator("list_streams")
        for page in paginator.paginate():
            for stream_name in page.get("StreamNames", []):
                try:
                    # 상세 정보 조회
                    detail = kinesis.describe_stream_summary(StreamName=stream_name)
                    summary = detail.get("StreamDescriptionSummary", {})

                    stream_arn = summary.get("StreamARN", "")

                    # 태그 조회
                    tags = {}
                    try:
                        tags_resp = kinesis.list_tags_for_stream(StreamName=stream_name)
                        tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("Tags", [])}
                    except Exception as e:
                        logger.debug("Failed to get tags for stream %s: %s", stream_name, e)

                    streams.append(
                        KinesisStream(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            stream_name=stream_name,
                            stream_arn=stream_arn,
                            status=summary.get("StreamStatus", ""),
                            stream_mode=summary.get("StreamModeDetails", {}).get("StreamMode", ""),
                            shard_count=summary.get("OpenShardCount", 0),
                            retention_period_hours=summary.get("RetentionPeriodHours", 24),
                            encryption_type=summary.get("EncryptionType", ""),
                            kms_key_id=summary.get("KeyId", ""),
                            stream_creation_timestamp=summary.get("StreamCreationTimestamp"),
                            tags=tags,
                        )
                    )
                except Exception as e:
                    logger.debug("Failed to describe stream %s: %s", stream_name, e)
    except Exception as e:
        logger.debug("Failed to list Kinesis streams: %s", e)

    return streams


def collect_kinesis_firehoses(session, account_id: str, account_name: str, region: str) -> list[KinesisFirehose]:
    """Kinesis Firehose Delivery Stream을 수집합니다.

    Delivery Stream 목록 조회 후 각 스트림의 상세 정보(소스/대상 타입 등)와 태그를 함께 수집합니다.
    list_delivery_streams에는 paginator가 없으므로 수동 페이지네이션을 사용합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        KinesisFirehose 데이터 클래스 목록
    """
    firehose = get_client(session, "firehose", region_name=region)
    delivery_streams = []

    try:
        # list_delivery_streams는 paginator가 없음
        stream_names = []
        has_more = True
        start_name = None

        while has_more:
            params = {"Limit": 100}
            if start_name:
                params["ExclusiveStartDeliveryStreamName"] = start_name

            resp = firehose.list_delivery_streams(**params)
            names = resp.get("DeliveryStreamNames", [])
            stream_names.extend(names)

            has_more = resp.get("HasMoreDeliveryStreams", False)
            if names:
                start_name = names[-1]

        for stream_name in stream_names:
            try:
                detail = firehose.describe_delivery_stream(DeliveryStreamName=stream_name)
                desc = detail.get("DeliveryStreamDescription", {})

                stream_arn = desc.get("DeliveryStreamARN", "")

                # 소스/대상 타입
                source = desc.get("Source", {})
                source_type = "DirectPut"
                if source.get("KinesisStreamSourceDescription"):
                    source_type = "KinesisStream"
                elif source.get("MSKSourceDescription"):
                    source_type = "MSK"

                destinations = desc.get("Destinations", [])
                destination_type = ""
                if destinations:
                    dest = destinations[0]
                    if dest.get("S3DestinationDescription"):
                        destination_type = "S3"
                    elif dest.get("ExtendedS3DestinationDescription"):
                        destination_type = "ExtendedS3"
                    elif dest.get("RedshiftDestinationDescription"):
                        destination_type = "Redshift"
                    elif dest.get("ElasticsearchDestinationDescription"):
                        destination_type = "Elasticsearch"
                    elif dest.get("SplunkDestinationDescription"):
                        destination_type = "Splunk"
                    elif dest.get("HttpEndpointDestinationDescription"):
                        destination_type = "HttpEndpoint"
                    elif dest.get("AmazonOpenSearchServerlessDestinationDescription"):
                        destination_type = "OpenSearchServerless"

                # 태그 조회
                tags = {}
                try:
                    tags_resp = firehose.list_tags_for_delivery_stream(DeliveryStreamName=stream_name)
                    tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("Tags", [])}
                except Exception as e:
                    logger.debug("Failed to get tags for delivery stream %s: %s", stream_name, e)

                delivery_streams.append(
                    KinesisFirehose(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        delivery_stream_name=stream_name,
                        delivery_stream_arn=stream_arn,
                        delivery_stream_status=desc.get("DeliveryStreamStatus", ""),
                        delivery_stream_type=desc.get("DeliveryStreamType", ""),
                        source_type=source_type,
                        destination_type=destination_type,
                        has_more_destinations=desc.get("HasMoreDestinations", False),
                        version_id=desc.get("VersionId", ""),
                        create_timestamp=desc.get("CreateTimestamp"),
                        tags=tags,
                    )
                )
            except Exception as e:
                logger.debug("Failed to describe delivery stream %s: %s", stream_name, e)
    except Exception as e:
        logger.debug("Failed to list Firehose delivery streams: %s", e)

    return delivery_streams


def collect_glue_databases(session, account_id: str, account_name: str, region: str) -> list[GlueDatabase]:
    """Glue Database 리소스를 수집합니다.

    데이터베이스 목록 조회 후 각 데이터베이스의 테이블 수를 확인합니다.
    Glue Database는 태그 API가 별도이므로 태그는 빈 딕셔너리로 설정됩니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        GlueDatabase 데이터 클래스 목록
    """
    glue = get_client(session, "glue", region_name=region)
    databases = []

    try:
        paginator = glue.get_paginator("get_databases")
        for page in paginator.paginate():
            for db in page.get("DatabaseList", []):
                db_name = db.get("Name", "")

                # 테이블 수 조회
                table_count = 0
                try:
                    tables_resp = glue.get_tables(DatabaseName=db_name, MaxResults=1)
                    # 정확한 수를 위해서는 모든 테이블을 페이지네이션해야 하지만
                    # 여기서는 간단히 첫 페이지가 있는지만 확인
                    table_count = len(tables_resp.get("TableList", []))
                    if tables_resp.get("NextToken"):
                        table_count = -1  # 1개 이상
                except Exception as e:
                    logger.debug("Failed to get tables for database %s: %s", db_name, e)

                databases.append(
                    GlueDatabase(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        database_name=db_name,
                        catalog_id=db.get("CatalogId", ""),
                        description=db.get("Description", ""),
                        location_uri=db.get("LocationUri", ""),
                        table_count=table_count,
                        create_time=db.get("CreateTime"),
                        tags={},  # Glue Database는 태그 API가 다름
                    )
                )
    except Exception as e:
        logger.debug("Failed to list Glue databases: %s", e)

    return databases
