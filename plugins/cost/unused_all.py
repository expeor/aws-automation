"""
plugins/cost/unused_all.py - 미사용 리소스 종합 분석

모든 미사용 리소스 종합 보고서:
- NAT Gateway, ENI, EBS, EIP, ELB, Target Group
- EBS Snapshot, AMI, RDS Snapshot
- CloudWatch Log Group
- VPC Endpoint, Secrets Manager, KMS
- ECR, Route53, S3
- Lambda

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from botocore.exceptions import ClientError
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from rich.console import Console

from core.auth import SessionIterator
from core.tools.output import OutputPath, open_in_explorer

# 각 도구에서 수집/분석 함수 import
from plugins.vpc.nat_audit_analysis import NATCollector, NATAnalyzer
from plugins.vpc.eni_audit import collect_enis, analyze_enis, ENIAnalysisResult
from plugins.ec2.ebs_audit import collect_ebs, analyze_ebs, EBSAnalysisResult
from plugins.ec2.eip_audit import collect_eips, analyze_eips, EIPAnalysisResult
from plugins.ec2.snapshot_audit import (
    collect_snapshots, get_ami_snapshot_mapping, analyze_snapshots, SnapshotAnalysisResult
)
from plugins.ec2.ami_audit import (
    collect_amis, get_used_ami_ids, analyze_amis, AMIAnalysisResult
)
from plugins.elb.unused import (
    collect_v2_load_balancers, collect_classic_load_balancers,
    analyze_load_balancers, LBAnalysisResult
)
from plugins.rds.snapshot_audit import (
    collect_rds_snapshots, analyze_rds_snapshots, RDSSnapshotAnalysisResult
)
from plugins.cloudwatch.loggroup_audit import (
    collect_log_groups, analyze_log_groups, LogGroupAnalysisResult
)
from plugins.elb.target_group_audit import (
    collect_target_groups, analyze_target_groups, TargetGroupAnalysisResult
)
from plugins.vpc.endpoint_audit import (
    collect_endpoints, analyze_endpoints, EndpointAnalysisResult
)
from plugins.secretsmanager.unused import (
    collect_secrets, analyze_secrets, SecretAnalysisResult
)
from plugins.kms.unused import (
    collect_kms_keys, analyze_kms_keys, KMSKeyAnalysisResult
)
from plugins.ecr.unused import (
    collect_ecr_repos, analyze_ecr_repos, ECRAnalysisResult
)
from plugins.route53.empty_zone import (
    collect_hosted_zones, analyze_hosted_zones, Route53AnalysisResult
)
from plugins.s3.empty_bucket import (
    collect_buckets, analyze_buckets, S3AnalysisResult
)
from plugins.fn.unused import (
    LambdaAnalysisResult, analyze_functions as analyze_lambda_functions
)
from plugins.fn.common.collector import collect_functions_with_metrics

console = Console()


# =============================================================================
# 종합 결과 데이터 구조
# =============================================================================


@dataclass
class UnusedResourceSummary:
    """미사용 리소스 종합 요약"""

    account_id: str
    account_name: str
    region: str

    # NAT Gateway
    nat_total: int = 0
    nat_unused: int = 0
    nat_monthly_waste: float = 0.0

    # ENI
    eni_total: int = 0
    eni_unused: int = 0

    # EBS
    ebs_total: int = 0
    ebs_unused: int = 0
    ebs_monthly_waste: float = 0.0

    # EIP
    eip_total: int = 0
    eip_unused: int = 0
    eip_monthly_waste: float = 0.0

    # ELB
    elb_total: int = 0
    elb_unused: int = 0
    elb_monthly_waste: float = 0.0

    # EBS Snapshot
    snap_total: int = 0
    snap_unused: int = 0
    snap_monthly_waste: float = 0.0

    # AMI
    ami_total: int = 0
    ami_unused: int = 0
    ami_monthly_waste: float = 0.0

    # RDS Snapshot
    rds_snap_total: int = 0
    rds_snap_old: int = 0
    rds_snap_monthly_waste: float = 0.0

    # CloudWatch Log Group
    loggroup_total: int = 0
    loggroup_issue: int = 0
    loggroup_monthly_waste: float = 0.0

    # Target Group
    tg_total: int = 0
    tg_issue: int = 0

    # VPC Endpoint
    endpoint_total: int = 0
    endpoint_unused: int = 0
    endpoint_monthly_waste: float = 0.0

    # Secrets Manager
    secret_total: int = 0
    secret_unused: int = 0
    secret_monthly_waste: float = 0.0

    # KMS
    kms_total: int = 0
    kms_unused: int = 0
    kms_monthly_waste: float = 0.0

    # ECR
    ecr_total: int = 0
    ecr_issue: int = 0
    ecr_monthly_waste: float = 0.0

    # Route53
    route53_total: int = 0
    route53_empty: int = 0
    route53_monthly_waste: float = 0.0

    # S3
    s3_total: int = 0
    s3_empty: int = 0

    # Lambda
    lambda_total: int = 0
    lambda_unused: int = 0
    lambda_monthly_waste: float = 0.0


@dataclass
class UnusedAllResult:
    """종합 분석 결과"""

    summaries: List[UnusedResourceSummary] = field(default_factory=list)

    # 상세 결과
    nat_findings: List[Any] = field(default_factory=list)
    eni_results: List[ENIAnalysisResult] = field(default_factory=list)
    ebs_results: List[EBSAnalysisResult] = field(default_factory=list)
    eip_results: List[EIPAnalysisResult] = field(default_factory=list)
    elb_results: List[LBAnalysisResult] = field(default_factory=list)
    snap_results: List[SnapshotAnalysisResult] = field(default_factory=list)
    ami_results: List[AMIAnalysisResult] = field(default_factory=list)
    rds_snap_results: List[RDSSnapshotAnalysisResult] = field(default_factory=list)
    loggroup_results: List[LogGroupAnalysisResult] = field(default_factory=list)
    tg_results: List[TargetGroupAnalysisResult] = field(default_factory=list)
    endpoint_results: List[EndpointAnalysisResult] = field(default_factory=list)
    secret_results: List[SecretAnalysisResult] = field(default_factory=list)
    kms_results: List[KMSKeyAnalysisResult] = field(default_factory=list)
    ecr_results: List[ECRAnalysisResult] = field(default_factory=list)
    route53_results: List[Route53AnalysisResult] = field(default_factory=list)
    s3_results: List[S3AnalysisResult] = field(default_factory=list)
    lambda_results: List[LambdaAnalysisResult] = field(default_factory=list)


# =============================================================================
# 종합 분석
# =============================================================================


def run(ctx) -> None:
    """미사용 리소스 종합 분석 실행"""
    console.print("[bold]미사용 리소스 종합 분석 시작...[/bold]")

    result = UnusedAllResult()
    collected = set()
    global_collected = set()  # 글로벌 서비스용 (Route53, S3)
    errors = []

    with SessionIterator(ctx) as sessions:
        for session, identifier, region in sessions:
            try:
                sts = session.client("sts")
                account_id = sts.get_caller_identity()["Account"]

                key = f"{account_id}:{region}"
                if key in collected:
                    continue
                collected.add(key)

                # 계정명
                account_name = identifier
                if hasattr(ctx, "accounts") and ctx.accounts:
                    for acc in ctx.accounts:
                        if acc.id == account_id:
                            account_name = acc.name
                            break

                console.print(f"\n[cyan]{account_name} / {region}[/cyan]")

                summary = UnusedResourceSummary(
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                )

                # ----- NAT Gateway -----
                console.print("  [dim]NAT Gateway...[/dim]", end=" ")
                try:
                    nat_collector = NATCollector()
                    nat_data = nat_collector.collect(session, account_id, account_name, region)
                    if nat_data.nat_gateways:
                        analyzer = NATAnalyzer(nat_data)
                        nat_result = analyzer.analyze()
                        stats = analyzer.get_summary_stats()
                        summary.nat_total = stats.get("total_nat_count", 0)
                        summary.nat_unused = stats.get("unused_count", 0) + stats.get("low_usage_count", 0)
                        summary.nat_monthly_waste = stats.get("total_monthly_waste", 0)
                        result.nat_findings.append(nat_result)
                        if summary.nat_unused > 0:
                            console.print(f"[red]{summary.nat_unused}개[/red]")
                        else:
                            console.print(f"[green]{summary.nat_total}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"NAT: {e}")

                # ----- ENI -----
                console.print("  [dim]ENI...[/dim]", end=" ")
                try:
                    enis = collect_enis(session, account_id, account_name, region)
                    if enis:
                        eni_result = analyze_enis(enis, account_id, account_name, region)
                        summary.eni_total = eni_result.total_count
                        summary.eni_unused = eni_result.unused_count
                        result.eni_results.append(eni_result)
                        if summary.eni_unused > 0:
                            console.print(f"[red]{summary.eni_unused}개[/red]")
                        else:
                            console.print(f"[green]{eni_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"ENI: {e}")

                # ----- EBS -----
                console.print("  [dim]EBS...[/dim]", end=" ")
                try:
                    volumes = collect_ebs(session, account_id, account_name, region)
                    if volumes:
                        ebs_result = analyze_ebs(volumes, account_id, account_name, region)
                        summary.ebs_total = ebs_result.total_count
                        summary.ebs_unused = ebs_result.unused_count
                        summary.ebs_monthly_waste = ebs_result.unused_monthly_cost
                        result.ebs_results.append(ebs_result)
                        if summary.ebs_unused > 0:
                            console.print(f"[red]{summary.ebs_unused}개[/red]")
                        else:
                            console.print(f"[green]{ebs_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"EBS: {e}")

                # ----- EIP -----
                console.print("  [dim]EIP...[/dim]", end=" ")
                try:
                    eips = collect_eips(session, account_id, account_name, region)
                    if eips:
                        eip_result = analyze_eips(eips, account_id, account_name, region)
                        summary.eip_total = eip_result.total_count
                        summary.eip_unused = eip_result.unused_count
                        summary.eip_monthly_waste = eip_result.unused_monthly_cost
                        result.eip_results.append(eip_result)
                        if summary.eip_unused > 0:
                            console.print(f"[red]{summary.eip_unused}개[/red]")
                        else:
                            console.print(f"[green]{eip_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"EIP: {e}")

                # ----- ELB -----
                console.print("  [dim]ELB...[/dim]", end=" ")
                try:
                    v2_lbs = collect_v2_load_balancers(session, account_id, account_name, region)
                    classic_lbs = collect_classic_load_balancers(session, account_id, account_name, region)
                    all_lbs = v2_lbs + classic_lbs
                    if all_lbs:
                        elb_result = analyze_load_balancers(all_lbs, account_id, account_name, region)
                        summary.elb_total = elb_result.total_count
                        summary.elb_unused = elb_result.unused_count + elb_result.unhealthy_count
                        summary.elb_monthly_waste = elb_result.unused_monthly_cost
                        result.elb_results.append(elb_result)
                        if summary.elb_unused > 0:
                            console.print(f"[red]{summary.elb_unused}개[/red]")
                        else:
                            console.print(f"[green]{elb_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"ELB: {e}")

                # ----- EBS Snapshot -----
                console.print("  [dim]EBS Snapshot...[/dim]", end=" ")
                try:
                    snapshots = collect_snapshots(session, account_id, account_name, region)
                    if snapshots:
                        ami_mapping = get_ami_snapshot_mapping(session, region)
                        snap_result = analyze_snapshots(snapshots, ami_mapping, account_id, account_name, region)
                        summary.snap_total = snap_result.total_count
                        summary.snap_unused = snap_result.orphan_count + snap_result.old_count
                        summary.snap_monthly_waste = snap_result.orphan_monthly_cost + snap_result.old_monthly_cost
                        result.snap_results.append(snap_result)
                        if summary.snap_unused > 0:
                            console.print(f"[red]{summary.snap_unused}개[/red]")
                        else:
                            console.print(f"[green]{snap_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"EBS Snapshot: {e}")

                # ----- AMI -----
                console.print("  [dim]AMI...[/dim]", end=" ")
                try:
                    amis = collect_amis(session, account_id, account_name, region)
                    if amis:
                        used_ami_ids = get_used_ami_ids(session, region)
                        ami_result = analyze_amis(amis, used_ami_ids, account_id, account_name, region)
                        summary.ami_total = ami_result.total_count
                        summary.ami_unused = ami_result.unused_count
                        summary.ami_monthly_waste = ami_result.unused_monthly_cost
                        result.ami_results.append(ami_result)
                        if summary.ami_unused > 0:
                            console.print(f"[red]{summary.ami_unused}개[/red]")
                        else:
                            console.print(f"[green]{ami_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"AMI: {e}")

                # ----- RDS Snapshot -----
                console.print("  [dim]RDS Snapshot...[/dim]", end=" ")
                try:
                    rds_snaps = collect_rds_snapshots(session, account_id, account_name, region)
                    if rds_snaps:
                        rds_snap_result = analyze_rds_snapshots(rds_snaps, account_id, account_name, region)
                        summary.rds_snap_total = rds_snap_result.total_count
                        summary.rds_snap_old = rds_snap_result.old_count
                        summary.rds_snap_monthly_waste = rds_snap_result.old_monthly_cost
                        result.rds_snap_results.append(rds_snap_result)
                        if summary.rds_snap_old > 0:
                            console.print(f"[yellow]{summary.rds_snap_old}개[/yellow]")
                        else:
                            console.print(f"[green]{rds_snap_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"RDS Snapshot: {e}")

                # ----- CloudWatch Log Group -----
                console.print("  [dim]Log Group...[/dim]", end=" ")
                try:
                    log_groups = collect_log_groups(session, account_id, account_name, region)
                    if log_groups:
                        lg_result = analyze_log_groups(log_groups, account_id, account_name, region)
                        summary.loggroup_total = lg_result.total_count
                        summary.loggroup_issue = lg_result.empty_count + lg_result.old_count
                        summary.loggroup_monthly_waste = lg_result.empty_monthly_cost + lg_result.old_monthly_cost
                        result.loggroup_results.append(lg_result)
                        if summary.loggroup_issue > 0:
                            console.print(f"[yellow]{summary.loggroup_issue}개[/yellow]")
                        else:
                            console.print(f"[green]{lg_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"Log Group: {e}")

                # ----- Target Group -----
                console.print("  [dim]Target Group...[/dim]", end=" ")
                try:
                    tgs = collect_target_groups(session, account_id, account_name, region)
                    if tgs:
                        tg_result = analyze_target_groups(tgs, account_id, account_name, region)
                        summary.tg_total = tg_result.total_count
                        summary.tg_issue = tg_result.unattached_count + tg_result.no_targets_count
                        result.tg_results.append(tg_result)
                        if summary.tg_issue > 0:
                            console.print(f"[yellow]{summary.tg_issue}개[/yellow]")
                        else:
                            console.print(f"[green]{tg_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"Target Group: {e}")

                # ----- VPC Endpoint -----
                console.print("  [dim]VPC Endpoint...[/dim]", end=" ")
                try:
                    endpoints = collect_endpoints(session, account_id, account_name, region)
                    if endpoints:
                        ep_result = analyze_endpoints(endpoints, account_id, account_name, region)
                        summary.endpoint_total = ep_result.total_count
                        summary.endpoint_unused = ep_result.unused_count
                        summary.endpoint_monthly_waste = ep_result.unused_monthly_cost
                        result.endpoint_results.append(ep_result)
                        if summary.endpoint_unused > 0:
                            console.print(f"[red]{summary.endpoint_unused}개[/red]")
                        else:
                            console.print(f"[green]{ep_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"VPC Endpoint: {e}")

                # ----- Secrets Manager -----
                console.print("  [dim]Secrets Manager...[/dim]", end=" ")
                try:
                    secrets = collect_secrets(session, account_id, account_name, region)
                    if secrets:
                        sec_result = analyze_secrets(secrets, account_id, account_name, region)
                        summary.secret_total = sec_result.total_count
                        summary.secret_unused = sec_result.unused_count
                        summary.secret_monthly_waste = sec_result.unused_monthly_cost
                        result.secret_results.append(sec_result)
                        if summary.secret_unused > 0:
                            console.print(f"[yellow]{summary.secret_unused}개[/yellow]")
                        else:
                            console.print(f"[green]{sec_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"Secrets Manager: {e}")

                # ----- KMS -----
                console.print("  [dim]KMS...[/dim]", end=" ")
                try:
                    kms_keys = collect_kms_keys(session, account_id, account_name, region)
                    if kms_keys:
                        kms_result = analyze_kms_keys(kms_keys, account_id, account_name, region)
                        summary.kms_total = kms_result.total_count
                        summary.kms_unused = kms_result.disabled_count + kms_result.pending_delete_count
                        summary.kms_monthly_waste = kms_result.disabled_monthly_cost
                        result.kms_results.append(kms_result)
                        if summary.kms_unused > 0:
                            console.print(f"[yellow]{summary.kms_unused}개[/yellow]")
                        else:
                            console.print(f"[green]{kms_result.normal_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"KMS: {e}")

                # ----- ECR -----
                console.print("  [dim]ECR...[/dim]", end=" ")
                try:
                    repos = collect_ecr_repos(session, account_id, account_name, region)
                    if repos:
                        ecr_result = analyze_ecr_repos(repos, account_id, account_name, region)
                        summary.ecr_total = ecr_result.total_repos
                        summary.ecr_issue = ecr_result.empty_repos + ecr_result.repos_with_old_images
                        summary.ecr_monthly_waste = ecr_result.old_images_monthly_cost
                        result.ecr_results.append(ecr_result)
                        if summary.ecr_issue > 0:
                            console.print(f"[yellow]{summary.ecr_issue}개[/yellow]")
                        else:
                            console.print(f"[green]{ecr_result.total_repos}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"ECR: {e}")

                # ----- Lambda -----
                console.print("  [dim]Lambda...[/dim]", end=" ")
                try:
                    functions = collect_functions_with_metrics(session, account_id, account_name, region)
                    if functions:
                        lambda_result = analyze_lambda_functions(functions, account_id, account_name, region)
                        summary.lambda_total = lambda_result.total_count
                        summary.lambda_unused = lambda_result.unused_count
                        summary.lambda_monthly_waste = lambda_result.unused_monthly_cost
                        result.lambda_results.append(lambda_result)
                        if summary.lambda_unused > 0:
                            console.print(f"[red]{summary.lambda_unused}개[/red]")
                        else:
                            console.print(f"[green]{lambda_result.total_count}개[/green]")
                    else:
                        console.print("[dim](없음)[/dim]")
                except Exception as e:
                    console.print(f"[red]오류[/red]")
                    errors.append(f"Lambda: {e}")

                # ----- 글로벌 서비스 (계정당 한 번만) -----
                if account_id not in global_collected:
                    global_collected.add(account_id)

                    # ----- Route53 -----
                    console.print("  [dim]Route53...[/dim]", end=" ")
                    try:
                        zones = collect_hosted_zones(session, account_id, account_name)
                        if zones:
                            r53_result = analyze_hosted_zones(zones, account_id, account_name)
                            summary.route53_total = r53_result.total_zones
                            summary.route53_empty = r53_result.empty_zones + r53_result.ns_soa_only_zones
                            summary.route53_monthly_waste = r53_result.wasted_monthly_cost
                            result.route53_results.append(r53_result)
                            if summary.route53_empty > 0:
                                console.print(f"[yellow]{summary.route53_empty}개[/yellow]")
                            else:
                                console.print(f"[green]{r53_result.total_zones}개[/green]")
                        else:
                            console.print("[dim](없음)[/dim]")
                    except Exception as e:
                        console.print(f"[red]오류[/red]")
                        errors.append(f"Route53: {e}")

                    # ----- S3 -----
                    console.print("  [dim]S3...[/dim]", end=" ")
                    try:
                        buckets = collect_buckets(session, account_id, account_name)
                        if buckets:
                            s3_result = analyze_buckets(buckets, account_id, account_name)
                            summary.s3_total = s3_result.total_buckets
                            summary.s3_empty = s3_result.empty_buckets + s3_result.versioning_only_buckets
                            result.s3_results.append(s3_result)
                            if summary.s3_empty > 0:
                                console.print(f"[yellow]{summary.s3_empty}개[/yellow]")
                            else:
                                console.print(f"[green]{s3_result.total_buckets}개[/green]")
                        else:
                            console.print("[dim](없음)[/dim]")
                    except Exception as e:
                        console.print(f"[red]오류[/red]")
                        errors.append(f"S3: {e}")

                result.summaries.append(summary)

            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "Unknown")
                if code not in ("InvalidClientTokenId", "ExpiredToken", "AccessDenied"):
                    console.print(f"  [yellow]{code}[/yellow]")
            except Exception as e:
                console.print(f"  [red]{e}[/red]")

    if not result.summaries:
        console.print("[yellow]분석 결과 없음[/yellow]")
        return

    # 총 절감 가능 금액 계산
    total_waste = sum(
        s.nat_monthly_waste + s.ebs_monthly_waste + s.eip_monthly_waste +
        s.elb_monthly_waste + s.snap_monthly_waste + s.ami_monthly_waste +
        s.rds_snap_monthly_waste + s.loggroup_monthly_waste +
        s.endpoint_monthly_waste + s.secret_monthly_waste + s.kms_monthly_waste +
        s.ecr_monthly_waste + s.route53_monthly_waste + s.lambda_monthly_waste
        for s in result.summaries
    )

    # 요약 출력
    console.print("\n" + "=" * 50)
    console.print("[bold]종합 결과[/bold]")
    console.print("=" * 50)

    _print_summary("NAT Gateway", result.summaries, "nat_total", "nat_unused", "nat_monthly_waste")
    _print_summary("ENI", result.summaries, "eni_total", "eni_unused", None)
    _print_summary("EBS", result.summaries, "ebs_total", "ebs_unused", "ebs_monthly_waste")
    _print_summary("EIP", result.summaries, "eip_total", "eip_unused", "eip_monthly_waste")
    _print_summary("ELB", result.summaries, "elb_total", "elb_unused", "elb_monthly_waste")
    _print_summary("EBS Snapshot", result.summaries, "snap_total", "snap_unused", "snap_monthly_waste")
    _print_summary("AMI", result.summaries, "ami_total", "ami_unused", "ami_monthly_waste")
    _print_summary("RDS Snapshot", result.summaries, "rds_snap_total", "rds_snap_old", "rds_snap_monthly_waste")
    _print_summary("Log Group", result.summaries, "loggroup_total", "loggroup_issue", "loggroup_monthly_waste")
    _print_summary("Target Group", result.summaries, "tg_total", "tg_issue", None)
    _print_summary("VPC Endpoint", result.summaries, "endpoint_total", "endpoint_unused", "endpoint_monthly_waste")
    _print_summary("Secrets Manager", result.summaries, "secret_total", "secret_unused", "secret_monthly_waste")
    _print_summary("KMS", result.summaries, "kms_total", "kms_unused", "kms_monthly_waste")
    _print_summary("ECR", result.summaries, "ecr_total", "ecr_issue", "ecr_monthly_waste")
    _print_summary("Route53", result.summaries, "route53_total", "route53_empty", "route53_monthly_waste")
    _print_summary("S3", result.summaries, "s3_total", "s3_empty", None)
    _print_summary("Lambda", result.summaries, "lambda_total", "lambda_unused", "lambda_monthly_waste")

    if total_waste > 0:
        console.print(f"\n[bold yellow]총 월간 절감 가능: ${total_waste:,.2f}[/bold yellow]")

    # 보고서 생성
    console.print("\n[cyan]Excel 보고서 생성 중...[/cyan]")

    if hasattr(ctx, "is_sso_session") and ctx.is_sso_session() and ctx.accounts:
        identifier = ctx.accounts[0].id
    elif ctx.profile_name:
        identifier = ctx.profile_name
    else:
        identifier = "default"

    output_path = OutputPath(identifier).sub("unused-all").with_date().build()
    filepath = generate_report(result, output_path)

    console.print(f"[bold green]완료![/bold green] {filepath}")

    if errors:
        console.print(f"\n[yellow]오류 {len(errors)}건[/yellow]")

    open_in_explorer(output_path)


def _print_summary(name: str, summaries: List, total_attr: str, unused_attr: str, waste_attr: Optional[str]) -> None:
    """요약 출력 헬퍼"""
    total = sum(getattr(s, total_attr, 0) for s in summaries)
    unused = sum(getattr(s, unused_attr, 0) for s in summaries)
    waste = sum(getattr(s, waste_attr, 0) for s in summaries) if waste_attr else 0

    console.print(f"\n[bold]{name}[/bold]: 전체 {total}개", end="")
    if unused > 0:
        waste_str = f" (${waste:,.2f}/월)" if waste > 0 else ""
        console.print(f" / [red]미사용 {unused}개{waste_str}[/red]")
    else:
        console.print("")


# =============================================================================
# Excel 보고서
# =============================================================================


def generate_report(result: UnusedAllResult, output_dir: str) -> str:
    """종합 Excel 보고서 생성"""
    wb = Workbook()
    if wb.active:
        wb.remove(wb.active)

    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    red_fill = PatternFill(start_color="FF6B6B", end_color="FF6B6B", fill_type="solid")

    # ===== Summary =====
    ws = wb.create_sheet("Summary")
    ws["A1"] = "미사용 리소스 종합 보고서"
    ws["A1"].font = Font(bold=True, size=16)
    ws["A2"] = f"생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    row = 4
    for col, h in enumerate(["리소스", "전체", "미사용", "월간 낭비"], 1):
        ws.cell(row=row, column=col, value=h).fill = header_fill
        ws.cell(row=row, column=col).font = header_font

    resources = [
        ("NAT Gateway", "nat_total", "nat_unused", "nat_monthly_waste"),
        ("ENI", "eni_total", "eni_unused", None),
        ("EBS", "ebs_total", "ebs_unused", "ebs_monthly_waste"),
        ("EIP", "eip_total", "eip_unused", "eip_monthly_waste"),
        ("ELB", "elb_total", "elb_unused", "elb_monthly_waste"),
        ("EBS Snapshot", "snap_total", "snap_unused", "snap_monthly_waste"),
        ("AMI", "ami_total", "ami_unused", "ami_monthly_waste"),
        ("RDS Snapshot", "rds_snap_total", "rds_snap_old", "rds_snap_monthly_waste"),
        ("Log Group", "loggroup_total", "loggroup_issue", "loggroup_monthly_waste"),
        ("Target Group", "tg_total", "tg_issue", None),
        ("VPC Endpoint", "endpoint_total", "endpoint_unused", "endpoint_monthly_waste"),
        ("Secrets Manager", "secret_total", "secret_unused", "secret_monthly_waste"),
        ("KMS", "kms_total", "kms_unused", "kms_monthly_waste"),
        ("ECR", "ecr_total", "ecr_issue", "ecr_monthly_waste"),
        ("Route53", "route53_total", "route53_empty", "route53_monthly_waste"),
        ("S3", "s3_total", "s3_empty", None),
        ("Lambda", "lambda_total", "lambda_unused", "lambda_monthly_waste"),
    ]

    for name, total_attr, unused_attr, waste_attr in resources:
        row += 1
        total = sum(getattr(s, total_attr, 0) for s in result.summaries)
        unused = sum(getattr(s, unused_attr, 0) for s in result.summaries)
        waste = sum(getattr(s, waste_attr, 0) for s in result.summaries) if waste_attr else 0
        ws.cell(row=row, column=1, value=name)
        ws.cell(row=row, column=2, value=total)
        ws.cell(row=row, column=3, value=unused)
        ws.cell(row=row, column=4, value=f"${waste:,.2f}" if waste > 0 else "-")
        if unused > 0:
            ws.cell(row=row, column=3).fill = red_fill

    # 총 절감
    total_waste = sum(
        s.nat_monthly_waste + s.ebs_monthly_waste + s.eip_monthly_waste +
        s.elb_monthly_waste + s.snap_monthly_waste + s.ami_monthly_waste +
        s.rds_snap_monthly_waste + s.loggroup_monthly_waste +
        s.endpoint_monthly_waste + s.secret_monthly_waste + s.kms_monthly_waste +
        s.ecr_monthly_waste + s.route53_monthly_waste + s.lambda_monthly_waste
        for s in result.summaries
    )
    row += 2
    ws.cell(row=row, column=1, value="총 월간 절감 가능").font = Font(bold=True)
    ws.cell(row=row, column=4, value=f"${total_waste:,.2f}").font = Font(bold=True, color="FF0000")

    # ===== 상세 시트들 =====
    _create_nat_sheet(wb, result.nat_findings, header_fill, header_font)
    _create_eni_sheet(wb, result.eni_results, header_fill, header_font)
    _create_ebs_sheet(wb, result.ebs_results, header_fill, header_font)
    _create_eip_sheet(wb, result.eip_results, header_fill, header_font)
    _create_elb_sheet(wb, result.elb_results, header_fill, header_font)
    _create_snap_sheet(wb, result.snap_results, header_fill, header_font)
    _create_ami_sheet(wb, result.ami_results, header_fill, header_font)
    _create_rds_snap_sheet(wb, result.rds_snap_results, header_fill, header_font)
    _create_loggroup_sheet(wb, result.loggroup_results, header_fill, header_font)
    _create_tg_sheet(wb, result.tg_results, header_fill, header_font)
    _create_endpoint_sheet(wb, result.endpoint_results, header_fill, header_font)
    _create_secret_sheet(wb, result.secret_results, header_fill, header_font)
    _create_kms_sheet(wb, result.kms_results, header_fill, header_font)
    _create_ecr_sheet(wb, result.ecr_results, header_fill, header_font)
    _create_route53_sheet(wb, result.route53_results, header_fill, header_font)
    _create_s3_sheet(wb, result.s3_results, header_fill, header_font)
    _create_lambda_sheet(wb, result.lambda_results, header_fill, header_font)

    # 열 너비 조정
    for sheet in wb.worksheets:
        for col in sheet.columns:
            max_len = max(len(str(c.value) if c.value else "") for c in col)
            col_idx = col[0].column
            if col_idx:
                sheet.column_dimensions[get_column_letter(col_idx)].width = min(max(max_len + 2, 10), 40)
        if sheet.title != "Summary":
            sheet.freeze_panes = "A2"

    # 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"Unused_Resources_{timestamp}.xlsx")
    os.makedirs(output_dir, exist_ok=True)
    wb.save(filepath)

    return filepath


def _create_nat_sheet(wb, findings, header_fill, header_font):
    ws = wb.create_sheet("NAT Gateway")
    ws.append(["Account", "Region", "NAT ID", "Name", "Usage", "Monthly Waste", "Recommendation"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for nat_result in findings:
        for f in nat_result.findings:
            if f.usage_status.value in ("unused", "low_usage"):
                ws.append([f.nat.account_name, f.nat.region, f.nat.nat_gateway_id, f.nat.name,
                          f.usage_status.value, f"${f.monthly_waste:,.2f}", f.recommendation])


def _create_eni_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("ENI")
    ws.append(["Account", "Region", "ENI ID", "Name", "Usage", "Type", "Recommendation"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.usage_status.value in ("unused", "pending"):
                ws.append([f.eni.account_name, f.eni.region, f.eni.id, f.eni.name,
                          f.usage_status.value, f.eni.interface_type, f.recommendation])


def _create_ebs_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("EBS")
    ws.append(["Account", "Region", "Volume ID", "Name", "Type", "Size (GB)", "Monthly Cost", "Recommendation"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.usage_status.value in ("unused", "pending"):
                ws.append([f.volume.account_name, f.volume.region, f.volume.id, f.volume.name,
                          f.volume.volume_type, f.volume.size_gb, round(f.volume.monthly_cost, 2), f.recommendation])


def _create_eip_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("EIP")
    ws.append(["Account", "Region", "Allocation ID", "Public IP", "Name", "Monthly Cost", "Recommendation"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.usage_status.value == "unused":
                ws.append([f.eip.account_name, f.eip.region, f.eip.allocation_id, f.eip.public_ip,
                          f.eip.name, round(f.eip.monthly_cost, 2), f.recommendation])


def _create_elb_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("ELB")
    ws.append(["Account", "Region", "Name", "Type", "Usage", "Targets", "Healthy", "Monthly Cost", "Recommendation"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.usage_status.value in ("unused", "unhealthy"):
                ws.append([f.lb.account_name, f.lb.region, f.lb.name, f.lb.lb_type.upper(),
                          f.usage_status.value, f.lb.total_targets, f.lb.healthy_targets,
                          round(f.lb.monthly_cost, 2), f.recommendation])


def _create_snap_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("EBS Snapshot")
    ws.append(["Account", "Region", "Snapshot ID", "Name", "Usage", "Size (GB)", "Age (days)", "Monthly Cost", "Recommendation"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.usage_status.value in ("orphan", "old"):
                ws.append([f.snapshot.account_name, f.snapshot.region, f.snapshot.id, f.snapshot.name,
                          f.usage_status.value, f.snapshot.volume_size_gb, f.snapshot.age_days,
                          round(f.snapshot.monthly_cost, 2), f.recommendation])


def _create_ami_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("AMI")
    ws.append(["Account", "Region", "AMI ID", "Name", "Size (GB)", "Age (days)", "Monthly Cost", "Recommendation"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.usage_status.value == "unused":
                ws.append([f.ami.account_name, f.ami.region, f.ami.id, f.ami.name,
                          f.ami.total_size_gb, f.ami.age_days, round(f.ami.monthly_cost, 2), f.recommendation])


def _create_rds_snap_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("RDS Snapshot")
    ws.append(["Account", "Region", "Snapshot ID", "DB Identifier", "Type", "Engine", "Size (GB)", "Age (days)", "Monthly Cost", "Recommendation"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.usage_status.value == "old":
                ws.append([f.snapshot.account_name, f.snapshot.region, f.snapshot.id, f.snapshot.db_identifier,
                          f.snapshot.snapshot_type.value.upper(), f.snapshot.engine, f.snapshot.allocated_storage_gb,
                          f.snapshot.age_days, round(f.snapshot.monthly_cost, 2), f.recommendation])


def _create_loggroup_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("Log Group")
    ws.append(["Account", "Region", "Log Group", "상태", "저장 (GB)", "보존 기간", "마지막 Ingestion", "월간 비용", "권장 조치"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                lg = f.log_group
                ws.append([lg.account_name, lg.region, lg.name, f.status.value,
                          round(lg.stored_gb, 4), f"{lg.retention_days}일" if lg.retention_days else "무기한",
                          lg.last_ingestion_time.strftime("%Y-%m-%d") if lg.last_ingestion_time else "-",
                          round(lg.monthly_cost, 4), f.recommendation])


def _create_tg_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("Target Group")
    ws.append(["Account", "Region", "Name", "상태", "Type", "Protocol", "Port", "LB 연결", "Total Targets", "Healthy", "권장 조치"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                tg = f.tg
                ws.append([tg.account_name, tg.region, tg.name, f.status.value,
                          tg.target_type, tg.protocol or "-", tg.port or "-",
                          len(tg.load_balancer_arns), tg.total_targets, tg.healthy_targets, f.recommendation])


def _create_endpoint_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("VPC Endpoint")
    ws.append(["Account", "Region", "Endpoint ID", "Type", "Service", "VPC", "State", "월간 비용", "권장 조치"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                ep = f.endpoint
                ws.append([ep.account_name, ep.region, ep.endpoint_id, ep.endpoint_type,
                          ep.service_name.split(".")[-1], ep.vpc_id, ep.state,
                          round(ep.monthly_cost, 2), f.recommendation])


def _create_secret_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("Secrets Manager")
    ws.append(["Account", "Region", "Name", "상태", "마지막 액세스", "월간 비용", "권장 조치"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                sec = f.secret
                last_access = sec.last_accessed_date.strftime("%Y-%m-%d") if sec.last_accessed_date else "없음"
                ws.append([sec.account_name, sec.region, sec.name, f.status.value,
                          last_access, round(sec.monthly_cost, 2), f.recommendation])


def _create_kms_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("KMS")
    ws.append(["Account", "Region", "Key ID", "Description", "상태", "Manager", "월간 비용", "권장 조치"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                key = f.key
                ws.append([key.account_name, key.region, key.key_id, key.description[:50] if key.description else "-",
                          f.status.value, key.key_manager, round(key.monthly_cost, 2), f.recommendation])


def _create_ecr_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("ECR")
    ws.append(["Account", "Region", "Repository", "상태", "이미지 수", "오래된 이미지", "총 크기", "낭비 비용", "Lifecycle", "권장 조치"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                repo = f.repo
                ws.append([repo.account_name, repo.region, repo.name, f.status.value,
                          repo.image_count, repo.old_image_count, f"{repo.total_size_gb:.2f} GB",
                          f"${repo.old_images_monthly_cost:.2f}", "있음" if repo.has_lifecycle_policy else "없음",
                          f.recommendation])


def _create_route53_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("Route53")
    ws.append(["Account", "Zone ID", "Domain", "Type", "상태", "레코드 수", "월간 비용", "권장 조치"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                zone = f.zone
                ws.append([zone.account_name, zone.zone_id, zone.name, "Private" if zone.is_private else "Public",
                          f.status.value, zone.record_count, f"${zone.monthly_cost:.2f}", f.recommendation])


def _create_s3_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("S3")
    ws.append(["Account", "Bucket", "Region", "상태", "객체 수", "크기", "버전관리", "Lifecycle", "권장 조치"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                bucket = f.bucket
                ws.append([bucket.account_name, bucket.name, bucket.region, f.status.value,
                          bucket.object_count, f"{bucket.total_size_mb:.2f} MB",
                          "Enabled" if bucket.versioning_enabled else "Disabled",
                          "있음" if bucket.has_lifecycle else "없음", f.recommendation])


def _create_lambda_sheet(wb, results, header_fill, header_font):
    ws = wb.create_sheet("Lambda")
    ws.append(["Account", "Region", "Function Name", "Runtime", "Memory (MB)", "상태", "월간 낭비", "권장 조치"])
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                fn = f.function
                ws.append([fn.account_name, fn.region, fn.function_name, fn.runtime,
                          fn.memory_mb, f.status.value,
                          f"${f.monthly_waste:.2f}" if f.monthly_waste > 0 else "-",
                          f.recommendation])
