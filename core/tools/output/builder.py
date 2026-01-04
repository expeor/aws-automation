"""
pkg/output/builder.py - 출력 경로 빌더 구현
"""

import os
import subprocess
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import NamedTuple


class DatePattern(str, Enum):
    """날짜 패턴"""

    DAILY = "daily"  # 2025-12-09
    MONTHLY = "monthly"  # 2025/12
    YEARLY = "yearly"  # 2025
    WEEKLY = "weekly"  # 2025/12/12월1주차


class OutputResult(NamedTuple):
    """출력 결과"""

    path: str  # 파일 전체 경로
    directory: str  # 디렉토리 경로
    filename: str  # 파일명만


class OutputPath:
    """출력 경로 빌더

    프로파일/계정별로 체계적인 출력 경로를 생성합니다.

    사용 예시:
        # 기본
        path = OutputPath("my-profile").sub("tools", "ebs").build()
        # → output/my-profile/tools/ebs/

        # 날짜 포함
        path = OutputPath("my-profile") \\
            .sub("AWS_EBS_Reports") \\
            .with_date("monthly") \\
            .build()
        # → output/my-profile/AWS_EBS_Reports/2025/12/

        # 주차 계산 (weekly)
        path = OutputPath("my-profile") \\
            .sub("AWS_Daily_Status_Reports") \\
            .with_date("weekly") \\
            .build()
        # → output/my-profile/AWS_Daily_Status_Reports/2025/12/12월1주차/
    """

    def __init__(self, identifier: str):
        """
        Args:
            identifier: 프로파일명 또는 계정 ID
        """
        self._identifier = self._sanitize(identifier)
        self._parts: list[str] = []
        self._date_pattern: DatePattern | None = None
        self._root = self._get_project_root()

    def sub(self, *parts: str) -> "OutputPath":
        """하위 경로 추가

        Args:
            *parts: 경로 세그먼트들 (예: "tools", "ebs")

        Returns:
            자기 자신 (메서드 체이닝용)
        """
        self._parts.extend(parts)
        return self

    def with_date(self, pattern: str | DatePattern = DatePattern.DAILY) -> "OutputPath":
        """날짜 기반 하위 경로 추가

        Args:
            pattern: 날짜 패턴 ("daily", "monthly", "yearly", "weekly")

        Returns:
            자기 자신 (메서드 체이닝용)
        """
        if isinstance(pattern, str):
            pattern = DatePattern(pattern)
        self._date_pattern = pattern
        return self

    def build(self) -> str:
        """최종 디렉토리 경로 생성

        디렉토리가 없으면 자동으로 생성합니다.

        Returns:
            절대 경로 문자열
        """
        parts = ["output", self._identifier]
        parts.extend(self._parts)

        if self._date_pattern:
            parts.extend(self._get_date_parts(self._date_pattern))

        path = os.path.join(self._root, *parts)
        os.makedirs(path, exist_ok=True)
        return path

    def save_file(self, filename: str, content: str = "") -> OutputResult:
        """파일 저장 (빈 파일 또는 내용 포함)

        Args:
            filename: 파일명
            content: 파일 내용 (옵션)

        Returns:
            OutputResult(path, directory, filename)
        """
        directory = self.build()
        filepath = os.path.join(directory, filename)

        if content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        return OutputResult(
            path=filepath,
            directory=directory,
            filename=filename,
        )

    def open(self) -> None:
        """OS 파일 탐색기에서 디렉토리 열기"""
        path = self.build()
        open_in_explorer(path)

    @staticmethod
    def _sanitize(identifier: str) -> str:
        """파일 시스템 안전한 문자열로 변환"""
        return identifier.replace(" ", "_").replace("/", "_").replace("\\", "_")

    @staticmethod
    def _get_project_root() -> str:
        """프로젝트 루트 경로 반환

        우선순위:
        1. 환경 변수 AA_OUTPUT_ROOT
        2. CWD에서 pyproject.toml 또는 .git 탐색
        3. Fallback: CWD
        """
        # 1. 환경 변수 체크
        env_root = os.environ.get("AA_OUTPUT_ROOT")
        if env_root and Path(env_root).exists():
            return env_root

        # 2. CWD 기준으로 프로젝트 루트 탐색
        cwd = Path.cwd().resolve()
        for parent in [cwd, *cwd.parents]:
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                return str(parent)

        # 3. Fallback: CWD
        return str(cwd)

    @staticmethod
    def _get_date_parts(pattern: DatePattern) -> list[str]:
        """날짜 패턴에 따른 경로 세그먼트 반환"""
        now = datetime.now()

        if pattern == DatePattern.YEARLY:
            return [f"{now.year}"]

        elif pattern == DatePattern.MONTHLY:
            return [f"{now.year}", f"{now.month:02d}"]

        elif pattern == DatePattern.DAILY:
            return [f"{now.year}-{now.month:02d}-{now.day:02d}"]

        elif pattern == DatePattern.WEEKLY:
            # 주차 계산: 현재 날짜의 월의 첫째 주부터 1주차
            first_day_of_month = datetime(now.year, now.month, 1)
            days_since_first = (now - first_day_of_month).days
            week_number = (days_since_first // 7) + 1
            return [f"{now.year}", f"{now.month:02d}", f"{now.month}월{week_number}주차"]

        return []


def open_in_explorer(path: str) -> bool:
    """OS 파일 탐색기에서 폴더 열기

    Args:
        path: 열 폴더 경로

    Returns:
        True if 성공
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

    try:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
        return True
    except Exception:
        return False


def open_file(filepath: str) -> bool:
    """기본 프로그램으로 파일 열기

    Args:
        filepath: 열 파일 경로

    Returns:
        True if 성공
    """
    if not os.path.exists(filepath):
        return False

    try:
        if sys.platform == "win32":
            os.startfile(filepath)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", filepath], check=False)
        else:
            subprocess.run(["xdg-open", filepath], check=False)
        return True
    except Exception:
        return False


def single_report_directory(session_name: str) -> str:
    """SSO 세션 기반 단일 보고서 디렉토리 생성

    레거시 utils.file_handler.single_report_directory 호환 함수.

    Args:
        session_name: SSO 세션 이름

    Returns:
        생성된 디렉토리 경로

    사용 예시:
        output_dir = single_report_directory("my-sso-session")
        # → output/my-sso-session/reports/2025-12-31/
    """
    return OutputPath(session_name).sub("reports").with_date(DatePattern.DAILY).build()


def create_report_directory(
    tool_name: str,
    identifier: str = "default",
    date_pattern: str = "monthly",
) -> str:
    """도구별 보고서 디렉토리 생성

    레거시 utils.file_handler.create_report_directory 호환 함수.
    OutputPath를 사용하여 체계적인 경로를 생성합니다.

    Args:
        tool_name: 도구 이름 (예: "alb_log", "ebs", "tag")
        identifier: 프로파일명 또는 계정 ID (기본값: "default")
        date_pattern: 날짜 패턴 ("daily", "monthly", "yearly", "weekly")

    Returns:
        생성된 디렉토리 경로

    사용 예시:
        output_dir = create_report_directory("alb_log", "my-profile")
        # → output/my-profile/tools/alb_log/2025/12/
    """
    return OutputPath(identifier).sub("tools", tool_name).with_date(date_pattern).build()
