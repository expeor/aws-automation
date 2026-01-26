from __future__ import annotations

import bisect
import concurrent.futures
import gc
import gzip
import os
import shutil
from collections import namedtuple
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytz  # type: ignore[import-untyped]
from botocore.exceptions import ClientError
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

# 콘솔 및 로거 (aa_cli.aa.ui 또는 로컬 생성)
try:
    from cli.ui import (
        console,
        logger,
        print_sub_info,
        print_sub_task_done,
        print_sub_warning,
    )
except ImportError:
    import logging

    console = Console()
    logger = logging.getLogger(__name__)

    # Fallback functions
    def print_sub_info(msg: str) -> None:
        console.print(f"[blue]{msg}[/blue]")

    def print_sub_task_done(msg: str) -> None:
        console.print(f"[green]✓ {msg}[/green]")

    def print_sub_warning(msg: str) -> None:
        console.print(f"[yellow]! {msg}[/yellow]")


import contextlib

from core.tools.cache import get_cache_dir


def _create_report_directory(prefix: str, session_name: str = "") -> str:
    """보고서 디렉토리 생성 (레거시 호환)"""
    from datetime import datetime

    timestamp = datetime.now().strftime("%Y%m%d")
    base_dir = os.path.join("output", session_name or "default", prefix, timestamp)
    os.makedirs(base_dir, exist_ok=True)
    return base_dir


class LogDownloadError(Exception):
    """로그 다운로드 중 발생하는 오류"""

    pass


# 경량화된 S3 객체 정보 (캐시 제거)
S3LogFile = namedtuple("S3LogFile", ["key", "last_modified", "size", "timestamp"])


