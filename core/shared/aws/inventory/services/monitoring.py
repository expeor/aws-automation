"""
core/shared/aws/inventory/services/monitoring.py - Monitoring 리소스 수집

CloudWatch Alarm, CloudWatch Log Group 수집.
"""

from __future__ import annotations

import logging

from core.parallel import get_client

from ..types import CloudWatchAlarm, CloudWatchLogGroup

logger = logging.getLogger(__name__)


def collect_cloudwatch_alarms(session, account_id: str, account_name: str, region: str) -> list[CloudWatchAlarm]:
    """CloudWatch Metric Alarm 리소스를 수집합니다.

    Metric Alarm 목록 조회 후 각 알람의 메트릭, 임계값, 비교 연산자,
    평가 기간, Action 설정 등 상세 정보와 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        CloudWatchAlarm 데이터 클래스 목록
    """
    cw = get_client(session, "cloudwatch", region_name=region)
    alarms = []

    paginator = cw.get_paginator("describe_alarms")
    for page in paginator.paginate():
        for alarm in page.get("MetricAlarms", []):
            alarm_arn = alarm.get("AlarmArn", "")

            # 태그 조회
            tags = {}
            if alarm_arn:
                try:
                    tags_resp = cw.list_tags_for_resource(ResourceARN=alarm_arn)
                    tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("Tags", [])}
                except Exception as e:
                    logger.debug("Failed to get tags: %s", e)

            alarms.append(
                CloudWatchAlarm(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    alarm_name=alarm.get("AlarmName", ""),
                    alarm_arn=alarm_arn,
                    state_value=alarm.get("StateValue", ""),
                    metric_name=alarm.get("MetricName", ""),
                    namespace=alarm.get("Namespace", ""),
                    statistic=alarm.get("Statistic", ""),
                    period=alarm.get("Period", 0),
                    threshold=alarm.get("Threshold", 0.0),
                    comparison_operator=alarm.get("ComparisonOperator", ""),
                    evaluation_periods=alarm.get("EvaluationPeriods", 0),
                    datapoints_to_alarm=alarm.get("DatapointsToAlarm", 0),
                    treat_missing_data=alarm.get("TreatMissingData", ""),
                    actions_enabled=alarm.get("ActionsEnabled", True),
                    alarm_actions=alarm.get("AlarmActions", []),
                    insufficient_data_actions=alarm.get("InsufficientDataActions", []),
                    ok_actions=alarm.get("OKActions", []),
                    state_updated_timestamp=alarm.get("StateUpdatedTimestamp"),
                    tags=tags,
                )
            )

    return alarms


def collect_cloudwatch_log_groups(session, account_id: str, account_name: str, region: str) -> list[CloudWatchLogGroup]:
    """CloudWatch Log Group 리소스를 수집합니다.

    Log Group 목록 조회 후 각 그룹의 저장 크기, 보존 기간, Metric Filter 수,
    KMS 암호화 설정 등과 태그를 함께 수집합니다.

    Args:
        session: boto3 Session 객체
        account_id: AWS 계정 ID
        account_name: AWS 계정 이름
        region: AWS 리전 코드

    Returns:
        CloudWatchLogGroup 데이터 클래스 목록
    """
    logs = get_client(session, "logs", region_name=region)
    log_groups = []

    paginator = logs.get_paginator("describe_log_groups")
    for page in paginator.paginate():
        for lg in page.get("logGroups", []):
            log_group_name = lg.get("logGroupName", "")
            log_group_arn = lg.get("arn", "")

            # 태그 조회
            tags = {}
            try:
                tags_resp = logs.list_tags_for_resource(resourceArn=log_group_arn)
                tags = tags_resp.get("tags", {})
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

            log_groups.append(
                CloudWatchLogGroup(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    log_group_name=log_group_name,
                    log_group_arn=log_group_arn,
                    stored_bytes=lg.get("storedBytes", 0),
                    retention_in_days=lg.get("retentionInDays"),
                    metric_filter_count=lg.get("metricFilterCount", 0),
                    kms_key_id=lg.get("kmsKeyId", ""),
                    creation_time=lg.get("creationTime", 0),
                    tags=tags,
                )
            )

    return log_groups
