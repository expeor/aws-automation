"""functions/reports/scheduled/registry.py - 정기 작업 레지스트리.

YAML 설정 파일을 로드하고 주기별 그룹(ScheduleGroup)으로 변환합니다.

설정 선택 우선순위:
    1. 함수 파라미터 (company).
    2. 환경변수 (AA_SCHEDULED_CONFIG).
    3. 기본값 (default.yaml).
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from .types import ScheduledTask, ScheduleGroup, TaskCycle

CONFIG_DIR = Path(__file__).parent / "config"

# 환경변수 키
ENV_CONFIG = "AA_SCHEDULED_CONFIG"


def get_config_from_env() -> str | None:
    """환경변수에서 설정 프로필명 조회"""
    return os.environ.get(ENV_CONFIG)


def resolve_company(company: str | None = None) -> str:
    """설정 프로필명 결정 (우선순위 적용)

    Args:
        company: 명시적 설정 프로필명 (최우선)

    Returns:
        결정된 설정명 (기본값: "default")
    """
    if company:
        return company
    return get_config_from_env() or "default"


def list_available_companies() -> list[str]:
    """사용 가능한 설정 프로필 목록 반환"""
    if not CONFIG_DIR.exists():
        return ["default"]
    return sorted([f.stem for f in CONFIG_DIR.glob("*.yaml")])


def _load_config_internal(company: str) -> dict[str, Any]:
    """내부 설정 로드 함수 (캐시 없음)"""
    config_file = CONFIG_DIR / f"{company}.yaml"
    if not config_file.exists():
        config_file = CONFIG_DIR / "default.yaml"

    with config_file.open(encoding="utf-8") as f:
        result: dict[str, Any] = yaml.safe_load(f)
        return result


# 캐시: company별로 최대 8개 설정 캐시
@lru_cache(maxsize=8)
def load_config(company: str | None = None) -> dict[str, Any]:
    """설정 파일 로드

    Args:
        company: 회사명 (None이면 환경변수 → default 순서)

    Returns:
        설정 딕셔너리
    """
    resolved = resolve_company(company)
    return _load_config_internal(resolved)


def get_schedule_groups(
    company: str | None = None,
    lang: str = "ko",
    include_empty: bool = False,
) -> list[ScheduleGroup]:
    """주기별 그룹 목록 반환

    Args:
        company: 설정 프로필명 (None이면 default)
        lang: 언어 ("ko" 또는 "en")
        include_empty: 빈 그룹 포함 여부 (기본: False)

    Returns:
        ScheduleGroup 목록 (빈 그룹은 기본적으로 제외)
    """
    config = load_config(company)
    groups = []

    for cycle_code, data in config.get("cycles", {}).items():
        try:
            cycle = TaskCycle(cycle_code)
        except ValueError:
            # 유효하지 않은 주기 코드 무시
            continue

        # tasks 섹션이 없거나 빈 리스트인 경우 처리
        task_list = data.get("tasks") or []

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
            for t in task_list
            if t.get("enabled", True)
        ]

        # 빈 그룹 필터링 (include_empty=False인 경우)
        if not include_empty and not tasks:
            continue

        groups.append(
            ScheduleGroup(
                cycle=cycle,
                display_name=data.get("display_name", cycle_code)
                if lang == "ko"
                else data.get("display_name_en", data.get("display_name", cycle_code)),
                display_name_en=data.get("display_name_en", data.get("display_name", cycle_code)),
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
