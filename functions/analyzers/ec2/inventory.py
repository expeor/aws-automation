"""
plugins/ec2/inventory.py - EC2 인벤토리 조회 (스트리밍 방식)

EC2 인스턴스 및 Security Group 현황 조회.
메모리 효율적인 스트리밍 처리 - 수집 → 쓰기 → 해제 순환.

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table

from core.shared.aws.inventory import InventoryCollector
from core.shared.io.excel import ColumnDef, Workbook
from core.shared.io.output import OutputPath, open_in_explorer

if TYPE_CHECKING:
    from core.cli.flow.context import ExecutionContext

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
    state_counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def run(ctx: ExecutionContext) -> None:
    """EC2 인벤토리 조회 (스트리밍 방식)"""
    console.print("\n[bold]EC2 인벤토리[/bold]\n")

    collector = InventoryCollector(ctx)
    output_dir = OutputPath(ctx.profile_name or "default").sub("ec2", "inventory").with_date("daily").build()
    wb = Workbook()
    stats = Stats()

    # =========================================================================
    # 리소스 정의
    # =========================================================================
    resources = [
        ResourceDef(
            name="EC2 인스턴스",
            sheet_name="EC2 Instances",
            method="collect_ec2",
            columns=[
                ColumnDef("Account ID", width=15),
                ColumnDef("Account Name", width=20),
                ColumnDef("Region", width=15),
                ColumnDef("Instance ID", width=20),
                ColumnDef("Name", width=30),
                ColumnDef("Type", width=15),
                ColumnDef("State", width=12),
                ColumnDef("Private IP", width=15),
                ColumnDef("Public IP", width=15),
                ColumnDef("VPC ID", width=20),
                ColumnDef("Platform", width=15),
            ],
            row_mapper=lambda i: [
                i.account_id,
                i.account_name,
                i.region,
                i.instance_id,
                i.name,
                i.instance_type,
                i.state,
                i.private_ip,
                i.public_ip,
                i.vpc_id,
                i.platform,
            ],
        ),
        ResourceDef(
            name="Security Group",
            sheet_name="Security Groups",
            method="collect_security_groups",
            columns=[
                ColumnDef("Account ID", width=15),
                ColumnDef("Account Name", width=20),
                ColumnDef("Region", width=15),
                ColumnDef("Group ID", width=22),
                ColumnDef("Group Name", width=30),
                ColumnDef("VPC ID", width=20),
                ColumnDef("Description", width=40),
                ColumnDef("Inbound Rules", width=12),
                ColumnDef("Outbound Rules", width=12),
            ],
            row_mapper=lambda sg: [
                sg.account_id,
                sg.account_name,
                sg.region,
                sg.group_id,
                sg.group_name,
                sg.vpc_id,
                sg.description[:50] + "..." if len(sg.description) > 50 else sg.description,
                len(sg.inbound_rules),
                len(sg.outbound_rules),
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

                # EC2 상태별 통계 수집
                if res_def.name == "EC2 인스턴스":
                    for inst in data:
                        stats.state_counts[inst.state] = stats.state_counts.get(inst.state, 0) + 1
                    stopped = sum(1 for i in data if i.state == "stopped")
                    if stopped > 0:
                        stats.warnings.append(f"Stopped 인스턴스: {stopped}개")

                # SG 공개 접근 경고
                if res_def.name == "Security Group":
                    public_sgs = sum(1 for sg in data if sg.has_public_access)
                    if public_sgs > 0:
                        stats.warnings.append(f"0.0.0.0/0 허용 SG: {public_sgs}개")

            # 메모리 해제
            del data

        console.print(f"[dim]  {res_def.name}: {count:,}개[/dim]")

    # =========================================================================
    # 콘솔 출력
    # =========================================================================
    console.print()
    for name, count in stats.counts.items():
        console.print(f"총 {name}: [green]{count:,}[/green]개")

    if stats.state_counts:
        console.print()
        table = Table(title="EC2 상태별 현황")
        table.add_column("상태", style="cyan")
        table.add_column("수량", justify="right", style="green")
        for state, count in sorted(stats.state_counts.items()):
            table.add_row(state, str(count))
        console.print(table)

    for warning in stats.warnings:
        console.print(f"[yellow]  ⚠ {warning}[/yellow]")

    # =========================================================================
    # 저장
    # =========================================================================
    total = sum(stats.counts.values())
    if total > 0:
        filepath = wb.save_as(output_dir, "ec2_inventory")
        console.print(f"\n[green]엑셀 저장 완료:[/green] {filepath}")
        open_in_explorer(output_dir)
    else:
        console.print("\n[yellow]수집된 리소스가 없습니다.[/yellow]")
