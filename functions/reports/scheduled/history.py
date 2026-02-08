"""
reports/scheduled/history.py - 정기 작업 실행 이력 관리

실행 이력을 JSON 파일로 저장하고 조회하는 기능 제공
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ScheduledRunRecord:
    """정기 작업 실행 기록"""

    task_id: str  # "D-001", "3M-002"
    task_name: str  # 작업명 (표시용)
    company: str  # 설정 프로필명
    run_at: str  # ISO format
    status: str  # "success", "failed", "cancelled"
    duration_sec: float  # 실행 시간 (초)
    error_msg: str = ""  # 오류 메시지 (실패 시)

    def get_display_time(self) -> str:
        """상대 시간 표시 (예: '2분 전', '1시간 전')"""
        try:
            run_time = datetime.fromisoformat(self.run_at)
            now = datetime.now()
            diff = now - run_time

            seconds = diff.total_seconds()

            if seconds < 60:
                return "방금 전"
            elif seconds < 3600:
                minutes = int(seconds / 60)
                return f"{minutes}분 전"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                return f"{hours}시간 전"
            elif seconds < 604800:
                days = int(seconds / 86400)
                return f"{days}일 전"
            else:
                return run_time.strftime("%m/%d")
        except (ValueError, TypeError):
            return ""

    def get_formatted_datetime(self) -> str:
        """포맷된 날짜/시간 (MM-DD HH:MM)"""
        try:
            run_time = datetime.fromisoformat(self.run_at)
            return run_time.strftime("%m-%d %H:%M")
        except (ValueError, TypeError):
            return ""

    def get_duration_display(self) -> str:
        """실행 시간 표시 (예: '12s', '1m 30s')"""
        if self.duration_sec < 0:
            return "--"
        if self.duration_sec < 60:
            return f"{int(self.duration_sec)}s"
        minutes = int(self.duration_sec / 60)
        seconds = int(self.duration_sec % 60)
        return f"{minutes}m {seconds}s"


class ScheduledRunHistory:
    """정기 작업 실행 이력 관리 (싱글톤)"""

    MAX_ITEMS = 100
    _instance: Optional["ScheduledRunHistory"] = None

    def __new__(cls) -> "ScheduledRunHistory":
        """싱글톤 패턴"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._path = self._get_history_path()
        self._items: list[ScheduledRunRecord] = []
        self._load()
        self._initialized = True

    def _get_history_path(self) -> Path:
        """이력 파일 경로"""
        from core.tools.cache import get_cache_path

        return Path(get_cache_path("history", "scheduled_runs.json"))

    def add(
        self,
        task_id: str,
        task_name: str,
        company: str,
        status: str,
        duration_sec: float,
        error_msg: str = "",
    ) -> None:
        """실행 기록 추가

        Args:
            task_id: 작업 ID (예: "D-001")
            task_name: 작업 표시명 (예: "Health 이벤트 현황")
            company: 설정 프로필명
            status: 상태 ("success", "failed", "cancelled")
            duration_sec: 실행 시간 (초)
            error_msg: 오류 메시지 (실패 시)
        """
        now = datetime.now().isoformat()

        # 새 기록 추가 (맨 앞에)
        self._items.insert(
            0,
            ScheduledRunRecord(
                task_id=task_id,
                task_name=task_name,
                company=company,
                run_at=now,
                status=status,
                duration_sec=duration_sec,
                error_msg=error_msg,
            ),
        )

        # 최대 개수 제한
        if len(self._items) > self.MAX_ITEMS:
            self._items = self._items[: self.MAX_ITEMS]

        self._save()

    def get_recent(self, limit: int = 10) -> list[ScheduledRunRecord]:
        """최근 실행 목록 (시간순)

        Args:
            limit: 반환할 최대 개수

        Returns:
            최근 실행 기록 리스트
        """
        return self._items[:limit]

    def get_by_task_id(self, task_id: str, limit: int = 5) -> list[ScheduledRunRecord]:
        """특정 작업의 실행 기록

        Args:
            task_id: 작업 ID
            limit: 반환할 최대 개수

        Returns:
            해당 작업의 실행 기록 리스트
        """
        results = [item for item in self._items if item.task_id == task_id]
        return results[:limit]

    def get_last_run(self, task_id: str) -> ScheduledRunRecord | None:
        """특정 작업의 마지막 실행 기록

        Args:
            task_id: 작업 ID

        Returns:
            마지막 실행 기록 또는 None
        """
        for item in self._items:
            if item.task_id == task_id:
                return item
        return None

    def get_all(self) -> list[ScheduledRunRecord]:
        """전체 이력"""
        return self._items.copy()

    def clear(self) -> None:
        """이력 초기화"""
        self._items.clear()
        self._save()

    def _load(self) -> None:
        """파일에서 로드"""
        if not self._path.exists():
            self._items = []
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._items = [ScheduledRunRecord(**item) for item in data]
        except (json.JSONDecodeError, TypeError, KeyError):
            self._items = []

    def _save(self) -> None:
        """파일에 저장"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(item) for item in self._items]
        self._path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def reload(self) -> None:
        """파일에서 다시 로드 (외부 변경 반영)"""
        self._load()
