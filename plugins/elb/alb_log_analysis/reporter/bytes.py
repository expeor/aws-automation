"""Bytes analysis sheet writer."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from .base import BaseSheetWriter
from .config import HEADERS, SHEET_NAMES, SheetConfig

logger = logging.getLogger(__name__)


class BytesSheetWriter(BaseSheetWriter):
    """Creates data transfer analysis sheet."""

    def write(self) -> None:
        """Create bytes analysis sheet."""
        try:
            received_bytes = self.data.get("received_bytes", {})
            sent_bytes = self.data.get("sent_bytes", {})

            if not received_bytes and not sent_bytes:
                return

            ws = self.create_sheet(SHEET_NAMES.BYTES_ANALYSIS)
            headers = list(HEADERS.BYTES_ANALYSIS)
            self.write_header_row(ws, headers)

            # Combine and sort URLs by total bytes
            all_urls = sorted(
                set(list(received_bytes.keys()) + list(sent_bytes.keys()))
            )

            total_data: Dict[str, int] = {}
            for url in all_urls:
                total_data[url] = int(received_bytes.get(url, 0)) + int(
                    sent_bytes.get(url, 0)
                )

            sorted_urls = sorted(
                all_urls, key=lambda url: total_data[url], reverse=True
            )[: SheetConfig.TOP_BYTES_LIMIT]

            # Write data rows
            border = self.styles.thin_border
            for row_idx, url in enumerate(sorted_urls, start=2):
                received = int(received_bytes.get(url, 0))
                sent = int(sent_bytes.get(url, 0))
                total = received + sent
                formatted = self.format_bytes(total)

                values = [url, received, sent, total, formatted]

                for col_idx, value in enumerate(values, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.border = border

                    if col_idx > 1:
                        cell.alignment = self.styles.align_right
                        if col_idx in (2, 3, 4):
                            cell.number_format = "#,##0"
                    else:
                        cell.alignment = self.styles.align_left_wrap

            # Add total row
            self._add_total_row(ws, received_bytes, sent_bytes, len(sorted_urls))

            # Finalize
            self._apply_column_widths(ws, headers)
            ws.row_dimensions[1].height = SheetConfig.HEADER_ROW_HEIGHT
            ws.freeze_panes = ws.cell(row=2, column=1)
            ws.sheet_view.zoomScale = SheetConfig.ZOOM_SCALE

        except Exception as e:
            logger.error(f"데이터 전송량 시트 생성 중 오류: {e}")

    def _add_total_row(
        self,
        ws,
        received_bytes: Dict[str, int],
        sent_bytes: Dict[str, int],
        data_count: int,
    ) -> None:
        """Add total/summary row."""
        total_row = data_count + 2
        total_received = sum(int(v) for v in received_bytes.values())
        total_sent = sum(int(v) for v in sent_bytes.values())
        total_all = total_received + total_sent

        values = [
            "총계",
            total_received,
            total_sent,
            total_all,
            self.format_bytes(total_all),
        ]
        border = self.styles.thin_border

        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=total_row, column=col_idx, value=value)
            cell.font = self.styles.font_bold
            cell.border = border

            if col_idx > 1:
                cell.alignment = self.styles.align_right
                if col_idx in (2, 3, 4):
                    cell.number_format = "#,##0"
            else:
                cell.alignment = self.styles.align_left
