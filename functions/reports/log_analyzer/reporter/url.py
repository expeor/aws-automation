"""functions/reports/log_analyzer/reporter/url.py - URL 통계 시트 Writer.

요청 URL별 통계(요청 수, 고유 IP 수, 평균 응답 시간, 에러율)를 분석하여
Top N 시트를 생성합니다.
"""

from __future__ import annotations

import logging
from typing import Any

from .base import BaseSheetWriter
from .config import HEADERS, SHEET_NAMES, SheetConfig

logger = logging.getLogger(__name__)


class URLSheetWriter(BaseSheetWriter):
    """Creates the URL request statistics sheet."""

    def write(self) -> None:
        """Create URL request sheet (detailed or simple based on available data)."""
        try:
            if self.data.get("request_url_details"):
                self._write_detailed_url_sheet()
            elif self.data.get("request_url_counts"):
                self._write_simple_url_sheet()
        except Exception as e:
            logger.error(f"요청 URL 시트 생성 중 오류: {e}")

    def _write_detailed_url_sheet(self) -> None:
        """Write detailed URL statistics with client info."""
        url_details: dict[str, Any] = self.data["request_url_details"]
        url_data: list[dict[str, Any]] = []

        for url, details in url_details.items():
            methods = details.get("methods", {})
            top_method = max(methods.items(), key=lambda x: x[1])[0] if methods else ""
            if isinstance(top_method, str):
                top_method = top_method.replace("-", "")

            # Unique IPs
            if "unique_ips" in details and isinstance(details.get("unique_ips"), (int, float)):
                unique_ips = int(details.get("unique_ips") or 0)
            else:
                client_ips_val = details.get("client_ips", set())
                unique_ips = len(client_ips_val) if isinstance(client_ips_val, (set, list, tuple)) else 0

            # Average response time
            avg_response_time = self._parse_avg_response_time(details)

            # Status statistics
            status_counts = details.get("status_counts", {})
            top_status = self._get_top_status(status_counts)
            error_rate = self._calculate_error_rate(status_counts)

            # Count
            count = details.get("count", 0)
            if not isinstance(count, (int, float)):
                count = 0

            # Client info - Top Client IP (가장 많이 요청한 IP)
            client_ip = details.get("top_client_ip", "")
            country = ""
            if client_ip:
                country = self.get_country_code(client_ip)
            elif "client_info" in details:
                client_info = details.get("client_info", {})
                client_ip = client_info.get("ip", "")
                country = client_info.get("country", "")
            elif "client_ips" in details:
                client_ips = details.get("client_ips", set())
                if isinstance(client_ips, (set, list, tuple)) and client_ips:
                    client_ip = next(iter(client_ips))
                    country = self.get_country_code(client_ip)

            url_data.append(
                {
                    "Count": count,
                    "Client": client_ip,
                    "Country": country,
                    "Method": top_method,
                    "Request": url,
                    "Unique IPs": unique_ips,
                    "Avg Response Time": avg_response_time,
                    "Top Status": top_status,
                    "Error Rate (%)": error_rate,
                }
            )

        # Sort and limit
        url_data_sorted = sorted(url_data, key=lambda x: x["Count"], reverse=True)[: SheetConfig.TOP_URL_LIMIT]

        if not url_data_sorted:
            return

        ws = self.create_sheet(SHEET_NAMES.URL_TOP100)
        headers = list(HEADERS.URL_DETAILED)

        self.write_header_row(ws, headers)
        rows_written = self.write_data_rows(ws, url_data_sorted, headers)

        # Add summary row
        self._add_summary_row(ws, url_data_sorted, headers)

        self.finalize_sheet(ws, headers, rows_written)

    def _write_simple_url_sheet(self) -> None:
        """Write simple URL count statistics."""
        url_counts = self.data["request_url_counts"]

        url_data = [{"Count": count, "Request": url} for url, count in url_counts.items()]
        url_data_sorted = sorted(url_data, key=lambda x: x["Count"], reverse=True)[: SheetConfig.TOP_URL_LIMIT]

        if not url_data_sorted:
            return

        ws = self.create_sheet(SHEET_NAMES.URL_TOP100)
        headers = list(HEADERS.URL_SIMPLE)

        self.write_header_row(ws, headers)
        rows_written = self.write_data_rows(ws, url_data_sorted, headers)

        # Add summary row
        self._add_summary_row(ws, url_data_sorted, headers)

        self.finalize_sheet(ws, headers, rows_written)

    def _parse_avg_response_time(self, details: dict[str, Any]) -> float:
        """Parse average response time from details."""
        if "avg_response_time" not in details:
            return 0.0

        avg_rt_val = details.get("avg_response_time")

        if isinstance(avg_rt_val, str):
            try:
                return float(avg_rt_val.strip())
            except (ValueError, TypeError):
                return 0.0
        elif isinstance(avg_rt_val, (int, float)):
            return float(avg_rt_val)

        return 0.0

    def _get_top_status(self, status_counts: dict[str, int]) -> str:
        """Get most common status code."""
        if not status_counts:
            return ""

        # Filter valid status codes
        valid_counts = {k: v for k, v in status_counts.items() if k and str(k).strip() not in ("", "-", "N/A")}

        if not valid_counts:
            return ""

        top_status = max(valid_counts.items(), key=lambda x: x[1])[0]
        return str(top_status)

    def _calculate_error_rate(self, status_counts: dict[str, int]) -> float:
        """Calculate error rate from status counts."""
        if not status_counts:
            return 0.0

        total = sum(status_counts.values())
        if total == 0:
            return 0.0

        error_count = sum(count for status, count in status_counts.items() if str(status).startswith(("4", "5")))

        return round((error_count / total) * 100, 2)

    def _add_summary_row(
        self,
        ws,
        data: list[dict[str, Any]],
        headers: list[str],
    ) -> None:
        """Add summary/total row at the end."""
        total_row = len(data) + 2
        total_count = sum(row.get("Count", 0) for row in data)

        if len(headers) >= 7:
            # Detailed view
            cell = ws.cell(row=total_row, column=1, value=f"합계: {total_count:,}")
            cell.font = self.styles.font_bold
            cell.alignment = self.styles.align_left
            cell.border = self.styles.thin_border

            for col_idx in range(2, len(headers) + 1):
                cell = ws.cell(row=total_row, column=col_idx, value="")
                cell.border = self.styles.thin_border
        else:
            # Simple view
            cell = ws.cell(row=total_row, column=1, value="합계")
            cell.font = self.styles.font_bold
            cell.border = self.styles.thin_border

            cell = ws.cell(row=total_row, column=2, value=total_count)
            cell.font = self.styles.font_bold
            cell.alignment = self.styles.align_right
            cell.number_format = "#,##0"
            cell.border = self.styles.thin_border
