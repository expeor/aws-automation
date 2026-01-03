# tests/test_time_utils.py
"""
pkg/time/utils.py 단위 테스트

날짜/시간 변환 유틸리티 함수 테스트.
"""

import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from core.tools.time.utils import (
    format_local_datetime,
    format_sso_token_expiry,
    get_local_timezone_offset,
    get_timezone_aware_now,
    utc_to_local,
)

# =============================================================================
# get_local_timezone_offset 테스트
# =============================================================================


class TestGetLocalTimezoneOffset:
    """get_local_timezone_offset 함수 테스트"""

    def test_returns_integer(self):
        """정수 반환 확인 (시스템 시간대 사용)"""
        # 환경변수 설정 없이 시스템 시간대 사용
        with patch.dict(os.environ, {}, clear=True):
            # TZ_OFFSET이 없으면 시스템 시간대 사용
            if "TZ_OFFSET" in os.environ:
                del os.environ["TZ_OFFSET"]
        result = get_local_timezone_offset()
        assert isinstance(result, int)

    @patch.dict(os.environ, {"TZ_OFFSET": "9"})
    def test_uses_env_variable(self):
        """환경변수 TZ_OFFSET 사용 확인"""
        result = get_local_timezone_offset()
        assert result == 9

    @patch.dict(os.environ, {"TZ_OFFSET": "-5"})
    def test_negative_offset(self):
        """음수 오프셋 환경변수 확인"""
        result = get_local_timezone_offset()
        assert result == -5

    @patch.dict(os.environ, {"TZ_OFFSET": "0"})
    def test_zero_offset(self):
        """0 오프셋 환경변수 확인"""
        result = get_local_timezone_offset()
        assert result == 0

    def test_system_timezone_fallback(self):
        """환경변수 없을 때 시스템 시간대 사용"""
        # 환경변수 제거 후 테스트
        original = os.environ.pop("TZ_OFFSET", None)
        try:
            result = get_local_timezone_offset()
            # 시스템 시간대가 반환되어야 함 (정수)
            assert isinstance(result, int)
            # 합리적인 범위 내 (-12 ~ +14)
            assert -12 <= result <= 14
        finally:
            if original is not None:
                os.environ["TZ_OFFSET"] = original


# =============================================================================
# utc_to_local 테스트
# =============================================================================


class TestUtcToLocal:
    """utc_to_local 함수 테스트"""

    def test_converts_utc_string(self):
        """UTC 문자열을 datetime으로 변환"""
        result = utc_to_local("2025-12-10T10:00:00Z")

        assert isinstance(result, datetime)
        # UTC 10:00 → 로컬 시간대로 변환됨
        assert result.year == 2025
        assert result.month == 12

    def test_returns_datetime_object(self):
        """datetime 객체 반환"""
        result = utc_to_local("2025-01-15T08:30:00Z")
        assert isinstance(result, datetime)

    def test_custom_format(self):
        """커스텀 포맷 지원"""
        result = utc_to_local("2025-12-10 10:00:00", format_str="%Y-%m-%d %H:%M:%S")
        assert isinstance(result, datetime)

    def test_invalid_format_returns_current_time(self):
        """잘못된 포맷 시 현재 시간 반환"""
        result = utc_to_local("invalid-date-string")

        # 현재 시간이 반환되어야 함
        now = datetime.now()
        assert abs((result - now).total_seconds()) < 5  # 5초 이내


# =============================================================================
# format_local_datetime 테스트
# =============================================================================


class TestFormatLocalDatetime:
    """format_local_datetime 함수 테스트"""

    def test_returns_string(self):
        """문자열 반환 확인"""
        result = format_local_datetime("2025-12-10T10:00:00Z")
        assert isinstance(result, str)

    def test_contains_date_time(self):
        """날짜와 시간 포함"""
        result = format_local_datetime("2025-12-10T10:00:00Z")
        assert "2025" in result
        assert "12" in result

    def test_contains_timezone_info(self):
        """시간대 정보 포함"""
        result = format_local_datetime("2025-12-10T10:00:00Z")
        # UTC, KST, UTC+X, UTC-X 형태 중 하나 포함
        has_tz = any(tz in result for tz in ["UTC", "KST", "UTC+", "UTC-"])
        assert has_tz, f"시간대 정보가 없음: {result}"

    @patch("core.tools.time.utils.get_local_timezone_offset", return_value=9)
    def test_kst_timezone_label(self, mock_offset):
        """KST 시간대 레이블 확인"""
        result = format_local_datetime("2025-12-10T10:00:00Z")
        assert "KST" in result

    @patch("core.tools.time.utils.get_local_timezone_offset", return_value=0)
    def test_utc_timezone_label(self, mock_offset):
        """UTC 시간대 레이블 확인"""
        result = format_local_datetime("2025-12-10T10:00:00Z")
        assert "UTC" in result

    @patch("core.tools.time.utils.get_local_timezone_offset", return_value=-5)
    def test_negative_offset_label(self, mock_offset):
        """음수 오프셋 레이블 확인"""
        result = format_local_datetime("2025-12-10T10:00:00Z")
        assert "UTC-5" in result

    @patch("core.tools.time.utils.get_local_timezone_offset", return_value=5)
    def test_positive_offset_label(self, mock_offset):
        """양수 오프셋 레이블 확인"""
        result = format_local_datetime("2025-12-10T10:00:00Z")
        assert "UTC+5" in result

    def test_custom_output_format(self):
        """커스텀 출력 포맷"""
        result = format_local_datetime("2025-12-10T10:00:00Z", output_format="%Y/%m/%d")
        assert "2025/12/" in result

    def test_invalid_input_returns_fallback(self):
        """잘못된 입력 시 현재 시간 반환 (fallback)"""
        result = format_local_datetime("not-a-date")
        # 잘못된 입력이면 현재 시간이 반환됨 (예외 처리로 인해)
        # 결과는 문자열이고 시간대 정보 포함
        assert isinstance(result, str)
        # 현재 연도가 포함되어야 함
        assert "2025" in result or "2024" in result or "2026" in result


# =============================================================================
# get_timezone_aware_now 테스트
# =============================================================================


class TestGetTimezoneAwareNow:
    """get_timezone_aware_now 함수 테스트"""

    def test_returns_datetime(self):
        """datetime 객체 반환"""
        result = get_timezone_aware_now()
        assert isinstance(result, datetime)

    def test_has_timezone_info(self):
        """시간대 정보 포함"""
        result = get_timezone_aware_now()
        assert result.tzinfo is not None

    def test_is_current_time(self):
        """현재 시간에 가까움"""
        result = get_timezone_aware_now()
        now = datetime.now().astimezone()

        # 1초 이내여야 함
        diff = abs((result - now).total_seconds())
        assert diff < 1


# =============================================================================
# format_sso_token_expiry 테스트
# =============================================================================


class TestFormatSsoTokenExpiry:
    """format_sso_token_expiry 함수 테스트"""

    def test_returns_string(self):
        """문자열 반환"""
        result = format_sso_token_expiry("2025-12-10T10:00:00Z")
        assert isinstance(result, str)

    def test_contains_formatted_date(self):
        """포맷된 날짜 포함"""
        result = format_sso_token_expiry("2025-12-10T10:00:00Z")
        assert "2025" in result
        assert "12" in result
        assert "10" in result

    def test_readable_format(self):
        """읽기 쉬운 포맷"""
        result = format_sso_token_expiry("2025-12-10T10:00:00Z")
        # YYYY-MM-DD HH:MM:SS 형태여야 함
        assert "-" in result or "/" in result
        assert ":" in result
