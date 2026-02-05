"""
analyzers/ec2/snapshot_cleanup.py - 미사용 EBS Snapshot 정리

고아/오래된 EBS Snapshot 삭제 (Dry-run 지원)

분석 로직은 snapshot_audit.py를 재사용하고, 삭제 기능만 추가.

안전장치:
- Dry-run 기본 활성화
- 이중 확인 (Dry-run 해제 시)
- AMI에 연결된 스냅샷은 절대 삭제하지 않음
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

from .snapshot_audit import (
    UsageStatus,
    analyze_snapshots,
    collect_snapshots,
    get_ami_snapshot_mapping,
)

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

console = Console()

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "ec2:DescribeSnapshots",
        "ec2:DescribeImages",
    ],
    "delete": [
        "ec2:DeleteSnapshot",
    ],
}


# =============================================================================
# 데이터 구조
# =============================================================================


@dataclass
class CleanupOperationLog:
    """개별 삭제 작업 로그"""

    snapshot_id: str
    snapshot_name: str
    volume_size_gb: int
    monthly_cost: float
    usage_status: str  # "orphan" / "old"
    operation: str  # "delete" / "delete (dry-run)"
    result: str  # "SUCCESS" / "FAILED" / "SKIPPED"
    error_message: str = ""
    account_id: str = ""
    account_name: str = ""
    region: str = ""


@dataclass
class SnapshotCleanupResult:
    """계정/리전별 정리 결과"""

    account_id: str
    account_name: str
    region: str
    total_targeted: int = 0
    deleted_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_size_freed_gb: int = 0
    total_cost_saved: float = 0.0
    operation_logs: list[CleanupOperationLog] = field(default_factory=list)


# =============================================================================
# 옵션 수집
# =============================================================================


def collect_options(ctx: ExecutionContext) -> None:
    """사용자 입력 수집 (timeline 밖에서 실행)"""
    console.print("\n[bold cyan]EBS Snapshot 정리 설정[/bold cyan]")

    # 1. 경과일 기준
    age_str = Prompt.ask("\n최소 경과일 (이 기간보다 오래된 스냅샷만 대상)", default="90")
    try:
        age_threshold = int(age_str)
    except ValueError:
        age_threshold = 90
    ctx.options["age_threshold"] = age_threshold

    # 2. 대상 유형
    console.print("\n[bold]대상 유형 선택[/bold]")
    console.print("1. 고아 스냅샷만 (AMI 삭제됨)")
    console.print("2. 오래된 스냅샷만 (AMI 있지만 오래됨)")
    console.print("3. 둘 다")

    target_choice = Prompt.ask("선택", choices=["1", "2", "3"], default="3")
    target_map = {"1": "orphan", "2": "old", "3": "both"}
    ctx.options["target_type"] = target_map[target_choice]

    # 3. Dry-run 모드
    dry_run = Confirm.ask(
        "\nDry-run 모드로 실행? (실제 삭제하지 않음)",
        default=True,
    )
    ctx.options["dry_run"] = dry_run

    if not dry_run:
        console.print("\n[yellow bold]경고: 실제로 스냅샷이 삭제됩니다![/yellow bold]")
        confirm = Confirm.ask("계속하시겠습니까?", default=False)
        if not confirm:
            ctx.options["dry_run"] = True
            console.print("[dim]Dry-run 모드로 전환됨[/dim]")


# =============================================================================
# Excel 보고서
# =============================================================================


def _generate_report(results: list[SnapshotCleanupResult], output_dir: str) -> str:
    """Excel 보고서 생성"""
    from core.tools.io.excel import ColumnDef, Styles, Workbook

    wb = Workbook()

    # Summary sheet
    summary = wb.new_summary_sheet("Summary")
    summary.add_title("EBS Snapshot 정리 보고서")
    summary.add_item("생성일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    summary.add_blank_row()

    total_targeted = sum(r.total_targeted for r in results)
    total_deleted = sum(r.deleted_count for r in results)
    total_failed = sum(r.failed_count for r in results)
    total_skipped = sum(r.skipped_count for r in results)
    total_size = sum(r.total_size_freed_gb for r in results)
    total_cost = sum(r.total_cost_saved for r in results)

    summary.add_section("정리 결과")
    summary.add_item("대상 스냅샷", total_targeted)
    summary.add_item("삭제 성공", total_deleted, highlight="success" if total_deleted > 0 else None)
    summary.add_item("삭제 실패", total_failed, highlight="danger" if total_failed > 0 else None)
    summary.add_item("스킵 (dry-run)", total_skipped, highlight="warning" if total_skipped > 0 else None)
    summary.add_item("해제 용량 (GB)", total_size)
    summary.add_item("절감 비용 ($/월)", f"${total_cost:.2f}")

    # Operation Logs sheet
    columns = [
        ColumnDef(header="Account", width=20),
        ColumnDef(header="Region", width=15),
        ColumnDef(header="Snapshot ID", width=25),
        ColumnDef(header="Name", width=25),
        ColumnDef(header="Status", width=12),
        ColumnDef(header="Size (GB)", width=12, style="number"),
        ColumnDef(header="Monthly Cost ($)", width=15, style="number"),
        ColumnDef(header="Operation", width=20),
        ColumnDef(header="Result", width=12),
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
                log.snapshot_id,
                log.snapshot_name,
                log.usage_status,
                log.volume_size_gb,
                round(log.monthly_cost, 2),
                log.operation,
                log.result,
                log.error_message,
            ],
            style=style,
        )

    return str(wb.save_as(output_dir, "Snapshot_Cleanup"))


# =============================================================================
# 메인
# =============================================================================


def run(ctx: ExecutionContext) -> None:
    """미사용 EBS Snapshot 정리 실행"""
    age_threshold = ctx.options.get("age_threshold", 90)
    target_type = ctx.options.get("target_type", "both")
    dry_run = ctx.options.get("dry_run", True)

    mode_str = "[yellow](Dry-run)[/yellow]" if dry_run else "[red](실제 삭제)[/red]"
    target_labels = {"orphan": "고아 스냅샷", "old": "오래된 스냅샷", "both": "고아 + 오래된 스냅샷"}

    console.print(f"[bold]EBS Snapshot 정리 시작... {mode_str}[/bold]")
    console.print(f"  대상: {target_labels.get(target_type, target_type)}")
    console.print(f"  기준: {age_threshold}일 이상 경과\n")

    # 클로저 패턴으로 worker 생성
    def worker(session, account_id: str, account_name: str, region: str) -> SnapshotCleanupResult | None:
        return _collect_and_cleanup(session, account_id, account_name, region, age_threshold, target_type, dry_run)

    result = parallel_collect(ctx, worker, max_workers=20, service="ec2")

    all_results: list[SnapshotCleanupResult] = [r for r in result.get_data() if r is not None]

    # 에러 출력
    if result.error_count > 0:
        console.print(f"[yellow]일부 오류 발생: {result.error_count}건[/yellow]")
        console.print(f"[dim]{result.get_error_summary()}[/dim]")

    if not all_results:
        console.print("[yellow]정리 대상 스냅샷 없음[/yellow]")
        return

    # 빈 결과 제외
    all_results = [r for r in all_results if r.total_targeted > 0]

    if not all_results:
        console.print("[yellow]정리 대상 스냅샷 없음[/yellow]")
        return

    # 요약 테이블
    total_targeted = sum(r.total_targeted for r in all_results)
    total_deleted = sum(r.deleted_count for r in all_results)
    total_failed = sum(r.failed_count for r in all_results)
    total_skipped = sum(r.skipped_count for r in all_results)
    total_size = sum(r.total_size_freed_gb for r in all_results)
    total_cost = sum(r.total_cost_saved for r in all_results)

    console.print("\n[bold]정리 결과[/bold]")

    table = Table(show_header=True)
    table.add_column("항목", style="cyan")
    table.add_column("수량", justify="right")

    table.add_row("대상 스냅샷", str(total_targeted))
    if total_deleted > 0:
        table.add_row("삭제 성공", f"[green]{total_deleted}[/green]")
    if total_failed > 0:
        table.add_row("삭제 실패", f"[red]{total_failed}[/red]")
    if total_skipped > 0:
        table.add_row("스킵 (dry-run)", f"[yellow]{total_skipped}[/yellow]")
    table.add_row("해제 용량", f"{total_size} GB")
    table.add_row("절감 비용", f"${total_cost:.2f}/월")

    console.print(table)

    if dry_run:
        console.print("\n[yellow]Dry-run 모드: 실제 스냅샷은 삭제되지 않았습니다.[/yellow]")
        console.print("[dim]실제 삭제하려면 dry-run 모드를 해제하고 다시 실행하세요.[/dim]")

    # Excel 보고서
    console.print("\n[cyan]Excel 보고서 생성 중...[/cyan]")

    if hasattr(ctx, "is_sso_session") and ctx.is_sso_session() and ctx.accounts:
        identifier = ctx.accounts[0].id
    elif ctx.profile_name:
        identifier = ctx.profile_name
    else:
        identifier = "default"

    output_path = OutputPath(identifier).sub("ebs", "snapshot_cleanup").with_date().build()
    filepath = _generate_report(all_results, output_path)

    console.print(f"[bold green]완료![/bold green] {filepath}")
    open_in_explorer(output_path)


def _collect_and_cleanup(
    session,
    account_id: str,
    account_name: str,
    region: str,
    age_threshold: int,
    target_type: str,
    dry_run: bool,
) -> SnapshotCleanupResult | None:
    """단일 계정/리전의 스냅샷 수집 및 정리 (병렬 실행용)"""
    from botocore.exceptions import ClientError

    # 1. 기존 분석 로직 재사용
    snapshots = collect_snapshots(session, account_id, account_name, region)
    if not snapshots:
        return None

    ami_mapping = get_ami_snapshot_mapping(session, region)
    analysis = analyze_snapshots(snapshots, ami_mapping, account_id, account_name, region)

    # 2. 대상 필터링
    targets = []
    for finding in analysis.findings:
        snap = finding.snapshot

        # target_type 필터링
        if target_type == "orphan" and finding.usage_status != UsageStatus.ORPHAN:
            continue
        if target_type == "old" and finding.usage_status != UsageStatus.OLD:
            continue
        if target_type == "both" and finding.usage_status not in (UsageStatus.ORPHAN, UsageStatus.OLD):
            continue

        # age_threshold 미만 스킵
        if snap.age_days < age_threshold:
            continue

        # 안전 가드: AMI에 연결된 스냅샷은 절대 삭제하지 않음
        if snap.has_ami and finding.usage_status == UsageStatus.ORPHAN:
            continue

        targets.append(finding)

    if not targets:
        return None

    # 3. 삭제 수행
    cleanup_result = SnapshotCleanupResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
        total_targeted=len(targets),
    )

    ec2 = get_client(session, "ec2", region_name=region)

    for finding in targets:
        snap = finding.snapshot
        log = CleanupOperationLog(
            snapshot_id=snap.id,
            snapshot_name=snap.name,
            volume_size_gb=snap.volume_size_gb,
            monthly_cost=snap.monthly_cost,
            usage_status=finding.usage_status.value,
            operation="delete (dry-run)" if dry_run else "delete",
            result="SKIPPED",
            account_id=account_id,
            account_name=account_name,
            region=region,
        )

        if dry_run:
            log.result = "SKIPPED"
            cleanup_result.skipped_count += 1
            cleanup_result.total_size_freed_gb += snap.volume_size_gb
            cleanup_result.total_cost_saved += snap.monthly_cost
        else:
            try:
                ec2.delete_snapshot(SnapshotId=snap.id)
                log.result = "SUCCESS"
                cleanup_result.deleted_count += 1
                cleanup_result.total_size_freed_gb += snap.volume_size_gb
                cleanup_result.total_cost_saved += snap.monthly_cost
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_msg = e.response.get("Error", {}).get("Message", str(e))
                log.result = "FAILED"
                log.error_message = f"{error_code}: {error_msg}"
                cleanup_result.failed_count += 1

        cleanup_result.operation_logs.append(log)

    return cleanup_result
