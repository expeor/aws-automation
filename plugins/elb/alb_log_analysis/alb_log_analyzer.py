#!/usr/bin/env python3
"""
🚀 DuckDB 기반 ALB 로그 분석기

기존 파싱 로직을 DuckDB SQL로 교체하여 초고속 분석을 제공합니다.
기존 인터페이스와 완전 호환성을 유지합니다.
"""

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
    from cli.ui import console, logger
except ImportError:
    import logging

    console = Console()
    logger = logging.getLogger(__name__)

import contextlib

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
                self.start_datetime = datetime.strptime(
                    start_datetime, "%Y-%m-%d %H:%M"
                )
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
        self.temp_work_dir = os.getenv("AA_DUCKDB_TEMP_DIR") or os.path.join(
            self.base_dir, "duckdb"
        )
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
        tz_name = (
            self.timezone.zone if hasattr(self.timezone, "zone") else str(self.timezone)
        )
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
        """🚀 DuckDB 기반 로그 파일들을 분석합니다."""
        try:
            self.console.print("[bold blue]🚀 ALB 로그 분석을 시작합니다...[/bold blue]")

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
                analysis_results = self._analyze_with_duckdb(
                    progress=progress, task_id=task
                )

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

            progress.update(task, description="[green]✅ 분석 완료!")
            self.console.print("[bold green]✅ ALB 로그 분석이 완료되었습니다![/bold green]")
            return analysis_results

        except Exception as e:
            logger.error(f"❌ 로그 분석 중 오류 발생: {str(e)}")
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
                            date_str = (
                                f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                            )
                        date_counts[date_str] = date_counts.get(date_str, 0) + 1
                    else:
                        # 3) 추가 패턴 시도 - 파일명 전체에서 날짜 찾기
                        date_anywhere = re.search(
                            r"(\d{4}[\-_]?\d{2}[\-_]?\d{2})", filename
                        )
                        if date_anywhere:
                            raw_date = date_anywhere.group(1).replace("_", "-")
                            if len(raw_date) == 8:  # YYYYMMDD
                                date_str = (
                                    f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                                )
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
                pass

            # 파일 리스트를 DuckDB가 이해할 수 있는 리스트 리터럴로 변환
            backslash = "\\"
            file_list_sql = ", ".join(
                [f"'{p.replace(backslash, '/')}'" for p in log_files]
            )

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
                extract_sent_bytes(line) as sent_bytes
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
                    target_display_key = (
                        f"{target_group_name}({target})"
                        if target_group_name
                        else target
                    )
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
                progress.update(
                    task_id, description="[cyan]IP/URL/User Agent 카운트 완료..."
                )
                progress.advance(task_id)

            # URL 별 상세 통계 (Top 100 URL 대상)
            request_url_details: dict[str, dict[str, Any]] = {}
            try:
                top_urls = [
                    str(url).strip() for url, _ in request_url_results[:100] if url
                ]
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

                    # 6) 총 카운트 (이미 계산된 request_url_counts 사용)
                    for url in top_urls:
                        request_url_details[url] = {
                            "count": int(request_url_counts.get(url, 0) or 0),
                            "methods": {},
                            "user_agents": {},
                            "status_codes": {},
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
                        if (
                            url in request_url_details
                            and status is not None
                            and status != ""
                        ):
                            request_url_details[url]["status_codes"][status] = int(cnt)

                    for url, uniq in unique_ip_rows:
                        if url in request_url_details:
                            try:
                                request_url_details[url]["unique_ips"] = int(uniq or 0)
                            except Exception:
                                request_url_details[url]["unique_ips"] = 0

                    for url, avg_rt in avg_rt_rows:
                        if url in request_url_details:
                            try:
                                request_url_details[url]["avg_response_time"] = float(
                                    avg_rt or 0.0
                                )
                            except Exception:
                                request_url_details[url]["avg_response_time"] = 0.0
            except Exception:
                # 세부 URL 통계는 선택 항목이므로 실패해도 전체 분석을 계속
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
                long_response_count_val = (
                    long_resp_count_row[0] if long_resp_count_row else 0
                )
            except Exception:
                long_response_count_val = 0

            # 바이트 분석
            received_bytes_query = """
            SELECT url, SUM(received_bytes) as total_bytes
            FROM alb_logs
            WHERE received_bytes > 0
            GROUP BY url
            ORDER BY total_bytes DESC
            """
            received_bytes_results = self.conn.execute(received_bytes_query).fetchall()
            received_bytes = {
                url: bytes_count for url, bytes_count in received_bytes_results
            }

            sent_bytes_query = """
            SELECT url, SUM(sent_bytes) as total_bytes
            FROM alb_logs
            WHERE sent_bytes > 0
            GROUP BY url
            ORDER BY total_bytes DESC
            """
            sent_bytes_results = self.conn.execute(sent_bytes_query).fetchall()
            sent_bytes = {url: bytes_count for url, bytes_count in sent_bytes_results}
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
            actual_start_time = (
                summary_result[2].strftime("%Y-%m-%d %H:%M:%S")
                if summary_result[2]
                else "N/A"
            )

            actual_end_time = (
                summary_result[3].strftime("%Y-%m-%d %H:%M:%S")
                if summary_result[3]
                else "N/A"
            )

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
                pass

            # 상태 코드별 로그 데이터 추가
            analysis_results.update(status_code_logs)

            # 🌍 국가 정보 추가 (IPIntelligence 통합 API 사용)
            try:
                if self.ip_intel.initialize():
                    logger.debug("🌍 IP 국가 정보 매핑 시작...")

                    # 고유한 클라이언트 IP 목록 추출
                    unique_ips = list(client_ip_counts.keys())

                    # 상위 10개 IP 디버깅 정보 출력
                    top_ips = sorted(
                        client_ip_counts.items(), key=lambda x: x[1], reverse=True
                    )[:10]
                    logger.debug(f"🔍 상위 10개 클라이언트 IP: {[ip for ip, count in top_ips]}")

                    # 국가 정보 매핑
                    country_mapping = self.ip_intel.get_country_codes_batch(unique_ips)

                    # 국가별 통계 생성
                    country_stats = self.ip_intel.get_country_statistics(unique_ips)

                    # 결과에 추가
                    analysis_results["ip_country_mapping"] = country_mapping
                    analysis_results["country_statistics"] = country_stats

                    # 상위 10개 IP의 국가 매핑 결과 출력
                    top_ip_countries = [
                        (ip, country_mapping.get(ip, "UNKNOWN"))
                        for ip, count in top_ips
                    ]
                    logger.debug(f"🌍 상위 10개 IP 국가 매핑: {top_ip_countries}")

                    logger.debug(
                        f"✅ 국가 정보 매핑 완료: {len(country_mapping)}개 IP, {len(country_stats)}개 국가"
                    )
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
                    logger.error(
                        f"❌ 다운로드 디렉토리 정리 실패: {self.download_dir}, 오류: {str(e)}"
                    )

            # 압축 해제 디렉토리 명시적 정리
            if hasattr(self, "decompressed_dir") and os.path.exists(
                self.decompressed_dir
            ):
                try:
                    logger.debug(f"압축 해제 디렉토리 정리 중: {self.decompressed_dir}")
                    shutil.rmtree(self.decompressed_dir, ignore_errors=True)
                    logger.debug(f"✅ 압축 해제 디렉토리 정리 완료: {self.decompressed_dir}")
                except Exception as e:
                    logger.error(
                        f"❌ 압축 해제 디렉토리 정리 실패: {self.decompressed_dir}, 오류: {str(e)}"
                    )

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
                    logger.error(
                        f"❌ DuckDB 파일 삭제 실패: {self.duckdb_db_path}, 오류: {str(e)}"
                    )

            if (
                hasattr(self, "duckdb_dir")
                and isinstance(self.duckdb_dir, str)
                and os.path.isdir(self.duckdb_dir)
            ):
                try:
                    # 비어 있으면 제거
                    if not os.listdir(self.duckdb_dir):
                        os.rmdir(self.duckdb_dir)
                except Exception:
                    pass

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
                    logger.warning(
                        f"스킵: 디렉토리가 문자열이 아님 - {type(directory)}: {directory}"
                    )
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
