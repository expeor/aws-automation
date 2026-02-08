"""미사용 리소스 리포트 시트 생성 함수"""

from __future__ import annotations

from core.shared.io.excel import ColumnDef, Styles, Workbook


def _create_ecr_sheet(wb: Workbook, results) -> None:
    """미사용/비효율 ECR 리포지토리 상세 시트를 생성한다."""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Repository", width=40, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="이미지 수", width=10, style="number"),
        ColumnDef(header="오래된 이미지", width=12, style="number"),
        ColumnDef(header="총 크기", width=12, style="data"),
        ColumnDef(header="낭비 비용", width=12, style="data"),
        ColumnDef(header="Lifecycle", width=10, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("ECR", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                repo = f.repo
                sheet.add_row(
                    [
                        repo.account_name,
                        repo.region,
                        repo.name,
                        f.status.value,
                        repo.image_count,
                        repo.old_image_count,
                        f"{repo.total_size_gb:.2f} GB",
                        f"${repo.old_images_monthly_cost:.2f}",
                        "있음" if repo.has_lifecycle_policy else "없음",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_efs_sheet(wb: Workbook, results) -> None:
    """EFS 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="ID", width=25, style="data"),
        ColumnDef(header="Name", width=25, style="data"),
        ColumnDef(header="Size", width=12, style="data"),
        ColumnDef(header="Mount Targets", width=12, style="number"),
        ColumnDef(header="Mode", width=15, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="Avg Conn", width=10, style="data"),
        ColumnDef(header="Total I/O", width=12, style="data"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("EFS", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                fs = f.efs
                sheet.add_row(
                    [
                        fs.account_name,
                        fs.region,
                        fs.file_system_id,
                        fs.name or "-",
                        f"{fs.size_gb:.2f} GB",
                        fs.mount_target_count,
                        fs.throughput_mode,
                        f.status.value,
                        f"{fs.avg_client_connections:.1f}",
                        f"{fs.total_io_bytes / (1024**2):.1f} MB",
                        f"${fs.estimated_monthly_cost:.2f}",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_s3_sheet(wb: Workbook, results) -> None:
    """미사용/비효율 S3 버킷 상세 시트를 생성한다."""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Bucket", width=40, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="객체 수", width=12, style="number"),
        ColumnDef(header="크기", width=15, style="data"),
        ColumnDef(header="버전관리", width=10, style="center"),
        ColumnDef(header="Lifecycle", width=10, style="center"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("S3", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value != "normal":
                bucket = f.bucket
                sheet.add_row(
                    [
                        bucket.account_name,
                        bucket.name,
                        bucket.region,
                        f.status.value,
                        bucket.object_count,
                        f"{bucket.total_size_mb:.2f} MB",
                        "Enabled" if bucket.versioning_enabled else "Disabled",
                        "있음" if bucket.has_lifecycle else "없음",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )


def _create_fsx_sheet(wb: Workbook, results) -> None:
    """FSx 상세 시트 생성"""
    columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="File System ID", width=25, style="data"),
        ColumnDef(header="Type", width=12, style="center"),
        ColumnDef(header="Storage(GB)", width=12, style="number"),
        ColumnDef(header="Throughput", width=12, style="number"),
        ColumnDef(header="Lifecycle", width=12, style="center"),
        ColumnDef(header="Total Ops", width=12, style="number"),
        ColumnDef(header="Daily Avg", width=12, style="number"),
        ColumnDef(header="상태", width=12, style="center"),
        ColumnDef(header="월간 비용", width=15, style="data"),
        ColumnDef(header="권장 조치", width=40, style="data"),
    ]
    sheet = wb.new_sheet("FSx", columns=columns)

    for r in results:
        for f in r.findings:
            if f.status.value not in ("normal", "creating"):
                fs = f.filesystem
                sheet.add_row(
                    [
                        fs.account_name,
                        fs.region,
                        fs.file_system_id,
                        fs.file_system_type,
                        fs.storage_capacity_gb,
                        fs.throughput_capacity,
                        fs.lifecycle,
                        int(fs.total_ops),
                        int(fs.avg_daily_ops),
                        f.status.value,
                        f"${fs.estimated_monthly_cost:.2f}",
                        f.recommendation,
                    ],
                    style=Styles.danger() if f.status.value == "unused" else Styles.warning(),
                )
