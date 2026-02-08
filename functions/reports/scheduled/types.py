"""
reports/scheduled/types.py - 정기 작업 데이터 타입

작업 유형:
- 점검 (read): 현황 파악, 보고서 생성
- 적용 (write): 설정 변경, 태그 적용
- 정리 (delete): 리소스 삭제, 정리
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class TaskCycle(Enum):
    """작업 주기"""

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
    """정기 작업 항목"""

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
    """주기별 그룹"""

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
