"""미사용 리소스 리포트 시트 생성 함수"""

from __future__ import annotations

from core.shared.io.excel import ColumnDef, Styles, Workbook


def _create_ami_sheet(wb: Workbook, results) -> None:
    """미사용 AMI 상세 시트를 생성한다."""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="AMI ID", width=25, style="data"),
        ColumnDef(header="Name", width=30, style="data"),
        ColumnDef(header="Size (GB)", width=12, style="number"),
        ColumnDef(header="Age (days)", width=12, style="number"),
        ColumnDef(header="Monthly Cost", width=15, style="data"),
        ColumnDef(header="Recommendation", width=40, style="data"),
    ]
    sheet = wb.new_sheet("AMI", columns=columns)

    for r in results:
        for f in r.findings:
            if f.usage_status.value == "unused":
                sheet.add_row(
                    [
                        f.ami.account_name,
                        f.ami.region,
                        f.ami.id,
                        f.ami.name,
                        f.ami.total_size_gb,
                        f.ami.age_days,
                        round(f.ami.monthly_cost, 2),
                        f.recommendation,
                    ],
                    style=Styles.danger(),
                )


def _create_ebs_sheet(wb: Workbook, results) -> None:
    """미사용 EBS 볼륨 상세 시트를 생성한다."""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Volume ID", width=25, style="data"),
        ColumnDef(header="Name", width=25, style="data"),
        ColumnDef(header="Type", width=10, style="center"),
        ColumnDef(header="Size (GB)", width=12, style="number"),
        ColumnDef(header="Monthly Cost", width=15, style="data"),
        ColumnDef(header="Recommendation", width=40, style="data"),
    ]
    sheet = wb.new_sheet("EBS", columns=columns)

    for r in results:
        for f in r.findings:
            if f.usage_status.value in ("unused", "pending"):
                sheet.add_row(
                    [
                        f.volume.account_name,
                        f.volume.region,
                        f.volume.id,
                        f.volume.name,
                        f.volume.volume_type,
                        f.volume.size_gb,
                        round(f.volume.monthly_cost, 2),
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.usage_status.value == "unused" else Styles.warning(),
                )


def _create_snap_sheet(wb: Workbook, results) -> None:
    """미사용 EBS Snapshot 상세 시트를 생성한다."""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Snapshot ID", width=25, style="data"),
        ColumnDef(header="Name", width=25, style="data"),
        ColumnDef(header="Usage", width=12, style="center"),
        ColumnDef(header="Size (GB)", width=12, style="number"),
        ColumnDef(header="Age (days)", width=12, style="number"),
        ColumnDef(header="Monthly Cost", width=15, style="data"),
        ColumnDef(header="Recommendation", width=40, style="data"),
    ]
    sheet = wb.new_sheet("EBS Snapshot", columns=columns)

    for r in results:
        for f in r.findings:
            if f.usage_status.value in ("orphan", "old"):
                sheet.add_row(
                    [
                        f.snapshot.account_name,
                        f.snapshot.region,
                        f.snapshot.id,
                        f.snapshot.name,
                        f.usage_status.value,
                        f.snapshot.volume_size_gb,
                        f.snapshot.age_days,
                        round(f.snapshot.monthly_cost, 2),
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.usage_status.value == "orphan" else Styles.warning(),
                )


def _create_eip_sheet(wb: Workbook, results) -> None:
    """미사용 Elastic IP 상세 시트를 생성한다."""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Allocation ID", width=30, style="data"),
        ColumnDef(header="Public IP", width=18, style="data"),
        ColumnDef(header="Name", width=25, style="data"),
        ColumnDef(header="Monthly Cost", width=15, style="data"),
        ColumnDef(header="Recommendation", width=40, style="data"),
    ]
    sheet = wb.new_sheet("EIP", columns=columns)

    for r in results:
        for f in r.findings:
            if f.usage_status.value == "unused":
                sheet.add_row(
                    [
                        f.eip.account_name,
                        f.eip.region,
                        f.eip.allocation_id,
                        f.eip.public_ip,
                        f.eip.name,
                        round(f.eip.monthly_cost, 2),
                        f.recommendation,
                    ],
                    style=Styles.danger(),
                )


