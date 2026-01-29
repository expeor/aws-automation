#!/usr/bin/env python3
"""
🚀 DuckDB 기반 ALB 로그 분석기

기존 파싱 로직을 DuckDB SQL로 교체하여 초고속 분석을 제공합니다.
기존 인터페이스와 완전 호환성을 유지합니다.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import pytz  # type: ignore[import-untyped]

# DuckDB - optional dependency
try:
    import duckdb
except ImportError:
    duckdb = None  # type: ignore

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

# 콘솔 및 로거 (aa_cli.aa.ui 또는 로컬 생성)
try:
    from cli.ui import console, logger, print_sub_info, print_sub_task_done
except ImportError:
    import logging

    console = Console()
    logger = logging.getLogger(__name__)

    # Fallback functions
    def print_sub_info(message: str) -> None:
        console.print(f"[blue]{message}[/blue]")

    def print_sub_task_done(message: str) -> None:
        console.print(f"[green]✓ {message}[/green]")


from core.tools.cache import get_cache_dir

from .alb_log_downloader import ALBLogDownloader
from .ip_intelligence import IPIntelligence


def _check_duckdb():
    """DuckDB 설치 여부를 확인합니다."""
    if duckdb is None:
        raise ImportError(
            "❌ DuckDB가 설치되지 않았습니다.\n"
            "   ALB 로그 분석 기능을 사용하려면 다음 명령어로 설치하세요:\n\n"
            "   pip install duckdb"
        )


class ALBLogAnalyzer:
    """🚀 DuckDB 기반 ALB 로그를 분석하는 클래스입니다."""

    def __init__(
        self,
        s3_client: Any,
        bucket_name: str,
        prefix: str,
        start_datetime: Any,
        end_datetime: Any | None = None,
        timezone: str = "Asia/Seoul",
        max_workers: int = 5,
    ):
        """ALB 로그 분석기를 초기화합니다."""
        # DuckDB 설치 확인
        _check_duckdb()

        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.prefix = prefix.strip("/")

        # datetime 객체 또는 문자열을 datetime 객체로 변환
        if isinstance(start_datetime, str):
            try:
                self.start_datetime = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M")
            except ValueError as e:
                raise ValueError(f"잘못된 시작 시간 형식: {start_datetime}") from e
        else:
            self.start_datetime = start_datetime

        if end_datetime is None:
            self.end_datetime = datetime.now()
        elif isinstance(end_datetime, str):
            try:
                self.end_datetime = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M")
            except ValueError as e:
                raise ValueError(f"잘못된 종료 시간 형식: {end_datetime}") from e
        else:
            self.end_datetime = end_datetime

        # 타임존 설정
        try:
            self.timezone = pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"알 수 없는 타임존 '{timezone}'입니다. UTC를 사용합니다.")
            self.timezone = pytz.UTC

        self.console = console
        self.max_workers = max_workers

        # ALBLogDownloader 인스턴스 생성
        self.downloader = ALBLogDownloader(
            s3_client=s3_client,
            s3_uri=f"s3://{bucket_name}/{prefix}",
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            timezone=timezone,
            max_workers=max_workers,
        )

        # 작업 디렉토리 설정 (temp/alb 하위)
        self.base_dir = get_cache_dir("alb")
        self.temp_dir = os.path.join(self.base_dir, "gz")
        self.decompressed_dir = os.path.join(self.base_dir, "log")
        self.download_dir = self.temp_dir

        # DuckDB 임시/데이터 디렉토리
        self.temp_work_dir = os.getenv("AA_DUCKDB_TEMP_DIR") or os.path.join(self.base_dir, "duckdb")
        self.duckdb_dir = os.path.join(self.base_dir, "checkpoint")
        self.duckdb_db_path = os.path.join(self.duckdb_dir, "alb_logs.duckdb")

        # 디렉토리 생성
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.decompressed_dir, exist_ok=True)
        os.makedirs(self.temp_work_dir, exist_ok=True)
        os.makedirs(self.duckdb_dir, exist_ok=True)

        # 🚀 DuckDB 연결 초기화 (파일 DB로 전환)
        self.conn = duckdb.connect(self.duckdb_db_path, read_only=False)
        self._setup_duckdb()

        # 🌍 IP 인텔리전스 초기화 (국가 매핑 + 악성 IP)
        self.ip_intel = IPIntelligence()

    def _setup_duckdb(self):
        """DuckDB 설정 및 ALB 로그 파싱 함수들을 생성합니다."""
        try:
            # DuckDB 설정 최적화 (환경변수로 조정 가능)
            memory_limit = os.getenv("AA_DUCKDB_MEMORY_LIMIT", "2GB")
            threads_default = min(8, os.cpu_count() or 8)
            try:
                threads = int(os.getenv("AA_DUCKDB_THREADS", str(threads_default)))
            except ValueError:
                threads = threads_default

            temp_dir_sql = Path(self.temp_work_dir).as_posix()

            self.conn.execute(f"SET temp_directory='{temp_dir_sql}'")
            self.conn.execute(f"SET memory_limit='{memory_limit}'")
            self.conn.execute(f"SET threads={threads}")
            self.conn.execute("SET enable_progress_bar=false")

            # ALB 로그 파싱을 위한 사용자 정의 함수들
            self._create_alb_parsing_functions()

            logger.debug("✅ DuckDB 초기화 완료")

        except Exception as e:
            logger.error(f"❌ DuckDB 설정 실패: {str(e)}")
            raise

    def _create_alb_parsing_functions(self):
        """ALB 로그 파싱을 위한 사용자 정의 함수 생성"""

        # 간단한 정규식 기반 파싱 매크로들 (DuckDB MACRO)
        # 타임존 변환: ALB 로그는 UTC로 기록되므로, 사용자 타임존으로 변환
        tz_name = self.timezone.zone if hasattr(self.timezone, "zone") else str(self.timezone)
        functions = [
            # UTC 타임스탬프를 파싱 후 사용자 타임존으로 변환
            f"""CREATE OR REPLACE MACRO extract_timestamp(log_line) AS (
                   timezone('{tz_name}',
                       strptime(regexp_extract(log_line, '\\S+ (\\S+) ', 1), '%Y-%m-%dT%H:%M:%S.%fZ')
                       AT TIME ZONE 'UTC'
                   )
               )""",
            """CREATE OR REPLACE MACRO extract_client_ip(log_line) AS (
                   split_part(regexp_extract(log_line, '\\S+ \\S+ \\S+ (\\S+) ', 1), ':', 1)
               )""",
            """CREATE OR REPLACE MACRO extract_target_ip(log_line) AS (
                   CASE
                       WHEN regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) = '-' THEN ''
                       ELSE split_part(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ (\\S+) ', 1), ':', 1)
                   END
               )""",
            """CREATE OR REPLACE MACRO extract_elb_status(log_line) AS (
                   regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1)
               )""",
            """CREATE OR REPLACE MACRO extract_target_status(log_line) AS (
                   regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1)
               )""",
            """CREATE OR REPLACE MACRO extract_response_time(log_line) AS (
                   CAST(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) AS DOUBLE) +
                   CAST(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) AS DOUBLE) +
                   CAST(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) AS DOUBLE)
               )""",
            """CREATE OR REPLACE MACRO extract_request(log_line) AS (
                   regexp_extract(log_line, '"([^\"]*)"', 1)
               )""",
            """CREATE OR REPLACE MACRO extract_method(log_line) AS (
                   split_part(regexp_extract(log_line, '"([^\"]*)"', 1), ' ', 1)
               )""",
            """CREATE OR REPLACE MACRO extract_url(log_line) AS (
                   split_part(regexp_extract(log_line, '"([^\"]*)"', 1), ' ', 2)
               )""",
            """CREATE OR REPLACE MACRO extract_user_agent(log_line) AS (
                   coalesce(regexp_extract(log_line, '"[^\"]*"\\s+"([^\"]*)"', 1), '')
               )""",
            """CREATE OR REPLACE MACRO extract_received_bytes(log_line) AS (
                   CAST(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) AS BIGINT)
               )""",
            """CREATE OR REPLACE MACRO extract_sent_bytes(log_line) AS (
                   CAST(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) AS BIGINT)
               )""",
            # 추가 필드: target_port
            """CREATE OR REPLACE MACRO extract_target_port(log_line) AS (
                   CASE
                       WHEN regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) = '-' THEN ''
                       ELSE split_part(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ (\\S+) ', 1), ':', 2)
                   END
               )""",
            # 처리 시간 3필드 분리 (-1은 타임아웃/연결실패를 의미, NULL로 처리)
            """CREATE OR REPLACE MACRO extract_request_proc_time(log_line) AS (
                   CASE WHEN regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) IN ('-', '-1') THEN NULL
                        WHEN CAST(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) AS DOUBLE) < 0 THEN NULL
                        ELSE CAST(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) AS DOUBLE) END
               )""",
            """CREATE OR REPLACE MACRO extract_target_proc_time(log_line) AS (
                   CASE WHEN regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) IN ('-', '-1') THEN NULL
                        WHEN CAST(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) AS DOUBLE) < 0 THEN NULL
                        ELSE CAST(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) AS DOUBLE) END
               )""",
            """CREATE OR REPLACE MACRO extract_response_proc_time(log_line) AS (
                   CASE WHEN regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) IN ('-', '-1') THEN NULL
                        WHEN CAST(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) AS DOUBLE) < 0 THEN NULL
                        ELSE CAST(regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) AS DOUBLE) END
               )""",
            # 총 응답 시간: 모든 필드가 NULL이면 NULL, 아니면 합산 (NULL은 0으로 처리)
            """CREATE OR REPLACE MACRO extract_total_response_time(log_line) AS (
                   CASE
                       WHEN extract_request_proc_time(log_line) IS NULL
                            AND extract_target_proc_time(log_line) IS NULL
                            AND extract_response_proc_time(log_line) IS NULL
                       THEN NULL
                       ELSE coalesce(extract_request_proc_time(log_line), 0) +
                            coalesce(extract_target_proc_time(log_line), 0) +
                            coalesce(extract_response_proc_time(log_line), 0)
                   END
               )""",
            # target 필드 (5번째 space-separated field, target:port 형태)
            """CREATE OR REPLACE MACRO extract_target(log_line) AS (
                   CASE
                       WHEN regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ (\\S+) ', 1) = '-' THEN ''
                       ELSE regexp_extract(log_line, '\\S+ \\S+ \\S+ \\S+ (\\S+) ', 1)
                   END
               )""",
            # target_group_arn 및 name (라인 내 어디서든 안전하게 추출)
            """CREATE OR REPLACE MACRO extract_target_group_arn(log_line) AS (
                   coalesce(regexp_extract(log_line, '(arn:aws:elasticloadbalancing:[^\\s]+:targetgroup/[^\\s]+)', 1), '')
               )""",
            """CREATE OR REPLACE MACRO extract_target_group_name(log_line) AS (
                   coalesce(regexp_extract(log_line, 'targetgroup/([^/]+)/', 1), '')
               )""",
            # redirect_url (마지막 7개 quoted field 중 두 번째)
            """CREATE OR REPLACE MACRO extract_redirect_url(log_line) AS (
                   coalesce(regexp_extract(log_line, '"[^\"]*"\\s+"([^\"]*)"\\s+"[^\"]*"\\s+"[^\"]*"\\s+"[^\"]*"\\s+"[^\"]*"\\s+"[^\"]*"\\s+\\S+\\s*$', 1), '')
               )""",
            # error_reason (마지막 7개 quoted field 중 세 번째)
            """CREATE OR REPLACE MACRO extract_error_reason(log_line) AS (
                   coalesce(regexp_extract(log_line, '"[^\"]*"\\s+"[^\"]*"\\s+"([^\"]*)"\\s+"[^\"]*"\\s+"[^\"]*"\\s+"[^\"]*"\\s+"[^\"]*"\\s+\\S+\\s*$', 1), '')
               )""",
            # elb 이름 추출 (예: app/my-alb-name/50dc6... -> my-alb-name)
            """CREATE OR REPLACE MACRO extract_elb_full(log_line) AS (
                   regexp_extract(log_line, '\\S+ \\S+ (\\S+) ', 1)
               )""",
            """CREATE OR REPLACE MACRO extract_elb_name(log_line) AS (
                   coalesce(regexp_extract(extract_elb_full(log_line), '^[^/]+/([^/]+)/', 1), '')
               )""",
            # ========== 추가 분석 필드 (Phase 2) ==========
            # HTTP 버전 추출 (request 필드에서: "GET /path HTTP/1.1")
            """CREATE OR REPLACE MACRO extract_http_version(log_line) AS (
                   CASE
                       WHEN regexp_extract(log_line, '"[^"]*\\s+HTTP/2[^"]*"', 0) IS NOT NULL THEN 'HTTP/2'
                       WHEN regexp_extract(log_line, '"[^"]*\\s+HTTP/1\\.1[^"]*"', 0) IS NOT NULL THEN 'HTTP/1.1'
                       WHEN regexp_extract(log_line, '"[^"]*\\s+HTTP/1\\.0[^"]*"', 0) IS NOT NULL THEN 'HTTP/1.0'
                       WHEN log_line LIKE '%grpc%' OR log_line LIKE '%gRPC%' THEN 'gRPC'
                       WHEN log_line LIKE 'h2 %' OR log_line LIKE 'grpcs %' THEN 'HTTP/2'
                       WHEN log_line LIKE 'wss %' OR log_line LIKE 'ws %' THEN 'WebSocket'
                       ELSE 'Unknown'
                   END
               )""",
            # SSL/TLS 프로토콜 (필드 15: ssl_protocol - TLSv1.2, TLSv1.3 등)
            """CREATE OR REPLACE MACRO extract_ssl_protocol(log_line) AS (
                   coalesce(
                       regexp_extract(log_line, '\\s(TLSv1\\.[0-3])\\s', 1),
                       CASE WHEN log_line LIKE 'http %' THEN 'None' ELSE '-' END
                   )
               )""",
            # SSL/TLS 암호 스위트 (필드 14: ssl_cipher)
            """CREATE OR REPLACE MACRO extract_ssl_cipher(log_line) AS (
                   coalesce(
                       regexp_extract(log_line, '\\s([A-Z][A-Z0-9]+-[A-Z0-9-]+)\\s+TLSv', 1),
                       CASE WHEN log_line LIKE 'http %' THEN 'None' ELSE '-' END
                   )
               )""",
            # Actions Executed (필드 22: "waf,forward", "authenticate,forward" 등)
            """CREATE OR REPLACE MACRO extract_actions(log_line) AS (
                   coalesce(
                       regexp_extract(log_line, '"(waf[^"]*|forward|redirect|fixed-response|authenticate[^"]*)"', 1),
                       '-'
                   )
               )""",
            # Classification (필드 28: Acceptable, Ambiguous, Severe)
            """CREATE OR REPLACE MACRO extract_classification(log_line) AS (
                   coalesce(
                       regexp_extract(log_line, '"(Acceptable|Ambiguous|Severe)"', 1),
                       'Unknown'
                   )
               )""",
            # Classification Reason (필드 29)
            """CREATE OR REPLACE MACRO extract_classification_reason(log_line) AS (
                   coalesce(
                       regexp_extract(log_line, '"(Acceptable|Ambiguous|Severe)"\\s+"([^"]*)"', 2),
                       '-'
                   )
               )""",
        ]

        # 함수들을 개별적으로 실행
        for func_sql in functions:
            try:
                self.conn.execute(func_sql)
            except Exception as e:
                logger.debug(f"함수 생성 중 오류 (무시됨): {str(e)}")

    def download_logs(self) -> list[str]:
        """S3에서 로그 파일을 다운로드합니다."""
        return self.downloader.download_logs()

    def decompress_logs(self, gz_directory: str) -> str:
        """압축된 로그 파일을 해제합니다."""
        return self.downloader.decompress_logs(gz_directory)

    def analyze_logs(self, log_directory: str) -> dict[str, Any]:
        """DuckDB 기반 로그 파일들을 분석합니다."""
        try:
            print_sub_info("ALB 로그 분석을 시작합니다...")

            # 단일 진행 바로 전체 파이프라인 진행 상황 표시
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task("[cyan]분석 중...", total=7)

                # 1) 로그 파일들을 DuckDB로 로드
                progress.update(task, description="[cyan]로그 파일 로드 중...")
                table_name = self._load_logs_to_duckdb(log_directory)
                if not table_name:
                    logger.warning("분석할 로그가 없습니다.")
                    return self._get_empty_analysis_results()
                progress.advance(task)

                # 2) DuckDB로 로그 분석 수행 (5단계)
                analysis_results = self._analyze_with_duckdb(progress=progress, task_id=task)

            # AbuseIPDB 데이터 추가 (IPIntelligence 통합 API 사용)
            progress.update(task, description="[cyan]AbuseIPDB 데이터 다운로드 중...")
            abuseipdb_result = self.ip_intel.download_abuse_data()

            # AbuseIPDB 결과에서 실제 IP 리스트와 상세 정보 추출
            abuse_ips_data = abuseipdb_result.get("abuse_ips", [])
            abuse_ip_details = abuseipdb_result.get("abuse_ip_details", {})

            # abuse_ips_data가 set인 경우 list로 변환
            if isinstance(abuse_ips_data, set):
                abuse_ips_list = list(abuse_ips_data)
            elif isinstance(abuse_ips_data, list):
                abuse_ips_list = abuse_ips_data
            else:
                abuse_ips_list = []

            # AbuseIPDB 데이터를 분석 결과에 추가
            analysis_results["abuse_ips"] = abuse_ips_list
            analysis_results["abuse_ips_list"] = abuse_ips_list
            analysis_results["abuse_ip_details"] = abuse_ip_details

            progress.update(task, description="[green]✓ 분석 완료!")
            print_sub_task_done("ALB 로그 분석이 완료되었습니다!")
            return analysis_results

        except Exception as e:
            logger.error(f"로그 분석 중 오류 발생: {str(e)}")
            raise Exception(f"로그 분석 중 오류 발생: {str(e)}") from e

    def _load_logs_to_duckdb(self, log_directory: str) -> str | None:
        """로그 파일들을 DuckDB 테이블로 로드합니다."""
        try:
            # 로그 파일 찾기
            log_files = []
            for root, _, files in os.walk(log_directory):
                for file in files:
                    if file.endswith(".log"):
                        log_files.append(os.path.join(root, file))

            if not log_files:
                logger.warning("파싱할 로그 파일이 없습니다.")
                return None

            logger.debug(f"📁 {len(log_files)}개의 로그 파일 발견")

            # 각 날짜별 파일 수 계산 - 파일명에서 날짜 정보 추출
            date_counts: dict[str, int] = {}
            for log_file in log_files:
                # 1) 파일 경로에서 날짜 추출 (기존 방식)
                date_match = re.search(r"(\d{4})[/\\](\d{2})[/\\](\d{2})", log_file)
                if date_match:
                    date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                    date_counts[date_str] = date_counts.get(date_str, 0) + 1
                else:
                    # 2) 파일명에서 날짜 추출 시도 (ALB 로그 파일명 형식)
                    filename = os.path.basename(log_file)
                    # 파일명: account_elasticloadbalancing_region_loadbalancer_20250817T000000Z_ip_random.log
                    # 다양한 패턴 시도
                    timestamp_patterns = [
                        r"_(\d{8})T\d{6}Z?_",  # _20250817T123456Z_
                        r"_(\d{8})T\d{6}_",  # _20250817T123456_
                        r"_(\d{4}-\d{2}-\d{2})T",  # _2025-08-17T
                        r"(\d{8})T\d{6}",  # 20250817T123456
                        r"(\d{4}\d{2}\d{2})_\d{6}_",  # 20250817_123456_
                    ]

                    timestamp_match = None
                    for pattern in timestamp_patterns:
                        timestamp_match = re.search(pattern, filename)
                        if timestamp_match:
                            break
                    if timestamp_match:
                        date_part = timestamp_match.group(1)  # 20250817 또는 2025-08-17
                        if "-" in date_part:
                            date_str = date_part  # 이미 YYYY-MM-DD 형식
                        else:
                            date_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                        date_counts[date_str] = date_counts.get(date_str, 0) + 1
                    else:
                        # 3) 추가 패턴 시도 - 파일명 전체에서 날짜 찾기
                        date_anywhere = re.search(r"(\d{4}[\-_]?\d{2}[\-_]?\d{2})", filename)
                        if date_anywhere:
                            raw_date = date_anywhere.group(1).replace("_", "-")
                            if len(raw_date) == 8:  # YYYYMMDD
                                date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                            else:
                                date_str = raw_date
                            date_counts[date_str] = date_counts.get(date_str, 0) + 1
                        else:
                            # 디버깅을 위해 파일명 예시 출력
                            if date_counts.get("unknown", 0) < 3:
                                logger.debug(f"날짜 추출 실패 파일명 예시: {filename}")
                            date_counts["unknown"] = date_counts.get("unknown", 0) + 1

            if date_counts:
                logger.debug(f"📅 날짜별 파일 분포: {date_counts}")
                # 정렬된 날짜로 표시
                sorted_dates = sorted([k for k in date_counts if k != "unknown"])
                if sorted_dates:
                    logger.debug(f"📊 날짜 범위: {sorted_dates[0]} ~ {sorted_dates[-1]}")

            # 로드된 파일 메타 저장 (Summary 시트 표시용)
            try:
                self.loaded_log_files_count = len(log_files)
                self.loaded_log_files_paths = log_files
                self.loaded_log_directory = log_directory
            except Exception:
                pass  # nosec B110 - Non-critical metadata assignment

            # 파일 리스트를 DuckDB가 이해할 수 있는 리스트 리터럴로 변환
            backslash = "\\"
            file_list_sql = ", ".join([f"'{p.replace(backslash, '/')}'" for p in log_files])

            # 로그 파일들을 하나의 테이블로 로드
            create_table_query = f"""
            CREATE OR REPLACE TABLE alb_logs AS
            SELECT
                line as raw_line,
                extract_timestamp(line) as timestamp,
                extract_client_ip(line) as client_ip,
                extract_target_ip(line) as target_ip,
                extract_target_port(line) as target_port,
                extract_target(line) as target,
                extract_elb_full(line) as elb_full,
                extract_elb_name(line) as elb_name,
                extract_elb_status(line) as elb_status_code,
                extract_target_status(line) as target_status_code,
                extract_request_proc_time(line) as request_processing_time,
                extract_target_proc_time(line) as target_processing_time,
                extract_response_proc_time(line) as response_processing_time,
                extract_total_response_time(line) as response_time,
                extract_request(line) as request,
                extract_method(line) as http_method,
                extract_url(line) as url,
                extract_user_agent(line) as user_agent,
                extract_target_group_arn(line) as target_group_arn,
                extract_target_group_name(line) as target_group_name,
                extract_redirect_url(line) as redirect_url,
                extract_error_reason(line) as error_reason,
                extract_received_bytes(line) as received_bytes,
                extract_sent_bytes(line) as sent_bytes,
                -- 추가 분석 필드 (Phase 2)
                extract_http_version(line) as http_version,
                extract_ssl_protocol(line) as ssl_protocol,
                extract_ssl_cipher(line) as ssl_cipher,
                extract_actions(line) as actions_executed,
                extract_classification(line) as classification,
                extract_classification_reason(line) as classification_reason
            FROM read_csv_auto([{file_list_sql}],
                              delim='\\t',
                              header=false,
                              columns={{'line': 'VARCHAR'}},
                              ignore_errors=true)
            WHERE line IS NOT NULL
              AND line != ''
              AND length(line) > 50
            """

            # 로그 로드 및 체크포인트 (상위 Progress에서 관리)
            self.conn.execute(create_table_query)
            # 로드 직후 디스크에 플러시하여 메모리 압박을 줄임
            with contextlib.suppress(Exception):
                self.conn.execute("CHECKPOINT")

            # 로드된 레코드 수 확인
            count_result = self.conn.execute("SELECT COUNT(*) FROM alb_logs").fetchone()
            total_records = count_result[0] if count_result else 0

            logger.debug(f"✅ 총 {total_records:,}개의 로그 레코드 로드 완료")

            return "alb_logs"

        except Exception as e:
            logger.error(f"❌ 로그 파일 로드 실패: {str(e)}")
            return None

    def _analyze_with_duckdb(
        self,
        progress: Progress | None = None,
        task_id: Any | None = None,
    ) -> dict[str, Any]:
        """DuckDB를 사용하여 로그를 분석합니다."""
        try:
            # 🎯 타임스탬프는 이미 사용자 타임존으로 변환되어 저장되므로
            # 필터링도 사용자 타임존 기준으로 수행
            start_local = self.start_datetime.strftime("%Y-%m-%d %H:%M:%S")
            end_local = self.end_datetime.strftime("%Y-%m-%d %H:%M:%S")

            summary_query = f"""
            SELECT
                COUNT(*) as total_logs,
                COUNT(DISTINCT client_ip) as unique_client_ips,
                MIN(timestamp) as start_time,
                MAX(timestamp) as end_time,
                AVG(response_time) as avg_response_time,
                SUM(received_bytes) as total_received_bytes,
                SUM(sent_bytes) as total_sent_bytes,
                SUM(CASE WHEN elb_status_code LIKE '2%' AND elb_status_code != '-' AND elb_status_code IS NOT NULL THEN 1 ELSE 0 END) as elb_2xx_count,
                SUM(CASE WHEN elb_status_code LIKE '3%' AND elb_status_code != '-' AND elb_status_code IS NOT NULL THEN 1 ELSE 0 END) as elb_3xx_count,
                SUM(CASE WHEN elb_status_code LIKE '4%' AND elb_status_code != '-' AND elb_status_code IS NOT NULL THEN 1 ELSE 0 END) as elb_4xx_count,
                SUM(CASE WHEN elb_status_code LIKE '5%' AND elb_status_code != '-' AND elb_status_code IS NOT NULL THEN 1 ELSE 0 END) as elb_5xx_count,
                SUM(CASE WHEN target_status_code LIKE '4%' AND target_status_code != '-' AND target_status_code IS NOT NULL THEN 1 ELSE 0 END) as backend_4xx_count,
                SUM(CASE WHEN target_status_code LIKE '5%' AND target_status_code != '-' AND target_status_code IS NOT NULL THEN 1 ELSE 0 END) as backend_5xx_count
            FROM alb_logs
            WHERE timestamp IS NOT NULL
              AND timestamp >= '{start_local}'
              AND timestamp <= '{end_local}'
            """

            # 1) 요약 통계
            if progress is not None and task_id is not None:
                progress.update(task_id, description="[cyan]요약 통계 계산 중...")
            summary_result = self.conn.execute(summary_query).fetchone()
            if summary_result is None:
                raise ValueError("Failed to get summary statistics from database")
            if progress is not None and task_id is not None:
                progress.advance(task_id)

            # 2) 카운트 계산
            if progress is not None and task_id is not None:
                progress.update(task_id, description="[cyan]IP/URL/User Agent 카운트 중...")
            client_ip_query = """
            SELECT client_ip, COUNT(*) as count
            FROM alb_logs
            WHERE client_ip != '' AND client_ip IS NOT NULL
            GROUP BY client_ip
            ORDER BY count DESC
            """
            client_ip_results = self.conn.execute(client_ip_query).fetchall()
            client_ip_counts = {ip: count for ip, count in client_ip_results}

            # Client별 상태코드 통계
            client_status_query = """
            SELECT client_ip, elb_status_code, COUNT(*) as count
            FROM alb_logs
            WHERE client_ip != '' AND client_ip IS NOT NULL
              AND elb_status_code IS NOT NULL AND elb_status_code != '-'
            GROUP BY client_ip, elb_status_code
            ORDER BY client_ip, elb_status_code
            """
            client_status_results = self.conn.execute(client_status_query).fetchall()
            client_status_statistics: dict[str, dict[str, int]] = {}
            for client_ip, status_code, count in client_status_results:
                if client_ip not in client_status_statistics:
                    client_status_statistics[client_ip] = {}
                client_status_statistics[client_ip][status_code] = count

            # Target별 상태코드 통계 (target이 있는 경우만)
            target_status_query = """
            SELECT target, target_group_name, target_group_arn, elb_status_code, target_status_code, COUNT(*) as count
            FROM alb_logs
            WHERE target != '' AND target IS NOT NULL
              AND (
                (elb_status_code IS NOT NULL AND elb_status_code != '-') OR
                (target_status_code IS NOT NULL AND target_status_code != '-')
              )
            GROUP BY target, target_group_name, target_group_arn, elb_status_code, target_status_code
            ORDER BY target, target_group_name, elb_status_code, target_status_code
            """
            target_status_results = self.conn.execute(target_status_query).fetchall()
            target_status_statistics: dict[str, Any] = {}
            for (
                target,
                target_group_name,
                _target_group_arn,
                elb_status,
                target_status,
                count,
            ) in target_status_results:
                # target 표시용 키 생성 (다른 시트들과 동일한 형태)
                if target and target != "-":
                    target_display_key = f"{target_group_name}({target})" if target_group_name else target
                else:
                    continue  # target이 없으면 스킵

                if target_display_key not in target_status_statistics:
                    target_status_statistics[target_display_key] = {}

                # ELB 상태코드 처리
                if elb_status and elb_status != "-":
                    elb_key = f"ELB:{elb_status}"
                    if elb_key not in target_status_statistics[target_display_key]:
                        target_status_statistics[target_display_key][elb_key] = 0
                    target_status_statistics[target_display_key][elb_key] += count

                # Backend 상태코드 처리 (Target에서 실제 응답한 경우만)
                if target_status and target_status != "-":
                    backend_key = f"Backend:{target_status}"
                    if backend_key not in target_status_statistics[target_display_key]:
                        target_status_statistics[target_display_key][backend_key] = 0
                    target_status_statistics[target_display_key][backend_key] += count

            # 요청 URL 카운트
            request_url_query = """
            SELECT TRIM(url) as url, COUNT(*) as count
            FROM alb_logs
            WHERE url IS NOT NULL AND TRIM(url) != ''
            GROUP BY url
            ORDER BY count DESC
            """
            request_url_results = self.conn.execute(request_url_query).fetchall()
            request_url_counts = {url: count for url, count in request_url_results}

            # User Agent 카운트
            user_agent_query = """
            SELECT user_agent, COUNT(*) as count
            FROM alb_logs
            WHERE user_agent != '' AND user_agent IS NOT NULL
            GROUP BY user_agent
            ORDER BY count DESC
            """
            user_agent_results = self.conn.execute(user_agent_query).fetchall()
            user_agent_counts = {ua: count for ua, count in user_agent_results}
            if progress is not None and task_id is not None:
                progress.update(task_id, description="[cyan]IP/URL/User Agent 카운트 완료...")
                progress.advance(task_id)

            # URL 별 상세 통계 (Top 100 URL 대상)
            request_url_details: dict[str, dict[str, Any]] = {}
            try:
                top_urls = [str(url).strip() for url, _ in request_url_results[:100] if url]
                if top_urls:
                    # DuckDB IN 리스트 구성 (quote escape 처리)
                    def _escape_sql(val: str) -> str:
                        return val.replace("'", "''")

                    in_list_sql = ", ".join([f"'{_escape_sql(u)}'" for u in top_urls])

                    # 1) 메서드별 카운트
                    methods_sql = f"""
                    SELECT TRIM(url) as url, TRIM(http_method) as http_method, COUNT(*) as cnt
                    FROM alb_logs
                    WHERE TRIM(url) IN ({in_list_sql}) AND url IS NOT NULL AND TRIM(url) != ''
                    GROUP BY url, http_method
                    """
                    method_rows = self.conn.execute(methods_sql).fetchall()

                    # 2) User-Agent별 카운트
                    ua_sql = f"""
                    SELECT TRIM(url) as url, TRIM(user_agent) as user_agent, COUNT(*) as cnt
                    FROM alb_logs
                    WHERE TRIM(url) IN ({in_list_sql}) AND url IS NOT NULL AND TRIM(url) != ''
                    GROUP BY url, user_agent
                    """
                    ua_rows = self.conn.execute(ua_sql).fetchall()

                    # 3) 상태코드별 카운트 (ELB)
                    status_sql = f"""
                    SELECT TRIM(url) as url, elb_status_code, COUNT(*) as cnt
                    FROM alb_logs
                    WHERE TRIM(url) IN ({in_list_sql}) AND url IS NOT NULL AND TRIM(url) != ''
                    GROUP BY url, elb_status_code
                    """
                    status_rows = self.conn.execute(status_sql).fetchall()

                    # 4) 고유 IP 수
                    unique_ip_sql = f"""
                    SELECT TRIM(url) as url, COUNT(DISTINCT client_ip) as unique_ips
                    FROM alb_logs
                    WHERE TRIM(url) IN ({in_list_sql}) AND url IS NOT NULL AND TRIM(url) != ''
                    GROUP BY url
                    """
                    unique_ip_rows = self.conn.execute(unique_ip_sql).fetchall()

                    # 5) 평균 응답 시간
                    avg_rt_sql = f"""
                    SELECT TRIM(url) as url, AVG(response_time) as avg_rt
                    FROM alb_logs
                    WHERE TRIM(url) IN ({in_list_sql}) AND url IS NOT NULL AND TRIM(url) != ''
                      AND response_time IS NOT NULL
                    GROUP BY url
                    """
                    avg_rt_rows = self.conn.execute(avg_rt_sql).fetchall()

                    # 6) URL별 Top Client IP (가장 많이 요청한 IP)
                    top_client_sql = f"""
                    WITH ranked AS (
                        SELECT TRIM(url) as url, client_ip, COUNT(*) as cnt,
                               ROW_NUMBER() OVER (PARTITION BY TRIM(url) ORDER BY COUNT(*) DESC) as rn
                        FROM alb_logs
                        WHERE TRIM(url) IN ({in_list_sql}) AND url IS NOT NULL AND TRIM(url) != ''
                          AND client_ip IS NOT NULL AND client_ip != ''
                        GROUP BY TRIM(url), client_ip
                    )
                    SELECT url, client_ip FROM ranked WHERE rn = 1
                    """
                    top_client_rows = self.conn.execute(top_client_sql).fetchall()
                    top_client_map = {url: ip for url, ip in top_client_rows}

                    # 7) 총 카운트 (이미 계산된 request_url_counts 사용)
                    for url in top_urls:
                        request_url_details[url] = {
                            "count": int(request_url_counts.get(url, 0) or 0),
                            "methods": {},
                            "user_agents": {},
                            "status_codes": {},
                            "top_client_ip": top_client_map.get(url, ""),
                            # 메모리 절약: 세트/리스트 대신 통계 값만 저장
                            "unique_ips": 0,
                            "avg_response_time": 0.0,
                        }

                    for url, method, cnt in method_rows:
                        if url in request_url_details:
                            # http_method가 빈 문자열인 경우 대시 제거와 일치하도록 정규화는 리포터에서 처리
                            request_url_details[url]["methods"][method] = int(cnt)

                    for url, ua, cnt in ua_rows:
                        if url in request_url_details:
                            request_url_details[url]["user_agents"][ua] = int(cnt)

                    for url, status, cnt in status_rows:
                        if url in request_url_details and status is not None and status != "":
                            request_url_details[url]["status_codes"][status] = int(cnt)

                    for url, uniq in unique_ip_rows:
                        if url in request_url_details:
                            try:
                                request_url_details[url]["unique_ips"] = int(uniq or 0)
                            except Exception:
                                request_url_details[url]["unique_ips"] = 0  # Type conversion fallback

                    for url, avg_rt in avg_rt_rows:
                        if url in request_url_details:
                            try:
                                request_url_details[url]["avg_response_time"] = float(avg_rt or 0.0)
                            except Exception:
                                request_url_details[url]["avg_response_time"] = 0.0  # Type conversion fallback
            except Exception:
                # 세부 URL 통계는 선택 항목이므로 실패해도 전체 분석을 계속 (optional stats)
                request_url_details = {}

            # 3) 느린 응답/바이트 계산
            if progress is not None and task_id is not None:
                progress.update(task_id, description="[cyan]느린 응답/바이트 분석 중...")
            long_response_query = """
            SELECT timestamp,
                   client_ip,
                   target_ip,
                   target_port,
                   target,
                   http_method,
                   url,
                   elb_status_code,
                   target_status_code,
                   response_time,
                   received_bytes,
                   sent_bytes,
                   user_agent,
                   target_group_arn,
                   target_group_name
            FROM alb_logs
            ORDER BY response_time DESC
            LIMIT 100
            """
            long_response_results = self.conn.execute(long_response_query).fetchall()
            long_response_times = []
            for row in long_response_results:
                long_response_times.append(
                    {
                        "timestamp": row[0],
                        "client_ip": row[1],
                        "target_ip": row[2],
                        "target_port": row[3],
                        "target": row[4],
                        "http_method": row[5],
                        "request": row[6],
                        "elb_status_code": row[7],
                        "target_status_code": row[8],
                        "response_time": row[9],
                        "received_bytes": row[10],
                        "sent_bytes": row[11],
                        "user_agent": row[12],
                        "target_group_arn": row[13],
                        "target_group_name": row[14],
                    }
                )

            # 1초 이상 응답 카운트 (Summary용)
            try:
                long_resp_count_row = self.conn.execute(
                    "SELECT COUNT(*) FROM alb_logs WHERE response_time >= 1.0"
                ).fetchone()
                long_response_count_val = long_resp_count_row[0] if long_resp_count_row else 0
            except Exception:
                long_response_count_val = 0  # Query fallback

            # 응답 시간 백분위수 (P50, P90, P95, P99)
            response_time_percentiles: dict[str, float] = {}
            try:
                percentile_query = """
                SELECT
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY response_time) as p50,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY response_time) as p90,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time) as p95,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time) as p99,
                    AVG(response_time) as avg,
                    MIN(response_time) as min,
                    MAX(response_time) as max
                FROM alb_logs
                WHERE response_time IS NOT NULL AND response_time >= 0
                """
                percentile_result = self.conn.execute(percentile_query).fetchone()
                if percentile_result:
                    response_time_percentiles = {
                        "p50": float(percentile_result[0] or 0),
                        "p90": float(percentile_result[1] or 0),
                        "p95": float(percentile_result[2] or 0),
                        "p99": float(percentile_result[3] or 0),
                        "avg": float(percentile_result[4] or 0),
                        "min": float(percentile_result[5] or 0),
                        "max": float(percentile_result[6] or 0),
                    }
            except Exception as e:
                logger.debug(f"응답 시간 백분위수 계산 실패: {e}")
                response_time_percentiles = {}

            # 에러 원인(error_reason) 분포
            error_reason_counts: dict[str, int] = {}
            try:
                error_reason_query = """
                SELECT error_reason, COUNT(*) as count
                FROM alb_logs
                WHERE error_reason IS NOT NULL
                  AND error_reason != ''
                  AND error_reason != '-'
                GROUP BY error_reason
                ORDER BY count DESC
                """
                error_reason_results = self.conn.execute(error_reason_query).fetchall()
                error_reason_counts = {reason: count for reason, count in error_reason_results if reason}
            except Exception as e:
                logger.debug(f"에러 원인 집계 실패: {e}")
                error_reason_counts = {}

            # Target별 요청 분포 및 에러율
            target_request_stats: dict[str, dict[str, Any]] = {}
            try:
                target_stats_query = """
                SELECT
                    target,
                    target_group_name,
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN elb_status_code LIKE '4%' OR elb_status_code LIKE '5%' THEN 1 ELSE 0 END) as error_count,
                    AVG(response_time) as avg_response_time
                FROM alb_logs
                WHERE target IS NOT NULL AND target != '' AND target != '-'
                GROUP BY target, target_group_name
                ORDER BY total_requests DESC
                """
                target_stats_results = self.conn.execute(target_stats_query).fetchall()
                for target, tg_name, total, errors, avg_rt in target_stats_results:
                    display_key = f"{tg_name}({target})" if tg_name else target
                    error_rate = (errors / total * 100) if total > 0 else 0
                    target_request_stats[display_key] = {
                        "total_requests": total,
                        "error_count": errors,
                        "error_rate": round(error_rate, 2),
                        "avg_response_time": round(float(avg_rt or 0), 4),
                    }
            except Exception as e:
                logger.debug(f"Target 통계 계산 실패: {e}")
                target_request_stats = {}

            # URL별 에러율
            url_error_stats: dict[str, dict[str, Any]] = {}
            try:
                url_error_query = """
                SELECT
                    TRIM(url) as url,
                    COUNT(*) as total_requests,
                    SUM(CASE WHEN elb_status_code LIKE '4%' THEN 1 ELSE 0 END) as count_4xx,
                    SUM(CASE WHEN elb_status_code LIKE '5%' THEN 1 ELSE 0 END) as count_5xx
                FROM alb_logs
                WHERE url IS NOT NULL AND TRIM(url) != ''
                GROUP BY url
                HAVING COUNT(*) >= 10
                ORDER BY (count_4xx + count_5xx) DESC
                LIMIT 50
                """
                url_error_results = self.conn.execute(url_error_query).fetchall()
                for url, total, c4xx, c5xx in url_error_results:
                    error_total = (c4xx or 0) + (c5xx or 0)
                    error_rate = (error_total / total * 100) if total > 0 else 0
                    url_error_stats[url] = {
                        "total_requests": total,
                        "count_4xx": c4xx or 0,
                        "count_5xx": c5xx or 0,
                        "error_count": error_total,
                        "error_rate": round(error_rate, 2),
                    }
            except Exception as e:
                logger.debug(f"URL 에러율 계산 실패: {e}")
                url_error_stats = {}

            # 바이트 분석
            received_bytes_query = """
            SELECT url, SUM(received_bytes) as total_bytes
            FROM alb_logs
            WHERE received_bytes > 0
            GROUP BY url
            ORDER BY total_bytes DESC
            """
            received_bytes_results = self.conn.execute(received_bytes_query).fetchall()
            received_bytes = {url: bytes_count for url, bytes_count in received_bytes_results}

            sent_bytes_query = """
            SELECT url, SUM(sent_bytes) as total_bytes
            FROM alb_logs
            WHERE sent_bytes > 0
            GROUP BY url
            ORDER BY total_bytes DESC
            """
            sent_bytes_results = self.conn.execute(sent_bytes_query).fetchall()
            sent_bytes = {url: bytes_count for url, bytes_count in sent_bytes_results}

            # ==================================================================================
            # 성능 분석 (TPS, 시간별 Latency, SLA, Target별 성능)
            # ==================================================================================

            # 시간 버킷 크기 결정 (데이터 범위에 따라 적응)
            time_range_seconds = (self.end_datetime - self.start_datetime).total_seconds()
            time_range_hours = time_range_seconds / 3600

            if time_range_hours <= 1:
                bucket_minutes = 1
            elif time_range_hours <= 3:
                bucket_minutes = 5
            elif time_range_hours <= 24:
                bucket_minutes = 15
            elif time_range_hours <= 24 * 7:
                bucket_minutes = 60
            else:
                bucket_minutes = 240

            bucket_interval = f"{bucket_minutes} minutes"

            # 시간 버킷별 TPS 및 요약 통계
            tps_time_series: list[dict[str, Any]] = []
            try:
                tps_query = f"""
                SELECT
                    time_bucket(INTERVAL '{bucket_interval}', timestamp) as bucket,
                    COUNT(*) as request_count,
                    ROUND(COUNT(*) / ({bucket_minutes} * 60.0), 2) as tps,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY response_time) as p50,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY response_time) as p90,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time) as p99,
                    SUM(CASE WHEN elb_status_code LIKE '4%' OR elb_status_code LIKE '5%' THEN 1 ELSE 0 END) as error_count
                FROM alb_logs
                WHERE timestamp IS NOT NULL
                  AND timestamp >= '{start_local}'
                  AND timestamp <= '{end_local}'
                GROUP BY bucket
                ORDER BY bucket
                """
                tps_results = self.conn.execute(tps_query).fetchall()
                for bucket_ts, req_count, tps, p50, p90, p99, errors in tps_results:
                    error_rate = (errors / req_count * 100) if req_count > 0 else 0
                    tps_time_series.append(
                        {
                            "timestamp": bucket_ts,
                            "request_count": int(req_count),
                            "tps": float(tps or 0),
                            "p50_ms": round(float(p50 or 0) * 1000, 2),
                            "p90_ms": round(float(p90 or 0) * 1000, 2),
                            "p99_ms": round(float(p99 or 0) * 1000, 2),
                            "error_count": int(errors or 0),
                            "error_rate": round(error_rate, 2),
                        }
                    )
            except Exception as e:
                logger.debug(f"TPS 시계열 계산 실패: {e}")
                tps_time_series = []

            # SLA 준수율 계산 (응답 시간 임계값별)
            sla_compliance: dict[str, dict[str, Any]] = {}
            try:
                sla_query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN response_time < 0.1 THEN 1 ELSE 0 END) as under_100ms,
                    SUM(CASE WHEN response_time < 0.5 THEN 1 ELSE 0 END) as under_500ms,
                    SUM(CASE WHEN response_time < 1.0 THEN 1 ELSE 0 END) as under_1s
                FROM alb_logs
                WHERE response_time IS NOT NULL AND response_time >= 0
                """
                sla_result = self.conn.execute(sla_query).fetchone()
                if sla_result and sla_result[0] > 0:
                    total = sla_result[0]
                    sla_compliance = {
                        "under_100ms": {
                            "compliant": int(sla_result[1] or 0),
                            "non_compliant": total - int(sla_result[1] or 0),
                            "rate": round(int(sla_result[1] or 0) / total * 100, 2),
                            "threshold": "< 100ms",
                            "slo_target": 99.0,
                        },
                        "under_500ms": {
                            "compliant": int(sla_result[2] or 0),
                            "non_compliant": total - int(sla_result[2] or 0),
                            "rate": round(int(sla_result[2] or 0) / total * 100, 2),
                            "threshold": "< 500ms",
                            "slo_target": 99.0,
                        },
                        "under_1s": {
                            "compliant": int(sla_result[3] or 0),
                            "non_compliant": total - int(sla_result[3] or 0),
                            "rate": round(int(sla_result[3] or 0) / total * 100, 2),
                            "threshold": "< 1s",
                            "slo_target": 99.9,
                        },
                    }
            except Exception as e:
                logger.debug(f"SLA 준수율 계산 실패: {e}")
                sla_compliance = {}

            # Target별 Latency 백분위수
            target_latency_stats: dict[str, dict[str, Any]] = {}
            try:
                target_latency_query = """
                SELECT
                    target,
                    target_group_name,
                    COUNT(*) as total_requests,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY response_time) as p50,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY response_time) as p90,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time) as p99,
                    AVG(response_time) as avg_rt,
                    SUM(CASE WHEN elb_status_code LIKE '4%' OR elb_status_code LIKE '5%' THEN 1 ELSE 0 END) as error_count
                FROM alb_logs
                WHERE target IS NOT NULL AND target != '' AND target != '-'
                  AND response_time IS NOT NULL AND response_time >= 0
                GROUP BY target, target_group_name
                ORDER BY total_requests DESC
                LIMIT 50
                """
                target_latency_results = self.conn.execute(target_latency_query).fetchall()
                for target, tg_name, total, p50, p90, p99, avg_rt, errors in target_latency_results:
                    display_key = f"{tg_name}({target})" if tg_name else target
                    error_rate = (errors / total * 100) if total > 0 else 0
                    target_latency_stats[display_key] = {
                        "total_requests": int(total),
                        "p50_ms": round(float(p50 or 0) * 1000, 2),
                        "p90_ms": round(float(p90 or 0) * 1000, 2),
                        "p99_ms": round(float(p99 or 0) * 1000, 2),
                        "avg_ms": round(float(avg_rt or 0) * 1000, 2),
                        "error_count": int(errors or 0),
                        "error_rate": round(error_rate, 2),
                    }
            except Exception as e:
                logger.debug(f"Target Latency 통계 계산 실패: {e}")
                target_latency_stats = {}

            # 응답 시간 구간별 분포 (히스토그램 데이터)
            response_time_distribution: dict[str, int] = {}
            try:
                distribution_query = """
                SELECT
                    SUM(CASE WHEN response_time < 0.1 THEN 1 ELSE 0 END) as under_100ms,
                    SUM(CASE WHEN response_time >= 0.1 AND response_time < 0.5 THEN 1 ELSE 0 END) as ms_100_500,
                    SUM(CASE WHEN response_time >= 0.5 AND response_time < 1.0 THEN 1 ELSE 0 END) as ms_500_1000,
                    SUM(CASE WHEN response_time >= 1.0 AND response_time < 3.0 THEN 1 ELSE 0 END) as s_1_3,
                    SUM(CASE WHEN response_time >= 3.0 THEN 1 ELSE 0 END) as over_3s
                FROM alb_logs
                WHERE response_time IS NOT NULL AND response_time >= 0
                """
                dist_result = self.conn.execute(distribution_query).fetchone()
                if dist_result:
                    response_time_distribution = {
                        "<100ms": int(dist_result[0] or 0),
                        "100-500ms": int(dist_result[1] or 0),
                        "500ms-1s": int(dist_result[2] or 0),
                        "1-3s": int(dist_result[3] or 0),
                        ">3s": int(dist_result[4] or 0),
                    }
            except Exception as e:
                logger.debug(f"응답 시간 분포 계산 실패: {e}")
                response_time_distribution = {}

            # ==================================================================================
            # 추가 분석 (Phase 2): 처리 시간 분해, 연결 실패, HTTP 버전, SSL/TLS, Actions, Classification
            # ==================================================================================

            # 처리 시간 분해 분석 (Request/Target/Response 각각의 P50/P90/P99)
            processing_time_breakdown: dict[str, dict[str, float]] = {}
            try:
                breakdown_query = """
                SELECT
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY request_processing_time) as req_p50,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY request_processing_time) as req_p90,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY request_processing_time) as req_p99,
                    AVG(request_processing_time) as req_avg,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY target_processing_time) as target_p50,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY target_processing_time) as target_p90,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY target_processing_time) as target_p99,
                    AVG(target_processing_time) as target_avg,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY response_processing_time) as resp_p50,
                    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY response_processing_time) as resp_p90,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_processing_time) as resp_p99,
                    AVG(response_processing_time) as resp_avg
                FROM alb_logs
                WHERE request_processing_time IS NOT NULL
                  AND target_processing_time IS NOT NULL
                  AND response_processing_time IS NOT NULL
                """
                breakdown_result = self.conn.execute(breakdown_query).fetchone()
                if breakdown_result:
                    processing_time_breakdown = {
                        "request": {
                            "p50_ms": round(float(breakdown_result[0] or 0) * 1000, 3),
                            "p90_ms": round(float(breakdown_result[1] or 0) * 1000, 3),
                            "p99_ms": round(float(breakdown_result[2] or 0) * 1000, 3),
                            "avg_ms": round(float(breakdown_result[3] or 0) * 1000, 3),
                        },
                        "target": {
                            "p50_ms": round(float(breakdown_result[4] or 0) * 1000, 3),
                            "p90_ms": round(float(breakdown_result[5] or 0) * 1000, 3),
                            "p99_ms": round(float(breakdown_result[6] or 0) * 1000, 3),
                            "avg_ms": round(float(breakdown_result[7] or 0) * 1000, 3),
                        },
                        "response": {
                            "p50_ms": round(float(breakdown_result[8] or 0) * 1000, 3),
                            "p90_ms": round(float(breakdown_result[9] or 0) * 1000, 3),
                            "p99_ms": round(float(breakdown_result[10] or 0) * 1000, 3),
                            "avg_ms": round(float(breakdown_result[11] or 0) * 1000, 3),
                        },
                    }
            except Exception as e:
                logger.debug(f"처리 시간 분해 분석 실패: {e}")
                processing_time_breakdown = {}

            # 연결 실패 분석 (-1 값 탐지)
            connection_failures: dict[str, Any] = {}
            try:
                failure_query = """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN request_processing_time IS NULL THEN 1 ELSE 0 END) as request_failures,
                    SUM(CASE WHEN target_processing_time IS NULL THEN 1 ELSE 0 END) as target_failures,
                    SUM(CASE WHEN response_processing_time IS NULL THEN 1 ELSE 0 END) as response_failures
                FROM alb_logs
                """
                failure_result = self.conn.execute(failure_query).fetchone()
                if failure_result and failure_result[0] > 0:
                    total = failure_result[0]
                    connection_failures = {
                        "total_requests": int(total),
                        "request_failures": int(failure_result[1] or 0),
                        "target_failures": int(failure_result[2] or 0),
                        "response_failures": int(failure_result[3] or 0),
                        "request_failure_rate": round((failure_result[1] or 0) / total * 100, 2),
                        "target_failure_rate": round((failure_result[2] or 0) / total * 100, 2),
                        "response_failure_rate": round((failure_result[3] or 0) / total * 100, 2),
                    }

                # Target별 연결 실패 상세
                target_failure_query = """
                SELECT target, target_group_name, COUNT(*) as failure_count
                FROM alb_logs
                WHERE target_processing_time IS NULL
                  AND target IS NOT NULL AND target != '' AND target != '-'
                GROUP BY target, target_group_name
                ORDER BY failure_count DESC
                LIMIT 20
                """
                target_failure_results = self.conn.execute(target_failure_query).fetchall()
                connection_failures["target_failures_detail"] = [
                    {"target": t, "target_group": tg or "", "count": c} for t, tg, c in target_failure_results
                ]
            except Exception as e:
                logger.debug(f"연결 실패 분석 실패: {e}")
                connection_failures = {}

            # HTTP 버전 분포
            http_version_distribution: dict[str, int] = {}
            try:
                http_version_query = """
                SELECT http_version, COUNT(*) as count
                FROM alb_logs
                WHERE http_version IS NOT NULL AND http_version != 'Unknown'
                GROUP BY http_version
                ORDER BY count DESC
                """
                http_version_results = self.conn.execute(http_version_query).fetchall()
                http_version_distribution = {version: int(count) for version, count in http_version_results}
            except Exception as e:
                logger.debug(f"HTTP 버전 분포 계산 실패: {e}")
                http_version_distribution = {}

            # SSL/TLS 통계
            ssl_stats: dict[str, Any] = {}
            try:
                # TLS 프로토콜 분포
                ssl_protocol_query = """
                SELECT ssl_protocol, COUNT(*) as count
                FROM alb_logs
                WHERE ssl_protocol IS NOT NULL AND ssl_protocol != '-' AND ssl_protocol != 'None'
                GROUP BY ssl_protocol
                ORDER BY count DESC
                """
                ssl_protocol_results = self.conn.execute(ssl_protocol_query).fetchall()
                ssl_stats["protocol_distribution"] = {proto: int(count) for proto, count in ssl_protocol_results}

                # 암호 스위트 Top 10
                ssl_cipher_query = """
                SELECT ssl_cipher, COUNT(*) as count
                FROM alb_logs
                WHERE ssl_cipher IS NOT NULL AND ssl_cipher != '-' AND ssl_cipher != 'None'
                GROUP BY ssl_cipher
                ORDER BY count DESC
                LIMIT 10
                """
                ssl_cipher_results = self.conn.execute(ssl_cipher_query).fetchall()
                ssl_stats["cipher_distribution"] = {cipher: int(count) for cipher, count in ssl_cipher_results}

                # 취약 TLS 버전 사용자 (TLSv1.0, TLSv1.1)
                weak_tls_query = """
                SELECT client_ip, ssl_protocol, COUNT(*) as count
                FROM alb_logs
                WHERE ssl_protocol IN ('TLSv1.0', 'TLSv1.1')
                GROUP BY client_ip, ssl_protocol
                ORDER BY count DESC
                LIMIT 50
                """
                weak_tls_results = self.conn.execute(weak_tls_query).fetchall()
                ssl_stats["weak_tls_clients"] = [
                    {"client_ip": ip, "protocol": proto, "count": int(count)} for ip, proto, count in weak_tls_results
                ]
            except Exception as e:
                logger.debug(f"SSL/TLS 통계 계산 실패: {e}")
                ssl_stats = {}

            # Actions 통계
            actions_stats: dict[str, int] = {}
            try:
                actions_query = """
                SELECT
                    CASE
                        WHEN actions_executed LIKE '%waf-failed%' THEN 'WAF Blocked'
                        WHEN actions_executed LIKE '%waf%' THEN 'WAF Passed'
                        WHEN actions_executed LIKE '%authenticate%' THEN 'Authenticated'
                        WHEN actions_executed LIKE '%redirect%' THEN 'Redirect'
                        WHEN actions_executed LIKE '%fixed-response%' THEN 'Fixed Response'
                        WHEN actions_executed LIKE '%forward%' THEN 'Forward'
                        WHEN actions_executed = '-' OR actions_executed IS NULL THEN 'None'
                        ELSE 'Other'
                    END as action_type,
                    COUNT(*) as count
                FROM alb_logs
                GROUP BY action_type
                ORDER BY count DESC
                """
                actions_results = self.conn.execute(actions_query).fetchall()
                actions_stats = {action: int(count) for action, count in actions_results}
            except Exception as e:
                logger.debug(f"Actions 통계 계산 실패: {e}")
                actions_stats = {}

            # Classification 통계 (Desync 탐지)
            classification_stats: dict[str, Any] = {}
            try:
                classification_query = """
                SELECT classification, COUNT(*) as count
                FROM alb_logs
                WHERE classification IS NOT NULL AND classification != 'Unknown'
                GROUP BY classification
                ORDER BY count DESC
                """
                classification_results = self.conn.execute(classification_query).fetchall()
                classification_stats["distribution"] = {cls: int(count) for cls, count in classification_results}

                # Ambiguous/Severe 요청 상세 (보안 이벤트) - Excel 최대 행 제한 적용
                # Excel 2007+ (.xlsx) max rows: 1,048,576 (header 1행 제외 = 1,048,575)
                security_events_query = f"""
                SELECT timestamp, client_ip, classification, classification_reason, url, elb_status_code
                FROM alb_logs
                WHERE classification IN ('Ambiguous', 'Severe')
                  AND timestamp >= '{start_local}'
                  AND timestamp <= '{end_local}'
                ORDER BY timestamp DESC
                LIMIT 1048575
                """
                security_events_results = self.conn.execute(security_events_query).fetchall()
                classification_stats["security_events"] = [
                    {
                        "timestamp": ts,
                        "client_ip": ip,
                        "classification": cls,
                        "reason": reason,
                        "url": url,
                        "status_code": status,
                    }
                    for ts, ip, cls, reason, url, status in security_events_results
                ]
            except Exception as e:
                logger.debug(f"Classification 통계 계산 실패: {e}")
                classification_stats = {}

            if progress is not None and task_id is not None:
                progress.update(task_id, description="[cyan]느린 응답/바이트 분석 완료...")
                progress.advance(task_id)

            # 4) 상태 코드별 로그 수집
            if progress is not None and task_id is not None:
                progress.update(task_id, description="[cyan]ELB 상태 코드별 로그 수집 중...")
            status_code_logs = {}
            for status_prefix, log_key in [
                ("2", "ELB 2xx Count"),
                ("3", "ELB 3xx Count"),
                ("4", "ELB 4xx Count"),
                ("5", "ELB 5xx Count"),
            ]:
                query = f"""
                SELECT timestamp,
                       client_ip,
                       target_ip,
                       target_port,
                       target,
                       http_method,
                       url,
                       elb_status_code,
                       target_status_code,
                       response_time,
                       received_bytes,
                       sent_bytes,
                       user_agent,
                       redirect_url,
                       error_reason,
                       target_group_arn,
                       target_group_name
                FROM alb_logs
                WHERE elb_status_code LIKE '{status_prefix}%'
                  AND elb_status_code != '-'
                  AND elb_status_code IS NOT NULL
                  AND timestamp IS NOT NULL
                  AND timestamp >= '{start_local}'
                  AND timestamp <= '{end_local}'
                ORDER BY timestamp DESC
                """
                results = self.conn.execute(query).fetchall()
                logs_list = []
                timestamps_list = []

                for row in results:
                    # 타임스탬프는 이미 사용자 타임존으로 변환되어 있음
                    local_timestamp = row[0]

                    log_dict = {
                        "timestamp": local_timestamp,
                        "client_ip": row[1],
                        "target_ip": row[2],
                        "target_port": row[3],
                        "target": row[4],
                        "http_method": row[5],
                        "request": row[6],
                        "elb_status_code": row[7],
                        "target_status_code": row[8],
                        "response_time": row[9],
                        "received_bytes": row[10],
                        "sent_bytes": row[11],
                        "user_agent": row[12],
                        "redirect_url": row[13],
                        "error_reason": row[14],
                        "target_group_arn": row[15],
                        "target_group_name": row[16],
                    }
                    logs_list.append(log_dict)
                    timestamps_list.append(local_timestamp)

                status_code_logs[log_key] = {
                    "full_logs": logs_list,
                    "timestamps": timestamps_list,
                    "count": len(logs_list),
                    "fill": None,
                }

                # 타임스탬프 버전도 추가
                timestamp_key = log_key.replace("Count", "Timestamp")
                status_code_logs[timestamp_key] = {
                    "full_logs": logs_list,
                    "timestamps": timestamps_list,
                    "count": len(logs_list),
                    "fill": None,
                }

            # Backend 상태 코드별 로그
            if progress is not None and task_id is not None:
                progress.update(task_id, description="[cyan]Backend 상태 코드별 로그 수집 중...")
            for status_prefix, log_key in [
                ("4", "Backend 4xx Count"),
                ("5", "Backend 5xx Count"),
            ]:
                query = f"""
                SELECT timestamp,
                       client_ip,
                       target_ip,
                       target_port,
                       target,
                       http_method,
                       url,
                       elb_status_code,
                       target_status_code,
                       response_time,
                       received_bytes,
                       sent_bytes,
                       user_agent,
                       error_reason,
                       target_group_arn,
                       target_group_name
                FROM alb_logs
                WHERE target_status_code LIKE '{status_prefix}%'
                  AND target_status_code != '-'
                  AND target_status_code IS NOT NULL
                  AND timestamp IS NOT NULL
                  AND timestamp >= '{start_local}'
                  AND timestamp <= '{end_local}'
                ORDER BY timestamp DESC
                """
                results = self.conn.execute(query).fetchall()
                logs_list = []
                timestamps_list = []

                for row in results:
                    # 타임스탬프는 이미 사용자 타임존으로 변환되어 있음
                    local_timestamp = row[0]

                    log_dict = {
                        "timestamp": local_timestamp,
                        "client_ip": row[1],
                        "target_ip": row[2],
                        "target_port": row[3],
                        "target": row[4],
                        "http_method": row[5],
                        "request": row[6],
                        "elb_status_code": row[7],
                        "target_status_code": row[8],
                        "response_time": row[9],
                        "received_bytes": row[10],
                        "sent_bytes": row[11],
                        "user_agent": row[12],
                        "error_reason": row[13],
                        "target_group_arn": row[14],
                        "target_group_name": row[15],
                    }
                    logs_list.append(log_dict)
                    timestamps_list.append(local_timestamp)

                status_code_logs[log_key] = {
                    "full_logs": logs_list,
                    "timestamps": timestamps_list,
                    "count": len(logs_list),
                    "fill": None,
                }

                # 타임스탬프 버전도 추가
                timestamp_key = log_key.replace("Count", "Timestamp")
                status_code_logs[timestamp_key] = {
                    "full_logs": logs_list,
                    "timestamps": timestamps_list,
                    "count": len(logs_list),
                    "fill": None,
                }

            # 상태 코드 수집 단계 완료 반영 (ELB + Backend)
            if progress is not None and task_id is not None:
                progress.advance(task_id)
                progress.advance(task_id)

            if progress is not None and task_id is not None:
                progress.update(task_id, description="[cyan]국가 정보 매핑 중...")

            # 시작/종료 시간 포맷팅 - 사용자가 설정한 분석 기간 사용
            start_time = self.start_datetime.strftime("%Y-%m-%d %H:%M:%S")
            end_time = self.end_datetime.strftime("%Y-%m-%d %H:%M:%S")

            # 실제 로그 데이터의 시간 범위 - 이미 사용자 타임존으로 변환되어 있음
            actual_start_time = summary_result[2].strftime("%Y-%m-%d %H:%M:%S") if summary_result[2] else "N/A"

            actual_end_time = summary_result[3].strftime("%Y-%m-%d %H:%M:%S") if summary_result[3] else "N/A"

            # 분석 결과 구성
            analysis_results = {
                # 기본 정보
                "start_time": start_time,
                "end_time": end_time,
                "actual_start_time": actual_start_time,
                "actual_end_time": actual_end_time,
                "timezone": self.timezone.zone,
                "log_lines_count": summary_result[0],
                "log_files_count": getattr(self, "loaded_log_files_count", 0),
                "log_files_path": getattr(self, "loaded_log_directory", ""),
                "unique_client_ips": summary_result[1],
                "total_received_bytes": summary_result[5] or 0,
                "total_sent_bytes": summary_result[6] or 0,
                # S3 정보
                "s3_bucket_name": self.bucket_name,
                "s3_prefix": self.prefix,
                "s3_uri": f"s3://{self.bucket_name}/{self.prefix}",
                # 카운트 데이터
                "elb_2xx_count": summary_result[7] or 0,
                "elb_3xx_count": summary_result[8] or 0,
                "elb_4xx_count": summary_result[9] or 0,
                "elb_5xx_count": summary_result[10] or 0,
                "backend_4xx_count": summary_result[11] or 0,
                "backend_5xx_count": summary_result[12] or 0,
                "long_response_count": long_response_count_val,
                # 카운트 데이터
                "client_ip_counts": client_ip_counts,
                "request_url_counts": request_url_counts,
                "user_agent_counts": user_agent_counts,
                "client_status_statistics": client_status_statistics,
                "target_status_statistics": target_status_statistics,
                "request_url_details": request_url_details,
                "long_response_times": long_response_times,
                "received_bytes": received_bytes,
                "sent_bytes": sent_bytes,
                # 추가 분석 데이터
                "response_time_percentiles": response_time_percentiles,
                "error_reason_counts": error_reason_counts,
                "target_request_stats": target_request_stats,
                "url_error_stats": url_error_stats,
                # 성능 분석 데이터 (TPS, SLA, Target Latency)
                "tps_time_series": tps_time_series,
                "sla_compliance": sla_compliance,
                "target_latency_stats": target_latency_stats,
                "response_time_distribution": response_time_distribution,
                "bucket_minutes": bucket_minutes,
                # 추가 분석 데이터 (Phase 2)
                "processing_time_breakdown": processing_time_breakdown,
                "connection_failures": connection_failures,
                "http_version_distribution": http_version_distribution,
                "ssl_stats": ssl_stats,
                "actions_stats": actions_stats,
                "classification_stats": classification_stats,
                # 빈 데이터 (호환성)
                "elb_error_timestamps": [],
                "backend_error_timestamps": [],
                "elb_2xx_timestamps": [],
                "elb_3xx_timestamps": [],
                "elb_4xx_timestamps": [],
                "elb_5xx_timestamps": [],
                "backend_4xx_timestamps": [],
                "backend_5xx_timestamps": [],
            }

            # elb/alb 이름 추출 (가능한 경우)
            try:
                alb_name_row = self.conn.execute(
                    "SELECT elb_name FROM alb_logs WHERE elb_name IS NOT NULL AND elb_name != '' LIMIT 1"
                ).fetchone()
                if alb_name_row and alb_name_row[0]:
                    analysis_results["alb_name"] = alb_name_row[0]
            except Exception:
                pass  # nosec B110 - ALB name extraction is optional

            # 상태 코드별 로그 데이터 추가
            analysis_results.update(status_code_logs)

            # 🌍 국가 정보 추가 (IPIntelligence 통합 API 사용)
            try:
                if self.ip_intel.initialize():
                    logger.debug("🌍 IP 국가 정보 매핑 시작...")

                    # 고유한 클라이언트 IP 목록 추출
                    unique_ips = list(client_ip_counts.keys())

                    # 상위 10개 IP 디버깅 정보 출력
                    top_ips = sorted(client_ip_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                    logger.debug(f"🔍 상위 10개 클라이언트 IP: {[ip for ip, count in top_ips]}")

                    # 국가 정보 매핑
                    country_mapping = self.ip_intel.get_country_codes_batch(unique_ips)

                    # 국가별 통계 생성
                    country_stats = self.ip_intel.get_country_statistics(unique_ips)

                    # 결과에 추가
                    analysis_results["ip_country_mapping"] = country_mapping
                    analysis_results["country_statistics"] = country_stats

                    # 상위 10개 IP의 국가 매핑 결과 출력
                    top_ip_countries = [(ip, country_mapping.get(ip, "UNKNOWN")) for ip, count in top_ips]
                    logger.debug(f"🌍 상위 10개 IP 국가 매핑: {top_ip_countries}")

                    logger.debug(f"✅ 국가 정보 매핑 완료: {len(country_mapping)}개 IP, {len(country_stats)}개 국가")
                else:
                    logger.warning("⚠️ IP-Country 매퍼 초기화 실패, 국가 정보를 건너뜁니다.")
                    analysis_results["ip_country_mapping"] = {}
                    analysis_results["country_statistics"] = {}
            except Exception as e:
                logger.error(f"❌ 국가 정보 매핑 중 오류: {str(e)}")
                analysis_results["ip_country_mapping"] = {}
                analysis_results["country_statistics"] = {}
            finally:
                # 국가 정보 매핑 단계 완료 반영
                if progress is not None and task_id is not None:
                    progress.advance(task_id)

            return analysis_results

        except Exception as e:
            logger.error(f"❌ DuckDB 분석 실패: {str(e)}")
            return self._get_empty_analysis_results()

    def _get_empty_analysis_results(self) -> dict[str, Any]:
        """빈 분석 결과를 반환합니다."""
        return {
            # 기본 정보
            "start_time": self.start_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "actual_start_time": "N/A",
            "actual_end_time": "N/A",
            "timezone": self.timezone.zone,
            "log_lines_count": 0,
            "log_files_count": 0,
            "log_files_path": "",
            "unique_client_ips": 0,
            "total_received_bytes": 0,
            "total_sent_bytes": 0,
            # S3 정보
            "s3_bucket_name": self.bucket_name,
            "s3_prefix": self.prefix,
            "s3_uri": f"s3://{self.bucket_name}/{self.prefix}",
            # 카운트 데이터
            "elb_2xx_count": 0,
            "elb_3xx_count": 0,
            "elb_4xx_count": 0,
            "elb_5xx_count": 0,
            "backend_4xx_count": 0,
            "backend_5xx_count": 0,
            "long_response_count": 0,
            # 타임스탬프
            "elb_error_timestamps": [],
            "backend_error_timestamps": [],
            "elb_2xx_timestamps": [],
            "elb_3xx_timestamps": [],
            "elb_4xx_timestamps": [],
            "elb_5xx_timestamps": [],
            "backend_4xx_timestamps": [],
            "backend_5xx_timestamps": [],
            # 카운트 데이터
            "client_ip_counts": {},
            "client_status_statistics": {},
            "target_status_statistics": {},
            "request_url_counts": {},
            "user_agent_counts": {},
            "abuse_ips": [],
            "abuse_ips_list": [],
            "abuse_ip_details": {},
            "long_response_times": [],
            "received_bytes": {},
            "sent_bytes": {},
            # 추가 분석 데이터
            "response_time_percentiles": {},
            "error_reason_counts": {},
            "target_request_stats": {},
            "url_error_stats": {},
            # 성능 분석 데이터 (TPS, SLA, Target Latency)
            "tps_time_series": [],
            "sla_compliance": {},
            "target_latency_stats": {},
            "response_time_distribution": {},
            "bucket_minutes": 15,
            # 추가 분석 데이터 (Phase 2)
            "processing_time_breakdown": {},
            "connection_failures": {},
            "http_version_distribution": {},
            "ssl_stats": {},
            "actions_stats": {},
            "classification_stats": {},
            # 국가 정보
            "ip_country_mapping": {},
            "country_statistics": {},
            # 전체 로그 데이터
            "ELB 2xx Count": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "ELB 3xx Count": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "ELB 4xx Count": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "ELB 5xx Count": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "Backend 4xx Count": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "Backend 5xx Count": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "ELB 2xx Timestamp": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "ELB 3xx Timestamp": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "ELB 4xx Timestamp": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "ELB 5xx Timestamp": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "Backend 4xx Timestamp": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "Backend 5xx Timestamp": {
                "full_logs": [],
                "timestamps": [],
                "count": 0,
                "fill": None,
            },
            "request_url_details": {},
        }

    def clean_up(self, directories: list[str]) -> None:
        """임시 파일 및 디렉토리를 정리합니다."""
        try:
            # DuckDB 연결 정리
            if hasattr(self, "conn") and self.conn:
                self.conn.close()
                logger.debug("✅ DuckDB 연결 정리 완료")

            # 다운로드 디렉토리 명시적 정리
            if hasattr(self, "download_dir") and os.path.exists(self.download_dir):
                try:
                    logger.debug(f"다운로드 디렉토리 정리 중: {self.download_dir}")
                    shutil.rmtree(self.download_dir, ignore_errors=True)
                    logger.debug(f"✅ 다운로드 디렉토리 정리 완료: {self.download_dir}")
                except Exception as e:
                    logger.error(f"❌ 다운로드 디렉토리 정리 실패: {self.download_dir}, 오류: {str(e)}")

            # 압축 해제 디렉토리 명시적 정리
            if hasattr(self, "decompressed_dir") and os.path.exists(self.decompressed_dir):
                try:
                    logger.debug(f"압축 해제 디렉토리 정리 중: {self.decompressed_dir}")
                    shutil.rmtree(self.decompressed_dir, ignore_errors=True)
                    logger.debug(f"✅ 압축 해제 디렉토리 정리 완료: {self.decompressed_dir}")
                except Exception as e:
                    logger.error(f"❌ 압축 해제 디렉토리 정리 실패: {self.decompressed_dir}, 오류: {str(e)}")

            # DuckDB 작업 임시 디렉토리 정리
            if (
                hasattr(self, "temp_work_dir")
                and isinstance(self.temp_work_dir, str)
                and os.path.exists(self.temp_work_dir)
            ):
                try:
                    logger.debug(f"임시 디렉토리 정리 중: {self.temp_work_dir}")
                    shutil.rmtree(self.temp_work_dir, ignore_errors=True)
                    logger.debug(f"✅ 임시 디렉토리 정리 완료: {self.temp_work_dir}")
                except Exception as e:
                    logger.error(f"❌ 임시 디렉토리 정리 실패: {self.temp_work_dir}, 오류: {str(e)}")

            # DuckDB 파일 및 디렉토리 정리 (일회성 분석이므로 삭제)
            if (
                hasattr(self, "duckdb_db_path")
                and isinstance(self.duckdb_db_path, str)
                and os.path.exists(self.duckdb_db_path)
            ):
                try:
                    logger.debug(f"DuckDB 파일 삭제 중: {self.duckdb_db_path}")
                    os.remove(self.duckdb_db_path)
                    logger.debug(f"✅ DuckDB 파일 삭제 완료: {self.duckdb_db_path}")
                except Exception as e:
                    logger.error(f"❌ DuckDB 파일 삭제 실패: {self.duckdb_db_path}, 오류: {str(e)}")

            if hasattr(self, "duckdb_dir") and isinstance(self.duckdb_dir, str) and os.path.isdir(self.duckdb_dir):
                try:
                    # 비어 있으면 제거
                    if not os.listdir(self.duckdb_dir):
                        os.rmdir(self.duckdb_dir)
                except Exception:
                    pass  # nosec B110 - Directory cleanup is best-effort

            # 기존에 전달된 디렉토리도 정리
            already_cleaned = []
            if hasattr(self, "download_dir"):
                already_cleaned.append(self.download_dir)
            if hasattr(self, "decompressed_dir"):
                already_cleaned.append(self.decompressed_dir)

            for directory in directories:
                # 이미 처리한 디렉토리면 스킵
                if directory in already_cleaned:
                    logger.debug(f"스킵: 이미 정리된 디렉토리 - {directory}")
                    continue

                if not isinstance(directory, str):
                    logger.warning(f"스킵: 디렉토리가 문자열이 아님 - {type(directory)}: {directory}")
                    continue

                if os.path.exists(directory):
                    try:
                        logger.debug(f"임시 디렉토리 정리 중: {directory}")
                        shutil.rmtree(directory, ignore_errors=True)
                        logger.debug(f"✅ 임시 디렉토리 정리 완료: {directory}")
                    except Exception as e:
                        logger.error(f"❌ 디렉토리 정리 실패: {directory}, 오류: {str(e)}")
        except Exception as e:
            logger.error(f"정리 과정 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    # 테스트 실행
    print("🚀 DuckDB 기반 ALB 로그 분석기 테스트")

    # 샘플 로그 디렉토리로 테스트
    log_dir = "data/log"
    if os.path.exists(log_dir):
        # 더미 매개변수로 분석기 생성
        analyzer = ALBLogAnalyzer(
            s3_client=None,
            bucket_name="test",
            prefix="test",
            start_datetime=datetime.now(),
        )

        results = analyzer.analyze_logs(log_dir)
        print(f"📊 분석 결과: {len(results)}개 카테고리")

        for key, value in results.items():
            if isinstance(value, list):
                print(f"  - {key}: {len(value)}개 항목")
            elif isinstance(value, dict):
                print(f"  - {key}: {len(value)}개 필드")
            else:
                print(f"  - {key}: {value}")

        analyzer.clean_up([])
    else:
        print(f"❌ 로그 디렉토리를 찾을 수 없습니다: {log_dir}")
