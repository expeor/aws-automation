"""Response time sheet writer."""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseSheetWriter, get_column_letter
from .config import HEADERS, SHEET_NAMES, SheetConfig

logger = logging.getLogger(__name__)


class ResponseTimeSheetWriter(BaseSheetWriter):
    """Creates response time analysis sheet."""

    def write(self) -> None:
        """Create response time sheet."""
        try:
            if not (self.data.get("response_time") or self.data.get("long_response_times")):
                return

            # Get and filter logs
            long_response_logs = self.data.get("long_response_times", [])
            if not isinstance(long_response_logs, list):
                long_response_logs = []

            # Sort by response time (descending), filter nulls
            sorted_logs = sorted(
                long_response_logs,
                key=lambda x: x.get("response_time") if x.get("response_time") is not None else -1,
                reverse=True,
            )
            filtered_logs = [log for log in sorted_logs if log.get("response_time") is not None][
                : SheetConfig.TOP_RESPONSE_TIME_LIMIT
            ]

            if not filtered_logs:
                return

            ws = self.create_sheet(SHEET_NAMES.RESPONSE_TIME)
            headers = list(HEADERS.RESPONSE_TIME)
            self.write_header_row(ws, headers)

            # Get abuse IPs for highlighting
            abuse_ips_list, _ = self.get_normalized_abuse_ips()
            abuse_ips_set = set(abuse_ips_list)

            # Write data rows
            self._write_response_time_rows(ws, filtered_logs, headers, abuse_ips_set)

            # Finalize
            self.apply_wrap_text(ws, headers)
            self._apply_column_widths(ws, headers)
            ws.row_dimensions[1].height = SheetConfig.HEADER_ROW_HEIGHT

            if filtered_logs:
                last_col = get_column_letter(len(headers))
                ws.auto_filter.ref = f"A1:{last_col}{len(filtered_logs) + 1}"

            ws.freeze_panes = ws.cell(row=2, column=1)  # pyright: ignore[reportAttributeAccessIssue]
            ws.sheet_view.zoomScale = SheetConfig.ZOOM_SCALE

        except Exception as e:
            logger.error(f"응답 시간 시트 생성 중 오류: {e}")

    def _write_response_time_rows(
        self,
        ws,
        logs: list[dict[str, Any]],
        headers: list[str],
        abuse_ips: set[str],
    ) -> None:
        """Write response time rows."""
        border = self.styles.thin_border
        abuse_fill = self.styles.fill_abuse

        for row_idx, log in enumerate(logs, start=2):
            client_ip = log.get("client_ip", "N/A")
            is_abuse = client_ip in abuse_ips

            target = log.get("target", "")
            target_field = "" if not target or target == "-" else target
            target_group = log.get("target_group_name", "") or ""

            country = self.get_country_code(client_ip)
            timestamp_str = self.format_timestamp(log.get("timestamp"))

            values = [
                log.get("response_time", 0),
                timestamp_str,
                client_ip,
                country,
                target_field,
                target_group,
                log.get("http_method", "").replace("-", ""),
                log.get("request", "N/A"),
                log.get("user_agent", "N/A"),
                self.convert_status_code(log.get("elb_status_code", "N/A")),
                self.convert_status_code(log.get("target_status_code", "N/A")),
            ]

            for col_idx, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = border

                # Alignment
                if col_idx == 1:  # Response time
                    cell.alignment = self.styles.align_right
                elif col_idx in (2, 3, 4, 5, 6, 7):  # Timestamp through Method
                    cell.alignment = self.styles.align_center
                elif col_idx in (8, 9):  # Request, User Agent
                    cell.alignment = self.styles.align_left
                elif col_idx in (10, 11):  # Status codes
                    cell.alignment = self.styles.align_right
                    if isinstance(value, int):
                        cell.number_format = "0"

                if is_abuse:
                    cell.fill = abuse_fill
