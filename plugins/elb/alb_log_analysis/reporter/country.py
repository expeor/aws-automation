"""Country statistics sheet writer."""

from __future__ import annotations

import logging

from .base import BaseSheetWriter
from .config import HEADERS, SHEET_NAMES, SPECIAL_COUNTRY_CODES, SheetConfig

logger = logging.getLogger(__name__)


class CountrySheetWriter(BaseSheetWriter):
    """Creates the country statistics sheet."""

    def write(self) -> None:
        """Create country statistics sheet."""
        try:
            country_stats = self.data.get("country_statistics", {})
            if not country_stats:
                return

            client_ip_counts: dict[str, int] = (
                self.data.get("client_ip_counts", {}) or {}
            )
            ip_country_mapping: dict[str, str | None] = (
                self.data.get("ip_country_mapping", {}) or {}
            )

            # Calculate country request counts
            country_request_counts: dict[str, int] = {}
            for ip, req_count in client_ip_counts.items():
                country_code = ip_country_mapping.get(ip) or "ZZ"
                if country_code in SPECIAL_COUNTRY_CODES:
                    country_code = "ZZ"
                country_request_counts[country_code] = country_request_counts.get(
                    country_code, 0
                ) + int(req_count or 0)

            total_requests = sum(country_request_counts.values()) or 1

            # Build country data
            country_data = []
            for country_code, ip_count in country_stats.items():
                total_req = country_request_counts.get(country_code, 0)
                percentage = round((total_req / total_requests) * 100, 2)
                country_data.append(
                    {
                        "Count": total_req,
                        "Country": country_code,
                        "IP Count": ip_count,
                        "Percentage": percentage,
                    }
                )

            # Sort by count, limit to top countries
            country_data_sorted = sorted(
                country_data, key=lambda x: x["Count"], reverse=True
            )[: SheetConfig.TOP_COUNTRY_LIMIT]

            if not country_data_sorted:
                return

            # Create sheet
            ws = self.create_sheet(SHEET_NAMES.COUNTRY_STATS)
            headers = list(HEADERS.COUNTRY_STATS)

            self.write_header_row(ws, headers)
            rows_written = self.write_data_rows(
                ws, country_data_sorted, headers, highlight_abuse=False
            )
            self.finalize_sheet(ws, headers, rows_written)

        except Exception as e:
            logger.error(f"국가별 통계 시트 생성 중 오류: {e}")
