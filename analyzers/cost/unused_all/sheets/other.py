"""미사용 리소스 리포트 시트 생성 함수"""

from __future__ import annotations

from shared.io.excel import ColumnDef, Styles, Workbook


def _create_loggroup_sheet(wb: Workbook, results) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Log Group", width=40, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="저장 (GB)", width=12, style="number"),
        ColumnDef(header="보존 기간", width=12, style="data"),
        ColumnDef(header="마지막 Ingestion", width=15, style="data"),
        ColumnDef(header="월간 비용", width=12, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("Log Group", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                lg = f.log_group
                sheet.add_row(
                    [
                        lg.account_name,
                        lg.region,
                        lg.name,
                        f.status.value,
                        round(lg.stored_gb, 4),
                        f"{lg.retention_days}일" if lg.retention_days else "무기한",
                        lg.last_ingestion_time.strftime("%Y-%m-%d") if lg.last_ingestion_time else "-",
                        round(lg.monthly_cost, 4),
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_secret_sheet(wb: Workbook, results) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Name", width=40, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="마지막 액세스", width=15, style="data"),
        ColumnDef(header="월간 비용", width=12, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("Secrets Manager", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                sec = f.secret
                last_access = sec.last_accessed_date.strftime("%Y-%m-%d") if sec.last_accessed_date else "없음"
                sheet.add_row(
                    [
                        sec.account_name,
                        sec.region,
                        sec.name,
                        f.status.value,
                        last_access,
                        round(sec.monthly_cost, 2),
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_kms_sheet(wb: Workbook, results) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Key ID", width=40, style="data"),
        ColumnDef(header="Description", width=50, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="Manager", width=12, style="center"),
        ColumnDef(header="월간 비용", width=12, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("KMS", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                key = f.key
                sheet.add_row(
                    [
                        key.account_name,
                        key.region,
                        key.key_id,
                        key.description[:50] if key.description else "-",
                        f.status.value,
                        key.key_manager,
                        round(key.monthly_cost, 2),
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_route53_sheet(wb: Workbook, results) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Zone ID", width=20, style="data"),
        ColumnDef(header="Domain", width=40, style="data"),
        ColumnDef(header="Type", width=10, style="center"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="레코드 수", width=10, style="number"),
        ColumnDef(header="월간 비용", width=12, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("Route53", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                zone = f.zone
                sheet.add_row(
                    [
                        zone.account_name,
                        zone.zone_id,
                        zone.name,
                        "Private" if zone.is_private else "Public",
                        f.status.value,
                        zone.record_count,
                        f"${zone.monthly_cost:.2f}",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_sqs_sheet(wb: Workbook, results) -> None:
    """SQS 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Queue Name", width=40, style="data"),
        ColumnDef(header="Type", width=15, style="center"),
        ColumnDef(header="Messages", width=12, style="number"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="Sent", width=10, style="number"),
        ColumnDef(header="Received", width=10, style="number"),
        ColumnDef(header="Deleted", width=10, style="number"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("SQS", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                q = f.queue
                queue_type = "FIFO" if q.is_fifo else "Standard"
                if q.is_dlq:
                    queue_type += " (DLQ)"
                sheet.add_row(
                    [
                        q.account_name,
                        q.region,
                        q.queue_name,
                        queue_type,
                        q.approximate_messages,
                        f.status.value,
                        int(q.messages_sent),
                        int(q.messages_received),
                        int(q.messages_deleted),
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_sns_sheet(wb: Workbook, results) -> None:
    """SNS 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Topic Name", width=40, style="data"),
        ColumnDef(header="Subscribers", width=12, style="number"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="Published", width=12, style="number"),
        ColumnDef(header="Delivered", width=12, style="number"),
        ColumnDef(header="Failed", width=10, style="number"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("SNS", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                t = f.topic
                sheet.add_row(
                    [
                        t.account_name,
                        t.region,
                        t.topic_name,
                        t.subscription_count,
                        f.status.value,
                        int(t.messages_published),
                        int(t.notifications_delivered),
                        int(t.notifications_failed),
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_acm_sheet(wb: Workbook, results) -> None:
    """ACM 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Domain", width=40, style="data"),
        ColumnDef(header="Type", width=12, style="center"),
        ColumnDef(header="Status", width=15, style="center"),
        ColumnDef(header="Expiry", width=12, style="data"),
        ColumnDef(header="Days Left", width=10, style="number"),
        ColumnDef(header="In Use", width=8, style="number"),
        ColumnDef(header="분석상태", width=12, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("ACM", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                c = f.cert
                sheet.add_row(
                    [
                        c.account_name,
                        c.region,
                        c.domain_name,
                        c.cert_type,
                        c.status,
                        c.not_after.strftime("%Y-%m-%d") if c.not_after else "-",
                        c.days_until_expiry if c.days_until_expiry else "-",
                        len(c.in_use_by),
                        f.status.value,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_apigateway_sheet(wb: Workbook, results) -> None:
    """API Gateway 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="API Name", width=30, style="data"),
        ColumnDef(header="Type", width=12, style="center"),
        ColumnDef(header="Endpoint", width=15, style="data"),
        ColumnDef(header="Stages", width=8, style="number"),
        ColumnDef(header="Requests", width=12, style="number"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("API Gateway", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                a = f.api
                sheet.add_row(
                    [
                        a.account_name,
                        a.region,
                        a.api_name,
                        a.api_type,
                        a.endpoint_type,
                        a.stage_count,
                        int(a.total_requests),
                        f.status.value,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_eventbridge_sheet(wb: Workbook, results) -> None:
    """EventBridge 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Rule Name", width=30, style="data"),
        ColumnDef(header="Event Bus", width=20, style="data"),
        ColumnDef(header="State", width=12, style="center"),
        ColumnDef(header="Schedule", width=20, style="data"),
        ColumnDef(header="Targets", width=8, style="number"),
        ColumnDef(header="Triggers", width=10, style="number"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("EventBridge", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                rule = f.rule
                sheet.add_row(
                    [
                        rule.account_name,
                        rule.region,
                        rule.rule_name,
                        rule.event_bus_name,
                        rule.state,
                        rule.schedule_expression or "-",
                        rule.target_count,
                        int(rule.triggered_rules),
                        f.status.value,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_cw_alarm_sheet(wb: Workbook, results) -> None:
    """CloudWatch Alarm 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Alarm Name", width=40, style="data"),
        ColumnDef(header="Namespace", width=25, style="data"),
        ColumnDef(header="Metric", width=25, style="data"),
        ColumnDef(header="Dimensions", width=30, style="data"),
        ColumnDef(header="State", width=15, style="center"),
        ColumnDef(header="분석상태", width=12, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("CloudWatch Alarm", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                a = f.alarm
                sheet.add_row(
                    [
                        a.account_name,
                        a.region,
                        a.alarm_name,
                        a.namespace,
                        a.metric_name,
                        a.dimensions,
                        a.state,
                        f.status.value,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_sagemaker_endpoint_sheet(wb: Workbook, results) -> None:
    """SageMaker Endpoint 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Endpoint Name", width=35, style="data"),
        ColumnDef(header="Status", width=12, style="center"),
        ColumnDef(header="Instance Type", width=18, style="data"),
        ColumnDef(header="Instance Count", width=12, style="number"),
        ColumnDef(header="Total Invocations", width=15, style="number"),
        ColumnDef(header="Avg/Day", width=10, style="data"),
        ColumnDef(header="Latency (ms)", width=12, style="data"),
        ColumnDef(header="Age (days)", width=10, style="number"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("SageMaker Endpoint", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                e = f.endpoint
                sheet.add_row(
                    [
                        e.account_name,
                        e.region,
                        e.endpoint_name,
                        e.status,
                        e.instance_type,
                        e.instance_count,
                        e.total_invocations,
                        f"{e.avg_invocations_per_day:.1f}",
                        f"{e.model_latency_avg_ms:.2f}",
                        e.age_days,
                        f"${e.estimated_monthly_cost:.2f}",
                        f.status.value,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_kinesis_sheet(wb: Workbook, results) -> None:
    """Kinesis 스트림 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Stream Name", width=35, style="data"),
        ColumnDef(header="Mode", width=12, style="center"),
        ColumnDef(header="Shards", width=8, style="number"),
        ColumnDef(header="Retention", width=12, style="data"),
        ColumnDef(header="Status", width=12, style="center"),
        ColumnDef(header="Avg Records/Day", width=15, style="data"),
        ColumnDef(header="Avg Bytes/Day", width=15, style="data"),
        ColumnDef(header="Consumers", width=10, style="number"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="분석상태", width=12, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("Kinesis", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                s = f.stream
                sheet.add_row(
                    [
                        s.account_name,
                        s.region,
                        s.stream_name,
                        s.stream_mode,
                        s.shard_count,
                        f"{s.retention_hours}h",
                        s.stream_status,
                        f"{s.incoming_records:,.0f}",
                        f"{s.incoming_bytes / (1024 * 1024):,.2f} MB",
                        s.consumer_count,
                        f"${s.estimated_monthly_cost:.2f}",
                        f.status.value,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_glue_sheet(wb: Workbook, results) -> None:
    """Glue 작업 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Job Name", width=40, style="data"),
        ColumnDef(header="Type", width=15, style="center"),
        ColumnDef(header="Glue Version", width=12, style="data"),
        ColumnDef(header="Max DPU", width=10, style="data"),
        ColumnDef(header="Workers", width=12, style="data"),
        ColumnDef(header="Last Run", width=15, style="data"),
        ColumnDef(header="Last Status", width=12, style="center"),
        ColumnDef(header="Runs (30d)", width=12, style="number"),
        ColumnDef(header="Runs (90d)", width=12, style="number"),
        ColumnDef(header="분석상태", width=12, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("Glue", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                j = f.job
                last_run_str = j.last_run_time.strftime("%Y-%m-%d") if j.last_run_time else "-"
                workers_str = f"{j.worker_type} x {j.num_workers}" if j.worker_type else "-"
                sheet.add_row(
                    [
                        j.account_name,
                        j.region,
                        j.job_name,
                        j.job_type,
                        j.glue_version or "-",
                        f"{j.max_capacity:.1f}",
                        workers_str,
                        last_run_str,
                        j.last_run_status or "-",
                        j.run_count_30d,
                        j.run_count_90d,
                        f.status.value,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_transfer_sheet(wb: Workbook, results) -> None:
    """Transfer Family 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Server ID", width=25, style="data"),
        ColumnDef(header="Protocols", width=15, style="data"),
        ColumnDef(header="Endpoint", width=15, style="data"),
        ColumnDef(header="State", width=12, style="center"),
        ColumnDef(header="Users", width=8, style="number"),
        ColumnDef(header="Files In", width=12, style="number"),
        ColumnDef(header="Files Out", width=12, style="number"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("Transfer Family", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                s = f.server
                sheet.add_row(
                    [
                        s.account_name,
                        s.region,
                        s.server_id,
                        ", ".join(s.protocols),
                        s.endpoint_type,
                        s.state,
                        s.user_count,
                        int(s.files_in),
                        int(s.files_out),
                        f.status.value,
                        f"${s.estimated_monthly_cost:.2f}",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )
