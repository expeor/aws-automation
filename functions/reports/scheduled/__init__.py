"""functions/reports/scheduled/__init__.py - 정기 작업 시스템 (Scheduled Operations).

회사 거버넌스에 맞게 일간/주간/월간/분기/반기/연간 정기 작업을 관리합니다.
YAML 설정 파일로 회사별 작업 목록을 정의하고, 실행 이력을 JSON으로 관리합니다.

작업 유형:
    - 점검 (read): 현황 파악, 보고서 생성.
    - 적용 (write): 설정 변경, 태그 적용.
    - 정리 (delete): 리소스 삭제, 정리.
"""

CATEGORY = {
    "name": "scheduled",
    "display_name": "Scheduled Operations",
    "description": "정기 작업 (일간/월간/분기/반기/연간)",
    "description_en": "Scheduled Operations (Daily/Monthly/Quarterly/Biannual/Annual)",
    "aliases": ["periodic", "routine", "governance", "schedule"],
}

# 메뉴 전환용 도구 (CategoryStep에서 is_menu 처리)
TOOLS = [
    {
        "name": "정기 작업 관리",
        "name_en": "Scheduled Operations Management",
        "description": "일간/월간/분기/반기/연간 정기 작업 실행",
        "description_en": "Execute daily/monthly/quarterly/biannual/annual scheduled operations",
        "permission": "read",
        "module": "menu",
        "is_menu": True,
        "area": "inventory",  # 관리 도구이므로 inventory 분류
        "require_session": False,  # 메뉴 진입 시 인증 불필요
    },
]

# 외부 API
from .history import ScheduledRunHistory, ScheduledRunRecord
from .menu import show_scheduled_menu
from .registry import get_all_tasks, get_schedule_groups, get_tasks_by_permission, load_config
from .schedule import format_next_run_date, get_next_run_date, is_due
from .types import PERMISSION_COLORS, ScheduledTask, ScheduleGroup, TaskCycle

__all__ = [
    "CATEGORY",
    "TOOLS",
    "TaskCycle",
    "ScheduledTask",
    "ScheduleGroup",
    "PERMISSION_COLORS",
    "get_schedule_groups",
    "get_all_tasks",
    "get_tasks_by_permission",
    "load_config",
    "show_scheduled_menu",
    # history
    "ScheduledRunHistory",
    "ScheduledRunRecord",
    # schedule
    "get_next_run_date",
    "format_next_run_date",
    "is_due",
]
