"""
analyzers/ec2/ami_cleanup.py - 미사용 AMI 정리

미사용 AMI 및 연관 스냅샷 삭제 (Dry-run 지원)

분석 로직은 ami_audit.py를 재사용하고, 삭제 기능만 추가.

안전장치:
- Dry-run 기본 활성화
- 이중 확인 (Dry-run 해제 시)
- deregister 실패 시 해당 AMI의 스냅샷 삭제 시도하지 않음
- 리소스별 에러 격리

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
    - collect_options(ctx): 옵션. 사용자 입력 수집.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from core.parallel import get_client, parallel_collect
from core.tools.output import OutputPath, open_in_explorer

from .ami_audit import (
    UsageStatus,
    analyze_amis,
    collect_amis,
    get_used_ami_ids,
)

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

console = Console()

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "ec2:DescribeImages",
        "ec2:DescribeInstances",
    ],
    "delete": [
        "ec2:DeregisterImage",
        "ec2:DeleteSnapshot",
    ],
}


# =============================================================================
# 데이터 구조
# =============================================================================


@dataclass
class AMICleanupOperationLog:
    """개별 AMI 정리 작업 로그"""

    ami_id: str
    ami_name: str
    total_size_gb: int
    monthly_cost: float
    operation: str  # "deregister" / "delete_snapshot" / dry-run 변형
    result: str  # "SUCCESS" / "FAILED" / "SKIPPED"
    snapshot_ids_deleted: list[str] = field(default_factory=list)
    snapshot_ids_failed: list[str] = field(default_factory=list)
    error_message: str = ""
    account_id: str = ""
    account_name: str = ""
    region: str = ""


@dataclass
class AMICleanupResult:
    """계정/리전별 AMI 정리 결과"""

    account_id: str
    account_name: str
    region: str
    total_targeted: int = 0
    deregistered_count: int = 0
    snapshots_deleted_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_size_freed_gb: int = 0
    total_cost_saved: float = 0.0
    operation_logs: list[AMICleanupOperationLog] = field(default_factory=list)


# =============================================================================
# 옵션 수집
# =============================================================================


def collect_options(ctx: ExecutionContext) -> None:
    """사용자 입력 수집 (timeline 밖에서 실행)"""
    console.print("\n[bold cyan]미사용 AMI 정리 설정[/bold cyan]")

    # 1. 최소 경과일
    age_str = Prompt.ask("\n최소 경과일 (이 기간보다 오래된 AMI만 대상)", default="14")
    try:
        age_threshold = int(age_str)
    except ValueError:
        age_threshold = 14
    ctx.options["age_threshold"] = age_threshold

    # 2. 연관 스냅샷 삭제 여부
    delete_snapshots = Confirm.ask(
        "\n연관 스냅샷도 함께 삭제?",
        default=True,
    )
    ctx.options["delete_snapshots"] = delete_snapshots

    # 3. Dry-run 모드
    dry_run = Confirm.ask(
        "\nDry-run 모드로 실행? (실제 삭제하지 않음)",
        default=True,
    )
    ctx.options["dry_run"] = dry_run

    if not dry_run:
        if delete_snapshots:
            console.print("\n[yellow bold]경고: AMI가 영구 삭제되며, 연관 스냅샷도 함께 삭제됩니다![/yellow bold]")
        else:
            console.print("\n[yellow bold]경고: AMI가 영구 삭제됩니다![/yellow bold]")
        confirm = Confirm.ask("계속하시겠습니까?", default=False)
        if not confirm:
            ctx.options["dry_run"] = True
            console.print("[dim]Dry-run 모드로 전환됨[/dim]")


# =============================================================================
# Excel 보고서
# =============================================================================


def _generate_report(results: list[AMICleanupResult], output_dir: str) -> str:
    """Excel 보고서 생성"""
    from core.tools.io.excel import ColumnDef, Styles, Workbook

    wb = Workbook()

    # Summary sheet
    summary = wb.new_summary_sheet("Summary")
    summary.add_title("AMI 정리 보고서")
    summary.add_item("생성일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    summary.add_blank_row()

    total_targeted = sum(r.total_targeted for r in results)
    total_deregistered = sum(r.deregistered_count for r in results)
    total_snaps_deleted = sum(r.snapshots_deleted_count for r in results)
    total_failed = sum(r.failed_count for r in results)
    total_skipped = sum(r.skipped_count for r in results)
    total_size = sum(r.total_size_freed_gb for r in results)
    total_cost = sum(r.total_cost_saved for r in results)

    summary.add_section("정리 결과")
    summary.add_item("대상 AMI", total_targeted)
    summary.add_item("AMI 삭제 성공", total_deregistered, highlight="success" if total_deregistered > 0 else None)
    summary.add_item("스냅샷 삭제 성공", total_snaps_deleted, highlight="success" if total_snaps_deleted > 0 else None)
    summary.add_item("실패", total_failed, highlight="danger" if total_failed > 0 else None)
    summary.add_item("스킵 (dry-run)", total_skipped, highlight="warning" if total_skipped > 0 else None)
    summary.add_item("해제 용량 (GB)", total_size)
    summary.add_item("절감 비용 ($/월)", f"${total_cost:.2f}")

    # Operation Logs sheet
    columns = [
        ColumnDef(header="Account", width=20),
        ColumnDef(header="Region", width=15),
        ColumnDef(header="AMI ID", width=22),
        ColumnDef(header="Name", width=30),
        ColumnDef(header="Size (GB)", width=12, style="number"),
        ColumnDef(header="Monthly Cost ($)", width=15, style="number"),
        ColumnDef(header="Operation", width=25),
        ColumnDef(header="Result", width=12),
        ColumnDef(header="Snapshots Deleted", width=25),
        ColumnDef(header="Snapshots Failed", width=25),
        ColumnDef(header="Error", width=40),
    ]
    sheet = wb.new_sheet("Operation Logs", columns)

    all_logs = []
    for r in results:
        all_logs.extend(r.operation_logs)

    # 비용순 정렬
    all_logs.sort(key=lambda x: x.monthly_cost, reverse=True)

    for log in all_logs:
        if log.result == "SUCCESS":
            style = Styles.success()
        elif log.result == "FAILED":
            style = Styles.danger()
        else:
            style = Styles.warning()

        sheet.add_row(
            [
                log.account_name,
                log.region,
                log.ami_id,
                log.ami_name,
                log.total_size_gb,
                round(log.monthly_cost, 2),
                log.operation,
                log.result,
                ", ".join(log.snapshot_ids_deleted) if log.snapshot_ids_deleted else "",
                ", ".join(log.snapshot_ids_failed) if log.snapshot_ids_failed else "",
                log.error_message,
            ],
            style=style,
        )

    return str(wb.save_as(output_dir, "AMI_Cleanup"))


# =============================================================================
# 메인
# =============================================================================


def run(ctx: ExecutionContext) -> None:
    """미사용 AMI 정리 실행"""
    age_threshold = ctx.options.get("age_threshold", 14)
    delete_snapshots = ctx.options.get("delete_snapshots", True)
    dry_run = ctx.options.get("dry_run", True)

    mode_str = "[yellow](Dry-run)[/yellow]" if dry_run else "[red](실제 삭제)[/red]"
    snap_str = "연관 스냅샷 포함" if delete_snapshots else "AMI만"

    console.print(f"[bold]미사용 AMI 정리 시작... {mode_str}[/bold]")
    console.print(f"  대상: 미사용 AMI ({snap_str})")
    console.print(f"  기준: {age_threshold}일 이상 경과\n")

    # 클로저 패턴으로 worker 생성
    def worker(session, account_id: str, account_name: str, region: str) -> AMICleanupResult | None:
        return _collect_and_cleanup(session, account_id, account_name, region, age_threshold, delete_snapshots, dry_run)

    result = parallel_collect(ctx, worker, max_workers=20, service="ec2")

    all_results: list[AMICleanupResult] = [r for r in result.get_data() if r is not None]

    # 에러 출력
    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")
        console.print(f"[dim]{result.get_error_summary()}[/dim]")

    if not all_results:
        console.print("[yellow]정리 대상 AMI 없음[/yellow]")
        return

    # 빈 결과 제외
    all_results = [r for r in all_results if r.total_targeted > 0]

    if not all_results:
        console.print("[yellow]정리 대상 AMI 없음[/yellow]")
        return

    # 요약 테이블
    total_targeted = sum(r.total_targeted for r in all_results)
    total_deregistered = sum(r.deregistered_count for r in all_results)
    total_snaps_deleted = sum(r.snapshots_deleted_count for r in all_results)
    total_failed = sum(r.failed_count for r in all_results)
    total_skipped = sum(r.skipped_count for r in all_results)
    total_size = sum(r.total_size_freed_gb for r in all_results)
    total_cost = sum(r.total_cost_saved for r in all_results)

    console.print("\n[bold]정리 결과[/bold]")

    table = Table(show_header=True)
    table.add_column("항목", style="cyan")
    table.add_column("수량", justify="right")

    table.add_row("대상 AMI", str(total_targeted))
    if total_deregistered > 0:
        table.add_row("AMI 삭제 성공", f"[green]{total_deregistered}[/green]")
    if total_snaps_deleted > 0:
        table.add_row("스냅샷 삭제 성공", f"[green]{total_snaps_deleted}[/green]")
    if total_failed > 0:
        table.add_row("실패", f"[red]{total_failed}[/red]")
    if total_skipped > 0:
        table.add_row("스킵 (dry-run)", f"[yellow]{total_skipped}[/yellow]")
    table.add_row("해제 용량", f"{total_size} GB")
    table.add_row("절감 비용", f"${total_cost:.2f}/월")

    console.print(table)

    if dry_run:
        console.print("\n[yellow]Dry-run 모드: 실제 AMI/스냅샷은 삭제되지 않았습니다.[/yellow]")
        console.print("[dim]실제 삭제하려면 dry-run 모드를 해제하고 다시 실행하세요.[/dim]")

    # Excel 보고서
    console.print("\n[cyan]Excel 보고서 생성 중...[/cyan]")

    if hasattr(ctx, "is_sso_session") and ctx.is_sso_session() and ctx.accounts:
        identifier = ctx.accounts[0].id
    elif ctx.profile_name:
        identifier = ctx.profile_name
    else:
        identifier = "default"

    output_path = OutputPath(identifier).sub("ami", "cleanup").with_date().build()
    filepath = _generate_report(all_results, output_path)

    console.print(f"[bold green]완료![/bold green] {filepath}")
    open_in_explorer(output_path)


def _collect_and_cleanup(
    session,
    account_id: str,
    account_name: str,
    region: str,
    age_threshold: int,
    delete_snapshots: bool,
    dry_run: bool,
) -> AMICleanupResult | None:
    """단일 계정/리전의 AMI 수집 및 정리 (병렬 실행용)"""
    from botocore.exceptions import ClientError

    # 1. 기존 분석 로직 재사용
    amis = collect_amis(session, account_id, account_name, region)
    if not amis:
        return None

    used_ami_ids = get_used_ami_ids(session, region)
    analysis = analyze_amis(amis, used_ami_ids, account_id, account_name, region)

    # 2. UNUSED만 필터링, age_threshold 미만 스킵
    targets = []
    for finding in analysis.findings:
        if finding.usage_status != UsageStatus.UNUSED:
            continue
        if finding.ami.age_days < age_threshold:
            continue
        targets.append(finding)

    if not targets:
        return None

    # 3. 삭제 수행
    cleanup_result = AMICleanupResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
        total_targeted=len(targets),
    )

    ec2 = get_client(session, "ec2", region_name=region)

    for finding in targets:
        ami = finding.ami
        log = AMICleanupOperationLog(
            ami_id=ami.id,
            ami_name=ami.name,
            total_size_gb=ami.total_size_gb,
            monthly_cost=ami.monthly_cost,
            operation="deregister (dry-run)" if dry_run else "deregister",
            result="SKIPPED",
            account_id=account_id,
            account_name=account_name,
            region=region,
        )

        if dry_run:
            log.result = "SKIPPED"
            cleanup_result.skipped_count += 1
            cleanup_result.total_size_freed_gb += ami.total_size_gb
            cleanup_result.total_cost_saved += ami.monthly_cost
            cleanup_result.operation_logs.append(log)
            continue

        # 실제 삭제: deregister_image 먼저
        try:
            ec2.deregister_image(ImageId=ami.id)
            log.result = "SUCCESS"
            log.operation = "deregister"
            cleanup_result.deregistered_count += 1
            cleanup_result.total_size_freed_gb += ami.total_size_gb
            cleanup_result.total_cost_saved += ami.monthly_cost
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            log.result = "FAILED"
            log.error_message = f"{error_code}: {error_msg}"
            cleanup_result.failed_count += 1
            cleanup_result.operation_logs.append(log)
            # deregister 실패 시 스냅샷 삭제 시도하지 않음
            continue

        # deregister 성공 시 연관 스냅샷 삭제
        if delete_snapshots and ami.snapshot_ids:
            for snap_id in ami.snapshot_ids:
                try:
                    ec2.delete_snapshot(SnapshotId=snap_id)
                    log.snapshot_ids_deleted.append(snap_id)
                    cleanup_result.snapshots_deleted_count += 1
                except ClientError:
                    log.snapshot_ids_failed.append(snap_id)

        cleanup_result.operation_logs.append(log)

    return cleanup_result
