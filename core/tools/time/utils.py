"""
pkg/time/utils.py - 날짜/시간 관련 유틸리티 함수들
"""

import os
from datetime import datetime, timezone


def get_local_timezone_offset() -> int:
    """로컬 시간대의 UTC 오프셋을 시간 단위로 반환합니다.

    Returns:
        int: UTC 오프셋 (예: KST는 +9)
    """
    # 환경변수에서 시간대 오프셋 읽기 (예: TZ_OFFSET=9 for KST)
    tz_offset = os.getenv("TZ_OFFSET")
    if tz_offset:
        try:
            return int(tz_offset)
        except ValueError:
            pass

    # 시스템 로컬 시간대 자동 감지
    # 시간대 정보가 있는 현재 시간을 사용하여 오프셋 계산
    local_now = datetime.now().astimezone()
    utc_offset = local_now.utcoffset()

    if utc_offset is not None:
        offset_hours = int(utc_offset.total_seconds() / 3600)
        return offset_hours

    # fallback: 기본값 0 (UTC)
    return 0


def utc_to_local(
    utc_time_str: str,
    format_str: str = "%Y-%m-%dT%H:%M:%SZ",
) -> datetime:
    """UTC 시간 문자열을 로컬 시간대의 datetime 객체로 변환합니다.

    Args:
        utc_time_str: UTC 시간 문자열 (예: "2025-09-24T16:58:08Z")
        format_str: 시간 문자열 형식

    Returns:
        datetime: 로컬 시간대로 변환된 datetime 객체
    """
    try:
        # UTC 시간을 datetime 객체로 파싱
        utc_dt = datetime.strptime(utc_time_str, format_str).replace(
            tzinfo=timezone.utc
        )

        # 로컬 시간대로 변환
        local_dt = utc_dt.astimezone()

        return local_dt
    except Exception:
        # 파싱 실패 시 현재 시간 반환
        return datetime.now()


def format_local_datetime(
    utc_time_str: str,
    format_str: str = "%Y-%m-%dT%H:%M:%SZ",
    output_format: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """UTC 시간 문자열을 로컬 시간대로 변환하여 포맷된 문자열로 반환합니다.

    Args:
        utc_time_str: UTC 시간 문자열
        format_str: 입력 시간 형식
        output_format: 출력 시간 형식

    Returns:
        str: 로컬 시간대로 변환된 포맷된 시간 문자열
    """
    try:
        local_dt = utc_to_local(utc_time_str, format_str)

        # 시간대 정보 추가
        tz_offset = get_local_timezone_offset()
        tz_name = "UTC"
        if tz_offset > 0:
            tz_name = f"UTC+{tz_offset}"
        elif tz_offset < 0:
            tz_name = f"UTC{tz_offset}"

        # KST 특별 처리
        if tz_offset == 9:
            tz_name = "KST"

        return f"{local_dt.strftime(output_format)} {tz_name}"

    except Exception:
        return f"시간 변환 실패: {utc_time_str}"


def get_timezone_aware_now() -> datetime:
    """현재 시간을 로컬 시간대 정보와 함께 반환합니다.

    Returns:
        datetime: 시간대 정보가 포함된 현재 시간
    """
    return datetime.now().replace(tzinfo=None).astimezone()


def format_sso_token_expiry(expires_at: str) -> str:
    """SSO 토큰 만료시간을 사용자 친화적 형식으로 변환합니다.

    Args:
        expires_at: UTC 형식의 만료시간 (예: "2025-09-24T16:58:08Z")

    Returns:
        str: 로컬 시간대로 변환된 만료시간 문자열
    """
    return format_local_datetime(expires_at, output_format="%Y-%m-%d %H:%M:%S")
