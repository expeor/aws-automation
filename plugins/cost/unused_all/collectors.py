"""
plugins/cost/unused_all/collectors.py - 개별 리소스 수집/분석 함수

각 AWS 리소스 타입별 수집 및 분석 함수 정의
"""

from __future__ import annotations

from typing import Any, Callable, Dict

# 각 도구에서 수집/분석 함수 import
from plugins.cloudwatch.loggroup_audit import (
    analyze_log_groups,
    collect_log_groups,
)
from plugins.cloudwatch.alarm_orphan import (
    analyze_alarms as analyze_cw_alarms,
    collect_alarms as collect_cw_alarms,
)
from plugins.ec2.ami_audit import (
    analyze_amis,
    collect_amis,
    get_used_ami_ids,
)
from plugins.ec2.ebs_audit import analyze_ebs, collect_ebs
from plugins.ec2.eip_audit import analyze_eips, collect_eips
from plugins.ec2.snapshot_audit import (
    analyze_snapshots,
    collect_snapshots,
    get_ami_snapshot_mapping,
)
from plugins.ecr.unused import analyze_ecr_repos, collect_ecr_repos
from plugins.elb.target_group_audit import (
    analyze_target_groups,
    collect_target_groups,
)
from plugins.elb.unused import (
    analyze_load_balancers,
    collect_classic_load_balancers,
    collect_v2_load_balancers,
)
from plugins.fn.common.collector import collect_functions_with_metrics
from plugins.fn.unused import analyze_functions as analyze_lambda_functions
from plugins.kms.unused import analyze_kms_keys, collect_kms_keys
from plugins.rds.snapshot_audit import (
    analyze_rds_snapshots,
    collect_rds_snapshots,
)
from plugins.route53.empty_zone import (
    analyze_hosted_zones,
    collect_hosted_zones,
)
from plugins.s3.empty_bucket import analyze_buckets, collect_buckets
from plugins.secretsmanager.unused import (
    analyze_secrets,
    collect_secrets,
)
from plugins.vpc.endpoint_audit import (
    analyze_endpoints,
    collect_endpoints,
)
from plugins.vpc.eni_audit import analyze_enis, collect_enis
from plugins.vpc.nat_audit_analysis import NATAnalyzer, NATCollector

# 신규 추가된 미사용 리소스 분석 모듈
from plugins.elasticache.unused import (
    analyze_clusters as analyze_elasticache_clusters,
    collect_elasticache_clusters,
)
from plugins.rds.unused import (
    analyze_instances as analyze_rds_instances,
    collect_rds_instances,
)
from plugins.efs.unused import (
    analyze_filesystems as analyze_efs_filesystems,
    collect_efs_filesystems,
)
from plugins.sqs.unused import (
    analyze_queues as analyze_sqs_queues,
    collect_sqs_queues,
)
from plugins.sns.unused import (
    analyze_topics as analyze_sns_topics,
    collect_sns_topics,
)
from plugins.acm.unused import (
    analyze_certificates as analyze_acm_certificates,
    collect_certificates as collect_acm_certificates,
)
from plugins.apigateway.unused import (
    analyze_apis as analyze_apigateway_apis,
    collect_apis as collect_apigateway_apis,
)
from plugins.eventbridge.unused import (
    analyze_rules as analyze_eventbridge_rules,
    collect_rules as collect_eventbridge_rules,
)
from plugins.dynamodb.unused import (
    analyze_tables as analyze_dynamodb_tables,
    collect_dynamodb_tables,
)
from plugins.codecommit.unused import (
    analyze_repos as analyze_codecommit_repos,
    collect_repos as collect_codecommit_repos,
)


# =============================================================================
# 개별 리소스 수집/분석 함수 (병렬 실행용)
# =============================================================================


