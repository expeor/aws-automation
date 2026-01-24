"""
plugins/cost/unused_all/report.py - Excel 보고서 생성

미사용 리소스 종합 분석 Excel 보고서 생성
"""

from __future__ import annotations

from datetime import datetime

from core.tools.io.excel import ColumnDef, Styles, Workbook

from .types import UnusedAllResult


def generate_report(result: UnusedAllResult, output_dir: str) -> str:
    """종합 Excel 보고서 생성"""
    wb = Workbook()

    # ===== Summary =====
    summary = wb.new_summary_sheet("Summary")
    summary.add_title("미사용 리소스 종합 보고서")
    summary.add_item("생성", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 카테고리별 리소스 목록
    resources = [
        # Compute (EC2)
        ("AMI", "ami_total", "ami_unused", "ami_monthly_waste"),
        ("EBS", "ebs_total", "ebs_unused", "ebs_monthly_waste"),
        ("EBS Snapshot", "snap_total", "snap_unused", "snap_monthly_waste"),
        ("EIP", "eip_total", "eip_unused", "eip_monthly_waste"),
        ("ENI", "eni_total", "eni_unused", None),
        ("EC2 Instance", "ec2_instance_total", "ec2_instance_unused", "ec2_instance_monthly_waste"),
        # Networking (VPC)
        ("NAT Gateway", "nat_total", "nat_unused", "nat_monthly_waste"),
        ("VPC Endpoint", "endpoint_total", "endpoint_unused", "endpoint_monthly_waste"),
        # Load Balancing
        ("ELB", "elb_total", "elb_unused", "elb_monthly_waste"),
        ("Target Group", "tg_total", "tg_unused", None),
        # Database
        ("DynamoDB", "dynamodb_total", "dynamodb_unused", "dynamodb_monthly_waste"),
        ("ElastiCache", "elasticache_total", "elasticache_unused", "elasticache_monthly_waste"),
        ("RDS Instance", "rds_instance_total", "rds_instance_unused", "rds_instance_monthly_waste"),
        ("RDS Snapshot", "rds_snap_total", "rds_snap_unused", "rds_snap_monthly_waste"),
        # Storage
        ("ECR", "ecr_total", "ecr_unused", "ecr_monthly_waste"),
        ("EFS", "efs_total", "efs_unused", "efs_monthly_waste"),
        ("S3", "s3_total", "s3_unused", None),
        # Serverless
        ("API Gateway", "apigateway_total", "apigateway_unused", None),
        ("EventBridge", "eventbridge_total", "eventbridge_unused", None),
        ("Lambda", "lambda_total", "lambda_unused", "lambda_monthly_waste"),
        # ML
        (
            "SageMaker Endpoint",
            "sagemaker_endpoint_total",
            "sagemaker_endpoint_unused",
            "sagemaker_endpoint_monthly_waste",
        ),
        # Messaging
        ("SNS", "sns_total", "sns_unused", None),
        ("SQS", "sqs_total", "sqs_unused", None),
        # Security
        ("ACM", "acm_total", "acm_unused", None),
        ("KMS", "kms_total", "kms_unused", "kms_monthly_waste"),
        ("Secrets Manager", "secret_total", "secret_unused", "secret_monthly_waste"),
        # Monitoring
        ("CloudWatch Alarm", "cw_alarm_total", "cw_alarm_unused", None),
        ("Log Group", "loggroup_total", "loggroup_unused", "loggroup_monthly_waste"),
        # DNS (Global)
        ("Route53", "route53_total", "route53_unused", "route53_monthly_waste"),
    ]

    summary.add_blank_row()
    summary.add_section("리소스 현황")

    for name, total_attr, unused_attr, waste_attr in resources:
        total = sum(getattr(s, total_attr, 0) for s in result.summaries)
        unused = sum(getattr(s, unused_attr, 0) for s in result.summaries)
        waste = sum(getattr(s, waste_attr, 0) for s in result.summaries) if waste_attr else 0

        value_str = f"전체: {total}, 미사용: {unused}"
        if waste > 0:
            value_str += f", 월간 낭비: ${waste:,.2f}"

        highlight = "danger" if unused > 0 else None
        summary.add_item(name, value_str, highlight=highlight)

    # 총 절감
    total_waste = sum(
        s.nat_monthly_waste
        + s.ebs_monthly_waste
        + s.eip_monthly_waste
        + s.elb_monthly_waste
        + s.snap_monthly_waste
        + s.ami_monthly_waste
        + s.rds_snap_monthly_waste
        + s.loggroup_monthly_waste
        + s.endpoint_monthly_waste
        + s.secret_monthly_waste
        + s.kms_monthly_waste
        + s.ecr_monthly_waste
        + s.route53_monthly_waste
        + s.lambda_monthly_waste
        + s.elasticache_monthly_waste
        + s.rds_instance_monthly_waste
        + s.efs_monthly_waste
        + s.dynamodb_monthly_waste
        + s.ec2_instance_monthly_waste
        + s.sagemaker_endpoint_monthly_waste
        for s in result.summaries
    )

    summary.add_blank_row()
    summary.add_item("총 월간 절감 가능", f"${total_waste:,.2f}", highlight="danger")

    # ===== 상세 시트들 (카테고리별 정렬) =====
    # Compute (EC2)
    _create_ami_sheet(wb, result.ami_results)
    _create_ebs_sheet(wb, result.ebs_results)
    _create_snap_sheet(wb, result.snap_results)
    _create_eip_sheet(wb, result.eip_results)
    _create_eni_sheet(wb, result.eni_results)
    _create_ec2_instance_sheet(wb, result.ec2_instance_results)
    # Networking (VPC)
    _create_nat_sheet(wb, result.nat_findings)
    _create_endpoint_sheet(wb, result.endpoint_results)
    # Load Balancing
    _create_elb_sheet(wb, result.elb_results)
    _create_tg_sheet(wb, result.tg_results)
    # Database
    _create_dynamodb_sheet(wb, result.dynamodb_results)
    _create_elasticache_sheet(wb, result.elasticache_results)
    _create_rds_instance_sheet(wb, result.rds_instance_results)
    _create_rds_snap_sheet(wb, result.rds_snap_results)
    # Storage
    _create_ecr_sheet(wb, result.ecr_results)
    _create_efs_sheet(wb, result.efs_results)
    _create_s3_sheet(wb, result.s3_results)
    # Serverless
    _create_apigateway_sheet(wb, result.apigateway_results)
    _create_eventbridge_sheet(wb, result.eventbridge_results)
    _create_lambda_sheet(wb, result.lambda_results)
    # ML
    _create_sagemaker_endpoint_sheet(wb, result.sagemaker_endpoint_results)
    # Messaging
    _create_sns_sheet(wb, result.sns_results)
    _create_sqs_sheet(wb, result.sqs_results)
    # Security
    _create_acm_sheet(wb, result.acm_results)
    _create_kms_sheet(wb, result.kms_results)
    _create_secret_sheet(wb, result.secret_results)
    # Monitoring
    _create_cw_alarm_sheet(wb, result.cw_alarm_results)
    _create_loggroup_sheet(wb, result.loggroup_results)
    # DNS (Global)
    _create_route53_sheet(wb, result.route53_results)

    return str(wb.save_as(output_dir, "Unused_Resources"))


# =============================================================================
# 개별 시트 생성 함수들
# =============================================================================


def _create_nat_sheet(wb: Workbook, findings) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="NAT ID", width=25, style="data"),
        ColumnDef(header="Name", width=25, style="data"),
        ColumnDef(header="Usage", width=12, style="center"),
        ColumnDef(header="Monthly Waste", width=15, style="data"),
        ColumnDef(header="Recommendation", width=40, style="data"),
    ]
    sheet = wb.new_sheet("NAT Gateway", columns=columns)

    for nat_result in findings:
        for f in nat_result.findings:
            if f.usage_status.value in ("unused", "low_usage"):
                sheet.add_row(
                    [
                        f.nat.account_name,
                        f.nat.region,
                        f.nat.nat_gateway_id,
                        f.nat.name,
                        f.usage_status.value,
                        f"${f.monthly_waste:,.2f}",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.usage_status.value == "unused" else Styles.warning(),
                )


def _create_eni_sheet(wb: Workbook, results) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="ENI ID", width=25, style="data"),
        ColumnDef(header="Name", width=25, style="data"),
        ColumnDef(header="Usage", width=12, style="center"),
        ColumnDef(header="Type", width=15, style="data"),
        ColumnDef(header="Recommendation", width=40, style="data"),
    ]
    sheet = wb.new_sheet("ENI", columns=columns)

    for r in results:
        for f in r.findings:
            if f.usage_status.value in ("unused", "pending"):
                sheet.add_row(
                    [
                        f.eni.account_name,
                        f.eni.region,
                        f.eni.id,
                        f.eni.name,
                        f.usage_status.value,
                        f.eni.interface_type,
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.usage_status.value == "unused" else Styles.warning(),
                )


def _create_ebs_sheet(wb: Workbook, results) -> None:
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


def _create_eip_sheet(wb: Workbook, results) -> None:
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


def _create_elb_sheet(wb: Workbook, results) -> None:
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


def _create_snap_sheet(wb: Workbook, results) -> None:
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


def _create_ami_sheet(wb: Workbook, results) -> None:
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


def _create_tg_sheet(wb: Workbook, results) -> None:
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


def _create_endpoint_sheet(wb: Workbook, results) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Endpoint ID", width=25, style="data"),
        ColumnDef(header="Type", width=12, style="center"),
        ColumnDef(header="Service", width=20, style="data"),
        ColumnDef(header="VPC", width=20, style="data"),
        ColumnDef(header="State", width=12, style="center"),
        ColumnDef(header="월간 비용", width=12, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("VPC Endpoint", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                ep = f.endpoint
                sheet.add_row(
                    [
                        ep.account_name,
                        ep.region,
                        ep.endpoint_id,
                        ep.endpoint_type,
                        ep.service_name.split(".")[-1],
                        ep.vpc_id,
                        ep.state,
                        round(ep.monthly_cost, 2),
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


def _create_ecr_sheet(wb: Workbook, results) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Repository", width=40, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="이미지 수", width=10, style="number"),
        ColumnDef(header="오래된 이미지", width=12, style="number"),
        ColumnDef(header="총 크기", width=12, style="data"),
        ColumnDef(header="낭비 비용", width=12, style="data"),
        ColumnDef(header="Lifecycle", width=10, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("ECR", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                repo = f.repo
                sheet.add_row(
                    [
                        repo.account_name,
                        repo.region,
                        repo.name,
                        f.status.value,
                        repo.image_count,
                        repo.old_image_count,
                        f"{repo.total_size_gb:.2f} GB",
                        f"${repo.old_images_monthly_cost:.2f}",
                        "있음" if repo.has_lifecycle_policy else "없음",
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


def _create_s3_sheet(wb: Workbook, results) -> None:
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Bucket", width=40, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="객체 수", width=12, style="number"),
        ColumnDef(header="크기", width=15, style="data"),
        ColumnDef(header="버전관리", width=10, style="center"),
        ColumnDef(header="Lifecycle", width=10, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("S3", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                bucket = f.bucket
                sheet.add_row(
                    [
                        bucket.account_name,
                        bucket.name,
                        bucket.region,
                        f.status.value,
                        bucket.object_count,
                        f"{bucket.total_size_mb:.2f} MB",
                        "Enabled" if bucket.versioning_enabled else "Disabled",
                        "있음" if bucket.has_lifecycle else "없음",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_lambda_sheet(wb: Workbook, results) -> None:
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


def _create_efs_sheet(wb: Workbook, results) -> None:
    """EFS 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="ID", width=25, style="data"),
        ColumnDef(header="Name", width=25, style="data"),
        ColumnDef(header="Size", width=12, style="data"),
        ColumnDef(header="Mount Targets", width=12, style="number"),
        ColumnDef(header="Mode", width=15, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="Avg Conn", width=10, style="data"),
        ColumnDef(header="Total I/O", width=12, style="data"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("EFS", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                fs = f.efs
                sheet.add_row(
                    [
                        fs.account_name,
                        fs.region,
                        fs.file_system_id,
                        fs.name or "-",
                        f"{fs.size_gb:.2f} GB",
                        fs.mount_target_count,
                        fs.throughput_mode,
                        f.status.value,
                        f"{fs.avg_client_connections:.1f}",
                        f"{fs.total_io_bytes / (1024**2):.1f} MB",
                        f"${fs.estimated_monthly_cost:.2f}",
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
