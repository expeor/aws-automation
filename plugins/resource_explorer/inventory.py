"""
plugins/resource_explorer/inventory.py - 종합 인벤토리 조회 (스트리밍 방식)

60개 리소스 타입을 카테고리별로 수집하여 즉시 Excel에 기록.
메모리 효율적인 스트리밍 처리 - 수집 → 쓰기 → 해제 순환.

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from rich.console import Console
from rich.table import Table

from core.tools.io.excel import ColumnDef, Workbook
from core.tools.output import OutputPath, open_in_explorer

from .common import InventoryCollector

console = Console()


@dataclass
class ResourceDef:
    """리소스 수집 정의"""

    name: str  # 표시명
    method: str  # collector 메서드명
    columns: list[ColumnDef]
    row_mapper: Callable  # 데이터 → 행 변환 함수


@dataclass
class CategoryDef:
    """카테고리 정의"""

    name: str
    resources: list[ResourceDef]


@dataclass
class CategoryStats:
    """카테고리별 통계"""

    name: str
    counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def run(ctx) -> None:
    """종합 리소스 인벤토리 조회 (스트리밍 방식)"""
    console.print("\n[bold]AWS 종합 리소스 인벤토리[/bold]\n")

    collector = InventoryCollector(ctx)

    # Excel 워크북 먼저 생성
    output_dir = OutputPath(ctx.profile_name or "default").sub("resource_explorer").with_date("daily").build()
    wb = Workbook()

    # 전체 통계 수집용
    all_stats: list[CategoryStats] = []
    total_resources = 0

    # =========================================================================
    # 카테고리별 리소스 정의
    # =========================================================================
    categories = _define_categories()

    # =========================================================================
    # 스트리밍 처리: 카테고리별로 수집 → Excel 쓰기 → 메모리 해제
    # =========================================================================
    for category in categories:
        stats = CategoryStats(name=category.name)

        for res_def in category.resources:
            with console.status(f"[yellow]{res_def.name} 수집 중...[/yellow]"):
                # 수집
                method = getattr(collector, res_def.method)
                data = method()
                count = len(data)
                stats.counts[res_def.name] = count
                total_resources += count

                # Excel 쓰기 (데이터가 있을 때만)
                if data:
                    sheet = wb.new_sheet(res_def.name, res_def.columns)
                    for item in data:
                        sheet.add_row(res_def.row_mapper(item))

                    # 특수 경고 수집
                    _collect_warnings(res_def.name, data, stats)

                # 메모리 해제
                del data

        all_stats.append(stats)
        console.print(f"[dim]  {category.name}: {sum(stats.counts.values()):,}개 수집 완료[/dim]")

    # =========================================================================
    # 콘솔 출력
    # =========================================================================
    console.print()
    for stats in all_stats:
        table = Table(title=stats.name)
        table.add_column("리소스", style="cyan")
        table.add_column("수량", justify="right", style="green")
        for name, count in stats.counts.items():
            table.add_row(name, f"{count:,}")
        console.print(table)

        # 경고 출력
        for warning in stats.warnings:
            console.print(f"[yellow]  ⚠ {warning}[/yellow]")

    console.print(f"\n[bold green]총 리소스: {total_resources:,}개[/bold green]")

    if total_resources == 0:
        console.print("\n[yellow]수집된 리소스가 없습니다.[/yellow]")
        return

    # =========================================================================
    # Summary Sheet 생성 (맨 앞에 삽입)
    # =========================================================================
    summary = wb.new_summary_sheet("요약", "Summary", position=0)
    summary.add_title("AWS 종합 리소스 인벤토리")

    summary.add_section("수집 정보")
    summary.add_item("프로파일", ctx.profile_name or "default")
    summary.add_item("리전", ", ".join(ctx.regions) if hasattr(ctx, "regions") and ctx.regions else "N/A")
    summary.add_item("수집 일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    summary.add_item("총 리소스", f"{total_resources:,}개", highlight="info")

    for stats in all_stats:
        summary.add_blank_row()
        summary.add_section(stats.name)
        for name, count in stats.counts.items():
            summary.add_item(name, f"{count:,}개")
        for warning in stats.warnings:
            summary.add_item("  ⚠", warning, highlight="warning")

    # 저장
    filepath = wb.save_as(output_dir, "comprehensive_inventory")
    console.print(f"\n[green]엑셀 저장 완료:[/green] {filepath}")
    open_in_explorer(output_dir)


def _collect_warnings(resource_name: str, data: list, stats: CategoryStats) -> None:
    """리소스별 경고 수집"""
    if resource_name == "Elastic IP":
        unattached = len([e for e in data if not e.is_attached])
        if unattached > 0:
            stats.warnings.append(f"미연결 EIP: {unattached}개")

    elif resource_name == "EBS Volume":
        unattached = len([v for v in data if not v.instance_id])
        if unattached > 0:
            stats.warnings.append(f"미연결 Volume: {unattached}개")

    elif resource_name == "Security Group":
        public_sgs = len([sg for sg in data if sg.has_public_access])
        if public_sgs > 0:
            stats.warnings.append(f"0.0.0.0/0 허용 SG: {public_sgs}개")

    elif resource_name == "EC2 Instance":
        stopped = len([i for i in data if i.state == "stopped"])
        if stopped > 0:
            stats.warnings.append(f"Stopped 인스턴스: {stopped}개")

    elif resource_name == "IAM User":
        no_mfa = len([u for u in data if not u.mfa_enabled and u.has_console_access])
        if no_mfa > 0:
            stats.warnings.append(f"MFA 미설정 사용자: {no_mfa}개")

    elif resource_name == "ACM Certificate":
        expiring = len([c for c in data if c.not_after and (c.not_after - datetime.now(c.not_after.tzinfo)).days < 30])
        if expiring > 0:
            stats.warnings.append(f"30일 내 만료 인증서: {expiring}개")


def _define_categories() -> list[CategoryDef]:
    """60개 리소스 타입의 카테고리 정의"""

    return [
        # =====================================================================
        # Network (Basic) - 8개
        # =====================================================================
        CategoryDef(
            name="Network (Basic)",
            resources=[
                ResourceDef(
                    name="VPC",
                    method="collect_vpcs",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("VPC ID", width=22), ColumnDef("Name", width=25),
                        ColumnDef("CIDR", width=18), ColumnDef("State", width=12),
                        ColumnDef("Default", width=8), ColumnDef("Tenancy", width=12),
                    ],
                    row_mapper=lambda v: [v.account_id, v.region, v.vpc_id, v.name, v.cidr_block,
                                          v.state, "Yes" if v.is_default else "No", v.instance_tenancy],
                ),
                ResourceDef(
                    name="Subnet",
                    method="collect_subnets",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Subnet ID", width=25), ColumnDef("Name", width=25),
                        ColumnDef("VPC ID", width=22), ColumnDef("CIDR", width=18),
                        ColumnDef("AZ", width=15), ColumnDef("Available IPs", width=12),
                    ],
                    row_mapper=lambda s: [s.account_id, s.region, s.subnet_id, s.name, s.vpc_id,
                                          s.cidr_block, s.availability_zone, s.available_ip_count],
                ),
                ResourceDef(
                    name="Route Table",
                    method="collect_route_tables",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Route Table ID", width=25), ColumnDef("Name", width=25),
                        ColumnDef("VPC ID", width=22), ColumnDef("Main", width=8),
                        ColumnDef("Routes", width=8), ColumnDef("Associations", width=12),
                    ],
                    row_mapper=lambda rt: [rt.account_id, rt.region, rt.route_table_id, rt.name,
                                           rt.vpc_id, "Yes" if rt.is_main else "No", rt.route_count, rt.association_count],
                ),
                ResourceDef(
                    name="Internet Gateway",
                    method="collect_internet_gateways",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("IGW ID", width=25), ColumnDef("Name", width=25),
                        ColumnDef("VPC ID", width=22), ColumnDef("State", width=12),
                    ],
                    row_mapper=lambda igw: [igw.account_id, igw.region, igw.igw_id, igw.name, igw.vpc_id, igw.state],
                ),
                ResourceDef(
                    name="Elastic IP",
                    method="collect_elastic_ips",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Allocation ID", width=25), ColumnDef("Public IP", width=15),
                        ColumnDef("Name", width=20), ColumnDef("Instance ID", width=20),
                        ColumnDef("Attached", width=10),
                    ],
                    row_mapper=lambda eip: [eip.account_id, eip.region, eip.allocation_id, eip.public_ip,
                                            eip.name, eip.instance_id, "Yes" if eip.is_attached else "No"],
                ),
                ResourceDef(
                    name="ENI",
                    method="collect_enis",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("ENI ID", width=22), ColumnDef("Status", width=12),
                        ColumnDef("Type", width=15), ColumnDef("Private IP", width=15),
                        ColumnDef("VPC ID", width=22), ColumnDef("Connected Type", width=15),
                    ],
                    row_mapper=lambda eni: [eni.account_id, eni.region, eni.eni_id, eni.status,
                                            eni.interface_type, eni.private_ip, eni.vpc_id, eni.connected_resource_type],
                ),
                ResourceDef(
                    name="NAT Gateway",
                    method="collect_nat_gateways",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("NAT Gateway ID", width=22), ColumnDef("Name", width=20),
                        ColumnDef("State", width=12), ColumnDef("Type", width=10),
                        ColumnDef("Public IP", width=15), ColumnDef("VPC ID", width=22),
                    ],
                    row_mapper=lambda nat: [nat.account_id, nat.region, nat.nat_gateway_id, nat.name,
                                            nat.state, nat.connectivity_type, nat.public_ip, nat.vpc_id],
                ),
                ResourceDef(
                    name="VPC Endpoint",
                    method="collect_vpc_endpoints",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Endpoint ID", width=25), ColumnDef("Type", width=12),
                        ColumnDef("State", width=12), ColumnDef("Service", width=40),
                        ColumnDef("VPC ID", width=22),
                    ],
                    row_mapper=lambda ep: [ep.account_id, ep.region, ep.endpoint_id, ep.endpoint_type,
                                           ep.state, ep.service_name, ep.vpc_id],
                ),
            ],
        ),
        # =====================================================================
        # Network (Advanced) - 6개
        # =====================================================================
        CategoryDef(
            name="Network (Advanced)",
            resources=[
                ResourceDef(
                    name="Transit Gateway",
                    method="collect_transit_gateways",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("TGW ID", width=25), ColumnDef("Name", width=25),
                        ColumnDef("State", width=12), ColumnDef("ASN", width=12),
                    ],
                    row_mapper=lambda tgw: [tgw.account_id, tgw.region, tgw.tgw_id, tgw.name,
                                            tgw.state, tgw.amazon_side_asn],
                ),
                ResourceDef(
                    name="TGW Attachment",
                    method="collect_transit_gateway_attachments",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Attachment ID", width=25), ColumnDef("TGW ID", width=25),
                        ColumnDef("Resource Type", width=15), ColumnDef("Resource ID", width=25),
                        ColumnDef("State", width=12),
                    ],
                    row_mapper=lambda att: [att.account_id, att.region, att.attachment_id, att.tgw_id,
                                            att.resource_type, att.resource_id, att.state],
                ),
                ResourceDef(
                    name="VPN Gateway",
                    method="collect_vpn_gateways",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("VPN Gateway ID", width=25), ColumnDef("Name", width=25),
                        ColumnDef("State", width=12), ColumnDef("Type", width=12),
                    ],
                    row_mapper=lambda vgw: [vgw.account_id, vgw.region, vgw.vpn_gateway_id, vgw.name,
                                            vgw.state, vgw.vpn_type],
                ),
                ResourceDef(
                    name="VPN Connection",
                    method="collect_vpn_connections",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("VPN Connection ID", width=25), ColumnDef("Name", width=25),
                        ColumnDef("State", width=12), ColumnDef("CGW ID", width=22),
                    ],
                    row_mapper=lambda vpn: [vpn.account_id, vpn.region, vpn.vpn_connection_id, vpn.name,
                                            vpn.state, vpn.customer_gateway_id],
                ),
                ResourceDef(
                    name="Network ACL",
                    method="collect_network_acls",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("NACL ID", width=25), ColumnDef("Name", width=25),
                        ColumnDef("VPC ID", width=22), ColumnDef("Default", width=8),
                        ColumnDef("Inbound Rules", width=12), ColumnDef("Outbound Rules", width=12),
                    ],
                    row_mapper=lambda nacl: [nacl.account_id, nacl.region, nacl.nacl_id, nacl.name,
                                             nacl.vpc_id, "Yes" if nacl.is_default else "No",
                                             nacl.inbound_rule_count, nacl.outbound_rule_count],
                ),
                ResourceDef(
                    name="VPC Peering",
                    method="collect_vpc_peering_connections",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Peering ID", width=25), ColumnDef("Status", width=12),
                        ColumnDef("Requester VPC", width=22), ColumnDef("Accepter VPC", width=22),
                    ],
                    row_mapper=lambda pcx: [pcx.account_id, pcx.region, pcx.peering_id, pcx.status,
                                            pcx.requester_vpc_id, pcx.accepter_vpc_id],
                ),
            ],
        ),
        # =====================================================================
        # Compute - 11개
        # =====================================================================
        CategoryDef(
            name="Compute",
            resources=[
                ResourceDef(
                    name="EC2 Instance",
                    method="collect_ec2",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Instance ID", width=20), ColumnDef("Name", width=25),
                        ColumnDef("Type", width=12), ColumnDef("State", width=10),
                        ColumnDef("Private IP", width=15), ColumnDef("Public IP", width=15),
                    ],
                    row_mapper=lambda i: [i.account_id, i.region, i.instance_id, i.name, i.instance_type,
                                          i.state, i.private_ip, i.public_ip],
                ),
                ResourceDef(
                    name="EBS Volume",
                    method="collect_ebs_volumes",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Volume ID", width=22), ColumnDef("Name", width=20),
                        ColumnDef("Size (GB)", width=10), ColumnDef("Type", width=10),
                        ColumnDef("State", width=12), ColumnDef("Instance ID", width=20),
                    ],
                    row_mapper=lambda v: [v.account_id, v.region, v.volume_id, v.name, v.size_gb,
                                          v.volume_type, v.state, v.instance_id],
                ),
                ResourceDef(
                    name="Lambda Function",
                    method="collect_lambda_functions",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Function Name", width=30), ColumnDef("Runtime", width=15),
                        ColumnDef("Memory", width=10), ColumnDef("Timeout", width=10),
                    ],
                    row_mapper=lambda fn: [fn.account_id, fn.region, fn.function_name, fn.runtime,
                                           fn.memory_size, fn.timeout],
                ),
                ResourceDef(
                    name="ECS Cluster",
                    method="collect_ecs_clusters",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Cluster Name", width=30), ColumnDef("Status", width=12),
                        ColumnDef("Running Tasks", width=12), ColumnDef("Services", width=10),
                    ],
                    row_mapper=lambda c: [c.account_id, c.region, c.cluster_name, c.status,
                                          c.running_tasks_count, c.active_services_count],
                ),
                ResourceDef(
                    name="ECS Service",
                    method="collect_ecs_services",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Service Name", width=30), ColumnDef("Status", width=12),
                        ColumnDef("Desired", width=10), ColumnDef("Running", width=10),
                    ],
                    row_mapper=lambda s: [s.account_id, s.region, s.service_name, s.status,
                                          s.desired_count, s.running_count],
                ),
                ResourceDef(
                    name="Auto Scaling Group",
                    method="collect_auto_scaling_groups",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("ASG Name", width=30), ColumnDef("Min", width=6),
                        ColumnDef("Max", width=6), ColumnDef("Desired", width=8),
                        ColumnDef("Current", width=8),
                    ],
                    row_mapper=lambda asg: [asg.account_id, asg.region, asg.asg_name, asg.min_size,
                                            asg.max_size, asg.desired_capacity, asg.current_capacity],
                ),
                ResourceDef(
                    name="Launch Template",
                    method="collect_launch_templates",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Template ID", width=22), ColumnDef("Name", width=25),
                        ColumnDef("Version", width=10), ColumnDef("Instance Type", width=15),
                    ],
                    row_mapper=lambda lt: [lt.account_id, lt.region, lt.template_id, lt.template_name,
                                           lt.latest_version, lt.instance_type],
                ),
                ResourceDef(
                    name="EKS Cluster",
                    method="collect_eks_clusters",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Cluster Name", width=25), ColumnDef("Status", width=12),
                        ColumnDef("Version", width=10), ColumnDef("VPC ID", width=22),
                    ],
                    row_mapper=lambda eks: [eks.account_id, eks.region, eks.cluster_name, eks.status,
                                            eks.version, eks.vpc_id],
                ),
                ResourceDef(
                    name="EKS Node Group",
                    method="collect_eks_node_groups",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Cluster", width=20), ColumnDef("Node Group", width=25),
                        ColumnDef("Status", width=12), ColumnDef("Desired", width=8),
                    ],
                    row_mapper=lambda ng: [ng.account_id, ng.region, ng.cluster_name, ng.nodegroup_name,
                                           ng.status, ng.scaling_desired],
                ),
                ResourceDef(
                    name="AMI",
                    method="collect_amis",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Image ID", width=22), ColumnDef("Name", width=40),
                        ColumnDef("State", width=12), ColumnDef("Architecture", width=12),
                    ],
                    row_mapper=lambda ami: [ami.account_id, ami.region, ami.image_id, ami.name,
                                            ami.state, ami.architecture],
                ),
                ResourceDef(
                    name="Snapshot",
                    method="collect_snapshots",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Snapshot ID", width=22), ColumnDef("Volume ID", width=22),
                        ColumnDef("Size (GB)", width=10), ColumnDef("State", width=12),
                    ],
                    row_mapper=lambda snap: [snap.account_id, snap.region, snap.snapshot_id, snap.volume_id,
                                             snap.volume_size, snap.state],
                ),
            ],
        ),
        # =====================================================================
        # Database/Storage - 8개
        # =====================================================================
        CategoryDef(
            name="Database/Storage",
            resources=[
                ResourceDef(
                    name="RDS Instance",
                    method="collect_rds_instances",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("DB Instance ID", width=25), ColumnDef("Class", width=15),
                        ColumnDef("Engine", width=12), ColumnDef("Status", width=12),
                        ColumnDef("Multi-AZ", width=10),
                    ],
                    row_mapper=lambda db: [db.account_id, db.region, db.db_instance_id, db.db_instance_class,
                                           db.engine, db.status, "Yes" if db.multi_az else "No"],
                ),
                ResourceDef(
                    name="RDS Cluster",
                    method="collect_rds_clusters",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Cluster ID", width=25), ColumnDef("Engine", width=15),
                        ColumnDef("Status", width=12), ColumnDef("Members", width=10),
                    ],
                    row_mapper=lambda c: [c.account_id, c.region, c.cluster_id, c.engine,
                                          c.status, c.db_cluster_members],
                ),
                ResourceDef(
                    name="S3 Bucket",
                    method="collect_s3_buckets",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Bucket Name", width=40), ColumnDef("Versioning", width=12),
                        ColumnDef("Encryption", width=12), ColumnDef("Public Block", width=12),
                    ],
                    row_mapper=lambda b: [b.account_id, b.region, b.bucket_name, b.versioning_status,
                                          b.encryption_type, "Yes" if b.public_access_block else "No"],
                ),
                ResourceDef(
                    name="DynamoDB Table",
                    method="collect_dynamodb_tables",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Table Name", width=30), ColumnDef("Status", width=12),
                        ColumnDef("Billing Mode", width=12), ColumnDef("Items", width=12),
                    ],
                    row_mapper=lambda t: [t.account_id, t.region, t.table_name, t.status,
                                          t.billing_mode, t.item_count],
                ),
                ResourceDef(
                    name="ElastiCache Cluster",
                    method="collect_elasticache_clusters",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Cluster ID", width=25), ColumnDef("Engine", width=10),
                        ColumnDef("Node Type", width=18), ColumnDef("Status", width=12),
                    ],
                    row_mapper=lambda c: [c.account_id, c.region, c.cluster_id, c.engine,
                                          c.node_type, c.status],
                ),
                ResourceDef(
                    name="Redshift Cluster",
                    method="collect_redshift_clusters",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Cluster ID", width=25), ColumnDef("Node Type", width=15),
                        ColumnDef("Status", width=12), ColumnDef("Nodes", width=8),
                    ],
                    row_mapper=lambda c: [c.account_id, c.region, c.cluster_id, c.node_type,
                                          c.cluster_status, c.number_of_nodes],
                ),
                ResourceDef(
                    name="EFS File System",
                    method="collect_efs_file_systems",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("File System ID", width=22), ColumnDef("Name", width=25),
                        ColumnDef("State", width=12), ColumnDef("Performance", width=15),
                    ],
                    row_mapper=lambda fs: [fs.account_id, fs.region, fs.file_system_id, fs.name,
                                           fs.life_cycle_state, fs.performance_mode],
                ),
                ResourceDef(
                    name="FSx File System",
                    method="collect_fsx_file_systems",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("File System ID", width=22), ColumnDef("Type", width=15),
                        ColumnDef("Lifecycle", width=12), ColumnDef("Storage (GB)", width=12),
                    ],
                    row_mapper=lambda fs: [fs.account_id, fs.region, fs.file_system_id, fs.file_system_type,
                                           fs.lifecycle, fs.storage_capacity],
                ),
            ],
        ),
        # =====================================================================
        # Security - 8개
        # =====================================================================
        CategoryDef(
            name="Security",
            resources=[
                ResourceDef(
                    name="Security Group",
                    method="collect_security_groups",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Group ID", width=22), ColumnDef("Name", width=25),
                        ColumnDef("VPC ID", width=22), ColumnDef("Rules", width=8),
                        ColumnDef("Public", width=8),
                    ],
                    row_mapper=lambda sg: [sg.account_id, sg.region, sg.group_id, sg.group_name,
                                           sg.vpc_id, sg.rule_count, "Yes" if sg.has_public_access else "No"],
                ),
                ResourceDef(
                    name="KMS Key",
                    method="collect_kms_keys",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Key ID", width=38), ColumnDef("Alias", width=30),
                        ColumnDef("State", width=12), ColumnDef("Manager", width=10),
                    ],
                    row_mapper=lambda k: [k.account_id, k.region, k.key_id, k.alias,
                                          k.key_state, k.key_manager],
                ),
                ResourceDef(
                    name="Secret",
                    method="collect_secrets",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Secret Name", width=40), ColumnDef("Rotation", width=10),
                    ],
                    row_mapper=lambda s: [s.account_id, s.region, s.name, "Yes" if s.rotation_enabled else "No"],
                ),
                ResourceDef(
                    name="IAM Role",
                    method="collect_iam_roles",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Role Name", width=40),
                        ColumnDef("Path", width=15), ColumnDef("Attached Policies", width=15),
                        ColumnDef("Last Used", width=20),
                    ],
                    row_mapper=lambda r: [r.account_id, r.role_name, r.path, r.attached_policies_count,
                                          str(r.last_used_date) if r.last_used_date else "Never"],
                ),
                ResourceDef(
                    name="IAM User",
                    method="collect_iam_users",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("User Name", width=30),
                        ColumnDef("Console", width=10), ColumnDef("Access Keys", width=12),
                        ColumnDef("MFA", width=8),
                    ],
                    row_mapper=lambda u: [u.account_id, u.user_name, "Yes" if u.has_console_access else "No",
                                          u.access_key_count, "Yes" if u.mfa_enabled else "No"],
                ),
                ResourceDef(
                    name="IAM Policy",
                    method="collect_iam_policies",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Policy Name", width=40),
                        ColumnDef("Path", width=15), ColumnDef("Attachments", width=12),
                    ],
                    row_mapper=lambda p: [p.account_id, p.policy_name, p.path, p.attachment_count],
                ),
                ResourceDef(
                    name="ACM Certificate",
                    method="collect_acm_certificates",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Domain Name", width=40), ColumnDef("Status", width=12),
                        ColumnDef("Type", width=12), ColumnDef("In Use", width=8),
                    ],
                    row_mapper=lambda c: [c.account_id, c.region, c.domain_name, c.status,
                                          c.certificate_type, len(c.in_use_by)],
                ),
                ResourceDef(
                    name="WAF WebACL",
                    method="collect_waf_web_acls",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Name", width=30), ColumnDef("Scope", width=12),
                        ColumnDef("Rules", width=8), ColumnDef("Default Action", width=12),
                    ],
                    row_mapper=lambda w: [w.account_id, w.region, w.name, w.scope,
                                          w.rule_count, w.default_action],
                ),
            ],
        ),
        # =====================================================================
        # CDN/DNS - 2개
        # =====================================================================
        CategoryDef(
            name="CDN/DNS",
            resources=[
                ResourceDef(
                    name="CloudFront Distribution",
                    method="collect_cloudfront_distributions",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Distribution ID", width=16),
                        ColumnDef("Domain Name", width=40), ColumnDef("Status", width=12),
                        ColumnDef("Enabled", width=10), ColumnDef("Origins", width=8),
                    ],
                    row_mapper=lambda d: [d.account_id, d.distribution_id, d.domain_name, d.status,
                                          "Yes" if d.enabled else "No", d.origin_count],
                ),
                ResourceDef(
                    name="Route53 Hosted Zone",
                    method="collect_route53_hosted_zones",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Zone ID", width=16),
                        ColumnDef("Name", width=35), ColumnDef("Records", width=10),
                        ColumnDef("Private", width=10),
                    ],
                    row_mapper=lambda z: [z.account_id, z.zone_id, z.name, z.record_count,
                                          "Yes" if z.is_private else "No"],
                ),
            ],
        ),
        # =====================================================================
        # Load Balancing - 2개
        # =====================================================================
        CategoryDef(
            name="Load Balancing",
            resources=[
                ResourceDef(
                    name="Load Balancer",
                    method="collect_load_balancers",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Name", width=30), ColumnDef("Type", width=12),
                        ColumnDef("Scheme", width=12), ColumnDef("State", width=10),
                    ],
                    row_mapper=lambda lb: [lb.account_id, lb.region, lb.name, lb.lb_type,
                                           lb.scheme, lb.state],
                ),
                ResourceDef(
                    name="Target Group",
                    method="collect_target_groups",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Name", width=30), ColumnDef("Type", width=10),
                        ColumnDef("Protocol", width=10), ColumnDef("Healthy", width=8),
                    ],
                    row_mapper=lambda tg: [tg.account_id, tg.region, tg.name, tg.target_type,
                                           tg.protocol, tg.healthy_targets],
                ),
            ],
        ),
        # =====================================================================
        # Integration/Messaging - 5개
        # =====================================================================
        CategoryDef(
            name="Integration/Messaging",
            resources=[
                ResourceDef(
                    name="SNS Topic",
                    method="collect_sns_topics",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Topic Name", width=40), ColumnDef("Subscriptions", width=12),
                        ColumnDef("FIFO", width=8),
                    ],
                    row_mapper=lambda t: [t.account_id, t.region, t.name, t.subscriptions_confirmed,
                                          "Yes" if t.fifo_topic else "No"],
                ),
                ResourceDef(
                    name="SQS Queue",
                    method="collect_sqs_queues",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Queue Name", width=40), ColumnDef("Messages", width=12),
                        ColumnDef("FIFO", width=8),
                    ],
                    row_mapper=lambda q: [q.account_id, q.region, q.name, q.approximate_number_of_messages,
                                          "Yes" if q.fifo_queue else "No"],
                ),
                ResourceDef(
                    name="EventBridge Rule",
                    method="collect_eventbridge_rules",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Rule Name", width=35), ColumnDef("Event Bus", width=20),
                        ColumnDef("State", width=10), ColumnDef("Targets", width=8),
                    ],
                    row_mapper=lambda r: [r.account_id, r.region, r.rule_name, r.event_bus_name,
                                          r.state, r.target_count],
                ),
                ResourceDef(
                    name="Step Function",
                    method="collect_step_functions",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Name", width=35), ColumnDef("Type", width=12),
                        ColumnDef("Status", width=12),
                    ],
                    row_mapper=lambda sf: [sf.account_id, sf.region, sf.name, sf.state_machine_type, sf.status],
                ),
                ResourceDef(
                    name="API Gateway API",
                    method="collect_api_gateway_apis",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("API ID", width=15), ColumnDef("Name", width=30),
                        ColumnDef("Type", width=10), ColumnDef("Endpoint", width=12),
                    ],
                    row_mapper=lambda api: [api.account_id, api.region, api.api_id, api.name,
                                            api.api_type, api.endpoint_type],
                ),
            ],
        ),
        # =====================================================================
        # Monitoring - 2개
        # =====================================================================
        CategoryDef(
            name="Monitoring",
            resources=[
                ResourceDef(
                    name="CloudWatch Alarm",
                    method="collect_cloudwatch_alarms",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Alarm Name", width=35), ColumnDef("State", width=10),
                        ColumnDef("Metric", width=25), ColumnDef("Namespace", width=20),
                    ],
                    row_mapper=lambda a: [a.account_id, a.region, a.alarm_name, a.state_value,
                                          a.metric_name, a.namespace],
                ),
                ResourceDef(
                    name="CloudWatch Log Group",
                    method="collect_cloudwatch_log_groups",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Log Group Name", width=50), ColumnDef("Retention", width=12),
                        ColumnDef("Stored Bytes", width=15),
                    ],
                    row_mapper=lambda lg: [lg.account_id, lg.region, lg.log_group_name,
                                           lg.retention_in_days or "Never", lg.stored_bytes],
                ),
            ],
        ),
        # =====================================================================
        # Analytics - 3개
        # =====================================================================
        CategoryDef(
            name="Analytics",
            resources=[
                ResourceDef(
                    name="Kinesis Stream",
                    method="collect_kinesis_streams",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Stream Name", width=35), ColumnDef("Status", width=12),
                        ColumnDef("Shards", width=8), ColumnDef("Retention (hrs)", width=14),
                    ],
                    row_mapper=lambda s: [s.account_id, s.region, s.stream_name, s.status,
                                          s.shard_count, s.retention_period_hours],
                ),
                ResourceDef(
                    name="Kinesis Firehose",
                    method="collect_kinesis_firehoses",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Stream Name", width=35), ColumnDef("Status", width=12),
                        ColumnDef("Source", width=15), ColumnDef("Destination", width=15),
                    ],
                    row_mapper=lambda f: [f.account_id, f.region, f.delivery_stream_name,
                                          f.delivery_stream_status, f.source_type, f.destination_type],
                ),
                ResourceDef(
                    name="Glue Database",
                    method="collect_glue_databases",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Database Name", width=35), ColumnDef("Catalog ID", width=15),
                        ColumnDef("Tables", width=10),
                    ],
                    row_mapper=lambda db: [db.account_id, db.region, db.database_name,
                                           db.catalog_id, db.table_count],
                ),
            ],
        ),
        # =====================================================================
        # DevOps - 3개
        # =====================================================================
        CategoryDef(
            name="DevOps",
            resources=[
                ResourceDef(
                    name="CloudFormation Stack",
                    method="collect_cloudformation_stacks",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Stack Name", width=35), ColumnDef("Status", width=20),
                        ColumnDef("Drift", width=15),
                    ],
                    row_mapper=lambda s: [s.account_id, s.region, s.stack_name, s.stack_status, s.drift_status],
                ),
                ResourceDef(
                    name="CodePipeline",
                    method="collect_codepipelines",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Pipeline Name", width=35), ColumnDef("Version", width=10),
                        ColumnDef("Stages", width=8),
                    ],
                    row_mapper=lambda p: [p.account_id, p.region, p.pipeline_name, p.pipeline_version, p.stage_count],
                ),
                ResourceDef(
                    name="CodeBuild Project",
                    method="collect_codebuild_projects",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Project Name", width=35), ColumnDef("Source Type", width=15),
                        ColumnDef("Compute Type", width=18),
                    ],
                    row_mapper=lambda p: [p.account_id, p.region, p.project_name, p.source_type, p.compute_type],
                ),
            ],
        ),
        # =====================================================================
        # Backup - 2개
        # =====================================================================
        CategoryDef(
            name="Backup",
            resources=[
                ResourceDef(
                    name="Backup Vault",
                    method="collect_backup_vaults",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Vault Name", width=35), ColumnDef("Recovery Points", width=15),
                        ColumnDef("Locked", width=10),
                    ],
                    row_mapper=lambda v: [v.account_id, v.region, v.vault_name, v.number_of_recovery_points,
                                          "Yes" if v.locked else "No"],
                ),
                ResourceDef(
                    name="Backup Plan",
                    method="collect_backup_plans",
                    columns=[
                        ColumnDef("Account ID", width=15), ColumnDef("Region", width=15),
                        ColumnDef("Plan Name", width=35), ColumnDef("Rules", width=8),
                    ],
                    row_mapper=lambda p: [p.account_id, p.region, p.backup_plan_name, p.rule_count],
                ),
            ],
        ),
    ]