def _create_ec2_instance_sheet(wb: Workbook, results) -> None:
    """EC2 Instance 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Instance ID", width=22, style="data"),
        ColumnDef(header="Name", width=25, style="data"),
        ColumnDef(header="Type", width=15, style="data"),
        ColumnDef(header="State", width=12, style="center"),
        ColumnDef(header="Platform", width=12, style="data"),
        ColumnDef(header="Avg CPU", width=10, style="data"),
        ColumnDef(header="Max CPU", width=10, style="data"),
        ColumnDef(header="Network In", width=12, style="data"),
        ColumnDef(header="Network Out", width=12, style="data"),
        ColumnDef(header="Age (days)", width=10, style="number"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("EC2 Instance", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                i = f.instance
                sheet.add_row(
                    [
                        i.account_name,
                        i.region,
                        i.instance_id,
                        i.name,
                        i.instance_type,
                        i.state,
                        i.platform,
                        f"{i.avg_cpu:.1f}%",
                        f"{i.max_cpu:.1f}%",
                        f"{i.total_network_in / (1024 * 1024):.2f} MB",
                        f"{i.total_network_out / (1024 * 1024):.2f} MB",
                        i.age_days,
                        f"${i.estimated_monthly_cost:.2f}",
                        f.status.value,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_elb_sheet(wb: Workbook, results) -> None:
    """미사용/비정상 ELB 상세 시트를 생성한다."""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Name", width=30, style="data"),
        ColumnDef(header="Type", width=10, style="center"),
        ColumnDef(header="Usage", width=12, style="center"),
        ColumnDef(header="Targets", width=10, style="number"),
        ColumnDef(header="Healthy", width=10, style="number"),
        ColumnDef(header="Monthly Cost", width=15, style="data"),
        ColumnDef(header="Recommendation", width=40, style="data"),
    ]
    sheet = wb.new_sheet("ELB", columns=columns)

    for r in results:
        for f in r.findings:
            if f.usage_status.value in ("unused", "unhealthy"):
                sheet.add_row(
                    [
                        f.lb.account_name,
                        f.lb.region,
                        f.lb.name,
                        f.lb.lb_type.upper(),
                        f.usage_status.value,
                        f.lb.total_targets,
                        f.lb.healthy_targets,
                        round(f.lb.monthly_cost, 2),
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.usage_status.value == "unused" else Styles.warning(),
                )


def _create_tg_sheet(wb: Workbook, results) -> None:
    """미사용 Target Group 상세 시트를 생성한다."""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Name", width=30, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="Type", width=12, style="center"),
        ColumnDef(header="Protocol", width=10, style="center"),
        ColumnDef(header="Port", width=8, style="number"),
        ColumnDef(header="LB 연결", width=10, style="number"),
        ColumnDef(header="Total Targets", width=12, style="number"),
        ColumnDef(header="Healthy", width=10, style="number"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("Target Group", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                tg = f.tg
                sheet.add_row(
                    [
                        tg.account_name,
                        tg.region,
                        tg.name,
                        f.status.value,
                        tg.target_type,
                        tg.protocol or "-",
                        tg.port or "-",
                        len(tg.load_balancer_arns),
                        tg.total_targets,
                        tg.healthy_targets,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_lambda_sheet(wb: Workbook, results) -> None:
    """미사용/비정상 Lambda 함수 상세 시트를 생성한다."""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Function Name", width=40, style="data"),
        ColumnDef(header="Runtime", width=15, style="data"),
        ColumnDef(header="Memory (MB)", width=12, style="number"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="월간 낭비", width=12, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("Lambda", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                fn = f.function
                sheet.add_row(
                    [
                        fn.account_name,
                        fn.region,
                        fn.function_name,
                        fn.runtime,
                        fn.memory_mb,
                        f.status.value,
                        f"${f.monthly_waste:.2f}" if f.monthly_waste > 0 else "-",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )
