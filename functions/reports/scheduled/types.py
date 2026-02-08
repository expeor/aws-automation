"""functions/reports/scheduled/types.py - 정기 작업 데이터 타입.

TaskCycle(주기 Enum), ScheduledTask(작업 항목), ScheduleGroup(주기별 그룹)
데이터 클래스와 권한별 색상 매핑을 정의합니다.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class TaskCycle(Enum):
    """작업 실행 주기.

    Attributes:
        DAILY: 일간 ("D").
        WEEKLY: 주간 ("W").
        MONTHLY: 월간 ("1M").
        QUARTERLY: 분기 ("3M").
        BIANNUAL: 반기 ("6M").
        ANNUAL: 연간 ("12M").
    """

    DAILY = "D"  # 일간
    WEEKLY = "W"  # 주간
    MONTHLY = "1M"  # 월간
    QUARTERLY = "3M"  # 분기
    BIANNUAL = "6M"  # 반기
    ANNUAL = "12M"  # 연간


# 권한 타입 (read/write/delete)
Permission = Literal["read", "write", "delete"]

# 권한별 색상 (기존 PERMISSION_COLORS와 일치)
PERMISSION_COLORS = {
    "read": "green",
    "write": "yellow",
    "delete": "red",
}


@dataclass
class ScheduledTask:
    """정기 작업 항목.

    Attributes:
        id: 고유 ID (예: "D-001", "3M-004").
        name: 한글 이름.
        name_en: 영문 이름.
        description: 한글 설명.
        description_en: 영문 설명.
        cycle: 작업 실행 주기 (TaskCycle).
        tool_ref: 참조 도구 경로 (예: "ec2/ebs_audit").
        permission: 권한 타입 ("read", "write", "delete").
        supports_regions: 멀티 리전 지원 여부.
        requires_input: 추가 입력이 필요한 경우의 입력 설정.
        requires_confirm: delete 작업 시 확인 필요 여부.
        enabled: 작업 활성화 여부.
    """

    id: str  # 고유 ID (예: "D-001", "3M-004")
    name: str  # 한글 이름
    name_en: str  # 영문 이름
    description: str
    description_en: str
    cycle: TaskCycle
    tool_ref: str  # 참조 도구 (예: "ec2/ebs_audit")
    permission: Permission  # read, write, delete
    supports_regions: bool = True
    requires_input: dict | None = None
    requires_confirm: bool = False  # delete 작업 시 확인 필요
    enabled: bool = True


@dataclass
class ScheduleGroup:
    """주기별 작업 그룹.

    Attributes:
        cycle: 이 그룹의 실행 주기 (TaskCycle).
        display_name: 한글 표시 이름 (예: "일간 작업").
        display_name_en: 영문 표시 이름 (예: "Daily Operations").
        color: Rich 콘솔 출력 색상.
        icon: 아이콘 문자열.
        tasks: 이 그룹에 속한 ScheduledTask 리스트.
    """

    cycle: TaskCycle
    display_name: str  # "일간 작업"
    display_name_en: str  # "Daily Operations"
    color: str  # Rich 색상
    icon: str  # 아이콘 (🕕, 📅, 📊, 📋, 📆)
    tasks: list[ScheduledTask] = field(default_factory=list)

    @property
    def read_count(self) -> int:
        """점검 작업 수"""
        return sum(1 for t in self.tasks if t.permission == "read")

    @property
    def write_count(self) -> int:
        """적용 작업 수"""
        return sum(1 for t in self.tasks if t.permission == "write")

    @property
    def delete_count(self) -> int:
        """정리 작업 수"""
        return sum(1 for t in self.tasks if t.permission == "delete")
