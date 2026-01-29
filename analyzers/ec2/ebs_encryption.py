"""
analyzers/ec2/ebs_encryption.py - 암호화되지 않은 EBS 볼륨 탐지

암호화되지 않은 EBS 볼륨과 연결된 인스턴스를 탐지합니다.

보안 기준:
- 암호화되지 않은 볼륨은 데이터 유출 위험이 있음
- 연결된 볼륨(in-use)은 즉시 조치 필요
- 미연결 볼륨(available)은 삭제 전 암호화 검토

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from rich.console import Console

from core.parallel import get_client, is_quiet, parallel_collect
from core.tools.output import OutputPath, open_in_explorer

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

console = Console()

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "ec2:DescribeVolumes",
    ],
}


# =============================================================================
# 데이터 구조
# =============================================================================


@dataclass
class UnencryptedEBSInfo:
    """암호화되지 않은 EBS 볼륨 정보"""

    volume_id: str
    volume_name: str
    state: str  # available, in-use
    volume_type: str
    size_gb: int
    iops: int
    availability_zone: str
    create_time: datetime | None
    attachments: list[dict[str, Any]]
    account_id: str
    account_name: str
    region: str
    tags: dict[str, str]

    @property
    def is_attached(self) -> bool:
        """연결 여부"""
        return self.state == "in-use" and len(self.attachments) > 0

    @property
    def attached_instances(self) -> str:
        """연결된 인스턴스 ID 목록 (쉼표 구분)"""
        if not self.attachments:
            return ""
        return ", ".join(a.get("InstanceId", "") for a in self.attachments if a.get("InstanceId"))

    @property
    def device_paths(self) -> str:
        """디바이스 경로 목록 (쉼표 구분)"""
        if not self.attachments:
            return ""
        return ", ".join(a.get("Device", "") for a in self.attachments if a.get("Device"))


@dataclass
class UnencryptedEBSResult:
    """암호화되지 않은 EBS 분석 결과"""

    account_id: str
    account_name: str
    region: str
    volumes: list[UnencryptedEBSInfo] = field(default_factory=list)
    total_volumes_checked: int = 0
    unencrypted_count: int = 0
    unencrypted_size_gb: int = 0
    attached_count: int = 0
    available_count: int = 0


# =============================================================================
# 수집
# =============================================================================


def collect_unencrypted_volumes(
    session, account_id: str, account_name: str, region: str
) -> tuple[list[UnencryptedEBSInfo], int]:
    """암호화되지 않은 EBS 볼륨 수집

    Returns:
        tuple: (암호화되지 않은 볼륨 목록, 전체 볼륨 수)
    """
    from botocore.exceptions import ClientError

    unencrypted_volumes = []
    total_count = 0

    try:
        ec2 = get_client(session, "ec2", region_name=region)
        paginator = ec2.get_paginator("describe_volumes")

        for page in paginator.paginate():
            for data in page.get("Volumes", []):
                total_count += 1

                # 암호화된 볼륨은 스킵
                if data.get("Encrypted", False):
                    continue

                # 태그 파싱
                tags = {
                    t.get("Key", ""): t.get("Value", "")
                    for t in data.get("Tags", [])
                    if not t.get("Key", "").startswith("aws:")
                }

                volume = UnencryptedEBSInfo(
                    volume_id=data.get("VolumeId", ""),
                    volume_name=tags.get("Name", ""),
                    state=data.get("State", ""),
                    volume_type=data.get("VolumeType", ""),
                    size_gb=data.get("Size", 0),
                    iops=data.get("Iops", 0),
                    availability_zone=data.get("AvailabilityZone", ""),
                    create_time=data.get("CreateTime"),
                    attachments=data.get("Attachments", []),
                    account_id=account_id,
                    account_name=account_name,
                    region=region,
                    tags=tags,
                )
                unencrypted_volumes.append(volume)

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if not is_quiet():
            console.print(f"    [yellow]{account_name}/{region} EBS 수집 오류: {error_code}[/yellow]")

    return unencrypted_volumes, total_count


# =============================================================================
# Excel 보고서
# =============================================================================


def generate_report(results: list[UnencryptedEBSResult], output_dir: str) -> str:
    """Excel 보고서 생성"""
    from core.tools.io.excel import ColumnDef, Workbook

    wb = Workbook()

    # Summary sheet
    summary = wb.new_summary_sheet("Summary")
    summary.add_title("암호화되지 않은 EBS 볼륨 보고서")
    summary.add_item("생성일시", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    summary.add_blank_row()

    totals = {
        "total_checked": sum(r.total_volumes_checked for r in results),
        "unencrypted": sum(r.unencrypted_count for r in results),
        "unencrypted_size": sum(r.unencrypted_size_gb for r in results),
        "attached": sum(r.attached_count for r in results),
        "available": sum(r.available_count for r in results),
    }

    summary.add_section("통계")
    summary.add_item("전체 볼륨", totals["total_checked"])
    summary.add_item(
        "암호화되지 않은 볼륨", totals["unencrypted"], highlight="danger" if totals["unencrypted"] > 0 else None
    )
    summary.add_item("암호화되지 않은 용량 (GB)", totals["unencrypted_size"])
    summary.add_item("연결됨 (in-use)", totals["attached"], highlight="danger" if totals["attached"] > 0 else None)
    summary.add_item(
        "미연결 (available)", totals["available"], highlight="warning" if totals["available"] > 0 else None
    )

    # Volumes sheet
    columns = [
        ColumnDef(header="Account", width=20),
        ColumnDef(header="Region", width=15),
        ColumnDef(header="Volume ID", width=22),
        ColumnDef(header="Volume Name", width=25),
        ColumnDef(header="State", width=12, style="center"),
        ColumnDef(header="Type", width=10, style="center"),
        ColumnDef(header="Size (GB)", width=12, style="number"),
        ColumnDef(header="IOPS", width=10, style="number"),
        ColumnDef(header="AZ", width=18),
        ColumnDef(header="Attached Instances", width=25),
        ColumnDef(header="Device Paths", width=20),
        ColumnDef(header="Created", width=12),
    ]
    sheet = wb.new_sheet("Unencrypted Volumes", columns)

    # 모든 볼륨 수집
    all_volumes: list[UnencryptedEBSInfo] = []
    for result in results:
        all_volumes.extend(result.volumes)

    # 용량 기준 내림차순 정렬
    all_volumes.sort(key=lambda x: x.size_gb, reverse=True)

    for vol in all_volumes:
        sheet.add_row(
            [
                vol.account_name,
                vol.region,
                vol.volume_id,
                vol.volume_name,
                vol.state,
                vol.volume_type,
                vol.size_gb,
                vol.iops,
                vol.availability_zone,
                vol.attached_instances,
                vol.device_paths,
                vol.create_time.strftime("%Y-%m-%d") if vol.create_time else "",
            ]
        )

    return str(wb.save_as(output_dir, "EBS_Unencrypted"))


# =============================================================================
# 메인
# =============================================================================


def _collect_and_analyze(session, account_id: str, account_name: str, region: str) -> UnencryptedEBSResult:
    """단일 계정/리전의 암호화되지 않은 EBS 수집 (병렬 실행용)"""
    volumes, total_count = collect_unencrypted_volumes(session, account_id, account_name, region)

    attached_count = sum(1 for v in volumes if v.is_attached)
    available_count = len(volumes) - attached_count

    return UnencryptedEBSResult(
        account_id=account_id,
        account_name=account_name,
        region=region,
        volumes=volumes,
        total_volumes_checked=total_count,
        unencrypted_count=len(volumes),
        unencrypted_size_gb=sum(v.size_gb for v in volumes),
        attached_count=attached_count,
        available_count=available_count,
    )


def run(ctx: ExecutionContext) -> None:
    """암호화되지 않은 EBS 볼륨 탐지 실행 (병렬 처리)"""
    console.print("[bold]암호화되지 않은 EBS 볼륨 탐지 시작...[/bold]")

    # 병렬 수집
    result = parallel_collect(
        ctx,
        _collect_and_analyze,
        max_workers=20,
        service="ec2",
    )

    # 결과 처리
    all_results: list[UnencryptedEBSResult] = result.get_data()

    # 진행 상황 출력
    console.print(f"  [dim]수집 완료: 성공 {result.success_count}, 실패 {result.error_count}[/dim]")

    # 에러 요약
    if result.error_count > 0:
        console.print(f"\n[yellow]{result.get_error_summary()}[/yellow]")

    if not all_results:
        console.print("[yellow]분석할 EBS 없음[/yellow]")
        return

    # 개별 결과 요약
    for r in all_results:
        if r.unencrypted_count > 0:
            attached_str = f"연결됨 {r.attached_count}개" if r.attached_count > 0 else ""
            available_str = f"미연결 {r.available_count}개" if r.available_count > 0 else ""
            parts = [p for p in [attached_str, available_str] if p]
            console.print(
                f"  {r.account_name}/{r.region}: [red]암호화되지 않은 볼륨 {r.unencrypted_count}개 ({', '.join(parts)})[/red]"
            )
        elif r.total_volumes_checked > 0:
            console.print(f"  {r.account_name}/{r.region}: [green]모든 볼륨 암호화됨 ({r.total_volumes_checked}개)[/green]")

    # 전체 통계
    totals = {
        "total_checked": sum(r.total_volumes_checked for r in all_results),
        "unencrypted": sum(r.unencrypted_count for r in all_results),
        "unencrypted_size": sum(r.unencrypted_size_gb for r in all_results),
        "attached": sum(r.attached_count for r in all_results),
        "available": sum(r.available_count for r in all_results),
    }

    console.print(f"\n[bold]전체 EBS: {totals['total_checked']}개[/bold]")
    if totals["unencrypted"] > 0:
        console.print(
            f"  [red bold]암호화되지 않은 볼륨: {totals['unencrypted']}개 ({totals['unencrypted_size']}GB)[/red bold]"
        )
        if totals["attached"] > 0:
            console.print(f"    [red]- 연결됨 (in-use): {totals['attached']}개 - 즉시 조치 필요[/red]")
        if totals["available"] > 0:
            console.print(f"    [yellow]- 미연결 (available): {totals['available']}개[/yellow]")
    else:
        console.print("  [green bold]모든 볼륨이 암호화되어 있습니다[/green bold]")

    # 보고서 생성 (암호화되지 않은 볼륨이 있을 때만)
    if totals["unencrypted"] > 0:
        console.print("\n[cyan]Excel 보고서 생성 중...[/cyan]")

        if hasattr(ctx, "is_sso_session") and ctx.is_sso_session() and ctx.accounts:
            identifier = ctx.accounts[0].id
        elif ctx.profile_name:
            identifier = ctx.profile_name
        else:
            identifier = "default"

        output_path = OutputPath(identifier).sub("ebs", "encryption").with_date().build()
        filepath = generate_report(all_results, output_path)

        console.print(f"[bold green]완료![/bold green] {filepath}")
        open_in_explorer(output_path)
    else:
        console.print("\n[green]암호화되지 않은 볼륨이 없으므로 보고서를 생성하지 않습니다.[/green]")
