"""
plugins/cost/unused_all/collectors.py - 개별 리소스 수집/분석 함수

각 AWS 리소스 타입별 수집 및 분석 함수 정의
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from analyzers.acm.unused import (
    analyze_certificates as analyze_acm_certificates,
)
from analyzers.acm.unused import (
    collect_certificates as collect_acm_certificates,
)
from analyzers.apigateway.unused import (
    analyze_apis as analyze_apigateway_apis,
)
from analyzers.apigateway.unused import (
    collect_apis as collect_apigateway_apis,
)
from analyzers.cloudwatch.alarm_orphan import (
    analyze_alarms as analyze_cw_alarms,
)
from analyzers.cloudwatch.alarm_orphan import (
    collect_alarms as collect_cw_alarms,
)

# 각 도구에서 수집/분석 함수 import
from analyzers.cloudwatch.loggroup_audit import (
    analyze_log_groups,
    collect_log_groups,
)
from analyzers.codecommit.unused import (
    analyze_repos as analyze_codecommit_repos,
)
from analyzers.codecommit.unused import (
    collect_repos as collect_codecommit_repos,
)
from analyzers.dynamodb.unused import (
    analyze_tables as analyze_dynamodb_tables,
)
from analyzers.dynamodb.unused import (
    collect_dynamodb_tables,
)
from analyzers.ec2.ami_audit import (
    analyze_amis,
    collect_amis,
    get_used_ami_ids,
)
from analyzers.ec2.ebs_audit import analyze_ebs, collect_ebs
from analyzers.ec2.eip_audit import analyze_eips, collect_eips
from analyzers.ec2.snapshot_audit import (
    analyze_snapshots,
    collect_snapshots,
    get_ami_snapshot_mapping,
)
from analyzers.ec2.unused import (
    analyze_instances as analyze_ec2_instances,
)
from analyzers.ec2.unused import (
    collect_ec2_instances,
)
from analyzers.ecr.unused import analyze_ecr_repos, collect_ecr_repos
from analyzers.efs.unused import (
    analyze_filesystems as analyze_efs_filesystems,
)
from analyzers.efs.unused import (
    collect_efs_filesystems,
)

# 신규 추가된 미사용 리소스 분석 모듈
from analyzers.elasticache.unused import (
    analyze_clusters as analyze_elasticache_clusters,
)
from analyzers.elasticache.unused import (
    collect_elasticache_clusters,
)
from analyzers.elb.target_group_audit import (
    analyze_target_groups,
    collect_target_groups,
)
from analyzers.elb.unused import (
    analyze_load_balancers,
    collect_classic_load_balancers,
    collect_v2_load_balancers,
)
from analyzers.eventbridge.unused import (
    analyze_rules as analyze_eventbridge_rules,
)
from analyzers.eventbridge.unused import (
    collect_rules as collect_eventbridge_rules,
)
from analyzers.fn.unused import analyze_functions as analyze_lambda_functions
from analyzers.fsx.unused import (
    analyze_filesystems as analyze_fsx_filesystems,
)
from analyzers.fsx.unused import (
    collect_filesystems as collect_fsx_filesystems,
)
from analyzers.glue.unused import (
    analyze_jobs as analyze_glue_jobs,
)
from analyzers.glue.unused import (
    collect_glue_jobs,
)
from analyzers.kinesis.unused import (
    analyze_streams as analyze_kinesis_streams,
)
from analyzers.kinesis.unused import (
    collect_kinesis_streams,
)
from analyzers.kms.unused import analyze_kms_keys, collect_kms_keys
from analyzers.opensearch.unused import (
    analyze_domains as analyze_opensearch_domains,
)
from analyzers.opensearch.unused import (
    collect_opensearch_domains,
)
from analyzers.rds.snapshot_audit import (
    analyze_rds_snapshots,
    collect_rds_snapshots,
)
from analyzers.rds.unused import (
    analyze_instances as analyze_rds_instances,
)
from analyzers.rds.unused import (
    collect_rds_instances,
)
from analyzers.redshift.unused import (
    analyze_clusters as analyze_redshift_clusters,
)
from analyzers.redshift.unused import (
    collect_redshift_clusters,
)
from analyzers.route53.empty_zone import (
    analyze_hosted_zones,
    collect_hosted_zones,
)
from analyzers.s3.empty_bucket import analyze_buckets, collect_buckets
from analyzers.sagemaker.unused import (
    analyze_endpoints as analyze_sagemaker_endpoints,
)
from analyzers.sagemaker.unused import (
    collect_sagemaker_endpoints,
)
from analyzers.secretsmanager.unused import (
    analyze_secrets,
    collect_secrets,
)
from analyzers.sns.unused import (
    analyze_topics as analyze_sns_topics,
)
from analyzers.sns.unused import (
    collect_sns_topics,
)
from analyzers.sqs.unused import (
    analyze_queues as analyze_sqs_queues,
)
from analyzers.sqs.unused import (
    collect_sqs_queues,
)
from analyzers.transfer.unused import (
    analyze_servers as analyze_transfer_servers,
)
from analyzers.transfer.unused import (
    collect_servers as collect_transfer_servers,
)
from analyzers.vpc.endpoint_audit import (
    analyze_endpoints,
    collect_endpoints,
)
from analyzers.vpc.eni_audit import analyze_enis, collect_enis
from analyzers.vpc.nat_audit_analysis import NATAnalyzer, NATCollector
from analyzers.vpc.sg_audit_analysis import SGAnalyzer, SGCollector, SGStatus
from shared.aws.lambda_.collector import collect_functions_with_metrics

# =============================================================================
# 개별 리소스 수집/분석 함수 (병렬 실행용)
# =============================================================================


def collect_nat(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_eni(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_ebs_volumes(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_eip_addresses(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_elb(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """ELB 수집 및 분석"""
    try:
        v2_lbs = collect_v2_load_balancers(session, account_id, account_name, region)
        classic_lbs = collect_classic_load_balancers(session, account_id, account_name, region)
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


def collect_snapshot(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """EBS Snapshot 수집 및 분석"""
    try:
        snapshots = collect_snapshots(session, account_id, account_name, region)
        if not snapshots:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        ami_mapping = get_ami_snapshot_mapping(session, region)
        result = analyze_snapshots(snapshots, ami_mapping, account_id, account_name, region)
        return {
            "total": result.total_count,
            "unused": result.orphan_count + result.old_count,
            "waste": result.orphan_monthly_cost + result.old_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"EBS Snapshot: {e}"}


def collect_ami(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_rds_snapshot(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_loggroup(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_target_group(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_endpoint(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_secret(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_kms(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_ecr(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_lambda(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """Lambda 수집 및 분석"""
    try:
        functions = collect_functions_with_metrics(session, account_id, account_name, region)
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


def collect_elasticache(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """ElastiCache 수집 및 분석"""
    try:
        clusters = collect_elasticache_clusters(session, account_id, account_name, region)
        if not clusters:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_elasticache_clusters(clusters, account_id, account_name, region)
        return {
            "total": result.total_clusters,
            "unused": result.unused_clusters + result.low_usage_clusters,
            "waste": result.unused_monthly_cost + result.low_usage_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"ElastiCache: {e}"}


def collect_rds_instance(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """RDS Instance 수집 및 분석"""
    try:
        instances = collect_rds_instances(session, account_id, account_name, region)
        if not instances:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_rds_instances(instances, account_id, account_name, region)
        return {
            "total": result.total_instances,
            "unused": result.unused_instances + result.low_usage_instances + result.stopped_instances,
            "waste": result.unused_monthly_cost + result.low_usage_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"RDS Instance: {e}"}


def collect_efs(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_sqs(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_sns(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_acm(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_apigateway(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_eventbridge(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_cw_alarm(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_dynamodb(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_codecommit(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
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


def collect_ec2_instance(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """EC2 Instance 수집 및 분석"""
    try:
        instances = collect_ec2_instances(session, account_id, account_name, region)
        if not instances:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_ec2_instances(instances, account_id, account_name, region)
        return {
            "total": result.total_instances,
            "unused": result.unused_instances + result.low_usage_instances + result.stopped_instances,
            "waste": result.unused_monthly_cost + result.low_usage_monthly_cost + result.stopped_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"EC2 Instance: {e}"}


def collect_sagemaker_endpoint(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """SageMaker Endpoint 수집 및 분석"""
    try:
        endpoints = collect_sagemaker_endpoints(session, account_id, account_name, region)
        if not endpoints:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_sagemaker_endpoints(endpoints, account_id, account_name, region)
        return {
            "total": result.total_endpoints,
            "unused": result.unused_endpoints + result.low_usage_endpoints,
            "waste": result.unused_monthly_cost + result.low_usage_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"SageMaker Endpoint: {e}"}


def collect_route53(session, account_id: str, account_name: str) -> dict[str, Any]:
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


def collect_s3(session, account_id: str, account_name: str) -> dict[str, Any]:
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


def collect_redshift(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """Redshift 클러스터 수집 및 분석"""
    try:
        clusters = collect_redshift_clusters(session, account_id, account_name, region)
        if not clusters:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_redshift_clusters(clusters, account_id, account_name, region)
        return {
            "total": result.total_clusters,
            "unused": result.unused_clusters + result.low_usage_clusters + result.paused_clusters,
            "waste": result.unused_monthly_cost + result.low_usage_monthly_cost + result.paused_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Redshift: {e}"}


def collect_opensearch(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """OpenSearch 도메인 수집 및 분석"""
    try:
        domains = collect_opensearch_domains(session, account_id, account_name, region)
        if not domains:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_opensearch_domains(domains, account_id, account_name, region)
        return {
            "total": result.total_domains,
            "unused": result.unused_domains + result.low_usage_domains,
            "waste": result.unused_monthly_cost + result.low_usage_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"OpenSearch: {e}"}


def collect_kinesis(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """Kinesis 스트림 수집 및 분석"""
    try:
        streams = collect_kinesis_streams(session, account_id, account_name, region)
        if not streams:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_kinesis_streams(streams, account_id, account_name, region)
        return {
            "total": result.total_streams,
            "unused": result.unused_streams + result.low_usage_streams,
            "waste": result.unused_monthly_cost + result.low_usage_monthly_cost,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Kinesis: {e}"}


def collect_glue(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """Glue 작업 수집 및 분석"""
    try:
        jobs = collect_glue_jobs(session, account_id, account_name, region)
        if not jobs:
            return {"total": 0, "unused": 0, "result": None}

        result = analyze_glue_jobs(jobs, account_id, account_name, region)
        return {
            "total": result.total_jobs,
            "unused": result.unused_jobs + result.failed_jobs,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Glue: {e}"}


def collect_security_group(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """Security Group 수집 및 분석"""
    try:
        collector = SGCollector()
        sgs = collector.collect(session, account_id, account_name, region)
        if not sgs:
            return {"total": 0, "unused": 0, "result": None}

        analyzer = SGAnalyzer(sgs)
        sg_results, _ = analyzer.analyze()

        # 미사용 SG 수 계산
        unused_count = sum(1 for r in sg_results if r.status == SGStatus.UNUSED)

        return {
            "total": len(sg_results),
            "unused": unused_count,
            "result": sg_results,
        }
    except Exception as e:
        return {"error": f"Security Group: {e}"}


def collect_transfer(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """Transfer Family 서버 수집 및 분석"""
    try:
        servers = collect_transfer_servers(session, account_id, account_name, region)
        if not servers:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_transfer_servers(servers, account_id, account_name, region)
        return {
            "total": result.total_servers,
            "unused": result.unused_servers + result.idle_servers + result.no_users_servers,
            "waste": result.total_monthly_waste,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Transfer Family: {e}"}


def collect_fsx(session, account_id: str, account_name: str, region: str) -> dict[str, Any]:
    """FSx 파일 시스템 수집 및 분석"""
    try:
        filesystems = collect_fsx_filesystems(session, account_id, account_name, region)
        if not filesystems:
            return {"total": 0, "unused": 0, "waste": 0.0, "result": None}

        result = analyze_fsx_filesystems(filesystems, account_id, account_name, region)
        return {
            "total": result.total_filesystems,
            "unused": result.unused_filesystems + result.idle_filesystems,
            "waste": result.total_monthly_waste,
            "result": result,
        }
    except Exception as e:
        return {"error": f"FSx: {e}"}


# =============================================================================
# 리전별 리소스 수집기 매핑 (카테고리별 정렬)
# =============================================================================

REGIONAL_COLLECTORS: dict[str, Callable] = {
    # Compute (EC2)
    "ami": collect_ami,
    "ebs": collect_ebs_volumes,
    "snapshot": collect_snapshot,
    "eip": collect_eip_addresses,
    "eni": collect_eni,
    "ec2_instance": collect_ec2_instance,
    # Networking (VPC)
    "nat": collect_nat,
    "endpoint": collect_endpoint,
    # Load Balancing
    "elb": collect_elb,
    "target_group": collect_target_group,
    # Database
    "dynamodb": collect_dynamodb,
    "elasticache": collect_elasticache,
    "redshift": collect_redshift,
    "opensearch": collect_opensearch,
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
    # ML
    "sagemaker_endpoint": collect_sagemaker_endpoint,
    # Analytics
    "kinesis": collect_kinesis,
    "glue": collect_glue,
    # Security (VPC)
    "security_group": collect_security_group,
    # File Transfer
    "transfer": collect_transfer,
    "fsx": collect_fsx,
}

# 글로벌 수집기 (DNS)
GLOBAL_COLLECTORS: dict[str, Callable] = {
    "route53": collect_route53,
    "s3": collect_s3,
}
