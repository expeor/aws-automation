"""
reports/scheduled/registry.py - 정기 작업 레지스트리

YAML 설정 파일 로드 및 주기별 그룹화
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .types import ScheduledTask, ScheduleGroup, TaskCycle

CONFIG_DIR = Path(__file__).parent / "config"


@lru_cache(maxsize=1)
def load_config(company: str | None = None) -> dict[str, Any]:
    """설정 파일 로드

    Args:
        company: 회사명 (None이면 default)

    Returns:
        설정 딕셔너리
    """
    config_file = CONFIG_DIR / f"{company or 'default'}.yaml"
    if not config_file.exists():
        config_file = CONFIG_DIR / "default.yaml"

    with config_file.open(encoding="utf-8") as f:
        result: dict[str, Any] = yaml.safe_load(f)
        return result


def get_schedule_groups(company: str | None = None, lang: str = "ko") -> list[ScheduleGroup]:
    """주기별 그룹 목록 반환

    Args:
        company: 회사명 (None이면 default)
        lang: 언어 ("ko" 또는 "en")

    Returns:
        ScheduleGroup 목록
    """
    config = load_config(company)
    groups = []

    for cycle_code, data in config.get("cycles", {}).items():
        try:
            cycle = TaskCycle(cycle_code)
        except ValueError:
            continue

        tasks = [
            ScheduledTask(
                id=t["id"],
                name=t["name"],
                name_en=t.get("name_en", t["name"]),
                description=t.get("description", ""),
                description_en=t.get("description_en", ""),
                cycle=cycle,
                tool_ref=t["tool_ref"],
                permission=t.get("permission", "read"),
                supports_regions=t.get("supports_regions", True),
                requires_input=t.get("requires_input"),
                requires_confirm=t.get("requires_confirm", False),
                enabled=t.get("enabled", True),
            )
            for t in data.get("tasks", [])
            if t.get("enabled", True)
        ]

        groups.append(
            ScheduleGroup(
                cycle=cycle,
                display_name=data["display_name"] if lang == "ko" else data.get("display_name_en", data["display_name"]),
                display_name_en=data.get("display_name_en", data["display_name"]),
                color=data.get("color", "dim"),
                icon=data.get("icon", "📄"),
                tasks=tasks,
            )
        )

    # 주기 순서 정렬 (일간 → 연간)
    cycle_order = ["D", "W", "1M", "3M", "6M", "12M"]
    groups.sort(key=lambda g: cycle_order.index(g.cycle.value) if g.cycle.value in cycle_order else 99)

    return groups


def get_all_tasks(company: str | None = None) -> list[ScheduledTask]:
    """모든 정기 작업 평면 목록

    Args:
        company: 회사명 (None이면 default)

    Returns:
        ScheduledTask 목록
    """
    tasks = []
    for group in get_schedule_groups(company):
        tasks.extend(group.tasks)
    return tasks


def get_tasks_by_permission(permission: str, company: str | None = None) -> list[ScheduledTask]:
    """권한별 작업 필터링

    Args:
        permission: 권한 타입 ("read", "write", "delete")
        company: 회사명 (None이면 default)

    Returns:
        해당 권한의 ScheduledTask 목록
    """
    return [t for t in get_all_tasks(company) if t.permission == permission]
