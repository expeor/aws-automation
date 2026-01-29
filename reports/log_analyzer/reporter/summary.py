"""Summary sheet writer for ALB log analysis report."""

from __future__ import annotations

import logging

from .base import BaseSheetWriter, SummarySheetHelper
from .config import SHEET_NAMES, SheetConfig

logger = logging.getLogger(__name__)


class SummarySheetWriter(BaseSheetWriter):
    """Creates the summary/overview sheet for the report.

    Essential information only:
    1. ALB Info (identification)
    2. Analysis Period
    3. Key Metrics (requests, IPs, error rate, latency)
    4. Status Code Summary
    5. Security Alerts (if any)
    """

    def write(self) -> None:
        """Create the summary sheet."""
        try:
            ws = self.workbook.create_sheet(SHEET_NAMES.SUMMARY, 0)
            helper = SummarySheetHelper(ws)

            # 1. Title
            helper.add_title("ALB 로그 분석 요약")

            # 2. ALB Info
            s3_uri = self.data.get("s3_uri", "")
            _, account_id, region, _ = self._parse_s3_uri(s3_uri)
            alb_name = self.data.get("alb_name", "N/A")

            helper.add_section("ALB 정보")
            helper.add_item("ALB 이름", alb_name)
            helper.add_item("계정", account_id, number_format="@")
            helper.add_item("리전", region)

            # 3. Analysis Period
            helper.add_blank_row()
            helper.add_section("분석 기간")

            # Use actual log time if available, otherwise requested time
            actual_start = self.data.get("actual_start_time")
            actual_end = self.data.get("actual_end_time")

            if actual_start and actual_start != "N/A":
                helper.add_item("시작", actual_start)
                helper.add_item("종료", actual_end)
            else:
                helper.add_item("시작", self.data.get("start_time", "N/A"))
                helper.add_item("종료", self.data.get("end_time", "N/A"))

            helper.add_item("타임존", self.data.get("timezone", "N/A"))

            # 4. Key Metrics
            helper.add_blank_row()
            helper.add_section("핵심 지표")

            total_requests = (
                self.data.get("elb_2xx_count", 0)
                + self.data.get("elb_3xx_count", 0)
                + self.data.get("elb_4xx_count", 0)
                + self.data.get("elb_5xx_count", 0)
            )
            helper.add_item("총 요청 수", f"{total_requests:,}")
            helper.add_item("고유 클라이언트 IP", f"{self.data.get('unique_client_ips', 0):,}")

            # Error rate with highlighting
            error_rate = self._calculate_error_rate()
            error_rate_value = float(error_rate.replace("%", "")) if error_rate != "N/A" else 0
            highlight = "danger" if error_rate_value >= 5 else ("warning" if error_rate_value >= 1 else None)
            helper.add_item("에러율 (4xx+5xx)", error_rate, highlight=highlight)

            # Response time percentiles
            percentiles = self.data.get("response_time_percentiles", {})
            if percentiles:
                p50 = percentiles.get("p50", 0) * 1000
                p99 = percentiles.get("p99", 0) * 1000
                helper.add_item("P50 응답시간", f"{p50:.0f}ms")
                highlight = "danger" if p99 > 3000 else ("warning" if p99 > 1000 else None)
                helper.add_item("P99 응답시간", f"{p99:.0f}ms", highlight=highlight)

            # 5. Status Code Summary
            helper.add_blank_row()
            helper.add_section("상태 코드")

            elb_2xx = self.data.get("elb_2xx_count", 0)
            elb_4xx = self.data.get("elb_4xx_count", 0)
            elb_5xx = self.data.get("elb_5xx_count", 0)
            backend_5xx = self.data.get("backend_5xx_count", 0)

            # Calculate percentages
            if total_requests > 0:
                helper.add_item("2xx 성공", f"{elb_2xx:,} ({elb_2xx / total_requests * 100:.1f}%)")
                if elb_4xx > 0:
                    helper.add_item(
                        "4xx 클라이언트 에러",
                        f"{elb_4xx:,} ({elb_4xx / total_requests * 100:.1f}%)",
                        highlight="warning",
                    )
                if elb_5xx > 0:
                    helper.add_item(
                        "5xx 서버 에러",
                        f"{elb_5xx:,} ({elb_5xx / total_requests * 100:.1f}%)",
                        highlight="danger",
                    )
                if backend_5xx > 0:
                    helper.add_item(
                        "Backend 5xx",
                        f"{backend_5xx:,} ({backend_5xx / total_requests * 100:.1f}%)",
                        highlight="danger",
                    )
            else:
                helper.add_item("2xx 성공", f"{elb_2xx:,}")

            # 6. Security Alerts (only if issues exist)
            abuse_count = len(self.get_matching_abuse_ips())
            classification_stats = self.data.get("classification_stats", {})
            ambiguous_count = classification_stats.get("distribution", {}).get("Ambiguous", 0)
            severe_count = classification_stats.get("distribution", {}).get("Severe", 0)

            if abuse_count > 0 or ambiguous_count > 0 or severe_count > 0:
                helper.add_blank_row()
                helper.add_section("⚠️ 보안 경고")

                if abuse_count > 0:
                    abuse_requests = self._calculate_abuse_requests()
                    helper.add_item(
                        "Abuse IP 탐지",
                        f"{abuse_count:,}개 IP ({abuse_requests:,}건 요청)",
                        highlight="danger",
                    )

                if severe_count > 0:
                    helper.add_item(
                        "Severe 요청 (Desync 의심)",
                        f"{severe_count:,}건",
                        highlight="danger",
                    )

                if ambiguous_count > 0:
                    helper.add_item(
                        "Ambiguous 요청",
                        f"{ambiguous_count:,}건",
                        highlight="warning",
                    )

            # Set zoom
            ws.sheet_view.zoomScale = SheetConfig.ZOOM_SCALE

        except Exception as e:
            logger.error(f"Summary 시트 생성 중 오류 발생: {e}")

    def _parse_s3_uri(self, s3_uri: str) -> tuple[str, str, str, str]:
        """Parse S3 URI into components."""
        bucket_name = account_id = region = service_prefix = "N/A"

        if not s3_uri:
            return bucket_name, account_id, region, service_prefix

        try:
            path = s3_uri.replace("s3://", "")
            parts = path.split("/")

            if parts:
                bucket_name = parts[0]

            if "/AWSLogs/" in path:
                prefix_part = path.split("/AWSLogs/")[0]
                service_prefix = prefix_part.split("/", 1)[1] if "/" in prefix_part else prefix_part
                awslogs_part = path.split("/AWSLogs/")[1]
                awslogs_parts = awslogs_part.split("/")

                if awslogs_parts:
                    account_id = awslogs_parts[0]
                if len(awslogs_parts) > 2:
                    region = awslogs_parts[2]

        except Exception as e:
            logger.warning(f"S3 URI 파싱 중 오류: {e}")

        return bucket_name, account_id, region, service_prefix

    def _calculate_error_rate(self) -> str:
        """Calculate error rate percentage."""
        try:
            total_requests = (
                self.data.get("elb_2xx_count", 0)
                + self.data.get("elb_3xx_count", 0)
                + self.data.get("elb_4xx_count", 0)
                + self.data.get("elb_5xx_count", 0)
            )

            if total_requests == 0:
                return "0.0%"

            error_requests = self.data.get("elb_4xx_count", 0) + self.data.get("elb_5xx_count", 0)
            return f"{(error_requests / total_requests) * 100:.1f}%"

        except Exception as e:
            logger.error(f"에러율 계산 중 오류: {e}")
            return "N/A"

    def _calculate_abuse_requests(self) -> int:
        """Calculate total requests from abuse IPs."""
        try:
            client_ip_counts = self.data.get("client_ip_counts", {})
            if not isinstance(client_ip_counts, dict):
                return 0

            matching_abuse_ips = self.get_matching_abuse_ips()
            return sum(int(client_ip_counts.get(ip, 0) or 0) for ip in matching_abuse_ips)
        except Exception as e:
            logger.debug("Failed to calculate abuse IP requests: %s", e)
            return 0
