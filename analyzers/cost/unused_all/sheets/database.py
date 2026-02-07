"""미사용 리소스 리포트 시트 생성 함수"""

from __future__ import annotations

from shared.io.excel import ColumnDef, Styles, Workbook


def _create_dynamodb_sheet(wb: Workbook, results) -> None:
    """DynamoDB 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Table Name", width=30, style="data"),
        ColumnDef(header="Billing Mode", width=15, style="center"),
        ColumnDef(header="Items", width=12, style="number"),
        ColumnDef(header="Size (MB)", width=12, style="data"),
        ColumnDef(header="RCU", width=8, style="number"),
        ColumnDef(header="WCU", width=8, style="number"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("DynamoDB", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                t = f.table
                sheet.add_row(
                    [
                        t.account_name,
                        t.region,
                        t.table_name,
                        t.billing_mode,
                        t.item_count,
                        f"{t.size_mb:.2f}",
                        t.provisioned_read,
                        t.provisioned_write,
                        f.status.value,
                        f"${t.estimated_monthly_cost:.2f}",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_elasticache_sheet(wb: Workbook, results) -> None:
    """ElastiCache 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Cluster ID", width=30, style="data"),
        ColumnDef(header="Engine", width=12, style="data"),
        ColumnDef(header="Node Type", width=18, style="data"),
        ColumnDef(header="Nodes", width=8, style="number"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="Avg Conn", width=10, style="data"),
        ColumnDef(header="Avg CPU", width=10, style="data"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("ElastiCache", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                c = f.cluster
                sheet.add_row(
                    [
                        c.account_name,
                        c.region,
                        c.cluster_id,
                        c.engine,
                        c.node_type,
                        c.num_nodes,
                        f.status.value,
                        f"{c.avg_connections:.1f}",
                        f"{c.avg_cpu:.1f}%",
                        f"${c.estimated_monthly_cost:.2f}",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_redshift_sheet(wb: Workbook, results) -> None:
    """Redshift 클러스터 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Cluster ID", width=30, style="data"),
        ColumnDef(header="Node Type", width=15, style="data"),
        ColumnDef(header="Nodes", width=8, style="number"),
        ColumnDef(header="Status", width=12, style="center"),
        ColumnDef(header="Avg Conn", width=10, style="data"),
        ColumnDef(header="Avg CPU", width=10, style="data"),
        ColumnDef(header="Avg IOPS", width=10, style="data"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="분석상태", width=12, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("Redshift", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                c = f.cluster
                sheet.add_row(
                    [
                        c.account_name,
                        c.region,
                        c.cluster_id,
                        c.node_type,
                        c.num_nodes,
                        c.status,
                        f"{c.avg_connections:.1f}",
                        f"{c.avg_cpu:.1f}%",
                        f"{c.avg_read_iops + c.avg_write_iops:.1f}",
                        f"${c.estimated_monthly_cost:.2f}",
                        f.status.value,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_opensearch_sheet(wb: Workbook, results) -> None:
    """OpenSearch 도메인 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Domain Name", width=30, style="data"),
        ColumnDef(header="Instance Type", width=18, style="data"),
        ColumnDef(header="Instances", width=10, style="number"),
        ColumnDef(header="Storage (GB)", width=12, style="data"),
        ColumnDef(header="Engine", width=15, style="data"),
        ColumnDef(header="Avg CPU", width=10, style="data"),
        ColumnDef(header="Docs", width=12, style="data"),
        ColumnDef(header="Index Rate", width=12, style="data"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="분석상태", width=12, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("OpenSearch", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                d = f.domain
                sheet.add_row(
                    [
                        d.account_name,
                        d.region,
                        d.domain_name,
                        d.instance_type,
                        d.instance_count,
                        f"{d.storage_gb:.0f}",
                        d.engine_version,
                        f"{d.avg_cpu:.1f}%",
                        f"{d.searchable_docs:,.0f}",
                        f"{d.indexing_rate:.2f}/min",
                        f"${d.estimated_monthly_cost:.2f}",
                        f.status.value,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_rds_instance_sheet(wb: Workbook, results) -> None:
    """RDS Instance 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Instance ID", width=30, style="data"),
        ColumnDef(header="Engine", width=15, style="data"),
        ColumnDef(header="Class", width=18, style="data"),
        ColumnDef(header="Storage", width=12, style="data"),
        ColumnDef(header="Multi-AZ", width=10, style="center"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="Avg Conn", width=10, style="data"),
        ColumnDef(header="Avg CPU", width=10, style="data"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("RDS Instance", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                inst = f.instance
                sheet.add_row(
                    [
                        inst.account_name,
                        inst.region,
                        inst.db_instance_id,
                        inst.engine,
                        inst.db_instance_class,
                        f"{inst.allocated_storage} GB",
                        "Yes" if inst.multi_az else "No",
                        f.status.value,
                        f"{inst.avg_connections:.1f}",
                        f"{inst.avg_cpu:.1f}%",
                        f"${inst.estimated_monthly_cost:.2f}",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_rds_snap_sheet(wb: Workbook, results) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Snapshot ID", width=30, style="data"),
        ColumnDef(header="DB Identifier", width=25, style="data"),
        ColumnDef(header="Type", width=10, style="center"),
        ColumnDef(header="Engine", width=15, style="data"),
        ColumnDef(header="Size (GB)", width=12, style="number"),
        ColumnDef(header="Age (days)", width=12, style="number"),
        ColumnDef(header="Monthly Cost", width=15, style="data"),
        ColumnDef(header="Recommendation", width=40, style="data"),
    ]
    sheet = wb.new_sheet("RDS Snapshot", columns=columns)

    for r in results:
        for f in r.findings:
            if f.usage_status.value == "old":
                sheet.add_row(
                    [
                        f.snapshot.account_name,
                        f.snapshot.region,
                        f.snapshot.id,
                        f.snapshot.db_identifier,
                        f.snapshot.snapshot_type.value.upper(),
                        f.snapshot.engine,
                        f.snapshot.allocated_storage_gb,
                        f.snapshot.age_days,
                        round(f.snapshot.monthly_cost, 2),
                        f.recommendation,
                    ],
                    style=Styles.warning(),
                )
