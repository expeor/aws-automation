"""
plugins/elb/inventory.py - ELB 인벤토리 조회 (스트리밍 방식)

모든 유형의 로드밸런서 및 Target Group 현황 조회.
메모리 효율적인 스트리밍 처리 - 수집 → 쓰기 → 해제 순환.

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.table import Table

from shared.aws.inventory import InventoryCollector
from shared.io.excel import ColumnDef, Workbook
from shared.io.output import OutputPath, open_in_explorer

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

console = Console()


@dataclass
class ResourceDef:
    """리소스 수집 정의"""

    name: str
    sheet_name: str
    method: str
    method_kwargs: dict[str, Any]
    columns: list[ColumnDef]
    row_mapper: Callable


@dataclass
class Stats:
    """수집 통계"""

    counts: dict[str, int] = field(default_factory=dict)
    type_counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def run(ctx: ExecutionContext) -> None:
    """ELB 인벤토리 조회 (스트리밍 방식)"""
    console.print("\n[bold]ELB 인벤토리[/bold]\n")

    collector = InventoryCollector(ctx)
    output_dir = OutputPath(ctx.profile_name or "default").sub("elb", "inventory").with_date("daily").build()
    wb = Workbook()
    stats = Stats()

    # =========================================================================
    # 리소스 정의
    # =========================================================================
    resources = [
        ResourceDef(
            name="Load Balancer",
            sheet_name="Load Balancers",
            method="collect_load_balancers",
            method_kwargs={"include_classic": True},
            columns=[
                ColumnDef("Account ID", width=15),
                ColumnDef("Account Name", width=20),
                ColumnDef("Region", width=15),
                ColumnDef("Name", width=30),
                ColumnDef("Type", width=12),
                ColumnDef("Scheme", width=15),
                ColumnDef("State", width=10),
                ColumnDef("VPC ID", width=22),
                ColumnDef("DNS Name", width=50),
                ColumnDef("Total Targets", width=12),
                ColumnDef("Healthy Targets", width=14),
            ],
            row_mapper=lambda lb: [
                lb.account_id,
                lb.account_name,
                lb.region,
                lb.name,
                lb.lb_type,
                lb.scheme,
                lb.state,
                lb.vpc_id,
                lb.dns_name,
                lb.total_targets,
                lb.healthy_targets,
            ],
        ),
        ResourceDef(
            name="Target Group",
            sheet_name="Target Groups",
            method="collect_target_groups",
            method_kwargs={},
            columns=[
                ColumnDef("Account ID", width=15),
                ColumnDef("Account Name", width=20),
                ColumnDef("Region", width=15),
                ColumnDef("Name", width=30),
                ColumnDef("Target Type", width=12),
                ColumnDef("Protocol", width=10),
                ColumnDef("Port", width=8),
                ColumnDef("VPC ID", width=22),
                ColumnDef("Total Targets", width=12),
                ColumnDef("Healthy", width=10),
                ColumnDef("Unhealthy", width=10),
                ColumnDef("LBs", width=8),
            ],
            row_mapper=lambda tg: [
                tg.account_id,
                tg.account_name,
                tg.region,
                tg.name,
                tg.target_type,
                tg.protocol,
                tg.port,
                tg.vpc_id,
                tg.total_targets,
                tg.healthy_targets,
                tg.unhealthy_targets,
                len(tg.load_balancer_arns),
            ],
        ),
    ]

    # =========================================================================
    # 스트리밍 처리: 수집 → Excel 쓰기 → 메모리 해제
    # =========================================================================
    for res_def in resources:
        with console.status(f"[yellow]{res_def.name} 수집 중...[/yellow]"):
            method = getattr(collector, res_def.method)
            data = method(**res_def.method_kwargs)
            count = len(data)
            stats.counts[res_def.name] = count

            # Excel 쓰기
            if data:
                sheet = wb.new_sheet(res_def.sheet_name, res_def.columns)
                for item in data:
                    sheet.add_row(res_def.row_mapper(item))

                # LB 유형별 통계
                if res_def.name == "Load Balancer":
                    for lb in data:
                        stats.type_counts[lb.lb_type] = stats.type_counts.get(lb.lb_type, 0) + 1
                    inactive = sum(1 for lb in data if lb.state != "active")
                    if inactive > 0:
                        stats.warnings.append(f"비활성 LB: {inactive}개")

                # TG 미연결 경고
                if res_def.name == "Target Group":
                    unattached = sum(1 for tg in data if not tg.load_balancer_arns)
                    if unattached > 0:
                        stats.warnings.append(f"LB 미연결 TG: {unattached}개")

            # 메모리 해제
            del data

        console.print(f"[dim]  {res_def.name}: {count:,}개[/dim]")

    # =========================================================================
    # 콘솔 출력
    # =========================================================================
    console.print()
    for name, count in stats.counts.items():
        console.print(f"총 {name}: [green]{count:,}[/green]개")

    if stats.type_counts:
        console.print()
        table = Table(title="Load Balancer 유형별 현황")
        table.add_column("유형", style="cyan")
        table.add_column("수량", justify="right", style="green")
        type_names = {"application": "ALB", "network": "NLB", "gateway": "GWLB", "classic": "CLB"}
        for lb_type, count in sorted(stats.type_counts.items()):
            table.add_row(type_names.get(lb_type, lb_type), str(count))
        console.print(table)

    for warning in stats.warnings:
        console.print(f"[yellow]  ⚠ {warning}[/yellow]")

    # =========================================================================
    # 저장
    # =========================================================================
    total = sum(stats.counts.values())
    if total > 0:
        filepath = wb.save_as(output_dir, "elb_inventory")
        console.print(f"\n[green]엑셀 저장 완료:[/green] {filepath}")
        open_in_explorer(output_dir)
    else:
        console.print("\n[yellow]수집된 리소스가 없습니다.[/yellow]")
