"""
plugins/tag_editor/report.py - MAP 태그 Excel 리포트 생성

분석 및 적용 결과를 Excel 파일로 출력
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from core.tools.io.excel import ColumnDef, Styles, Workbook

from .types import (
    MAP_TAG_KEY,
    MapTagAnalysisResult,
    MapTagApplyResult,
    TagOperationResult,
)

# =============================================================================
# 분석 리포트
# =============================================================================


def generate_audit_report(
    results: list[MapTagAnalysisResult],
    output_dir: str,
    untagged_only: bool = False,
) -> str:
    """MAP 태그 분석 Excel 리포트 생성"""
    wb = Workbook()

    # ===== Summary 시트 =====
    summary = wb.new_summary_sheet("Summary")
    summary.add_title("MAP 태그 분석 리포트")
    summary.add_item("분석 태그", MAP_TAG_KEY)
    summary.add_item("생성", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 전체 통계
    total_resources = sum(r.total_resources for r in results)
    total_tagged = sum(r.tagged_resources for r in results)
    total_untagged = sum(r.untagged_resources for r in results)
    overall_rate = (total_tagged / total_resources * 100) if total_resources > 0 else 0

    summary.add_blank_row()
    summary.add_section("전체 현황")
    summary.add_item("총 리소스", total_resources)
    summary.add_item("태그됨", total_tagged, highlight="success")
    summary.add_item("미태그", total_untagged, highlight="danger" if total_untagged > 0 else None)
    summary.add_item("적용률", f"{overall_rate:.1f}%")

    # ===== 계정/리전별 현황 시트 =====
    account_columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="전체", width=10, style="number"),
        ColumnDef(header="태그됨", width=10, style="number"),
        ColumnDef(header="미태그", width=10, style="number"),
        ColumnDef(header="적용률", width=12, style="center"),
    ]
    account_sheet = wb.new_sheet("By Account", columns=account_columns)

    for r in results:
        rate = (r.tagged_resources / r.total_resources * 100) if r.total_resources > 0 else 0
        row_style = Styles.danger() if r.untagged_resources > 0 else None
        account_sheet.add_row(
            [
                r.account_name,
                r.region,
                r.total_resources,
                r.tagged_resources,
                r.untagged_resources,
                f"{rate:.1f}%",
            ],
            style=row_style,
        )

    # ===== 리소스 타입별 시트 =====
    type_columns = [
        ColumnDef(header="리소스 타입", width=30, style="data"),
        ColumnDef(header="전체", width=10, style="number"),
        ColumnDef(header="태그됨", width=10, style="number"),
        ColumnDef(header="미태그", width=10, style="number"),
        ColumnDef(header="적용률", width=12, style="center"),
    ]
    type_sheet = wb.new_sheet("By Resource Type", columns=type_columns)

    # 타입별 통계 집계
    type_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "tagged": 0})
    for r in results:
        for ts in r.type_stats:
            type_totals[ts.resource_type]["total"] += ts.total
            type_totals[ts.resource_type]["tagged"] += ts.tagged

    for res_type, counts in sorted(type_totals.items(), key=lambda x: x[1]["total"], reverse=True):
        total = counts["total"]
        tagged = counts["tagged"]
        untagged = total - tagged
        rate = (tagged / total * 100) if total > 0 else 0

        # 표시 이름
        parts = res_type.split(":")
        display = " ".join(p.capitalize() for p in parts)

        row_style = Styles.danger() if untagged > 0 else None
        type_sheet.add_row(
            [display, total, tagged, untagged, f"{rate:.1f}%"],
            style=row_style,
        )

    # ===== 미태그 리소스 시트 =====
    untagged_columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Type", width=25, style="data"),
        ColumnDef(header="Resource ID", width=30, style="data"),
        ColumnDef(header="Name", width=30, style="data"),
        ColumnDef(header="ARN", width=60, style="data"),
    ]
    untagged_sheet = wb.new_sheet("Untagged Resources", columns=untagged_columns)

    for r in results:
        for res in r.resources:
            if not res.has_map_tag:
                parts = res.resource_type.split(":")
                type_display = " ".join(p.capitalize() for p in parts)
                untagged_sheet.add_row(
                    [
                        res.account_name,
                        res.region,
                        type_display,
                        res.resource_id,
                        res.name or "-",
                        res.resource_arn,
                    ]
                )

    # ===== 태그된 리소스 시트 (옵션) =====
    if not untagged_only:
        tagged_columns = [
            ColumnDef(header="Account", width=25, style="data"),
            ColumnDef(header="Region", width=15, style="data"),
            ColumnDef(header="Type", width=25, style="data"),
            ColumnDef(header="Resource ID", width=30, style="data"),
            ColumnDef(header="Name", width=30, style="data"),
            ColumnDef(header="MAP Tag Value", width=30, style="data"),
            ColumnDef(header="ARN", width=60, style="data"),
        ]
        tagged_sheet = wb.new_sheet("Tagged Resources", columns=tagged_columns)

        for r in results:
            for res in r.resources:
                if res.has_map_tag:
                    parts = res.resource_type.split(":")
                    type_display = " ".join(p.capitalize() for p in parts)
                    tagged_sheet.add_row(
                        [
                            res.account_name,
                            res.region,
                            type_display,
                            res.resource_id,
                            res.name or "-",
                            res.map_tag_value or "-",
                            res.resource_arn,
                        ]
                    )

    # ===== 전체 리소스 시트 =====
    all_columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Type", width=25, style="data"),
        ColumnDef(header="Resource ID", width=30, style="data"),
        ColumnDef(header="Name", width=30, style="data"),
        ColumnDef(header="MAP Tagged", width=12, style="center"),
        ColumnDef(header="MAP Value", width=30, style="data"),
        ColumnDef(header="ARN", width=60, style="data"),
    ]
    all_sheet = wb.new_sheet("All Resources", columns=all_columns)

    for r in results:
        for res in r.resources:
            parts = res.resource_type.split(":")
            type_display = " ".join(p.capitalize() for p in parts)
            row_style = Styles.success() if res.has_map_tag else Styles.danger()
            all_sheet.add_row(
                [
                    res.account_name,
                    res.region,
                    type_display,
                    res.resource_id,
                    res.name or "-",
                    "Yes" if res.has_map_tag else "No",
                    res.map_tag_value or "-",
                    res.resource_arn,
                ],
                style=row_style,
            )

    return str(wb.save_as(output_dir, "MAP_Tag_Audit"))


# =============================================================================
# 적용 리포트
# =============================================================================


def generate_apply_report(
    results: list[MapTagApplyResult],
    output_dir: str,
) -> str:
    """MAP 태그 적용 결과 Excel 리포트 생성"""
    wb = Workbook()

    # ===== Summary 시트 =====
    summary = wb.new_summary_sheet("Summary")
    summary.add_title("MAP 태그 적용 결과 리포트")
    summary.add_item("생성", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 전체 통계
    total_targeted = sum(r.total_targeted for r in results)
    total_success = sum(r.success_count for r in results)
    total_failed = sum(r.failed_count for r in results)
    total_skipped = sum(r.skipped_count for r in results)

    summary.add_blank_row()
    summary.add_section("적용 결과")
    summary.add_item("대상 리소스", total_targeted)
    summary.add_item("성공", total_success, highlight="success")
    summary.add_item("실패", total_failed, highlight="danger" if total_failed > 0 else None)
    summary.add_item("스킵", total_skipped)

    # ===== 계정/리전별 결과 시트 =====
    account_columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="태그 값", width=30, style="data"),
        ColumnDef(header="대상", width=10, style="number"),
        ColumnDef(header="성공", width=10, style="number"),
        ColumnDef(header="실패", width=10, style="number"),
        ColumnDef(header="스킵", width=10, style="number"),
    ]
    account_sheet = wb.new_sheet("By Account", columns=account_columns)

    for r in results:
        row_style = Styles.danger() if r.failed_count > 0 else None
        account_sheet.add_row(
            [
                r.account_name,
                r.region,
                r.tag_value,
                r.total_targeted,
                r.success_count,
                r.failed_count,
                r.skipped_count,
            ],
            style=row_style,
        )

    # ===== 상세 로그 시트 =====
    log_columns = [
        ColumnDef(header="Account", width=25, style="data"),
        ColumnDef(header="Region", width=15, style="data"),
        ColumnDef(header="Type", width=25, style="data"),
        ColumnDef(header="Resource ID", width=30, style="data"),
        ColumnDef(header="Name", width=30, style="data"),
        ColumnDef(header="Operation", width=15, style="center"),
        ColumnDef(header="Result", width=10, style="center"),
        ColumnDef(header="Error", width=40, style="data"),
        ColumnDef(header="Previous", width=25, style="data"),
        ColumnDef(header="New", width=25, style="data"),
    ]
    log_sheet = wb.new_sheet("Operation Log", columns=log_columns)

    for r in results:
        for log in r.operation_logs:
            parts = log.resource_type.split(":")
            type_display = " ".join(p.capitalize() for p in parts)

            # 결과에 따른 스타일
            if log.result == TagOperationResult.SUCCESS:
                row_style = Styles.success()
            elif log.result == TagOperationResult.FAILED:
                row_style = Styles.danger()
            else:
                row_style = Styles.warning()

            log_sheet.add_row(
                [
                    r.account_name,
                    r.region,
                    type_display,
                    log.resource_id,
                    log.name or "-",
                    log.operation,
                    log.result.value,
                    log.error_message or "-",
                    log.previous_value or "-",
                    log.new_value or "-",
                ],
                style=row_style,
            )

    return str(wb.save_as(output_dir, "MAP_Tag_Apply"))