class ALBLogDownloader:
    def __init__(
        self,
        s3_client: Any,
        s3_uri: str,
        start_datetime: Any,
        end_datetime: Any | None = None,
        timezone: str = "Asia/Seoul",
        max_workers: int = 5,
        chunk_size: int = 8 * 1024 * 1024,  # 8MB
        session_name: str = "default",
        batch_size: int = 50,
        smart_filtering: bool = True,  # 스마트 필터링 활성화
    ):
        """
        ALB 로그 다운로더를 초기화합니다.

        Args:
            s3_client: S3 클라이언트 (readonly 역할로 설정된 클라이언트)
            s3_uri: S3 URI (예: s3://bucket-name/prefix/AWSLogs/account-number/elasticloadbalancing/region)
            start_datetime: 시작 시간 (datetime 객체 또는 문자열)
            end_datetime: 종료 시간 (datetime 객체 또는 문자열, 기본값: None)
            timezone: 타임존 (기본값: Asia/Seoul)
            max_workers: 병렬 다운로드 최대 작업자 수 (기본값: 5)
            chunk_size: 다운로드 청크 크기 (기본값: 8MB)
            session_name: 세션 이름 (기본값: default)
            batch_size: 한 번에 처리할 파일 수 (기본값: 50)
            smart_filtering: 스마트 필터링 활성화 여부
        """
        # 🚀 auth 세션 유지 - 원본 클라이언트 그대로 사용
        self.s3_client = s3_client  # auth에서 받은 인증된 클라이언트 사용
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.session_name = session_name
        self.batch_size = batch_size
        self.smart_filtering = smart_filtering

        # S3 URI 파싱
        if not s3_uri.startswith("s3://"):
            raise ValueError("S3 URI는 's3://'로 시작해야 합니다.")

        self.s3_uri = s3_uri  # Store for later use

        # s3:// 제거
        path = s3_uri[5:]

        # 버킷 이름과 접두사 분리
        parts = path.split("/", 1)
        self.bucket_name = parts[0]
        self.prefix = parts[1] if len(parts) > 1 else ""

        # 접두사가 있는 경우 끝에 '/' 추가
        if self.prefix and not self.prefix.endswith("/"):
            self.prefix += "/"

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
            # 시간에 타임존 정보 추가
            self.start_datetime = self.timezone.localize(self.start_datetime)
            self.end_datetime = self.timezone.localize(self.end_datetime)

            # UTC로 변환 (S3 타임스탬프는 UTC 기준)
            self.start_datetime_utc = self.start_datetime.astimezone(pytz.UTC)
            self.end_datetime_utc = self.end_datetime.astimezone(pytz.UTC)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"알 수 없는 타임존 '{timezone}'입니다. UTC를 사용합니다.")
            self.timezone = pytz.UTC
            self.start_datetime = self.timezone.localize(self.start_datetime)
            self.end_datetime = self.timezone.localize(self.end_datetime)
            self.start_datetime_utc = self.start_datetime
            self.end_datetime_utc = self.end_datetime

        self.console = console

        # ALB 로그 전용 디렉토리 (temp/alb 하위)
        alb_data_dir = get_cache_dir("alb")
        self.temp_dir = os.path.join(alb_data_dir, "gz")  # gz 파일 저장
        self.decompressed_dir = os.path.join(alb_data_dir, "log")  # 압축 해제된 로그 저장

        # 요청 범위 미스매치 시 사용자 안내를 위해 S3에서 확인된 실제 로그 범위(KST)를 저장
        self.available_range_local: tuple[datetime, datetime] | None = None

        # 디렉토리 생성
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.decompressed_dir, exist_ok=True)

        # 출력 디렉토리 설정
        self.output_dir = _create_report_directory("alb_log", self.session_name)
        self.report_filename = self._generate_report_filename()

        print_sub_info(f"분석 기간: {self.start_datetime} ~ {self.end_datetime} ({timezone})")

    def _generate_report_filename(self) -> str:
        """보고서 파일 이름을 생성합니다."""
        from secrets import token_hex

        # AWS ALB 로그 파일 네이밍 규칙에 맞는 파일명 생성 시도
        try:
            aws_account_id = "unknown"
            region = "unknown"

            # S3 URI에서 정보 추출
            if "/AWSLogs/" in self.s3_uri:
                path = self.s3_uri.replace("s3://", "")
                aws_logs_path = path.split("/AWSLogs/")[1]
                path_parts = aws_logs_path.split("/")

                if len(path_parts) >= 3:
                    aws_account_id = path_parts[0]
                    region = path_parts[2]

            # Load Balancer ID 추출
            s3_parts = self.s3_uri.replace("s3://", "").split("/")
            bucket_name = s3_parts[0] if len(s3_parts) > 0 else ""
            prefix_parts = s3_parts[1:-2] if len(s3_parts) > 2 else []  # AWSLogs 전까지의 prefix

            load_balancer_id = ""
            if prefix_parts:
                load_balancer_id = "-".join(prefix_parts).replace("/", "-")
            elif bucket_name:
                load_balancer_id = bucket_name.replace("-", "-")

            if not load_balancer_id:
                load_balancer_id = "elb"

            # 간결하고 고유한 이름으로 축소
            suffix = token_hex(4)  # 8 hex chars
            return f"{aws_account_id}_{region}_alb_{suffix}.xlsx"

        except Exception:
            # 오류 발생 시 기본 파일명 반환 (filename generation fallback)
            suffix = token_hex(4)
            return f"alb_{suffix}.xlsx"

    def _smart_date_range_optimization(self) -> list[str]:
        """스마트 날짜 범위 최적화 - 시간 범위에 따라 접두사 세분화"""
        prefixes = []

        # 시간 범위 계산 (UTC 기준)
        time_diff = self.end_datetime_utc - self.start_datetime_utc
        total_hours = time_diff.total_seconds() / 3600

        logger.debug(f"📊 분석 대상 시간: {total_hours:.1f}시간")

        # 🔧 수정: 원래 시간대(로컬) 기준으로 날짜 범위 계산
        # ALB 로그 파일은 S3에 UTC 기준으로 저장되지만, 파일 경로의 날짜 부분은
        # 사용자가 요청한 시간대를 반영해야 합니다
        local_start_date = self.start_datetime.date()
        local_end_date = self.end_datetime.date()

        # 안전을 위해 시작날짜에서 1일 앞, 종료날짜에서 1일 뒤까지 확장
        extended_start_date = local_start_date - timedelta(days=1)
        extended_end_date = local_end_date + timedelta(days=1)

        logger.debug(f"📅 로컬 날짜 범위: {local_start_date} ~ {local_end_date}")
        logger.debug(f"📅 확장된 날짜 범위: {extended_start_date} ~ {extended_end_date}")

        if total_hours <= 24:  # 24시간 이하
            # 일 단위로만 조회 (ALB 로그는 하루 단위로 파티셔닝)
            current_date = extended_start_date

            while current_date <= extended_end_date:
                date_path = current_date.strftime("%Y/%m/%d")
                date_prefix = f"{self.prefix}{date_path}"
                prefixes.append(date_prefix)
                current_date += timedelta(days=1)

        elif total_hours <= 168:  # 1주일 이하
            # 일 단위 조회
            current_date = extended_start_date

            while current_date <= extended_end_date:
                date_path = current_date.strftime("%Y/%m/%d")
                date_prefix = f"{self.prefix}{date_path}"
                prefixes.append(date_prefix)
                current_date += timedelta(days=1)

        else:  # 1주일 초과
            # 기존 방식: 일 단위 접두사
            current_date = extended_start_date

            while current_date <= extended_end_date:
                date_path = current_date.strftime("%Y/%m/%d")
                date_prefix = f"{self.prefix}{date_path}"
                prefixes.append(date_prefix)
                current_date += timedelta(days=1)

        logger.debug(f"✓ 날짜별 접두사 생성 완료: {len(prefixes)}개")
        logger.debug(f"생성된 접두사 목록: {prefixes}")
        return prefixes

    def _extract_timestamp_from_key(self, key: str) -> datetime | None:
        """S3 객체 키에서 타임스탬프를 추출합니다."""
        try:
            # ALB 로그 파일명 형식에서 타임스탬프 추출
            parts = key.split("/")
            if len(parts) >= 7:
                # 파일명에서 타임스탬프 추출
                filename = parts[-1]
                filename_parts = filename.split("_")

                if len(filename_parts) >= 5:
                    # 실제 ALB 파일명 구조에 맞게 수정
                    # 파일명: account_elasticloadbalancing_region_loadbalancer_timestamp_ip_randomstring.log.gz
                    # 타임스탬프는 뒤에서 3번째 위치 (IP 주소 앞)
                    timestamp_str = filename_parts[-3]  # timestamp 부분 추출 (수정됨)

                    # 디버깅을 위한 첫 번째 파일 정보 출력
                    if not hasattr(self, "_debug_printed"):
                        logger.debug(f"ALB 로그 파일명 분석: {filename} → {timestamp_str}")
                        self._debug_printed = True

                    # 다양한 타임스탬프 형식 시도
                    try:
                        # 1. YYYYMMDDTHHMMSSZ 형식 (Z 포함)
                        if "T" in timestamp_str and timestamp_str.endswith("Z"):
                            return datetime.strptime(timestamp_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=pytz.UTC)
                    except ValueError:
                        pass

                    try:
                        # 2. YYYYMMDDTHHMMSS 형식 (Z 없음)
                        if "T" in timestamp_str and len(timestamp_str) >= 15:
                            return datetime.strptime(timestamp_str, "%Y%m%dT%H%M%S").replace(tzinfo=pytz.UTC)
                    except ValueError:
                        pass

                    try:
                        # 3. 숫자만으로 구성된 형식 (YYYYMMDDHHMMS)
                        if timestamp_str.isdigit() and len(timestamp_str) >= 14:
                            return datetime.strptime(timestamp_str[:14], "%Y%m%d%H%M%S").replace(tzinfo=pytz.UTC)
                    except ValueError:
                        pass

                    # 모든 형식 실패시 경고 출력
                    logger.debug(f"타임스탬프 파싱 실패: {timestamp_str} (파일: {filename})")

                # 경로에서 날짜 추출 시도
                try:
                    year = int(parts[-4])
                    month = int(parts[-3])
                    day = int(parts[-2])
                    # 경로에서 추출한 날짜를 기본값으로 사용 (시간은 자정으로 설정)
                    return datetime(year, month, day, tzinfo=pytz.UTC)
                except (ValueError, IndexError):
                    pass

            return None
        except Exception as e:
            logger.debug(f"타임스탬프 추출 실패 ({key}): {str(e)}")
            return None

    def _binary_search_time_filter(self, log_files: list[S3LogFile]) -> list[S3LogFile]:
        """바이너리 서치를 사용한 시간 범위 필터링"""
        if not self.smart_filtering or not log_files:
            # 스마트 필터링 비활성화시 기존 방식
            return [
                f for f in log_files if f.timestamp and self.start_datetime_utc <= f.timestamp <= self.end_datetime_utc
            ]

        # 타임스탬프가 있는 파일들만 필터링
        files_with_timestamp = [f for f in log_files if f.timestamp]
        files_without_timestamp = [f for f in log_files if not f.timestamp]

        logger.debug(
            f"바이너리 서치 필터링: {len(log_files)} → {len(files_with_timestamp)} 파일 (타임스탬프 추출 성공)"
        )
        logger.debug(f"타임스탬프 추출 실패: {len(files_without_timestamp)} 파일")
        logger.debug(f"검색 시간 범위: {self.start_datetime_utc} ~ {self.end_datetime_utc}")

        if not files_with_timestamp:
            logger.warning("타임스탬프를 추출할 수 있는 파일이 없습니다.")
            return log_files  # 원본 반환

        # 타임스탬프 추출에 실패한 파일들도 포함 (안전망)
        if files_without_timestamp:
            logger.debug(f"타임스탬프 추출 실패한 파일 {len(files_without_timestamp)}개도 포함합니다.")

        # 타임스탬프로 정렬
        files_with_timestamp.sort(key=lambda x: x.timestamp)

        # 타임스탬프 범위 정보 출력 및 사용자 타임존 범위 저장
        if files_with_timestamp:
            earliest_timestamp = files_with_timestamp[0].timestamp
            latest_timestamp = files_with_timestamp[-1].timestamp
            logger.debug(f"파일 타임스탬프 범위: {earliest_timestamp} ~ {latest_timestamp}")
            try:
                earliest_local = earliest_timestamp.astimezone(self.timezone)
                latest_local = latest_timestamp.astimezone(self.timezone)
                self.available_range_local = (earliest_local, latest_local)
            except Exception:
                self.available_range_local = None  # Timezone conversion fallback

        # 🎯 ALB 5분 단위 적재 특성에 맞춘 10분 확장 (여유있게)
        # ALB는 5분 구간 로그를 구간 끝 시간에 저장 (예: 08:00~08:05 → T0805Z 파일)
        from datetime import timedelta

        extended_start_datetime_utc = self.start_datetime_utc - timedelta(minutes=10)
        extended_end_datetime_utc = self.end_datetime_utc + timedelta(minutes=10)

        logger.debug(f"요청된 시간 범위: {self.start_datetime_utc} ~ {self.end_datetime_utc} (UTC)")
        logger.debug(f"ALB 특성 고려 확장: {extended_start_datetime_utc} ~ {extended_end_datetime_utc} (±10분)")

        # 바이너리 서치로 시작/끝 인덱스 찾기 (10분 확장된 범위 사용)
        start_idx = bisect.bisect_left(files_with_timestamp, extended_start_datetime_utc, key=lambda x: x.timestamp)

        end_idx = bisect.bisect_right(files_with_timestamp, extended_end_datetime_utc, key=lambda x: x.timestamp)

        logger.debug(f"바이너리 서치 결과: {start_idx} ~ {end_idx} (선택: {end_idx - start_idx}개)")

        filtered_files = files_with_timestamp[start_idx:end_idx]

        # 타임스탬프 추출 실패한 파일들도 추가 (안전망)
        filtered_files.extend(files_without_timestamp)

        logger.debug(f"시간 범위 필터링 완료: {len(filtered_files)}개 파일 선택")

        # 최종 필터링 결과가 비어있는 경우 명확한 메시지 제공
        if not filtered_files:
            logger.error("❌ 요청 범위에 해당하는 ALB 로그 파일을 찾지 못했습니다.")
            logger.error(f"   요청 범위({self.timezone.zone}): {self.start_datetime} ~ {self.end_datetime}")
            if files_with_timestamp:
                earliest_local = files_with_timestamp[0].timestamp.astimezone(self.timezone)
                latest_local = files_with_timestamp[-1].timestamp.astimezone(self.timezone)
                self.available_range_local = (earliest_local, latest_local)
                # 가장 최근 파일 시각 기준 권장 구간 제안 (최근 10분)
                try:
                    suggest_start = latest_local - timedelta(minutes=10)
                    suggest_end = latest_local
                    logger.error(f"   S3 실제 로그 범위: {earliest_local} ~ {latest_local}")
                    logger.error(f"   권장: 최근 유효 시각 근처로 재시도 (예: {suggest_start} ~ {suggest_end})")
                except Exception:
                    logger.error(f"   S3 실제 로그 범위: {earliest_local} ~ {latest_local}")  # Fallback message
            logger.error(
                "   참고: ALB는 5분 단위 파일을 생성하며, 트래픽 0 또는 전송 지연 시 해당 구간 파일이 생성되지 않습니다."
            )

        return filtered_files

    def _adaptive_batch_size(self, total_files: int, avg_file_size: float) -> int:
        """파일 수와 크기에 따른 적응형 배치 크기 계산"""
        base_batch_size = self.batch_size

        # 파일 수가 적으면 배치 크기 감소
        if total_files < 20:
            return min(5, total_files)

        # 파일 크기가 큰 경우 배치 크기 감소
        if avg_file_size > 50 * 1024 * 1024:  # 50MB 이상
            return max(10, base_batch_size // 2)
        elif avg_file_size > 20 * 1024 * 1024:  # 20MB 이상
            return max(20, int(base_batch_size / 1.5))  # float 결과를 int로 변환
        elif avg_file_size < 5 * 1024 * 1024:  # 5MB 미만
            return min(100, base_batch_size * 2)

        return base_batch_size

    def _list_objects_for_prefix(self, prefix: str, progress: Progress, task_id: Any) -> list[S3LogFile]:
        """특정 접두사에 대한 S3 객체 목록을 최적화하여 반환합니다."""
        result = []
        paginator = self.s3_client.get_paginator("list_objects_v2")

        try:
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    key = obj["Key"]
                    if key.endswith(".log.gz"):
                        # S3LogFile namedtuple 생성
                        timestamp = self._extract_timestamp_from_key(key)
                        log_file = S3LogFile(
                            key=key,
                            last_modified=obj["LastModified"].replace(tzinfo=pytz.UTC),
                            size=obj["Size"],
                            timestamp=timestamp,
                        )
                        result.append(log_file)
                        progress.update(task_id, advance=1)

            logger.debug(f"✓ 접두사 '{prefix}'에서 {len(result)}개의 로그 파일을 찾았습니다.")
            return result

        except Exception as e:
            logger.error(f"❌ 객체 목록 조회 실패 ({prefix}): {str(e)}")
            return []

    def _list_objects_for_prefix_simple(self, prefix: str) -> list[S3LogFile]:
        """특정 접두사에 대한 S3 객체 목록을 간단히 반환합니다 (Progress 없이)."""
        result = []
        paginator = self.s3_client.get_paginator("list_objects_v2")

        try:
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    key = obj["Key"]
                    if key.endswith(".log.gz"):
                        # S3LogFile namedtuple 생성
                        timestamp = self._extract_timestamp_from_key(key)
                        log_file = S3LogFile(
                            key=key,
                            last_modified=obj["LastModified"].replace(tzinfo=pytz.UTC),
                            size=obj["Size"],
                            timestamp=timestamp,
                        )
                        result.append(log_file)

            logger.debug(f"✓ 접두사 '{prefix}'에서 {len(result)}개의 로그 파일을 찾았습니다.")
            return result

        except Exception as e:
            logger.error(f"❌ 객체 목록 조회 실패 ({prefix}): {str(e)}")
            return []

    def _verify_s3_access(self) -> bool:
        """S3 버킷 접근 권한을 사전 검증합니다.

        Returns:
            True: 접근 가능

        Raises:
            LogDownloadError: 접근 권한이 없는 경우
        """
        try:
            # HeadBucket으로 버킷 존재 및 접근 권한 확인
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.debug(f"✓ S3 버킷 접근 확인 완료: {self.bucket_name}")
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            if error_code == "403":
                raise LogDownloadError(
                    f"❌ S3 버킷 '{self.bucket_name}'에 대한 접근 권한이 없습니다.\n\n"
                    f"   가능한 원인:\n"
                    f"   1. 현재 역할/사용자에게 "
                    f"s3:GetObject, s3:ListBucket 권한이 없음\n"
                    f"   2. S3 버킷 정책이 현재 계정/역할의 접근을 거부\n"
                    f"   3. 버킷이 다른 AWS 계정에 있고 "
                    f"크로스 계정 접근 설정이 안 됨\n\n"
                    f"   해결 방법:\n"
                    f"   - S3 버킷이 있는 계정에서 직접 접근하거나\n"
                    f"   - S3 버킷 정책에 현재 역할에 대한 접근 권한 추가 필요"
                ) from e
            elif error_code == "404":
                raise LogDownloadError(
                    f"❌ S3 버킷 '{self.bucket_name}'을(를) 찾을 수 없습니다.\n   버킷 이름을 확인해주세요."
                ) from e
            else:
                raise LogDownloadError(
                    f"❌ S3 버킷 '{self.bucket_name}' 접근 오류: {error_code}\n   상세: {str(e)}"
                ) from e
        except Exception as e:
            raise LogDownloadError(f"❌ S3 버킷 '{self.bucket_name}' 접근 확인 실패: {str(e)}") from e

    def download_logs(self) -> list[str]:
        """최적화된 방식으로 S3에서 로그 파일을 다운로드합니다."""
        try:
            # 🔐 S3 버킷 접근 권한 사전 검증
            self._verify_s3_access()

            # 🗂️ 임시 디렉터리 정리 (기존 파일 모두 삭제)
            logger.debug("✓ 디렉터리 정리 시작 (gz + log)")
            self._clean_directory(self.temp_dir)  # gz 파일 디렉터리
            self._clean_directory(self.decompressed_dir)  # log 파일 디렉터리
            logger.debug("✓ 디렉터리 정리 완료 (gz + log)")

            # 날짜 범위 생성
            date_prefixes = self._smart_date_range_optimization()

            if not date_prefixes:
                print_sub_warning("생성된 날짜별 접두사가 없습니다.")
                return []

            # S3에서 로그 파일 검색 및 시간 필터링
            all_log_files = self._get_log_files_from_s3(date_prefixes)

            # 전체 발견 파일 수 로그
            if all_log_files:
                print_sub_task_done(f"S3에서 총 {len(all_log_files)}개 파일 발견, 시간 범위로 필터링 중...")

            filtered_files = self._binary_search_time_filter(all_log_files)

            if not filtered_files:
                # 사용자 친화적 메시지 (가능하면 실제 가능한 범위와 권장 구간 포함)
                print_sub_warning(f"시간 범위 ({self.start_datetime} ~ {self.end_datetime}) 내에 로그 파일이 없습니다.")
                if self.available_range_local:
                    earliest_local, latest_local = self.available_range_local
                    try:
                        suggest_start = latest_local - timedelta(minutes=10)
                        suggest_end = latest_local
                        print_sub_warning(f"실제 로그 범위({self.timezone.zone}): {earliest_local} ~ {latest_local}")
                        print_sub_warning(f"권장 재시도: {suggest_start} ~ {suggest_end} 또는 범위를 넓혀 재시도")
                    except Exception:
                        print_sub_warning(
                            f"실제 로그 범위({self.timezone.zone}): {earliest_local} ~ {latest_local}"
                        )  # Fallback
                return []

            total_files = len(filtered_files)
            total_size = sum(f.size for f in filtered_files)
            avg_file_size = total_size / total_files if total_files > 0 else 0

            # 적응형 배치 크기 계산
            adaptive_batch_size = self._adaptive_batch_size(total_files, avg_file_size)

            print_sub_task_done(
                f"필터링 완료: {total_files}개 파일 다운로드 시작 (총 크기: {total_size / 1024 / 1024:.1f}MB)"
            )

            # 파일 크기별 정렬 (큰 파일 먼저 - 병렬 처리 효율성 향상)
            filtered_files.sort(key=lambda x: x.size, reverse=True)

            # 배치 단위로 다운로드
            downloaded_files = []

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self.console,
            ) as progress:
                download_task = progress.add_task(
                    f"[cyan]로그 파일 다운로드 중 (0/{total_files})...",
                    total=total_files,
                )

                # 적응형 배치로 다운로드
                for i in range(0, total_files, adaptive_batch_size):
                    batch = filtered_files[i : i + adaptive_batch_size]
                    batch_size_mb = sum(f.size for f in batch) / 1024 / 1024

                    logger.debug(f"배치 {i // adaptive_batch_size + 1}: {len(batch)}개 파일, {batch_size_mb:.1f}MB")

                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=min(self.max_workers, len(batch))
                    ) as executor:
                        future_to_file = {
                            executor.submit(
                                self._download_single_file,
                                f.key,
                                progress,
                                download_task,
                            ): f
                            for f in batch
                        }

                        for future in concurrent.futures.as_completed(future_to_file):
                            log_file = future_to_file[future]
                            try:
                                result = future.result()
                                if result:
                                    downloaded_files.append(result)
                                progress.update(download_task, advance=1)
                            except Exception as e:
                                logger.error(f"❌ 파일 다운로드 실패 ({log_file.key}): {str(e)}")
                                progress.update(download_task, advance=1)

                    # 배치 완료 후 메모리 정리
                    gc.collect()

            if not downloaded_files:
                raise LogDownloadError("다운로드된 파일이 없습니다.")

            print_sub_task_done(f"다운로드 완료: {len(downloaded_files)}개 파일")
            return downloaded_files

        except Exception as e:
            logger.error(f"로그 다운로드 중 오류 발생: {str(e)}")
            raise LogDownloadError(f"로그 다운로드 중 오류 발생: {str(e)}") from e

    def _download_single_file(self, key: str, progress: Progress, task_id: Any) -> str | None:
        """단일 파일을 다운로드합니다."""
        try:
            # 🔧 수정: 모든 파일을 한 폴더에 저장 (날짜별 디렉토리 분리 제거)
            filename = os.path.basename(key)
            local_path = os.path.join(self.temp_dir, filename)

            # Path traversal 방지: 경로가 temp_dir 내에 있는지 검증
            resolved_path = Path(local_path).resolve()
            temp_dir_resolved = Path(self.temp_dir).resolve()
            if not str(resolved_path).startswith(str(temp_dir_resolved)):
                logger.warning(f"Path traversal 시도 감지: {key}")
                return None

            # 파일이 이미 존재하는지 확인 (중복 다운로드 방지)
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                logger.debug(f"파일이 이미 존재: {filename} ({file_size / 1024 / 1024:.2f}MB)")
                return local_path

            try:
                # 🚀 Connection pool 최적화된 TransferConfig 사용 (auth 세션 유지)
                from boto3.s3.transfer import TransferConfig

                # TransferConfig 설정 - Connection pool 경고 해결
                transfer_config = TransferConfig(
                    multipart_threshold=self.chunk_size,
                    max_concurrency=10,  # auth session pool(10개)
                    multipart_chunksize=self.chunk_size,
                    use_threads=True,
                    max_io_queue=1000,  # I/O 큐 크기 증가
                    io_chunksize=262144,  # I/O 청크 크기 최적화 (256KB)
                    num_download_attempts=3,  # 다운로드 재시도 횟수
                )

                with open(local_path, "wb") as f:
                    # auth에서 받은 인증된 S3 클라이언트 사용 (세션 유지)
                    self.s3_client.download_fileobj(
                        Bucket=self.bucket_name,
                        Key=key,
                        Fileobj=f,
                        Config=transfer_config,  # 최적화된 TransferConfig 사용 ⭐
                    )

                # 파일 크기 확인
                file_size = os.path.getsize(local_path)
                progress.update(
                    task_id,
                    description="[cyan]다운로드 진행중...",
                )

            except Exception as e:
                logger.error(f"❌ 파일 다운로드 실패 ({key}): {str(e)}")
                if os.path.exists(local_path):
                    os.remove(local_path)
                return None

            return local_path

        except Exception as e:
            logger.error(f"❌ 파일 다운로드 실패 ({key}): {str(e)}")
            return None

    def decompress_logs(self, gz_directory: str | None = None) -> str:
        """압축된 로그 파일을 해제합니다."""
        if gz_directory is None:
            gz_directory = self.temp_dir

        try:
            logger.debug(f"📂 압축 해제 시작 - gz 디렉토리: {gz_directory}")

            # gz 파일이 있는 디렉토리 검증
            if not os.path.exists(gz_directory):
                logger.error(f"❌ gz 디렉토리가 존재하지 않습니다: {gz_directory}")
                raise FileNotFoundError(f"gz 디렉토리가 존재하지 않습니다: {gz_directory}")

            # gz 파일 목록 가져오기
            gz_files = []
            for root, _, files in os.walk(gz_directory):
                for file in files:
                    if file.endswith(".gz"):
                        gz_files.append(os.path.join(root, file))

            if not gz_files:
                logger.error("❌ 압축된 로그 파일이 없습니다.")
                raise FileNotFoundError("압축된 로그 파일이 없습니다.")

            logger.debug(f"📦 발견된 gz 파일: {len(gz_files)}개")

            # 해제된 로그를 저장할 디렉토리 생성 (중복 정리 방지)
            self._clean_directory(self.decompressed_dir)
            logger.debug(f"📁 로그 디렉토리 생성: {self.decompressed_dir}")

            # gz 파일 해제
            decompressed_files = []
            logger.debug(f"🔧 압축 해제 시작: {len(gz_files)}개 파일")

            for gz_file_path in gz_files:
                # 🔧 수정: 모든 로그 파일을 한 폴더에 저장 (날짜별 디렉토리 분리 제거)
                # 압축 해제할 파일 경로
                log_file_path = os.path.join(
                    self.decompressed_dir, os.path.basename(gz_file_path)[:-3]
                )  # .gz 확장자 제거

                try:
                    # 압축 해제 진행
                    with (
                        gzip.open(gz_file_path, "rb") as gz_file,
                        open(log_file_path, "wb") as log_file,
                    ):
                        shutil.copyfileobj(gz_file, log_file)

                    # 개별 파일 로그를 DEBUG로 변경 (터미널 출력 정리)
                    logger.debug(
                        f"✓ 압축 해제 완료: {os.path.basename(gz_file_path)} -> {os.path.basename(log_file_path)}"
                    )

                    decompressed_files.append(log_file_path)

                except Exception as e:
                    logger.error(f"❌ 압축 해제 실패 {os.path.basename(gz_file_path)}: {str(e)}")
                    continue

            # 해제된 로그 파일 검증
            log_files = []
            for root, _, files in os.walk(self.decompressed_dir):
                for file in files:
                    if file.endswith(".log"):
                        log_files.append(os.path.join(root, file))

            if not log_files:
                logger.error("❌ 압축 해제된 로그 파일이 없습니다.")
                raise FileNotFoundError("압축 해제된 로그 파일이 없습니다.")

            # 압축 해제 완료 후 요약 출력 ⭐
            total_files = len(decompressed_files)
            if total_files > 0:
                logger.debug(f"✅ 압축 해제 완료: {total_files}개 파일")
            else:
                logger.warning("⚠️ 압축 해제된 파일이 없습니다.")

        except Exception as e:
            logger.error(f"❌ 압축 해제 중 오류 발생: {str(e)}")
            return ""

        logger.debug(
            f"✅ 총 {len(decompressed_files) if 'decompressed_files' in locals() else 0}개의 로그 파일이 압축 해제되었습니다."
        )
        logger.debug(f"📁 압축 해제 디렉토리: {self.decompressed_dir}")
        return self.decompressed_dir

    def _clean_directory(self, directory: str) -> None:
        """📁 디렉토리 내부 파일만 정리 (디렉토리 자체는 유지)"""
        try:
            # 디렉토리가 존재하지 않으면 생성만
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.debug(f"✓ 디렉토리 생성: {directory}")
                return

            # 📁 디렉토리 내부 파일과 하위 디렉토리만 삭제 (디렉토리 자체는 유지)
            for root, dirs, files in os.walk(directory, topdown=False):
                # 파일 삭제
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        os.unlink(file_path)
                    except Exception as e:
                        logger.debug(f"파일 삭제 실패 (무시됨): {file_path}, 오류: {e}")

                # 하위 디렉토리 삭제 (root 디렉토리는 유지)
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        os.rmdir(dir_path)
                    except Exception as e:
                        logger.debug(f"하위 디렉토리 삭제 실패 (무시됨): {dir_path}, 오류: {e}")

            logger.debug(f"✓ 디렉토리 내부 정리 완료: {directory}")

        except Exception as e:
            logger.error(f"❌ 디렉토리 정리 실패: {directory}, 오류: {e}")
            # 실패해도 디렉터리 생성 시도
            with contextlib.suppress(Exception):
                os.makedirs(directory, exist_ok=True)

    def _get_log_files_from_s3(self, date_prefixes: list[str]) -> list[S3LogFile]:
        """S3에서 로그 파일 목록을 간단하게 가져옵니다."""
        print_sub_info("S3에서 로그 파일 검색 중...")

        all_log_files = []

        # 날짜별 접두사 병렬 처리 (Progress bar 제거)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_workers, len(date_prefixes))) as executor:
            future_to_prefix = {
                executor.submit(self._list_objects_for_prefix_simple, prefix): prefix for prefix in date_prefixes
            }

            for future in concurrent.futures.as_completed(future_to_prefix):
                prefix = future_to_prefix[future]
                try:
                    files = future.result()
                    all_log_files.extend(files)
                except Exception as e:
                    logger.error(f"❌ 로그 파일 검색 실패 ({prefix}): {str(e)}")

        return all_log_files
