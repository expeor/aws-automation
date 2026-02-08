"""ALB Excel Reporter - High-Performance Report Generator

Performance-optimized Excel report generator for ALB logs.
Designed for large-scale data processing with memory efficiency.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from secrets import token_hex
from typing import TYPE_CHECKING, Any

from rich.console import Console

if TYPE_CHECKING:
    from openpyxl.workbook import Workbook as OpenpyxlWorkbook

try:
    from core.cli.ui import console, logger, step_progress
except ImportError:
    console = Console()
    logger = logging.getLogger(__name__)
    step_progress = None  # type: ignore[assignment]


class ExcelReportError(Exception):
    """Excel report generation error."""


class ALBExcelReporter:
    """ALB log analysis Excel report generator.

    Usage:
        reporter = ALBExcelReporter(data=analysis_data, output_dir="reports")
        report_path = reporter.generate_report()
    """

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        output_dir: str = "reports",
    ) -> None:
        self.output_dir = output_dir
        self.data: dict[str, Any] = data or {}

        from .reporter.styles import get_style_cache

        self._style_cache = get_style_cache()

    def generate_report(self, report_name: str | None = None) -> str:
        """Generate Excel report."""
        return self._create_report(self.data, report_name)

    def _create_report(
        self,
        data: dict[str, Any],
        report_name: str | None = None,
    ) -> str:
        """Create Excel report from data."""
        from openpyxl import Workbook as OpenpyxlWorkbook

        wb = OpenpyxlWorkbook()
        if wb.active is not None:
            wb.remove(wb.active)

        self._style_cache.register_named_styles(wb)

        if console.is_terminal and step_progress is not None:
            with step_progress("Excel 보고서 생성", total_steps=10, console=console) as tracker:
                callback = tracker.as_callback(include_status=True)
                output_path = self._build_sheets(wb, data, report_name, callback)
        else:
            output_path = self._build_sheets(wb, data, report_name, None)

        return output_path

    def _build_sheets(
        self,
        wb: OpenpyxlWorkbook,
        data: dict[str, Any],
        report_name: str | None,
        progress: Callable[[str, bool], None] | None,
    ) -> str:
        """Build all sheets.

        Sheet order:
        1. Summary (분석 요약)
        2. Country (국가별 통계)
        3. URL (요청 URL Top 100)
        4. Client Status (Client 상태코드 통계)
        5. Target Status (Target 상태코드 통계)
        6. Response Time (응답 시간 Top 100) - includes processing time breakdown
        7. Bytes (데이터 전송량)
        8. TPS Analysis (TPS 분석)
        9. Target Performance (Target 성능 분석)
        10. Abuse IP List (악성 IP 목록)
        11. Security Events (보안 이벤트) - merged abuse requests + security events
        12. Status Codes (상태 코드 참조)

        HTML-only sections (not in Excel):
        - SLA Compliance (게이지 차트로 HTML이 더 적합)
        - Processing Time Breakdown (바 차트로 HTML이 더 적합)
        - Connection Failure Analysis (도넛 차트로 HTML이 더 적합)
        - SSL/TLS Security Analysis (파이 차트로 HTML이 더 적합)
        """
        from .reporter.abuse import AbuseIPSheetWriter, AbuseRequestsSheetWriter
        from .reporter.bytes import BytesSheetWriter
        from .reporter.country import CountrySheetWriter
        from .reporter.response_time import ResponseTimeSheetWriter
        from .reporter.status_code import (
            ClientStatusSheetWriter,
            StatusCodeSheetWriter,
            TargetStatusSheetWriter,
        )
        from .reporter.summary import SummarySheetWriter
        from .reporter.target_performance import TargetPerformanceSheetWriter
        from .reporter.tps import TPSSheetWriter
        from .reporter.url import URLSheetWriter

        def step(msg: str, done: bool = False) -> None:
            if progress:
                progress(msg, done)

        abuse_ips = self._get_matching_abuse_ips(data)

        # 1. Summary
        step("[bold blue]분석 요약 시트 생성중...")
        SummarySheetWriter(wb, data, abuse_ips).write()
        step("[bold blue]분석 요약 완료", True)

        # 2. Country
        if data.get("country_statistics"):
            step("[bold blue]국가별 통계 시트 생성중...")
            CountrySheetWriter(wb, data, abuse_ips).write()
            step("[bold blue]국가별 통계 완료", True)

        # 3. URL
        if data.get("request_url_details") or data.get("request_url_counts"):
            step("[bold blue]요청 URL Top 100 시트 생성중...")
            URLSheetWriter(wb, data, abuse_ips).write()
            step("[bold blue]요청 URL 완료", True)

        # 4. Client status
        if data.get("client_status_statistics"):
            step("[bold blue]Client 상태코드 통계 시트 생성중...")
            ClientStatusSheetWriter(wb, data, abuse_ips).write()
            step("[bold blue]Client 상태코드 완료", True)

        # 5. Target status
        if data.get("target_status_statistics"):
            step("[bold blue]Target 상태코드 통계 시트 생성중...")
            TargetStatusSheetWriter(wb, data, abuse_ips).write()
            step("[bold blue]Target 상태코드 완료", True)

        # 6. Response time (includes processing time breakdown columns)
        if data.get("long_response_times"):
            step("[bold blue]응답 시간 시트 생성중...")
            ResponseTimeSheetWriter(wb, data, abuse_ips).write()
            step("[bold blue]응답 시간 완료", True)

        # 7. Bytes
        if data.get("received_bytes") or data.get("sent_bytes"):
            step("[bold blue]데이터 전송량 시트 생성중...")
            BytesSheetWriter(wb, data, abuse_ips).write()
            step("[bold blue]데이터 전송량 완료", True)

        # 8. TPS Analysis
        if data.get("tps_time_series"):
            step("[bold blue]TPS 분석 시트 생성중...")
            TPSSheetWriter(wb, data, abuse_ips).write()
            step("[bold blue]TPS 분석 완료", True)

        # 9. Target Performance
        if data.get("target_latency_stats"):
            step("[bold blue]Target 성능 분석 시트 생성중...")
            TargetPerformanceSheetWriter(wb, data, abuse_ips).write()
            step("[bold blue]Target 성능 분석 완료", True)

        # 10-11. Abuse IP + Security Events (merged)
        abuse_list, _ = self._get_normalized_abuse_ips(data)
        security_events = data.get("classification_stats", {}).get("security_events", [])

        if abuse_list:
            step("[bold blue]악성 IP 목록 시트 생성중...")
            AbuseIPSheetWriter(wb, data, abuse_ips).write()
            step("[bold blue]악성 IP 목록 완료", True)

        # Create security events sheet if abuse IPs or security events exist
        if abuse_list or security_events:
            step("[bold blue]보안 이벤트 시트 생성중...")
            AbuseRequestsSheetWriter(wb, data, abuse_ips).write()
            step("[bold blue]보안 이벤트 완료", True)

        # 12. Status codes (Reference)
        step("[bold blue]상태 코드 시트 생성중...")
        StatusCodeSheetWriter(wb, data, abuse_ips).write()
        step("[bold blue]상태 코드 완료", True)

        # Save
        step("[bold blue]파일 저장중...")
        output_path = self._save(wb, data, report_name)
        step("[bold green]완료!", True)

        return output_path

    def _save(
        self,
        wb: OpenpyxlWorkbook,
        data: dict[str, Any],
        report_name: str | None,
    ) -> str:
        """Save workbook."""
        if report_name:
            report_path = Path(report_name)
            if report_path.is_absolute() or "/" in report_name or "\\" in report_name:
                path = str(report_path if report_name.endswith(".xlsx") else Path(f"{report_name}.xlsx"))
            else:
                path = str(Path(self.output_dir) / f"{report_name}.xlsx")
        else:
            path = self._generate_filename(data)

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        wb.save(path)
        return path

    def _generate_filename(self, data: dict[str, Any]) -> str:
        """Generate filename from S3 URI."""
        s3_uri = data.get("s3_uri", "")
        account_id = "acct"
        region = "region"

        if "/AWSLogs/" in (s3_uri or ""):
            try:
                parts = s3_uri.replace("s3://", "").split("/AWSLogs/")[1].split("/")
                if len(parts) >= 3:
                    account_id, region = parts[0], parts[2]
            except Exception:
                pass  # nosec B110 - S3 URI parsing fallback to defaults

        alb_name = str(data.get("alb_name") or "alb").strip().replace("/", "-").replace("\\", "-")
        return str(Path(self.output_dir) / f"{account_id}_{region}_{alb_name}_report_{token_hex(4)}.xlsx")

    def _get_matching_abuse_ips(self, data: dict[str, Any]) -> set[str]:
        """Get abuse IPs matching actual client IPs."""
        client_ips = set(data.get("client_ip_counts", {}).keys())
        abuse_list, _ = self._get_normalized_abuse_ips(data)
        return client_ips.intersection(abuse_list)

    def _get_normalized_abuse_ips(self, data: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        """Normalize abuse IP data."""
        excluded = {"abuse_ips", "abuse_ip_details", "timestamp"}

        def valid(ip: Any) -> bool:
            s = str(ip).strip() if ip else ""
            return bool(s) and not any(k in s for k in excluded)

        ips: list[str] = []
        details: dict[str, Any] = {}

        if data.get("abuse_ips_list"):
            ips = [str(ip).strip() for ip in data["abuse_ips_list"] if valid(ip)]
        elif data.get("abuse_ips"):
            abuse = data["abuse_ips"]
            if isinstance(abuse, (list, set)):
                ips = [str(ip).strip() for ip in abuse if valid(ip)]
            elif isinstance(abuse, dict):
                ips = [str(ip).strip() for ip in abuse if valid(ip)]
                details = abuse

        if data.get("abuse_ip_details"):
            details.update(data["abuse_ip_details"])

        return ips, details
