"""functions/reports/log_analyzer/reporter/security_events.py - 보안 이벤트 분석 시트 Writer.

Classification 필드를 기반으로 보안 이벤트(WAF Block, Rate Limit 등)를
분류하고 시트로 생성합니다.
"""

from __future__ import annotations

import logging

from .base import BaseSheetWriter, SummarySheetHelper, get_column_letter
from .config import SheetConfig

logger = logging.getLogger(__name__)

SHEET_NAME_SECURITY_EVENTS = "보안 이벤트"
HEADERS_SECURITY_EVENTS = ("시간", "클라이언트 IP", "분류", "사유", "URL", "상태 코드")

SECURITY_EVENTS_COLUMN_WIDTHS = {
    "시간": 22,
    "클라이언트 IP": 18,
    "분류": 12,
    "사유": 30,
    "URL": 60,
    "상태 코드": 10,
}


class SecurityEventsSheetWriter(BaseSheetWriter):
    """Creates security events (HTTP classification) analysis sheet."""

    def write(self) -> None:
        """Create security events analysis sheet."""
        try:
            classification_stats = self.data.get("classification_stats", {})
            if not classification_stats:
                return

            distribution = classification_stats.get("distribution", {})
            security_events = classification_stats.get("security_events", [])

            # Ambiguous/Severe가 없으면 시트 생성 안함
            ambiguous_count = distribution.get("Ambiguous", 0)
            severe_count = distribution.get("Severe", 0)

            if ambiguous_count == 0 and severe_count == 0 and not security_events:
                return

            ws = self.create_sheet(SHEET_NAME_SECURITY_EVENTS)
            helper = SummarySheetHelper(ws)

            # Title
            helper.add_title("보안 이벤트 (HTTP 요청 분류)")

            # Classification Distribution
            if distribution:
                helper.add_section("요청 분류 통계")
                total = sum(distribution.values())

                for cls, count in sorted(distribution.items(), key=lambda x: -x[1]):
                    pct = (count / total * 100) if total > 0 else 0
                    highlight = None
                    if cls == "Severe":
                        highlight = "danger"
                    elif cls == "Ambiguous":
                        highlight = "warning"
                    helper.add_item(cls, f"{count:,} ({pct:.1f}%)", highlight=highlight)

                helper.add_blank_row()

            # Description
            helper.add_section("분류 설명")
            helper.add_item("Acceptable", "정상적인 HTTP 요청")
            helper.add_item("Ambiguous", "모호한 요청 (잠재적 공격 가능성)", highlight="warning")
            helper.add_item("Severe", "심각한 이상 요청 (HTTP Desync 공격 의심)", highlight="danger")
            helper.add_blank_row()

            # Security Events Table
            if security_events:
                helper.add_section(f"⚠️ Ambiguous/Severe 요청 상세 ({len(security_events)}건)")

                # 테이블 헤더 작성
                start_row = helper.row
                headers = list(HEADERS_SECURITY_EVENTS)
                self.write_header_row(ws, headers, row=start_row)

                # 데이터 행 작성
                border = self.styles.thin_border
                for row_idx, event in enumerate(security_events, start=start_row + 1):
                    ts = event.get("timestamp")
                    timestamp_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, "strftime") else str(ts)

                    values = [
                        timestamp_str,
                        event.get("client_ip", ""),
                        event.get("classification", ""),
                        event.get("reason", "")[:50],
                        event.get("url", "")[:80],
                        event.get("status_code", ""),
                    ]

                    classification = event.get("classification", "")
                    fill = self.styles.danger_fill if classification == "Severe" else self.styles.warning_fill

                    for col_idx, value in enumerate(values, 1):
                        cell = ws.cell(row=row_idx, column=col_idx, value=value)
                        cell.border = border
                        cell.fill = fill

                        if col_idx == 1:  # Timestamp
                            cell.alignment = self.styles.align_center
                        elif col_idx == 6:  # Status code
                            cell.alignment = self.styles.align_right
                        else:
                            cell.alignment = self.styles.align_left

                # 컬럼 너비 적용
                for col, header in enumerate(headers, 1):
                    width = SECURITY_EVENTS_COLUMN_WIDTHS.get(header, 15)
                    ws.column_dimensions[get_column_letter(col)].width = width

                # Auto filter
                if security_events:
                    last_col = get_column_letter(len(headers))
                    ws.auto_filter.ref = f"A{start_row}:{last_col}{start_row + len(security_events)}"

            # Security recommendations
            helper.add_blank_row()
            helper.add_section("대응 권장 사항")
            helper.add_item("Ambiguous 요청", "WAF 규칙 검토, 클라이언트 IP 모니터링")
            helper.add_item("Severe 요청", "즉시 조사 필요, HTTP Desync 공격 가능성 확인")
            helper.add_item("참고 문서", "AWS ALB Desync Mitigation Mode 설정 확인")

            ws.freeze_panes = ws.cell(row=start_row + 1, column=1) if security_events else None
            ws.sheet_view.zoomScale = SheetConfig.ZOOM_SCALE

        except Exception as e:
            logger.error(f"보안 이벤트 시트 생성 중 오류: {e}")
