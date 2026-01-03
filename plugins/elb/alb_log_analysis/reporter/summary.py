"""Summary sheet writer for ALB log analysis report."""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from .base import BaseSheetWriter, SummarySheetHelper
from .config import SHEET_NAMES, SheetConfig

logger = logging.getLogger(__name__)


class SummarySheetWriter(BaseSheetWriter):
    """Creates the summary/overview sheet for the report."""

    def write(self) -> None:
        """Create the summary sheet."""
        try:
            ws = self.workbook.create_sheet(SHEET_NAMES.SUMMARY, 0)
            helper = SummarySheetHelper(ws)

            # 1. Title
            helper.add_title("ALB 로그 분석 보고서")

            # 2. Analysis Info
            s3_uri = self.data.get("s3_uri", "")
            bucket_name, account_id, region, _ = self._parse_s3_uri(s3_uri)
            alb_name = self.data.get("alb_name", "N/A")

            helper.add_section("분석 정보")
            helper.add_item("계정 번호", account_id, number_format="@")
            helper.add_item("ALB 이름", alb_name)
            helper.add_item("S3 버킷", bucket_name)
            helper.add_item("리전", region)

            # 3. Analysis Period
            helper.add_blank_row()
            helper.add_section("분석 기간")
            helper.add_item("요청 시작 시간", self.data.get("start_time", "N/A"))
            helper.add_item("요청 종료 시간", self.data.get("end_time", "N/A"))
            helper.add_item("타임존", self.data.get("timezone", "N/A"))

            if (
                self.data.get("actual_start_time")
                and self.data.get("actual_start_time") != "N/A"
            ):
                helper.add_item("실제 로그 시작", self.data.get("actual_start_time", "N/A"))
                helper.add_item("실제 로그 종료", self.data.get("actual_end_time", "N/A"))

            # 4. Data Statistics
            helper.add_blank_row()
            helper.add_section("데이터 통계")
            helper.add_item("총 로그 라인 수", f"{self.data.get('log_lines_count', 0):,}개")
            helper.add_item("분석된 로그 파일 수", f"{self.data.get('log_files_count', 0):,}개")
            helper.add_item(
                "고유 클라이언트 IP 수", f"{self.data.get('unique_client_ips', 0):,}개"
            )
            helper.add_item(
                "총 수신 바이트",
                self.format_bytes(self.data.get("total_received_bytes", 0)),
            )
            helper.add_item(
                "총 송신 바이트",
                self.format_bytes(self.data.get("total_sent_bytes", 0)),
            )
            helper.add_item("평균 응답 시간", self._calculate_average_response_time())
            helper.add_item("전체 에러율", self._calculate_error_rate())

            # 5. HTTP Status Code Statistics
            helper.add_blank_row()
            self._add_status_code_statistics(helper)

            # 6. Security Information
            helper.add_blank_row()
            helper.add_section("보안 정보")

            abuse_count = len(self.get_matching_abuse_ips())
            highlight = "danger" if abuse_count > 0 else None
            helper.add_item("탐지된 Abuse IP", f"{abuse_count:,}개", highlight=highlight)

            # Abuse IP request count
            abuse_total_requests = self._calculate_abuse_requests()
            highlight = "danger" if abuse_total_requests > 0 else None
            helper.add_item(
                "전체 Abuse IP 요청 수",
                f"{abuse_total_requests:,}개",
                highlight=highlight,
            )

            # 7. Request Pattern Analysis
            helper.add_blank_row()
            helper.add_section("요청 패턴 분석")
            top_urls = self._get_top_request_urls(SheetConfig.SUMMARY_TOP_ITEMS)
            helper.add_list_section("상위 요청 URL", top_urls, suffix="회")

            helper.add_blank_row()
            top_agents = self._get_top_user_agents(SheetConfig.SUMMARY_TOP_ITEMS)
            helper.add_list_section("상위 User Agent", top_agents, suffix="회")

            # 8. Geographic Analysis
            helper.add_blank_row()
            helper.add_section("지리적 분석")
            top_countries = self._get_top_countries(SheetConfig.SUMMARY_TOP_ITEMS)
            helper.add_list_section("상위 국가", top_countries, suffix="개 IP")

            # 9. Performance Analysis
            helper.add_blank_row()
            helper.add_section("성능 분석")
            response_stats = self._calculate_response_time_stats()
            helper.add_item("최대 응답 시간", response_stats["max"])
            helper.add_item("최소 응답 시간", response_stats["min"])
            helper.add_item("중간 응답 시간", response_stats["median"])

            # Set zoom
            ws.sheet_view.zoomScale = SheetConfig.ZOOM_SCALE

        except Exception as e:
            logger.error(f"Summary 시트 생성 중 오류 발생: {e}")

    def _parse_s3_uri(self, s3_uri: str) -> Tuple[str, str, str, str]:
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
                service_prefix = (
                    prefix_part.split("/", 1)[1] if "/" in prefix_part else prefix_part
                )
                awslogs_part = path.split("/AWSLogs/")[1]
                awslogs_parts = awslogs_part.split("/")

                if awslogs_parts:
                    account_id = awslogs_parts[0]
                if len(awslogs_parts) > 2:
                    region = awslogs_parts[2]

        except Exception as e:
            logger.warning(f"S3 URI 파싱 중 오류: {e}")

        return bucket_name, account_id, region, service_prefix

    def _calculate_average_response_time(self) -> str:
        """Calculate average response time from data."""
        try:
            long_response_times = self.data.get("long_response_times", [])
            if not long_response_times or not isinstance(long_response_times, list):
                return "0.000초"

            total_time = 0.0
            valid_count = 0

            for entry in long_response_times:
                if isinstance(entry, dict) and "response_time" in entry:
                    response_time = entry.get("response_time", 0)
                    if isinstance(response_time, (int, float)) and response_time > 0:
                        total_time += float(response_time)
                        valid_count += 1

            if valid_count == 0:
                return "0.000초"

            return f"{total_time / valid_count:.3f}초"

        except Exception as e:
            logger.error(f"평균 응답 시간 계산 중 오류: {e}")
            return "N/A"

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

            error_requests = self.data.get("elb_4xx_count", 0) + self.data.get(
                "elb_5xx_count", 0
            )
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
            return sum(
                int(client_ip_counts.get(ip, 0) or 0) for ip in matching_abuse_ips
            )
        except Exception:
            return 0

    def _add_status_code_statistics(self, helper: SummarySheetHelper) -> None:
        """Add HTTP status code statistics section."""
        helper.add_section("HTTP 상태 코드 통계")

        total_requests = (
            self.data.get("elb_2xx_count", 0)
            + self.data.get("elb_3xx_count", 0)
            + self.data.get("elb_4xx_count", 0)
            + self.data.get("elb_5xx_count", 0)
        )

        status_codes = [
            ("ELB 2xx", "elb_2xx_count", None),
            ("ELB 3xx", "elb_3xx_count", None),
            ("ELB 4xx", "elb_4xx_count", "warning"),
            ("ELB 5xx", "elb_5xx_count", "danger"),
            ("Backend 4xx", "backend_4xx_count", "warning"),
            ("Backend 5xx", "backend_5xx_count", "danger"),
        ]

        for label, key, highlight_type in status_codes:
            count = self.data.get(key, 0)
            if total_requests > 0 and key.startswith("elb_"):
                percentage = (count / total_requests) * 100
                display_value = f"{count:,}개 ({percentage:.1f}%)"
            else:
                display_value = f"{count:,}개"

            highlight = highlight_type if count > 0 else None
            helper.add_item(label, display_value, highlight=highlight)

    def _get_top_request_urls(self, limit: int) -> List[Tuple[str, int]]:
        """Get top requested URLs."""
        try:
            url_counts = self.data.get("request_url_counts", {})
            if not url_counts:
                return []

            sorted_urls = sorted(url_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_urls[:limit]
        except Exception as e:
            logger.error(f"상위 요청 URL 계산 중 오류: {e}")
            return []

    def _get_top_user_agents(self, limit: int) -> List[Tuple[str, int]]:
        """Get top user agents."""
        try:
            ua_counts = self.data.get("user_agent_counts", {})
            if not ua_counts:
                return []

            sorted_agents = sorted(ua_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_agents[:limit]
        except Exception as e:
            logger.error(f"상위 User Agent 계산 중 오류: {e}")
            return []

    def _get_top_countries(self, limit: int) -> List[Tuple[str, int]]:
        """Get top countries."""
        try:
            country_stats = self.data.get("country_statistics", {})
            if not country_stats:
                return []

            sorted_countries = sorted(
                country_stats.items(), key=lambda x: x[1], reverse=True
            )
            return sorted_countries[:limit]
        except Exception as e:
            logger.error(f"상위 국가 계산 중 오류: {e}")
            return []

    def _calculate_response_time_stats(self) -> Dict[str, str]:
        """Calculate response time statistics."""
        try:
            long_response_times = self.data.get("long_response_times", [])
            if not long_response_times or not isinstance(long_response_times, list):
                return {"max": "N/A", "min": "N/A", "median": "N/A"}

            response_times = []
            for entry in long_response_times:
                if isinstance(entry, dict) and "response_time" in entry:
                    rt = entry.get("response_time", 0)
                    if isinstance(rt, (int, float)) and rt > 0:
                        response_times.append(float(rt))

            if not response_times:
                return {"max": "N/A", "min": "N/A", "median": "N/A"}

            response_times.sort()
            n = len(response_times)

            if n % 2 == 0:
                median = (response_times[n // 2 - 1] + response_times[n // 2]) / 2
            else:
                median = response_times[n // 2]

            return {
                "max": f"{response_times[-1]:.3f}초",
                "min": f"{response_times[0]:.3f}초",
                "median": f"{median:.3f}초",
            }

        except Exception as e:
            logger.error(f"응답 시간 통계 계산 중 오류: {e}")
            return {"max": "N/A", "min": "N/A", "median": "N/A"}
