"""
plugins/resource_explorer/common/services/messaging.py - Integration/Messaging 리소스 수집

SNS Topic, SQS Queue, EventBridge Rule, Step Functions, API Gateway 수집.
"""

import logging

from core.parallel import get_client

from ..types import APIGatewayAPI, EventBridgeRule, SNSTopic, SQSQueue, StepFunction

logger = logging.getLogger(__name__)


def collect_sns_topics(session, account_id: str, account_name: str, region: str) -> list[SNSTopic]:
    """SNS Topic 수집"""
    sns = get_client(session, "sns", region_name=region)
    topics = []

    paginator = sns.get_paginator("list_topics")
    for page in paginator.paginate():
        for topic in page.get("Topics", []):
            topic_arn = topic.get("TopicArn", "")
            # ARN에서 이름 추출
            name = topic_arn.split(":")[-1] if topic_arn else ""

            try:
                # 속성 조회
                attrs_resp = sns.get_topic_attributes(TopicArn=topic_arn)
                attrs = attrs_resp.get("Attributes", {})

                # 태그 조회
                tags = {}
                try:
                    tags_resp = sns.list_tags_for_resource(ResourceArn=topic_arn)
                    tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("Tags", [])}
                except Exception as e:
                    logger.debug("Failed to get tags: %s", e)

                topics.append(
                    SNSTopic(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        topic_arn=topic_arn,
                        name=name,
                        display_name=attrs.get("DisplayName", ""),
                        subscriptions_confirmed=int(attrs.get("SubscriptionsConfirmed", 0)),
                        subscriptions_pending=int(attrs.get("SubscriptionsPending", 0)),
                        kms_key_id=attrs.get("KmsMasterKeyId", ""),
                        fifo_topic=attrs.get("FifoTopic", "false") == "true",
                        content_based_deduplication=attrs.get("ContentBasedDeduplication", "false") == "true",
                        tags=tags,
                    )
                )
            except Exception as e:
                logger.debug("Failed to get resource details: %s", e)

    return topics


def collect_sqs_queues(session, account_id: str, account_name: str, region: str) -> list[SQSQueue]:
    """SQS Queue 수집"""
    sqs = get_client(session, "sqs", region_name=region)
    queues = []

    try:
        paginator = sqs.get_paginator("list_queues")
        for page in paginator.paginate():
            for queue_url in page.get("QueueUrls", []):
                try:
                    # 속성 조회
                    attrs_resp = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])
                    attrs = attrs_resp.get("Attributes", {})

                    # 이름 추출
                    name = queue_url.split("/")[-1]
                    queue_arn = attrs.get("QueueArn", "")

                    # 태그 조회
                    tags = {}
                    try:
                        tags_resp = sqs.list_queue_tags(QueueUrl=queue_url)
                        tags = tags_resp.get("Tags", {})
                    except Exception as e:
                        logger.debug("Failed to get details: %s", e)

                    queues.append(
                        SQSQueue(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            queue_url=queue_url,
                            queue_arn=queue_arn,
                            name=name,
                            fifo_queue=name.endswith(".fifo"),
                            visibility_timeout=int(attrs.get("VisibilityTimeout", 30)),
                            message_retention_period=int(attrs.get("MessageRetentionPeriod", 345600)),
                            max_message_size=int(attrs.get("MaximumMessageSize", 262144)),
                            delay_seconds=int(attrs.get("DelaySeconds", 0)),
                            receive_message_wait_time=int(attrs.get("ReceiveMessageWaitTimeSeconds", 0)),
                            approximate_number_of_messages=int(attrs.get("ApproximateNumberOfMessages", 0)),
                            kms_key_id=attrs.get("KmsMasterKeyId", ""),
                            dead_letter_target_arn=attrs.get("RedrivePolicy", ""),
                            created_timestamp=attrs.get("CreatedTimestamp", ""),
                            tags=tags,
                        )
                    )
                except Exception as e:
                    logger.debug("Failed to get tags: %s", e)
    except Exception as e:
        logger.debug("Failed to list resources: %s", e)

    return queues


def collect_eventbridge_rules(session, account_id: str, account_name: str, region: str) -> list[EventBridgeRule]:
    """EventBridge Rule 수집"""
    events = get_client(session, "events", region_name=region)
    rules = []

    # 이벤트 버스 목록 조회
    event_buses = ["default"]
    try:
        bus_resp = events.list_event_buses()
        for bus in bus_resp.get("EventBuses", []):
            if bus.get("Name") != "default":
                event_buses.append(bus.get("Name", ""))
    except Exception as e:
        logger.debug("Failed to list resources: %s", e)

    for bus_name in event_buses:
        try:
            paginator = events.get_paginator("list_rules")
            for page in paginator.paginate(EventBusName=bus_name):
                for rule in page.get("Rules", []):
                    rule_name = rule.get("Name", "")

                    # 타겟 수 조회
                    target_count = 0
                    try:
                        targets_resp = events.list_targets_by_rule(Rule=rule_name, EventBusName=bus_name)
                        target_count = len(targets_resp.get("Targets", []))
                    except Exception as e:
                        logger.debug("Failed to get details: %s", e)

                    # 태그 조회
                    tags = {}
                    rule_arn = rule.get("Arn", "")
                    if rule_arn:
                        try:
                            tags_resp = events.list_tags_for_resource(ResourceARN=rule_arn)
                            tags = {tag["Key"]: tag["Value"] for tag in tags_resp.get("Tags", [])}
                        except Exception as e:
                            logger.debug("Failed to get EventBridge rule tags: %s", e)

                    rules.append(
                        EventBridgeRule(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            rule_name=rule_name,
                            rule_arn=rule_arn,
                            event_bus_name=bus_name,
                            state=rule.get("State", ""),
                            description=rule.get("Description", ""),
                            schedule_expression=rule.get("ScheduleExpression", ""),
                            event_pattern=rule.get("EventPattern", ""),
                            target_count=target_count,
                            managed_by=rule.get("ManagedBy", ""),
                            tags=tags,
                        )
                    )
        except Exception as e:
            logger.debug("Failed to process rules: %s", e)

    return rules


