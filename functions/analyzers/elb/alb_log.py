"""
core/tools/analysis/log/alb_analyzer.py - ALB 로그 분석 도구 진입점

플러그인 규약:
    - run(ctx): 필수. 실행 함수.
    - collect_options(ctx): 선택. 추가 옵션 수집.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from core.auth import get_context_session
from core.cli.ui import (
    console,
    print_step_header,
    print_sub_info,
    print_sub_task_done,
    print_sub_warning,
)
from core.parallel import get_client
from core.shared.io.output import open_in_explorer
from core.tools.cache import get_cache_dir

from .alb_log_prompts import (
    _get_bucket_input_with_options,
    _get_time_range_input,
    _get_timezone_input,
)
from .alb_log_report import _generate_reports

if TYPE_CHECKING:
    from core.cli.flow.context import ExecutionContext

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
    from functions.reports.log_analyzer import ALBLogAnalyzer

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

        from core.shared.io.output import print_report_complete

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


def _create_output_directory(ctx) -> str:
    """출력 디렉토리 생성"""
    from core.shared.io.output import OutputPath

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
