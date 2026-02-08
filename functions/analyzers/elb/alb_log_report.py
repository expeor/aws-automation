"""ALB 로그 분석 - 리포트 생성 함수

Excel/HTML 리포트 생성 로직
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


def _generate_reports(ctx, analyzer, analysis_results: dict[str, Any], output_dir: str) -> dict[str, str]:
    """출력 설정에 따라 Excel/HTML 보고서 생성

    Args:
        ctx: ExecutionContext (output_config 포함)
        analyzer: ALBLogAnalyzer 인스턴스
        analysis_results: 분석 결과 딕셔너리
        output_dir: 출력 디렉토리

    Returns:
        생성된 파일 경로 딕셔너리 {"excel": "...", "html": "..."}
    """
    from functions.reports.log_analyzer import ALBExcelReporter

    report_paths: dict[str, str] = {}

    # 출력 설정 확인
    should_excel = ctx.should_output_excel() if hasattr(ctx, "should_output_excel") else True
    should_html = ctx.should_output_html() if hasattr(ctx, "should_output_html") else True

    # Excel 보고서 생성 (기본 - 최적화된 상세 리포트)
    if should_excel:
        report_filename = _generate_report_filename(analyzer, analysis_results)
        report_path = os.path.join(output_dir, report_filename)

        reporter = ALBExcelReporter(data=analysis_results, output_dir=output_dir)
        final_report_path = reporter.generate_report(report_path)
        report_paths["excel"] = final_report_path

    # HTML 보고서 생성 (요약 대시보드)
    if should_html:
        console.print("   HTML 보고서 생성 중...")
        html_path = _generate_html_report(ctx, analyzer, analysis_results, output_dir)
        if html_path:
            console.print("   [green]✓ HTML 보고서 생성 완료[/green]")
            report_paths["html"] = html_path

            # HTML만 생성한 경우 브라우저에서 자동 열기
            if not should_excel:
                from core.shared.io.html import open_in_browser

                output_config = ctx.get_output_config() if hasattr(ctx, "get_output_config") else None
                if output_config is None or output_config.auto_open:
                    open_in_browser(html_path)

    return report_paths


def _generate_html_report(ctx, analyzer, analysis_results: dict[str, Any], output_dir: str) -> str | None:
    """HTML 요약 보고서 생성

    ALB 로그 분석의 주요 지표를 시각화하는 HTML 대시보드 생성.
    Excel 리포트의 상세 데이터를 보완하는 용도.

    레이아웃:
        [개요 섹션] ELB 상태 코드 / 정상 응답 비율 게이지 / 시간대별 요청 트렌드
        [트래픽 분석 섹션] 국가별 분포 / Top 클라이언트 IP / Top 요청 URL
        [요청 분석 섹션] HTTP 메서드 / User-Agent / 클라이언트 상태 코드 / Target별 분포
        [성능 분석 섹션] 응답 시간 백분위 / 응답 시간 구간 분포 / 데이터 전송량 / Backend 상태 코드
        [에러 분석 섹션] ELB vs Backend 에러 / 에러 원인 / URL별 에러율 / 시간대별 에러율 / 에러 트렌드
    """
    try:
        from core.shared.io.html import HTMLReport

        # 기본 정보 추출
        total_logs = analysis_results.get("log_lines_count", 0)
        alb_name = analysis_results.get("alb_name", "ALB")
        unique_ips = analysis_results.get("unique_client_ips", 0)

        # 에러 카운트
        elb_2xx = analysis_results.get("elb_2xx_count", 0)
        elb_3xx = analysis_results.get("elb_3xx_count", 0)
        elb_4xx = analysis_results.get("elb_4xx_count", 0)
        elb_5xx = analysis_results.get("elb_5xx_count", 0)
        backend_4xx = analysis_results.get("backend_4xx_count", 0)
        backend_5xx = analysis_results.get("backend_5xx_count", 0)
        long_response = analysis_results.get("long_response_count", 0)

        # 정상 응답 비율 계산
        total_responses = elb_2xx + elb_3xx + elb_4xx + elb_5xx
        success_rate = ((elb_2xx + elb_3xx) / total_responses * 100) if total_responses > 0 else 0

        # 실제 요청한 IP 중 악성 IP 매칭
        client_ip_counts = analysis_results.get("client_ip_counts", {})
        abuse_ips_all = set(analysis_results.get("abuse_ips_list", []))
        matching_abuse_ips = [(ip, client_ip_counts.get(ip, 0)) for ip in client_ip_counts if ip in abuse_ips_all]
        matching_abuse_ips = sorted(matching_abuse_ips, key=lambda x: -x[1])
        abuse_count = len(matching_abuse_ips)

        # HTMLReport 생성
        subtitle = f"분석 기간: {analyzer.start_datetime.strftime('%Y-%m-%d %H:%M')} ~ {analyzer.end_datetime.strftime('%Y-%m-%d %H:%M')}"
        report = HTMLReport(title=f"ALB 로그 분석: {alb_name}", subtitle=subtitle)

        # 요약 카드
        report.add_summary(
            [
                ("총 요청", f"{total_logs:,}", None),
                ("고유 IP", f"{unique_ips:,}", None),
                ("정상 응답률", f"{success_rate:.1f}%", "success" if success_rate >= 99 else None),
                ("ELB 4xx", f"{elb_4xx:,}", "warning" if elb_4xx > 0 else None),
                ("ELB 5xx", f"{elb_5xx:,}", "danger" if elb_5xx > 0 else None),
                ("Backend 5xx", f"{backend_5xx:,}", "danger" if backend_5xx > 0 else None),
                ("느린 응답 (≥1s)", f"{long_response:,}", "warning" if long_response > 0 else None),
                ("악성 IP", f"{abuse_count:,}", "danger" if abuse_count > 0 else None),
            ]
        )

        # =============================================================================
        # [개요 섹션]
        # =============================================================================
        report.add_section_title("📊 개요")

        # 1. ELB 상태 코드 분포 (도넛 차트)
        status_data = [
            ("2xx 성공", elb_2xx),
            ("3xx 리다이렉트", elb_3xx),
            ("4xx 클라이언트 에러", elb_4xx),
            ("5xx 서버 에러", elb_5xx),
        ]
        status_data = [(name, count) for name, count in status_data if count > 0]
        if status_data:
            report.add_pie_chart("ELB 상태 코드 분포", status_data, doughnut=True)

        # 2. 정상 응답 비율 게이지 (NEW)
        report.add_gauge_chart(
            "정상 응답 비율",
            value=success_rate,
            max_value=100,
            thresholds=[(0.9, "#ee6666"), (0.95, "#fac858"), (1, "#91cc75")],
            unit="%",
        )

        # 3. 시간대별 요청 트렌드 (라인 차트) - CloudWatch 스타일 적응형 해상도
        all_timestamps: list[datetime] = []
        is_error_list: list[int | float] = []

        for key in ["ELB 2xx Count", "ELB 3xx Count", "ELB 4xx Count", "ELB 5xx Count"]:
            log_data = analysis_results.get(key, {})
            if isinstance(log_data, dict):
                timestamps = log_data.get("timestamps", [])
                is_error = 1 if ("4xx" in key or "5xx" in key) else 0
                for ts in timestamps:
                    if ts and hasattr(ts, "timestamp"):
                        all_timestamps.append(ts)
                        is_error_list.append(is_error)

        if all_timestamps:
            values: dict[str, list[int | float]] = {
                "전체 요청": [1] * len(all_timestamps),
                "에러 (4xx+5xx)": is_error_list,
            }
            report.add_time_series_chart(
                "시간대별 요청 트렌드",
                timestamps=all_timestamps,
                values=values,
                aggregation="sum",
                area=True,
            )

        # =============================================================================
        # [트래픽 분석 섹션]
        # =============================================================================
        report.add_section_title("🌍 트래픽 분석")

        # 4. 국가별 요청 분포 (바 차트)
        country_stats = analysis_results.get("country_statistics", {})
        if country_stats:
            sorted_countries = [
                (country, data.get("count", 0) if isinstance(data, dict) else data)
                for country, data in country_stats.items()
            ]
            sorted_countries = sorted(sorted_countries, key=lambda x: -x[1])[:15]
            if sorted_countries:
                countries = [c[0] for c in sorted_countries]
                counts = [c[1] for c in sorted_countries]
                report.add_bar_chart(
                    "국가별 요청 분포",
                    categories=countries,
                    series=[("요청 수", counts)],
                    horizontal=True,
                )

        # 5. Top 클라이언트 IP (바 차트)
        if client_ip_counts:
            sorted_ips = sorted(client_ip_counts.items(), key=lambda x: -x[1])[:10]
            if sorted_ips:
                ips = [ip for ip, _ in sorted_ips]
                counts = [count for _, count in sorted_ips]
                report.add_bar_chart(
                    "Top 클라이언트 IP",
                    categories=ips,
                    series=[("요청 수", counts)],
                    horizontal=True,
                )

        # 6. Top 요청 URL (바 차트)
        url_counts = analysis_results.get("request_url_counts", {})
        if url_counts:
            sorted_urls = sorted(url_counts.items(), key=lambda x: -x[1])[:15]
            if sorted_urls:
                urls = [url[:60] + "..." if len(url) > 60 else url for url, _ in sorted_urls]
                url_counts_list = [count for _, count in sorted_urls]
                report.add_bar_chart(
                    "Top 요청 URL",
                    categories=urls,
                    series=[("요청 수", url_counts_list)],
                    horizontal=True,
                )

        # =============================================================================
        # [요청 분석 섹션]
        # =============================================================================
        report.add_section_title("📝 요청 분석")

        # 7. HTTP 메서드 분포 (도넛 차트)
        request_url_details = analysis_results.get("request_url_details", {})
        if request_url_details:
            method_totals: dict[str, int] = {}
            for url_detail in request_url_details.values():
                if isinstance(url_detail, dict):
                    methods = url_detail.get("methods", {})
                    for method, cnt in methods.items():
                        if method and isinstance(cnt, int):
                            method_totals[method] = method_totals.get(method, 0) + cnt
            if method_totals:
                sorted_methods = sorted(method_totals.items(), key=lambda x: -x[1])
                method_data: list[tuple[str, int | float]] = [(m, c) for m, c in sorted_methods if m.strip()]
                if method_data:
                    report.add_pie_chart("HTTP 메서드 분포", method_data, doughnut=True)

        # 8. Top User-Agent (바 차트)
        user_agent_counts = analysis_results.get("user_agent_counts", {})
        if user_agent_counts:
            sorted_uas = sorted(user_agent_counts.items(), key=lambda x: -x[1])[:10]
            if sorted_uas:
                uas = [ua[:50] + "..." if len(ua) > 50 else ua for ua, _ in sorted_uas]
                counts = [count for _, count in sorted_uas]
                report.add_bar_chart(
                    "Top User-Agent",
                    categories=uas,
                    series=[("요청 수", counts)],
                    horizontal=True,
                )

        # 9. 클라이언트 상태 코드 분포 (바 차트)
        client_status = analysis_results.get("client_status_statistics", {})
        if client_status:
            status_totals: dict[str, int] = {}
            for ip_stats in client_status.values():
                if isinstance(ip_stats, dict):
                    for code, count in ip_stats.items():
                        if isinstance(count, int):
                            status_totals[code] = status_totals.get(code, 0) + count
            if status_totals:
                top_codes = sorted(status_totals.items(), key=lambda x: -x[1])[:10]
                if top_codes:
                    codes = [str(code) for code, _ in top_codes]
                    status_counts: list[int | float] = [count for _, count in top_codes]
                    status_series: list[tuple[str, list[int | float]]] = [("요청 수", status_counts)]
                    report.add_bar_chart(
                        "클라이언트 상태 코드 분포",
                        categories=codes,
                        series=status_series,
                    )

        # 10. Target별 요청 분포 (바 차트)
        target_request_stats = analysis_results.get("target_request_stats", {})
        if target_request_stats:
            sorted_targets = sorted(
                target_request_stats.items(),
                key=lambda x: x[1].get("total_requests", 0),
                reverse=True,
            )[:10]
            if sorted_targets:
                target_names = [name[:40] + "..." if len(name) > 40 else name for name, _ in sorted_targets]
                request_counts = [stats.get("total_requests", 0) for _, stats in sorted_targets]
                error_counts = [stats.get("error_count", 0) for _, stats in sorted_targets]
                report.add_bar_chart(
                    "Target별 요청 분포",
                    categories=target_names,
                    series=[
                        ("정상 요청", [r - e for r, e in zip(request_counts, error_counts, strict=True)]),
                        ("에러", error_counts),
                    ],
                    stacked=True,
                    horizontal=True,
                )

        # =============================================================================
        # [성능 분석 섹션]
        # =============================================================================
        report.add_section_title("⚡ 성능 분석")

        # NEW: TPS 시계열 차트 (처리량)
        tps_time_series = analysis_results.get("tps_time_series", [])
        if tps_time_series:
            tps_timestamps = [item.get("timestamp") for item in tps_time_series if item.get("timestamp")]
            tps_values = [item.get("tps", 0) for item in tps_time_series]
            if tps_timestamps and any(v > 0 for v in tps_values):
                bucket_minutes = analysis_results.get("bucket_minutes", 15)
                report.add_time_series_chart(
                    f"TPS 추이 ({bucket_minutes}분 단위)",
                    timestamps=tps_timestamps,
                    values={"TPS": tps_values},
                    aggregation="last",
                    area=True,
                )

        # NEW: 시간대별 Latency 추이 차트 (P50/P90/P99)
        if tps_time_series:
            tps_timestamps = [item.get("timestamp") for item in tps_time_series if item.get("timestamp")]
            p50_values = [item.get("p50_ms", 0) for item in tps_time_series]
            p90_values = [item.get("p90_ms", 0) for item in tps_time_series]
            p99_values = [item.get("p99_ms", 0) for item in tps_time_series]
            if tps_timestamps and any(v > 0 for v in p50_values + p90_values + p99_values):
                bucket_minutes = analysis_results.get("bucket_minutes", 15)
                report.add_time_series_chart(
                    f"응답 시간 추이 ({bucket_minutes}분 단위)",
                    timestamps=tps_timestamps,
                    values={
                        "P50 (ms)": p50_values,
                        "P90 (ms)": p90_values,
                        "P99 (ms)": p99_values,
                    },
                    aggregation="last",
                    area=False,
                )

        # NEW: SLA 준수율 게이지 차트 (3개)
        sla_compliance = analysis_results.get("sla_compliance", {})
        if sla_compliance:
            # 100ms 기준
            if "under_100ms" in sla_compliance:
                sla_100ms = sla_compliance["under_100ms"]
                report.add_gauge_chart(
                    "SLA: 100ms 미만 응답률",
                    value=sla_100ms.get("rate", 0),
                    max_value=100,
                    thresholds=[(0.9, "#ee6666"), (0.95, "#fac858"), (1, "#91cc75")],
                    unit="%",
                )

            # 500ms 기준
            if "under_500ms" in sla_compliance:
                sla_500ms = sla_compliance["under_500ms"]
                report.add_gauge_chart(
                    "SLA: 500ms 미만 응답률",
                    value=sla_500ms.get("rate", 0),
                    max_value=100,
                    thresholds=[(0.95, "#ee6666"), (0.99, "#fac858"), (1, "#91cc75")],
                    unit="%",
                )

            # 1s 기준
            if "under_1s" in sla_compliance:
                sla_1s = sla_compliance["under_1s"]
                report.add_gauge_chart(
                    "SLA: 1초 미만 응답률",
                    value=sla_1s.get("rate", 0),
                    max_value=100,
                    thresholds=[(0.99, "#ee6666"), (0.999, "#fac858"), (1, "#91cc75")],
                    unit="%",
                )

        # 11. 응답 시간 백분위수 (바 차트)
        response_time_percentiles = analysis_results.get("response_time_percentiles", {})
        if response_time_percentiles:
            percentile_labels = ["P50", "P90", "P95", "P99", "평균"]
            percentile_values = [
                round(response_time_percentiles.get("p50", 0) * 1000, 1),
                round(response_time_percentiles.get("p90", 0) * 1000, 1),
                round(response_time_percentiles.get("p95", 0) * 1000, 1),
                round(response_time_percentiles.get("p99", 0) * 1000, 1),
                round(response_time_percentiles.get("avg", 0) * 1000, 1),
            ]
            if any(v > 0 for v in percentile_values):
                report.add_bar_chart(
                    "응답 시간 분포 (ms)",
                    categories=percentile_labels,
                    series=[("응답 시간", percentile_values)],
                )

        # 12. 응답 시간 구간 분포 - 바 차트 (DuckDB에서 계산된 데이터 우선 사용)
        response_time_distribution = analysis_results.get("response_time_distribution", {})
        long_response_times = analysis_results.get("long_response_times", [])
        if response_time_distribution:
            # DuckDB에서 계산된 분포 사용
            if any(v > 0 for v in response_time_distribution.values()):
                report.add_bar_chart(
                    "응답 시간 구간 분포",
                    categories=list(response_time_distribution.keys()),
                    series=[("요청 수", list(response_time_distribution.values()))],
                )
        else:
            # Fallback: long_response_times에서 계산
            if long_response_times or response_time_percentiles:
                # 구간별 카운트 계산
                buckets = {"<100ms": 0, "100-500ms": 0, "500ms-1s": 0, "1-3s": 0, ">3s": 0}

                # long_response_times에서 응답 시간 추출
                for r in long_response_times:
                    rt = r.get("response_time")
                    if rt is not None:
                        rt_ms = rt * 1000
                        if rt_ms < 100:
                            buckets["<100ms"] += 1
                        elif rt_ms < 500:
                            buckets["100-500ms"] += 1
                        elif rt_ms < 1000:
                            buckets["500ms-1s"] += 1
                        elif rt_ms < 3000:
                            buckets["1-3s"] += 1
                        else:
                            buckets[">3s"] += 1

                # 값이 있으면 차트 추가
                if any(v > 0 for v in buckets.values()):
                    report.add_bar_chart(
                        "응답 시간 구간 분포",
                        categories=list(buckets.keys()),
                        series=[("요청 수", list(buckets.values()))],
                    )

        # 13. 데이터 전송량 (바 차트)
        total_received = analysis_results.get("total_received_bytes") or 0
        total_sent = analysis_results.get("total_sent_bytes") or 0
        if total_received > 0 or total_sent > 0:

            def to_gb(b: int) -> float:
                return b / (1024**3) if b else 0

            transfer_data = [
                ("수신 (Received)", to_gb(total_received)),
                ("송신 (Sent)", to_gb(total_sent)),
            ]
            transfer_data = [(name, val) for name, val in transfer_data if val > 0]
            if transfer_data:
                report.add_bar_chart(
                    "데이터 전송량 (GB)",
                    categories=[name for name, _ in transfer_data],
                    series=[("GB", [round(val, 2) for _, val in transfer_data])],
                )

        # 14. Backend 상태 코드 분포 (도넛 차트)
        backend_status_data = [
            ("4xx 클라이언트 에러", backend_4xx),
            ("5xx 서버 에러", backend_5xx),
        ]
        backend_status_data = [(name, count) for name, count in backend_status_data if count > 0]
        if backend_status_data:
            report.add_pie_chart("Backend 상태 코드 분포", backend_status_data, doughnut=True)

        # NEW: Target별 Latency 비교 차트
        target_latency_stats = analysis_results.get("target_latency_stats", {})
        if target_latency_stats:
            # Top 10 targets by request count
            sorted_targets = sorted(
                target_latency_stats.items(),
                key=lambda x: x[1].get("total_requests", 0),
                reverse=True,
            )[:10]
            if sorted_targets:
                target_names = [name[:40] + "..." if len(name) > 40 else name for name, _ in sorted_targets]
                p50_values = [stats.get("p50_ms", 0) for _, stats in sorted_targets]
                p90_values = [stats.get("p90_ms", 0) for _, stats in sorted_targets]
                p99_values = [stats.get("p99_ms", 0) for _, stats in sorted_targets]
                report.add_bar_chart(
                    "Target별 응답 시간 비교 (ms)",
                    categories=target_names,
                    series=[
                        ("P50", p50_values),
                        ("P90", p90_values),
                        ("P99", p99_values),
                    ],
                    horizontal=True,
                )

        # NEW: 처리 시간 분해 분석 (Request/Target/Response)
        processing_time_breakdown = analysis_results.get("processing_time_breakdown", {})
        if processing_time_breakdown:
            req_data = processing_time_breakdown.get("request", {})
            target_data = processing_time_breakdown.get("target", {})
            resp_data = processing_time_breakdown.get("response", {})

            if any([req_data, target_data, resp_data]):
                # P50/P90/P99별 각 단계의 처리 시간
                report.add_bar_chart(
                    "처리 단계별 응답 시간 (ms)",
                    categories=["P50", "P90", "P99"],
                    series=[
                        (
                            "Request (ALB)",
                            [req_data.get("p50_ms", 0), req_data.get("p90_ms", 0), req_data.get("p99_ms", 0)],
                        ),
                        (
                            "Target (Backend)",
                            [target_data.get("p50_ms", 0), target_data.get("p90_ms", 0), target_data.get("p99_ms", 0)],
                        ),
                        (
                            "Response (전송)",
                            [resp_data.get("p50_ms", 0), resp_data.get("p90_ms", 0), resp_data.get("p99_ms", 0)],
                        ),
                    ],
                )

        # NEW: 연결 실패 분석
        connection_failures = analysis_results.get("connection_failures", {})
        if connection_failures and connection_failures.get("target_failures", 0) > 0:
            failure_data = [
                ("Request 실패", connection_failures.get("request_failures", 0)),
                ("Target 연결 실패", connection_failures.get("target_failures", 0)),
                ("Response 전송 실패", connection_failures.get("response_failures", 0)),
            ]
            failure_data = [(name, count) for name, count in failure_data if count > 0]
            if failure_data:
                report.add_pie_chart("연결 실패 유형 분포", failure_data, doughnut=True)

            # Target별 실패 상세
            target_failures_detail = connection_failures.get("target_failures_detail", [])
            if target_failures_detail:
                target_names = [
                    f"{d['target_group']}({d['target']})" if d["target_group"] else d["target"]
                    for d in target_failures_detail[:10]
                ]
                failure_counts = [d["count"] for d in target_failures_detail[:10]]
                report.add_bar_chart(
                    "Target별 연결 실패",
                    categories=target_names,
                    series=[("실패 수", failure_counts)],
                    horizontal=True,
                )

        # 느린 응답 테이블 (성능 분석 섹션)
        if long_response_times:
            slow_rows = []
            for r in long_response_times[:100]:
                response_time = r.get("response_time")
                response_time_str = f"{response_time:.3f}" if response_time is not None else "-"
                slow_rows.append(
                    [
                        str(r.get("timestamp") or "")[:19],
                        r.get("client_ip") or "",
                        (r.get("request") or "")[:50],
                        response_time_str,
                        r.get("elb_status_code") or "",
                        r.get("target_status_code") or "",
                    ]
                )
            report.add_table(
                title="🐢 느린 응답 Top 100",
                headers=["시간", "Client IP", "URL", "응답 시간(s)", "ELB Status", "Target Status"],
                rows=slow_rows,
                page_size=20,
            )

        # =============================================================================
        # [프로토콜 분석 섹션]
        # =============================================================================
        report.add_section_title("🔐 프로토콜 분석")

        # NEW: HTTP 버전 분포
        http_version_distribution = analysis_results.get("http_version_distribution", {})
        if http_version_distribution:
            http_version_data = [(version, count) for version, count in http_version_distribution.items() if count > 0]
            if http_version_data:
                report.add_pie_chart("HTTP 프로토콜 버전 분포", http_version_data, doughnut=True)

        # NEW: SSL/TLS 프로토콜 분포
        ssl_stats = analysis_results.get("ssl_stats", {})
        if ssl_stats:
            protocol_dist = ssl_stats.get("protocol_distribution", {})
            if protocol_dist:
                tls_data = [(proto, count) for proto, count in protocol_dist.items() if count > 0]
                if tls_data:
                    report.add_pie_chart("TLS 프로토콜 버전 분포", tls_data, doughnut=True)

            cipher_dist = ssl_stats.get("cipher_distribution", {})
            if cipher_dist:
                cipher_names = list(cipher_dist.keys())[:10]
                cipher_counts = [cipher_dist[c] for c in cipher_names]
                if cipher_names:
                    report.add_bar_chart(
                        "암호 스위트 Top 10",
                        categories=cipher_names,
                        series=[("요청 수", cipher_counts)],
                        horizontal=True,
                    )

            # 취약 TLS 경고
            weak_tls_clients = ssl_stats.get("weak_tls_clients", [])
            if weak_tls_clients:
                report.add_table(
                    title=f"⚠️ 취약 TLS 사용 클라이언트 ({len(weak_tls_clients)}개)",
                    headers=["클라이언트 IP", "TLS 버전", "요청 수"],
                    rows=[[c["client_ip"], c["protocol"], c["count"]] for c in weak_tls_clients[:20]],
                    page_size=10,
                )

        # NEW: Actions 분포
        actions_stats = analysis_results.get("actions_stats", {})
        if actions_stats:
            # 'None'과 'Forward'를 제외한 의미 있는 액션만 표시
            meaningful_actions = [
                (action, count)
                for action, count in actions_stats.items()
                if action not in ("None", "Forward", "Other") and count > 0
            ]
            if meaningful_actions:
                report.add_pie_chart("ALB Actions 분포 (WAF/인증/리다이렉트)", meaningful_actions, doughnut=True)

        # =============================================================================
        # [보안 분석 섹션]
        # =============================================================================
        report.add_section_title("🛡️ 보안 분석")

        # NEW: Classification 분포 (Desync 탐지)
        classification_stats = analysis_results.get("classification_stats", {})
        if classification_stats:
            class_dist = classification_stats.get("distribution", {})
            if class_dist:
                # Ambiguous/Severe가 있으면 경고
                ambiguous_count = class_dist.get("Ambiguous", 0)
                severe_count = class_dist.get("Severe", 0)

                if ambiguous_count > 0 or severe_count > 0:
                    class_data = [(cls, count) for cls, count in class_dist.items() if count > 0]
                    report.add_pie_chart("HTTP 요청 분류 (Desync 탐지)", class_data, doughnut=True)

            # 보안 이벤트 테이블 (전체 표시)
            security_events = classification_stats.get("security_events", [])
            if security_events:
                report.add_table(
                    title=f"🚨 보안 이벤트 (Ambiguous/Severe 요청) - {len(security_events)}건",
                    headers=["시간", "클라이언트 IP", "분류", "사유", "URL"],
                    rows=[
                        [
                            e["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                            if hasattr(e["timestamp"], "strftime")
                            else str(e["timestamp"]),
                            e["client_ip"],
                            e["classification"],
                            e["reason"][:30] + "..." if len(e.get("reason", "")) > 30 else e.get("reason", ""),
                            e["url"][:50] + "..." if len(e.get("url", "")) > 50 else e.get("url", ""),
                        ]
                        for e in security_events
                    ],
                    page_size=50,
                )

        # 악성 IP 테이블 (보안 분석 섹션)
        if matching_abuse_ips:
            report.add_table(
                title=f"🚫 악성 IP 목록 ({len(matching_abuse_ips)}개)",
                headers=["IP 주소", "요청 수", "상태"],
                rows=[[ip, count, "AbuseIPDB 등록"] for ip, count in matching_abuse_ips[:50]],
                page_size=20,
            )

        # =============================================================================
        # [에러 분석 섹션]
        # =============================================================================
        report.add_section_title("🚨 에러 분석")

        # 15. ELB vs Backend 에러 비교 (바 차트)
        if elb_4xx > 0 or elb_5xx > 0 or backend_4xx > 0 or backend_5xx > 0:
            report.add_bar_chart(
                "ELB vs Backend 에러 비교",
                categories=["4xx 에러", "5xx 에러"],
                series=[
                    ("ELB", [elb_4xx, elb_5xx]),
                    ("Backend", [backend_4xx, backend_5xx]),
                ],
            )

        # 16. 에러 원인 분포 (바 차트)
        error_reason_counts = analysis_results.get("error_reason_counts", {})
        if error_reason_counts:
            sorted_reasons = sorted(error_reason_counts.items(), key=lambda x: -x[1])[:10]
            if sorted_reasons:
                reasons = [reason for reason, _ in sorted_reasons]
                counts = [count for _, count in sorted_reasons]
                report.add_bar_chart(
                    "에러 원인 분포",
                    categories=reasons,
                    series=[("건수", counts)],
                    horizontal=True,
                )

        # 17. URL별 에러율 (바 차트)
        url_error_stats = analysis_results.get("url_error_stats", {})
        if url_error_stats:
            sorted_urls = sorted(
                [(url, stats) for url, stats in url_error_stats.items() if stats.get("error_count", 0) > 0],
                key=lambda x: x[1].get("error_rate", 0),
                reverse=True,
            )[:15]
            if sorted_urls:
                url_names = [url[:50] + "..." if len(url) > 50 else url for url, _ in sorted_urls]
                error_rates = [stats.get("error_rate", 0) for _, stats in sorted_urls]
                report.add_bar_chart(
                    "URL별 에러율 (%)",
                    categories=url_names,
                    series=[("에러율", error_rates)],
                    horizontal=True,
                )

        # 18. 시간대별 에러율 추이 (NEW) - 라인 차트
        error_timestamps: list[datetime] = []
        error_types: list[str] = []

        for key, error_type in [("ELB 4xx Count", "4xx"), ("ELB 5xx Count", "5xx")]:
            log_data = analysis_results.get(key, {})
            if isinstance(log_data, dict):
                timestamps = log_data.get("timestamps", [])
                for ts in timestamps:
                    if ts and hasattr(ts, "timestamp"):
                        error_timestamps.append(ts)
                        error_types.append(error_type)

        # 에러율 추이 계산 (시간 버킷별)
        if all_timestamps and error_timestamps:
            from collections import defaultdict

            # 버킷 크기 결정 (시간 범위에 따라)
            min_time = min(all_timestamps) if all_timestamps else datetime.now()
            max_time = max(all_timestamps) if all_timestamps else datetime.now()
            total_seconds = (max_time - min_time).total_seconds()
            total_hours = total_seconds / 3600

            if total_hours <= 3:
                bucket_minutes = 5
            elif total_hours <= 24:
                bucket_minutes = 15
            elif total_hours <= 24 * 7:
                bucket_minutes = 60
            else:
                bucket_minutes = 240

            bucket_seconds = bucket_minutes * 60

            # 버킷별 전체 요청과 에러 카운트
            total_buckets: dict[datetime, int] = defaultdict(int)
            error_buckets: dict[datetime, int] = defaultdict(int)

            for ts in all_timestamps:
                bucket_start = datetime.fromtimestamp((ts.timestamp() // bucket_seconds) * bucket_seconds)
                total_buckets[bucket_start] += 1

            for ts in error_timestamps:
                bucket_start = datetime.fromtimestamp((ts.timestamp() // bucket_seconds) * bucket_seconds)
                error_buckets[bucket_start] += 1

            # 에러율 계산
            if total_buckets:
                sorted_buckets = sorted(total_buckets.keys())
                error_rates_time: list[float] = []

                for bucket in sorted_buckets:
                    total = total_buckets[bucket]
                    errors = error_buckets.get(bucket, 0)
                    rate = (errors / total * 100) if total > 0 else 0
                    error_rates_time.append(round(rate, 2))

                # 시간 포맷
                if total_hours <= 24:
                    time_format = "%H:%M"
                elif total_hours <= 24 * 7:
                    time_format = "%m/%d %H:%M"
                else:
                    time_format = "%m/%d"

                categories = [ts.strftime(time_format) for ts in sorted_buckets]

                if any(r > 0 for r in error_rates_time):
                    report.add_line_chart(
                        f"시간대별 에러율 추이 ({bucket_minutes}분 단위)",
                        categories=categories,
                        series=[("에러율 (%)", error_rates_time)],
                        area=True,
                        smooth=True,
                    )

        # 19. 시간대별 에러 트렌드 (라인 차트)
        if error_timestamps:
            is_4xx: list[int | float] = [1 if t == "4xx" else 0 for t in error_types]
            is_5xx: list[int | float] = [1 if t == "5xx" else 0 for t in error_types]

            error_values: dict[str, list[int | float]] = {
                "4xx 에러": is_4xx,
                "5xx 에러": is_5xx,
            }
            report.add_time_series_chart(
                "시간대별 에러 트렌드",
                timestamps=error_timestamps,
                values=error_values,
                aggregation="sum",
                area=True,
            )

        # =============================================================================
        # 테이블 섹션
        # =============================================================================
        def format_bytes(b: int | None) -> str:
            if b is None:
                return "0 B"
            if b >= 1024**3:
                return f"{b / 1024**3:.2f} GB"
            elif b >= 1024**2:
                return f"{b / 1024**2:.2f} MB"
            elif b >= 1024:
                return f"{b / 1024:.2f} KB"
            return f"{b} B"

        # 분석 정보 테이블
        report.add_table(
            title="분석 정보",
            headers=["항목", "값"],
            rows=[
                ["S3 경로", analysis_results.get("s3_uri", "")],
                [
                    "분석 기간 (요청)",
                    f"{analysis_results.get('start_time', '')} ~ {analysis_results.get('end_time', '')}",
                ],
                [
                    "실제 데이터 기간",
                    f"{analysis_results.get('actual_start_time', '')} ~ {analysis_results.get('actual_end_time', '')}",
                ],
                ["타임존", analysis_results.get("timezone", "")],
                ["총 로그 라인", f"{total_logs:,}"],
                ["로그 파일 수", f"{analysis_results.get('log_files_count') or 0:,}"],
                ["수신 데이터", format_bytes(total_received)],
                ["송신 데이터", format_bytes(total_sent)],
            ],
            sortable=False,
            searchable=False,
        )

        # 파일명 생성 및 저장
        report_filename = _generate_report_filename(analyzer, analysis_results).replace(".xlsx", ".html")
        html_path = os.path.join(output_dir, report_filename)

        report.save(html_path, auto_open=False)
        return html_path

    except Exception as e:
        console.print(f"[yellow]⚠️ HTML 보고서 생성 실패: {e}[/yellow]")
        import traceback

        traceback.print_exc()
        return None


def _generate_report_filename(analyzer, analysis_results: dict[str, Any]) -> str:
    """보고서 파일명 생성"""
    import secrets

    try:
        # 시간 범위 정보
        start_dt = analyzer.start_datetime
        end_dt = analyzer.end_datetime
        time_diff = end_dt - start_dt
        hours = int(time_diff.total_seconds() / 3600)

        if hours < 24:
            pass
        else:
            hours // 24
            hours % 24

        # 계정/리전 정보
        account_id = "unknown"
        region = "unknown"

        s3_uri = f"s3://{analyzer.bucket_name}/{analyzer.prefix}"
        if "/AWSLogs/" in s3_uri:
            path = s3_uri.replace("s3://", "")
            parts = path.split("/AWSLogs/")[1].split("/")
            if len(parts) >= 3:
                account_id = parts[0]
                region = parts[2]

        # ALB 이름
        alb_name = analysis_results.get("alb_name") or "alb"
        alb_name = str(alb_name).strip().replace("/", "-").replace("\\", "-")

        # 파일명 생성
        random_suffix = secrets.token_hex(4)
        return f"{account_id}_{region}_{alb_name}_report_{random_suffix}.xlsx"

    except Exception as e:
        logger.debug("Failed to generate report filename: %s", e)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"ALB_Log_Analysis_{timestamp}.xlsx"
