"""functions/reports/log_analyzer/reporter/ssl_security.py - SSL/TLS 보안 분석 시트 Writer.

SSL/TLS 프로토콜 버전, 암호화 스위트 분포를 분석하여 보안 현황 시트를 생성합니다.
"""

from __future__ import annotations

import logging

from .base import BaseSheetWriter, SummarySheetHelper, get_column_letter
from .config import SheetConfig

logger = logging.getLogger(__name__)

SHEET_NAME_SSL_SECURITY = "TLS 보안 분석"
HEADERS_WEAK_TLS = ("클라이언트 IP", "TLS 버전", "요청 수")

WEAK_TLS_COLUMN_WIDTHS = {
    "클라이언트 IP": 20,
    "TLS 버전": 15,
    "요청 수": 12,
}


class SSLSecuritySheetWriter(BaseSheetWriter):
    """Creates SSL/TLS security analysis sheet."""

    def write(self) -> None:
        """Create SSL/TLS security analysis sheet."""
        try:
            ssl_stats = self.data.get("ssl_stats", {})
            if not ssl_stats:
                return

            protocol_dist = ssl_stats.get("protocol_distribution", {})
            cipher_dist = ssl_stats.get("cipher_distribution", {})

            # 데이터가 없으면 시트 생성 안함
            if not protocol_dist and not cipher_dist:
                return

            ws = self.create_sheet(SHEET_NAME_SSL_SECURITY)
            helper = SummarySheetHelper(ws)

            # Title
            helper.add_title("TLS 보안 분석")

            # TLS Protocol Distribution
            if protocol_dist:
                helper.add_section("TLS 프로토콜 버전 분포")
                total_tls = sum(protocol_dist.values())

                for protocol, count in sorted(protocol_dist.items(), key=lambda x: -x[1]):
                    pct = (count / total_tls * 100) if total_tls > 0 else 0
                    # 취약 TLS 버전 경고
                    highlight = None
                    if protocol in ("TLSv1.0", "TLSv1.1"):
                        highlight = "danger"
                    helper.add_item(protocol, f"{count:,} ({pct:.1f}%)", highlight=highlight)

                helper.add_blank_row()

            # Cipher Suite Distribution
            if cipher_dist:
                helper.add_section("암호 스위트 Top 10")
                total_cipher = sum(cipher_dist.values())

                for cipher, count in sorted(cipher_dist.items(), key=lambda x: -x[1])[:10]:
                    pct = (count / total_cipher * 100) if total_cipher > 0 else 0
                    helper.add_item(cipher[:40], f"{count:,} ({pct:.1f}%)")

                helper.add_blank_row()

            # Weak TLS Clients
            weak_tls_clients = ssl_stats.get("weak_tls_clients", [])
            if weak_tls_clients:
                helper.add_section("⚠️ 취약 TLS 사용 클라이언트 (TLSv1.0/1.1)")

                # 테이블 헤더 작성
                start_row = helper.row
                headers = list(HEADERS_WEAK_TLS)
                self.write_header_row(ws, headers, row=start_row)

                # 데이터 행 작성
                data_rows = [
                    {
                        "클라이언트 IP": d.get("client_ip", ""),
                        "TLS 버전": d.get("protocol", ""),
                        "요청 수": d.get("count", 0),
                    }
                    for d in weak_tls_clients
                ]

                # Write rows with danger highlighting
                border = self.styles.thin_border
                for row_idx, row_data in enumerate(data_rows, start=start_row + 1):
                    for col_idx, header in enumerate(headers, 1):
                        value = row_data.get(header, "")
                        cell = ws.cell(row=row_idx, column=col_idx, value=value)
                        cell.border = border
                        cell.fill = self.styles.danger_fill
                        if header == "요청 수":
                            cell.alignment = self.styles.align_right
                            cell.number_format = "#,##0"
                        else:
                            cell.alignment = self.styles.align_center

                # 컬럼 너비 적용
                for col, header in enumerate(headers, 1):
                    width = WEAK_TLS_COLUMN_WIDTHS.get(header, 15)
                    ws.column_dimensions[get_column_letter(col)].width = width

            # Security recommendations
            helper.add_blank_row()
            helper.add_section("보안 권장 사항")
            helper.add_item("TLSv1.0/1.1", "즉시 비활성화 권장 (PCI-DSS, HIPAA 미준수)")
            helper.add_item("TLSv1.2", "현재 표준, 유지 권장")
            helper.add_item("TLSv1.3", "최신 표준, 업그레이드 권장")

            ws.sheet_view.zoomScale = SheetConfig.ZOOM_SCALE

        except Exception as e:
            logger.error(f"TLS 보안 분석 시트 생성 중 오류: {e}")
