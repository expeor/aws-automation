"""
plugins/cost/unused_all/report.py - Excel 보고서 생성

미사용 리소스 종합 분석 Excel 보고서 생성
"""

from __future__ import annotations

from datetime import datetime

from core.shared.io.excel import Workbook

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
        ("Redshift", "redshift_total", "redshift_unused", "redshift_monthly_waste"),
        ("OpenSearch", "opensearch_total", "opensearch_unused", "opensearch_monthly_waste"),
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
        # Analytics
        ("Kinesis Stream", "kinesis_total", "kinesis_unused", "kinesis_monthly_waste"),
        ("Glue Job", "glue_total", "glue_unused", None),
        # Security (VPC)
        ("Security Group", "sg_total", "sg_unused", None),
        # File Transfer
        ("Transfer Family", "transfer_total", "transfer_unused", "transfer_monthly_waste"),
        ("FSx", "fsx_total", "fsx_unused", "fsx_monthly_waste"),
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
        + s.redshift_monthly_waste
        + s.opensearch_monthly_waste
        + s.rds_instance_monthly_waste
        + s.efs_monthly_waste
        + s.dynamodb_monthly_waste
        + s.ec2_instance_monthly_waste
        + s.sagemaker_endpoint_monthly_waste
        + s.kinesis_monthly_waste
        + s.transfer_monthly_waste
        + s.fsx_monthly_waste
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
    _create_redshift_sheet(wb, result.redshift_results)
    _create_opensearch_sheet(wb, result.opensearch_results)
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
    # Analytics
    _create_kinesis_sheet(wb, result.kinesis_results)
    _create_glue_sheet(wb, result.glue_results)
    # Security (VPC)
    _create_security_group_sheet(wb, result.sg_results)
    # File Transfer
    _create_transfer_sheet(wb, result.transfer_results)
    _create_fsx_sheet(wb, result.fsx_results)

    return str(wb.save_as(output_dir, "Unused_Resources"))


# =============================================================================
# 개별 시트 생성 함수들
# =============================================================================


from .sheets.compute import (
    _create_ami_sheet,
    _create_ebs_sheet,
    _create_ec2_instance_sheet,
    _create_eip_sheet,
    _create_elb_sheet,
    _create_lambda_sheet,
    _create_snap_sheet,
    _create_tg_sheet,
)
from .sheets.database import (
    _create_dynamodb_sheet,
    _create_elasticache_sheet,
    _create_opensearch_sheet,
    _create_rds_instance_sheet,
    _create_rds_snap_sheet,
    _create_redshift_sheet,
)
from .sheets.other import (
    _create_acm_sheet,
    _create_apigateway_sheet,
    _create_cw_alarm_sheet,
    _create_eventbridge_sheet,
    _create_glue_sheet,
    _create_kinesis_sheet,
    _create_kms_sheet,
    _create_loggroup_sheet,
    _create_route53_sheet,
    _create_sagemaker_endpoint_sheet,
    _create_secret_sheet,
    _create_sns_sheet,
    _create_sqs_sheet,
    _create_transfer_sheet,
)
from .sheets.storage import _create_ecr_sheet, _create_efs_sheet, _create_fsx_sheet, _create_s3_sheet
from .sheets.vpc import _create_endpoint_sheet, _create_eni_sheet, _create_nat_sheet, _create_security_group_sheet