def collect_nat(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """NAT Gateway 수집 및 분석"""
    try:
        collector = NATCollector()
        nat_data = collector.collect(session, account_id, account_name, region)
        if not nat_data.nat_gateways:
            return {"total": 0, "unused": 0, "waste": 0.0, "findings": []}

        analyzer = NATAnalyzer(nat_data)
        nat_result = analyzer.analyze()
        stats = analyzer.get_summary_stats()

        return {
            "total": stats.get("total_nat_count", 0),
            "unused": stats.get("unused_count", 0) + stats.get("low_usage_count", 0),
            "waste": stats.get("total_monthly_waste", 0),
            "findings": [nat_result],
        }
    except Exception as e:
        return {"error": f"NAT Gateway: {e}"}


def collect_eni(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """ENI 수집 및 분석"""
    try:
        enis = collect_enis(session, account_id, account_name, region)
        if not enis:
            return {"total": 0, "unused": 0, "result": None}

        result = analyze_enis(enis, account_id, account_name, region)
        return {
            "total": result.total_count,
            "unused": result.unused_count,
            "result": result,
        }
    except Exception as e:
        return {"error": f"ENI: {e}"}


def collect_ebs_volumes(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """EBS 수집 및 분석"""
    try:
        volumes = collect_ebs(session, account_id, account_name, region)
        if not volumes:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_ebs(volumes, account_id, account_name, region)
        return {
            "total": result.total_count,
            "unused": result.unused_count,
            "waste": result.unused_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"EBS: {e}"}


def collect_eip_addresses(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """EIP 수집 및 분석"""
    try:
        eips = collect_eips(session, account_id, account_name, region)
        if not eips:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_eips(eips, account_id, account_name, region)
        return {
            "total": result.total_count,
            "unused": result.unused_count,
            "waste": result.unused_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"EIP: {e}"}


def collect_elb(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """ELB 수집 및 분석"""
    try:
        v2_lbs = collect_v2_load_balancers(session, account_id, account_name, region)
        classic_lbs = collect_classic_load_balancers(
            session, account_id, account_name, region
        )
        all_lbs = v2_lbs + classic_lbs
        if not all_lbs:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_load_balancers(all_lbs, account_id, account_name, region)
        return {
            "total": result.total_count,
            "unused": result.unused_count + result.unhealthy_count,
            "waste": result.unused_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"ELB: {e}"}


def collect_snapshot(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """EBS Snapshot 수집 및 분석"""
    try:
        snapshots = collect_snapshots(session, account_id, account_name, region)
        if not snapshots:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        ami_mapping = get_ami_snapshot_mapping(session, region)
        result = analyze_snapshots(
            snapshots, ami_mapping, account_id, account_name, region
        )
        return {
            "total": result.total_count,
            "unused": result.orphan_count + result.old_count,
            "waste": result.orphan_monthly_cost + result.old_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"EBS Snapshot: {e}"}


def collect_ami(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """AMI 수집 및 분석"""
    try:
        amis = collect_amis(session, account_id, account_name, region)
        if not amis:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        used_ami_ids = get_used_ami_ids(session, region)
        result = analyze_amis(amis, used_ami_ids, account_id, account_name, region)
        return {
            "total": result.total_count,
            "unused": result.unused_count,
            "waste": result.unused_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"AMI: {e}"}


def collect_rds_snapshot(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """RDS Snapshot 수집 및 분석"""
    try:
        rds_snaps = collect_rds_snapshots(session, account_id, account_name, region)
        if not rds_snaps:
            return {"total": 0, "old": 0, "waste": 0.0, "result": None}

        result = analyze_rds_snapshots(rds_snaps, account_id, account_name, region)
        return {
            "total": result.total_count,
            "old": result.old_count,
            "waste": result.old_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"RDS Snapshot: {e}"}


def collect_loggroup(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """CloudWatch Log Group 수집 및 분석"""
    try:
        log_groups = collect_log_groups(session, account_id, account_name, region)
        if not log_groups:
            return {"total": 0, "issue": 0, "waste": 0.0, "result": None}

        result = analyze_log_groups(log_groups, account_id, account_name, region)
        return {
            "total": result.total_count,
            "issue": result.empty_count + result.old_count,
            "waste": result.empty_monthly_cost + result.old_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Log Group: {e}"}


def collect_target_group(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """Target Group 수집 및 분석"""
    try:
        tgs = collect_target_groups(session, account_id, account_name, region)
        if not tgs:
            return {"total": 0, "issue": 0, "result": None}

        result = analyze_target_groups(tgs, account_id, account_name, region)
        return {
            "total": result.total_count,
            "issue": result.unattached_count + result.no_targets_count,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Target Group: {e}"}


def collect_endpoint(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """VPC Endpoint 수집 및 분석"""
    try:
        endpoints = collect_endpoints(session, account_id, account_name, region)
        if not endpoints:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_endpoints(endpoints, session, account_id, account_name, region)
        return {
            "total": result.total_count,
            "unused": result.unused_count,
            "waste": result.unused_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"VPC Endpoint: {e}"}


def collect_secret(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """Secrets Manager 수집 및 분석"""
    try:
        secrets = collect_secrets(session, account_id, account_name, region)
        if not secrets:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_secrets(secrets, account_id, account_name, region)
        return {
            "total": result.total_count,
            "unused": result.unused_count,
            "waste": result.unused_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Secrets Manager: {e}"}


def collect_kms(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """KMS 수집 및 분석"""
    try:
        kms_keys = collect_kms_keys(session, account_id, account_name, region)
        if not kms_keys:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_kms_keys(kms_keys, account_id, account_name, region)
        return {
            "total": result.total_count,
            "unused": result.disabled_count + result.pending_delete_count,
            "waste": result.disabled_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"KMS: {e}"}


def collect_ecr(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """ECR 수집 및 분석"""
    try:
        repos = collect_ecr_repos(session, account_id, account_name, region)
        if not repos:
            return {"total": 0, "issue": 0, "waste": 0.0, "result": None}

        result = analyze_ecr_repos(repos, account_id, account_name, region)
        return {
            "total": result.total_repos,
            "issue": result.empty_repos + result.repos_with_old_images,
            "waste": result.old_images_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"ECR: {e}"}


def collect_lambda(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """Lambda 수집 및 분석"""
    try:
        functions = collect_functions_with_metrics(
            session, account_id, account_name, region
        )
        if not functions:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_lambda_functions(functions, account_id, account_name, region)
        return {
            "total": result.total_count,
            "unused": result.unused_count,
            "waste": result.unused_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Lambda: {e}"}


def collect_elasticache(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """ElastiCache 수집 및 분석"""
    try:
        clusters = collect_elasticache_clusters(
            session, account_id, account_name, region
        )
        if not clusters:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_elasticache_clusters(
            clusters, account_id, account_name, region
        )
        return {
            "total": result.total_clusters,
            "unused": result.unused_clusters + result.low_usage_clusters,
            "waste": result.unused_monthly_cost + result.low_usage_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"ElastiCache: {e}"}


def collect_rds_instance(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """RDS Instance 수집 및 분석"""
    try:
        instances = collect_rds_instances(session, account_id, account_name, region)
        if not instances:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_rds_instances(instances, account_id, account_name, region)
        return {
            "total": result.total_instances,
            "unused": result.unused_instances
            + result.low_usage_instances
            + result.stopped_instances,
            "waste": result.unused_monthly_cost + result.low_usage_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"RDS Instance: {e}"}


def collect_efs(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """EFS 수집 및 분석"""
    try:
        filesystems = collect_efs_filesystems(session, account_id, account_name, region)
        if not filesystems:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_efs_filesystems(filesystems, account_id, account_name, region)
        return {
            "total": result.total_filesystems,
            "unused": result.no_mount_target + result.no_io + result.empty,
            "waste": result.unused_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"EFS: {e}"}


def collect_sqs(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """SQS 수집 및 분석"""
    try:
        queues = collect_sqs_queues(session, account_id, account_name, region)
        if not queues:
            return {"total": 0, "unused": 0, "result": None}

        result = analyze_sqs_queues(queues, account_id, account_name, region)
        return {
            "total": result.total_queues,
            "unused": result.unused_queues + result.empty_dlqs,
            "result": result,
        }
    except Exception as e:
        return {"error": f"SQS: {e}"}


def collect_sns(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """SNS 수집 및 분석"""
    try:
        topics = collect_sns_topics(session, account_id, account_name, region)
        if not topics:
            return {"total": 0, "unused": 0, "result": None}

        result = analyze_sns_topics(topics, account_id, account_name, region)
        return {
            "total": result.total_topics,
            "unused": result.unused_topics + result.no_subscribers + result.no_messages,
            "result": result,
        }
    except Exception as e:
        return {"error": f"SNS: {e}"}


def collect_acm(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """ACM 수집 및 분석"""
    try:
        certs = collect_acm_certificates(session, account_id, account_name, region)
        if not certs:
            return {"total": 0, "unused": 0, "result": None}

        result = analyze_acm_certificates(certs, account_id, account_name, region)
        return {
            "total": result.total_certs,
            "unused": result.unused_certs + result.expired_certs,
            "result": result,
        }
    except Exception as e:
        return {"error": f"ACM: {e}"}


def collect_apigateway(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """API Gateway 수집 및 분석"""
    try:
        apis = collect_apigateway_apis(session, account_id, account_name, region)
        if not apis:
            return {"total": 0, "unused": 0, "result": None}

        result = analyze_apigateway_apis(apis, account_id, account_name, region)
        return {
            "total": result.total_apis,
            "unused": result.unused_apis + result.no_stages + result.low_usage,
            "result": result,
        }
    except Exception as e:
        return {"error": f"API Gateway: {e}"}


def collect_eventbridge(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """EventBridge 수집 및 분석"""
    try:
        rules = collect_eventbridge_rules(session, account_id, account_name, region)
        if not rules:
            return {"total": 0, "unused": 0, "result": None}

        result = analyze_eventbridge_rules(rules, account_id, account_name, region)
        return {
            "total": result.total_rules,
            "unused": result.disabled_rules + result.no_targets + result.unused_rules,
            "result": result,
        }
    except Exception as e:
        return {"error": f"EventBridge: {e}"}


def collect_cw_alarm(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """CloudWatch Alarm 수집 및 분석"""
    try:
        alarms = collect_cw_alarms(session, account_id, account_name, region)
        if not alarms:
            return {"total": 0, "orphan": 0, "result": None}

        result = analyze_cw_alarms(alarms, account_id, account_name, region)
        return {
            "total": result.total_alarms,
            "orphan": result.orphan_alarms + result.no_actions,
            "result": result,
        }
    except Exception as e:
        return {"error": f"CloudWatch Alarm: {e}"}


def collect_dynamodb(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """DynamoDB 수집 및 분석"""
    try:
        tables = collect_dynamodb_tables(session, account_id, account_name, region)
        if not tables:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_dynamodb_tables(tables, account_id, account_name, region)
        return {
            "total": result.total_tables,
            "unused": result.unused_tables + result.low_usage_tables,
            "waste": result.unused_monthly_cost + result.low_usage_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"DynamoDB: {e}"}


def collect_codecommit(
    session, account_id: str, account_name: str, region: str
) -> Dict[str, Any]:
    """CodeCommit 수집 및 분석"""
    try:
        repos = collect_codecommit_repos(session, account_id, account_name, region)
        if not repos:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_codecommit_repos(repos, account_id, account_name, region)
        return {
            "total": result.total_repos,
            "unused": result.empty_repos,
            "waste": 0.0,  # CodeCommit 빈 리포지토리는 비용 없음
            "result": result,
        }
    except Exception as e:
        return {"error": f"CodeCommit: {e}"}


def collect_route53(session, account_id: str, account_name: str) -> Dict[str, Any]:
    """Route53 수집 및 분석 (글로벌 서비스)"""
    try:
        zones = collect_hosted_zones(session, account_id, account_name)
        if not zones:
            return {"total": 0, "empty": 0, "waste": 0.0, "result": None}

        result = analyze_hosted_zones(zones, account_id, account_name)
        return {
            "total": result.total_zones,
            "empty": result.empty_zones + result.ns_soa_only_zones,
            "waste": result.wasted_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Route53: {e}"}


def collect_s3(session, account_id: str, account_name: str) -> Dict[str, Any]:
    """S3 수집 및 분석 (글로벌 서비스)"""
    try:
        buckets = collect_buckets(session, account_id, account_name)
        if not buckets:
            return {"total": 0, "empty": 0, "result": None}

        result = analyze_buckets(buckets, account_id, account_name)
        return {
            "total": result.total_buckets,
            "empty": result.empty_buckets + result.versioning_only_buckets,
            "result": result,
        }
    except Exception as e:
        return {"error": f"S3: {e}"}


# =============================================================================
# 리전별 리소스 수집기 매핑 (카테고리별 정렬)
# =============================================================================

REGIONAL_COLLECTORS: Dict[str, Callable] = {
    # Compute (EC2)
    "ami": collect_ami,
    "ebs": collect_ebs_volumes,
    "snapshot": collect_snapshot,
    "eip": collect_eip_addresses,
    "eni": collect_eni,
    # Networking (VPC)
    "nat": collect_nat,
    "endpoint": collect_endpoint,
    # Load Balancing
    "elb": collect_elb,
    "target_group": collect_target_group,
    # Database
    "dynamodb": collect_dynamodb,
    "elasticache": collect_elasticache,
    "rds_instance": collect_rds_instance,
    "rds_snapshot": collect_rds_snapshot,
    # Storage
    "ecr": collect_ecr,
    "efs": collect_efs,
    # Serverless
    "apigateway": collect_apigateway,
    "eventbridge": collect_eventbridge,
    "lambda": collect_lambda,
    # Messaging
    "sns": collect_sns,
    "sqs": collect_sqs,
    # Security
    "acm": collect_acm,
    "kms": collect_kms,
    "secret": collect_secret,
    # Monitoring
    "cw_alarm": collect_cw_alarm,
    "loggroup": collect_loggroup,
    # Developer Tools
    "codecommit": collect_codecommit,
}

# 글로벌 수집기 (DNS)
GLOBAL_COLLECTORS: Dict[str, Callable] = {
    "route53": collect_route53,
    "s3": collect_s3,
}
