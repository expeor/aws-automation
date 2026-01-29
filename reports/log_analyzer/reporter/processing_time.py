"""Processing time breakdown sheet writer."""

from __future__ import annotations

import logging

from .base import BaseSheetWriter, SummarySheetHelper
from .config import SheetConfig

logger = logging.getLogger(__name__)

SHEET_NAME_PROCESSING_TIME = "처리 단계별 응답 시간"


class ProcessingTimeSheetWriter(BaseSheetWriter):
    """Creates processing time breakdown analysis sheet."""

    def write(self) -> None:
        """Create processing time breakdown sheet."""
        try:
            breakdown = self.data.get("processing_time_breakdown", {})
            if not breakdown:
                return

            ws = self.create_sheet(SHEET_NAME_PROCESSING_TIME)
            helper = SummarySheetHelper(ws)

            # Title
            helper.add_title("처리 단계별 응답 시간 분석")

            # Description
            helper.add_section("분석 설명")
            helper.add_item("Request Processing", "ALB가 요청을 수신하고 백엔드로 전달하는 시간")
            helper.add_item("Target Processing", "백엔드 서버가 요청을 처리하는 시간 (가장 중요)")
            helper.add_item("Response Processing", "ALB가 응답을 클라이언트에 전송하는 시간")
            helper.add_blank_row()

            # Request Processing Time
            req_data = breakdown.get("request", {})
            if req_data:
                helper.add_section("Request Processing Time (ALB)")
                helper.add_item("P50 (ms)", req_data.get("p50_ms", 0), number_format="0.000")
                helper.add_item("P90 (ms)", req_data.get("p90_ms", 0), number_format="0.000")
                helper.add_item("P99 (ms)", req_data.get("p99_ms", 0), number_format="0.000")
                helper.add_item("평균 (ms)", req_data.get("avg_ms", 0), number_format="0.000")
                helper.add_blank_row()

            # Target Processing Time
            target_data = breakdown.get("target", {})
            if target_data:
                helper.add_section("Target Processing Time (Backend)")
                helper.add_item("P50 (ms)", target_data.get("p50_ms", 0), number_format="0.000")
                helper.add_item("P90 (ms)", target_data.get("p90_ms", 0), number_format="0.000")
                helper.add_item("P99 (ms)", target_data.get("p99_ms", 0), number_format="0.000")
                helper.add_item("평균 (ms)", target_data.get("avg_ms", 0), number_format="0.000")
                helper.add_blank_row()

            # Response Processing Time
            resp_data = breakdown.get("response", {})
            if resp_data:
                helper.add_section("Response Processing Time (전송)")
                helper.add_item("P50 (ms)", resp_data.get("p50_ms", 0), number_format="0.000")
                helper.add_item("P90 (ms)", resp_data.get("p90_ms", 0), number_format="0.000")
                helper.add_item("P99 (ms)", resp_data.get("p99_ms", 0), number_format="0.000")
                helper.add_item("평균 (ms)", resp_data.get("avg_ms", 0), number_format="0.000")

            # Adjust column widths
            ws.column_dimensions["A"].width = 30
            ws.column_dimensions["B"].width = 20
            ws.sheet_view.zoomScale = SheetConfig.ZOOM_SCALE

        except Exception as e:
            logger.error(f"처리 시간 분해 시트 생성 중 오류: {e}")
