"""
plugins/resource_explorer/common/services/monitoring.py - Monitoring 리소스 수집

CloudWatch Alarm, CloudWatch Log Group 수집.
"""

from core.parallel import get_client

from ..types import CloudWatchAlarm, CloudWatchLogGroup


def collect_cloudwatch_alarms(session, account_id: str, account_name: str, region: str) -> list[CloudWatchAlarm]:
    """CloudWatch Alarm 수집"""
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
                except Exception:
                    pass

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
    """CloudWatch Log Group 수집"""
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
            except Exception:
                pass

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
