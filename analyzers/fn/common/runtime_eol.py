"""
plugins/fn/common/runtime_eol.py - Lambda 런타임 EOL 정보

AWS Lambda 런타임 지원 종료 일정 관리
https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

# Amazon Linux OS 버전 상수
OS_AL1 = "AL1"
OS_AL2 = "AL2"
OS_AL2023 = "AL2023"


class EOLStatus(Enum):
    """EOL 상태"""

    DEPRECATED = "deprecated"  # 이미 지원 종료
    CRITICAL = "critical"  # 30일 이내 종료
    HIGH = "high"  # 90일 이내 종료
    MEDIUM = "medium"  # 180일 이내 종료
    LOW = "low"  # 180일 이상 남음
    SUPPORTED = "supported"  # 지원 중 (EOL 미정)


@dataclass
class RuntimeInfo:
    """런타임 정보"""

    runtime_id: str
    name: str
    deprecation_date: date | None  # Phase 1: 생성 차단
    block_update_date: date | None  # Phase 2: 업데이트 차단
    eol_date: date | None  # 완전 종료 (있는 경우)
    os_version: str = ""  # Amazon Linux 버전: AL1, AL2, AL2023
    recommended_upgrade: str = ""  # 권장 업그레이드 런타임 (예: "python3.13")

    @property
    def is_deprecated(self) -> bool:
        """지원 종료 여부"""
        if not self.deprecation_date:
            return False
        return date.today() >= self.deprecation_date

    @property
    def days_until_deprecation(self) -> int | None:
        """지원 종료까지 남은 일수"""
        if not self.deprecation_date:
            return None
        delta = self.deprecation_date - date.today()
        return delta.days

    @property
    def status(self) -> EOLStatus:
        """EOL 상태"""
        if self.is_deprecated:
            return EOLStatus.DEPRECATED

        days = self.days_until_deprecation
        if days is None:
            return EOLStatus.SUPPORTED

        if days <= 30:
            return EOLStatus.CRITICAL
        elif days <= 90:
            return EOLStatus.HIGH
        elif days <= 180:
            return EOLStatus.MEDIUM
        else:
            return EOLStatus.LOW


# Lambda 런타임 EOL 정보 (2026년 2월 기준)
# 출처: https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
RUNTIME_EOL_DATA: dict[str, RuntimeInfo] = {
    # Python - Active
    "python3.14": RuntimeInfo("python3.14", "Python 3.14", None, None, None, OS_AL2023),
    "python3.13": RuntimeInfo("python3.13", "Python 3.13", None, None, None, OS_AL2023),
    "python3.12": RuntimeInfo("python3.12", "Python 3.12", date(2028, 10, 31), date(2029, 2, 28), None, OS_AL2023),
    "python3.11": RuntimeInfo(
        "python3.11", "Python 3.11", date(2027, 6, 30), date(2027, 10, 31), None, OS_AL2, "python3.13"
    ),
    "python3.10": RuntimeInfo(
        "python3.10", "Python 3.10", date(2026, 10, 31), date(2027, 2, 28), None, OS_AL2, "python3.13"
    ),
    # Python - Deprecated
    "python3.9": RuntimeInfo(
        "python3.9", "Python 3.9", date(2025, 12, 15), date(2026, 3, 15), None, OS_AL2, "python3.13"
    ),
    "python3.8": RuntimeInfo(
        "python3.8", "Python 3.8", date(2024, 10, 14), date(2025, 2, 28), None, OS_AL2, "python3.13"
    ),
    "python3.7": RuntimeInfo(
        "python3.7", "Python 3.7", date(2023, 12, 4), date(2024, 1, 9), None, OS_AL1, "python3.13"
    ),
    "python3.6": RuntimeInfo(
        "python3.6", "Python 3.6", date(2022, 7, 18), date(2022, 8, 17), None, OS_AL1, "python3.13"
    ),
    "python2.7": RuntimeInfo(
        "python2.7", "Python 2.7", date(2021, 7, 15), date(2022, 5, 30), None, OS_AL1, "python3.13"
    ),
    # Node.js - Active
    "nodejs24.x": RuntimeInfo("nodejs24.x", "Node.js 24", date(2028, 4, 30), date(2028, 8, 31), None, OS_AL2023),
    "nodejs22.x": RuntimeInfo("nodejs22.x", "Node.js 22", date(2027, 4, 30), date(2027, 8, 31), None, OS_AL2023),
    "nodejs20.x": RuntimeInfo(
        "nodejs20.x", "Node.js 20", date(2026, 4, 30), date(2026, 8, 31), None, OS_AL2023, "nodejs22.x"
    ),
    # Node.js - Deprecated
    "nodejs18.x": RuntimeInfo(
        "nodejs18.x", "Node.js 18", date(2025, 9, 1), date(2025, 12, 1), None, OS_AL2023, "nodejs22.x"
    ),
    "nodejs16.x": RuntimeInfo(
        "nodejs16.x", "Node.js 16", date(2024, 6, 12), date(2025, 2, 28), None, OS_AL2, "nodejs22.x"
    ),
    "nodejs14.x": RuntimeInfo(
        "nodejs14.x", "Node.js 14", date(2023, 12, 4), date(2024, 1, 9), None, OS_AL2, "nodejs22.x"
    ),
    "nodejs12.x": RuntimeInfo(
        "nodejs12.x", "Node.js 12", date(2023, 3, 31), date(2023, 4, 30), None, OS_AL2, "nodejs22.x"
    ),
    # Java - Active
    "java25": RuntimeInfo("java25", "Java 25", None, None, None, OS_AL2023),
    "java21": RuntimeInfo("java21", "Java 21", None, None, None, OS_AL2023),
    "java17": RuntimeInfo("java17", "Java 17", date(2027, 6, 30), date(2027, 10, 31), None, OS_AL2, "java21"),
    "java11": RuntimeInfo("java11", "Java 11", date(2027, 6, 30), date(2027, 10, 31), None, OS_AL2, "java21"),
    "java8.al2": RuntimeInfo(
        "java8.al2", "Java 8 (AL2)", date(2027, 6, 30), date(2027, 10, 31), None, OS_AL2, "java21"
    ),
    # Java - Deprecated
    "java8": RuntimeInfo("java8", "Java 8", date(2024, 1, 8), date(2024, 2, 8), None, OS_AL1, "java21"),
    # .NET - Active
    "dotnet10": RuntimeInfo("dotnet10", ".NET 10", date(2028, 11, 14), date(2029, 3, 14), None, OS_AL2023),
    "dotnet8": RuntimeInfo("dotnet8", ".NET 8", date(2026, 11, 10), date(2027, 3, 10), None, OS_AL2023, "dotnet10"),
    # .NET - Deprecated
    "dotnet6": RuntimeInfo("dotnet6", ".NET 6", date(2024, 11, 12), date(2025, 2, 28), None, OS_AL2023, "dotnet10"),
    "dotnetcore3.1": RuntimeInfo(
        "dotnetcore3.1", ".NET Core 3.1", date(2023, 4, 3), date(2023, 5, 3), None, OS_AL2, "dotnet10"
    ),
    # Ruby - Active
    "ruby3.4": RuntimeInfo("ruby3.4", "Ruby 3.4", date(2028, 3, 31), date(2028, 7, 31), None, OS_AL2023),
    "ruby3.3": RuntimeInfo("ruby3.3", "Ruby 3.3", date(2027, 3, 31), date(2027, 7, 31), None, OS_AL2023),
    "ruby3.2": RuntimeInfo("ruby3.2", "Ruby 3.2", date(2026, 3, 31), date(2026, 7, 31), None, OS_AL2, "ruby3.4"),
    # Ruby - Deprecated
    "ruby2.7": RuntimeInfo("ruby2.7", "Ruby 2.7", date(2023, 12, 7), date(2024, 1, 9), None, OS_AL2, "ruby3.4"),
    # Go - Deprecated
    "go1.x": RuntimeInfo("go1.x", "Go 1.x", date(2023, 12, 31), date(2024, 1, 30), None, OS_AL1, "provided.al2023"),
    # Custom runtime
    "provided.al2023": RuntimeInfo("provided.al2023", "Custom (AL2023)", None, None, None, OS_AL2023),
    "provided.al2": RuntimeInfo(
        "provided.al2", "Custom (AL2)", date(2026, 7, 31), date(2026, 11, 30), None, OS_AL2, "provided.al2023"
    ),
    "provided": RuntimeInfo(
        "provided", "Custom", date(2023, 12, 31), date(2024, 1, 30), None, OS_AL1, "provided.al2023"
    ),
}


def get_runtime_info(runtime_id: str) -> RuntimeInfo | None:
    """런타임 정보 조회"""
    return RUNTIME_EOL_DATA.get(runtime_id)


def get_runtime_status(runtime_id: str) -> EOLStatus:
    """런타임 EOL 상태 조회"""
    info = get_runtime_info(runtime_id)
    if info:
        return info.status
    # 알 수 없는 런타임
    return EOLStatus.SUPPORTED


def get_deprecated_runtimes() -> dict[str, RuntimeInfo]:
    """지원 종료된 런타임 목록"""
    return {k: v for k, v in RUNTIME_EOL_DATA.items() if v.is_deprecated}


def get_expiring_runtimes(days: int = 180) -> dict[str, RuntimeInfo]:
    """곧 지원 종료될 런타임 목록"""
    result = {}
    for k, v in RUNTIME_EOL_DATA.items():
        remaining = v.days_until_deprecation
        if remaining is not None and 0 < remaining <= days:
            result[k] = v
    return result


def get_recommended_upgrade(runtime_id: str) -> str | None:
    """권장 업그레이드 런타임"""
    info = RUNTIME_EOL_DATA.get(runtime_id)
    if info and info.recommended_upgrade:
        return info.recommended_upgrade
    return None


def get_os_runtimes(os_version: str) -> dict[str, RuntimeInfo]:
    """특정 OS 버전의 런타임 목록"""
    return {k: v for k, v in RUNTIME_EOL_DATA.items() if v.os_version == os_version}
