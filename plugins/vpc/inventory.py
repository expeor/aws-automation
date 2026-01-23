"""
plugins/vpc/inventory.py - VPC 리소스 인벤토리 조회 (스트리밍 방식)

ENI, NAT Gateway, VPC Endpoint 현황 조회.
메모리 효율적인 스트리밍 처리 - 수집 → 쓰기 → 해제 순환.

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from rich.console import Console
from rich.table import Table

from core.tools.io.excel import ColumnDef, Workbook
from core.tools.output import OutputPath, open_in_explorer
from plugins.resource_explorer.common import InventoryCollector

console = Console()


@dataclass
class ResourceDef:
    """리소스 수집 정의"""

    name: str
    sheet_name: str
    method: str
    columns: list[ColumnDef]
    row_mapper: Callable


@dataclass
class Stats:
    """수집 통계"""

    counts: dict[str, int] = field(default_factory=dict)
    status_counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def run(ctx) -> None:
    """VPC 리소스 인벤토리 조회 (스트리밍 방식)"""
    console.print("\n[bold]VPC 리소스 인벤토리[/bold]\n")

    collector = InventoryCollector(ctx)
    output_dir = OutputPath(ctx.profile_name or "default").sub("vpc", "inventory").with_date("daily").build()
    wb = Workbook()
    stats = Stats()

    # =========================================================================
    # 리소스 정의
    # =========================================================================
    resources = [
        ResourceDef(
            name="ENI",
            sheet_name="ENIs",
            method="collect_enis",
            columns=[
                ColumnDef("Account ID", width=15),
                ColumnDef("Account Name", width=20),
                ColumnDef("Region", width=15),
                ColumnDef("ENI ID", width=22),
                ColumnDef("Name", width=25),
                ColumnDef("Status", width=12),
                ColumnDef("Type", width=20),
                ColumnDef("Private IP", width=15),
                ColumnDef("Public IP", width=15),
                ColumnDef("VPC ID", width=22),
                ColumnDef("Subnet ID", width=25),
                ColumnDef("Instance ID", width=22),
            ],
            row_mapper=lambda e: [
                e.account_id, e.account_name, e.region, e.eni_id, e.name, e.status,
                e.interface_type, e.private_ip, e.public_ip, e.vpc_id, e.subnet_id, e.instance_id,
            ],
        ),
        ResourceDef(
            name="NAT Gateway",
            sheet_name="NAT Gateways",
            method="collect_nat_gateways",
            columns=[
                ColumnDef("Account ID", width=15),
                ColumnDef("Account Name", width=20),
                ColumnDef("Region", width=15),
                ColumnDef("NAT Gateway ID", width=22),
                ColumnDef("Name", width=25),
                ColumnDef("State", width=12),
                ColumnDef("Type", width=10),
                ColumnDef("Public IP", width=15),
                ColumnDef("Private IP", width=15),
                ColumnDef("VPC ID", width=22),
                ColumnDef("Subnet ID", width=25),
            ],
            row_mapper=lambda n: [
                n.account_id, n.account_name, n.region, n.nat_gateway_id, n.name, n.state,
                n.connectivity_type, n.public_ip, n.private_ip, n.vpc_id, n.subnet_id,
            ],
        ),
        ResourceDef(
            name="VPC Endpoint",
            sheet_name="VPC Endpoints",
            method="collect_vpc_endpoints",
            columns=[
                ColumnDef("Account ID", width=15),
                ColumnDef("Account Name", width=20),
                ColumnDef("Region", width=15),
                ColumnDef("Endpoint ID", width=24),
                ColumnDef("Name", width=25),
                ColumnDef("Type", width=12),
                ColumnDef("State", width=12),
                ColumnDef("Service Name", width=50),
                ColumnDef("VPC ID", width=22),
            ],
            row_mapper=lambda ep: [
                ep.account_id, ep.account_name, ep.region, ep.endpoint_id, ep.name,
                ep.endpoint_type, ep.state, ep.service_name, ep.vpc_id,
            ],
        ),
    ]

    # =========================================================================
    # 스트리밍 처리: 수집 → Excel 쓰기 → 메모리 해제
    # =========================================================================
    for res_def in resources:
        with console.status(f"[yellow]{res_def.name} 수집 중...[/yellow]"):
            method = getattr(collector, res_def.method)
            data = method()
            count = len(data)
            stats.counts[res_def.name] = count

            # Excel 쓰기
            if data:
                sheet = wb.new_sheet(res_def.sheet_name, res_def.columns)
                for item in data:
                    sheet.add_row(res_def.row_mapper(item))

                # ENI 상태별 통계
                if res_def.name == "ENI":
                    for eni in data:
                        stats.status_counts[eni.status] = stats.status_counts.get(eni.status, 0) + 1
                    available = sum(1 for e in data if e.status == "available")
                    if available > 0:
                        stats.warnings.append(f"미연결 ENI: {available}개")

            # 메모리 해제
            del data

        console.print(f"[dim]  {res_def.name}: {count:,}개[/dim]")

    # =========================================================================
    # 콘솔 출력
    # =========================================================================
    console.print()
    for name, count in stats.counts.items():
        console.print(f"총 {name}: [green]{count:,}[/green]개")

    if stats.status_counts:
        console.print()
        table = Table(title="ENI 상태별 현황")
        table.add_column("상태", style="cyan")
        table.add_column("수량", justify="right", style="green")
        for status, count in sorted(stats.status_counts.items()):
            table.add_row(status, str(count))
        console.print(table)

    for warning in stats.warnings:
        console.print(f"[yellow]  ⚠ {warning}[/yellow]")

    # =========================================================================
    # 저장
    # =========================================================================
    total = sum(stats.counts.values())
    if total > 0:
        filepath = wb.save_as(output_dir, "vpc_inventory")
        console.print(f"\n[green]엑셀 저장 완료:[/green] {filepath}")
        open_in_explorer(output_dir)
    else:
        console.print("\n[yellow]수집된 리소스가 없습니다.[/yellow]")
