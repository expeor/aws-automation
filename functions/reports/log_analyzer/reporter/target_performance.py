"""Target performance analysis sheet writer."""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseSheetWriter, get_column_letter
from .config import SheetConfig

logger = logging.getLogger(__name__)

# Target Performance Sheet configuration
SHEET_NAME_TARGET_PERF = "Target 성능 분석"
HEADERS_TARGET_PERF = (
    "Target",
    "요청 수",
    "평균 (ms)",
    "P50 (ms)",
    "P90 (ms)",
    "P99 (ms)",
    "에러 수",
    "에러율 (%)",
)

TARGET_PERF_COLUMN_WIDTHS = {
    "Target": 50,
    "요청 수": 12,
    "평균 (ms)": 12,
    "P50 (ms)": 12,
    "P90 (ms)": 12,
    "P99 (ms)": 12,
    "에러 수": 10,
    "에러율 (%)": 12,
}


class TargetPerformanceSheetWriter(BaseSheetWriter):
    """Creates Target performance analysis sheet."""

    def write(self) -> None:
        """Create Target performance analysis sheet."""
        try:
            target_data = self.data.get("target_latency_stats", {})
            if not target_data:
                return

            ws = self.create_sheet(SHEET_NAME_TARGET_PERF)
            headers = list(HEADERS_TARGET_PERF)
            self.write_header_row(ws, headers)

            # Write data rows
            self._write_target_perf_rows(ws, target_data, headers)

            # Finalize sheet
            self._apply_target_perf_column_widths(ws, headers)
            ws.row_dimensions[1].height = SheetConfig.HEADER_ROW_HEIGHT

            data_count = len(target_data)
            if data_count > 0:
                last_col = get_column_letter(len(headers))
                ws.auto_filter.ref = f"A1:{last_col}{data_count + 1}"

            ws.freeze_panes = ws.cell(row=2, column=1)  # pyright: ignore[reportAttributeAccessIssue]
            ws.sheet_view.zoomScale = SheetConfig.ZOOM_SCALE

        except Exception as e:
            logger.error(f"Target 성능 분석 시트 생성 중 오류: {e}")

    def _write_target_perf_rows(
        self,
        ws,
        target_data: dict[str, dict[str, Any]],
        headers: list[str],
    ) -> None:
        """Write Target performance data rows."""
        border = self.styles.thin_border

        # Sort by request count (descending)
        sorted_targets = sorted(
            target_data.items(),
            key=lambda x: x[1].get("total_requests", 0),
            reverse=True,
        )

        for row_idx, (target_name, stats) in enumerate(sorted_targets, start=2):
            values = [
                target_name,
                stats.get("total_requests", 0),
                stats.get("avg_ms", 0),
                stats.get("p50_ms", 0),
                stats.get("p90_ms", 0),
                stats.get("p99_ms", 0),
                stats.get("error_count", 0),
                stats.get("error_rate", 0),
            ]

            for col_idx, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = border

                # Column-specific formatting
                if col_idx == 1:  # Target name
                    cell.alignment = self.styles.align_left
                elif col_idx == 2:  # Request count
                    cell.alignment = self.styles.align_right
                    cell.number_format = "#,##0"
                elif col_idx in (3, 4, 5, 6):  # Latency values (ms)
                    cell.alignment = self.styles.align_right
                    cell.number_format = "0.00"
                    # Highlight slow targets (P99 > 1000ms)
                    if col_idx == 6 and isinstance(value, (int, float)) and value > 1000:
                        cell.fill = self.styles.warning_fill
                    if col_idx == 6 and isinstance(value, (int, float)) and value > 3000:
                        cell.fill = self.styles.danger_fill
                elif col_idx == 7:  # Error count
                    cell.alignment = self.styles.align_right
                    cell.number_format = "#,##0"
                elif col_idx == 8:  # Error rate
                    cell.alignment = self.styles.align_right
                    cell.number_format = "0.00"
                    # Highlight high error rates
                    if isinstance(value, (int, float)) and value > 5:
                        cell.fill = self.styles.warning_fill
                    if isinstance(value, (int, float)) and value > 10:
                        cell.fill = self.styles.danger_fill

    def _apply_target_perf_column_widths(self, ws, headers: list[str]) -> None:
        """Apply column widths for Target performance sheet."""
        for col, header in enumerate(headers, 1):
            width = TARGET_PERF_COLUMN_WIDTHS.get(header, 15)
            ws.column_dimensions[get_column_letter(col)].width = width
