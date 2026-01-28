"""
reports/scheduled - 정기 작업 시스템 (Scheduled Operations)

회사 거버넌스에 맞게 일간/월간/분기/반기/연간 정기 작업을 관리합니다.

작업 유형:
- 점검 (read): 현황 파악, 보고서 생성
- 적용 (write): 설정 변경, 태그 적용
- 정리 (delete): 리소스 삭제, 정리
"""

CATEGORY = {
    "name": "scheduled",
    "display_name": "Scheduled Operations",
    "description": "정기 작업 (일간/월간/분기/반기/연간)",
    "description_en": "Scheduled Operations (Daily/Monthly/Quarterly/Biannual/Annual)",
    "aliases": ["periodic", "routine", "governance", "schedule"],
}

# Discovery용 빈 TOOLS (메뉴에서 직접 처리)
TOOLS: list = []

# 외부 API
from .menu import show_scheduled_menu
from .registry import get_all_tasks, get_schedule_groups, get_tasks_by_permission, load_config
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
]
