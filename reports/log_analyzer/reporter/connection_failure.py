"""Connection failure analysis sheet writer."""

from __future__ import annotations

import logging

from .base import BaseSheetWriter, SummarySheetHelper, get_column_letter
from .config import SheetConfig

logger = logging.getLogger(__name__)

SHEET_NAME_CONNECTION_FAILURE = "연결 실패 분석"
HEADERS_TARGET_FAILURES = ("Target", "Target Group", "실패 수")

TARGET_FAILURE_COLUMN_WIDTHS = {
    "Target": 30,
    "Target Group": 25,
    "실패 수": 12,
}


class ConnectionFailureSheetWriter(BaseSheetWriter):
    """Creates connection failure analysis sheet."""

    def write(self) -> None:
        """Create connection failure analysis sheet."""
        try:
            failures = self.data.get("connection_failures", {})
            if not failures:
                return

            # 실패가 하나도 없으면 시트 생성 안함
            total_failures = (
                failures.get("request_failures", 0)
                + failures.get("target_failures", 0)
                + failures.get("response_failures", 0)
            )
            if total_failures == 0:
                return

            ws = self.create_sheet(SHEET_NAME_CONNECTION_FAILURE)
            helper = SummarySheetHelper(ws)

            # Title
            helper.add_title("연결 실패 분석")

            # Summary
            helper.add_section("실패 유형별 통계")
            total = failures.get("total_requests", 0)
            helper.add_item("총 요청 수", f"{total:,}")

            req_failures = failures.get("request_failures", 0)
            req_rate = failures.get("request_failure_rate", 0)
            highlight = "danger" if req_rate > 1 else ("warning" if req_rate > 0.1 else None)
            helper.add_item("Request 실패", f"{req_failures:,} ({req_rate:.2f}%)", highlight=highlight)

            target_failures = failures.get("target_failures", 0)
            target_rate = failures.get("target_failure_rate", 0)
            highlight = "danger" if target_rate > 1 else ("warning" if target_rate > 0.1 else None)
            helper.add_item("Target 연결 실패", f"{target_failures:,} ({target_rate:.2f}%)", highlight=highlight)

            resp_failures = failures.get("response_failures", 0)
            resp_rate = failures.get("response_failure_rate", 0)
            highlight = "danger" if resp_rate > 1 else ("warning" if resp_rate > 0.1 else None)
            helper.add_item("Response 전송 실패", f"{resp_failures:,} ({resp_rate:.2f}%)", highlight=highlight)

            helper.add_blank_row()

            # Description
            helper.add_section("실패 유형 설명")
            helper.add_item("Request 실패", "클라이언트 연결이 끊어짐 (request_processing_time = -1)")
            helper.add_item("Target 연결 실패", "백엔드 서버에 연결할 수 없음 (target_processing_time = -1)")
            helper.add_item("Response 전송 실패", "응답 전송 중 클라이언트 연결 끊김 (response_processing_time = -1)")

            # Target별 실패 상세
            target_failures_detail = failures.get("target_failures_detail", [])
            if target_failures_detail:
                helper.add_blank_row()
                helper.add_section("Target별 연결 실패 Top 20")

                # 테이블 헤더 작성
                start_row = helper.row
                headers = list(HEADERS_TARGET_FAILURES)
                self.write_header_row(ws, headers, row=start_row)

                # 데이터 행 작성
                data_rows = [
                    {
                        "Target": d.get("target", ""),
                        "Target Group": d.get("target_group", ""),
                        "실패 수": d.get("count", 0),
                    }
                    for d in target_failures_detail
                ]
                self.write_data_rows(ws, data_rows, headers, start_row=start_row + 1, highlight_abuse=False)

                # 컬럼 너비 적용
                for col, header in enumerate(headers, 1):
                    width = TARGET_FAILURE_COLUMN_WIDTHS.get(header, 15)
                    ws.column_dimensions[get_column_letter(col)].width = width

            ws.sheet_view.zoomScale = SheetConfig.ZOOM_SCALE

        except Exception as e:
            logger.error(f"연결 실패 분석 시트 생성 중 오류: {e}")
