"""TPS (Throughput) analysis sheet writer."""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseSheetWriter, get_column_letter
from .config import SheetConfig

logger = logging.getLogger(__name__)

# TPS Sheet configuration
SHEET_NAME_TPS = "TPS 분석"
HEADERS_TPS = (
    "시간",
    "요청 수",
    "TPS",
    "P50 (ms)",
    "P90 (ms)",
    "P99 (ms)",
    "에러 수",
    "에러율 (%)",
)

TPS_COLUMN_WIDTHS = {
    "시간": 22,
    "요청 수": 12,
    "TPS": 10,
    "P50 (ms)": 12,
    "P90 (ms)": 12,
    "P99 (ms)": 12,
    "에러 수": 10,
    "에러율 (%)": 12,
}


class TPSSheetWriter(BaseSheetWriter):
    """Creates TPS (Throughput) analysis sheet."""

    def write(self) -> None:
        """Create TPS analysis sheet."""
        try:
            tps_data = self.data.get("tps_time_series", [])
            if not tps_data:
                return

            ws = self.create_sheet(SHEET_NAME_TPS)
            headers = list(HEADERS_TPS)
            self.write_header_row(ws, headers)

            # Write data rows
            self._write_tps_rows(ws, tps_data, headers)

            # Finalize sheet
            self._apply_tps_column_widths(ws, headers)
            ws.row_dimensions[1].height = SheetConfig.HEADER_ROW_HEIGHT

            if tps_data:
                last_col = get_column_letter(len(headers))
                ws.auto_filter.ref = f"A1:{last_col}{len(tps_data) + 1}"

            ws.freeze_panes = ws.cell(row=2, column=1)  # pyright: ignore[reportAttributeAccessIssue]
            ws.sheet_view.zoomScale = SheetConfig.ZOOM_SCALE

        except Exception as e:
            logger.error(f"TPS 시트 생성 중 오류: {e}")

    def _write_tps_rows(
        self,
        ws,
        data: list[dict[str, Any]],
        headers: list[str],
    ) -> None:
        """Write TPS data rows."""
        border = self.styles.thin_border

        for row_idx, row_data in enumerate(data, start=2):
            timestamp_str = self.format_timestamp(row_data.get("timestamp"))

            values = [
                timestamp_str,
                row_data.get("request_count", 0),
                row_data.get("tps", 0),
                row_data.get("p50_ms", 0),
                row_data.get("p90_ms", 0),
                row_data.get("p99_ms", 0),
                row_data.get("error_count", 0),
                row_data.get("error_rate", 0),
            ]

            for col_idx, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = border

                # Column-specific formatting
                if col_idx == 1:  # Timestamp
                    cell.alignment = self.styles.align_center
                elif col_idx in (2, 7):  # Request count, Error count (integers)
                    cell.alignment = self.styles.align_right
                    cell.number_format = "#,##0"
                elif col_idx == 3 or col_idx in (4, 5, 6):  # TPS
                    cell.alignment = self.styles.align_right
                    cell.number_format = "0.00"
                elif col_idx == 8:  # Error rate
                    cell.alignment = self.styles.align_right
                    cell.number_format = "0.00"
                    # Highlight high error rates
                    if isinstance(value, (int, float)) and value > 5:
                        cell.fill = self.styles.warning_fill
                    if isinstance(value, (int, float)) and value > 10:
                        cell.fill = self.styles.danger_fill

    def _apply_tps_column_widths(self, ws, headers: list[str]) -> None:
        """Apply column widths for TPS sheet."""
        for col, header in enumerate(headers, 1):
            width = TPS_COLUMN_WIDTHS.get(header, 15)
            ws.column_dimensions[get_column_letter(col)].width = width