def collect_step_functions(session, account_id: str, account_name: str, region: str) -> list[StepFunction]:
    """Step Functions State Machine 수집"""
    sfn = get_client(session, "stepfunctions", region_name=region)
    state_machines = []

    try:
        paginator = sfn.get_paginator("list_state_machines")
        for page in paginator.paginate():
            for sm in page.get("stateMachines", []):
                sm_arn = sm.get("stateMachineArn", "")

                # 상세 정보 조회
                try:
                    detail = sfn.describe_state_machine(stateMachineArn=sm_arn)

                    # 태그 조회
                    tags = {}
                    try:
                        tags_resp = sfn.list_tags_for_resource(resourceArn=sm_arn)
                        tags = {tag["key"]: tag["value"] for tag in tags_resp.get("tags", [])}
                    except Exception as e:
                        logger.debug("Failed to get details: %s", e)

                    logging_config = detail.get("loggingConfiguration", {})
                    tracing_config = detail.get("tracingConfiguration", {})

                    state_machines.append(
                        StepFunction(
                            account_id=account_id,
                            account_name=account_name,
                            region=region,
                            state_machine_arn=sm_arn,
                            name=sm.get("name", ""),
                            state_machine_type=sm.get("type", ""),
                            status=detail.get("status", ""),
                            role_arn=detail.get("roleArn", ""),
                            logging_level=logging_config.get("level", ""),
                            tracing_enabled=tracing_config.get("enabled", False),
                            creation_date=sm.get("creationDate"),
                            tags=tags,
                        )
                    )
                except Exception as e:
                    logger.debug("Failed to get tags: %s", e)
    except Exception as e:
        logger.debug("Failed to list resources: %s", e)

    return state_machines


def collect_api_gateway_apis(session, account_id: str, account_name: str, region: str) -> list[APIGatewayAPI]:
    """API Gateway REST/HTTP API 수집"""
    apis = []

    # REST API (API Gateway v1)
    try:
        apigw = get_client(session, "apigateway", region_name=region)
        paginator = apigw.get_paginator("get_rest_apis")
        for page in paginator.paginate():
            for api in page.get("items", []):
                api_id = api.get("id", "")

                # 태그
                tags = api.get("tags", {})

                # Endpoint Type
                endpoint_config = api.get("endpointConfiguration", {})
                endpoint_types = endpoint_config.get("types", [])
                endpoint_type = endpoint_types[0] if endpoint_types else ""

                apis.append(
                    APIGatewayAPI(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        api_id=api_id,
                        name=api.get("name", ""),
                        api_type="REST",
                        protocol_type="REST",
                        endpoint_type=endpoint_type,
                        description=api.get("description", ""),
                        version=api.get("version", ""),
                        api_endpoint=f"https://{api_id}.execute-api.{region}.amazonaws.com",
                        disable_execute_api_endpoint=api.get("disableExecuteApiEndpoint", False),
                        created_date=api.get("createdDate"),
                        tags=tags,
                    )
                )
    except Exception as e:
        logger.debug("Failed to list resources: %s", e)

    # HTTP/WebSocket API (API Gateway v2)
    try:
        apigwv2 = get_client(session, "apigatewayv2", region_name=region)
        paginator = apigwv2.get_paginator("get_apis")
        for page in paginator.paginate():
            for api in page.get("Items", []):
                api_id = api.get("ApiId", "")
                protocol = api.get("ProtocolType", "")

                apis.append(
                    APIGatewayAPI(
                        account_id=account_id,
                        account_name=account_name,
                        region=region,
                        api_id=api_id,
                        name=api.get("Name", ""),
                        api_type="HTTP" if protocol == "HTTP" else "WEBSOCKET",
                        protocol_type=protocol,
                        endpoint_type="REGIONAL",
                        description=api.get("Description", ""),
                        version=api.get("Version", ""),
                        api_endpoint=api.get("ApiEndpoint", ""),
                        disable_execute_api_endpoint=api.get("DisableExecuteApiEndpoint", False),
                        created_date=api.get("CreatedDate"),
                        tags=api.get("Tags", {}),
                    )
                )
    except Exception as e:
        logger.debug("Failed to list resources: %s", e)

    return apis
