"""
core/tools/analysis/log/alb_analyzer.py - ALB 로그 분석 도구 진입점

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
    - collect_options(ctx): 선택. 추가 옵션 수집.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytz  # type: ignore[import-untyped]
import questionary
from rich.panel import Panel
from rich.table import Table

from cli.ui import (
    console,
    print_step_header,
    print_sub_info,
    print_sub_task_done,
    print_sub_warning,
)
from core.auth import get_context_session
from core.parallel import get_client
from core.tools.cache import get_cache_dir
from core.tools.output import open_in_explorer

if TYPE_CHECKING:
    from cli.flow.context import ExecutionContext

logger = logging.getLogger(__name__)

# 필요한 AWS 권한 목록
REQUIRED_PERMISSIONS = {
    "read": [
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeLoadBalancerAttributes",
        "s3:ListBucket",
        "s3:GetObject",
        "sts:GetCallerIdentity",
    ],
}


def collect_options(ctx) -> None:
    """ALB 로그 분석에 필요한 옵션 수집

    - S3 버킷 경로 (자동 탐색 또는 수동 입력)
    - 시간 범위
    - 타임존

    Args:
        ctx: ExecutionContext
    """
    console.print("\n[bold cyan]ALB 로그 분석 설정[/bold cyan]")

    # 세션 획득 (첫 번째 리전 사용)
    region = ctx.regions[0] if ctx.regions else "ap-northeast-2"
    session = get_context_session(ctx, region)

    # 1. S3 버킷 경로 입력 방식 선택
    bucket_path = _get_bucket_input_with_options(session, ctx)
    ctx.options["bucket"] = bucket_path

    # 2. 시간 범위 입력
    start_time, end_time = _get_time_range_input()
    ctx.options["start_time"] = start_time
    ctx.options["end_time"] = end_time

    # 3. 타임존 입력
    timezone = _get_timezone_input()
    ctx.options["timezone"] = timezone


def run(ctx: ExecutionContext) -> None:
    """ALB 로그 분석 실행

    Args:
        ctx: ExecutionContext (options에 bucket, start_time, end_time, timezone 포함)
    """
    from .alb_log_analysis.alb_log_analyzer import ALBLogAnalyzer

    console.print("[bold]ALB 로그 분석을 시작합니다...[/bold]")

    # 옵션 추출
    bucket = ctx.options.get("bucket")
    start_time = ctx.options.get("start_time")
    end_time = ctx.options.get("end_time")
    timezone = ctx.options.get("timezone", "Asia/Seoul")

    if not bucket:
        console.print("[red]❌ S3 버킷 경로가 설정되지 않았습니다.[/red]")
        return

    # 세션 획득
    region = ctx.regions[0] if ctx.regions else "ap-northeast-2"
    session = get_context_session(ctx, region)
    s3_client = get_client(session, "s3")

    # S3 URI 파싱
    if not bucket.startswith("s3://"):
        bucket = f"s3://{bucket}"

    bucket_parts = bucket.split("/")
    bucket_name = bucket_parts[2]
    prefix = "/".join(bucket_parts[3:]) if len(bucket_parts) > 3 else ""

    # 작업 디렉토리 설정 (temp/alb 하위 사용)
    alb_cache_dir = get_cache_dir("alb")
    gz_dir = os.path.join(alb_cache_dir, "gz")
    log_dir = os.path.join(alb_cache_dir, "log")
    os.makedirs(gz_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    try:
        # Step 1: 로그 분석기 초기화
        print_step_header(1, "로그 분석기 준비 중...")
        analyzer = ALBLogAnalyzer(
            s3_client=s3_client,
            bucket_name=bucket_name,
            prefix=prefix,
            start_datetime=start_time,
            end_datetime=end_time,
            timezone=timezone,
            max_workers=5,
        )

        # Step 2: 로그 다운로드
        print_step_header(2, "로그 다운로드 및 압축 해제 중...")
        downloaded_files = analyzer.download_logs()
        if not downloaded_files:
            print_sub_warning("요청 범위에 해당하는 ALB 로그 파일이 없습니다.")
            print_sub_info("ALB는 5분 단위로 파일을 생성하며, 트래픽이 없으면 파일이 생성되지 않을 수 있습니다.")
            return

        # 압축 해제
        if isinstance(downloaded_files, list) and downloaded_files:
            gz_directory = os.path.dirname(downloaded_files[0]) if isinstance(downloaded_files[0], str) else gz_dir
        else:
            gz_directory = gz_dir

        log_directory = analyzer.decompress_logs(gz_directory)

        # Step 3: 로그 분석
        print_step_header(3, "로그 분석 중...")
        analysis_results = analyzer.analyze_logs(log_directory)

        # abuse_ips 처리
        if isinstance(analysis_results.get("abuse_ips"), (dict, set)):
            analysis_results["abuse_ips_list"] = list(analysis_results.get("abuse_ips", set()))
            analysis_results["abuse_ips"] = "AbuseIPDB IPs processed"

        # Step 4: 보고서 생성
        total_logs = analysis_results.get("log_lines_count", 0)
        print_sub_task_done(f"데이터 크기: {total_logs:,}개 로그 라인")
        print_step_header(4, "보고서 생성 중...")

        # 출력 경로 생성
        output_dir = _create_output_directory(ctx)

        # 리포트 생성 (ctx.output_config에 따라 Excel, HTML, 또는 둘 다)
        report_paths = _generate_reports(ctx, analyzer, analysis_results, output_dir)

        from core.tools.output import print_report_complete

        print_report_complete(report_paths)

        # Step 5: 임시 파일 정리
        _cleanup_temp_files(analyzer, gz_directory, log_directory)

        # 자동으로 보고서 폴더 열기 (Excel이 있으면 Explorer로, HTML만 있으면 브라우저로)
        if report_paths.get("excel"):
            open_in_explorer(os.path.dirname(report_paths["excel"]))

    except Exception as e:
        console.print(f"[red]❌ ALB 로그 분석 중 오류 발생: {e}[/red]")
        raise


# =============================================================================
# 헬퍼 함수들
# =============================================================================


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
    from .alb_log_analysis.alb_excel_reporter import ALBExcelReporter

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
        console.print("HTML 보고서 생성 중...")
        html_path = _generate_html_report(ctx, analyzer, analysis_results, output_dir)
        if html_path:
            console.print("[green]HTML 보고서 생성 완료[/green]")
            report_paths["html"] = html_path

            # HTML만 생성한 경우 브라우저에서 자동 열기
            if not should_excel:
                from core.tools.io.html import open_in_browser

                output_config = ctx.get_output_config() if hasattr(ctx, "get_output_config") else None
                if output_config is None or output_config.auto_open:
                    open_in_browser(html_path)

    return report_paths


def _generate_html_report(ctx, analyzer, analysis_results: dict[str, Any], output_dir: str) -> str | None:
    """HTML 요약 보고서 생성

    ALB 로그 분석의 주요 지표를 시각화하는 HTML 대시보드 생성.
    Excel 리포트의 상세 데이터를 보완하는 용도.
    """
    try:
        from core.tools.io.html import HTMLReport

        # 기본 정보 추출
        total_logs = analysis_results.get("log_lines_count", 0)
        alb_name = analysis_results.get("alb_name", "ALB")
        unique_ips = analysis_results.get("unique_client_ips", 0)

        # 에러 카운트
        elb_4xx = analysis_results.get("elb_4xx_count", 0)
        elb_5xx = analysis_results.get("elb_5xx_count", 0)
        backend_4xx = analysis_results.get("backend_4xx_count", 0)
        backend_5xx = analysis_results.get("backend_5xx_count", 0)
        long_response = analysis_results.get("long_response_count", 0)

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
                ("ELB 4xx", f"{elb_4xx:,}", "warning" if elb_4xx > 0 else None),
                ("ELB 5xx", f"{elb_5xx:,}", "danger" if elb_5xx > 0 else None),
                ("Backend 5xx", f"{backend_5xx:,}", "danger" if backend_5xx > 0 else None),
                ("느린 응답 (≥1s)", f"{long_response:,}", "warning" if long_response > 0 else None),
                ("악성 IP", f"{abuse_count:,}", "danger" if abuse_count > 0 else None),
            ]
        )

        # 1. ELB 상태 코드 분포 (도넛 차트)
        elb_2xx = analysis_results.get("elb_2xx_count", 0)
        elb_3xx = analysis_results.get("elb_3xx_count", 0)
        status_data = [
            ("2xx 성공", elb_2xx),
            ("3xx 리다이렉트", elb_3xx),
            ("4xx 클라이언트 에러", elb_4xx),
            ("5xx 서버 에러", elb_5xx),
        ]
        # 0인 항목 제외
        status_data = [(name, count) for name, count in status_data if count > 0]
        if status_data:
            report.add_pie_chart("ELB 상태 코드 분포", status_data, doughnut=True)

        # 2. Backend 상태 코드 분포 (도넛 차트) - ELB 상태 코드 옆에 배치
        backend_status_data = [
            ("4xx 클라이언트 에러", backend_4xx),
            ("5xx 서버 에러", backend_5xx),
        ]
        backend_status_data = [(name, count) for name, count in backend_status_data if count > 0]
        if backend_status_data:
            report.add_pie_chart("Backend 상태 코드 분포", backend_status_data, doughnut=True)

        # 3. 시간대별 요청 트렌드 (라인 차트) - CloudWatch 스타일 적응형 해상도
        # 타임스탬프와 에러 플래그 수집
        all_timestamps: list[datetime] = []
        is_error_list: list[int | float] = []  # 1 if error, 0 otherwise

        for key in ["ELB 2xx Count", "ELB 3xx Count", "ELB 4xx Count", "ELB 5xx Count"]:
            log_data = analysis_results.get(key, {})
            if isinstance(log_data, dict):
                timestamps = log_data.get("timestamps", [])
                is_error = 1 if ("4xx" in key or "5xx" in key) else 0
                for ts in timestamps:
                    if ts and hasattr(ts, "timestamp"):  # datetime 객체 확인
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

        # 4. ELB vs Backend 에러 비교 (바 차트)
        if elb_4xx > 0 or elb_5xx > 0 or backend_4xx > 0 or backend_5xx > 0:
            report.add_bar_chart(
                "ELB vs Backend 에러 비교",
                categories=["4xx 에러", "5xx 에러"],
                series=[
                    ("ELB", [elb_4xx, elb_5xx]),
                    ("Backend", [backend_4xx, backend_5xx]),
                ],
            )

        # 5. 국가별 요청 분포 (바 차트)
        country_stats = analysis_results.get("country_statistics", {})
        if country_stats:
            # 요청 수 기준 정렬 (두 가지 형식 지원: {country: count} 또는 {country: {"count": count}})
            sorted_countries = [
                (country, data.get("count", 0) if isinstance(data, dict) else data)
                for country, data in country_stats.items()
            ]
            sorted_countries = sorted(sorted_countries, key=lambda x: -x[1])[:15]  # Top 15 국가

            if sorted_countries:
                countries = [c[0] for c in sorted_countries]
                counts = [c[1] for c in sorted_countries]
                report.add_bar_chart(
                    "국가별 요청 분포",
                    categories=countries,
                    series=[("요청 수", counts)],
                    horizontal=True,
                )

        # 6. Top 요청 URL (바 차트)
        url_counts = analysis_results.get("request_url_counts", {})
        if url_counts:
            sorted_urls = sorted(url_counts.items(), key=lambda x: -x[1])[:15]
            if sorted_urls:
                # URL 길이 제한
                urls = [url[:60] + "..." if len(url) > 60 else url for url, _ in sorted_urls]
                url_counts_list = [count for _, count in sorted_urls]
                report.add_bar_chart(
                    "Top 요청 URL",
                    categories=urls,
                    series=[("요청 수", url_counts_list)],
                    horizontal=True,
                )

        # 7. Top 클라이언트 IP (바 차트)
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

        # 8. Client IP별 상태 코드 분포 (상위 IP들의 에러 현황)
        # client_status_statistics: {client_ip: {status_code: count}}
        client_status = analysis_results.get("client_status_statistics", {})
        if client_status:
            # 상태 코드별 총합 계산
            status_totals: dict[str, int] = {}
            for ip_stats in client_status.values():
                if isinstance(ip_stats, dict):
                    for code, count in ip_stats.items():
                        if isinstance(count, int):
                            status_totals[code] = status_totals.get(code, 0) + count

            if status_totals:
                # Top 10 상태 코드
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

        # 9. HTTP 메서드 분포 (클라이언트 상태 코드 옆에 배치)
        request_url_details = analysis_results.get("request_url_details", {})
        if request_url_details:
            # 모든 URL의 메서드를 집계
            method_totals: dict[str, int] = {}
            for url_detail in request_url_details.values():
                if isinstance(url_detail, dict):
                    methods = url_detail.get("methods", {})
                    for method, cnt in methods.items():
                        if method and isinstance(cnt, int):
                            method_totals[method] = method_totals.get(method, 0) + cnt

            if method_totals:
                sorted_methods = sorted(method_totals.items(), key=lambda x: -x[1])
                if sorted_methods:
                    method_data: list[tuple[str, int | float]] = [
                        (m, c) for m, c in sorted_methods if m.strip()
                    ]
                    if method_data:
                        report.add_pie_chart("HTTP 메서드 분포", method_data, doughnut=True)

        # 10. Top User-Agent (바 차트)
        user_agent_counts = analysis_results.get("user_agent_counts", {})
        if user_agent_counts:
            sorted_uas = sorted(user_agent_counts.items(), key=lambda x: -x[1])[:10]
            if sorted_uas:
                # User-Agent 문자열 길이 제한
                uas = [ua[:50] + "..." if len(ua) > 50 else ua for ua, _ in sorted_uas]
                counts = [count for _, count in sorted_uas]
                report.add_bar_chart(
                    "Top User-Agent",
                    categories=uas,
                    series=[("요청 수", counts)],
                    horizontal=True,
                )

        # 11. 데이터 전송량 (바 차트) - 시각적으로 표현
        total_received = analysis_results.get("total_received_bytes") or 0
        total_sent = analysis_results.get("total_sent_bytes") or 0
        if total_received > 0 or total_sent > 0:
            # GB 단위로 변환
            def to_gb(b: int) -> float:
                return b / (1024**3) if b else 0

            transfer_data = [
                ("수신 (Received)", to_gb(total_received)),
                ("송신 (Sent)", to_gb(total_sent)),
            ]
            # 값이 있는 항목만
            transfer_data = [(name, val) for name, val in transfer_data if val > 0]
            if transfer_data:
                report.add_bar_chart(
                    "데이터 전송량 (GB)",
                    categories=[name for name, _ in transfer_data],
                    series=[("GB", [round(val, 2) for _, val in transfer_data])],
                )

        # 12. 응답 시간 백분위수 (바 차트)
        response_time_percentiles = analysis_results.get("response_time_percentiles", {})
        if response_time_percentiles:
            percentile_labels = ["P50", "P90", "P95", "P99", "평균"]
            percentile_values = [
                round(response_time_percentiles.get("p50", 0) * 1000, 1),  # ms 변환
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

        # 13. 에러 원인 분포 (바 차트)
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

        # 14. Target별 요청 분포 및 에러율 (바 차트)
        target_request_stats = analysis_results.get("target_request_stats", {})
        if target_request_stats:
            # 요청 수 기준 정렬
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

        # 15. URL별 에러율 Top 20 (바 차트)
        url_error_stats = analysis_results.get("url_error_stats", {})
        if url_error_stats:
            # 에러율이 높은 순으로 정렬 (최소 에러가 있는 것만)
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

        # 16. 시간대별 에러 트렌드 (라인 차트) - 에러만 분리
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

        if error_timestamps:
            # 에러 타입별 값 리스트 생성
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

        # 악성 IP 테이블 (실제 요청한 IP 중 악성 IP만 표시)
        if matching_abuse_ips:
            report.add_table(
                title=f"악성 IP 목록 ({len(matching_abuse_ips)}개)",
                headers=["IP 주소", "요청 수", "상태"],
                rows=[
                    [ip, count, "AbuseIPDB 등록"]
                    for ip, count in matching_abuse_ips[:50]  # 최대 50개
                ],
                page_size=20,
            )

        # 느린 응답 테이블
        long_response_times = analysis_results.get("long_response_times", [])
        if long_response_times:
            rows = []
            for r in long_response_times[:100]:
                response_time = r.get("response_time")
                response_time_str = f"{response_time:.3f}" if response_time is not None else "-"
                rows.append(
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
                title="느린 응답 Top 100",
                headers=["시간", "Client IP", "URL", "응답 시간(s)", "ELB Status", "Target Status"],
                rows=rows,
                page_size=20,
            )

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


def _select_alb_with_pagination(
    alb_list: list[dict[str, Any]],
    page_size: int = 20,
) -> dict[str, Any] | None:
    """페이지네이션으로 ALB 선택

    Args:
        alb_list: ALB 정보 리스트 [{"lb": ..., "name": ..., "scheme": ..., "status": ...}, ...]
        page_size: 페이지당 항목 수 (기본 20)

    Returns:
        선택된 ALB의 lb 객체 또는 None

    Raises:
        KeyboardInterrupt: 사용자가 취소한 경우
    """
    if not alb_list:
        return None

    total = len(alb_list)
    (total + page_size - 1) // page_size
    current_page = 0
    filtered_list = alb_list  # 검색 필터링된 리스트

    while True:
        # 현재 페이지 항목 계산
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(filtered_list))
        page_items = filtered_list[start_idx:end_idx]

        # 테이블 출력
        table = Table(
            title=f"[bold cyan]ALB 목록[/bold cyan] (페이지 {current_page + 1}/{max(1, (len(filtered_list) + page_size - 1) // page_size)}, 총 {len(filtered_list)}개)",
            show_header=True,
            header_style="bold blue",
        )
        table.add_column("No.", style="dim", width=5, justify="right")
        table.add_column("ALB 이름", style="cyan", min_width=30)
        table.add_column("Scheme", width=16, justify="center")
        table.add_column("로그", width=4, justify="center")

        for i, item in enumerate(page_items, start=start_idx + 1):
            table.add_row(
                str(i),
                item["name"],
                item["scheme"],
                item["status"],
            )

        console.print()
        console.print(table)

        # 네비게이션 안내
        nav_hints = []
        if current_page > 0:
            nav_hints.append("[dim]p: 이전[/dim]")
        if end_idx < len(filtered_list):
            nav_hints.append("[dim]n: 다음[/dim]")
        nav_hints.append("[dim]/검색어: 검색[/dim]")
        nav_hints.append("[dim]q: 취소[/dim]")

        console.print(" | ".join(nav_hints))

        # 입력 받기
        try:
            user_input = questionary.text(
                "번호 입력 또는 명령:",
            ).ask()
        except KeyboardInterrupt:
            raise KeyboardInterrupt("사용자가 취소했습니다.") from None

        if user_input is None:
            raise KeyboardInterrupt("사용자가 취소했습니다.") from None

        user_input = user_input.strip()

        # 빈 입력 무시
        if not user_input:
            continue

        # 명령어 처리
        if user_input.lower() == "q":
            raise KeyboardInterrupt("사용자가 취소했습니다.") from None

        if user_input.lower() == "n":
            if end_idx < len(filtered_list):
                current_page += 1
            else:
                console.print("[yellow]마지막 페이지입니다.[/yellow]")
            continue

        if user_input.lower() == "p":
            if current_page > 0:
                current_page -= 1
            else:
                console.print("[yellow]첫 번째 페이지입니다.[/yellow]")
            continue

        # 검색 처리 (/로 시작)
        if user_input.startswith("/"):
            search_term = user_input[1:].strip().lower()
            if search_term:
                filtered_list = [item for item in alb_list if search_term in item["name"].lower()]
                current_page = 0
                if not filtered_list:
                    console.print(f"[yellow]'{search_term}' 검색 결과가 없습니다. 전체 목록으로 복원합니다.[/yellow]")
                    filtered_list = alb_list
                else:
                    console.print(f"[green]'{search_term}' 검색 결과: {len(filtered_list)}개[/green]")
            else:
                # 빈 검색어는 전체 목록 복원
                filtered_list = alb_list
                current_page = 0
                console.print("[green]전체 목록으로 복원합니다.[/green]")
            continue

        # 번호 입력 처리
        try:
            selected_num = int(user_input)
            if 1 <= selected_num <= len(filtered_list):
                selected_item = filtered_list[selected_num - 1]
                console.print(f"[green]✓ 선택됨: {selected_item['name']}[/green]")
                return dict(selected_item["lb"])
            else:
                console.print(f"[red]1~{len(filtered_list)} 범위의 번호를 입력하세요.[/red]")
        except ValueError:
            console.print("[yellow]번호, 명령어(n/p/q), 또는 /검색어를 입력하세요.[/yellow]")


def _get_bucket_input_with_options(session, ctx) -> str | None:
    """S3 버킷 경로 입력 방식 선택

    Returns:
        S3 버킷 경로 또는 None (취소 시)

    Raises:
        KeyboardInterrupt: 사용자가 취소한 경우
    """
    choices = [
        questionary.Choice("ALB 로그 경로 자동 탐색", value="auto"),
        questionary.Choice("ALB 로그 경로 수동 입력", value="manual"),
    ]

    choice = questionary.select(
        "S3 버킷 경로 입력 방식을 선택하세요:",
        choices=choices,
    ).ask()

    if choice is None:
        raise KeyboardInterrupt("사용자가 취소했습니다.")

    if choice == "auto":
        return _get_lb_and_build_path(session, ctx)
    else:
        return _get_bucket_input_manual()


def _get_lb_and_build_path(session, ctx) -> str | None:
    """자동 탐색으로 S3 경로 생성"""
    from botocore.exceptions import ClientError

    elbv2_client = get_client(session, "elbv2")

    # ALB 목록 조회
    try:
        console.print("[cyan]Application Load Balancer 목록을 조회하는 중...[/cyan]")
        response = elbv2_client.describe_load_balancers()

        albs = [lb for lb in response["LoadBalancers"] if lb["Type"] == "application"]

        if not albs:
            console.print("[yellow]! 이 계정에 ALB가 없습니다. 수동 입력으로 전환합니다.[/yellow]")
            return _get_bucket_input_manual()

        console.print(f"[green]✓ {len(albs)}개의 ALB를 발견했습니다.[/green]")

    except ClientError as e:
        if "AccessDenied" in str(e):
            console.print("[yellow]! ELB API 접근 권한이 없습니다. 수동 입력으로 전환합니다.[/yellow]")
        else:
            console.print(f"[yellow]! ALB 조회 실패: {e}. 수동 입력으로 전환합니다.[/yellow]")
        return _get_bucket_input_manual()

    # ALB 선택 - 목록 생성
    alb_list: list[dict[str, Any]] = []

    for lb in sorted(albs, key=lambda x: x["LoadBalancerName"]):
        # 로그 설정 확인
        try:
            attrs = elbv2_client.describe_load_balancer_attributes(LoadBalancerArn=lb["LoadBalancerArn"])
            log_enabled = any(
                attr["Key"] == "access_logs.s3.enabled" and attr["Value"] == "true" for attr in attrs["Attributes"]
            )
            status = "[green]✓[/green]" if log_enabled else "[red]✗[/red]"
        except Exception as e:
            logger.debug("Failed to get ALB log status: %s", e)
            status = "[dim]?[/dim]"

        alb_list.append(
            {
                "lb": lb,
                "name": lb["LoadBalancerName"],
                "scheme": lb["Scheme"],
                "status": status,
            }
        )

    # 페이지네이션으로 ALB 선택
    selected_lb = _select_alb_with_pagination(alb_list)

    if not selected_lb:
        return _get_bucket_input_manual()

    # 로그 설정 확인
    try:
        attrs = elbv2_client.describe_load_balancer_attributes(LoadBalancerArn=selected_lb["LoadBalancerArn"])

        log_config = {}
        for attr in attrs["Attributes"]:
            if attr["Key"] == "access_logs.s3.enabled":
                log_config["enabled"] = attr["Value"] == "true"
            elif attr["Key"] == "access_logs.s3.bucket":
                log_config["bucket"] = attr["Value"]
            elif attr["Key"] == "access_logs.s3.prefix":
                log_config["prefix"] = attr["Value"]

        if not log_config.get("enabled"):
            console.print(
                f"[yellow]⚠️ '{selected_lb['LoadBalancerName']}'의 액세스 로그가 비활성화되어 있습니다.[/yellow]"
            )
            return _get_bucket_input_manual()

        if not log_config.get("bucket"):
            console.print(f"[yellow]⚠️ '{selected_lb['LoadBalancerName']}'의 로그 버킷 정보가 없습니다.[/yellow]")
            return _get_bucket_input_manual()

        # S3 경로 생성
        bucket_name = log_config["bucket"]
        prefix = log_config.get("prefix", "")

        # 계정 ID 추출
        try:
            sts = get_client(session, "sts")
            account_id = sts.get_caller_identity()["Account"]
        except Exception as e:
            logger.debug("Failed to get account ID: %s", e)
            account_id = "unknown"

        # 리전 추출
        region = selected_lb["AvailabilityZones"][0]["ZoneName"][:-1]

        # S3 경로 생성
        if prefix:
            s3_path = f"s3://{bucket_name}/{prefix}/AWSLogs/{account_id}/elasticloadbalancing/{region}/"
        else:
            s3_path = f"s3://{bucket_name}/AWSLogs/{account_id}/elasticloadbalancing/{region}/"

        console.print(f"[green]✓ 자동 생성된 S3 경로: {s3_path}[/green]")
        return s3_path

    except ClientError as e:
        console.print(f"[yellow]! 로그 설정 조회 실패: {e}. 수동 입력으로 전환합니다.[/yellow]")
        return _get_bucket_input_manual()


def _get_bucket_input_manual() -> str | None:
    """수동으로 S3 버킷 경로 입력

    Returns:
        S3 버킷 경로 또는 None (취소 시)
    """
    console.print(
        Panel(
            "[bold cyan]S3 버킷 경로 형식:[/bold cyan]\n"
            "s3://bucket-name/prefix\n\n"
            "[bold cyan]예시:[/bold cyan]\n"
            "s3://my-alb-logs/AWSLogs/123456789012/elasticloadbalancing/ap-northeast-2",
            title="[bold]버킷 경로 안내[/bold]",
        )
    )

    while True:
        bucket = questionary.text(
            "S3 버킷 경로를 입력하세요 (s3://...):",
        ).ask()

        # Ctrl+C 또는 ESC로 취소한 경우
        if bucket is None:
            raise KeyboardInterrupt("사용자가 취소했습니다.")

        if not bucket.strip():
            console.print("[red]S3 버킷 경로를 입력해주세요.[/red]")
            continue

        if not bucket.startswith("s3://"):
            bucket = f"s3://{bucket}"

        # 기본 검증
        parts = bucket.split("/")
        if len(parts) < 3 or not parts[2]:
            console.print("[red]유효하지 않은 S3 경로입니다.[/red]")
            continue

        # 필수 경로 확인
        required = ["/AWSLogs/", "/elasticloadbalancing/"]
        missing = [p for p in required if p not in bucket]
        if missing:
            console.print(f"[yellow]⚠️ 필수 경로가 누락됨: {', '.join(missing)}[/yellow]")
            confirm = questionary.confirm("그래도 이 경로를 사용하시겠습니까?", default=False).ask()
            if confirm is None:
                raise KeyboardInterrupt("사용자가 취소했습니다.")
            if not confirm:
                continue

        return str(bucket)


def _get_time_range_input() -> tuple[datetime, datetime]:
    """시간 범위 입력

    Raises:
        KeyboardInterrupt: 사용자가 취소한 경우
    """
    now = datetime.now()
    yesterday = now - timedelta(days=1)

    console.print("\n[bold cyan]분석 시간 범위 설정[/bold cyan]")
    console.print(f"[dim]기본값: {yesterday.strftime('%Y-%m-%d %H:%M')} ~ {now.strftime('%Y-%m-%d %H:%M')}[/dim]")

    # 빠른 선택 (기본값인 24시간을 첫 번째에 배치)
    quick_choices = [
        questionary.Choice("최근 24시간", value="24h"),
        questionary.Choice("최근 1시간", value="1h"),
        questionary.Choice("최근 6시간", value="6h"),
        questionary.Choice("최근 7일", value="7d"),
        questionary.Choice("직접 입력", value="custom"),
    ]

    choice = questionary.select(
        "시간 범위를 선택하세요:",
        choices=quick_choices,
    ).ask()

    if choice is None:
        raise KeyboardInterrupt("사용자가 취소했습니다.")

    if choice == "custom":
        # 직접 입력
        start_str = questionary.text(
            "시작 시간 (YYYY-MM-DD HH:MM):",
        ).ask()
        if start_str is None:
            raise KeyboardInterrupt("사용자가 취소했습니다.")

        end_str = questionary.text(
            "종료 시간 (YYYY-MM-DD HH:MM):",
        ).ask()
        if end_str is None:
            raise KeyboardInterrupt("사용자가 취소했습니다.")

        try:
            start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(end_str, "%Y-%m-%d %H:%M")
        except ValueError:
            console.print("[yellow]⚠️ 잘못된 형식. 기본값(24시간)을 사용합니다.[/yellow]")
            start_time = yesterday
            end_time = now
    else:
        # 빠른 선택
        time_deltas = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(days=1),
            "7d": timedelta(days=7),
        }
        delta = time_deltas.get(choice, timedelta(days=1))
        start_time = now - delta
        end_time = now

    console.print(
        f"[green]✓ 분석 기간: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}[/green]"
    )
    return start_time, end_time


def _get_timezone_input() -> str:
    """타임존 입력

    Raises:
        KeyboardInterrupt: 사용자가 취소한 경우
    """
    tz_choices = [
        questionary.Choice("Asia/Seoul (한국)", value="Asia/Seoul"),
        questionary.Choice("UTC", value="UTC"),
        questionary.Choice("America/New_York", value="America/New_York"),
        questionary.Choice("Europe/London", value="Europe/London"),
        questionary.Choice("직접 입력", value="custom"),
    ]

    choice = questionary.select(
        "타임존을 선택하세요:",
        choices=tz_choices,
    ).ask()

    if choice is None:
        raise KeyboardInterrupt("사용자가 취소했습니다.")

    if choice == "custom":
        tz = questionary.text("타임존 입력:", default="Asia/Seoul").ask()
        if tz is None:
            raise KeyboardInterrupt("사용자가 취소했습니다.")
        try:
            pytz.timezone(tz)
            return str(tz)
        except pytz.exceptions.UnknownTimeZoneError:
            console.print("[yellow]⚠️ 잘못된 타임존. Asia/Seoul을 사용합니다.[/yellow]")
            return "Asia/Seoul"

    return str(choice)


def _create_output_directory(ctx) -> str:
    """출력 디렉토리 생성"""
    from core.tools.output import OutputPath

    # identifier 결정
    if ctx.is_sso_session() and ctx.accounts:
        identifier = ctx.accounts[0].id  # AccountInfo.id 사용
    elif ctx.profile_name:
        identifier = ctx.profile_name
    else:
        identifier = "default"

    # OutputPath.build()는 문자열(str)을 반환
    output_path = OutputPath(identifier).sub("elb", "log").with_date().build()
    return output_path


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


def _cleanup_temp_files(analyzer, gz_directory: str, log_directory: str) -> None:
    """임시 파일 정리 (분석 완료 후 gz, log 파일 삭제)"""
    print_sub_info("임시 파일 정리 중...")

    try:
        # 1. analyzer.clean_up 호출 (DuckDB 등 내부 리소스 정리)
        if hasattr(analyzer, "clean_up"):
            analyzer.clean_up([])

        # 2. gz 디렉토리 내부 파일 삭제
        if isinstance(gz_directory, str) and os.path.exists(gz_directory):
            try:
                for filename in os.listdir(gz_directory):
                    filepath = os.path.join(gz_directory, filename)
                    if os.path.isfile(filepath):
                        os.remove(filepath)
            except Exception as e:
                logger.debug("Failed to clean gz directory: %s", e)

        # 3. log 디렉토리 내부 파일 삭제
        if isinstance(log_directory, str) and os.path.exists(log_directory):
            try:
                for filename in os.listdir(log_directory):
                    filepath = os.path.join(log_directory, filename)
                    if os.path.isfile(filepath):
                        os.remove(filepath)
            except Exception as e:
                logger.debug("Failed to clean log directory: %s", e)

        print_sub_task_done("임시 파일 정리 완료")

    except Exception as e:
        logger.debug("Failed to cleanup temp files: %s", e)
